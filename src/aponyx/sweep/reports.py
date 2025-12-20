"""
Sweep analysis report generation.

Generates human-readable Markdown reports summarizing sweep results,
including swept parameters, top configurations, and metric statistics.
"""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from .config import ParameterOverride, SweepConfig
from .results import SweepResult, SweepSummary

logger = logging.getLogger(__name__)

# Metrics to display for each mode
INDICATOR_METRICS = [
    "composite_score",
    "data_health_score",
    "predictive_score",
    "economic_score",
    "stability_score",
    "effect_size_bps",
    "sign_consistency_ratio",
]

BACKTEST_METRICS = [
    "sharpe_ratio",
    "sortino_ratio",
    "calmar_ratio",
    "total_return",
    "annualized_return",
    "max_drawdown",
    "annualized_volatility",
    "hit_rate",
    "profit_factor",
    "n_trades",
]


def generate_sweep_report(result: SweepResult) -> str:
    """
    Generate a Markdown analysis report for sweep results.

    Parameters
    ----------
    result : SweepResult
        Complete sweep results including config, DataFrame, and summary.

    Returns
    -------
    str
        Markdown-formatted report content.

    Examples
    --------
    >>> report = generate_sweep_report(sweep_result)
    >>> print(report[:100])
    # Sweep Analysis Report: lookback_sensitivity
    """
    sections = [
        _generate_header(result.config, result.summary),
        _generate_parameters_section(result.config.parameters),
        _generate_summary_section(result.summary),
        _generate_top_results_section(result.results_df, result.config.mode),
        _generate_statistics_section(result.results_df, result.config.mode),
        _generate_parameter_sensitivity_section(
            result.results_df, result.config.parameters, result.config.mode
        ),
    ]

    return "\n\n".join(sections)


def save_sweep_report(result: SweepResult, output_dir: Path | None = None) -> Path:
    """
    Save the sweep analysis report to disk.

    Parameters
    ----------
    result : SweepResult
        Complete sweep results.
    output_dir : Path | None
        Output directory. Uses result.output_dir if None.

    Returns
    -------
    Path
        Path to the saved report file.

    Examples
    --------
    >>> report_path = save_sweep_report(sweep_result)
    >>> print(f"Report saved to: {report_path}")
    """
    if output_dir is None:
        output_dir = result.output_dir

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "sweep_analysis.md"

    report_content = generate_sweep_report(result)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    logger.info("Saved sweep report to: %s", report_path)
    return report_path


def _generate_header(config: SweepConfig, summary: SweepSummary) -> str:
    """Generate report header with title and description."""
    lines = [
        f"# Sweep Analysis Report: {config.name}",
        "",
        f"> {config.description}",
        "",
        f"**Mode:** {config.mode}  ",
        f"**Signal:** `{config.base.signal}`  ",
    ]

    if config.base.strategy:
        lines.append(f"**Strategy:** `{config.base.strategy}`  ")

    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)


def _generate_parameters_section(
    parameters: tuple[ParameterOverride, ...],
) -> str:
    """Generate swept parameters section."""
    lines = [
        "## Swept Parameters",
        "",
        "| Parameter Path | Values | Count |",
        "|----------------|--------|-------|",
    ]

    for param in parameters:
        display_path = _simplify_param_path(param.path)
        values_str = ", ".join(str(v) for v in param.values)
        lines.append(f"| `{display_path}` | {values_str} | {len(param.values)} |")

    # Calculate total combinations
    total = 1
    for p in parameters:
        total *= len(p.values)
    lines.extend(["", f"**Total combinations:** {total}"])

    return "\n".join(lines)


def _generate_summary_section(summary: SweepSummary) -> str:
    """Generate execution summary section."""
    lines = [
        "## Execution Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Start Time | {summary.start_time} |",
        f"| End Time | {summary.end_time} |",
        f"| Duration | {summary.duration_seconds:.2f}s |",
        f"| Total Combinations | {summary.total_combinations} |",
        f"| Successful | {summary.successful} |",
        f"| Failed | {summary.failed} |",
        f"| Success Rate | {summary.success_rate:.1%} |",
    ]

    return "\n".join(lines)


