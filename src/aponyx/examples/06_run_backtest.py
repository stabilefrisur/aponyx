"""
Execute backtest for signal using strategy from catalog.

Prerequisites
-------------
Signals saved from signal computation (04_compute_signal.py):
- Signal files exist in data/processed/signals/{signal_name}.parquet
CDX spread data available from registry.
Strategy catalog configured in backtest/strategy_catalog.json.

Outputs
-------
BacktestResult with positions and P&L:
- positions: DataFrame with signal, position, days_held, spread
- pnl: DataFrame with spread_pnl, cost, net_pnl, cumulative_pnl
- metadata: Config and execution details
Backtest results saved to data/processed/backtests/{signal_name}_{strategy}.parquet.

Examples
--------
Run from project root:
    python -m aponyx.examples.06_run_backtest

Expected output: BacktestResult with positions and P&L history.
Results saved to data/processed/backtests/spread_momentum_balanced.parquet.
"""

import pandas as pd

from aponyx.config import (
    REGISTRY_PATH,
    DATA_DIR,
    PROCESSED_DIR,
    STRATEGY_CATALOG_PATH,
)
from aponyx.data.registry import DataRegistry
from aponyx.backtest import BacktestResult, run_backtest, StrategyRegistry
from aponyx.persistence import load_parquet, save_parquet


def main() -> BacktestResult:
    """
    Execute backtest workflow.
    
    Loads signal and spread data, selects strategy from catalog,
    runs backtest, and saves results.
    
    Returns
    -------
    BacktestResult
        Backtest result with positions and P&L.
    """
    signal_name, product, strategy_name = define_backtest_parameters()
    signal, spread = load_backtest_data(signal_name, product)
    config = load_strategy_config(strategy_name)
    result = execute_backtest(signal, spread, config)
    save_backtest_result(result, signal_name, strategy_name)
    return result


def define_backtest_parameters() -> tuple[str, str, str]:
    """
    Define backtest parameters.
    
    Returns
    -------
    tuple[str, str, str]
        Signal name, product identifier, and strategy name.
        
    Notes
    -----
    Choose one signal-product-strategy combination for demonstration.
    In practice, evaluate multiple strategies per signal.
    """
    signal_name = "spread_momentum"
    product = "cdx_ig_5y"
    strategy_name = "balanced"
    return signal_name, product, strategy_name


def load_backtest_data(
    signal_name: str,
    product: str,
) -> tuple[pd.Series, pd.Series]:
    """
    Load signal and spread data for backtest.
    
    Parameters
    ----------
    signal_name : str
        Name of signal to load from processed directory.
    product : str
        Product identifier for spread data.
    
    Returns
    -------
    tuple[pd.Series, pd.Series]
        Signal series and spread series (aligned).
        
    Notes
    -----
    Loads signal saved by previous step (04_compute_signal.py).
    Spread data loaded from registry using product identifier.
    """
    signal = load_signal(signal_name)
    spread = load_spread_data(product)
    
    # Align signal and spread to common dates
    common_idx = signal.index.intersection(spread.index)
    signal = signal.loc[common_idx]
    spread = spread.loc[common_idx]
    
    return signal, spread


def load_signal(signal_name: str) -> pd.Series:
    """
    Load signal from processed directory.
    
    Parameters
    ----------
    signal_name : str
        Name of signal file (without .parquet extension).
    
    Returns
    -------
    pd.Series
        Signal series with DatetimeIndex.
    """
    signal_path = PROCESSED_DIR / "signals" / f"{signal_name}.parquet"
    signal_df = load_parquet(signal_path)
    return signal_df["value"]


def load_spread_data(product: str) -> pd.Series:
    """
    Load spread data for target product.
    
    Parameters
    ----------
    product : str
        Product identifier (e.g., "cdx_ig_5y").
    
    Returns
    -------
    pd.Series
        Spread series with DatetimeIndex.
        
    Notes
    -----
    Searches registry for datasets with matching security in metadata.
    """
    data_registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
    
    all_datasets = data_registry.list_datasets()
    
    for dataset_name in all_datasets:
        info = data_registry.get_dataset_info(dataset_name)
        metadata = info.get("metadata", {})
        params = metadata.get("params", {})
        
        if params.get("security") == product:
            spread_df = load_parquet(info["file_path"])
            return spread_df["spread"]
    
    raise ValueError(f"No dataset found for product: {product}")


def load_strategy_config(strategy_name: str):
    """
    Load strategy configuration from catalog.
    
    Parameters
    ----------
    strategy_name : str
        Name of strategy in catalog (e.g., "balanced", "conservative").
    
    Returns
    -------
    BacktestConfig
        Backtest configuration with strategy parameters.
        
    Notes
    -----
    Reads strategy metadata from catalog and converts to BacktestConfig.
    """
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    metadata = registry.get_metadata(strategy_name)
    return metadata.to_config()


def execute_backtest(
    signal: pd.Series,
    spread: pd.Series,
    config,
) -> BacktestResult:
    """
    Run backtest with signal and spread data.
    
    Parameters
    ----------
    signal : pd.Series
        Signal series with DatetimeIndex.
    spread : pd.Series
        Spread series with DatetimeIndex.
    config : BacktestConfig
        Backtest configuration.
    
    Returns
    -------
    BacktestResult
        Backtest result with positions and P&L.
    """
    return run_backtest(signal, spread, config)


def save_backtest_result(
    result: BacktestResult,
    signal_name: str,
    strategy_name: str,
) -> None:
    """
    Save backtest results to processed directory.
    
    Parameters
    ----------
    result : BacktestResult
        Backtest result to save.
    signal_name : str
        Name of signal.
    strategy_name : str
        Name of strategy.
        
    Notes
    -----
    Saves positions and P&L DataFrames to separate parquet files.
    File naming: {signal_name}_{strategy_name}_positions.parquet
                 {signal_name}_{strategy_name}_pnl.parquet
    """
    backtests_dir = PROCESSED_DIR / "backtests"
    backtests_dir.mkdir(parents=True, exist_ok=True)
    
    # Save positions
    positions_path = backtests_dir / f"{signal_name}_{strategy_name}_positions.parquet"
    save_parquet(result.positions, positions_path)
    
    # Save P&L
    pnl_path = backtests_dir / f"{signal_name}_{strategy_name}_pnl.parquet"
    save_parquet(result.pnl, pnl_path)


if __name__ == "__main__":
    main()
