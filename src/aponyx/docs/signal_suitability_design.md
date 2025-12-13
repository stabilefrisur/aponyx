# Signal–Product Suitability Evaluation Layer

**Version:** 2.0  
**Date:** December 2025  
**Module Path:** `src/aponyx/evaluation/suitability/`  
**Purpose:** Pre-backtest screening of signal-product pairs for statistical credibility, economic relevance, and temporal stability.

---

## 1. Purpose

The suitability evaluation layer provides **quantitative assessment of signal-product relationships** before committing resources to full backtesting. It answers four fundamental questions:

1. **Data Health** – Is there sufficient, clean data for reliable inference?  
2. **Predictive Credibility** – Does the signal predict the target with statistically significant evidence?  
3. **Economic Relevance** – Is the predicted effect large enough to be tradeable?  
4. **Temporal Stability** – Is the relationship persistent across market regimes?

**Assessment Framework:**

| Decision | Meaning | Interpretation |
|----------|---------|----------------|
| PASS     | Signal meets suitability criteria | High confidence for backtesting |
| HOLD     | Signal shows promise but has marginal scores | Review before backtesting |
| FAIL     | Signal lacks predictive evidence | Low confidence; consider improvements |

**Workflow Position:**

```
Data → Signal Generation → Suitability Evaluation → Backtest → Performance Analysis
                                 (assessment)
```

---

## 2. Design Principles

1. **Deterministic:** Evaluations produce identical results given identical inputs (no randomness).  
2. **Transparent:** All metrics have clear statistical and economic interpretation.  
3. **Lightweight:** Minimal dependencies; fast computation suitable for batch evaluation.  
4. **Reproducible:** Full metadata logging with versioned outputs and configuration tracking.  
5. **Functional:** Pure functions for all scoring logic; class-based registry for tracking.

---

## 3. Evaluation Components

### 3.1 Data Health

**Purpose:** Verify data quality and sufficiency for reliable statistical inference.

**Metrics:**

- **Valid Observations:** Count of aligned signal-target pairs after dropna  
- **Missing Percentage:** Proportion of data lost during alignment  
- **Minimum Sample Requirement:** Configurable threshold (default: 100 observations)

**Scoring Function:**

```python
def score_data_health(
    valid_obs: int,
    missing_pct: float,
    min_obs: int,
) -> float:
    """
    Score data quality on [0, 1] scale.
    
    Returns 0.0 if valid_obs < min_obs.
    Penalizes high missing_pct linearly.
    """
```

**Outcome:** Score ∈ [0, 1] with interpretation (excellent/adequate/poor).

---

### 3.2 Predictive Credibility

**Purpose:** Quantify statistical evidence that signal predicts target movements.

**Statistical Tests:**

- **Correlation:** Pearson correlation between signal and forward returns across multiple lags  
- **Regression:** OLS regression β coefficients and t-statistics  
- **Multi-Horizon:** Evaluate at configured lags (e.g., 1-day, 5-day, 10-day forward)

**Key Metric:** Mean absolute t-statistic across all lag horizons.

**Scoring Function:**

```python
def score_predictive(mean_abs_tstat: float) -> float:
    """
    Map t-statistic strength to [0, 1] score.
    
    |t| < 2.0: Low credibility (< 0.5)
    |t| ≥ 3.0: High credibility (> 0.8)
    """
```

**Outcome:** Score ∈ [0, 1] based on statistical significance strength.

---

### 3.3 Economic Relevance

**Purpose:** Translate statistical relationship into economically meaningful impact.

**Computation:**

1. Compute average β across all lag horizons  
2. Scale by signal volatility: `effect_size = |β| × σ_signal`  
3. Express in basis points for spread products

**Economic Context:**

- **CDX spreads:** Effect size < 1 bps likely too small to trade  
- **CDX spreads:** Effect size > 5 bps economically significant

**Scoring Function:**

```python
def score_economic(effect_size_bps: float) -> float:
    """
    Map economic impact to [0, 1] score.
    
    < 1 bps: Low relevance (< 0.3)
    > 5 bps: High relevance (> 0.8)
    """
```

**Outcome:** Score ∈ [0, 1] with bps-denominated effect size.

---

### 3.4 Temporal Stability

**Purpose:** Verify relationship persistence across market regimes.

**Method:**

