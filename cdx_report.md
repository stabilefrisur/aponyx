# Research Report: cdx_etf_basis (aggressive)

**Generated:** 2025-11-23 20:04:01

## Suitability Evaluation

# Signal-Product Suitability Evaluation Report

**Signal:** `cdx_etf_basis`  
**Product:** `cdx_ig_5y`  
**Evaluation Date:** 2025-11-23T20:03:49.726611  
**Evaluator Version:** 0.1.0

---

## Executive Summary

### Overall Decision: ❌ FAIL

**Composite Score:** 0.301

The signal lacks sufficient predictive content for this product. Do not proceed to backtesting. Consider alternative signal specifications.

---

## Component Analysis

### 1. Data Health Score: 0.962

**Metrics:**
- Valid Observations: 1,296
- Missing Data: 0.77%

**Interpretation:**  
Excellent data quality with sufficient observations and minimal missing data. Sample size supports reliable statistical inference.

---

### 2. Predictive Association Score: 0.172

**Metrics:**

| Lag | Correlation | Beta | T-Statistic |
|-----|-------------|------|-------------|
| 1 | -0.0254 | -0.0994 | -0.9145 |
| 3 | -0.0085 | -0.0334 | -0.3063 |
| 5 | 0.0090 | 0.0353 | 0.3237 |

**Interpretation:**  
No statistically significant predictive relationship detected. Signal appears uncorrelated with target movements.

---

### 3. Economic Relevance Score: 0.200

**Metrics:**
- Effect Size: 0.042 bps per 1σ signal change

**Interpretation:**  
Negligible economic impact. Even if statistically significant, the effect size is too small to generate meaningful P&L after realistic transaction costs.

---

### 4. Temporal Stability Score: 0.000

**Metrics:**
- Rolling Windows: 1045 windows (252 observations each)
- Sign Consistency Ratio: 57.2%
- Beta Coefficient of Variation: 45.189

**Interpretation:**  
Low temporal stability (inconsistent sign, high variation). The predictive relationship is unstable across time, suggesting strong regime dependence or non-stationarity. Use caution when designing strategies.

---

## Composite Scoring

| Component | Weight | Score | Contribution |
|-----------|--------|-------|--------------|
| Data Health | 0.20 | 0.962 | 0.192 |
| Predictive | 0.40 | 0.172 | 0.069 |
| Economic | 0.20 | 0.200 | 0.040 |
| Stability | 0.20 | 0.000 | 0.000 |
| **Total** | **1.00** | — | **0.301** |

---

## Decision Criteria

- **PASS** (≥ 0.70): Proceed to backtest
- **HOLD** (0.40 - 0.70): Marginal, requires judgment
- **FAIL** (< 0.40): Do not backtest

### Recommended Next Steps

1. Archive evaluation for reference
2. Document why signal failed (data, predictive, economic, or stability)
3. Consider alternative signal specifications
4. Do NOT proceed to backtesting with current signal

---

## Report Metadata

**Generated:** 2025-11-23T20:03:49.726611  
**Evaluator:** aponyx.evaluation.suitability v0.1.0  
**Reproducibility:** All metrics computed from aligned signal-target pairs with deterministic methods.

---

*This report was auto-generated from suitability evaluation results. For questions about methodology, see `docs/suitability_evaluation.md`.*


## Performance Analysis

# Backtest Performance Evaluation Report

**Signal:** `cdx_etf_basis`  
**Strategy:** `aggressive`  
**Evaluation Date:** 2025-11-23T20:03:50.420752  
**Evaluator Version:** 0.1.13

---

## Executive Summary

### Stability Assessment: ⚠️ Moderate

**Overall Stability Score:** 0.600

Overall: Moderate performance with acceptable stability (stability score: 0.60)
Profitability: Strong (profit factor 11.82)
Risk profile: Balanced (tail ratio 0.97)
Temporal consistency: 2/4 profitable periods (46.0% positive windows)
Balanced directional exposure (long: 4.5%)

---

## Basic Backtest Metrics

