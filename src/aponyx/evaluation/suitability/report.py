"""
Markdown report generation for suitability evaluation results.

Generates human-readable reports with evaluation metrics, scores,
and interpretation guidance.
"""

import logging
from datetime import datetime
from pathlib import Path

from aponyx.evaluation.suitability.evaluator import SuitabilityResult

logger = logging.getLogger(__name__)


def generate_suitability_report(
    result: SuitabilityResult,
    signal_id: str,
    product_id: str,
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

    Returns
    -------
    str
        Formatted Markdown report.

    Notes
    -----
    Report includes:
    - Header with identifiers and overall decision
    - Executive summary with composite score
    - Four component sections with metrics and interpretation
    - Composite scoring breakdown
    - Decision explanation and next steps
    - Footer with metadata

    Examples
    --------
    >>> report = generate_suitability_report(result, "cdx_etf_basis", "cdx_ig_5y")
    >>> print(report[:100])
    """
    # Decision indicator
    if result.decision == "PASS":
        indicator = "✅ PASS"
    elif result.decision == "HOLD":
        indicator = "⚠️ HOLD"
    else:
        indicator = "❌ FAIL"

    # Interpretation text for composite score
    if result.composite_score >= 0.7:
        interpretation = (
            "The signal demonstrates strong predictive content with good data quality. "
            "Proceed to strategy design and backtesting."
        )
    elif result.composite_score >= 0.4:
        interpretation = (
            "The signal shows marginal predictive content. "
            "Consider refining signal construction or gathering more data before backtesting. "
            "Manual review recommended."
        )
    else:
        interpretation = (
            "The signal lacks sufficient predictive content for this product. "
            "Do not proceed to backtesting. Consider alternative signal specifications."
        )

    # Component interpretations
    data_health_interp = _interpret_data_health(result)
    predictive_interp = _interpret_predictive(result)
    economic_interp = _interpret_economic(result)
    stability_interp = _interpret_stability(result)

    # Build report
    report = f"""# Signal-Product Suitability Evaluation Report

**Signal:** `{signal_id}`  
**Product:** `{product_id}`  
**Evaluation Date:** {result.timestamp}  
**Evaluator Version:** 0.1.0

---

## Executive Summary

### Overall Decision: {indicator}

**Composite Score:** {result.composite_score:.3f}

{interpretation}

---

## Component Analysis

### 1. Data Health Score: {result.data_health_score:.3f}

**Metrics:**
- Valid Observations: {result.valid_obs:,}
- Missing Data: {result.missing_pct:.2f}%

**Interpretation:**  
{data_health_interp}

---

### 2. Predictive Association Score: {result.predictive_score:.3f}

**Metrics:**

| Lag | Correlation | Beta | T-Statistic |
|-----|-------------|------|-------------|
"""

    # Add stats for each lag
    for lag in sorted(result.correlations.keys()):
        corr = result.correlations.get(lag, 0.0)
        beta = result.betas.get(lag, 0.0)
        tstat = result.t_stats.get(lag, 0.0)
        report += f"| {lag} | {corr:.4f} | {beta:.4f} | {tstat:.4f} |\n"

    report += f"""
**Interpretation:**  
{predictive_interp}

---

### 3. Economic Relevance Score: {result.economic_score:.3f}

**Metrics:**
- Effect Size: {result.effect_size_bps:.3f} bps per 1σ signal change

**Interpretation:**  
{economic_interp}

---

### 4. Temporal Stability Score: {result.stability_score:.3f}

**Metrics:**
- Subperiod Betas: {', '.join(f'{b:.4f}' for b in result.subperiod_betas)}
- Sign Consistent: {'Yes' if result.stability_score > 0.5 else 'No'}

**Interpretation:**  
{stability_interp}

---

## Composite Scoring

| Component | Weight | Score | Contribution |
|-----------|--------|-------|--------------|
| Data Health | {result.config.data_health_weight:.2f} | {result.data_health_score:.3f} | {result.config.data_health_weight * result.data_health_score:.3f} |
| Predictive | {result.config.predictive_weight:.2f} | {result.predictive_score:.3f} | {result.config.predictive_weight * result.predictive_score:.3f} |
| Economic | {result.config.economic_weight:.2f} | {result.economic_score:.3f} | {result.config.economic_weight * result.economic_score:.3f} |
| Stability | {result.config.stability_weight:.2f} | {result.stability_score:.3f} | {result.config.stability_weight * result.stability_score:.3f} |
| **Total** | **1.00** | — | **{result.composite_score:.3f}** |

---

## Decision Criteria

- **PASS** (≥ {result.config.pass_threshold:.2f}): Proceed to backtest
- **HOLD** ({result.config.hold_threshold:.2f} - {result.config.pass_threshold:.2f}): Marginal, requires judgment
- **FAIL** (< {result.config.hold_threshold:.2f}): Do not backtest

### Recommended Next Steps

"""

    if result.decision == "PASS":
        report += """1. Design trading strategy with entry/exit rules
2. Configure backtest parameters (position sizing, costs)
3. Run historical backtest with proper risk controls
4. Analyze performance metrics and risk-adjusted returns
"""
    elif result.decision == "HOLD":
        report += """1. Review component scores to identify weaknesses
2. Consider signal refinements (lookback periods, normalization)
3. Gather additional data if sample size is limited
4. Consult with senior researchers before proceeding
5. Document rationale for proceed/stop decision
"""
    else:
        report += """1. Archive evaluation for reference
2. Document why signal failed (data, predictive, economic, or stability)
3. Consider alternative signal specifications
4. Do NOT proceed to backtesting with current signal
"""

    report += f"""
---

## Report Metadata

**Generated:** {datetime.now().isoformat()}  
**Evaluator:** aponyx.evaluation.suitability v0.1.0  
**Reproducibility:** All metrics computed from aligned signal-target pairs with deterministic methods.

---

*This report was auto-generated from suitability evaluation results. For questions about methodology, see `docs/suitability_evaluation.md`.*
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
    if result.stability_score >= 0.9:
        return (
            "Excellent temporal stability. "
            "Predictive relationship maintains consistent sign across subperiods, "
            "indicating robustness across different market regimes."
        )
    else:
        return (
            "Temporal instability detected. "
            "Predictive relationship reversed sign in at least one subperiod, suggesting "
            "regime changes or non-stationarity. Use caution when designing strategies."
        )


def save_report(
    report: str,
    signal_id: str,
    product_id: str,
    output_dir: Path,
) -> Path:
    """
    Save report to Markdown file.

    Parameters
    ----------
    report : str
        Markdown report text.
    signal_id : str
        Signal identifier (for filename).
    product_id : str
        Product identifier matching security_id format (e.g., 'cdx_ig_5y').
    output_dir : Path
        Directory to save report.

    Returns
    -------
    Path
        Path to saved report file.

    Notes
    -----
    Filename format: {signal_id}_{product_id}_{YYYYMMDD_HHMMSS}.md
    Creates output directory if it doesn't exist.

    Examples
    --------
    >>> from aponyx.config import EVALUATION_DIR
    >>> path = save_report(report, "cdx_etf_basis", "cdx_ig_5y", EVALUATION_DIR)
    >>> print(path)
    """
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{signal_id}_{product_id}_{timestamp_str}.md"
    output_path = output_dir / filename

    # Write report
    output_path.write_text(report, encoding="utf-8")

    logger.info("Saved report to %s", output_path)

    return output_path
