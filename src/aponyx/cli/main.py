"""Command-line interface for systematic macro credit research."""

import logging
import sys
from datetime import datetime

import click

from aponyx import __version__
from aponyx.cli.commands import run, report, list_items, clean
from aponyx.config import LOGS_DIR


class BannerGroup(click.Group):
    """Custom Click Group that displays banner before help."""
    
    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> str:
        """Format help with banner at the top."""
        # Check if --no-banner is in sys.argv directly
        import sys
        no_banner = "--no-banner" in sys.argv
        
        # Print banner before help
        if not no_banner:
            print_banner()
        
        # Return standard help
        return super().format_help(ctx, formatter)


# ASCII Art Banner
BANNER = r"""
    ___                                
   / _ | ___  ___  ___  __ ____ __
  / __ |/ _ \/ _ \/ _ \/ // /\ \ /
 /_/ |_/ .__/\___/_//_/\_, / /_\_\
      /_/             /___/        
    
  Systematic Macro Credit Research
"""


def print_banner() -> None:
    """Display stylized CLI banner."""
    click.echo(click.style(BANNER, fg="cyan", bold=True))
    click.echo(
        click.style(f"  Version {__version__}", fg="bright_black")
        + click.style(" | ", fg="bright_black")
        + click.style("Python 3.12+", fg="bright_black")
    )
    click.echo()


@click.group(
    name="aponyx",
    cls=BannerGroup,
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose logging to see detailed execution information",
)
@click.option(
    "--no-banner",
    is_flag=True,
    help="Suppress the startup banner",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, no_banner: bool) -> None:
    """Systematic Macro Credit Research CLI."""
    # If no subcommand, just show help (banner already shown by format_help)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit()
    
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