def _generate_top_results_section(
    results_df: pd.DataFrame,
    mode: str,
    limit: int = 10,
) -> str:
    """Generate top results section with ranking table."""
    # Filter successful results
    if "status" in results_df.columns:
        df = results_df[results_df["status"] == "success"].copy()
    else:
        df = results_df.copy()

    if df.empty:
        return "## Top Results\n\nNo successful results to display."

    # Determine sort column and metrics based on mode
    if mode == "indicator":
        sort_col = "composite_score"
        metrics = INDICATOR_METRICS
    else:
        sort_col = "sharpe_ratio"
        metrics = BACKTEST_METRICS

    # Filter to existing metrics
    metrics = [m for m in metrics if m in df.columns]

    if sort_col not in df.columns:
        return "## Top Results\n\nSort column not found in results."

    # Get parameter columns (contain dots in name)
    param_cols = [c for c in df.columns if "." in c]

    # Sort and get top results
    sorted_df = df.sort_values(sort_col, ascending=False).head(limit)

    lines = [
        f"## Top {min(limit, len(sorted_df))} Results (by {sort_col})",
        "",
    ]

    # Build header with simplified param names
    display_param_cols = [_simplify_param_path(c) for c in param_cols]
    header_cols = ["Rank"] + display_param_cols + metrics
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "|".join(["---"] * len(header_cols)) + "|")

    # Build rows
    for rank, (_, row) in enumerate(sorted_df.iterrows(), start=1):
        row_values = [str(rank)]

        # Parameter values
        for col in param_cols:
            val = row[col]
            if isinstance(val, float):
                row_values.append(f"{val:.2f}")
            else:
                row_values.append(str(val))

        # Metric values
        for col in metrics:
            val = row[col]
            if pd.isna(val):
                row_values.append("N/A")
            elif isinstance(val, float):
                if abs(val) < 0.01:
                    row_values.append(f"{val:.4f}")
                elif abs(val) >= 1000:
                    row_values.append(f"{val:.0f}")
                else:
                    row_values.append(f"{val:.3f}")
            else:
                row_values.append(str(val))

        lines.append("| " + " | ".join(row_values) + " |")

    return "\n".join(lines)


def _generate_statistics_section(
    results_df: pd.DataFrame,
    mode: str,
) -> str:
    """Generate summary statistics for key metrics."""
    if "status" in results_df.columns:
        df = results_df[results_df["status"] == "success"].copy()
    else:
        df = results_df.copy()

    if df.empty:
        return "## Metric Statistics\n\nNo successful results for statistics."

    metrics = INDICATOR_METRICS if mode == "indicator" else BACKTEST_METRICS
    metrics = [m for m in metrics if m in df.columns]

    if not metrics:
        return "## Metric Statistics\n\nNo metrics available."

    lines = [
        "## Metric Statistics",
        "",
        "| Metric | Mean | Std | Min | Max |",
        "|--------|------|-----|-----|-----|",
    ]

    for metric in metrics:
        if df[metric].dtype in ["float64", "int64", float, int]:
            mean_val = df[metric].mean()
            std_val = df[metric].std()
            min_val = df[metric].min()
            max_val = df[metric].max()

            lines.append(
                f"| {metric} | {_format_stat(mean_val)} | "
                f"{_format_stat(std_val)} | {_format_stat(min_val)} | "
                f"{_format_stat(max_val)} |"
            )

    return "\n".join(lines)


def _simplify_param_path(path: str) -> str:
    """Simplify parameter path for display by removing '.parameters.' suffix."""
    return path.replace(".parameters.", ".")


def _generate_parameter_sensitivity_section(
    results_df: pd.DataFrame,
    parameters: tuple[ParameterOverride, ...],
    mode: str,
) -> str:
    """Generate parameter sensitivity analysis."""
    if "status" in results_df.columns:
        df = results_df[results_df["status"] == "success"].copy()
    else:
        df = results_df.copy()

    if df.empty:
        return "## Parameter Sensitivity\n\nNo successful results for analysis."

    # Select metrics based on mode
    metrics = INDICATOR_METRICS if mode == "indicator" else BACKTEST_METRICS
    available_metrics = [m for m in metrics if m in df.columns]

    if not available_metrics:
        return "## Parameter Sensitivity\n\nNo metrics found for analysis."

    lines = [
        "## Parameter Sensitivity",
        "",
        "Mean metric values by parameter value:",
        "",
    ]

    for param in parameters:
        if param.path not in df.columns:
            continue

        display_path = _simplify_param_path(param.path)
        lines.append(f"### `{display_path}`")
        lines.append("")

        # Build header row
        header = "| Value | Count |"
        separator = "|-------|-------|"
        for metric in available_metrics:
            header += f" {metric} |"
            separator += "------|"
        lines.append(header)
        lines.append(separator)

        # Group by parameter value and compute mean for all metrics
        grouped = df.groupby(param.path)[available_metrics].mean()
        counts = df.groupby(param.path).size()
        grouped = grouped.sort_index()

        for value in grouped.index:
            row_str = f"| {value} | {counts[value]} |"
            for metric in available_metrics:
                row_str += f" {_format_stat(grouped.loc[value, metric])} |"
            lines.append(row_str)

        lines.append("")

    return "\n".join(lines)


def _format_stat(value: float | int) -> str:
    """Format a statistic value for display."""
    if pd.isna(value):
        return "N/A"
    if isinstance(value, float):
        if abs(value) < 0.01:
            return f"{value:.4f}"
        elif abs(value) >= 1000:
            return f"{value:.0f}"
        else:
            return f"{value:.3f}"
    return str(value)
