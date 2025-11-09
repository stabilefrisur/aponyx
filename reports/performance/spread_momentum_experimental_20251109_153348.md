# Backtest Performance Evaluation Report

**Signal:** `spread_momentum`  
**Strategy:** `experimental`  
**Evaluation Date:** 2025-11-09T15:33:48.327132  
**Evaluator Version:** 0.1.6

---

## Executive Summary

### Stability Assessment: ❌ Weak

**Overall Stability Score:** 0.250

Overall: Inconsistent performance requiring review (stability score: 0.25)
Profitability: Weak (profit factor 0.64)
Risk profile: Negative skew (tail ratio 0.79)
Temporal consistency: 1/4 profitable periods (41.5% positive windows)
Strong long directional bias (84.9%)

---

## Extended Performance Metrics

### Risk-Adjusted Returns

| Metric | Value |
|--------|-------|
| Rolling Sharpe (Mean) | -2.922 |
| Rolling Sharpe (Std Dev) | 7.273 |
| Profit Factor | 0.643 |
| Tail Ratio (95th pct) | 0.788 |
| Consistency Score (21d) | 41.5% |

**Interpretation:**

- Weak profitability with gross losses approaching or exceeding gross wins
- Negative tail asymmetry with larger downside than upside extremes
- Moderate consistency with mixed profitable/unprofitable periods

### Drawdown Recovery

| Metric | Value |
|--------|-------|
| Max Drawdown Recovery | Not recovered |
| Average Recovery Time | 7.0 days |
| Number of Drawdowns | 8 |

**Warning:** Maximum drawdown has not been recovered as of backtest end date.

---

## Subperiod Stability Analysis

**Number of Subperiods:** 4  
**Profitable Periods:** 1/4  
**Consistency Rate:** 25.0%

| Period | Return | Sharpe |
|--------|--------|--------|
| 1 | -13,270,888.70 | -1.509 |
| 2 | -68,039,940.48 | -6.777 |
| 3 | -79,385,808.91 | -6.293 |
| 4 | 48,301,592.14 | 4.668 |

**Interpretation:**

Weak temporal consistency with performance concentrated in few subperiods. Strategy may be vulnerable to regime changes or overfitted to specific conditions.

---

## Return Attribution

### Directional Attribution

| Direction | P&L | Contribution |
|-----------|-----|--------------|
| Long | -80,667,503.72 | 84.9% |
| Short | -14,355,581.82 | 15.1% |

**Strong long bias** - Returns highly concentrated in long positions.

### Signal Strength Attribution

| Quantile | P&L | Contribution |
|----------|-----|--------------|\n| Q1 | -45,587,241.45 | 48.0% |
| Q2 | -25,868,344.05 | 27.2% |
| Q3 | -23,567,500.05 | 24.8% |

**Moderate signal strength relationship** - Mixed contribution across signal strengths.

### Win/Loss Decomposition

| Category | Amount | Contribution |
|----------|--------|--------------|
| Gross Wins | 197,365,458.04 | 207.7% |
| Gross Losses | -292,388,543.59 | 307.7% |
| Net P&L | -95,023,085.54 | — |

---

## Recommendations

⚠️ **Low stability score** - Review strategy robustness and consider regime filters

❌ **Negative profit factor** - Strategy is unprofitable; do not deploy

⚠️ **Low consistency** - Performance concentrated in few periods; assess regime dependency

⚠️ **Unrecovered drawdown** - Current strategy underwater; reassess viability

⚠️ **Negative skew** - Downside risk exceeds upside potential; review risk controls


---

## Report Metadata

**Generated:** 2025-11-09T15:33:48.663859  
**Evaluator:** aponyx.evaluation.performance  
**Configuration:**
- Minimum Observations: 252
- Subperiods: 4
- Rolling Window: 63 days
- Attribution Quantiles: 3

**Reproducibility:** All metrics computed from backtest P&L with deterministic methods.

---

*This report was auto-generated from performance evaluation results.*
