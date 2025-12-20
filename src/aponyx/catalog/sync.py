"""
YAML to JSON synchronization.

Generates all 7 JSON catalog files from YAML sources:
- src/aponyx/models/indicator_transformation.json
- src/aponyx/models/score_transformation.json
- src/aponyx/models/signal_transformation.json
- src/aponyx/models/signal_catalog.json
- src/aponyx/backtest/strategy_catalog.json
- src/aponyx/data/bloomberg_securities.json
- src/aponyx/data/bloomberg_instruments.json
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aponyx.catalog.data import CatalogsData, SecuritiesData
from aponyx.catalog.entries import (
    IndicatorTransformationEntry,
    InstrumentEntry,
    ScoreTransformationEntry,
    SecurityEntry,
    SignalEntry,
    SignalTransformationEntry,
    StrategyEntry,
)
from aponyx.catalog.sync_types import SyncResult

logger = logging.getLogger(__name__)


def _get_generation_marker() -> dict[str, dict[str, str]]:
    """Generate the _generated marker for JSON files."""
    return {
        "_generated": {
            "source": "config/catalogs.yaml or config/securities.yaml",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "generator": "aponyx catalog sync",
            "warning": "DO NOT EDIT - regenerate with 'aponyx catalog sync'",
        }
    }


def generate_indicator_json(
    entries: list[IndicatorTransformationEntry],
) -> list[dict[str, Any]]:
    """
    Generate JSON-compatible list for indicator_transformation.json.

    Parameters
    ----------
    entries : list[IndicatorTransformationEntry]
        Indicator transformation entries.

    Returns
    -------
    list[dict[str, Any]]
        JSON-serializable list.
    """
    return [
        {
            "name": e.name,
            "description": e.description,
            "compute_function_name": e.compute_function_name,
            "data_requirements": dict(e.data_requirements),
            "default_securities": dict(e.default_securities),
            "output_units": e.output_units,
            "parameters": dict(e.parameters) if e.parameters else {},
            "enabled": e.enabled,
        }
        for e in entries
    ]


def generate_score_json(
    entries: list[ScoreTransformationEntry],
) -> list[dict[str, Any]]:
    """
    Generate JSON-compatible list for score_transformation.json.

    Parameters
    ----------
    entries : list[ScoreTransformationEntry]
        Score transformation entries.

    Returns
    -------
    list[dict[str, Any]]
        JSON-serializable list.
    """
    return [
        {
            "name": e.name,
            "description": e.description,
            "transform_type": e.transform_type,
            "parameters": dict(e.parameters) if e.parameters else {},
            "enabled": e.enabled,
        }
        for e in entries
    ]


def generate_signal_transformation_json(
    entries: list[SignalTransformationEntry],
) -> list[dict[str, Any]]:
    """
    Generate JSON-compatible list for signal_transformation.json.

    Parameters
    ----------
    entries : list[SignalTransformationEntry]
        Signal transformation entries.

    Returns
    -------
    list[dict[str, Any]]
        JSON-serializable list.
    """
    result = []
    for e in entries:
        item: dict[str, Any] = {
            "name": e.name,
            "description": e.description,
            "scaling": e.scaling,
            "floor": e.floor,
            "cap": e.cap,
            "neutral_range": list(e.neutral_range) if e.neutral_range else None,
            "enabled": e.enabled,
        }
        result.append(item)
    return result


def generate_signal_json(entries: list[SignalEntry]) -> list[dict[str, Any]]:
    """
    Generate JSON-compatible list for signal_catalog.json.

    Parameters
    ----------
    entries : list[SignalEntry]
        Signal entries.

    Returns
    -------
    list[dict[str, Any]]
        JSON-serializable list.
    """
    return [
        {
            "name": e.name,
            "description": e.description,
            "indicator_transformation": e.indicator_transformation,
            "score_transformation": e.score_transformation,
            "signal_transformation": e.signal_transformation,
            "enabled": e.enabled,
            "sign_multiplier": e.sign_multiplier,
        }
        for e in entries
    ]


def generate_strategy_json(entries: list[StrategyEntry]) -> list[dict[str, Any]]:
    """
    Generate JSON-compatible list for strategy_catalog.json.

    Parameters
    ----------
    entries : list[StrategyEntry]
        Strategy entries.

    Returns
    -------
    list[dict[str, Any]]
        JSON-serializable list.
    """
    return [
        {
            "name": e.name,
            "description": e.description,
            "position_size_mm": e.position_size_mm,
            "sizing_mode": e.sizing_mode,
            "stop_loss_pct": e.stop_loss_pct,
            "take_profit_pct": e.take_profit_pct,
            "max_holding_days": e.max_holding_days,
            "entry_threshold": e.entry_threshold,
            "enabled": e.enabled,
        }
        for e in entries
    ]


def generate_securities_json(
    entries: dict[str, SecurityEntry],
) -> dict[str, dict[str, Any]]:
    """
    Generate JSON-compatible dict for bloomberg_securities.json.

    Parameters
    ----------
    entries : dict[str, SecurityEntry]
        Security entries keyed by name.

    Returns
    -------
    dict[str, dict[str, Any]]
        JSON-serializable dict.
    """
    result: dict[str, dict[str, Any]] = {}

    for name, e in entries.items():
        channels: dict[str, dict[str, Any]] = {}
        for channel_name, cfg in e.channels.items():
            channel_data: dict[str, Any] = {
                "bloomberg_ticker": cfg.bloomberg_ticker,
                "field": cfg.field,
            }
            if cfg.column:
                channel_data["column"] = cfg.column
            if cfg.validation:
                channel_data["validation"] = dict(cfg.validation)
            channels[channel_name] = channel_data

        security_data: dict[str, Any] = {
            "description": e.description,
            "instrument_type": e.instrument_type,
            "quote_type": e.quote_type,
            "channels": channels,
        }

        if e.dv01_per_million is not None:
            security_data["dv01_per_million"] = e.dv01_per_million
        if e.transaction_cost_bps is not None:
            security_data["transaction_cost_bps"] = e.transaction_cost_bps

        result[name] = security_data

    return result


def generate_instruments_json(
    entries: dict[str, InstrumentEntry],
) -> dict[str, dict[str, Any]]:
    """
    Generate JSON-compatible dict for bloomberg_instruments.json.

    Parameters
    ----------
    entries : dict[str, InstrumentEntry]
        Instrument entries keyed by type.

    Returns
    -------
    dict[str, dict[str, Any]]
        JSON-serializable dict.
    """
    return {
        name: {
            "description": e.description,
            "bloomberg_fields": list(e.bloomberg_fields),
            "field_mapping": dict(e.field_mapping),
            "requires_security_metadata": e.requires_security_metadata,
        }
        for name, e in entries.items()
    }


def _write_json(data: Any, path: Path, dry_run: bool = False) -> bool:
    """
    Write JSON data to file.

    Parameters
    ----------
    data : Any
        JSON-serializable data.
    path : Path
        Output path.
    dry_run : bool
        If True, don't actually write.

    Returns
    -------
    bool
        True if file would be changed (or was changed if not dry_run).
    """
    new_content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    if path.exists():
        old_content = path.read_text(encoding="utf-8")
        if old_content == new_content:
            return False  # No change

    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_content, encoding="utf-8")
        logger.debug("Wrote %s", path)

    return True


def sync_to_json(
    catalogs: CatalogsData,
    securities: SecuritiesData,
    output_dir: Path,
    dry_run: bool = False,
) -> SyncResult:
    """
    Synchronize YAML data to JSON catalog files.

    Parameters
    ----------
    catalogs : CatalogsData
        Loaded catalogs data.
    securities : SecuritiesData
        Loaded securities data.
    output_dir : Path
        Base directory for JSON output (typically src/aponyx).
    dry_run : bool
        If True, return what would change without writing.

    Returns
    -------
    SyncResult
        Sync outcome.
    """
    files_written: list[Path] = []
    files_unchanged: list[Path] = []
    errors: list[str] = []

    # Define output paths
    output_files = [
        (
            output_dir / "models" / "indicator_transformation.json",
            generate_indicator_json(catalogs.indicator_transformations),
        ),
        (
            output_dir / "models" / "score_transformation.json",
            generate_score_json(catalogs.score_transformations),
        ),
        (
            output_dir / "models" / "signal_transformation.json",
            generate_signal_transformation_json(catalogs.signal_transformations),
        ),
        (
            output_dir / "models" / "signal_catalog.json",
            generate_signal_json(catalogs.signals),
        ),
        (
            output_dir / "backtest" / "strategy_catalog.json",
            generate_strategy_json(catalogs.strategies),
        ),
        (
            output_dir / "data" / "bloomberg_securities.json",
            generate_securities_json(securities.securities),
        ),
        (
            output_dir / "data" / "bloomberg_instruments.json",
            generate_instruments_json(securities.instruments),
        ),
    ]

    for path, data in output_files:
        try:
            changed = _write_json(data, path, dry_run=dry_run)
            if changed:
                files_written.append(path)
            else:
                files_unchanged.append(path)
        except Exception as e:
            errors.append(f"Failed to write {path}: {e}")
            logger.error("Failed to write %s: %s", path, e)

    success = len(errors) == 0

    if dry_run:
        logger.info(
            "[DRY RUN] Would update %d files, %d unchanged",
            len(files_written),
            len(files_unchanged),
        )
    else:
        logger.info(
            "Sync complete: %d files updated, %d unchanged",
            len(files_written),
            len(files_unchanged),
        )

    return SyncResult(
        success=success,
        files_written=tuple(files_written),
        files_unchanged=tuple(files_unchanged),
        errors=tuple(errors),
        dry_run=dry_run,
    )
