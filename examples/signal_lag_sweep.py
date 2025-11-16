"""
Example: Signal lag parameter sweep for balanced strategy.

Tests how different signal_lag values affect Sharpe ratio performance
across all enabled signals using the balanced strategy thresholds.

Data Sources
------------
Bloomberg Terminal (with --bloomberg flag):
    Fetches live data from Bloomberg Terminal.

Cached File Data (default):
    Uses pre-generated synthetic data from data/cache/file/.
    Run generate_synthetic_data.py first if cache is empty.

Usage
-----
With cached synthetic data:
    python examples/signal_lag_sweep.py

With Bloomberg Terminal:
    python examples/signal_lag_sweep.py --bloomberg
"""

import logging
from datetime import datetime

import numpy as np
import pandas as pd

from aponyx.backtest.config import BacktestConfig
from aponyx.backtest.engine import run_backtest
from aponyx.backtest.registry import StrategyRegistry
from aponyx.config import SIGNAL_CATALOG_PATH, STRATEGY_CATALOG_PATH
from aponyx.data.fetch import fetch_cdx, fetch_etf, fetch_vix
from aponyx.data.sources import BloombergSource, FileSource
from aponyx.models.registry import SignalRegistry
from aponyx.models.signals import (
    compute_cdx_etf_basis,
    compute_cdx_vix_gap,
    compute_spread_momentum,
)

logger = logging.getLogger(__name__)


def compute_sharpe_ratio(pnl_series: pd.Series, annualization_factor: float = 252) -> float:
    """
    Compute annualized Sharpe ratio from daily P&L series.

    Parameters
    ----------
    pnl_series : pd.Series
        Daily P&L values.
    annualization_factor : float
        Trading days per year for annualization.

    Returns
    -------
    float
        Annualized Sharpe ratio.
    """
    if len(pnl_series) == 0 or pnl_series.std() == 0:
        return 0.0
    return (pnl_series.mean() / pnl_series.std()) * np.sqrt(annualization_factor)


def run_lag_sweep(
    signal_name: str,
    signal_series: pd.Series,
    spread_series: pd.Series,
    lag_values: list[int],
    strategy_name: str = "balanced",
) -> pd.DataFrame:
    """
    Test multiple signal_lag values and compute Sharpe ratios.

    Parameters
    ----------
    signal_name : str
        Name of the signal being tested.
    signal_series : pd.Series
        Computed signal values.
    spread_series : pd.Series
        CDX spread data for P&L calculation.
    lag_values : list[int]
        List of signal_lag values to test.
    strategy_name : str
        Strategy profile name from catalog.

    Returns
    -------
    pd.DataFrame
        Results with columns: signal_lag, sharpe_ratio, avg_pnl, pnl_std, num_trades.
    """
    logger.info("Running lag sweep for %s with %s strategy", signal_name, strategy_name)
    
    # Get strategy thresholds
    strategy_registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    strategy_metadata = strategy_registry.get_metadata(strategy_name)
    
    results = []
    
    for lag in lag_values:
        config = BacktestConfig(
            entry_threshold=strategy_metadata.entry_threshold,
            exit_threshold=strategy_metadata.exit_threshold,
            signal_lag=lag,
        )
        
        backtest_result = run_backtest(signal_series, spread_series, config)
        
        sharpe = compute_sharpe_ratio(backtest_result.pnl["net_pnl"])
        avg_pnl = backtest_result.pnl["net_pnl"].mean()
        pnl_std = backtest_result.pnl["net_pnl"].std()
        
        # Count position changes as proxy for trades
        position_changes = backtest_result.positions["position"].diff().abs()
        num_trades = int(position_changes.sum() / 2)  # Divide by 2 to count round trips
        
        results.append({
            "signal_lag": lag,
            "sharpe_ratio": sharpe,
            "avg_pnl": avg_pnl,
            "pnl_std": pnl_std,
            "num_trades": num_trades,
        })
        
        logger.debug(
            "Lag %d: Sharpe=%.2f, Trades=%d",
            lag,
            sharpe,
            num_trades,
        )
    
    return pd.DataFrame(results)


