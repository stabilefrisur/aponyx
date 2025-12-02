"""
Run workflow command.

Executes research workflows for signal-strategy combinations using YAML config files.
"""

import json
import logging
from pathlib import Path
from typing import Any

import click
import yaml

from aponyx.workflows import WorkflowEngine, WorkflowConfig
from aponyx.models.registry import SignalRegistry, IndicatorRegistry, TransformationRegistry
from aponyx.backtest.registry import StrategyRegistry
from aponyx.config import (
    SIGNAL_CATALOG_PATH,
    INDICATOR_CATALOG_PATH,
    TRANSFORMATION_CATALOG_PATH,
    STRATEGY_CATALOG_PATH,
    BLOOMBERG_SECURITIES_PATH,
)

logger = logging.getLogger(__name__)


def _validate_config_references(
    signal_name: str,
    strategy_name: str,
    indicator_override: str | None,
    transformation_override: str | None,
    securities: dict[str, str] | None,
) -> None:
    """
    Validate all catalog references before workflow execution.

    Parameters
    ----------
    signal_name : str
        Signal name to validate.
    strategy_name : str
        Strategy name to validate.
    indicator_override : str | None
        Indicator override to validate (if provided).
    transformation_override : str | None
        Transformation override to validate (if provided).
    securities : dict[str, str] | None
        Security mapping to validate (if provided).

    Raises
    ------
    click.ClickException
        If any validation fails, with helpful error message and available options.
    """
    # Validate signal exists
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    if not signal_registry.signal_exists(signal_name):
        available = ", ".join(sorted(signal_registry.list_all().keys()))
        raise click.ClickException(
            f"Signal '{signal_name}' not found in catalog.\n"
            f"Available signals: {available}"
        )

    # Validate strategy exists
    strategy_registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    if not strategy_registry.strategy_exists(strategy_name):
        available = ", ".join(sorted(strategy_registry.list_all().keys()))
        raise click.ClickException(
            f"Strategy '{strategy_name}' not found in catalog.\n"
            f"Available strategies: {available}"
        )

    # Validate indicator override (if provided)
    if indicator_override:
        indicator_registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)
        if not indicator_registry.indicator_exists(indicator_override):
            available = ", ".join(sorted(indicator_registry.list_all().keys()))
            raise click.ClickException(
                f"Indicator '{indicator_override}' not found in catalog.\n"
                f"Available indicators: {available}"
            )

    # Validate transformation override (if provided)
    if transformation_override:
        transformation_registry = TransformationRegistry(TRANSFORMATION_CATALOG_PATH)
        if not transformation_registry.transformation_exists(transformation_override):
            available = ", ".join(sorted(transformation_registry.list_all().keys()))
            raise click.ClickException(
                f"Transformation '{transformation_override}' not found in catalog.\n"
                f"Available transformations: {available}"
            )

    # Validate securities mapping (if provided)
    if securities:
        with open(BLOOMBERG_SECURITIES_PATH, "r", encoding="utf-8") as f:
            bloomberg_securities = json.load(f)

        for inst_type, security_id in securities.items():
            if security_id not in bloomberg_securities:
                available = ", ".join(sorted(bloomberg_securities.keys()))
                raise click.ClickException(
                    f"Security '{security_id}' not found in bloomberg_securities.json.\n"
                    f"Available securities: {available}"
                )

            # Check instrument_type matches
            security_info = bloomberg_securities[security_id]
            if security_info["instrument_type"] != inst_type:
                # Filter available securities by instrument_type
                filtered = [
                    k
                    for k, v in bloomberg_securities.items()
                    if v["instrument_type"] == inst_type
                ]
                available_filtered = ", ".join(sorted(filtered))
                raise click.ClickException(
                    f"Security '{security_id}' has instrument_type '{security_info['instrument_type']}', expected '{inst_type}'.\n"
                    f"Available {inst_type} securities: {available_filtered}"
                )


def _display_workflow_config(
    config: WorkflowConfig,
    config_dict: dict[str, Any],
) -> None:
    """
    Display complete workflow configuration with source attribution.

    Shows all configuration fields with tags indicating source:
    [config], [from signal], [from indicator], [default]

    Parameters
    ----------
    config : WorkflowConfig
        Workflow configuration to display.
    config_dict : dict[str, Any]
        Original YAML dict to determine what was user-specified.
    """
    header = "=== Workflow Configuration ==="
    click.echo(header)

    # Load registries for metadata lookup
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    signal_metadata = signal_registry.get_metadata(config.signal_name)

    indicator_registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)

    # Resolve actual indicator (override or from signal)
    if config.indicator_override:
        indicator_name = config.indicator_override
        indicator_source = "[config]"
    else:
        indicator_name = signal_metadata.indicator_dependencies[0]
        indicator_source = "[from signal]"

    indicator_metadata = indicator_registry.get_metadata(indicator_name)

    # Resolve actual transformation (override or from signal)
    if config.transformation_override:
        transformation_name = config.transformation_override
        transformation_source = "[config]"
    else:
        transformation_name = signal_metadata.transformations[0]
        transformation_source = "[from signal]"

    # Resolve actual securities (mapping or from indicator defaults)
    if config.security_mapping:
        securities_str = ", ".join(
            f"{k}:{v}" for k, v in sorted(config.security_mapping.items())
        )
        securities_source = "[config]"
    else:
        securities_str = ", ".join(
            f"{k}:{v}" for k, v in sorted(indicator_metadata.default_securities.items())
        )
        securities_source = "[from indicator]"

    # Display all fields with proper alignment
    click.echo(f"Label:           {config.label} [config]")
    click.echo(f"Product:         {config.product} {'[config]' if 'product' in config_dict else '[default]'}")
    click.echo(f"Signal:          {config.signal_name} [config]")
    click.echo(f"Indicator:       {indicator_name} {indicator_source}")
    click.echo(f"Securities:      {securities_str} {securities_source}")
    click.echo(f"Transformation:  {transformation_name} {transformation_source}")
    click.echo(f"Strategy:        {config.strategy_name} [config]")
    click.echo(f"Data:            {config.data_source} {'[config]' if 'data' in config_dict else '[default]'}")

    # Display steps
    if config.steps:
        steps_str = ", ".join(config.steps)
        steps_source = "[config]"
    else:
        steps_str = "all"
        steps_source = "[default]"
    click.echo(f"Steps:           {steps_str} {steps_source}")

    # Display force re-run
    force_source = "[config]" if "force" in config_dict else "[default]"
    click.echo(f"Force re-run:    {config.force_rerun} {force_source}")

    click.echo("=" * len(header))
    click.echo()


