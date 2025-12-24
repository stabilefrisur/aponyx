"""
Markdown report generation for suitability evaluation results.

Generates human-readable reports with evaluation metrics, scores,
and interpretation guidance.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from scipy import stats

from aponyx.evaluation.suitability.evaluator import SuitabilityResult

logger = logging.getLogger(__name__)


def _compute_pvalue(t_stat: float, n_obs: int) -> float:
    """Compute two-tailed p-value from t-statistic."""
    df = max(n_obs - 2, 1)  # Degrees of freedom for simple regression
    return 2 * (1 - stats.t.cdf(abs(t_stat), df))


def _score_to_label(score: float) -> str:
    """Convert numeric score to interpretation label."""
    if score >= 0.8:
        return "Excellent"
    elif score >= 0.7:
        return "Strong"
    elif score >= 0.5:
        return "Moderate"
    elif score >= 0.3:
        return "Weak"
    else:
        return "Low"


def generate_suitability_report(
    result: SuitabilityResult,
    signal_id: str,
    product_id: str,
    indicator_metadata: dict[str, Any] | None = None,
    date_range: tuple[str, str] | None = None,
) -> str:
    """
    Generate Markdown report from evaluation result.

    Parameters
    ----------
    result : SuitabilityResult
        Evaluation result to document.
    signal_id : str
        Signal identifier (for header).
    product_id : str
        Product identifier matching security_id format (e.g., 'cdx_ig_5y').
    indicator_metadata : dict[str, Any] or None, optional
        Indicator configuration metadata to include in report.
        Keys: name, description, output_units, lookback, compute_function_name, securities.
    date_range : tuple[str, str] or None, optional
        Date range tuple (start_date, end_date) for data summary section.

    Returns
    -------
    str
        Formatted Markdown report.

    Notes
    -----
    Report structure:
    - Header with indicator, product, evaluation date
    - Configuration Summary (indicator parameters, data summary)
    - Evaluation Results (component scores table)
    - Detailed Component Analysis (4 components with metrics)
    - Footer with methodology link

    Examples
    --------
    >>> report = generate_suitability_report(result, "cdx_etf_basis", "cdx_ig_5y")
    >>> print(report[:100])
    """
    # Component interpretations
    data_health_interp = _interpret_data_health(result)
    predictive_interp = _interpret_predictive(result)
    economic_interp = _interpret_economic(result)
    stability_interp = _interpret_stability(result)

    # Format timestamp for display (just date portion)
    eval_date = result.timestamp.split("T")[0] if "T" in result.timestamp else result.timestamp

    # Build Configuration Summary section
    config_section = """---

## Configuration Summary

### Indicator Parameters

| Parameter | Value |
|-----------|-------|
"""
    if indicator_metadata:
        securities = indicator_metadata.get("securities", [])
        securities_str = ", ".join(securities) if securities else "N/A"
        config_section += f"""| Name | {indicator_metadata.get('name', signal_id)} |
| Description | {indicator_metadata.get('description', 'N/A')} |
| Output Units | {indicator_metadata.get('output_units', 'N/A')} |
| Lookback Period | {indicator_metadata.get('lookback', 'N/A')} days |
| Computation Method | {indicator_metadata.get('compute_function_name', 'N/A')} |
| Securities Used | {securities_str} |
"""
    else:
        config_section += f"""| Name | {signal_id} |
| Description | N/A |
| Output Units | N/A |
| Lookback Period | N/A |
| Computation Method | N/A |
| Securities Used | N/A |
"""

    # Data Summary section
    if date_range:
        date_range_str = f"{date_range[0]} to {date_range[1]}"
    else:
        date_range_str = "N/A"

    config_section += f"""
### Data Summary

| Metric | Value |
|--------|-------|
| Valid Observations | {result.valid_obs:,} |
| Date Range | {date_range_str} |
| Missing Data | {result.missing_pct:.2f}% |

"""

    # Build report header
    report = f"""# Indicator Suitability Evaluation Report