1. Compute rolling β coefficients using sliding window (default: 252 observations)  
2. Calculate coefficient of variation (CV) of rolling betas  
3. Check sign consistency (proportion of windows with same sign as aggregate)

**Stability Indicators:**

- **Sign Consistency Ratio:** Proportion of rolling windows with same sign as aggregate β  
- **Magnitude Stability:** Coefficient of variation of rolling betas (lower = more stable)

**Scoring Function:**

```python
def score_stability(
    sign_consistency_ratio: float,
    beta_cv: float,
) -> float:
    """
    Score stability on [0, 1] scale using two components.
    
    Sign consistency: ≥80% same sign = high (0.5 contribution)
    Magnitude stability: CV < 0.5 = high (0.5 contribution)
    
    Returns weighted average of both stability measures.
    """
```

**Outcome:** Score ∈ [0, 1] based on both sign persistence and magnitude stability.

---

### 3.5 Composite Score

**Aggregation:** Weighted average of component scores.

**Default Weights:**

| Component | Weight | Rationale |
|-----------|--------|--------|
| Data Health | 0.20 | Foundation requirement |
| Predictive Credibility | 0.40 | Core screening criterion |
| Economic Relevance | 0.20 | Practical tradability |
| Temporal Stability | 0.20 | Regime robustness |

**Decision Thresholds:**

| Composite Score | Decision |
|----------------|----------|
| ≥ 0.70 | PASS |
| 0.40–0.69 | HOLD |
| < 0.40 | FAIL |

---

## 4. Evaluation Methodology (Conceptual)

### 4.1 Data Health

**Intention:** Only signals with reliable underlying data should be considered.  

**Considerations:**

* Minimum sample size for statistical inference  
* Missing data proportion and alignment with target variable  
* Identification of extreme outliers or discontinuities  

**Outcome:** A normalized score representing data reliability, along with interpretation text.

---

### 4.2 Predictive Credibility

**Intention:** Quantify the signal’s ability to predict the target in a statistically meaningful way.  

**Conceptual Steps:**

* Measure directional association between signal and future target moves  
* Adjust for residual correlation or autocorrelation effects  
* Aggregate predictive strength across relevant horizons or lags  

**Outcome:** A score representing statistical credibility, accompanied by key metrics and narrative interpretation.

---

### 4.3 Economic Relevance

**Intention:** Convert statistical association into a meaningful economic effect.  

**Conceptual Steps:**

* Scale estimated impact by the variability of the signal and the target  
* Present effect in units familiar to the researcher (e.g., bps, %, or σ-scaled moves)  
* Contextualize whether the magnitude is practically relevant for trading or risk allocation  

**Outcome:** Score reflecting the economic significance, and a short textual assessment.

---

### 4.4 Temporal Stability

**Intention:** Ensure the signal’s predictive effect is persistent and robust across different market conditions.  

**Conceptual Steps:**

* Perform rolling or windowed evaluation of predictive metrics  
* Track variability (CV), directional consistency, and frequency of sign flips  
* Identify potential regime dependence or intermittent predictability  

**Outcome:** Score reflecting stability, along with interpretive summary and optional visualization of temporal trends.

---

## 5. Composite Evaluation

* Combine the four dimension scores into a **composite score**.  
* Default weighting can be adjusted based on research priorities:  

| Dimension             | Default Weight |
|-----------------------|----------------|
| Data Health           | 0.2            |
| Predictive Credibility| 0.4            |
| Economic Relevance    | 0.2            |
| Temporal Stability    | 0.2            |

* Composite score interpretation:
  - **≥ 0.70:** High confidence (strong candidate for backtesting)
  - **0.40–0.69:** Marginal (requires judgment and further review)
  - **< 0.40:** Low confidence (consider signal improvements)

---

## 4. Report Structure

**Format:** Markdown with structured sections for human readability and git versioning.

**Standard Sections:**

1. **Header**  
   - Signal ID, Product ID, Evaluation timestamp  
   - Composite score and assessment category (PASS/HOLD/FAIL)

2. **Summary Table**  
   - Component scores with weights  
   - Composite calculation breakdown

3. **Component Details**  
   - **Data Health:** Valid observations, missing %, alignment quality  
   - **Predictive Credibility:** Correlations, betas, t-stats by lag horizon  
   - **Economic Relevance:** Effect size (bps), practical context  
   - **Temporal Stability:** Rolling beta statistics, sign consistency ratio, coefficient of variation, number of windows

