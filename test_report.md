# Research Report: spread_momentum (balanced)

**Generated:** 2025-11-23 20:03:09

## Suitability Evaluation

# Signal-Product Suitability Evaluation Report

**Signal:** `spread_momentum`  
**Product:** `cdx_ig_5y`  
**Evaluation Date:** 2025-11-23T20:02:16.706842  
**Evaluator Version:** 0.1.0

---

## Executive Summary

### Overall Decision: ✅ PASS

**Composite Score:** 0.904

The signal demonstrates strong predictive content with good data quality. Proceed to strategy design and backtesting.

---

## Component Analysis

### 1. Data Health Score: 0.920

**Metrics:**
- Valid Observations: 1,285
- Missing Data: 1.61%

**Interpretation:**  
Excellent data quality with sufficient observations and minimal missing data. Sample size supports reliable statistical inference.

---

### 2. Predictive Association Score: 1.000

**Metrics:**

| Lag | Correlation | Beta | T-Statistic |
|-----|-------------|------|-------------|
| 1 | 0.1508 | 0.3947 | 5.4622 |
| 3 | 0.1351 | 0.3537 | 4.8779 |
| 5 | 0.0974 | 0.2558 | 3.4984 |

**Interpretation:**  
Strong statistical evidence of predictive relationship. T-statistics exceed conventional significance thresholds with high confidence.

---

### 3. Economic Relevance Score: 0.600

**Metrics:**
- Effect Size: 0.650 bps per 1σ signal change

**Interpretation:**  
Moderate economic impact. Effect size is detectable but may be marginal after transaction costs. Careful strategy design required.

---

### 4. Temporal Stability Score: 1.000

**Metrics:**
- Rolling Windows: 1034 windows (252 observations each)
- Sign Consistency Ratio: 100.0%
- Beta Coefficient of Variation: 0.465

**Interpretation:**  
Excellent temporal stability (highly consistent sign, stable magnitude). The predictive relationship maintains consistent direction and magnitude across 1034 rolling windows, indicating robustness across different market regimes.

---

## Composite Scoring

| Component | Weight | Score | Contribution |
|-----------|--------|-------|--------------|
| Data Health | 0.20 | 0.920 | 0.184 |
| Predictive | 0.40 | 1.000 | 0.400 |
| Economic | 0.20 | 0.600 | 0.120 |
| Stability | 0.20 | 1.000 | 0.200 |
| **Total** | **1.00** | — | **0.904** |

---

## Decision Criteria

- **PASS** (≥ 0.70): Proceed to backtest
- **HOLD** (0.40 - 0.70): Marginal, requires judgment
- **FAIL** (< 0.40): Do not backtest

### Recommended Next Steps

1. Design trading strategy with entry/exit rules
2. Configure backtest parameters (position sizing, costs)
3. Run historical backtest with proper risk controls
4. Analyze performance metrics and risk-adjusted returns

---

## Report Metadata

**Generated:** 2025-11-23T20:02:16.706842  
**Evaluator:** aponyx.evaluation.suitability v0.1.0  
**Reproducibility:** All metrics computed from aligned signal-target pairs with deterministic methods.

---

*This report was auto-generated from suitability evaluation results. For questions about methodology, see `docs/suitability_evaluation.md`.*


## Performance Analysis

# Backtest Performance Evaluation Report

**Signal:** `spread_momentum`  
**Strategy:** `balanced`  
**Evaluation Date:** 2025-11-23T20:02:17.413793  
**Evaluator Version:** 0.1.13

---

## Executive Summary

### Stability Assessment: ✅ Strong

**Overall Stability Score:** 0.750

Overall: Strong and stable performance (stability score: 0.75)
Profitability: Weak (profit factor 0.66)
Risk profile: Favorable asymmetry (tail ratio 1.37)
Temporal consistency: 3/4 profitable periods (32.8% positive windows)
Balanced directional exposure (long: 48.9%)

---

