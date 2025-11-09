# Backtest Performance Evaluation Report

**Signal:** `spread_momentum`  
**Strategy:** `balanced`  
**Evaluation Date:** 2025-11-09T15:31:23.760537  
**Evaluator Version:** 0.1.6

---

## Executive Summary

### Stability Assessment: ❌ Weak

**Overall Stability Score:** 0.250

Overall: Inconsistent performance requiring review (stability score: 0.25)
Profitability: Weak (profit factor 0.75)
Risk profile: Negative skew (tail ratio 0.69)
Temporal consistency: 1/4 profitable periods (46.6% positive windows)
Balanced directional exposure (long: 40.2%)

---

## Extended Performance Metrics

### Risk-Adjusted Returns

| Metric | Value |
|--------|-------|
| Rolling Sharpe (Mean) | -1.063 |
| Rolling Sharpe (Std Dev) | 7.498 |
| Profit Factor | 0.750 |
| Tail Ratio (95th pct) | 0.688 |
| Consistency Score (21d) | 46.6% |

**Interpretation:**

- Weak profitability with gross losses approaching or exceeding gross wins
- Negative tail asymmetry with larger downside than upside extremes
- Moderate consistency with mixed profitable/unprofitable periods

### Drawdown Recovery

| Metric | Value |
|--------|-------|
| Max Drawdown Recovery | Not recovered |
| Average Recovery Time | 17.4 days |
| Number of Drawdowns | 10 |

**Warning:** Maximum drawdown has not been recovered as of backtest end date.

---

## Subperiod Stability Analysis

**Number of Subperiods:** 4  
**Profitable Periods:** 1/4  
**Consistency Rate:** 25.0%

| Period | Return | Sharpe |
|--------|--------|--------|
| 1 | -5,624,961.76 | -0.660 |
| 2 | -57,055,493.17 | -6.660 |
| 3 | -16,983,392.23 | -1.645 |
| 4 | 29,588,809.06 | 3.648 |

**Interpretation:**

Weak temporal consistency with performance concentrated in few subperiods. Strategy may be vulnerable to regime changes or overfitted to specific conditions.

---

## Return Attribution

### Directional Attribution

| Direction | P&L | Contribution |
|-----------|-----|--------------|
| Long | -10,535,882.91 | 40.2% |
| Short | -15,699,391.12 | 59.8% |

**Balanced exposure** - Returns distributed across both long and short positions.

### Signal Strength Attribution

| Quantile | P&L | Contribution |
|----------|-----|--------------|\n| Q1 | -45,572,461.61 | 173.7% |
| Q2 | -31,675,012.16 | 120.7% |
| Q3 | 51,012,199.74 | -194.4% |

**Weak signal strength relationship** - Returns not concentrated in highest conviction signals. Signal strength may not add value.

### Win/Loss Decomposition

| Category | Amount | Contribution |
|----------|--------|--------------|
| Gross Wins | 146,043,562.12 | 556.7% |
| Gross Losses | -172,278,836.15 | 656.7% |
| Net P&L | -26,235,274.03 | — |

---

## Recommendations

⚠️ **Low stability score** - Review strategy robustness and consider regime filters

❌ **Negative profit factor** - Strategy is unprofitable; do not deploy

⚠️ **Low consistency** - Performance concentrated in few periods; assess regime dependency

⚠️ **Unrecovered drawdown** - Current strategy underwater; reassess viability

⚠️ **Negative skew** - Downside risk exceeds upside potential; review risk controls


---

## Report Metadata

**Generated:** 2025-11-09T15:31:23.996893  
**Evaluator:** aponyx.evaluation.performance  
**Configuration:**
- Minimum Observations: 252
- Subperiods: 4
- Rolling Window: 63 days
- Attribution Quantiles: 3

**Reproducibility:** All metrics computed from backtest P&L with deterministic methods.

---

*This report was auto-generated from performance evaluation results.*
