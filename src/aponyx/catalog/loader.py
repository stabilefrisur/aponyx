"""
YAML loading and saving with comment preservation.

Uses ruamel.yaml to maintain inline comments during round-trip editing.
"""

import logging
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML, CommentedMap

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

logger = logging.getLogger(__name__)


def _get_yaml_instance() -> YAML:
    """Create a configured YAML instance for round-trip editing."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.default_flow_style = False
    return yaml


def _parse_indicator_transformation(data: dict[str, Any]) -> IndicatorTransformationEntry:
    """Parse a single indicator transformation entry."""
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


def _parse_score_transformation(data: dict[str, Any]) -> ScoreTransformationEntry:
    """Parse a single score transformation entry."""
    return ScoreTransformationEntry(
        name=data["name"],
        description=data.get("description", ""),
        transform_type=data["transform_type"],
        parameters=dict(data.get("parameters", {})),
        enabled=data.get("enabled", True),
    )


def _parse_signal_transformation(data: dict[str, Any]) -> SignalTransformationEntry:
    """Parse a single signal transformation entry."""
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


def _parse_signal(data: dict[str, Any]) -> SignalEntry:
    """Parse a single signal entry."""
    return SignalEntry(
        name=data["name"],
        description=data.get("description", ""),
        indicator_transformation=data["indicator_transformation"],
        score_transformation=data["score_transformation"],
        signal_transformation=data["signal_transformation"],
        sign_multiplier=int(data.get("sign_multiplier", 1)),
        enabled=data.get("enabled", True),
    )


def _parse_strategy(data: dict[str, Any]) -> StrategyEntry:
    """Parse a single strategy entry."""
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


def _parse_channel_config(data: dict[str, Any]) -> ChannelConfig:
    """Parse a single channel configuration."""
    return ChannelConfig(
        bloomberg_ticker=data["bloomberg_ticker"],
        field=data["field"],
        column=data.get("column"),
        validation=dict(data.get("validation", {})) if data.get("validation") else None,
    )


def _parse_security(name: str, data: dict[str, Any]) -> SecurityEntry:
    """Parse a single security entry."""
    channels = {}
    for channel_name, channel_data in data.get("channels", {}).items():
        channels[channel_name] = _parse_channel_config(channel_data)

    return SecurityEntry(
        name=name,
        description=data.get("description", ""),
        instrument_type=data["instrument_type"],
        quote_type=data["quote_type"],
        channels=channels,
        dv01_per_million=data.get("dv01_per_million"),
        transaction_cost_bps=data.get("transaction_cost_bps"),
    )


def _parse_instrument(name: str, data: dict[str, Any]) -> InstrumentEntry:
    """Parse a single instrument entry."""
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


def load_catalogs_yaml(path: Path) -> CatalogsData:
    """
    Load catalogs.yaml with comment preservation.

    Parameters
    ----------
    path : Path
        Path to catalogs.yaml file.

    Returns
    -------
    CatalogsData
        Parsed catalog data with raw YAML object.

    Raises
    ------
    FileNotFoundError
        If file not found.
    ValueError
        If structure is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Catalogs file not found: {path}")

    yaml = _get_yaml_instance()
    with open(path, encoding="utf-8") as f:
        raw: CommentedMap = yaml.load(f)

    if raw is None:
        raw = CommentedMap()

    # Parse each section
    indicator_transformations = [
        _parse_indicator_transformation(item)
        for item in raw.get("indicator_transformations", [])
    ]

    score_transformations = [
        _parse_score_transformation(item)
        for item in raw.get("score_transformations", [])
    ]

    signal_transformations = [
        _parse_signal_transformation(item)
        for item in raw.get("signal_transformations", [])
    ]

    signals = [_parse_signal(item) for item in raw.get("signals", [])]

    strategies = [_parse_strategy(item) for item in raw.get("strategies", [])]

    logger.debug(
        "Loaded catalogs.yaml: %d indicators, %d scores, %d signal_transforms, %d signals, %d strategies",
        len(indicator_transformations),
        len(score_transformations),
        len(signal_transformations),
        len(signals),
        len(strategies),
    )

    return CatalogsData(
        raw=raw,
        indicator_transformations=indicator_transformations,
        score_transformations=score_transformations,
        signal_transformations=signal_transformations,
        signals=signals,
        strategies=strategies,
    )