def main(use_bloomberg: bool = False) -> None:
    """
    Run signal lag sweep for all enabled signals.
    
    Parameters
    ----------
    use_bloomberg : bool, default False
        If True, fetch data from Bloomberg Terminal.
        If False, use cached file data from data/cache/file/.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    logger.info("Starting signal lag parameter sweep")
    
    if use_bloomberg:
        # Fetch Bloomberg data
        logger.info("Fetching Bloomberg data")
        source = BloombergSource()
        
        # Fetch last 2 years of data
        start_date = "2023-01-01"
        end_date = "2025-01-01"
        
        cdx_df = fetch_cdx(
            source=source,
            security="cdx_ig_5y",
            start_date=start_date,
            end_date=end_date,
        )
        
        etf_df = fetch_etf(
            source=source,
            security="hyg",
            start_date=start_date,
            end_date=end_date,
        )
        
        vix_df = fetch_vix(
            source=source,
            start_date=start_date,
            end_date=end_date,
        )
        
        logger.info(
            "Data loaded: CDX=%d rows, ETF=%d rows, VIX=%d rows",
            len(cdx_df),
            len(etf_df),
            len(vix_df),
        )
    else:
        # Use cached file data
        logger.info("Loading cached file data")
        from pathlib import Path
        
        cache_dir = Path("data/cache/file")
        
        # Check if cache files exist
        required_files = {
            "cdx_cdx_ig_5y.parquet": "CDX IG 5Y",
            "etf_hyg.parquet": "HYG ETF",
            "vix_vix.parquet": "VIX",
        }
        
        missing_files = [
            name for file, name in required_files.items()
            if not (cache_dir / file).exists()
        ]
        
        if missing_files:
            logger.error("Required cache files not found: %s", ", ".join(missing_files))
            print("\nERROR: Cache files not found!")
            print("=" * 80)
            print("\nMissing data files:")
            for name in missing_files:
                print(f"  - {name}")
            print("\nPlease generate synthetic data first:")
            print("  python -m aponyx.notebooks.generate_synthetic_data")
            print("\nOr use Bloomberg Terminal:")
            print(f"  python {__file__} --bloomberg")
            print("=" * 80)
            raise FileNotFoundError(f"Missing cache files: {', '.join(missing_files)}")
        
        # Fetch from cached files
        cdx_df = fetch_cdx(
            source=FileSource(cache_dir / "cdx_cdx_ig_5y.parquet"),
            security="cdx_ig_5y",
        )
        
        etf_df = fetch_etf(
            source=FileSource(cache_dir / "etf_hyg.parquet"),
            security="hyg",
        )
        
        vix_df = fetch_vix(
            source=FileSource(cache_dir / "vix_vix.parquet"),
        )
        
        logger.info(
            "Data loaded: CDX=%d rows, ETF=%d rows, VIX=%d rows",
            len(cdx_df),
            len(etf_df),
            len(vix_df),
        )
    
    # Test lag values from 0 (same-day) to 5 days
    lag_values = [0, 1, 2, 3, 4, 5]
    
    # Get enabled signals
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    enabled_signals = list(signal_registry.get_enabled().keys())
    
    logger.info("Testing %d signals with lag values: %s", len(enabled_signals), lag_values)
    
    # Compute signals
    signals = {
        "cdx_etf_basis": compute_cdx_etf_basis(cdx_df, etf_df),
        "cdx_vix_gap": compute_cdx_vix_gap(cdx_df, vix_df),
        "spread_momentum": compute_spread_momentum(cdx_df),
    }
    
    # Run sweep for each signal
    all_results = {}
    
    for signal_name in enabled_signals:
        if signal_name not in signals:
            logger.warning("Signal %s not found in computed signals, skipping", signal_name)
            continue
            
        logger.info("Testing %s signal", signal_name)
        results_df = run_lag_sweep(
            signal_name=signal_name,
            signal_series=signals[signal_name],
            spread_series=cdx_df["spread"],
            lag_values=lag_values,
            strategy_name="balanced",
        )
        all_results[signal_name] = results_df
    
    # Display results
    print("\n" + "="*80)
    print("Signal Lag Parameter Sweep Results (Balanced Strategy)")
    print(f"Data Source: {'Bloomberg Terminal' if use_bloomberg else 'Cached File Data'}")
    print("="*80 + "\n")
    
    for signal_name, results_df in all_results.items():
        print(f"\n{signal_name.upper()}")
        print("-" * 80)
        print(results_df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
        
        # Highlight best Sharpe
        best_idx = results_df["sharpe_ratio"].abs().idxmax()
        best_lag = results_df.loc[best_idx, "signal_lag"]
        best_sharpe = results_df.loc[best_idx, "sharpe_ratio"]
        print(f"\nBest Sharpe: {best_sharpe:.4f} at lag={int(best_lag)}")
    
    print("\n" + "="*80)
    print(f"Sweep completed at {datetime.now().isoformat()}")
    print("="*80 + "\n")
    
    logger.info("Signal lag sweep complete")


if __name__ == "__main__":
    import sys
    
    # Check command line argument for Bloomberg usage
    use_bloomberg = "--bloomberg" in sys.argv
    
    if use_bloomberg:
        logger.info("Bloomberg mode enabled via --bloomberg flag")
    else:
        logger.info("Using cached file data (pass --bloomberg to use Bloomberg Terminal)")
    
    main(use_bloomberg=use_bloomberg)
