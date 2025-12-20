"""CLI commands for catalog management."""

import click

from aponyx.config import PROJECT_ROOT


@click.group(name="catalog")
def catalog() -> None:
    """Manage YAML catalog files.

    Commands for validating, syncing, and migrating catalog configurations.
    """
    pass


@catalog.command(name="validate")
def validate_cmd() -> None:
    """Validate catalog YAML files.

    Checks cross-references, required fields, and constraints.
    Exit code 0 if valid, 1 if errors found.

    Examples:
        aponyx catalog validate
    """
    from aponyx.catalog.manager import CatalogManager

    config_dir = PROJECT_ROOT / "config"

    if not config_dir.exists():
        click.echo(
            click.style("Error: ", fg="red")
            + f"Config directory not found: {config_dir}"
        )
        click.echo("Run 'aponyx catalog migrate' to create YAML files from JSON.")
        raise SystemExit(1)

    try:
        manager = CatalogManager(config_dir)
        manager.load()
    except FileNotFoundError as e:
        click.echo(click.style("Error: ", fg="red") + str(e))
        click.echo("Run 'aponyx catalog migrate' to create YAML files from JSON.")
        raise SystemExit(1)

    result = manager.validate()

    # Display summary
    if result.summary:
        click.echo("Validating catalogs...")
        click.echo(
            click.style("✓ ", fg="green")
            + f"indicator_transformations: {result.summary.indicator_transformations} entries"
        )
        click.echo(
            click.style("✓ ", fg="green")
            + f"score_transformations: {result.summary.score_transformations} entries"
        )
        click.echo(
            click.style("✓ ", fg="green")
            + f"signal_transformations: {result.summary.signal_transformations} entries"
        )
        click.echo(
            click.style("✓ ", fg="green")
            + f"signals: {result.summary.signals} entries"
        )
        click.echo(
            click.style("✓ ", fg="green")
            + f"strategies: {result.summary.strategies} entries"
        )
        click.echo(
            click.style("✓ ", fg="green")
            + f"securities: {result.summary.securities} entries"
        )
        click.echo(
            click.style("✓ ", fg="green")
            + f"instruments: {result.summary.instruments} entries"
        )
        click.echo()

    # Display errors
    if result.errors:
        click.echo(
            click.style("Validation failed: ", fg="red")
            + f"{len(result.errors)} error(s)"
        )
        for error in result.errors:
            click.echo()
            click.echo(
                click.style("  Error: ", fg="red")
                + f"[{error.category}] {error.entry_name}.{error.field}"
            )
            click.echo(f"    {error.message}")
            if error.suggestion:
                click.echo(
                    click.style("    Suggestion: ", fg="yellow") + error.suggestion
                )
        raise SystemExit(1)

    # Display warnings
    if result.warnings:
        click.echo(
            click.style("Warnings: ", fg="yellow") + f"{len(result.warnings)} warning(s)"
        )
        for warning in result.warnings:
            click.echo(f"  [{warning.category}] {warning.entry_name}: {warning.message}")
        click.echo()

    click.echo(click.style("All catalog references valid.", fg="green"))


