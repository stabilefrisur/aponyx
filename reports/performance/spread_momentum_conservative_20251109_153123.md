# Backtest Performance Evaluation Report

**Signal:** `spread_momentum`  
**Strategy:** `conservative`  
**Evaluation Date:** 2025-11-09T15:31:23.742090  
**Evaluator Version:** 0.1.6

---

## Executive Summary

### Stability Assessment: ✅ Strong

**Overall Stability Score:** 0.750

Overall: Strong and stable performance (stability score: 0.75)
Profitability: Positive (profit factor 1.16)
Risk profile: Balanced (tail ratio 1.09)
Temporal consistency: 3/4 profitable periods (47.5% positive windows)
Balanced directional exposure (long: 39.1%)

---

## Extended Performance Metrics

### Risk-Adjusted Returns

| Metric | Value |
|--------|-------|
| Rolling Sharpe (Mean) | 0.232 |
| Rolling Sharpe (Std Dev) | 5.126 |
| Profit Factor | 1.165 |
| Tail Ratio (95th pct) | 1.088 |
| Consistency Score (21d) | 47.5% |

**Interpretation:**

- Positive profitability with gross wins exceeding gross losses
- Balanced tail distribution with similar upside and downside extremes
- Moderate consistency with mixed profitable/unprofitable periods

### Drawdown Recovery

| Metric | Value |
|--------|-------|
| Max Drawdown Recovery | 558 days |
| Average Recovery Time | 92.9 days |
| Number of Drawdowns | 13 |


---

## Subperiod Stability Analysis

**Number of Subperiods:** 4  
**Profitable Periods:** 3/4  
**Consistency Rate:** 75.0%

| Period | Return | Sharpe |
|--------|--------|--------|
| 1 | 12,745,230.79 | 2.197 |
| 2 | -18,148,457.55 | -3.508 |
| 3 | 56,360.55 | 0.007 |
| 4 | 22,565,490.43 | 3.448 |

**Interpretation:**

Excellent temporal consistency with strong performance across most subperiods. Strategy appears robust to different market conditions.

---

## Return Attribution

### Directional Attribution

| Direction | P&L | Contribution |
|-----------|-----|--------------|
| Long | 17,659,762.81 | 39.1% |
| Short | 27,541,969.74 | 60.9% |

**Balanced exposure** - Returns distributed across both long and short positions.

### Signal Strength Attribution

| Quantile | P&L | Contribution |
|----------|-----|--------------|\n| Q1 | -11,259,071.52 | -24.9% |
| Q2 | 5,157,526.72 | 11.4% |
| Q3 | 51,303,277.35 | 113.5% |

**Strong signal strength relationship** - Highest conviction signals contributed most to returns (113.5%).

### Win/Loss Decomposition

| Category | Amount | Contribution |
|----------|--------|--------------|
| Gross Wins | 117,891,778.52 | 260.8% |
| Gross Losses | -72,690,045.97 | 160.8% |
| Net P&L | 45,201,732.55 | — |

---

## Recommendations

✅ **Performance acceptable** - Consider proceeding with further validation and stress testing

Next steps: comparative analysis against alternative signals/strategies

Recommended: transaction cost sensitivity analysis and regime-conditional performance review


---

## Report Metadata

**Generated:** 2025-11-09T15:31:23.993902  
**Evaluator:** aponyx.evaluation.performance  
**Configuration:**
- Minimum Observations: 252
- Subperiods: 4
- Rolling Window: 63 days
- Attribution Quantiles: 3

**Reproducibility:** All metrics computed from backtest P&L with deterministic methods.

---

*This report was auto-generated from performance evaluation results.*
