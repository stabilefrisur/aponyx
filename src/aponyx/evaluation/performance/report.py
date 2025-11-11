"""
Markdown report generation for performance evaluation results.

Generates human-readable reports with performance metrics, attribution,
stability analysis, and interpretation guidance.
"""

import logging
from datetime import datetime
from pathlib import Path

from .config import PerformanceResult

logger = logging.getLogger(__name__)


def generate_performance_report(
    result: PerformanceResult,
    signal_id: str,
    strategy_id: str,
) -> str:
    """
    Generate Markdown report from performance evaluation result.

    Parameters
    ----------
    result : PerformanceResult
        Performance evaluation result to document.
    signal_id : str
        Signal identifier (for header).
    strategy_id : str
        Strategy identifier (for header).

    Returns
    -------
    str
        Formatted Markdown report.

    Notes
    -----
    Report includes:
    - Header with identifiers and stability score
    - Executive summary with key insights
    - Extended metrics section
    - Subperiod stability analysis
    - Return attribution breakdown
    - Recommendations
    - Footer with metadata

    Examples
    --------
    >>> report = generate_performance_report(result, "cdx_etf_basis", "simple_threshold")
    >>> print(report[:100])
    """
    # Stability indicator
    if result.stability_score >= 0.7:
        stability_indicator = "✅ Strong"
    elif result.stability_score >= 0.5:
        stability_indicator = "⚠️ Moderate"
    else:
        stability_indicator = "❌ Weak"

    # Extract key metrics (use dataclass field access)
    metrics = result.metrics
    subperiod = result.subperiod_analysis
    attribution = result.attribution

    # Build report
    report = f"""# Backtest Performance Evaluation Report

**Signal:** `{signal_id}`  
**Strategy:** `{strategy_id}`  
**Evaluation Date:** {result.timestamp}  
**Evaluator Version:** {result.metadata.get('evaluator_version', 'unknown')}

---

## Executive Summary

### Stability Assessment: {stability_indicator}

**Overall Stability Score:** {result.stability_score:.3f}

{result.summary}

---

## Basic Backtest Metrics

| Metric | Value |
|--------|-------|
| Total Return | ${metrics.total_return:,.2f} |
| Annualized Return | ${metrics.annualized_return:,.2f} |
| Sharpe Ratio | {metrics.sharpe_ratio:.3f} |
| Sortino Ratio | {metrics.sortino_ratio:.3f} |
| Max Drawdown | ${metrics.max_drawdown:,.2f} |
| Calmar Ratio | {metrics.calmar_ratio:.3f} |
| Annualized Volatility | ${metrics.annualized_volatility:,.2f} |

### Trade Statistics

| Metric | Value |
|--------|-------|
| Total Trades | {metrics.n_trades} |
| Hit Rate | {metrics.hit_rate:.1%} |
| Average Win | ${metrics.avg_win:,.2f} |
| Average Loss | ${metrics.avg_loss:,.2f} |
| Win/Loss Ratio | {metrics.win_loss_ratio:.3f} |
| Avg Holding Days | {metrics.avg_holding_days:.1f} |

---

## Extended Performance Metrics

### Risk-Adjusted Returns

| Metric | Value |
|--------|-------|
| Rolling Sharpe (Mean) | {metrics.rolling_sharpe_mean:.3f} |
| Rolling Sharpe (Std Dev) | {metrics.rolling_sharpe_std:.3f} |
| Profit Factor | {metrics.profit_factor:.3f} |
| Tail Ratio (95th pct) | {metrics.tail_ratio:.3f} |
| Consistency Score (21d) | {metrics.consistency_score:.1%} |

**Interpretation:**

"""

    # Add metric interpretations
    if metrics.profit_factor > 1.5:
        report += "- Strong profitability with gross wins substantially exceeding gross losses\n"
    elif metrics.profit_factor > 1.0:
        report += "- Positive profitability with gross wins exceeding gross losses\n"
    else:
        report += "- Weak profitability with gross losses approaching or exceeding gross wins\n"

    if metrics.tail_ratio > 1.2:
        report += "- Favorable tail asymmetry with larger upside than downside extremes\n"
    elif metrics.tail_ratio > 0.8:
        report += "- Balanced tail distribution with similar upside and downside extremes\n"
    else:
        report += "- Negative tail asymmetry with larger downside than upside extremes\n"

    if metrics.consistency_score > 0.6:
        report += "- High consistency with majority of rolling windows profitable\n"
    elif metrics.consistency_score > 0.4:
        report += "- Moderate consistency with mixed profitable/unprofitable periods\n"
    else:
        report += "- Low consistency with frequent unprofitable rolling windows\n"

    # Drawdown recovery
    max_dd_recovery = metrics.max_dd_recovery_days
    if max_dd_recovery == float("inf"):
        recovery_text = "Not recovered"
    else:
        recovery_text = f"{max_dd_recovery:.0f} days"

    report += f"""
### Drawdown Recovery

| Metric | Value |
|--------|-------|
| Max Drawdown Recovery | {recovery_text} |
| Average Recovery Time | {metrics.avg_recovery_days:.1f} days |
| Number of Drawdowns | {metrics.n_drawdowns} |

"""

    if max_dd_recovery == float("inf"):
        report += "**Warning:** Maximum drawdown has not been recovered as of backtest end date.\n"

    # Subperiod stability
    report += f"""
---

## Subperiod Stability Analysis

**Number of Subperiods:** {len(subperiod['subperiod_returns'])}  
**Profitable Periods:** {subperiod['positive_periods']}/{len(subperiod['subperiod_returns'])}  
**Consistency Rate:** {subperiod['consistency_rate']:.1%}

| Period | Return | Sharpe |
|--------|--------|--------|
"""

    for i, (ret, sharpe) in enumerate(
        zip(subperiod["subperiod_returns"], subperiod["subperiod_sharpes"]), 1
    ):
        report += f"| {i} | {ret:,.2f} | {sharpe:.3f} |\n"

    report += "\n**Interpretation:**\n\n"

    if subperiod["consistency_rate"] >= 0.75:
        report += (
            "Excellent temporal consistency with strong performance across most subperiods. "
            "Strategy appears robust to different market conditions.\n"
        )
    elif subperiod["consistency_rate"] >= 0.5:
        report += (
            "Moderate temporal consistency with mixed performance across subperiods. "
            "Performance may be regime-dependent.\n"
        )
    else:
        report += (
            "Weak temporal consistency with performance concentrated in few subperiods. "
            "Strategy may be vulnerable to regime changes or overfitted to specific conditions.\n"
        )

    # Return attribution
    direction = attribution["direction"]
    signal_strength = attribution["signal_strength"]
    win_loss = attribution["win_loss"]

    report += f"""
---

## Return Attribution

### Directional Attribution

| Direction | P&L | Contribution |
|-----------|-----|--------------|
| Long | {direction['long_pnl']:,.2f} | {direction['long_pct']:.1%} |
| Short | {direction['short_pnl']:,.2f} | {direction['short_pct']:.1%} |

"""

    if abs(direction["long_pct"]) > 0.7:
        bias = "long" if direction["long_pct"] > 0 else "short"
        report += f"**Strong {bias} bias** - Returns highly concentrated in {bias} positions.\n"
    else:
        report += (
            "**Balanced exposure** - Returns distributed across both long and short positions.\n"
        )

    report += "\n### Signal Strength Attribution\n\n"
    report += "| Quantile | P&L | Contribution |\n"
    report += "|----------|-----|--------------|\\n"

    n_quantiles = result.config.attribution_quantiles
    for i in range(1, n_quantiles + 1):
        pnl = signal_strength[f"q{i}_pnl"]
        pct = signal_strength[f"q{i}_pct"]
        report += f"| Q{i} | {pnl:,.2f} | {pct:.1%} |\n"

    report += "\n"

    # Check if highest quantile contributed most
    highest_q_pct = signal_strength[f"q{n_quantiles}_pct"]
    if highest_q_pct > 0.4:
        report += (
            "**Strong signal strength relationship** - Highest conviction signals contributed "
            f"most to returns ({highest_q_pct:.1%}).\n"
        )
    elif highest_q_pct < 0.2:
        report += (
            "**Weak signal strength relationship** - Returns not concentrated in highest "
            "conviction signals. Signal strength may not add value.\n"
        )
    else:
        report += "**Moderate signal strength relationship** - Mixed contribution across signal strengths.\n"

    report += f"""
### Win/Loss Decomposition

| Category | Amount | Contribution |
|----------|--------|--------------|
| Gross Wins | {win_loss['gross_wins']:,.2f} | {win_loss['win_contribution']:.1%} |
| Gross Losses | {win_loss['gross_losses']:,.2f} | {win_loss['loss_contribution']:.1%} |
| Net P&L | {win_loss['net_pnl']:,.2f} | — |

---

## Recommendations

"""

    # Generate recommendations based on metrics
    recommendations = []

    if result.stability_score < 0.5:
        recommendations.append(
            "⚠️ **Low stability score** - Review strategy robustness and consider regime filters"
        )

    if metrics.profit_factor < 1.0:
        recommendations.append(
            "❌ **Negative profit factor** - Strategy is unprofitable; do not deploy"
        )

    if subperiod["consistency_rate"] < 0.5:
        recommendations.append(
            "⚠️ **Low consistency** - Performance concentrated in few periods; assess regime dependency"
        )

    if max_dd_recovery == float("inf"):
        recommendations.append(
            "⚠️ **Unrecovered drawdown** - Current strategy underwater; reassess viability"
        )

    if metrics.tail_ratio < 0.8:
        recommendations.append(
            "⚠️ **Negative skew** - Downside risk exceeds upside potential; review risk controls"
        )

    if not recommendations:
        recommendations.append(
            "✅ **Performance acceptable** - Consider proceeding with further validation and stress testing"
        )
        recommendations.append(
            "Next steps: comparative analysis against alternative signals/strategies"
        )
        recommendations.append(
            "Recommended: transaction cost sensitivity analysis and regime-conditional performance review"
        )

    for rec in recommendations:
        report += f"{rec}\n\n"

    report += f"""
---

## Report Metadata

**Generated:** {datetime.now().isoformat()}  
**Evaluator:** aponyx.evaluation.performance  
**Configuration:**
- Minimum Observations: {result.config.min_obs}
- Subperiods: {result.config.n_subperiods}
- Rolling Window: {result.config.rolling_window} days
- Attribution Quantiles: {result.config.attribution_quantiles}

**Reproducibility:** All metrics computed from backtest P&L with deterministic methods.

---

*This report was auto-generated from performance evaluation results.*
"""

    logger.debug(
        "Generated performance report for %s/%s: %d characters",
        signal_id,
        strategy_id,
        len(report),
    )

    return report


def save_report(
    report: str,
    signal_id: str,
    strategy_id: str,
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
    strategy_id : str
        Strategy identifier (for filename).
    output_dir : Path
        Directory to save report.

    Returns
    -------
    Path
        Path to saved report file.

    Notes
    -----
    Filename format: {signal_id}_{strategy_id}_{YYYYMMDD_HHMMSS}.md
    Creates output directory if it doesn't exist.

    Examples
    --------
    >>> from aponyx.config import PERFORMANCE_REPORTS_DIR
    >>> path = save_report(report, "cdx_etf_basis", "simple_threshold", PERFORMANCE_REPORTS_DIR)
    >>> print(path)
    """
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{signal_id}_{strategy_id}_{timestamp_str}.md"
    output_path = output_dir / filename

    # Write report
    output_path.write_text(report, encoding="utf-8")

    logger.info("Saved performance report to %s", output_path)

    return output_path
