"""Command-line interface for systematic macro credit research."""

import sys

import click

from aponyx.cli.commands import run, report, list_items, clean


@click.group(name="aponyx", context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """Systematic Macro Credit Research CLI."""
    pass


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