@catalog.command(name="sync")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show changes without writing files",
)
def sync_cmd(dry_run: bool) -> None:
    """Sync YAML catalogs to JSON files.

    Validates before syncing. Fails if validation errors exist.

    Examples:
        aponyx catalog sync
        aponyx catalog sync --dry-run
    """
    from aponyx.catalog.manager import CatalogManager

    config_dir = PROJECT_ROOT / "config"

    if not config_dir.exists():
        click.echo(
            click.style("Error: ", fg="red")
            + f"Config directory not found: {config_dir}"
        )
        click.echo("Run 'aponyx catalog migrate' to create YAML files from JSON.")
        raise SystemExit(1)

    try:
        manager = CatalogManager(config_dir)
        manager.load()
    except FileNotFoundError as e:
        click.echo(click.style("Error: ", fg="red") + str(e))
        click.echo("Run 'aponyx catalog migrate' to create YAML files from JSON.")
        raise SystemExit(1)

    # Validate first
    validation = manager.validate()
    if not validation.passed:
        click.echo(
            click.style("Sync aborted: ", fg="red")
            + f"{len(validation.errors)} validation error(s) found."
        )
        click.echo("Run 'aponyx catalog validate' for details.")
        raise SystemExit(1)

    # Perform sync
    try:
        result = manager.sync(dry_run=dry_run)
    except Exception as e:
        click.echo(click.style("Sync failed: ", fg="red") + str(e))
        raise SystemExit(1)

    prefix = "[DRY RUN] " if dry_run else ""
    click.echo(f"{prefix}Syncing catalogs to JSON...")

    for path in result.files_written:
        click.echo(click.style("✓ ", fg="green") + str(path))

    for path in result.files_unchanged:
        click.echo(click.style("- ", fg="bright_black") + f"{path} (unchanged)")

    if result.errors:
        for error in result.errors:
            click.echo(click.style("✗ ", fg="red") + error)
        raise SystemExit(1)

    click.echo()
    if dry_run:
        click.echo(
            f"{prefix}Would update {len(result.files_written)} files, "
            f"{len(result.files_unchanged)} unchanged."
        )
    else:
        click.echo(
            f"Sync complete. {len(result.files_written)} files updated, "
            f"{len(result.files_unchanged)} unchanged."
        )


@catalog.command(name="migrate")
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing YAML files",
)
def migrate_cmd(force: bool) -> None:
    """Migrate JSON catalogs to YAML format.

    One-time migration to bootstrap YAML source files.

    Examples:
        aponyx catalog migrate
        aponyx catalog migrate --force
    """
    from aponyx.catalog.migration import migrate_json_to_yaml, verify_round_trip
    from aponyx.config import PACKAGE_ROOT

    config_dir = PROJECT_ROOT / "config"

    # Check if YAML files already exist
    catalogs_yaml = config_dir / "catalogs.yaml"
    securities_yaml = config_dir / "securities.yaml"

    if (catalogs_yaml.exists() or securities_yaml.exists()) and not force:
        click.echo(
            click.style("Error: ", fg="red") + "YAML files already exist."
        )
        click.echo(f"  {catalogs_yaml}")
        click.echo(f"  {securities_yaml}")
        click.echo()
        click.echo("Use --force to overwrite existing files.")
        raise SystemExit(1)

    click.echo("Migrating JSON catalogs to YAML...")

    try:
        catalogs_path, securities_path = migrate_json_to_yaml(
            source_dir=PACKAGE_ROOT,
            output_dir=config_dir,
        )
    except FileNotFoundError as e:
        click.echo(click.style("Migration failed: ", fg="red") + str(e))
        raise SystemExit(1)
    except Exception as e:
        click.echo(click.style("Migration failed: ", fg="red") + str(e))
        raise SystemExit(1)

    click.echo(click.style("✓ ", fg="green") + str(catalogs_path))
    click.echo(click.style("✓ ", fg="green") + str(securities_path))
    click.echo()

    # Verify round-trip
    click.echo("Verifying round-trip...")
    try:
        is_valid = verify_round_trip(yaml_dir=config_dir, json_dir=PACKAGE_ROOT)
    except Exception as e:
        click.echo(
            click.style("Warning: ", fg="yellow")
            + f"Round-trip verification failed: {e}"
        )
        is_valid = False

    if is_valid:
        click.echo(click.style("✓ ", fg="green") + "Round-trip verification passed")
    else:
        click.echo(
            click.style("⚠ ", fg="yellow")
            + "Round-trip verification failed (JSON output may differ)"
        )

    click.echo()
    click.echo("Migration complete. Edit YAML files in config/ and run 'aponyx catalog sync'.")
