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
3. Compute all enabled signals in batch
4. Individual signals then used separately for evaluation/backtesting

Outputs
-------
Dict of computed signals (one pd.Series per enabled signal).
Saved to data/processed/signals/{signal_name}.parquet for next steps.

Examples
--------
Run from project root:
    python -m aponyx.examples.04_compute_signal

Returns dict with signal names as keys and pd.Series as values.
Expected: 3 signals (cdx_etf_basis, cdx_vix_gap, spread_momentum).
"""

import pandas as pd

from aponyx.config import REGISTRY_PATH, DATA_DIR, SIGNAL_CATALOG_PATH, DATA_WORKFLOWS_DIR
from aponyx.data import DataRegistry, load_signal_required_data
from aponyx.models import SignalConfig, SignalRegistry, compute_registered_signals
from aponyx.persistence import save_parquet


def main() -> dict[str, pd.Series]:
    """
    Execute batch signal computation workflow.

    Loads all required market data from registry, then computes
    all enabled signals in a single pass.

    Returns
    -------
    dict[str, pd.Series]
        Mapping from signal name to computed signal series.
    """
    config = define_signal_config()
    market_data = load_all_required_data()
    signals = compute_all_signals(market_data, config)
    save_all_signals(signals)
    return signals


def define_signal_config() -> SignalConfig:
    """
    Define signal computation configuration.

    Returns
    -------
    SignalConfig
        Signal configuration with lookback and normalization parameters.
    """
    return SignalConfig(
        lookback=20,
        min_periods=10,
    )


def load_all_required_data() -> dict[str, pd.DataFrame]:
    """
    Load all market data required by enabled signals.

    Uses default_securities from each enabled signal to determine
    which specific securities to load for each instrument type.

    Returns
    -------
    dict[str, pd.DataFrame]
        Market data mapping with all required instruments.
        Keys are generic identifiers (e.g., "cdx", "etf", "vix").

    Notes
    -----
    Delegates to data layer helper for loading signal-required data.
    Can optionally pass security_mapping to override default securities.
    """
    data_registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

    # Load data using data layer helper
    # To override defaults, pass security_mapping parameter:
    # security_mapping={"cdx": "cdx_hy_5y", "etf": "hyg"}
    return load_signal_required_data(signal_registry, data_registry)


def compute_all_signals(
    market_data: dict[str, pd.DataFrame],
    config: SignalConfig,
) -> dict[str, pd.Series]:
    """
    Compute all enabled signals using complete market data.

    Parameters
    ----------
    market_data : dict[str, pd.DataFrame]
        Complete market data with all required instruments.
    config : SignalConfig
        Signal computation configuration.

    Returns
    -------
    dict[str, pd.Series]
        Mapping from signal name to computed signal series.

    Notes
    -----
    Orchestrator computes ALL enabled signals in one pass.
    Individual signals are then selected for evaluation/backtesting.
    """
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    return compute_registered_signals(signal_registry, market_data, config)


def save_all_signals(signals: dict[str, pd.Series]) -> None:
    """
    Save computed signals to processed directory.

    Parameters
    ----------
    signals : dict[str, pd.Series]
        Mapping from signal name to computed signal series.

    Notes
    -----
    Saves each signal as data/processed/signals/{signal_name}.parquet.
    """
    signals_dir = DATA_WORKFLOWS_DIR / "signals"
    signals_dir.mkdir(parents=True, exist_ok=True)

    for signal_name, signal_series in signals.items():
        signal_path = signals_dir / f"{signal_name}.parquet"
        signal_df = signal_series.to_frame(name="value")
        save_parquet(signal_df, signal_path)


if __name__ == "__main__":
    main()