4. **Assessment Notes**  
   - Threshold comparison  
   - Marginal components (if applicable)  
   - Areas for potential improvement

5. **Footer**  
   - Configuration snapshot (lags, rolling_window, thresholds, weights)  
   - Timestamp  
   - Reproducibility notice

**File Naming:** `{signal_id}_{product_id}_{timestamp}.md`

**Storage:** `data/workflows/{signal}_{strategy}_{timestamp}/reports/`

---

## 5. Module Architecture

```
aponyx/evaluation/suitability/
├── config.py           # SuitabilityConfig dataclass (frozen)
├── evaluator.py        # evaluate_signal_suitability() orchestration
├── tests.py            # Statistical test functions (pure)
├── scoring.py          # Score computation functions (pure)
├── report.py           # generate_suitability_report() function
├── registry.py         # SuitabilityRegistry class
└── __init__.py         # Public API exports

data/.registries/
└── suitability.json    # Evaluation metadata catalog (runtime)
```

**Design Patterns:**

| Module | Pattern | State | Purpose |
|--------|---------|-------|------|
| `config.py` | Frozen dataclass | Immutable | Configuration container |
| `evaluator.py` | Pure function | Stateless | Orchestration |
| `tests.py` | Pure functions | Stateless | Statistical computations |
| `scoring.py` | Pure functions | Stateless | Score mapping |
| `report.py` | Pure function | Stateless | Markdown generation |
| `registry.py` | Class-based | Mutable | Metadata tracking |

**Key Function Signatures:**

```python
# Orchestration (evaluator.py)
def evaluate_signal_suitability(
    signal: pd.Series,
    target_change: pd.Series,
    config: SuitabilityConfig | None = None,
) -> SuitabilityResult

# Statistical tests (tests.py)
def compute_correlation(signal: pd.Series, target: pd.Series) -> float
def compute_regression_stats(signal: pd.Series, target: pd.Series) -> dict[str, float]
def compute_rolling_betas(signal: pd.Series, target: pd.Series, window: int) -> pd.Series
def compute_stability_metrics(rolling_betas: pd.Series, aggregate_beta: float) -> dict[str, float]

# Scoring (scoring.py)
def score_data_health(valid_obs: int, missing_pct: float, min_obs: int) -> float
def score_predictive(mean_abs_tstat: float) -> float
def score_economic(effect_size_bps: float) -> float
def score_stability(sign_consistency_ratio: float, beta_cv: float) -> float
def compute_composite_score(
    data_health_score: float,
    predictive_score: float,
    economic_score: float,
    stability_score: float,
    config: SuitabilityConfig,
) -> float
def assign_decision(composite_score: float, config: SuitabilityConfig) -> str

# Reporting (report.py)
def generate_suitability_report(
    result: SuitabilityResult,
    signal_id: str,
    product_id: str,
) -> str
```

**Configuration Parameters:**

```python
@dataclass(frozen=True)
class SuitabilityConfig:
    lags: list[int] = [1, 3, 5]           # Forecast horizons (days ahead)
    min_obs: int = 500                     # Minimum valid observations
    rolling_window: int = 252              # Stability analysis window (~1 year)
    pass_threshold: float = 0.7            # Score for PASS decision
    hold_threshold: float = 0.4            # Score for HOLD decision
    data_health_weight: float = 0.2        # Component weights (must sum to 1.0)
    predictive_weight: float = 0.4
    economic_weight: float = 0.2
    stability_weight: float = 0.2
```

**Result Container:**

```python
@dataclass
class SuitabilityResult:
    decision: str                          # PASS/HOLD/FAIL
    composite_score: float                 # Weighted average (0-1)
    data_health_score: float               # Component scores (0-1)
    predictive_score: float
    economic_score: float
    stability_score: float
    valid_obs: int                         # Diagnostic metrics
    missing_pct: float
    correlations: dict[int, float]         # By lag horizon
    betas: dict[int, float]
    t_stats: dict[int, float]
    effect_size_bps: float
    sign_consistency_ratio: float          # Stability metrics
    beta_cv: float
    n_windows: int
    timestamp: str
    config: SuitabilityConfig
```  

---

## 6. Governance Integration

**Registry Pattern:** Class-based with mutable state.

**Lifecycle:**

