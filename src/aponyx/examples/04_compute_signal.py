"""
Compute all enabled signals from catalog using market data.

Prerequisites
-------------
Data fetched from previous step (02_fetch_data_file.py or 03_fetch_data_bloomberg.py):
- Cached data in data/cache/{provider}/ for required instruments
- Data registry populated with dataset entries

Workflow
--------
1. Determine required data keys from ALL enabled signals
2. Load all required market data once from registry
3. Compute all enabled signals via four-stage transformation pipeline
4. Individual signals then used separately for evaluation/backtesting

Four-Stage Transformation Pipeline
----------------------------------
Security → Indicator → Score → Signal → Position

1. Indicator Transformation: Compute economic metric (e.g., spread difference in bps)
2. Score Transformation: Normalize indicator (e.g., z-score)
3. Signal Transformation: Apply trading rules (floor, cap, neutral_range)
4. Position Calculation: Backtest layer (out of scope for this script)

Outputs
-------
Dict of computed signals (one pd.Series per enabled signal).
Saved to data/workflows/signals/{signal_name}.parquet for next steps.

Examples
--------
Run from project root:
    python -m aponyx.examples.04_compute_signal

Returns dict with signal names as keys and pd.Series as values.
Expected: 3 signals (cdx_etf_basis, cdx_vix_gap, spread_momentum).
"""

import pandas as pd

from aponyx.config import (
    REGISTRY_PATH,
    DATA_DIR,
    SIGNAL_CATALOG_PATH,
    DATA_WORKFLOWS_DIR,
    INDICATOR_TRANSFORMATION_PATH,
)
from aponyx.data import DataRegistry
from aponyx.models import SignalRegistry, compute_registered_signals
from aponyx.models.registry import (
    IndicatorTransformationRegistry,
)
from aponyx.persistence import save_parquet


def main() -> dict[str, pd.Series]:
    """
    Execute batch signal computation workflow.

    Loads all required market data from registry, then computes
    all enabled signals via the four-stage transformation pipeline.

    Returns
    -------
    dict[str, pd.Series]
        Mapping from signal name to computed signal series.
    """
    market_data = load_all_required_data()
    signals = compute_all_signals(market_data)
    save_all_signals(signals)
    return signals


def load_all_required_data() -> dict[str, pd.DataFrame]:
    """
    Load all market data required by enabled signals.

    Uses default_securities from each indicator's metadata to determine
    which specific securities to load for each instrument type.

    Returns
    -------
    dict[str, pd.DataFrame]
        Market data mapping with all required instruments.
        Keys are generic identifiers (e.g., "cdx", "etf", "vix").

    Notes
    -----
    Collects data requirements from indicator_transformation.json
    based on which indicators are referenced by enabled signals.
    """
    data_registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    indicator_registry = IndicatorTransformationRegistry(INDICATOR_TRANSFORMATION_PATH)

    # Build mapping from instrument type to security ID
    # by collecting default_securities from indicators used by enabled signals
    instrument_to_security: dict[str, str] = {}
    for signal_name, signal_meta in signal_registry.get_enabled().items():
        indicator_meta = indicator_registry.get_metadata(signal_meta.indicator_transformation)
        for inst_type, security_id in indicator_meta.default_securities.items():
            instrument_to_security[inst_type] = security_id

    # Load data for each instrument type using the mapped security
    market_data: dict[str, pd.DataFrame] = {}
    for inst_type, security_id in sorted(instrument_to_security.items()):
        df = data_registry.load_dataset_by_security(security_id)
        market_data[inst_type] = df

    return market_data


def compute_all_signals(
    market_data: dict[str, pd.DataFrame],
) -> dict[str, pd.Series]:
    """
    Compute all enabled signals using four-stage transformation pipeline.

    Parameters
    ----------
    market_data : dict[str, pd.DataFrame]
        Complete market data with all required instruments.

    Returns
    -------
    dict[str, pd.Series]
        Mapping from signal name to computed signal series.

    Notes
    -----
    Orchestrator computes ALL enabled signals in one pass via compose_signal().
    Individual signals are then selected for evaluation/backtesting.
    """
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    return compute_registered_signals(signal_registry, market_data)


def save_all_signals(signals: dict[str, pd.Series]) -> None:
    """
    Save computed signals to workflows directory.

    Parameters
    ----------
    signals : dict[str, pd.Series]
        Mapping from signal name to computed signal series.

    Notes
    -----
    Saves each signal as data/workflows/signals/{signal_name}.parquet.
    """
    signals_dir = DATA_WORKFLOWS_DIR / "signals"
    signals_dir.mkdir(parents=True, exist_ok=True)

    for signal_name, signal_series in signals.items():
        signal_path = signals_dir / f"{signal_name}.parquet"
        signal_df = signal_series.to_frame(name="value")
        save_parquet(signal_df, signal_path)


if __name__ == "__main__":
    main()