def load_securities_yaml(path: Path) -> SecuritiesData:
    """
    Load securities.yaml with comment preservation.

    Parameters
    ----------
    path : Path
        Path to securities.yaml file.

    Returns
    -------
    SecuritiesData
        Parsed securities data with raw YAML object.

    Raises
    ------
    FileNotFoundError
        If file not found.
    ValueError
        If structure is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Securities file not found: {path}")

    yaml = _get_yaml_instance()
    with open(path, encoding="utf-8") as f:
        raw: CommentedMap = yaml.load(f)

    if raw is None:
        raw = CommentedMap()

    # Parse securities (dict keyed by name)
    securities = {}
    for name, data in raw.get("securities", {}).items():
        securities[name] = _parse_security(name, data)

    # Parse instruments (dict keyed by type)
    instruments = {}
    for name, data in raw.get("instruments", {}).items():
        instruments[name] = _parse_instrument(name, data)

    logger.debug(
        "Loaded securities.yaml: %d securities, %d instruments",
        len(securities),
        len(instruments),
    )

    return SecuritiesData(
        raw=raw,
        securities=securities,
        instruments=instruments,
    )


def _entry_to_dict(entry: IndicatorTransformationEntry) -> dict[str, Any]:
    """Convert indicator transformation entry to dict for YAML."""
    return {
        "name": entry.name,
        "description": entry.description,
        "compute_function_name": entry.compute_function_name,
        "data_requirements": dict(entry.data_requirements),
        "default_securities": dict(entry.default_securities),
        "output_units": entry.output_units,
        "parameters": dict(entry.parameters) if entry.parameters else {},
        "enabled": entry.enabled,
    }


def _score_to_dict(entry: ScoreTransformationEntry) -> dict[str, Any]:
    """Convert score transformation entry to dict for YAML."""
    return {
        "name": entry.name,
        "description": entry.description,
        "transform_type": entry.transform_type,
        "parameters": dict(entry.parameters) if entry.parameters else {},
        "enabled": entry.enabled,
    }


def _signal_transformation_to_dict(entry: SignalTransformationEntry) -> dict[str, Any]:
    """Convert signal transformation entry to dict for YAML."""
    result: dict[str, Any] = {
        "name": entry.name,
        "description": entry.description,
        "scaling": entry.scaling,
        "floor": entry.floor,
        "cap": entry.cap,
        "neutral_range": list(entry.neutral_range) if entry.neutral_range else None,
        "enabled": entry.enabled,
    }
    return result


def _signal_to_dict(entry: SignalEntry) -> dict[str, Any]:
    """Convert signal entry to dict for YAML."""
    return {
        "name": entry.name,
        "description": entry.description,
        "indicator_transformation": entry.indicator_transformation,
        "score_transformation": entry.score_transformation,
        "signal_transformation": entry.signal_transformation,
        "sign_multiplier": entry.sign_multiplier,
        "enabled": entry.enabled,
    }


def _strategy_to_dict(entry: StrategyEntry) -> dict[str, Any]:
    """Convert strategy entry to dict for YAML."""
    return {
        "name": entry.name,
        "description": entry.description,
        "position_size_mm": entry.position_size_mm,
        "sizing_mode": entry.sizing_mode,
        "stop_loss_pct": entry.stop_loss_pct,
        "take_profit_pct": entry.take_profit_pct,
        "max_holding_days": entry.max_holding_days,
        "entry_threshold": entry.entry_threshold,
        "enabled": entry.enabled,
    }


def _channel_to_dict(entry: ChannelConfig) -> dict[str, Any]:
    """Convert channel config to dict for YAML."""
    result: dict[str, Any] = {
        "bloomberg_ticker": entry.bloomberg_ticker,
        "field": entry.field,
    }
    if entry.column:
        result["column"] = entry.column
    if entry.validation:
        result["validation"] = dict(entry.validation)
    return result


def _security_to_dict(entry: SecurityEntry) -> dict[str, Any]:
    """Convert security entry to dict for YAML (excludes name key)."""
    channels = {name: _channel_to_dict(cfg) for name, cfg in entry.channels.items()}
    result: dict[str, Any] = {
        "description": entry.description,
        "instrument_type": entry.instrument_type,
        "quote_type": entry.quote_type,
        "channels": channels,
    }
    if entry.dv01_per_million is not None:
        result["dv01_per_million"] = entry.dv01_per_million
    if entry.transaction_cost_bps is not None:
        result["transaction_cost_bps"] = entry.transaction_cost_bps
    return result


def _instrument_to_dict(entry: InstrumentEntry) -> dict[str, Any]:
    """Convert instrument entry to dict for YAML (excludes name key)."""
    return {
        "description": entry.description,
        "bloomberg_fields": list(entry.bloomberg_fields),
        "field_mapping": dict(entry.field_mapping),
        "requires_security_metadata": entry.requires_security_metadata,
    }


def save_catalogs_yaml(data: CatalogsData, path: Path) -> None:
    """
    Save catalogs data to YAML with comment preservation.

    Parameters
    ----------
    data : CatalogsData
        Catalog data to save.
    path : Path
        Output path.
    """
    yaml = _get_yaml_instance()

    # Use existing raw data to preserve comments, or create new
    output = data.raw if data.raw else CommentedMap()

    # Update sections from parsed entries
    output["indicator_transformations"] = [
        _entry_to_dict(e) for e in data.indicator_transformations
    ]
    output["score_transformations"] = [
        _score_to_dict(e) for e in data.score_transformations
    ]
    output["signal_transformations"] = [
        _signal_transformation_to_dict(e) for e in data.signal_transformations
    ]
    output["signals"] = [_signal_to_dict(e) for e in data.signals]
    output["strategies"] = [_strategy_to_dict(e) for e in data.strategies]

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(output, f)

    logger.debug("Saved catalogs.yaml to %s", path)


def save_securities_yaml(data: SecuritiesData, path: Path) -> None:
    """
    Save securities data to YAML with comment preservation.

    Parameters
    ----------
    data : SecuritiesData
        Securities data to save.
    path : Path
        Output path.
    """
    yaml = _get_yaml_instance()

    # Use existing raw data to preserve comments, or create new
    output = data.raw if data.raw else CommentedMap()

    # Update sections from parsed entries
    securities_dict = CommentedMap()
    for sec_name, sec_entry in data.securities.items():
        securities_dict[sec_name] = _security_to_dict(sec_entry)
    output["securities"] = securities_dict

    instruments_dict = CommentedMap()
    for inst_name, inst_entry in data.instruments.items():
        instruments_dict[inst_name] = _instrument_to_dict(inst_entry)
    output["instruments"] = instruments_dict

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(output, f)

    logger.debug("Saved securities.yaml to %s", path)