```python
from aponyx.config import SUITABILITY_REGISTRY_PATH
from aponyx.evaluation.suitability import SuitabilityRegistry, evaluate_signal_suitability

# 1. LOAD: Instantiate registry
registry = SuitabilityRegistry(SUITABILITY_REGISTRY_PATH)

# 2. EVALUATE: Run suitability check
result = evaluate_signal_suitability(signal, target, config)

# 3. REGISTER: Store evaluation metadata
eval_id = registry.register_evaluation(
    suitability_result=result,
    signal_id="cdx_etf_basis",
    product_id="cdx_ig_5y",
    report_path=report_path,
)

# 4. QUERY: Retrieve evaluations
all_evals = registry.list_evaluations()
cdx_evals = registry.list_evaluations(signal_id="cdx_etf_basis")
passed = registry.list_evaluations(decision="PASS")

# 5. SAVE: Auto-saves on register
registry.save_catalog()  # Manual save also available
```

**Metadata Schema:**

```json
{
    "evaluation_id": "eval_20251113_143022_a1b2c3",
    "signal_id": "cdx_etf_basis",
    "product_id": "cdx_ig_5y",
    "timestamp": "2025-11-13T14:30:22",
    "decision": "PASS",
    "composite_score": 0.78,
    "component_scores": {
        "data_health": 0.85,
        "predictive": 0.82,
        "economic": 0.70,
        "stability": 1.0
    },
    "stability_metrics": {
        "sign_consistency_ratio": 0.95,
        "beta_cv": 0.25,
        "n_windows": 475
    },
    "report_path": "data/workflows/cdx_etf_basis_balanced_20251113_120000/reports/cdx_etf_basis_cdx_ig_5y_20251113.md",
    "config": {
        "lags": [1, 3, 5],
        "rolling_window": 252,
        "pass_threshold": 0.7,
        "hold_threshold": 0.4
    }
}
```

---

## 7. Workflow Integration

**Research Sequence:**

```
1. Data → Signal Generation
   ↓
2. Suitability Evaluation
   - Produces: SuitabilityResult + Markdown report
   - Registry: Stores evaluation metadata
   ↓
3. Decision Gate
   - PASS → Proceed to strategy design
   - HOLD → Review marginal components
   - FAIL → Archive signal
   ↓
4. Backtest (PASS only)
   ↓
5. Performance Analysis
```

**Batch Evaluation:**

```python
# Evaluate all signals against a product
from aponyx.models import SignalRegistry, compute_registered_signals
from aponyx.evaluation.suitability import evaluate_signal_suitability

signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
market_data = {"cdx": cdx_df, "etf": etf_df, "vix": vix_df}
signals = compute_registered_signals(signal_registry, market_data, signal_config)

for signal_name, signal_series in signals.items():
    result = evaluate_signal_suitability(signal_series, cdx_df['spread'])
    if result.decision == "PASS":
        # Proceed to backtest
        pass
```

---

## 8. Design Rationale

**Why Four Components?**

- **Data Health:** Foundation check prevents garbage-in-garbage-out  
- **Predictive:** Core criterion for signal validity  
- **Economic:** Bridges statistics to trading reality  
- **Stability:** Guards against overfitting and regime dependence

**Why These Weights?**

- Predictive credibility (0.40) is doubled because statistical significance is the primary screening criterion  
- Other components (0.20 each) are equally important secondary checks

**Why Rolling Window for Stability?**

- Rolling statistics capture regime transitions better than fixed temporal splits  
- Provides continuous stability metrics rather than discrete subperiod comparisons  
- Default window of 252 observations (~1 year for daily data) balances statistical power with regime sensitivity  
- Minimum window of 50 observations ensures reliable beta estimation per window
- Dual-metric approach (sign consistency + coefficient of variation) captures both directional stability and magnitude consistency  
- Sign consistency ratio ≥ 0.8 indicates persistent directional relationship across regimes  
- Beta CV < 0.5 indicates stable effect size (low magnitude variation)

**Why Multi-Horizon Testing?**

- Different strategies may use different holding periods  
- Signal should be robust across reasonable trading horizons  
- Reduces risk of overfitting to single lag specification

---

**Document Status:** Active design specification for `aponyx.evaluation.suitability` layer.  
**Last Updated:** December 2025  
**Maintainer:** stabilefrisur

