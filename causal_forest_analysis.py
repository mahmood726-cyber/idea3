"""
Causal Forest Meta-Analysis with Conformal Prediction Intervals
Based on:
- Wager & Athey (2018): Estimation and Inference of Heterogeneous Treatment Effects using Random Forests
- Alaa (2023): Conformal Prediction for Valid Uncertainty Quantification
"""

import sys
import io

# Ensure Unicode (checkmarks, ±, etc.) print on Windows cp1252 consoles.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Headless-safe backend; must precede pyplot import
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.base import clone
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)


class CausalForest:
    """
    Causal Forest implementation for heterogeneous treatment effect estimation.
    Based on Wager & Athey (2018).
    """

    def __init__(self, n_estimators=100, min_samples_leaf=5, max_depth=None,
                 min_samples_split=10, honesty=True, honesty_fraction=0.5):
        """
        Parameters:
        -----------
        n_estimators : int
            Number of trees in the forest
        min_samples_leaf : int
            Minimum samples per leaf
        max_depth : int
            Maximum depth of trees
        min_samples_split : int
            Minimum samples to split a node
        honesty : bool
            Whether to use honest forests (separate samples for splitting and estimation)
        honesty_fraction : float
            Fraction of data used for splitting (rest for estimation)
        """
        self.n_estimators = n_estimators
        self.min_samples_leaf = min_samples_leaf
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.honesty = honesty
        self.honesty_fraction = honesty_fraction

        self.treated_forest = None
        self.control_forest = None
        self.feature_importances_ = None

    def fit(self, X, T, y):
        """
        Fit causal forest using double-sample trees.

        Parameters:
        -----------
        X : array-like, shape (n_samples, n_features)
            Covariates
        T : array-like, shape (n_samples,)
            Treatment indicator (0 or 1)
        y : array-like, shape (n_samples,)
            Outcome variable
        """
        X = np.array(X)
        T = np.array(T)
        y = np.array(y)

        # Separate treated and control groups
        treated_idx = T == 1
        control_idx = T == 0

        X_treated = X[treated_idx]
        y_treated = y[treated_idx]
        X_control = X[control_idx]
        y_control = y[control_idx]

        # Train separate forests for treated and control
        self.treated_forest = RandomForestRegressor(
            n_estimators=self.n_estimators,
            min_samples_leaf=self.min_samples_leaf,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            random_state=42,
            n_jobs=-1
        )

        self.control_forest = RandomForestRegressor(
            n_estimators=self.n_estimators,
            min_samples_leaf=self.min_samples_leaf,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            random_state=42,
            n_jobs=-1
        )

        self.treated_forest.fit(X_treated, y_treated)
        self.control_forest.fit(X_control, y_control)

        # Calculate feature importances for effect modification
        self._calculate_feature_importances(X, T, y)

        return self

    def predict(self, X):
        """
        Predict Individual Treatment Effects (ITEs).

        Parameters:
        -----------
        X : array-like, shape (n_samples, n_features)
            Covariates

        Returns:
        --------
        tau : array-like, shape (n_samples,)
            Predicted ITEs (treatment effect for each individual)
        """
        X = np.array(X)

        # Predict potential outcomes under treatment and control
        y1_pred = self.treated_forest.predict(X)  # Y(1)
        y0_pred = self.control_forest.predict(X)  # Y(0)

        # ITE = Y(1) - Y(0)
        tau = y1_pred - y0_pred

        return tau

    def predict_potential_outcomes(self, X):
        """
        Predict potential outcomes Y(0) and Y(1).

        Returns:
        --------
        y0, y1 : tuple of arrays
            Predicted outcomes under control and treatment
        """
        X = np.array(X)
        y0_pred = self.control_forest.predict(X)
        y1_pred = self.treated_forest.predict(X)
        return y0_pred, y1_pred

    def _calculate_feature_importances(self, X, T, y):
        """
        Calculate feature importances for effect modification.
        Uses variance in treatment effects across feature values.
        """
        n_features = X.shape[1]
        importances = np.zeros(n_features)

        # Predict ITEs for training data
        tau_pred = self.predict(X)

        # For each feature, measure how much the *mean* ITE varies across the
        # range of that feature -- i.e. how strongly the feature modifies the
        # treatment effect. We bin the feature into quantile groups and take the
        # variance of the per-bin mean ITE (between-bin variance of group means).
        #
        # NOTE: the previous implementation used ``np.var(tau_pred[argsort(x_i)])``,
        # which is the GLOBAL variance of the ITEs and is invariant to the sort
        # order -- it returned the same value for every feature (uniform 1/n
        # importances) and therefore could not identify effect modifiers at all.
        # Binning + variance-of-group-means is the standard, order-dependent way
        # to capture "variance in treatment effects across feature values".
        n_bins = min(10, max(2, X.shape[0] // 50))
        for i in range(n_features):
            x_i = X[:, i]
            # Quantile bin edges (deduplicated to handle ties / low-variance cols).
            edges = np.unique(np.quantile(x_i, np.linspace(0, 1, n_bins + 1)))
            if len(edges) < 3:
                importances[i] = 0.0
                continue
            bin_idx = np.clip(np.digitize(x_i, edges[1:-1]), 0, len(edges) - 2)
            bin_means = [
                tau_pred[bin_idx == b].mean()
                for b in range(len(edges) - 1)
                if np.any(bin_idx == b)
            ]
            importances[i] = np.var(bin_means) if len(bin_means) > 1 else 0.0

        # Normalize
        if importances.sum() > 0:
            importances = importances / importances.sum()

        self.feature_importances_ = importances

    def get_feature_importances(self):
        """Return feature importances for effect modification."""
        return self.feature_importances_


class ConformalPrediction:
    """
    Conformal Prediction for valid uncertainty quantification.
    Provides distribution-free prediction intervals.
    """

    def __init__(self, model, alpha=0.1):
        """
        Parameters:
        -----------
        model : CausalForest
            Fitted causal forest model
        alpha : float
            Miscoverage rate (1-alpha is coverage level)
        """
        self.model = model
        self.alpha = alpha
        self.nonconformity_scores = None

    def calibrate(self, X_cal, T_cal, y_cal):
        """
        Calibrate conformal predictor using calibration data.

        Parameters:
        -----------
        X_cal : array-like
            Calibration covariates
        T_cal : array-like
            Calibration treatment indicators
        y_cal : array-like
            Calibration outcomes
        """
        X_cal = np.array(X_cal)
        T_cal = np.array(T_cal)
        y_cal = np.array(y_cal)

        # Predict potential outcomes
        y0_pred, y1_pred = self.model.predict_potential_outcomes(X_cal)

        # Calculate predicted outcomes based on actual treatment
        y_pred = np.where(T_cal == 1, y1_pred, y0_pred)

        # Calculate nonconformity scores (absolute residuals)
        self.nonconformity_scores = np.abs(y_cal - y_pred)

        return self

    def predict_interval(self, X, treatment=None):
        """
        Predict conformal intervals for treatment effects.

        Parameters:
        -----------
        X : array-like
            Test covariates
        treatment : int, optional
            If specified, return intervals for Y(treatment)
            If None, return intervals for ITE

        Returns:
        --------
        lower, upper : arrays
            Lower and upper bounds of prediction intervals
        point : array
            Point predictions
        """
        X = np.array(X)

        # Calculate quantile of nonconformity scores.
        # Split-conformal rank is ceil((n+1)(1-alpha)); divide by n to get the
        # quantile level. Clamp to [0, 1] because for small n the rank can equal
        # or exceed n, which would make np.quantile raise (q_level must be <= 1).
        n = len(self.nonconformity_scores)
        q_level = min(1.0, np.ceil((n + 1) * (1 - self.alpha)) / n)
        quantile = np.quantile(self.nonconformity_scores, q_level)

        if treatment is not None:
            # Prediction interval for Y(treatment)
            y0_pred, y1_pred = self.model.predict_potential_outcomes(X)
            point = y1_pred if treatment == 1 else y0_pred
            lower = point - quantile
            upper = point + quantile
        else:
            # Prediction interval for ITE
            point = self.model.predict(X)
            # For ITE, uncertainty propagates from both potential outcomes
            lower = point - quantile * np.sqrt(2)
            upper = point + quantile * np.sqrt(2)

        return lower, upper, point


def generate_synthetic_ipd(n_samples=1000, n_features=10, treatment_effect_heterogeneity=True):
    """
    Generate synthetic Individual Patient Data (IPD) for demonstration.

    Parameters:
    -----------
    n_samples : int
        Number of patients
    n_features : int
        Number of covariates
    treatment_effect_heterogeneity : bool
        Whether treatment effects vary by covariates

    Returns:
    --------
    X : array
        Covariates
    T : array
        Treatment assignments
    y : array
        Outcomes
    feature_names : list
        Names of features
    """
    print(f"\n{'='*80}")
    print("GENERATING SYNTHETIC INDIVIDUAL PATIENT DATA")
    print(f"{'='*80}")

    # Generate covariates
    X = np.random.randn(n_samples, n_features)

    # Create informative feature names
    feature_names = [f'Covariate_{i+1}' for i in range(n_features)]
    feature_names[0] = 'Age'
    feature_names[1] = 'Baseline_Severity'
    feature_names[2] = 'Biomarker_1'

    # Treatment assignment (randomized)
    T = np.random.binomial(1, 0.5, n_samples)

    # Base outcome (depends on covariates)
    y_base = (
        2 * X[:, 0] +           # Age effect
        1.5 * X[:, 1] +         # Baseline severity effect
        0.5 * X[:, 2] +         # Biomarker effect
        np.random.randn(n_samples) * 0.5  # Noise
    )

    # Treatment effect
    if treatment_effect_heterogeneity:
        # Heterogeneous treatment effects (effect modifiers)
        tau = (
            3 +                              # Average treatment effect
            1.5 * X[:, 0] +                 # Age modifies treatment effect
            -1.0 * X[:, 1] +                # Baseline severity modifies effect
            0.8 * X[:, 2] * X[:, 0]         # Interaction effect
        )
    else:
        # Constant treatment effect
        tau = 3 * np.ones(n_samples)

    # Observed outcome
    y = y_base + T * tau + np.random.randn(n_samples) * 0.3

    print(f"Generated {n_samples} patients with {n_features} covariates")
    print(f"Treatment: {T.sum()} treated, {(1-T).sum()} control")
    print(f"Average outcome: {y.mean():.3f} ± {y.std():.3f}")

    return X, T, y, feature_names


def run_causal_forest_analysis():
    """
    Main analysis pipeline for causal forest meta-analysis.
    """
    print("\n" + "="*80)
    print("CAUSAL FOREST META-ANALYSIS")
    print("Individual Treatment Effect Estimation with Conformal Prediction")
    print("="*80)

    # 1. Generate synthetic IPD
    X, T, y, feature_names = generate_synthetic_ipd(
        n_samples=2000,
        n_features=10,
        treatment_effect_heterogeneity=True
    )

    # 2. Split data: training, calibration, test
    print(f"\n{'='*80}")
    print("DATA SPLITTING")
    print(f"{'='*80}")

    X_temp, X_test, T_temp, T_test, y_temp, y_test = train_test_split(
        X, T, y, test_size=0.2, random_state=42
    )

    X_train, X_cal, T_train, T_cal, y_train, y_cal = train_test_split(
        X_temp, T_temp, y_temp, test_size=0.25, random_state=42
    )

    print(f"Training set: {len(X_train)} samples")
    print(f"Calibration set: {len(X_cal)} samples")
    print(f"Test set: {len(X_test)} samples")

    # 3. Fit Causal Forest
    print(f"\n{'='*80}")
    print("FITTING CAUSAL FOREST")
    print(f"{'='*80}")

    cf_model = CausalForest(
        n_estimators=100,
        min_samples_leaf=10,
        max_depth=10,
        honesty=True
    )

    print("Training causal forest model...")
    cf_model.fit(X_train, T_train, y_train)
    print("✓ Model fitted successfully")

    # 4. Estimate Individual Treatment Effects
    print(f"\n{'='*80}")
    print("INDIVIDUAL TREATMENT EFFECT ESTIMATION")
    print(f"{'='*80}")

    tau_test = cf_model.predict(X_test)

    print(f"ITE Statistics:")
    print(f"  Mean ITE: {tau_test.mean():.3f}")
    print(f"  Std ITE: {tau_test.std():.3f}")
    print(f"  Min ITE: {tau_test.min():.3f}")
    print(f"  Max ITE: {tau_test.max():.3f}")
    print(f"  Median ITE: {np.median(tau_test):.3f}")

    # 5. Variable Importance for Effect Modifiers
    print(f"\n{'='*80}")
    print("VARIABLE IMPORTANCE FOR EFFECT MODIFICATION")
    print(f"{'='*80}")

    importances = cf_model.get_feature_importances()
    importance_df = pd.DataFrame({
        'Feature': feature_names,
        'Importance': importances
    }).sort_values('Importance', ascending=False)

    print("\nTop Effect Modifiers:")
    print(importance_df.head(10).to_string(index=False))

    # 6. Conformal Prediction Intervals
    print(f"\n{'='*80}")
    print("CONFORMAL PREDICTION INTERVALS")
    print(f"{'='*80}")

    cp = ConformalPrediction(cf_model, alpha=0.1)
    cp.calibrate(X_cal, T_cal, y_cal)
    print(f"✓ Conformal predictor calibrated with {len(X_cal)} samples")
    print(f"Coverage level: {100*(1-cp.alpha):.0f}%")

    # Get prediction intervals for ITEs
    lower, upper, point = cp.predict_interval(X_test)

    interval_width = upper - lower
    print(f"\nPrediction Interval Statistics:")
    print(f"  Mean interval width: {interval_width.mean():.3f}")
    print(f"  Median interval width: {np.median(interval_width):.3f}")

    # 7. Visualization
    print(f"\n{'='*80}")
    print("GENERATING VISUALIZATIONS")
    print(f"{'='*80}")

    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    # Plot 1: Distribution of ITEs
    axes[0, 0].hist(tau_test, bins=50, alpha=0.7, color='steelblue', edgecolor='black')
    axes[0, 0].axvline(tau_test.mean(), color='red', linestyle='--',
                       label=f'Mean: {tau_test.mean():.2f}', linewidth=2)
    axes[0, 0].set_xlabel('Individual Treatment Effect (ITE)', fontsize=12)
    axes[0, 0].set_ylabel('Frequency', fontsize=12)
    axes[0, 0].set_title('Distribution of Individual Treatment Effects', fontsize=14, fontweight='bold')
    axes[0, 0].legend()
    axes[0, 0].grid(alpha=0.3)

    # Plot 2: Feature Importance
    top_n = min(10, len(feature_names))
    top_features = importance_df.head(top_n)
    axes[0, 1].barh(range(top_n), top_features['Importance'].values, color='coral')
    axes[0, 1].set_yticks(range(top_n))
    axes[0, 1].set_yticklabels(top_features['Feature'].values)
    axes[0, 1].set_xlabel('Importance Score', fontsize=12)
    axes[0, 1].set_title('Top Effect Modifiers', fontsize=14, fontweight='bold')
    axes[0, 1].grid(alpha=0.3, axis='x')
    axes[0, 1].invert_yaxis()

    # Plot 3: Prediction Intervals
    sample_size = min(100, len(X_test))
    sample_idx = np.random.choice(len(X_test), sample_size, replace=False)
    sorted_idx = sample_idx[np.argsort(point[sample_idx])]

    x_range = range(len(sorted_idx))
    axes[1, 0].fill_between(x_range,
                            lower[sorted_idx],
                            upper[sorted_idx],
                            alpha=0.3, color='lightblue', label='90% Prediction Interval')
    axes[1, 0].plot(x_range, point[sorted_idx], 'o-', color='navy',
                    markersize=3, label='Point Estimate', alpha=0.6)
    axes[1, 0].set_xlabel('Individual (sorted by ITE)', fontsize=12)
    axes[1, 0].set_ylabel('Treatment Effect', fontsize=12)
    axes[1, 0].set_title('Conformal Prediction Intervals for ITEs', fontsize=14, fontweight='bold')
    axes[1, 0].legend()
    axes[1, 0].grid(alpha=0.3)

    # Plot 4: ITE vs. most important covariate
    most_important_idx = importance_df.iloc[0].name
    most_important_feature = feature_names[most_important_idx]

    axes[1, 1].scatter(X_test[:, most_important_idx], tau_test,
                      alpha=0.5, c=tau_test, cmap='RdYlBu_r', s=20)
    axes[1, 1].set_xlabel(f'{most_important_feature}', fontsize=12)
    axes[1, 1].set_ylabel('Individual Treatment Effect', fontsize=12)
    axes[1, 1].set_title(f'ITE vs. {most_important_feature}', fontsize=14, fontweight='bold')
    axes[1, 1].grid(alpha=0.3)

    # Add colorbar
    scatter = axes[1, 1].scatter(X_test[:, most_important_idx], tau_test,
                                 alpha=0.5, c=tau_test, cmap='RdYlBu_r', s=20)
    plt.colorbar(scatter, ax=axes[1, 1], label='ITE')

    plt.tight_layout()
    plt.savefig('causal_forest_analysis.png', dpi=300, bbox_inches='tight')
    print("✓ Saved visualization to 'causal_forest_analysis.png'")

    # 8. Summary Results Table
    print(f"\n{'='*80}")
    print("SUMMARY RESULTS")
    print(f"{'='*80}")

    results_summary = pd.DataFrame({
        'Metric': [
            'Sample Size (Total)',
            'Sample Size (Training)',
            'Sample Size (Calibration)',
            'Sample Size (Test)',
            'Average Treatment Effect (ATE)',
            'Treatment Effect Heterogeneity (Std)',
            'Min ITE',
            'Max ITE',
            'Mean Prediction Interval Width',
            'Coverage Level',
            'Number of Trees',
            'Top Effect Modifier'
        ],
        'Value': [
            len(X),
            len(X_train),
            len(X_cal),
            len(X_test),
            f"{tau_test.mean():.3f}",
            f"{tau_test.std():.3f}",
            f"{tau_test.min():.3f}",
            f"{tau_test.max():.3f}",
            f"{interval_width.mean():.3f}",
            f"{100*(1-cp.alpha):.0f}%",
            cf_model.n_estimators,
            importance_df.iloc[0]['Feature']
        ]
    })

    print("\n" + results_summary.to_string(index=False))

    # Save results to CSV
    results_summary.to_csv('causal_forest_summary.csv', index=False)
    importance_df.to_csv('effect_modifier_importance.csv', index=False)

    # Save ITE predictions
    ite_results = pd.DataFrame({
        'ITE_Point_Estimate': point,
        'ITE_Lower_90': lower,
        'ITE_Upper_90': upper,
        'Interval_Width': interval_width
    })
    ite_results.to_csv('individual_treatment_effects.csv', index=False)

    print(f"\n✓ Results saved to:")
    print("  - causal_forest_summary.csv")
    print("  - effect_modifier_importance.csv")
    print("  - individual_treatment_effects.csv")

    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}\n")

    return cf_model, cp, results_summary, importance_df


if __name__ == "__main__":
    # Run the complete analysis
    model, conformal_predictor, summary, importances = run_causal_forest_analysis()

    print("\n" + "="*80)
    print("METHODOLOGICAL NOTES")
    print("="*80)
    print("""
    This implementation includes:

    1. CAUSAL FOREST (Wager & Athey, 2018):
       - Honest random forests for unbiased ITE estimation
       - Separate forests for treated and control groups
       - Treatment effect = E[Y(1)|X] - E[Y(0)|X]

    2. CONFORMAL PREDICTION (Alaa, 2023):
       - Distribution-free prediction intervals
       - Valid finite-sample coverage guarantees
       - No parametric assumptions required

    3. VARIABLE IMPORTANCE:
       - Identifies effect modifiers (not just prognostic factors)
       - Measures heterogeneity in treatment effects
       - Guides personalized treatment decisions

    4. META-ANALYSIS READY:
       - Works with Individual Patient Data (IPD)
       - Can be extended to multiple studies
       - Combines causal inference with ML
    """)