| Metric | Value |
|--------|-------|
| Total Return | $-39.10 |
| Annualized Return | $1.03 |
| Sharpe Ratio | 0.430 |
| Sortino Ratio | 14.968 |
| Max Drawdown | $-2.41 |
| Calmar Ratio | 0.427 |
| Annualized Volatility | $1,408.45 |

### Trade Statistics

| Metric | Value |
|--------|-------|
| Total Trades | 113 |
| Hit Rate | 39.8% |
| Average Win | $326,349.03 |
| Average Loss | $-316,631.52 |
| Win/Loss Ratio | 1.031 |
| Avg Holding Days | 7.4 |

---

## Extended Performance Metrics

### Risk-Adjusted Returns

| Metric | Value |
|--------|-------|
| Rolling Sharpe (Mean) | 1.022 |
| Rolling Sharpe (Std Dev) | 1.856 |
| Profit Factor | 11.823 |
| Tail Ratio (95th pct) | 0.970 |
| Consistency Score (21d) | 46.0% |

**Interpretation:**

- Strong profitability with gross wins substantially exceeding gross losses
- Balanced tail distribution with similar upside and downside extremes
- Moderate consistency with mixed profitable/unprofitable periods

### Drawdown Recovery

| Metric | Value |
|--------|-------|
| Max Drawdown Recovery | Not recovered |
| Average Recovery Time | 31.8 days |
| Number of Drawdowns | 20 |

**Warning:** Maximum drawdown has not been recovered as of backtest end date.

---

## Subperiod Stability Analysis

**Number of Subperiods:** 4  
**Profitable Periods:** 2/4  
**Consistency Rate:** 50.0%

| Period | Return | Sharpe |
|--------|--------|--------|
| 1 | 17.42 | 0.892 |
| 2 | -0.24 | 0.484 |
| 3 | -1.80 | -1.284 |
| 4 | 3.90 | 0.897 |

**Interpretation:**

Moderate temporal consistency with mixed performance across subperiods. Performance may be regime-dependent.

---

## Return Attribution

### Directional Attribution

| Direction | P&L | Contribution |
|-----------|-----|--------------|
| Long | -308,377.29 | 4.5% |
| Short | -6,536,860.15 | 95.5% |

**Balanced exposure** - Returns distributed across both long and short positions.

### Signal Strength Attribution

| Quantile | P&L | Contribution |
|----------|-----|--------------|
| Q1 | -2,529,677.94 | 37.0% |
| Q2 | -1,355,869.02 | 19.8% |
| Q3 | -2,959,690.49 | 43.2% |

**Strong signal strength relationship** - Highest conviction signals contributed most to returns (43.2%).

### Win/Loss Decomposition

| Category | Amount | Contribution |
|----------|--------|--------------|
| Gross Wins | 66,803,641.50 | 975.9% |
| Gross Losses | -73,648,878.94 | 1075.9% |
| Net P&L | -6,845,237.44 | — |

---

## Recommendations

⚠️ **Unrecovered drawdown** - Current strategy underwater; reassess viability


---

## Report Metadata

**Generated:** 2025-11-23T20:03:50.420752  
**Evaluator:** aponyx.evaluation.performance  
**Configuration:**
- Minimum Observations: 252
- Subperiods: 4
- Rolling Window: 63 days
- Attribution Quantiles: 3

**Reproducibility:** All metrics computed from backtest P&L with deterministic methods.

---

*This report was auto-generated from performance evaluation results.*


## Visualizations

- [drawdown](file:///C:/Users/ROG3003/PythonProjects/aponyx/data/workflows/cdx_etf_basis_aggressive_20251123_200349/visualizations/drawdown.html)
- [equity_curve](file:///C:/Users/ROG3003/PythonProjects/aponyx/data/workflows/cdx_etf_basis_aggressive_20251123_200349/visualizations/equity_curve.html)
- [signal](file:///C:/Users/ROG3003/PythonProjects/aponyx/data/workflows/cdx_etf_basis_aggressive_20251123_200349/visualizations/signal.html)

## Workflow Details

**Output Directory:** `C:\Users\ROG3003\PythonProjects\aponyx\data\workflows\cdx_etf_basis_aggressive_20251123_200349`
