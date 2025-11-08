"""
Backtest Layer Demonstration - Registry-Based Strategy Evaluation

Demonstrates strategy backtesting using StrategyRegistry for governance:
1. Fetch market data from Bloomberg Terminal (primary) or synthetic fallback
2. Compute signal using SignalRegistry
3. Initialize StrategyRegistry from JSON catalog
4. Run backtests for all enabled strategies (conservative, balanced, aggressive)
5. Compare performance across different threshold configurations
6. Track metadata with version info for reproducibility

The registry pattern enables:
- Centralized strategy catalog management
- Easy comparison of threshold configurations
- Clear metadata tracking with version info
- Reproducible backtest execution

Output: Comparative performance metrics, metadata tracking

Configuration:
  - Signal: cdx_etf_basis (credit-equity basis)
  - Strategies: conservative, balanced, aggressive (from catalog)
  - Position size: $10MM notional
  - Transaction cost: 1.0 bps
  - DV01: $4,750 per $1MM notional
"""

import logging
from pathlib import Path

import aponyx
from .example_data import generate_example_data
from aponyx.data import fetch_cdx, fetch_vix, fetch_etf
from aponyx.models import (
    SignalRegistry,
    SignalConfig,
    compute_registered_signals,
)
from aponyx.backtest import (
    StrategyRegistry,
    run_backtest,
    compute_performance_metrics,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global flag to track data source
_using_bloomberg = False


def main() -> None:
    """Run complete backtest demonstration with strategy registry."""
    global _using_bloomberg

    print("=" * 70)
    print("BACKTEST LAYER DEMONSTRATION")
    print("Registry-Based Strategy Evaluation")
    print("=" * 70)
    print(f"Framework version: {aponyx.__version__}")

    # Fetch market data - try Bloomberg first
    print("\n" + "=" * 70)
    print("PART 1: Fetch Market Data")
    print("=" * 70)

    print("\nAttempting Bloomberg Terminal connection...")
    try:
        from aponyx.data import BloombergSource

        source = BloombergSource()
        logger.info("Bloomberg Terminal connection established")
        print("  OK Bloomberg Terminal available")
        print("  Fetching data from 2024-01-01 to present...")
        _using_bloomberg = True

        cdx_df = fetch_cdx(source, security="cdx_ig_5y", start_date="2024-01-01")
        vix_df = fetch_vix(source, start_date="2024-01-01")
        etf_df = fetch_etf(source, security="hyg", start_date="2024-01-01")

        logger.info("Fetched market data from Bloomberg: %d days", len(cdx_df))
        print(f"\n  OK Generated {len(cdx_df)} days of market data from Bloomberg")
        print(f"  Date range: {cdx_df.index.min().date()} to {cdx_df.index.max().date()}")

    except (ImportError, ModuleNotFoundError) as e:
        logger.warning("Bloomberg Terminal not available: missing xbbg or blpapi module")
        print("  ! Bloomberg Terminal not installed")
        print(f"    Reason: {e}")
        print("\n  Falling back to synthetic data...")
        _using_bloomberg = False

        cdx_df, vix_df, etf_df = generate_example_data(
            start_date="2023-01-01",
            periods=504,  # ~2 years
        )
        logger.info("Generated %d days of synthetic data", len(cdx_df))
        print(f"\n  OK Generated {len(cdx_df)} days of synthetic data")
        print(f"  Date range: {cdx_df.index.min().date()} to {cdx_df.index.max().date()}")

    except BaseException as e:
        # Catch pytest.Skipped and other xbbg errors
        error_str = str(e).lower()
        error_type = str(type(e).__name__).lower()
        if "blpapi" in error_str or "could not import" in error_str or "skipped" in error_type:
            logger.warning("Bloomberg Terminal not available: blpapi module missing")
            print("  ! Bloomberg Terminal not installed")
        else:
            logger.warning("Bloomberg Terminal connection failed: %s", e)
            print("  ! Bloomberg Terminal not running or authentication failed")
            print(f"    Reason: {type(e).__name__}: {e}")

        print("\n  Falling back to synthetic data...")
        _using_bloomberg = False

        cdx_df, vix_df, etf_df = generate_example_data(
            start_date="2023-01-01",
            periods=504,  # ~2 years
        )
        logger.info("Generated %d days of synthetic data", len(cdx_df))
        print(f"\n  OK Generated {len(cdx_df)} days of synthetic data")
        print(f"  Date range: {cdx_df.index.min().date()} to {cdx_df.index.max().date()}")

    # Compute signal using registry
    print("\n" + "=" * 70)
    print("PART 2: Compute Signal via Registry")
    print("=" * 70)

    signal_catalog = Path("src/aponyx/models/signal_catalog.json")
    signal_registry = SignalRegistry(signal_catalog)
    print(f"\n  OK Loaded signal catalog: {signal_catalog}")

    market_data = {"cdx": cdx_df, "vix": vix_df, "etf": etf_df}
    signal_config = SignalConfig(lookback=20, min_periods=10)

    signals = compute_registered_signals(signal_registry, market_data, signal_config)
    print(f"  OK Computed {len(signals)} signals")

    # Use cdx_etf_basis for demonstration
    signal_name = "cdx_etf_basis"
    signal = signals[signal_name]
    print(f"\n  Using signal: {signal_name}")
    print(f"  Valid observations: {signal.notna().sum()}")
    print(f"  Mean: {signal.mean():.3f}, Std: {signal.std():.3f}")
    print(f"  Range: [{signal.min():.2f}, {signal.max():.2f}]")

    # Initialize strategy registry
    print("\n" + "=" * 70)
    print("PART 3: Initialize Strategy Registry")
    print("=" * 70)

    strategy_catalog = Path("src/aponyx/backtest/strategy_catalog.json")
    strategy_registry = StrategyRegistry(strategy_catalog)
    print(f"\n  OK Loaded strategy catalog: {strategy_catalog}")

    # Query enabled strategies
    enabled_strategies = strategy_registry.get_enabled()
    print(f"  Found {len(enabled_strategies)} enabled strategies:")

    for name, metadata in enabled_strategies.items():
        print(f"\n  {name}:")
        print(f"    Description: {metadata.description}")
        print(f"    Entry threshold: {metadata.entry_threshold}")
        print(f"    Exit threshold: {metadata.exit_threshold}")

    # Run backtests for all enabled strategies
    print("\n" + "=" * 70)
    print("PART 4: Run Backtests for All Strategies")
    print("=" * 70)

    results = {}
    metrics_dict = {}

    for name, metadata in enabled_strategies.items():
        print(f"\nBacktesting {name} strategy...")

        # Convert metadata to BacktestConfig
        config = metadata.to_config(
            position_size=10.0,  # $10MM notional
            transaction_cost_bps=1.0,
            max_holding_days=None,
            dv01_per_million=4750.0,
        )

        # Run backtest
        result = run_backtest(signal, cdx_df["spread"], config)
        results[name] = result

        # Compute metrics
        metrics = compute_performance_metrics(result.pnl, result.positions)
        metrics_dict[name] = metrics

        print(
            f"  OK Complete: {result.metadata['summary']['n_trades']} trades, "
            f"Total P&L: ${result.metadata['summary']['total_pnl']:,.0f}"
        )

    # Compare strategy performance
    print("\n" + "=" * 70)
    print("PART 5: Strategy Performance Comparison")
    print("=" * 70)

    print(
        "\n{:<15s} {:>10s} {:>10s} {:>12s} {:>8s} {:>8s}".format(
            "Strategy", "Sharpe", "Sortino", "Max DD", "Trades", "Hit Rate"
        )
    )
    print("-" * 70)

    for name, metrics in metrics_dict.items():
        print(
            "{:<15s} {:>10.2f} {:>10.2f} ${:>10,.0f} {:>8d} {:>7.1%}".format(
                name,
                metrics.sharpe_ratio,
                metrics.sortino_ratio,
                metrics.max_drawdown,
                metrics.n_trades,
                metrics.hit_rate,
            )
        )

    # Detailed metrics for best strategy
    print("\n" + "=" * 70)
    print("PART 6: Detailed Metrics (Best Sharpe)")
    print("=" * 70)

    best_strategy = max(metrics_dict.items(), key=lambda x: x[1].sharpe_ratio)
    best_name, best_metrics = best_strategy

    print(f"\nBest performing strategy: {best_name}")
    print("-" * 70)
    print(f"  Sharpe Ratio:           {best_metrics.sharpe_ratio:>8.2f}")
    print(f"  Sortino Ratio:          {best_metrics.sortino_ratio:>8.2f}")
    print(f"  Calmar Ratio:           {best_metrics.calmar_ratio:>8.2f}")
    print(f"  Max Drawdown:           ${best_metrics.max_drawdown:>8,.0f}")
    print(f"  Total Return:           ${best_metrics.total_return:>8,.0f}")
    print(f"  Annualized Return:      ${best_metrics.annualized_return:>8,.0f}")
    print(f"  Annualized Volatility:  ${best_metrics.annualized_volatility:>8,.0f}")
    print("-" * 70)
    print(f"  Hit Rate:               {best_metrics.hit_rate:>8.1%}")
    print(f"  Average Win:            ${best_metrics.avg_win:>8,.0f}")
    print(f"  Average Loss:           ${best_metrics.avg_loss:>8,.0f}")
    print(f"  Win/Loss Ratio:         {best_metrics.win_loss_ratio:>8.2f}")
    print(f"  Number of Trades:       {best_metrics.n_trades:>8}")
    print(f"  Avg Holding Days:       {best_metrics.avg_holding_days:>8.1f}")
    print("-" * 70)

    # Metadata tracking demonstration
    print("\n" + "=" * 70)
    print("PART 7: Metadata Tracking for Reproducibility")
    print("=" * 70)

    print(f"\nMetadata from {best_name} backtest:")
    metadata = results[best_name].metadata

    print(f"  Timestamp: {metadata['timestamp']}")
    print(f"  Framework version: {aponyx.__version__}")
    print(f"  Signal: {signal_name}")
    print("\n  Configuration:")
    for key, value in metadata["config"].items():
        print(f"    {key}: {value}")

    print("\n  Summary:")
    for key, value in metadata["summary"].items():
        if isinstance(value, float):
            print(f"    {key}: {value:.2f}")
        else:
            print(f"    {key}: {value}")

    # Save metadata example
    from aponyx.persistence import save_json
    from aponyx.config import LOGS_DIR

    metadata_path = save_json(
        metadata,
        LOGS_DIR / f"backtest_{best_name}_metadata.json",
    )
    print(f"\n  OK Saved metadata to: {metadata_path}")

    # Summary
    data_source = "Bloomberg Terminal" if _using_bloomberg else "Synthetic data"
    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print(f"\nData source used: {data_source}")
    print("\nKey Features Demonstrated:")
    if _using_bloomberg:
        print("  OK Real market data from Bloomberg Terminal")
        print("  OK Backtest performance on live credit/equity data")
    else:
        print("  OK Graceful fallback when Bloomberg unavailable")
    print("  OK StrategyRegistry initialization from JSON catalog")
    print("  OK Query enabled strategies and inspect metadata")
    print("  OK Convert StrategyMetadata to BacktestConfig via to_config()")
    print("  OK Run multiple backtests with different thresholds")
    print("  OK Compare performance across strategies")
    print("  OK Metadata tracking with framework version")
    print("  OK Reproducibility through metadata persistence")
    print("=" * 70)

    print("\nNext steps:")
    if not _using_bloomberg:
        print("  -> Install Bloomberg Terminal and xbbg to use real data")
    print("  -> Edit strategy_catalog.json to test new thresholds")
    print("  -> Compare signals by running with different signals")
    print("  -> Analyze trade-by-trade details in BacktestResult")
    print("  -> Use metadata for reproducibility audits")


if __name__ == "__main__":
    main()
