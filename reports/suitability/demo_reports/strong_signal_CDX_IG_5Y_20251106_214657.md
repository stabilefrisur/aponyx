# Signal-Product Suitability Evaluation Report

**Signal:** `strong_signal`  
**Product:** `CDX_IG_5Y`  
**Evaluation Date:** 2025-11-06T21:46:57.874726  
**Evaluator Version:** 0.1.0

---

## Executive Summary

### Overall Decision: ✅ PASS

**Composite Score:** 0.920

The signal demonstrates strong predictive content with good data quality. Proceed to strategy design and backtesting.

---

## Component Analysis

### 1. Data Health Score: 1.000

**Metrics:**
- Valid Observations: 600
- Missing Data: 0.00%

**Interpretation:**  
Excellent data quality with sufficient observations and minimal missing data. Sample size supports reliable statistical inference.

---

### 2. Predictive Association Score: 1.000

**Metrics:**

| Lag | Correlation | Beta | T-Statistic |
|-----|-------------|------|-------------|
| 0 | 0.9558 | 1.9978 | 79.5181 |

**Interpretation:**  
Strong statistical evidence of predictive relationship. T-statistics exceed conventional significance thresholds with high confidence.

---

### 3. Economic Relevance Score: 0.600

**Metrics:**
- Effect Size: 1.942 bps per 1σ signal change

**Interpretation:**  
Moderate economic impact. Effect size is detectable but may be marginal after transaction costs. Careful strategy design required.

---

### 4. Temporal Stability Score: 1.000

**Metrics:**
- Subperiod Betas: 2.0111, 1.9838
- Sign Consistent: Yes

**Interpretation:**  
Excellent temporal stability. Predictive relationship maintains consistent sign across subperiods, indicating robustness across different market regimes.

---

## Composite Scoring

| Component | Weight | Score | Contribution |
|-----------|--------|-------|--------------|
| Data Health | 0.20 | 1.000 | 0.200 |
| Predictive | 0.40 | 1.000 | 0.400 |
| Economic | 0.20 | 0.600 | 0.120 |
| Stability | 0.20 | 1.000 | 0.200 |
| **Total** | **1.00** | — | **0.920** |

---

## Decision Criteria

- **PASS** (≥ 0.70): Proceed to backtest
- **HOLD** (0.40 - 0.70): Marginal, requires judgment
- **FAIL** (< 0.40): Do not backtest

### Recommended Next Steps

1. Design trading strategy with entry/exit rules
2. Configure backtest parameters (position sizing, costs)
3. Run historical backtest with proper risk controls
4. Analyze performance metrics and risk-adjusted returns

---

## Report Metadata

**Generated:** 2025-11-06T21:46:57.877744  
**Evaluator:** aponyx.evaluation.suitability v0.1.0  
**Reproducibility:** All metrics computed from aligned signal-target pairs with deterministic methods.

---

*This report was auto-generated from suitability evaluation results. For questions about methodology, see `docs/suitability_evaluation.md`.*
