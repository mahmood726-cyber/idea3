"""
Tests for the canonical causal-forest meta-analysis implementation
(``causal_forest_analysis.py``).

These tests validate the CORE computations against hand-derived / known-property
expectations:

* ITE definition  tau(x) = E[Y(1)|x] - E[Y(0)|x]  (sign + identity consistency)
* ATE recovery on a synthetic dataset with a KNOWN constant treatment effect
* CATE recovery on a dataset with a KNOWN heterogeneous (covariate-driven) effect
* Effect-modifier importance is normalised and points at the true modifier
* Separate treated/control forests (the structural basis of the T-learner CF)
* Split-conformal prediction intervals achieve >= target marginal coverage
* The finite-sample conformal quantile level is clamped to <= 1 (regression test)

Everything imports the pure classes/functions; no plotting or file I/O is
triggered (the heavy ``run_causal_forest_analysis`` driver stays under
``if __name__ == '__main__'`` in the module).
"""

import numpy as np
import pytest

from causal_forest_analysis import (
    CausalForest,
    ConformalPrediction,
    generate_synthetic_ipd,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _make_constant_effect_data(n=4000, true_tau=2.5, seed=0):
    """Randomised trial, linear prognosis, CONSTANT treatment effect."""
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n, 4))
    T = rng.binomial(1, 0.5, n)
    baseline = 1.5 * X[:, 0] + 0.8 * X[:, 1]
    y = baseline + T * true_tau + rng.standard_normal(n) * 0.3
    return X, T, y, true_tau


def _make_heterogeneous_effect_data(n=5000, seed=1):
    """Treatment effect is driven by feature 0 only:  tau(x) = 2 + 3*x0."""
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n, 4))
    T = rng.binomial(1, 0.5, n)
    tau = 2.0 + 3.0 * X[:, 0]            # feature 0 is the ONLY effect modifier
    baseline = 1.0 * X[:, 1]            # feature 1 is purely prognostic
    y = baseline + T * tau + rng.standard_normal(n) * 0.3
    return X, T, y


# --------------------------------------------------------------------------- #
# ITE definition / sign consistency
# --------------------------------------------------------------------------- #
def test_predict_equals_y1_minus_y0():
    """predict() must equal predict_potential_outcomes() difference exactly."""
    X, T, y, _ = _make_constant_effect_data()
    cf = CausalForest(n_estimators=40, min_samples_leaf=20).fit(X, T, y)

    tau = cf.predict(X)
    y0, y1 = cf.predict_potential_outcomes(X)

    assert np.allclose(tau, y1 - y0)
    assert tau.shape == (len(X),)


def test_treatment_effect_sign_positive():
    """A genuinely positive treatment effect must come out positive on average."""
    X, T, y, true_tau = _make_constant_effect_data(true_tau=2.5)
    cf = CausalForest(n_estimators=80, min_samples_leaf=20).fit(X, T, y)
    assert cf.predict(X).mean() > 0


def test_treatment_effect_sign_negative():
    """A genuinely negative treatment effect must come out negative on average."""
    X, T, y, _ = _make_constant_effect_data(true_tau=-2.5)
    cf = CausalForest(n_estimators=80, min_samples_leaf=20).fit(X, T, y)
    assert cf.predict(X).mean() < 0


