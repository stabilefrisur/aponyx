"""
Command-line interface for systematic macro credit research.

Provides commands for running workflows, generating reports, and
managing catalog items.
"""

import logging
import sys

import click

from aponyx.cli.commands import run, report, list_items, clean

logger = logging.getLogger(__name__)


@click.group(name="aponyx", context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging (DEBUG level)",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress all output except errors",
)
def cli(verbose: bool, quiet: bool) -> None:
    """
    Systematic Macro Credit Research CLI.
    
    Run research workflows, generate reports, and manage catalog items.
    """
    # Configure logging
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
        
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# Register commands
cli.add_command(run)
cli.add_command(report)
cli.add_command(list_items)
cli.add_command(clean)


def main() -> None:
    """Entry point for installed CLI."""
    try:
        cli()
    except Exception as e:
        logger.exception("Unexpected error: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
