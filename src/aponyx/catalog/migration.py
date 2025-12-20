"""
Migration utility for converting existing JSON catalogs to YAML.

Provides one-time migration to bootstrap YAML source files from
existing JSON catalog files.
"""

import json
import logging
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from aponyx.catalog.data import CatalogsData, SecuritiesData
from aponyx.catalog.entries import (
    ChannelConfig,
    IndicatorTransformationEntry,
    InstrumentEntry,
    ScoreTransformationEntry,
    SecurityEntry,
    SignalEntry,
    SignalTransformationEntry,
    StrategyEntry,
)
from aponyx.catalog.loader import save_catalogs_yaml, save_securities_yaml
from aponyx.catalog.sync import (
    generate_indicator_json,
    generate_instruments_json,
    generate_score_json,
    generate_securities_json,
    generate_signal_json,
    generate_signal_transformation_json,
    generate_strategy_json,
)

logger = logging.getLogger(__name__)

# Header comments for generated YAML files
CATALOGS_HEADER = """\
# Aponyx Signal & Strategy Catalogs
# Source of truth for all signal/strategy definitions
# 
# Generated JSON files:
#   - src/aponyx/models/indicator_transformation.json
#   - src/aponyx/models/score_transformation.json
#   - src/aponyx/models/signal_transformation.json
#   - src/aponyx/models/signal_catalog.json
#   - src/aponyx/backtest/strategy_catalog.json
#
# Run `aponyx catalog sync` after editing
"""

SECURITIES_HEADER = """\
# Aponyx Security & Instrument Definitions
# Source of truth for Bloomberg security mappings
#
# Generated JSON files:
#   - src/aponyx/data/bloomberg_securities.json
#   - src/aponyx/data/bloomberg_instruments.json
#
# Run `aponyx catalog sync` after editing
"""


