# Backtest Performance Evaluation Report

**Signal:** `cdx_etf_basis`  
**Strategy:** `experimental`  
**Evaluation Date:** 2025-11-09T15:33:48.191735  
**Evaluator Version:** 0.1.6

---

## Executive Summary

### Stability Assessment: ⚠️ Moderate

**Overall Stability Score:** 0.500

Overall: Moderate performance with acceptable stability (stability score: 0.50)
Profitability: Positive (profit factor 1.29)
Risk profile: Balanced (tail ratio 1.15)
Temporal consistency: 2/4 profitable periods (55.3% positive windows)
Balanced directional exposure (long: 40.3%)

---

## Extended Performance Metrics

### Risk-Adjusted Returns

| Metric | Value |
|--------|-------|
| Rolling Sharpe (Mean) | 1.256 |
| Rolling Sharpe (Std Dev) | 7.884 |
| Profit Factor | 1.294 |
| Tail Ratio (95th pct) | 1.153 |
| Consistency Score (21d) | 55.3% |

**Interpretation:**

- Positive profitability with gross wins exceeding gross losses
- Balanced tail distribution with similar upside and downside extremes
- Moderate consistency with mixed profitable/unprofitable periods

### Drawdown Recovery

| Metric | Value |
|--------|-------|
| Max Drawdown Recovery | Not recovered |
| Average Recovery Time | 18.4 days |
| Number of Drawdowns | 36 |

**Warning:** Maximum drawdown has not been recovered as of backtest end date.

---

## Subperiod Stability Analysis

**Number of Subperiods:** 4  
**Profitable Periods:** 2/4  
**Consistency Rate:** 50.0%

| Period | Return | Sharpe |
|--------|--------|--------|
| 1 | 74,493,315.37 | 6.928 |
| 2 | 32,532,072.15 | 3.232 |
| 3 | -12,443,809.37 | -0.959 |
| 4 | -27,045,589.39 | -2.340 |

**Interpretation:**

Moderate temporal consistency with mixed performance across subperiods. Performance may be regime-dependent.

---

## Return Attribution

### Directional Attribution

| Direction | P&L | Contribution |
|-----------|-----|--------------|
| Long | 23,987,077.31 | 40.3% |
| Short | 35,550,733.61 | 59.7% |

**Balanced exposure** - Returns distributed across both long and short positions.

### Signal Strength Attribution

| Quantile | P&L | Contribution |
|----------|-----|--------------|\n| Q1 | 41,802,183.12 | 70.2% |
| Q2 | 4,473,317.92 | 7.5% |
| Q3 | 13,262,309.88 | 22.3% |

**Moderate signal strength relationship** - Mixed contribution across signal strengths.

### Win/Loss Decomposition

| Category | Amount | Contribution |
|----------|--------|--------------|
| Gross Wins | 272,046,562.95 | 456.9% |
| Gross Losses | -212,508,752.03 | 356.9% |
| Net P&L | 59,537,810.92 | — |

---

## Recommendations

⚠️ **Unrecovered drawdown** - Current strategy underwater; reassess viability


---

## Report Metadata

**Generated:** 2025-11-09T15:33:48.652784  
**Evaluator:** aponyx.evaluation.performance  
**Configuration:**
- Minimum Observations: 252
- Subperiods: 4
- Rolling Window: 63 days
- Attribution Quantiles: 3

**Reproducibility:** All metrics computed from backtest P&L with deterministic methods.

---

*This report was auto-generated from performance evaluation results.*
