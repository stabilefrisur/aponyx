"""
Report generation logic for workflow results.

Aggregates metrics, charts, and analysis into formatted reports
for console output, markdown files, or HTML documents.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from aponyx.config import DATA_WORKFLOWS_DIR

logger = logging.getLogger(__name__)


class ReportFormat(str, Enum):
    """Report output format options."""

    CONSOLE = "console"
    MARKDOWN = "markdown"
    HTML = "html"


@dataclass
class ReportData:
    """
    Aggregated data for report generation.

    Attributes
    ----------
    workflow_dir : Path
        Workflow output directory path.
    label : str
        Workflow label.
    signal_name : str
        Signal identifier.
    strategy_name : str
        Strategy identifier.
    suitability_report : str | None
        Suitability evaluation report content.
    performance_report : str | None
        Performance analysis report content.
    has_visualizations : bool
        Whether visualization files exist.
    """

    workflow_dir: Path
    label: str
    signal_name: str
    strategy_name: str
    suitability_report: str | None = None
    performance_report: str | None = None
    has_visualizations: bool = False


def generate_report(
    workflow_dir: Path,
    format: ReportFormat | str = ReportFormat.CONSOLE,
    output_path: Path | None = None,
) -> str:
    """
    Generate comprehensive research report from workflow results.

    Aggregates suitability evaluation, performance metrics, and visualization
    references into a unified report document.

    Parameters
    ----------
    workflow_dir : Path
        Workflow output directory containing metadata.json and reports.
    format : ReportFormat or str
        Output format (console, markdown, or html).
    output_path : Path, optional
        Custom output file path. If None and format is not console,
        saves to default location in reports directory.

    Returns
    -------
    str
        Generated report content.

    Raises
    ------
    FileNotFoundError
        If workflow directory or required reports not found.

    Examples
    --------
    Generate console report:
        >>> from pathlib import Path
        >>> workflow_dir = Path("data/workflows/my_test_20241202_120000")
        >>> report = generate_report(workflow_dir)
        >>> print(report)

    Generate markdown file:
        >>> report = generate_report(
        ...     workflow_dir,
        ...     format="markdown",
        ...     output_path=Path("my_report.md"),
        ... )
    """
    # Convert string to enum if needed
    if isinstance(format, str):
        format = ReportFormat(format.lower())

    # Validate workflow directory exists
    if not workflow_dir.exists():
        raise FileNotFoundError(f"Workflow directory not found: {workflow_dir}")

    # Load metadata
    metadata_path = workflow_dir / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata not found in workflow directory: {workflow_dir}"
        )

    import json

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    label = metadata.get("label", "unknown")
    signal_name = metadata.get("signal", "unknown")
    strategy_name = metadata.get("strategy", "unknown")

    logger.info(
        "Generating %s report: workflow=%s (signal=%s, strategy=%s)",
        format.value,
        label,
        signal_name,
        strategy_name,
    )

    # Collect report data
    data = _collect_report_data(workflow_dir, label, signal_name, strategy_name)

    # Generate report based on format
    if format == ReportFormat.CONSOLE:
        content = _generate_console_report(data)
    elif format == ReportFormat.MARKDOWN:
        content = _generate_markdown_report(data)
    else:  # HTML
        content = _generate_html_report(data)

    # Save to file if not console
    if format != ReportFormat.CONSOLE:
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{label}_{timestamp}.{_get_extension(format)}"
            # Save aggregated reports to .reports subdirectory in workflows
            output_path = DATA_WORKFLOWS_DIR / ".reports" / filename

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        logger.info("Report saved: %s", output_path)

    return content


def _collect_report_data(
    workflow_dir: Path,
    label: str,
    signal_name: str,
    strategy_name: str,
) -> ReportData:
    """
    Collect workflow results for report generation.

    Parameters
    ----------
    workflow_dir : Path
        Workflow output directory.
    label : str
        Workflow label.
    signal_name : str
        Signal identifier.
    strategy_name : str
        Strategy identifier.

    Returns
    -------
    ReportData
        Aggregated report data.

    Raises
    ------
    FileNotFoundError
        If required workflow results not found.
    """
    data = ReportData(
        workflow_dir=workflow_dir,
        label=label,
        signal_name=signal_name,
        strategy_name=strategy_name,
    )

    logger.debug("Loading reports from workflow directory: %s", workflow_dir.name)

    logger.debug("Loading reports from workflow directory: %s", workflow_dir.name)

    # Load reports from reports/ subdirectory
    reports_dir = workflow_dir / "reports"
    if reports_dir.exists():
        # Load suitability report (filename pattern: suitability_evaluation_{timestamp}.md)
        suitability_files = list(reports_dir.glob("suitability_evaluation_*.md"))
        if suitability_files:
            suitability_file = sorted(suitability_files)[-1]
            data.suitability_report = suitability_file.read_text(encoding="utf-8")
            logger.debug("Loaded suitability report: %s", suitability_file.name)

        # Load performance report (filename pattern: performance_analysis_{timestamp}.md)
        performance_files = list(reports_dir.glob("performance_analysis_*.md"))
        if performance_files:
            performance_file = sorted(performance_files)[-1]
            data.performance_report = performance_file.read_text(encoding="utf-8")
            logger.debug("Loaded performance report: %s", performance_file.name)

    # Check for visualizations
    viz_dir = workflow_dir / "visualizations"
    data.has_visualizations = viz_dir.exists() and any(viz_dir.glob("*.html"))

    # Validate that we have some results
    if not (data.suitability_report or data.performance_report):
        raise FileNotFoundError(
            f"No reports found in workflow directory {workflow_dir}. "
            f"Run workflow with all steps enabled."
        )

    return data


def _generate_console_report(data: ReportData) -> str:
    """Generate console-friendly report."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"Research Report: {data.label}")
    lines.append(f"Signal: {data.signal_name} | Strategy: {data.strategy_name}")
    lines.append("=" * 80)
    lines.append("")

    # Suitability section
    if data.suitability_report:
        lines.append("SUITABILITY EVALUATION")
        lines.append("-" * 80)
        # Extract key metrics from markdown (simplified)
        lines.append(_extract_console_summary(data.suitability_report))
        lines.append("")

    # Performance section
    if data.performance_report:
        lines.append("PERFORMANCE ANALYSIS")
        lines.append("-" * 80)
        lines.append(_extract_console_summary(data.performance_report))
        lines.append("")

    # Visualizations
    if data.has_visualizations:
        lines.append("VISUALIZATIONS")
        lines.append("-" * 80)
        viz_dir = data.workflow_dir / "visualizations"
        for viz_file in sorted(viz_dir.glob("*.html")):
            lines.append(f"  • {viz_file.name}: {viz_file}")
        lines.append("")

    # Workflow info
    lines.append("WORKFLOW OUTPUT")
    lines.append("-" * 80)
    lines.append(f"  Directory: {data.workflow_dir}")
    lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def _generate_markdown_report(data: ReportData) -> str:
    """Generate markdown report."""
    lines = []
    lines.append(f"# Research Report: {data.label}")
    lines.append("")
    lines.append(f"**Signal:** {data.signal_name} | **Strategy:** {data.strategy_name}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Suitability section
    if data.suitability_report:
        lines.append("## Suitability Evaluation")
        lines.append("")
        lines.append(data.suitability_report)
        lines.append("")

    # Performance section
    if data.performance_report:
        lines.append("## Performance Analysis")
        lines.append("")
        lines.append(data.performance_report)
        lines.append("")

    # Visualizations
    if data.has_visualizations:
        lines.append("## Visualizations")
        lines.append("")
        viz_dir = data.workflow_dir / "visualizations"
        for viz_file in sorted(viz_dir.glob("*.html")):
            lines.append(f"- [{viz_file.stem}]({viz_file.resolve().as_uri()})")
        lines.append("")

    # Workflow info
    lines.append("## Workflow Details")
    lines.append("")
    lines.append(f"**Output Directory:** `{data.workflow_dir}`")
    lines.append("")

    return "\n".join(lines)


def _generate_html_report(data: ReportData) -> str:
    """Generate HTML report."""
    html_parts = []

    # HTML header
    html_parts.append("<!DOCTYPE html>")
    html_parts.append('<html lang="en">')
    html_parts.append("<head>")
    html_parts.append('    <meta charset="UTF-8">')
    html_parts.append(
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">'
    )
    html_parts.append(f"    <title>Research Report: {data.label}</title>")
    html_parts.append("    <style>")
    html_parts.append(
        "        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 40px auto; padding: 0 20px; line-height: 1.6; }"
    )
    html_parts.append(
        "        h1 { border-bottom: 3px solid #333; padding-bottom: 10px; }"
    )
    html_parts.append(
        "        h2 { border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-top: 40px; }"
    )
    html_parts.append(
        "        .metadata { color: #666; font-size: 0.9em; margin-bottom: 30px; }"
    )
    html_parts.append(
        "        pre { background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }"
    )
    html_parts.append(
        "        table { border-collapse: collapse; width: 100%; margin: 20px 0; }"
    )
    html_parts.append(
        "        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }"
    )
    html_parts.append("        th { background-color: #f2f2f2; }")
    html_parts.append("    </style>")
    html_parts.append("</head>")
    html_parts.append("<body>")

    # Title
    html_parts.append(f"    <h1>Research Report: {data.label}</h1>")
    html_parts.append(
        f'    <div class="metadata">Signal: {data.signal_name} | Strategy: {data.strategy_name}</div>'
    )
    html_parts.append(
        f'    <div class="metadata">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>'
    )

    # Suitability section
    if data.suitability_report:
        html_parts.append("    <h2>Suitability Evaluation</h2>")
        html_parts.append(_markdown_to_html(data.suitability_report))

    # Performance section
    if data.performance_report:
        html_parts.append("    <h2>Performance Analysis</h2>")
        html_parts.append(_markdown_to_html(data.performance_report))

    # Visualizations
    if data.has_visualizations:
        html_parts.append("    <h2>Visualizations</h2>")
        html_parts.append("    <ul>")
        viz_dir = data.workflow_dir / "visualizations"
        for viz_file in sorted(viz_dir.glob("*.html")):
            html_parts.append(
                f'        <li><a href="{viz_file.resolve().as_uri()}" target="_blank">{viz_file.stem}</a></li>'
            )
        html_parts.append("    </ul>")

    # Workflow info
    html_parts.append("    <h2>Workflow Details</h2>")
    html_parts.append(
        f"    <p><strong>Output Directory:</strong> <code>{data.workflow_dir}</code></p>"
    )

    # HTML footer
    html_parts.append("</body>")
    html_parts.append("</html>")

    return "\n".join(html_parts)


def _extract_console_summary(markdown_text: str) -> str:
    """Extract key summary from markdown report for console output."""
    lines = []
    in_table = False

    for line in markdown_text.split("\n"):
        # Include headers (remove markdown formatting)
        if line.startswith("#"):
            header = line.lstrip("#").strip()
            if header and not header.startswith("Research Report"):
                lines.append(f"  {header}")

        # Include table content (simplified)
        elif "|" in line and line.strip().startswith("|"):
            if not in_table:
                in_table = True
            if not line.strip().startswith("|-"):  # Skip separator lines
                # Clean up table formatting for console
                cells = [cell.strip() for cell in line.split("|") if cell.strip()]
                if cells:
                    lines.append("  " + " | ".join(cells))
        else:
            in_table = False
            # Include important summary lines
            if line.strip() and not line.startswith("**Generated"):
                if any(
                    keyword in line.lower()
                    for keyword in [
                        "decision:",
                        "score:",
                        "sharpe",
                        "return",
                        "drawdown",
                    ]
                ):
                    lines.append(f"  {line.strip()}")

    return "\n".join(lines) if lines else "  (See full report for details)"


def _markdown_to_html(markdown_text: str) -> str:
    """
    Convert simple markdown to HTML (basic implementation).

    Handles headers, bold text, tables, and paragraphs.
    For full markdown support, would use library like markdown or mistune.
    """
    lines = []
    in_table = False

    for line in markdown_text.split("\n"):
        # Skip top-level headers (already in main HTML)
        if line.startswith("# "):
            continue

        # Headers
        elif line.startswith("## "):
            lines.append(f"    <h3>{line[3:].strip()}</h3>")
        elif line.startswith("### "):
            lines.append(f"    <h4>{line[4:].strip()}</h4>")

        # Tables
        elif "|" in line and line.strip().startswith("|"):
            if not in_table:
                lines.append("    <table>")
                in_table = True

            if line.strip().startswith("|-"):  # Separator line
                continue

            cells = [cell.strip() for cell in line.split("|") if cell.strip()]
            if cells:
                # Detect header row (first row in table)
                if len(lines) > 0 and lines[-1] == "    <table>":
                    lines.append("        <tr>")
                    for cell in cells:
                        lines.append(
                            f"            <th>{_process_inline_markdown(cell)}</th>"
                        )
                    lines.append("        </tr>")
                else:
                    lines.append("        <tr>")
                    for cell in cells:
                        lines.append(
                            f"            <td>{_process_inline_markdown(cell)}</td>"
                        )
                    lines.append("        </tr>")
        else:
            if in_table:
                lines.append("    </table>")
                in_table = False

            # Paragraphs
            if line.strip():
                lines.append(f"    <p>{_process_inline_markdown(line.strip())}</p>")
            else:
                lines.append("")

    if in_table:
        lines.append("    </table>")

    return "\n".join(lines)


def _process_inline_markdown(text: str) -> str:
    """Process inline markdown formatting (bold, code)."""
    # Bold
    import re

    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    # Code
    text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)
    return text


def _get_extension(format: ReportFormat) -> str:
    """Get file extension for report format."""
    if format == ReportFormat.MARKDOWN:
        return "md"
    elif format == ReportFormat.HTML:
        return "html"
    return "txt"
