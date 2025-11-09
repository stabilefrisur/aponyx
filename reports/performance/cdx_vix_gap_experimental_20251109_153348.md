# Backtest Performance Evaluation Report

**Signal:** `cdx_vix_gap`  
**Strategy:** `experimental`  
**Evaluation Date:** 2025-11-09T15:33:48.258391  
**Evaluator Version:** 0.1.6

---

## Executive Summary

### Stability Assessment: ⚠️ Moderate

**Overall Stability Score:** 0.500

Overall: Moderate performance with acceptable stability (stability score: 0.50)
Profitability: Weak (profit factor 0.81)
Risk profile: Balanced (tail ratio 0.94)
Temporal consistency: 2/4 profitable periods (44.3% positive windows)
Balanced directional exposure (long: 41.7%)

---

## Extended Performance Metrics

### Risk-Adjusted Returns

| Metric | Value |
|--------|-------|
| Rolling Sharpe (Mean) | -1.138 |
| Rolling Sharpe (Std Dev) | 6.622 |
| Profit Factor | 0.811 |
| Tail Ratio (95th pct) | 0.938 |
| Consistency Score (21d) | 44.3% |

**Interpretation:**

- Weak profitability with gross losses approaching or exceeding gross wins
- Balanced tail distribution with similar upside and downside extremes
- Moderate consistency with mixed profitable/unprofitable periods

### Drawdown Recovery

| Metric | Value |
|--------|-------|
| Max Drawdown Recovery | Not recovered |
| Average Recovery Time | 11.4 days |
| Number of Drawdowns | 18 |

**Warning:** Maximum drawdown has not been recovered as of backtest end date.

---

## Subperiod Stability Analysis

**Number of Subperiods:** 4  
**Profitable Periods:** 2/4  
**Consistency Rate:** 50.0%

| Period | Return | Sharpe |
|--------|--------|--------|
| 1 | 7,486,488.61 | 0.753 |
| 2 | 9,144,593.64 | 0.871 |
| 3 | -40,896,031.14 | -4.246 |
| 4 | -19,895,457.50 | -2.635 |

**Interpretation:**

Moderate temporal consistency with mixed performance across subperiods. Performance may be regime-dependent.

---

## Return Attribution

### Directional Attribution

| Direction | P&L | Contribution |
|-----------|-----|--------------|
| Long | -24,657,502.44 | 41.7% |
| Short | -34,466,545.11 | 58.3% |

**Balanced exposure** - Returns distributed across both long and short positions.

### Signal Strength Attribution

| Quantile | P&L | Contribution |
|----------|-----|--------------|\n| Q1 | 25,493,885.38 | -43.1% |
| Q2 | -25,365,938.31 | 42.9% |
| Q3 | -59,251,994.62 | 100.2% |

**Strong signal strength relationship** - Highest conviction signals contributed most to returns (100.2%).

### Win/Loss Decomposition

| Category | Amount | Contribution |
|----------|--------|--------------|
| Gross Wins | 164,011,828.22 | 277.4% |
| Gross Losses | -223,135,875.77 | 377.4% |
| Net P&L | -59,124,047.55 | — |

---

## Recommendations

❌ **Negative profit factor** - Strategy is unprofitable; do not deploy

⚠️ **Unrecovered drawdown** - Current strategy underwater; reassess viability


---

## Report Metadata

**Generated:** 2025-11-09T15:33:48.658478  
**Evaluator:** aponyx.evaluation.performance  
**Configuration:**
- Minimum Observations: 252
- Subperiods: 4
- Rolling Window: 63 days
- Attribution Quantiles: 3

**Reproducibility:** All metrics computed from backtest P&L with deterministic methods.

---

*This report was auto-generated from performance evaluation results.*
