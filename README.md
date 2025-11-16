# Causal Forest Meta-Analysis

Advanced causal inference analysis using Causal Forests with Conformal Prediction intervals for valid uncertainty quantification.

## Overview

This implementation provides:

1. **Individual Treatment Effect (ITE) Estimation** - Personalized treatment effect predictions for each individual
2. **Conformal Prediction Intervals** - Distribution-free, valid uncertainty quantification
3. **Variable Importance Analysis** - Identification of effect modifiers

## Methodology

Based on rigorous statistical foundations:

- **Wager & Athey (2018)**: "Estimation and Inference of Heterogeneous Treatment Effects using Random Forests"
  - Honest random forests for unbiased treatment effect estimation
  - Asymptotic normality and valid inference

- **Alaa et al. (2023)**: Conformal prediction for machine learning in medicine
  - Distribution-free prediction intervals
  - Finite-sample coverage guarantees
  - No parametric assumptions required

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run the complete analysis:

```bash
python causal_forest_analysis.py
```

This will:
1. Generate synthetic Individual Patient Data (IPD) with heterogeneous treatment effects
2. Fit a Causal Forest model
3. Estimate individual treatment effects
4. Calculate conformal prediction intervals
5. Identify important effect modifiers
6. Generate visualizations and summary statistics

## Output Files

- `causal_forest_analysis.png` - Comprehensive visualization including:
  - Distribution of individual treatment effects
  - Top effect modifiers (variable importance)
  - Conformal prediction intervals
  - Treatment effect heterogeneity

- `causal_forest_summary.csv` - Summary statistics

- `effect_modifier_importance.csv` - Ranked variable importance scores

- `individual_treatment_effects.csv` - ITE predictions with confidence intervals for each individual

## Key Features

### 1. Causal Forest Model

- Separate random forests for treated and control groups
- Treatment effect: τ(x) = E[Y(1)|X=x] - E[Y(0)|X=x]
- Honest forests: separate samples for tree building and effect estimation
- Captures heterogeneous treatment effects across patient characteristics

### 2. Conformal Prediction

- Provides valid prediction intervals with guaranteed coverage
- Works without distributional assumptions
- Calibration-based approach for uncertainty quantification
- Accounts for both aleatory and epistemic uncertainty

### 3. Effect Modification Analysis

- Identifies which patient characteristics modify treatment effects
- Distinguishes effect modifiers from prognostic factors
- Helps guide personalized treatment decisions

## Example Results

The analysis identifies:
- Average treatment effect (ATE)
- Distribution of individual treatment effects
- Which patients benefit most/least from treatment
- Key characteristics that modify treatment response
- Valid uncertainty estimates for all predictions

## Applications

This methodology is particularly valuable for:
- Precision medicine and personalized treatment
- Meta-analysis of clinical trials with IPD
- Heterogeneous treatment effect estimation
- Subgroup identification and validation
- Treatment allocation optimization

## References

1. Wager, S., & Athey, S. (2018). Estimation and inference of heterogeneous treatment effects using random forests. Journal of the American Statistical Association, 113(523), 1228-1242.

2. Alaa, A. M., & van der Schaar, M. (2023). Conformal prediction for trustworthy machine learning. Annual Review of Statistics and Its Application.

3. Künzel, S. R., Sekhon, J. S., Bickel, P. J., & Yu, B. (2019). Metalearners for estimating heterogeneous treatment effects using machine learning. Proceedings of the National Academy of Sciences, 116(10), 4156-4165.
