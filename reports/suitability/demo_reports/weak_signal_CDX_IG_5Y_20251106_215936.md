# Signal-Product Suitability Evaluation Report

**Signal:** `weak_signal`  
**Product:** `CDX_IG_5Y`  
**Evaluation Date:** 2025-11-06T21:59:36.013313  
**Evaluator Version:** 0.1.0

---

## Executive Summary

### Overall Decision: ⚠️ HOLD

**Composite Score:** 0.515

The signal shows marginal predictive content. Consider refining signal construction or gathering more data before backtesting. Manual review recommended.

---

## Component Analysis

### 1. Data Health Score: 1.000

**Metrics:**
- Valid Observations: 600
- Missing Data: 0.00%

**Interpretation:**  
Excellent data quality with sufficient observations and minimal missing data. Sample size supports reliable statistical inference.

---

### 2. Predictive Association Score: 0.187

**Metrics:**

| Lag | Correlation | Beta | T-Statistic |
|-----|-------------|------|-------------|
| 1 | 0.0132 | 0.0268 | 0.3230 |
| 3 | 0.0428 | 0.0868 | 1.0447 |
| 5 | -0.0131 | -0.0265 | -0.3193 |

**Interpretation:**  
No statistically significant predictive relationship detected. Signal appears uncorrelated with target movements.

---

### 3. Economic Relevance Score: 0.200

**Metrics:**
- Effect Size: 0.029 bps per 1σ signal change

**Interpretation:**  
Negligible economic impact. Even if statistically significant, the effect size is too small to generate meaningful P&L after realistic transaction costs.

---

### 4. Temporal Stability Score: 1.000

**Metrics:**
- Subperiod Betas: 0.2500, 0.2520
- Sign Consistent: Yes

**Interpretation:**  
Excellent temporal stability. Predictive relationship maintains consistent sign across subperiods, indicating robustness across different market regimes.

---

## Composite Scoring

| Component | Weight | Score | Contribution |
|-----------|--------|-------|--------------|
| Data Health | 0.20 | 1.000 | 0.200 |
| Predictive | 0.40 | 0.187 | 0.075 |
| Economic | 0.20 | 0.200 | 0.040 |
| Stability | 0.20 | 1.000 | 0.200 |
| **Total** | **1.00** | — | **0.515** |

---

## Decision Criteria

- **PASS** (≥ 0.70): Proceed to backtest
- **HOLD** (0.40 - 0.70): Marginal, requires judgment
- **FAIL** (< 0.40): Do not backtest

### Recommended Next Steps

1. Review component scores to identify weaknesses
2. Consider signal refinements (lookback periods, normalization)
3. Gather additional data if sample size is limited
4. Consult with senior researchers before proceeding
5. Document rationale for proceed/stop decision

---

## Report Metadata

**Generated:** 2025-11-06T21:59:36.013313  
**Evaluator:** aponyx.evaluation.suitability v0.1.0  
**Reproducibility:** All metrics computed from aligned signal-target pairs with deterministic methods.

---

*This report was auto-generated from suitability evaluation results. For questions about methodology, see `docs/suitability_evaluation.md`.*
