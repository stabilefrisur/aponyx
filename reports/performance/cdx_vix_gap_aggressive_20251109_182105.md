# Backtest Performance Evaluation Report

**Signal:** `cdx_vix_gap`  
**Strategy:** `aggressive`  
**Evaluation Date:** 2025-11-09T18:21:05.271994  
**Evaluator Version:** 0.1.6

---

## Executive Summary

### Stability Assessment: ⚠️ Moderate

**Overall Stability Score:** 0.500

Overall: Moderate performance with acceptable stability (stability score: 0.50)
Profitability: Weak (profit factor 0.60)
Risk profile: Negative skew (tail ratio 0.73)
Temporal consistency: 2/4 profitable periods (39.0% positive windows)
Balanced directional exposure (long: 34.9%)

---

## Extended Performance Metrics

### Risk-Adjusted Returns

| Metric | Value |
|--------|-------|
| Rolling Sharpe (Mean) | -2.481 |
| Rolling Sharpe (Std Dev) | 5.800 |
| Profit Factor | 0.604 |
| Tail Ratio (95th pct) | 0.730 |
| Consistency Score (21d) | 39.0% |

**Interpretation:**

- Weak profitability with gross losses approaching or exceeding gross wins
- Negative tail asymmetry with larger downside than upside extremes
- Low consistency with frequent unprofitable rolling windows

### Drawdown Recovery

| Metric | Value |
|--------|-------|
| Max Drawdown Recovery | Not recovered |
| Average Recovery Time | 41.8 days |
| Number of Drawdowns | 9 |

**Warning:** Maximum drawdown has not been recovered as of backtest end date.

---

## Subperiod Stability Analysis

**Number of Subperiods:** 4  
**Profitable Periods:** 2/4  
**Consistency Rate:** 50.0%

| Period | Return | Sharpe |
|--------|--------|--------|
| 1 | 5,158,134.56 | 0.764 |
| 2 | 8,295,057.42 | 1.013 |
| 3 | -57,442,827.09 | -7.870 |
| 4 | -26,655,085.30 | -3.876 |

**Interpretation:**

Moderate temporal consistency with mixed performance across subperiods. Performance may be regime-dependent.

---

## Return Attribution

### Directional Attribution

| Direction | P&L | Contribution |
|-----------|-----|--------------|
| Long | -32,437,867.78 | 34.9% |
| Short | -60,499,634.96 | 65.1% |

**Balanced exposure** - Returns distributed across both long and short positions.

### Signal Strength Attribution

| Quantile | P&L | Contribution |
|----------|-----|--------------|\n| Q1 | 5,188,920.30 | -5.6% |
| Q2 | -33,865,148.10 | 36.4% |
| Q3 | -64,261,274.94 | 69.1% |

**Strong signal strength relationship** - Highest conviction signals contributed most to returns (69.1%).

### Win/Loss Decomposition

| Category | Amount | Contribution |
|----------|--------|--------------|
| Gross Wins | 76,949,727.96 | 82.8% |
| Gross Losses | -169,887,230.70 | 182.8% |
| Net P&L | -92,937,502.74 | — |

---

## Recommendations

❌ **Negative profit factor** - Strategy is unprofitable; do not deploy

⚠️ **Unrecovered drawdown** - Current strategy underwater; reassess viability

⚠️ **Negative skew** - Downside risk exceeds upside potential; review risk controls


---

## Report Metadata

**Generated:** 2025-11-09T18:21:05.575986  
**Evaluator:** aponyx.evaluation.performance  
**Configuration:**
- Minimum Observations: 252
- Subperiods: 4
- Rolling Window: 63 days
- Attribution Quantiles: 3

**Reproducibility:** All metrics computed from backtest P&L with deterministic methods.

---

*This report was auto-generated from performance evaluation results.*
