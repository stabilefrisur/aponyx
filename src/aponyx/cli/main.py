"""Command-line interface for systematic macro credit research."""

import logging
import sys

import click

from aponyx.cli.commands import run, report, list_items, clean


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
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s - %(name)s - %(message)s",
        force=True,
    )

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
