# Backtest Performance Evaluation Report

**Signal:** `spread_momentum`  
**Strategy:** `aggressive`  
**Evaluation Date:** 2025-11-09T18:21:05.344942  
**Evaluator Version:** 0.1.6

---

## Executive Summary

### Stability Assessment: ⚠️ Moderate

**Overall Stability Score:** 0.500

Overall: Moderate performance with acceptable stability (stability score: 0.50)
Profitability: Weak (profit factor 0.97)
Risk profile: Balanced (tail ratio 0.84)
Temporal consistency: 2/4 profitable periods (53.4% positive windows)
Balanced directional exposure (long: 69.9%)

---

## Extended Performance Metrics

### Risk-Adjusted Returns

| Metric | Value |
|--------|-------|
| Rolling Sharpe (Mean) | 0.281 |
| Rolling Sharpe (Std Dev) | 6.783 |
| Profit Factor | 0.965 |
| Tail Ratio (95th pct) | 0.839 |
| Consistency Score (21d) | 53.4% |

**Interpretation:**

- Weak profitability with gross losses approaching or exceeding gross wins
- Balanced tail distribution with similar upside and downside extremes
- Moderate consistency with mixed profitable/unprofitable periods

### Drawdown Recovery

| Metric | Value |
|--------|-------|
| Max Drawdown Recovery | Not recovered |
| Average Recovery Time | 25.8 days |
| Number of Drawdowns | 13 |

**Warning:** Maximum drawdown has not been recovered as of backtest end date.

---

## Subperiod Stability Analysis

**Number of Subperiods:** 4  
**Profitable Periods:** 2/4  
**Consistency Rate:** 50.0%

| Period | Return | Sharpe |
|--------|--------|--------|
| 1 | 12,654,592.62 | 1.545 |
| 2 | -31,692,481.53 | -3.384 |
| 3 | -21,264,029.93 | -1.873 |
| 4 | 32,816,622.51 | 3.457 |

**Interpretation:**

Moderate temporal consistency with mixed performance across subperiods. Performance may be regime-dependent.

---

## Return Attribution

### Directional Attribution

| Direction | P&L | Contribution |
|-----------|-----|--------------|
| Long | 10,690,706.97 | 69.9% |
| Short | 4,592,701.60 | 30.1% |

**Balanced exposure** - Returns distributed across both long and short positions.

### Signal Strength Attribution

| Quantile | P&L | Contribution |
|----------|-----|--------------|\n| Q1 | -15,670,956.83 | -102.5% |
| Q2 | -344,608.24 | -2.3% |
| Q3 | 31,298,973.63 | 204.8% |

**Strong signal strength relationship** - Highest conviction signals contributed most to returns (204.8%).

### Win/Loss Decomposition

| Category | Amount | Contribution |
|----------|--------|--------------|
| Gross Wins | 200,548,012.70 | 1312.2% |
| Gross Losses | -185,264,604.14 | 1212.2% |
| Net P&L | 15,283,408.57 | — |

---

## Recommendations

❌ **Negative profit factor** - Strategy is unprofitable; do not deploy

⚠️ **Unrecovered drawdown** - Current strategy underwater; reassess viability


---

## Report Metadata

**Generated:** 2025-11-09T18:21:05.581453  
**Evaluator:** aponyx.evaluation.performance  
**Configuration:**
- Minimum Observations: 252
- Subperiods: 4
- Rolling Window: 63 days
- Attribution Quantiles: 3

**Reproducibility:** All metrics computed from backtest P&L with deterministic methods.

---

*This report was auto-generated from performance evaluation results.*