**Indicator:** `{signal_id}`  
**Product:** `{product_id}`  
**Evaluation Date:** {eval_date}

{config_section}---

## Evaluation Results

### Component Scores

| Component | Weight | Score | Contribution | Interpretation |
|-----------|--------|-------|--------------|----------------|
| Data Health | {result.config.data_health_weight * 100:.0f}% | {result.data_health_score:.2f} | {result.config.data_health_weight * result.data_health_score:.2f} | {_score_to_label(result.data_health_score)} |
| Predictive Association | {result.config.predictive_weight * 100:.0f}% | {result.predictive_score:.2f} | {result.config.predictive_weight * result.predictive_score:.2f} | {_score_to_label(result.predictive_score)} |
| Economic Relevance | {result.config.economic_weight * 100:.0f}% | {result.economic_score:.2f} | {result.config.economic_weight * result.economic_score:.2f} | {_score_to_label(result.economic_score)} |
| Temporal Stability | {result.config.stability_weight * 100:.0f}% | {result.stability_score:.2f} | {result.config.stability_weight * result.stability_score:.2f} | {_score_to_label(result.stability_score)} |
| **Composite** | **100%** | **—** | **{result.composite_score:.2f}** | **{_score_to_label(result.composite_score)}** |

---

## Detailed Component Analysis

### 1. Data Health Score: {result.data_health_score:.2f}

**Metrics:**
- Valid Observations: {result.valid_obs:,}
- Missing Data: {result.missing_pct:.2f}%

**Interpretation:**  
{data_health_interp}

---

### 2. Predictive Association Score: {result.predictive_score:.2f}

**Metrics:**

| Lag | Correlation | Beta | T-Statistic | P-Value |
|-----|-------------|------|-------------|---------|
"""

    # Add stats for each lag
    for lag in sorted(result.correlations.keys()):
        corr = result.correlations.get(lag, 0.0)
        beta = result.betas.get(lag, 0.0)
        tstat = result.t_stats.get(lag, 0.0)
        pval = _compute_pvalue(tstat, result.valid_obs)
        report += f"| {lag} | {corr:.2f} | {beta:.2f} | {tstat:.2f} | {pval:.2f} |\n"

    report += f"""
**Interpretation:**  
{predictive_interp}

---

### 3. Economic Relevance Score: {result.economic_score:.2f}

**Metrics:**
- Effect Size: {result.effect_size_bps:.2f} bps per 1σ signal change

**Interpretation:**  
{economic_interp}

---

### 4. Temporal Stability Score: {result.stability_score:.2f}

**Metrics:**
- Rolling Windows: {result.n_windows} windows ({result.config.rolling_window} observations each)
- Sign Consistency Ratio: {result.sign_consistency_ratio * 100:.2f}%
- Beta Coefficient of Variation: {result.beta_cv:.2f}

**Interpretation:**  
{stability_interp}

---

