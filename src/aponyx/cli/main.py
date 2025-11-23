"""Command-line interface for systematic macro credit research."""

import logging
import sys
from datetime import datetime
from pathlib import Path

import click

from aponyx.cli.commands import run, report, list_items, clean
from aponyx.config import LOGS_DIR


@click.group(name="aponyx", context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose logging to see detailed execution information",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Systematic Macro Credit Research CLI."""
    # Configure logging based on verbosity
    log_level = logging.DEBUG if verbose else logging.WARNING
    
    # Create logs directory if it doesn't exist
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"aponyx_{timestamp}.log"
    
    # Configure logging with both console and file handlers
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s - %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.FileHandler(log_file, encoding="utf-8"),  # File output
        ],
        force=True,
    )
    
    logger = logging.getLogger(__name__)
    logger.debug("Logging to file: %s", log_file)

    # Store verbose flag in context for commands to access
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


# Register commands
cli.add_command(run)
cli.add_command(report)
cli.add_command(list_items)
cli.add_command(clean)


def main() -> None:
    """Entry point for installed CLI."""
    try:
        cli()
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
