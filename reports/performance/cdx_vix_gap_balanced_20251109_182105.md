# Backtest Performance Evaluation Report

**Signal:** `cdx_vix_gap`  
**Strategy:** `balanced`  
**Evaluation Date:** 2025-11-09T18:21:05.251854  
**Evaluator Version:** 0.1.6

---

## Executive Summary

### Stability Assessment: ❌ Weak

**Overall Stability Score:** 0.000

Overall: Inconsistent performance requiring review (stability score: 0.00)
Profitability: Weak (profit factor 0.49)
Risk profile: Negative skew (tail ratio 0.52)
Temporal consistency: 0/4 profitable periods (46.0% positive windows)
Balanced directional exposure (long: 54.0%)

---

## Extended Performance Metrics

### Risk-Adjusted Returns

| Metric | Value |
|--------|-------|
| Rolling Sharpe (Mean) | -1.498 |
| Rolling Sharpe (Std Dev) | 4.807 |
| Profit Factor | 0.488 |
| Tail Ratio (95th pct) | 0.524 |
| Consistency Score (21d) | 46.0% |

**Interpretation:**

- Weak profitability with gross losses approaching or exceeding gross wins
- Negative tail asymmetry with larger downside than upside extremes
- Moderate consistency with mixed profitable/unprofitable periods

### Drawdown Recovery

| Metric | Value |
|--------|-------|
| Max Drawdown Recovery | Not recovered |
| Average Recovery Time | 1.0 days |
| Number of Drawdowns | 2 |

**Warning:** Maximum drawdown has not been recovered as of backtest end date.

---

## Subperiod Stability Analysis

**Number of Subperiods:** 4  
**Profitable Periods:** 0/4  
**Consistency Rate:** 0.0%

| Period | Return | Sharpe |
|--------|--------|--------|
| 1 | -5,484,451.64 | -1.570 |
| 2 | -2,615,074.15 | -0.511 |
| 3 | -25,090,958.12 | -4.193 |
| 4 | -18,576,095.84 | -3.922 |

**Interpretation:**

Weak temporal consistency with performance concentrated in few subperiods. Strategy may be vulnerable to regime changes or overfitted to specific conditions.

---

## Return Attribution

### Directional Attribution

| Direction | P&L | Contribution |
|-----------|-----|--------------|
| Long | -38,542,348.22 | 54.0% |
| Short | -32,852,411.34 | 46.0% |

**Balanced exposure** - Returns distributed across both long and short positions.

### Signal Strength Attribution

| Quantile | P&L | Contribution |
|----------|-----|--------------|\n| Q1 | -12,465,068.57 | 17.5% |
| Q2 | -14,751,308.82 | 20.7% |
| Q3 | -44,178,382.16 | 61.9% |

**Strong signal strength relationship** - Highest conviction signals contributed most to returns (61.9%).

### Win/Loss Decomposition

| Category | Amount | Contribution |
|----------|--------|--------------|
| Gross Wins | 25,135,317.76 | 35.2% |
| Gross Losses | -96,530,077.31 | 135.2% |
| Net P&L | -71,394,759.55 | — |

---

## Recommendations

⚠️ **Low stability score** - Review strategy robustness and consider regime filters

❌ **Negative profit factor** - Strategy is unprofitable; do not deploy

⚠️ **Low consistency** - Performance concentrated in few periods; assess regime dependency

⚠️ **Unrecovered drawdown** - Current strategy underwater; reassess viability

⚠️ **Negative skew** - Downside risk exceeds upside potential; review risk controls


---

## Report Metadata

**Generated:** 2025-11-09T18:21:05.574982  
**Evaluator:** aponyx.evaluation.performance  
**Configuration:**
- Minimum Observations: 252
- Subperiods: 4
- Rolling Window: 63 days
- Attribution Quantiles: 3

**Reproducibility:** All metrics computed from backtest P&L with deterministic methods.

---

*This report was auto-generated from performance evaluation results.*
