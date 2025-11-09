# Backtest Performance Evaluation Report

**Signal:** `cdx_etf_basis`  
**Strategy:** `aggressive`  
**Evaluation Date:** 2025-11-09T15:33:48.175389  
**Evaluator Version:** 0.1.6

---

## Executive Summary

### Stability Assessment: ⚠️ Moderate

**Overall Stability Score:** 0.500

Overall: Moderate performance with acceptable stability (stability score: 0.50)
Profitability: Weak (profit factor 0.76)
Risk profile: Negative skew (tail ratio 0.78)
Temporal consistency: 2/4 profitable periods (42.6% positive windows)
Balanced directional exposure (long: 29.2%)

---

## Extended Performance Metrics

### Risk-Adjusted Returns

| Metric | Value |
|--------|-------|
| Rolling Sharpe (Mean) | -1.305 |
| Rolling Sharpe (Std Dev) | 5.060 |
| Profit Factor | 0.764 |
| Tail Ratio (95th pct) | 0.775 |
| Consistency Score (21d) | 42.6% |

**Interpretation:**

- Weak profitability with gross losses approaching or exceeding gross wins
- Negative tail asymmetry with larger downside than upside extremes
- Moderate consistency with mixed profitable/unprofitable periods

### Drawdown Recovery

| Metric | Value |
|--------|-------|
| Max Drawdown Recovery | Not recovered |
| Average Recovery Time | 48.8 days |
| Number of Drawdowns | 7 |

**Warning:** Maximum drawdown has not been recovered as of backtest end date.

---

## Subperiod Stability Analysis

**Number of Subperiods:** 4  
**Profitable Periods:** 2/4  
**Consistency Rate:** 50.0%

| Period | Return | Sharpe |
|--------|--------|--------|
| 1 | 5,358,148.02 | 0.728 |
| 2 | -15,235,292.16 | -1.839 |
| 3 | -40,633,848.46 | -4.083 |
| 4 | 5,434,206.73 | 0.670 |

**Interpretation:**

Moderate temporal consistency with mixed performance across subperiods. Performance may be regime-dependent.

---

## Return Attribution

### Directional Attribution

| Direction | P&L | Contribution |
|-----------|-----|--------------|
| Long | -14,242,410.50 | 29.2% |
| Short | -34,585,944.56 | 70.8% |

**Balanced exposure** - Returns distributed across both long and short positions.

### Signal Strength Attribution

| Quantile | P&L | Contribution |
|----------|-----|--------------|\n| Q1 | -14,620,246.67 | 29.9% |
| Q2 | -10,802,429.71 | 22.1% |
| Q3 | -23,405,678.67 | 47.9% |

**Strong signal strength relationship** - Highest conviction signals contributed most to returns (47.9%).

### Win/Loss Decomposition

| Category | Amount | Contribution |
|----------|--------|--------------|
| Gross Wins | 123,820,480.55 | 253.6% |
| Gross Losses | -172,648,835.60 | 353.6% |
| Net P&L | -48,828,355.05 | — |

---

## Recommendations

❌ **Negative profit factor** - Strategy is unprofitable; do not deploy

⚠️ **Unrecovered drawdown** - Current strategy underwater; reassess viability

⚠️ **Negative skew** - Downside risk exceeds upside potential; review risk controls


---

## Report Metadata

**Generated:** 2025-11-09T15:33:48.651734  
**Evaluator:** aponyx.evaluation.performance  
**Configuration:**
- Minimum Observations: 252
- Subperiods: 4
- Rolling Window: 63 days
- Attribution Quantiles: 3

**Reproducibility:** All metrics computed from backtest P&L with deterministic methods.

---

*This report was auto-generated from performance evaluation results.*
