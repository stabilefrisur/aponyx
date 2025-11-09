# Backtest Performance Evaluation Report

**Signal:** `cdx_etf_basis`  
**Strategy:** `conservative`  
**Evaluation Date:** 2025-11-09T18:21:05.140294  
**Evaluator Version:** 0.1.6

---

## Executive Summary

### Stability Assessment: ⚠️ Moderate

**Overall Stability Score:** 0.500

Overall: Moderate performance with acceptable stability (stability score: 0.50)
Profitability: Weak (profit factor 0.85)
Risk profile: Balanced (tail ratio 0.94)
Temporal consistency: 2/4 profitable periods (36.8% positive windows)
Balanced directional exposure (long: 1.9%)

---

## Extended Performance Metrics

### Risk-Adjusted Returns

| Metric | Value |
|--------|-------|
| Rolling Sharpe (Mean) | -0.377 |
| Rolling Sharpe (Std Dev) | 4.428 |
| Profit Factor | 0.855 |
| Tail Ratio (95th pct) | 0.939 |
| Consistency Score (21d) | 36.8% |

**Interpretation:**

- Weak profitability with gross losses approaching or exceeding gross wins
- Balanced tail distribution with similar upside and downside extremes
- Low consistency with frequent unprofitable rolling windows

### Drawdown Recovery

| Metric | Value |
|--------|-------|
| Max Drawdown Recovery | Not recovered |
| Average Recovery Time | 63.5 days |
| Number of Drawdowns | 5 |

**Warning:** Maximum drawdown has not been recovered as of backtest end date.

---

## Subperiod Stability Analysis

**Number of Subperiods:** 4  
**Profitable Periods:** 2/4  
**Consistency Rate:** 50.0%

| Period | Return | Sharpe |
|--------|--------|--------|
| 1 | 9,662,539.73 | 2.026 |
| 2 | -13,128,430.67 | -1.998 |
| 3 | -25,147,524.11 | -3.396 |
| 4 | 16,590,240.83 | 2.800 |

**Interpretation:**

Moderate temporal consistency with mixed performance across subperiods. Performance may be regime-dependent.

---

## Return Attribution

### Directional Attribution

| Direction | P&L | Contribution |
|-----------|-----|--------------|
| Long | -255,980.85 | 1.9% |
| Short | -13,231,806.37 | 98.1% |

**Balanced exposure** - Returns distributed across both long and short positions.

### Signal Strength Attribution

| Quantile | P&L | Contribution |
|----------|-----|--------------|\n| Q1 | -23,198,801.27 | 172.0% |
| Q2 | 9,170,556.13 | -68.0% |
| Q3 | 540,457.92 | -4.0% |

**Weak signal strength relationship** - Returns not concentrated in highest conviction signals. Signal strength may not add value.

### Win/Loss Decomposition

| Category | Amount | Contribution |
|----------|--------|--------------|
| Gross Wins | 58,716,489.44 | 435.3% |
| Gross Losses | -72,204,276.66 | 535.3% |
| Net P&L | -13,487,787.22 | — |

---

## Recommendations

❌ **Negative profit factor** - Strategy is unprofitable; do not deploy

⚠️ **Unrecovered drawdown** - Current strategy underwater; reassess viability


---

## Report Metadata

**Generated:** 2025-11-09T18:21:05.566211  
**Evaluator:** aponyx.evaluation.performance  
**Configuration:**
- Minimum Observations: 252
- Subperiods: 4
- Rolling Window: 63 days
- Attribution Quantiles: 3

**Reproducibility:** All metrics computed from backtest P&L with deterministic methods.

---

*This report was auto-generated from performance evaluation results.*
