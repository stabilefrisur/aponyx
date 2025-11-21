"""
Generate research report command.

Creates comprehensive analysis documents from workflow results.
"""

import logging
from pathlib import Path

import click

from aponyx.reporting import generate_report

logger = logging.getLogger(__name__)


@click.command(name="report")
@click.option(
    "--signal",
    required=True,
    type=str,
    help="Signal name",
)
@click.option(
    "--strategy",
    required=True,
    type=str,
    help="Strategy name",
)
@click.option(
    "--format",
    type=click.Choice(["console", "markdown", "html"], case_sensitive=False),
    default="console",
    help="Report output format (default: console)",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    help="Custom output path",
)
def report(
    signal: str,
    strategy: str,
    format: str,
    output: Path | None,
) -> None:
    """
    Generate comprehensive research report from existing results.
    
    Aggregates suitability evaluation, performance metrics, and visualization
    references into a single document. Supports console output, markdown, and HTML.
    
    Examples:

        aponyx report --signal spread_momentum --strategy balanced

        aponyx report --signal spread_momentum --strategy balanced --format markdown

        aponyx report --signal spread_momentum --strategy balanced --format html --output report.html
    """
    click.echo(f"\n📄 Generating {format} report: {signal} ({strategy})")
    
    try:
        content = generate_report(
            signal_name=signal,
            strategy_name=strategy,
            format=format,
            output_path=output,
        )
        
        # For console output, print the report
        if format == "console":
            click.echo("\n" + content)
        else:
            click.echo(f"\n✅ Report generated: {output if output else 'saved to default location'}")
            
    except FileNotFoundError as e:
        click.echo(f"\n❌ {str(e)}", err=True)
        raise click.Abort()
    except Exception as e:
        logger.exception("Error generating report")
        click.echo(f"\n❌ Report generation failed: {str(e)}", err=True)
        raise click.Abort()
