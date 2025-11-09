# Backtest Performance Evaluation Report

**Signal:** `cdx_vix_gap`  
**Strategy:** `conservative`  
**Evaluation Date:** 2025-11-09T15:31:23.660974  
**Evaluator Version:** 0.1.6

---

## Executive Summary

### Stability Assessment: ✅ Strong

**Overall Stability Score:** 0.750

Overall: Strong and stable performance (stability score: 0.75)
Profitability: Strong (profit factor 1.54)
Risk profile: Favorable asymmetry (tail ratio 1.49)
Temporal consistency: 3/4 profitable periods (48.4% positive windows)
Balanced directional exposure (long: 36.0%)

---

## Extended Performance Metrics

### Risk-Adjusted Returns

| Metric | Value |
|--------|-------|
| Rolling Sharpe (Mean) | 1.296 |
| Rolling Sharpe (Std Dev) | 3.339 |
| Profit Factor | 1.537 |
| Tail Ratio (95th pct) | 1.493 |
| Consistency Score (21d) | 48.4% |

**Interpretation:**

- Strong profitability with gross wins substantially exceeding gross losses
- Favorable tail asymmetry with larger upside than downside extremes
- Moderate consistency with mixed profitable/unprofitable periods

### Drawdown Recovery

| Metric | Value |
|--------|-------|
| Max Drawdown Recovery | Not recovered |
| Average Recovery Time | 6.1 days |
| Number of Drawdowns | 32 |

**Warning:** Maximum drawdown has not been recovered as of backtest end date.

---

## Subperiod Stability Analysis

**Number of Subperiods:** 4  
**Profitable Periods:** 3/4  
**Consistency Rate:** 75.0%

| Period | Return | Sharpe |
|--------|--------|--------|
| 1 | 2,381,809.68 | 1.156 |
| 2 | 13,124,230.65 | 4.292 |
| 3 | 391,520.04 | 0.192 |
| 4 | -4,866,808.62 | -1.711 |

**Interpretation:**

Excellent temporal consistency with strong performance across most subperiods. Strategy appears robust to different market conditions.

---

## Return Attribution

### Directional Attribution

| Direction | P&L | Contribution |
|-----------|-----|--------------|
| Long | -1,982,803.42 | 36.0% |
| Short | -3,530,916.34 | 64.0% |

**Balanced exposure** - Returns distributed across both long and short positions.

### Signal Strength Attribution

| Quantile | P&L | Contribution |
|----------|-----|--------------|\n| Q1 | 8,876,938.63 | -161.0% |
| Q2 | -3,804,777.39 | 69.0% |
| Q3 | -10,585,881.00 | 192.0% |

**Strong signal strength relationship** - Highest conviction signals contributed most to returns (192.0%).

### Win/Loss Decomposition

| Category | Amount | Contribution |
|----------|--------|--------------|
| Gross Wins | 14,426,588.02 | 261.6% |
| Gross Losses | -19,940,307.78 | 361.6% |
| Net P&L | -5,513,719.76 | — |

---

## Recommendations

⚠️ **Unrecovered drawdown** - Current strategy underwater; reassess viability


---

## Report Metadata

**Generated:** 2025-11-09T15:31:23.986957  
**Evaluator:** aponyx.evaluation.performance  
**Configuration:**
- Minimum Observations: 252
- Subperiods: 4
- Rolling Window: 63 days
- Attribution Quantiles: 3

**Reproducibility:** All metrics computed from backtest P&L with deterministic methods.

---

*This report was auto-generated from performance evaluation results.*