*This report was auto-generated from suitability evaluation results. For questions about methodology, see [signal_suitability_design.md](../../../../src/aponyx/docs/signal_suitability_design.md).*
"""

    logger.debug(
        "Generated report for %s/%s: %d characters",
        signal_id,
        product_id,
        len(report),
    )

    return report


def _interpret_data_health(result: SuitabilityResult) -> str:
    """Generate interpretation text for data health component."""
    if result.data_health_score >= 0.8:
        return (
            "Excellent data quality with sufficient observations and minimal missing data. "
            "Sample size supports reliable statistical inference."
        )
    elif result.data_health_score >= 0.5:
        return (
            "Acceptable data quality with some missing data. "
            "Results should be interpreted with awareness of data limitations."
        )
    else:
        return (
            "Data quality concerns due to insufficient observations or high missing data rate. "
            "Results may not be reliable. Consider gathering more data."
        )


def _interpret_predictive(result: SuitabilityResult) -> str:
    """Generate interpretation text for predictive component."""
    mean_abs_tstat = (
        sum(abs(t) for t in result.t_stats.values()) / len(result.t_stats)
        if result.t_stats
        else 0.0
    )

    if mean_abs_tstat >= 3.0:
        return (
            "Strong statistical evidence of predictive relationship. "
            "T-statistics exceed conventional significance thresholds with high confidence."
        )
    elif mean_abs_tstat >= 2.0:
        return (
            "Statistically significant predictive relationship at conventional levels (95% confidence). "
            "Signal contains meaningful information about target movements."
        )
    elif mean_abs_tstat >= 1.5:
        return (
            "Weak but detectable statistical relationship. "
            "Signal may contain information, but evidence is marginal."
        )
    else:
        return (
            "No statistically significant predictive relationship detected. "
            "Signal appears uncorrelated with target movements."
        )


def _interpret_economic(result: SuitabilityResult) -> str:
    """Generate interpretation text for economic component."""
    if result.effect_size_bps >= 2.0:
        return (
            "Economically meaningful effect size. "
            "A 1σ signal move is associated with substantial spread changes that could generate "
            "attractive risk-adjusted returns after costs."
        )
    elif result.effect_size_bps >= 0.5:
        return (
            "Moderate economic impact. "
            "Effect size is detectable but may be marginal after transaction costs. "
            "Careful strategy design required."
        )
    else:
        return (
            "Negligible economic impact. "
            "Even if statistically significant, the effect size is too small to generate "
            "meaningful P&L after realistic transaction costs."
        )


def _interpret_stability(result: SuitabilityResult) -> str:
    """Generate interpretation text for stability component."""
    sign_ratio = result.sign_consistency_ratio
    cv = result.beta_cv
    n_windows = result.n_windows

    # Interpret sign consistency
    if sign_ratio >= 0.8:
        sign_interp = "highly consistent"
    elif sign_ratio >= 0.6:
        sign_interp = "moderately consistent"
    else:
        sign_interp = "inconsistent"

    # Interpret magnitude stability
    if cv < 0.5:
        mag_interp = "stable magnitude"
    elif cv < 1.0:
        mag_interp = "moderate variation"
    else:
        mag_interp = "high variation"

    # Overall interpretation
    if result.stability_score >= 0.8:
        overall = (
            f"Excellent temporal stability ({sign_interp} sign, {mag_interp}). "
            f"The predictive relationship maintains consistent direction and magnitude "
            f"across {n_windows} rolling windows, indicating robustness across different market regimes."
        )
    elif result.stability_score >= 0.5:
        overall = (
            f"Moderate temporal stability ({sign_interp} sign, {mag_interp}). "
            f"The relationship shows some consistency but exhibits regime-dependent behavior. "
            f"Consider investigating the source of variation before strategy design."
        )
    else:
        overall = (
            f"Low temporal stability ({sign_interp} sign, {mag_interp}). "
            f"The predictive relationship is unstable across time, suggesting strong regime "
            f"dependence or non-stationarity. Use caution when designing strategies."
        )

    return overall


def save_report(
    report: str,
    output_dir: Path,
    timestamp: str | None = None,
) -> Path:
    """
    Save report to Markdown file.

    Parameters
    ----------
    report : str
        Markdown report text.
    output_dir : Path
        Directory to save report.
    timestamp : str or None, optional
        Timestamp string (YYYYMMDD_HHMMSS). If None, generates new timestamp.

    Returns
    -------
    Path
        Path to saved report file.

    Notes
    -----
    Filename format: suitability_evaluation_{YYYYMMDD_HHMMSS}.md
    Creates output directory if it doesn't exist.

    Examples
    --------
    >>> from aponyx.config import EVALUATION_DIR
    >>> path = save_report(report, EVALUATION_DIR)
    >>> print(path)
    """
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate or use provided timestamp
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"suitability_evaluation_{timestamp}.md"
    output_path = output_dir / filename

    # Write report
    output_path.write_text(report, encoding="utf-8")

    logger.info("Saved report to %s", output_path)

    return output_path