def _load_json_file(path: Path) -> Any:
    """Load a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _parse_indicator_from_json(data: dict[str, Any]) -> IndicatorTransformationEntry:
    """Parse indicator transformation from JSON dict."""
    return IndicatorTransformationEntry(
        name=data["name"],
        description=data.get("description", ""),
        compute_function_name=data["compute_function_name"],
        data_requirements=dict(data.get("data_requirements", {})),
        default_securities=dict(data.get("default_securities", {})),
        output_units=data.get("output_units", ""),
        parameters=dict(data.get("parameters", {})),
        enabled=data.get("enabled", True),
    )


def _parse_score_from_json(data: dict[str, Any]) -> ScoreTransformationEntry:
    """Parse score transformation from JSON dict."""
    return ScoreTransformationEntry(
        name=data["name"],
        description=data.get("description", ""),
        transform_type=data["transform_type"],
        parameters=dict(data.get("parameters", {})),
        enabled=data.get("enabled", True),
    )


def _parse_signal_transformation_from_json(
    data: dict[str, Any],
) -> SignalTransformationEntry:
    """Parse signal transformation from JSON dict."""
    neutral_range = data.get("neutral_range")
    if neutral_range is not None:
        neutral_range = tuple(neutral_range)

    return SignalTransformationEntry(
        name=data["name"],
        description=data.get("description", ""),
        scaling=float(data.get("scaling", 1.0)),
        floor=data.get("floor"),
        cap=data.get("cap"),
        neutral_range=neutral_range,
        enabled=data.get("enabled", True),
    )


def _parse_signal_from_json(data: dict[str, Any]) -> SignalEntry:
    """Parse signal from JSON dict."""
    return SignalEntry(
        name=data["name"],
        description=data.get("description", ""),
        indicator_transformation=data["indicator_transformation"],
        score_transformation=data["score_transformation"],
        signal_transformation=data["signal_transformation"],
        sign_multiplier=int(data.get("sign_multiplier", 1)),
        enabled=data.get("enabled", True),
    )


def _parse_strategy_from_json(data: dict[str, Any]) -> StrategyEntry:
    """Parse strategy from JSON dict."""
    return StrategyEntry(
        name=data["name"],
        description=data.get("description", ""),
        position_size_mm=float(data.get("position_size_mm", 10.0)),
        sizing_mode=data.get("sizing_mode", "proportional"),
        stop_loss_pct=data.get("stop_loss_pct"),
        take_profit_pct=data.get("take_profit_pct"),
        max_holding_days=data.get("max_holding_days"),
        entry_threshold=data.get("entry_threshold"),
        enabled=data.get("enabled", True),
    )


def _parse_security_from_json(name: str, data: dict[str, Any]) -> SecurityEntry:
    """Parse security from JSON dict."""
    channels: dict[str, ChannelConfig] = {}
    for channel_name, channel_data in data.get("channels", {}).items():
        channels[channel_name] = ChannelConfig(
            bloomberg_ticker=channel_data["bloomberg_ticker"],
            field=channel_data["field"],
            column=channel_data.get("column"),
            validation=(
                dict(channel_data["validation"])
                if channel_data.get("validation")
                else None
            ),
        )

    return SecurityEntry(
        name=name,
        description=data.get("description", ""),
        instrument_type=data["instrument_type"],
        quote_type=data["quote_type"],
        channels=channels,
        dv01_per_million=data.get("dv01_per_million"),
        transaction_cost_bps=data.get("transaction_cost_bps"),
    )


def _parse_instrument_from_json(name: str, data: dict[str, Any]) -> InstrumentEntry:
    """Parse instrument from JSON dict."""
    bloomberg_fields = data.get("bloomberg_fields", [])
    if isinstance(bloomberg_fields, list):
        bloomberg_fields = tuple(bloomberg_fields)

    return InstrumentEntry(
        name=name,
        description=data.get("description", ""),
        bloomberg_fields=bloomberg_fields,
        field_mapping=dict(data.get("field_mapping", {})),
        requires_security_metadata=data.get("requires_security_metadata", True),
    )


def migrate_json_to_yaml(
    source_dir: Path,
    output_dir: Path,
) -> tuple[Path, Path]:
    """
    Migrate existing JSON catalogs to YAML format.

    Reads all 7 JSON catalog files and generates:
    - catalogs.yaml (signals, transformations, strategies)
    - securities.yaml (securities, instruments)

    Parameters
    ----------
    source_dir : Path
        Base directory containing JSON files (typically src/aponyx).
    output_dir : Path
        Directory for output YAML files.

    Returns
    -------
    tuple[Path, Path]
        Paths to generated catalogs.yaml and securities.yaml.

    Raises
    ------
    FileNotFoundError
        If any JSON source file is missing.
    """
    logger.info("Migrating JSON catalogs from %s to %s", source_dir, output_dir)

    # Define JSON file paths
    indicator_path = source_dir / "models" / "indicator_transformation.json"
    score_path = source_dir / "models" / "score_transformation.json"
    signal_transform_path = source_dir / "models" / "signal_transformation.json"
    signal_path = source_dir / "models" / "signal_catalog.json"
    strategy_path = source_dir / "backtest" / "strategy_catalog.json"
    securities_path = source_dir / "data" / "bloomberg_securities.json"
    instruments_path = source_dir / "data" / "bloomberg_instruments.json"

    # Load all JSON files
    indicator_data = _load_json_file(indicator_path)
    score_data = _load_json_file(score_path)
    signal_transform_data = _load_json_file(signal_transform_path)
    signal_data = _load_json_file(signal_path)
    strategy_data = _load_json_file(strategy_path)
    securities_data = _load_json_file(securities_path)
    instruments_data = _load_json_file(instruments_path)

    # Parse into entry objects
    indicator_entries = [_parse_indicator_from_json(d) for d in indicator_data]
    score_entries = [_parse_score_from_json(d) for d in score_data]
    signal_transform_entries = [
        _parse_signal_transformation_from_json(d) for d in signal_transform_data
    ]
    signal_entries = [_parse_signal_from_json(d) for d in signal_data]
    strategy_entries = [_parse_strategy_from_json(d) for d in strategy_data]

    security_entries = {
        name: _parse_security_from_json(name, data)
        for name, data in securities_data.items()
    }
    instrument_entries = {
        name: _parse_instrument_from_json(name, data)
        for name, data in instruments_data.items()
    }

    # Create raw YAML structure for catalogs.yaml
    yaml = YAML()
    yaml.preserve_quotes = True

    from ruamel.yaml import CommentedMap

    catalogs_raw = CommentedMap()
    catalogs_raw.yaml_set_start_comment(CATALOGS_HEADER)

    catalogs_data = CatalogsData(
        raw=catalogs_raw,
        indicator_transformations=indicator_entries,
        score_transformations=score_entries,
        signal_transformations=signal_transform_entries,
        signals=signal_entries,
        strategies=strategy_entries,
    )

    securities_raw = CommentedMap()
    securities_raw.yaml_set_start_comment(SECURITIES_HEADER)

    securities_data_obj = SecuritiesData(
        raw=securities_raw,
        securities=security_entries,
        instruments=instrument_entries,
    )

    # Write YAML files
    output_dir.mkdir(parents=True, exist_ok=True)

    catalogs_yaml_path = output_dir / "catalogs.yaml"
    securities_yaml_path = output_dir / "securities.yaml"

    save_catalogs_yaml(catalogs_data, catalogs_yaml_path)
    save_securities_yaml(securities_data_obj, securities_yaml_path)

    logger.info("Created %s", catalogs_yaml_path)
    logger.info("Created %s", securities_yaml_path)

    return catalogs_yaml_path, securities_yaml_path


def verify_round_trip(
    yaml_dir: Path,
    json_dir: Path,
) -> bool:
    """
    Verify YAML → JSON round-trip produces identical output.

    Loads YAML files, generates JSON, and compares with original JSON.

    Parameters
    ----------
    yaml_dir : Path
        Directory with YAML files.
    json_dir : Path
        Directory with original JSON files (typically src/aponyx).

    Returns
    -------
    bool
        True if round-trip produces identical JSON content.
    """
    from aponyx.catalog.loader import load_catalogs_yaml, load_securities_yaml

    logger.info("Verifying round-trip: YAML -> JSON")

    # Load YAML
    catalogs = load_catalogs_yaml(yaml_dir / "catalogs.yaml")
    securities = load_securities_yaml(yaml_dir / "securities.yaml")

    # Generate JSON from YAML
    generated = {
        "models/indicator_transformation.json": generate_indicator_json(
            catalogs.indicator_transformations
        ),
        "models/score_transformation.json": generate_score_json(
            catalogs.score_transformations
        ),
        "models/signal_transformation.json": generate_signal_transformation_json(
            catalogs.signal_transformations
        ),
        "models/signal_catalog.json": generate_signal_json(catalogs.signals),
        "backtest/strategy_catalog.json": generate_strategy_json(catalogs.strategies),
        "data/bloomberg_securities.json": generate_securities_json(
            securities.securities
        ),
        "data/bloomberg_instruments.json": generate_instruments_json(
            securities.instruments
        ),
    }

    # Compare with original JSON
    all_match = True
    for rel_path, gen_data in generated.items():
        orig_path = json_dir / rel_path
        orig_data = _load_json_file(orig_path)

        # Normalize for comparison
        gen_str = json.dumps(gen_data, sort_keys=True)
        orig_str = json.dumps(orig_data, sort_keys=True)

        if gen_str != orig_str:
            logger.warning("Mismatch in %s", rel_path)
            all_match = False
        else:
            logger.debug("Match: %s", rel_path)

    return all_match
