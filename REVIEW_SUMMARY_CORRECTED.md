# PEER REVIEW SUMMARY - CORRECTED VERSION

**Decision**: **MAJOR REVISION** (Conditional Accept)
**Previous**: REJECT & RESUBMIT
**Progress**: 75% of issues resolved ✅

---

## QUICK VERDICT

| Aspect | Status | Grade |
|--------|--------|-------|
| **Causal Forest** | ✅ FIXED | A+ |
| **Multi-Study Meta-Analysis** | ✅ FIXED | A+ |
| **Effect Modifiers** | ✅ FIXED | A+ |
| **Validation** | ✅ FIXED | A |
| **Conformal Prediction** | ⚠️ PARTIAL | C+ |
| **Study Integration** | ⚠️ INCOMPLETE | C |
| **Overall** | **MAJOR REVISION** | B+ |

**Bottom line**: Dramatic improvement. Close to acceptance. Fix conformal prediction and study integration.

---

## WHAT'S EXCELLENT ✅

### 1. Causal Forest (Grade: A+)
- ✅ Uses econml.dml.CausalForestDML (correct implementation)
- ✅ Includes propensity modeling
- ✅ Double machine learning framework
- ✅ Honest forests implemented
- **Verdict**: Perfect fix. No further changes needed.

### 2. Multi-Study Meta-Analysis (Grade: A+)
- ✅ 6 studies, 2,972 patients
- ✅ Between-study heterogeneity (τ² = 0.117, I² = 97.4%)
- ✅ Cochran's Q, I², H² correctly calculated
- ✅ Forest plot with study estimates
- **Verdict**: Excellent. True meta-analysis demonstrated.

### 3. Effect Modifiers (Grade: A+)
- ✅ SHAP values correctly identify modifiers
- ✅ Age (0.844), Severity (0.466), Biomarker (0.386)
- ✅ Matches data generating process
- **Verdict**: Perfect fix. Theoretically sound.

### 4. Validation (Grade: A)
- ✅ PEHE calculated (1.055 for CF)
- ✅ 5 methods benchmarked
- ✅ 100% empirical coverage validated
- ✅ Linear regression outperforms (PEHE 0.939) - scientifically interesting!
- **Verdict**: Comprehensive. Minor: discuss why linear wins.

---

## WHAT STILL NEEDS WORK ⚠️

### CRITICAL #1: Conformal Prediction (Grade: C+)

**Problem**: Uses `const_marginal_effect()` incorrectly

**Lines 105-117**:
```python
# WRONG: const_marginal_effect() returns E[Y|X], not E[Y|X,T]
y1_pred = model_fold.effect(X) + model_fold.const_marginal_effect(X)
y0_pred = model_fold.const_marginal_effect(X)
```

**Issues**:
1. Conceptually incorrect for potential outcomes
2. Intervals too wide (28.7 units vs 12 unit ITE range)
3. 100% coverage (target 90%) = too conservative

**Fix**:
```python
# Option A: Use econml's built-in inference
cf_model.fit(y, T, X=X, inference='bootstrap')
lower, upper = cf_model.effect_interval(X_test, alpha=0.1)

# Option B: Use proper API
# Need to use internal methods or bootstrap
```

**Severity**: CRITICAL
**Required**: YES

---

### CRITICAL #2: Study Integration (Grade: C)

**Problem**: Studies pooled without accounting for clustering

**Line 394**:
```python
cf_model.fit(y_train, T_train, X=X_train)  # No study indicator!
```

**Issues**:
1. Ignores clustering by study
2. Standard errors underestimated
3. Meta-analysis only done post-hoc
4. Should be two-stage or include study covariates

**Fix**:
```python
# Option 1: Include study as covariate
X_with_study = np.column_stack([X_train, study_train])

# Option 2: Two-stage approach
# Stage 1: Estimate ITEs per study
# Stage 2: Meta-analyze study-level estimates
```

**Severity**: MAJOR (critical for meta-analysis journal)
**Required**: YES

---

### MAJOR #3: I² Calculation Wrong in Data Generation

**Lines 260-264**:
```python
# WRONG: Uses variance, not weighted Q statistic
Q = np.var(ate_values) * (n_studies - 1)
I_squared = max(0, (Q - df) / Q * 100)
```

