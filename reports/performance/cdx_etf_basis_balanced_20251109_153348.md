# Backtest Performance Evaluation Report

**Signal:** `cdx_etf_basis`  
**Strategy:** `balanced`  
**Evaluation Date:** 2025-11-09T15:33:48.153986  
**Evaluator Version:** 0.1.6

---

## Executive Summary

### Stability Assessment: ⚠️ Moderate

**Overall Stability Score:** 0.500

Overall: Moderate performance with acceptable stability (stability score: 0.50)
Profitability: Weak (profit factor 0.92)
Risk profile: Balanced (tail ratio 1.08)
Temporal consistency: 2/4 profitable periods (42.4% positive windows)
Strong long directional bias (112.1%)

---

## Extended Performance Metrics

### Risk-Adjusted Returns

| Metric | Value |
|--------|-------|
| Rolling Sharpe (Mean) | -0.679 |
| Rolling Sharpe (Std Dev) | 4.679 |
| Profit Factor | 0.921 |
| Tail Ratio (95th pct) | 1.080 |
| Consistency Score (21d) | 42.4% |

**Interpretation:**

- Weak profitability with gross losses approaching or exceeding gross wins
- Balanced tail distribution with similar upside and downside extremes
- Moderate consistency with mixed profitable/unprofitable periods

### Drawdown Recovery

| Metric | Value |
|--------|-------|
| Max Drawdown Recovery | Not recovered |
| Average Recovery Time | 21.3 days |
| Number of Drawdowns | 13 |

**Warning:** Maximum drawdown has not been recovered as of backtest end date.

---

## Subperiod Stability Analysis

**Number of Subperiods:** 4  
**Profitable Periods:** 2/4  
**Consistency Rate:** 50.0%

| Period | Return | Sharpe |
|--------|--------|--------|
| 1 | 7,984,221.96 | 1.356 |
| 2 | -17,777,493.89 | -2.577 |
| 3 | -14,054,840.98 | -1.499 |
| 4 | 13,318,693.76 | 1.583 |

**Interpretation:**

Moderate temporal consistency with mixed performance across subperiods. Performance may be regime-dependent.

---

## Return Attribution

### Directional Attribution

| Direction | P&L | Contribution |
|-----------|-----|--------------|
| Long | -15,292,082.97 | 112.1% |
| Short | 1,644,674.53 | -12.1% |

**Strong long bias** - Returns highly concentrated in long positions.

### Signal Strength Attribution

| Quantile | P&L | Contribution |
|----------|-----|--------------|\n| Q1 | -7,418,390.74 | 54.4% |
| Q2 | -4,647,807.25 | 34.1% |
| Q3 | -1,581,210.46 | 11.6% |

**Weak signal strength relationship** - Returns not concentrated in highest conviction signals. Signal strength may not add value.

### Win/Loss Decomposition

| Category | Amount | Contribution |
|----------|--------|--------------|
| Gross Wins | 104,202,940.43 | 763.5% |
| Gross Losses | -117,850,348.87 | 863.5% |
| Net P&L | -13,647,408.44 | — |

---

## Recommendations

❌ **Negative profit factor** - Strategy is unprofitable; do not deploy

⚠️ **Unrecovered drawdown** - Current strategy underwater; reassess viability


---

## Report Metadata

**Generated:** 2025-11-09T15:33:48.650730  
**Evaluator:** aponyx.evaluation.performance  
**Configuration:**
- Minimum Observations: 252
- Subperiods: 4
- Rolling Window: 63 days
- Attribution Quantiles: 3

**Reproducibility:** All metrics computed from backtest P&L with deterministic methods.

---

*This report was auto-generated from performance evaluation results.*