@click.command(name="run")
@click.argument(
    "config_path",
    type=click.Path(exists=True, path_type=Path),
)
def run(config_path: Path) -> None:
    """
    Run research workflow using YAML configuration file.

    Executes full pipeline: data -> signal -> evaluation -> backtest -> visualization.
    Skips completed steps unless force: true is specified in config.

    All workflow parameters must be specified in the YAML config file.

    Required YAML fields:
    - signal: Signal name (must exist in signal_catalog.json)
    - product: Product identifier (e.g., "cdx_ig_5y")
    - strategy: Strategy name (must exist in strategy_catalog.json)

    Optional YAML fields:
    - indicator: Indicator override (default: from signal)
    - transformation: Transformation override (default: from signal)
    - securities: Security mapping dict (default: from indicator)
    - data: Data source (default: "synthetic")
    - steps: List of steps to execute (default: all)
    - force: Boolean to force re-run (default: false)

    \b
    Examples:
        # Minimal config (workflow_minimal.yaml)
        signal: spread_momentum
        product: cdx_ig_5y
        strategy: balanced

        # Complete config (workflow_complete.yaml)
        signal: cdx_etf_basis
        product: cdx_ig_5y
        strategy: balanced
        indicator: cdx_etf_spread_diff
        transformation: z_score_20d
        securities:
          cdx: cdx_hy_5y
          etf: hyg
        data: bloomberg
        steps: [data, signal, backtest]
        force: true

        # Run workflow
        aponyx run examples/workflow_minimal.yaml
        aponyx run examples/workflow_complete.yaml
    """
    # Load YAML configuration
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f) or {}
        logger.info("Loaded configuration from %s", config_path)
    except Exception as e:
        raise click.ClickException(f"Failed to load config file: {e}")

    # Validate required fields present in YAML
    required_fields = ["label", "signal", "product", "strategy"]
    missing_fields = [f for f in required_fields if f not in config_dict]
    if missing_fields:
        raise click.ClickException(
            f"Missing required field(s) in config file: {', '.join(missing_fields)}\n"
            f"Required fields: label, signal, product, strategy"
        )

    # Extract fields from YAML (map simple keys to WorkflowConfig field names)
    label = config_dict["label"]
    signal_name = config_dict["signal"]
    product_id = config_dict["product"]
    strategy_name = config_dict["strategy"]
    indicator_override = config_dict.get("indicator")
    transformation_override = config_dict.get("transformation")
    securities = config_dict.get("securities")
    data_source = config_dict.get("data", "synthetic")
    step_list = config_dict.get("steps")
    force_rerun = config_dict.get("force", False)

    # Validate all catalog references
    _validate_config_references(
        signal_name=signal_name,
        strategy_name=strategy_name,
        indicator_override=indicator_override,
        transformation_override=transformation_override,
        securities=securities,
    )

    # Create WorkflowConfig
    try:
        workflow_config = WorkflowConfig(
            label=label,
            signal_name=signal_name,
            strategy_name=strategy_name,
            product=product_id,
            data_source=data_source,  # type: ignore
            security_mapping=securities,
            indicator_override=indicator_override,
            transformation_override=transformation_override,
            steps=step_list,  # type: ignore
            force_rerun=force_rerun,
        )
    except ValueError as e:
        raise click.ClickException(f"Configuration error: {e}")

    # Display configuration with source attribution
    _display_workflow_config(workflow_config, config_dict)

    # Execute workflow
    engine = WorkflowEngine(workflow_config)
    results = engine.execute()

    # Display results
    if results["errors"]:
        click.echo(
            f"Workflow failed: {results['steps_completed']} steps completed", err=True
        )
        for error in results["errors"]:
            click.echo(f"  {error['step']}: {error['error']}", err=True)
        raise click.Abort()

    click.echo(
        f"Completed {results['steps_completed']} steps in {results['duration_seconds']:.1f}s"
    )
    if results["steps_skipped"] > 0:
        click.echo(f"Skipped {results['steps_skipped']} cached steps")
    click.echo(f"Results: {results['output_dir']}")