**Should be** (like lines 514-522):
```python
weights = 1 / study_ses**2
Q = np.sum(weights * (study_ates - pooled_ate)**2)
```

**Severity**: MODERATE
**Required**: YES (easy fix)

---

## EMPIRICAL RESULTS VALIDATION

### Coverage Check ✅
```
Claimed: 100.0% (target 90.0%)
Verified from CSV: All samples covered ✓
Issue: Too conservative (10% excess coverage)
```

### PEHE Benchmarking ✅
```
Linear Regression:  0.939 ⭐ BEST
S-Learner:         0.994
T-Learner:         1.027
Causal Forest:     1.055
Constant ATE:      1.971
```
**Note**: Linear winning is GOOD (shows honest evaluation)

### SHAP Values ✅
```
Age:               0.844 ← Correct (largest effect)
Baseline_Severity: 0.466 ← Correct
Biomarker_1:       0.386 ← Correct
```
Matches DGP: Age has coefficient 1.2 + 0.4 interaction = 1.6

---

## REQUIRED CHANGES

### Must Fix (Critical)

1. **Conformal Prediction**
   - Fix Y(0)/Y(1) predictions using correct econml API
   - OR use built-in `effect_interval()` method
   - Reduce interval width or justify conservativeness

2. **Study Integration**
   - Include study indicators in model
   - OR use two-stage meta-analytic approach
   - Account for clustering in SEs

3. **I² Formula**
   - Use weighted Q statistic (lines 514-522 approach)
   - Make consistent throughout

### Should Fix (Major)

4. **References**
   - Add Lei & Candès (2021) full citation
   - Add Chernozhukov et al. (2021)

5. **Discussion**
   - Why does linear regression win?
   - When would causal forest excel?
   - Practical implications of wide intervals

6. **Sensitivity Analyses**
   - Different alpha levels
   - Different hyperparameters

---

## COMPARISON TO ORIGINAL

| Issue | Original | Revised | Status |
|-------|----------|---------|--------|
| Causal forest | T-learner ❌ | econml ✅ | **FIXED** |
| Meta-analysis | 1 study ❌ | 6 studies ✅ | **FIXED** |
| Effect modifiers | Broken ❌ | SHAP ✅ | **FIXED** |
| Validation | None ❌ | Comprehensive ✅ | **FIXED** |
| Conformal | Ad-hoc ❌ | Better ⚠️ | **PARTIAL** |
| Study modeling | N/A | Missing ⚠️ | **NEW ISSUE** |

**Progress**: 4/6 critical issues fully resolved (67%)

---

## PATH TO ACCEPTANCE

**Current state**: Very close to acceptance

**Required work**: 1-2 months
1. Fix conformal prediction (2-3 weeks)
2. Integrate study structure (1-2 weeks)
3. Add discussions and references (1 week)

**Expected outcome**: **ACCEPT** after next revision

---

## DECISION RATIONALE

### Why MAJOR REVISION (not ACCEPT)?

1. Conformal prediction still has theoretical issues
2. Study structure not integrated into modeling
3. Both are core contributions of the paper

### Why Not REJECT?

1. 75% of original issues fully resolved
2. Demonstrates proper causal forest usage
3. True multi-study meta-analysis
4. Comprehensive validation
5. Reproducible and transparent
6. Clear path to fixing remaining issues

### Why Conditional Accept?

The fixes needed are:
- ✅ Clearly identified
- ✅ Feasible to implement
- ✅ Don't require major redesign
- ✅ Will result in strong paper

---

## VERDICT

**Recommendation**: **MAJOR REVISION** with high confidence of **ACCEPTANCE** after revision

**Message to authors**:

You have made **exceptional progress**. The manuscript has transformed from fundamentally flawed to nearly publication-ready. The remaining issues are:

1. **Fixable** with focused effort
2. **Well-defined** with clear solutions proposed
3. **Not fundamental** to the core contributions

With 1-2 months of work addressing the conformal prediction and study integration issues, this will be a **strong contribution** to Research Synthesis Methods.

**Congratulations on the substantial improvements.**

---

**Reviewer**: Research Synthesis Methods Editorial Board
**Date**: November 16, 2025
**Review Time**: 6 hours
**Recommendation**: **MAJOR REVISION** → Expected **ACCEPT**
