"""
Compute signals using the four-stage transformation pipeline.

Prerequisites
-------------
Market data available from data registry or raw files.
Run 01_generate_synthetic_data.py to create sample data.

Four-Stage Pipeline
-------------------
Security → Indicator → Score → Signal → Position

1. Indicator: Economic metric (e.g., spread difference in bps)
2. Score: Normalized value (e.g., z-score)
3. Signal: Trading signal with rules (floor, cap, neutral_range)
4. Position: Backtest layer (not in this script)

Outputs
-------
Computed signals saved to data/workflows/signals/{signal_name}.parquet.

Examples
--------
Run from project root:
    python -m aponyx.examples.04_compute_signal

Returns dict with signal names as keys and pd.Series as values.
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
    Compute all enabled signals from catalog.

    Loads required market data and computes signals via
    the four-stage transformation pipeline.

    Returns
    -------
    dict[str, pd.Series]
        Mapping from signal name to computed signal series.
    """
    market_data = load_all_required_data()
    signals = compute_all_signals(market_data)
    save_all_signals(signals)

    print(f"Computed {len(signals)} signals:")
    for name, signal in signals.items():
        print(
            f"  {name}: {len(signal)} values, range [{signal.min():.2f}, {signal.max():.2f}]"
        )

    return signals


def load_all_required_data() -> dict[str, pd.DataFrame]:
    """
    Load market data required by enabled signals.

    Returns
    -------
    dict[str, pd.DataFrame]
        Market data mapping (e.g., "cdx", "etf", "vix").
    """
    data_registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    indicator_registry = IndicatorTransformationRegistry(INDICATOR_TRANSFORMATION_PATH)

    # Collect required securities from signal definitions
    instrument_to_security: dict[str, str] = {}
    for signal_name, signal_meta in signal_registry.get_enabled().items():
        indicator_meta = indicator_registry.get_metadata(
            signal_meta.indicator_transformation
        )
        for inst_type, security_id in indicator_meta.default_securities.items():
            instrument_to_security[inst_type] = security_id

    # Load data for each required instrument
    market_data: dict[str, pd.DataFrame] = {}
    for inst_type, security_id in sorted(instrument_to_security.items()):
        df = data_registry.load_dataset_by_security(security_id)
        market_data[inst_type] = df

    return market_data


def compute_all_signals(
    market_data: dict[str, pd.DataFrame],
) -> dict[str, pd.Series]:
    """
    Compute all enabled signals via four-stage pipeline.

    Parameters
    ----------
    market_data : dict[str, pd.DataFrame]
        Market data with all required instruments.

    Returns
    -------
    dict[str, pd.Series]
        Mapping from signal name to computed signal series.
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
    """
    signals_dir = DATA_WORKFLOWS_DIR / "signals"
    signals_dir.mkdir(parents=True, exist_ok=True)

    for signal_name, signal_series in signals.items():
        signal_path = signals_dir / f"{signal_name}.parquet"
        signal_df = signal_series.to_frame(name="value")
        save_parquet(signal_df, signal_path)


if __name__ == "__main__":
    main()