# --------------------------------------------------------------------------- #
# ATE / CATE recovery on known ground truth
# --------------------------------------------------------------------------- #
def test_recovers_known_constant_ate():
    """Estimated ATE recovers the known constant true effect within tolerance."""
    X, T, y, true_tau = _make_constant_effect_data(n=6000, true_tau=2.5)
    n = len(X)
    X_tr, X_te = X[: n // 2], X[n // 2 :]
    T_tr = T[: n // 2]
    y_tr = y[: n // 2]

    cf = CausalForest(n_estimators=200, min_samples_leaf=25).fit(X_tr, T_tr, y_tr)
    ate_hat = cf.predict(X_te).mean()              # evaluated out-of-sample

    assert abs(ate_hat - true_tau) < 0.4


def test_recovers_heterogeneous_cate_ordering():
    """
    When tau(x) = 2 + 3*x0, individuals with large x0 must have larger
    predicted ITEs than individuals with small x0 (correct CATE ordering),
    and the predicted ITE must correlate strongly with the truth.
    """
    X, T, y = _make_heterogeneous_effect_data(n=6000)
    n = len(X)
    X_tr, X_te = X[: n // 2], X[n // 2 :]
    T_tr, y_tr = T[: n // 2], y[: n // 2]

    cf = CausalForest(n_estimators=200, min_samples_leaf=20).fit(X_tr, T_tr, y_tr)
    tau_hat = cf.predict(X_te)
    tau_true = 2.0 + 3.0 * X_te[:, 0]

    # High-x0 group has a strictly larger mean predicted effect than low-x0.
    hi = X_te[:, 0] > np.quantile(X_te[:, 0], 0.8)
    lo = X_te[:, 0] < np.quantile(X_te[:, 0], 0.2)
    assert tau_hat[hi].mean() > tau_hat[lo].mean()

    # Predicted ITEs track the true heterogeneous effect.
    assert np.corrcoef(tau_hat, tau_true)[0, 1] > 0.7


# --------------------------------------------------------------------------- #
# Effect-modifier importance
# --------------------------------------------------------------------------- #
def test_importance_normalised_and_identifies_modifier():
    """Importances sum to 1 and feature 0 (the true modifier) ranks top."""
    X, T, y = _make_heterogeneous_effect_data(n=6000)
    cf = CausalForest(n_estimators=150, min_samples_leaf=20).fit(X, T, y)

    imp = cf.get_feature_importances()
    assert imp.shape == (X.shape[1],)
    assert np.all(imp >= 0)
    assert abs(imp.sum() - 1.0) < 1e-9          # normalised
    assert int(np.argmax(imp)) == 0             # feature 0 drives the effect


# --------------------------------------------------------------------------- #
# Honest / separate-forest structure
# --------------------------------------------------------------------------- #
def test_separate_treated_and_control_forests():
    """The model fits two distinct forests (basis of the causal-forest design)."""
    X, T, y, _ = _make_constant_effect_data()
    cf = CausalForest(n_estimators=30, min_samples_leaf=20).fit(X, T, y)
    assert cf.treated_forest is not None
    assert cf.control_forest is not None
    assert cf.treated_forest is not cf.control_forest


# --------------------------------------------------------------------------- #
# Conformal prediction intervals
# --------------------------------------------------------------------------- #
def test_conformal_quantile_level_clamped():
    """
    Regression test for the finite-sample conformal quantile.
    For small calibration sets ceil((n+1)(1-alpha))/n can exceed 1, which
    np.quantile rejects; predict_interval must clamp and not raise.
    """
    X, T, y, _ = _make_constant_effect_data(n=400)
    cf = CausalForest(n_estimators=30, min_samples_leaf=20).fit(X, T, y)

    # Tiny calibration set (n=5) -> ceil(6*0.9)/5 = 6/5 = 1.2 before clamping.
    cp = ConformalPrediction(cf, alpha=0.1)
    cp.calibrate(X[:5], T[:5], y[:5])
    lower, upper, point = cp.predict_interval(X[:10])   # must not raise
    assert np.all(upper >= lower)
    assert point.shape == (10,)


def test_conformal_interval_ordering_and_centering():
    """Interval is centred on the point estimate and lower <= point <= upper."""
    X, T, y, _ = _make_constant_effect_data(n=3000)
    n = len(X)
    cf = CausalForest(n_estimators=60, min_samples_leaf=20).fit(
        X[: n // 2], T[: n // 2], y[: n // 2]
    )
    cp = ConformalPrediction(cf, alpha=0.1)
    cp.calibrate(X[n // 2 : 3 * n // 4], T[n // 2 : 3 * n // 4], y[n // 2 : 3 * n // 4])
    lower, upper, point = cp.predict_interval(X[3 * n // 4 :])

    assert np.all(lower <= point + 1e-9)
    assert np.all(point <= upper + 1e-9)
    # Symmetric construction: point is the midpoint.
    assert np.allclose((lower + upper) / 2.0, point)


def test_conformal_outcome_coverage_meets_target():
    """
    Marginal coverage check on the *outcome* scale (where the calibration
    residuals are defined). Split-conformal guarantees >= 1 - alpha coverage
    of Y(t) by Y_hat(t) +/- q on exchangeable held-out data.
    """
    rng = np.random.default_rng(7)
    n = 4000
    X = rng.standard_normal((n, 4))
    T = rng.binomial(1, 0.5, n)
    tau = 2.0
    y = 1.5 * X[:, 0] + T * tau + rng.standard_normal(n) * 0.5

    tr, cal, te = slice(0, 2000), slice(2000, 3000), slice(3000, 4000)
    cf = CausalForest(n_estimators=120, min_samples_leaf=20).fit(X[tr], T[tr], y[tr])
    cp = ConformalPrediction(cf, alpha=0.1)
    cp.calibrate(X[cal], T[cal], y[cal])

    # Treatment-arm prediction interval for the realised outcome.
    X_te, T_te, y_te = X[te], T[te], y[te]
    treated = T_te == 1
    lower, upper, _ = cp.predict_interval(X_te[treated], treatment=1)
    covered = np.mean((y_te[treated] >= lower) & (y_te[treated] <= upper))

    # Target 90%; allow Monte-Carlo slack but require it to be valid (>= ~87%).
    assert covered >= 0.87


# --------------------------------------------------------------------------- #
# Data generator sanity
# --------------------------------------------------------------------------- #
def test_generate_synthetic_ipd_shapes():
    X, T, y, names = generate_synthetic_ipd(n_samples=500, n_features=6)
    assert X.shape == (500, 6)
    assert T.shape == (500,)
    assert y.shape == (500,)
    assert set(np.unique(T)).issubset({0, 1})
    assert len(names) == 6