## Basic Backtest Metrics

| Metric | Value |
|--------|-------|
| Total Return | $-182.95 |
| Annualized Return | $1.77 |
| Sharpe Ratio | -0.352 |
| Sortino Ratio | -0.364 |
| Max Drawdown | $-24.81 |
| Calmar Ratio | 0.072 |
| Annualized Volatility | $9.43 |

### Trade Statistics

| Metric | Value |
|--------|-------|
| Total Trades | 105 |
| Hit Rate | 24.8% |
| Average Win | $227,595.95 |
| Average Loss | $-362,280.02 |
| Win/Loss Ratio | 0.628 |
| Avg Holding Days | 6.6 |

---

## Extended Performance Metrics

### Risk-Adjusted Returns

| Metric | Value |
|--------|-------|
| Rolling Sharpe (Mean) | 1.232 |
| Rolling Sharpe (Std Dev) | 1.630 |
| Profit Factor | 0.656 |
| Tail Ratio (95th pct) | 1.367 |
| Consistency Score (21d) | 32.8% |

**Interpretation:**

- Weak profitability with gross losses approaching or exceeding gross wins
- Favorable tail asymmetry with larger upside than downside extremes
- Low consistency with frequent unprofitable rolling windows

### Drawdown Recovery

| Metric | Value |
|--------|-------|
| Max Drawdown Recovery | Not recovered |
| Average Recovery Time | 3.0 days |
| Number of Drawdowns | 2 |

**Warning:** Maximum drawdown has not been recovered as of backtest end date.

---

## Subperiod Stability Analysis

**Number of Subperiods:** 4  
**Profitable Periods:** 3/4  
**Consistency Rate:** 75.0%

| Period | Return | Sharpe |
|--------|--------|--------|
| 1 | -50.41 | -0.764 |
| 2 | 1.33 | 1.912 |
| 3 | 0.46 | 1.390 |
| 4 | 0.08 | 0.434 |

**Interpretation:**

Excellent temporal consistency with strong performance across most subperiods. Strategy appears robust to different market conditions.

---

## Return Attribution

### Directional Attribution

| Direction | P&L | Contribution |
|-----------|-----|--------------|
| Long | -11,103,900.73 | 48.9% |
| Short | -11,598,725.95 | 51.1% |

**Balanced exposure** - Returns distributed across both long and short positions.

### Signal Strength Attribution

| Quantile | P&L | Contribution |
|----------|-----|--------------|
| Q1 | -7,892,935.56 | 34.8% |
| Q2 | -7,297,857.74 | 32.1% |
| Q3 | -7,511,833.38 | 33.1% |

**Moderate signal strength relationship** - Mixed contribution across signal strengths.

### Win/Loss Decomposition

| Category | Amount | Contribution |
|----------|--------|--------------|
| Gross Wins | 59,211,959.74 | 260.8% |
| Gross Losses | -81,914,586.42 | 360.8% |
| Net P&L | -22,702,626.69 | — |

---

## Recommendations

❌ **Negative profit factor** - Strategy is unprofitable; do not deploy

⚠️ **Unrecovered drawdown** - Current strategy underwater; reassess viability


---

## Report Metadata

**Generated:** 2025-11-23T20:02:17.413793  
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

- [drawdown](file:///C:/Users/ROG3003/PythonProjects/aponyx/data/workflows/spread_momentum_balanced_20251123_200216/visualizations/drawdown.html)
- [equity_curve](file:///C:/Users/ROG3003/PythonProjects/aponyx/data/workflows/spread_momentum_balanced_20251123_200216/visualizations/equity_curve.html)
- [signal](file:///C:/Users/ROG3003/PythonProjects/aponyx/data/workflows/spread_momentum_balanced_20251123_200216/visualizations/signal.html)

## Workflow Details

**Output Directory:** `C:\Users\ROG3003\PythonProjects\aponyx\data\workflows\spread_momentum_balanced_20251123_200216`
