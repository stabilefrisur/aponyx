# Signal-Product Suitability Evaluation Report

**Signal:** `cdx_etf_basis`  
**Product:** `CDX_IG_5Y`  
**Evaluation Date:** 2025-11-07T22:49:21.788937  
**Evaluator Version:** 0.1.0

---

## Executive Summary

### Overall Decision: ✅ PASS

**Composite Score:** 0.964

The signal demonstrates strong predictive content with good data quality. Proceed to strategy design and backtesting.

---

## Component Analysis

### 1. Data Health Score: 0.821

**Metrics:**
- Valid Observations: 243
- Missing Data: 3.57%

**Interpretation:**  
Excellent data quality with sufficient observations and minimal missing data. Sample size supports reliable statistical inference.

---

### 2. Predictive Association Score: 1.000

**Metrics:**

| Lag | Correlation | Beta | T-Statistic |
|-----|-------------|------|-------------|
| 1 | 0.6046 | 2.8817 | 11.7577 |
| 3 | 0.3902 | 1.8595 | 6.5387 |
| 5 | 0.2916 | 1.3919 | 4.6837 |

**Interpretation:**  
Strong statistical evidence of predictive relationship. T-statistics exceed conventional significance thresholds with high confidence.

---

### 3. Economic Relevance Score: 1.000

**Metrics:**
- Effect Size: 2.416 bps per 1σ signal change

**Interpretation:**  
Economically meaningful effect size. A 1σ signal move is associated with substantial spread changes that could generate attractive risk-adjusted returns after costs.

---

### 4. Temporal Stability Score: 1.000

**Metrics:**
- Subperiod Betas: 2.5636, 4.0969
- Sign Consistent: Yes

**Interpretation:**  
Excellent temporal stability. Predictive relationship maintains consistent sign across subperiods, indicating robustness across different market regimes.

---

## Composite Scoring

| Component | Weight | Score | Contribution |
|-----------|--------|-------|--------------|
| Data Health | 0.20 | 0.821 | 0.164 |
| Predictive | 0.40 | 1.000 | 0.400 |
| Economic | 0.20 | 1.000 | 0.200 |
| Stability | 0.20 | 1.000 | 0.200 |
| **Total** | **1.00** | — | **0.964** |

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

**Generated:** 2025-11-07T22:49:21.790943  
**Evaluator:** aponyx.evaluation.suitability v0.1.0  
**Reproducibility:** All metrics computed from aligned signal-target pairs with deterministic methods.

---

*This report was auto-generated from suitability evaluation results. For questions about methodology, see `docs/suitability_evaluation.md`.*
