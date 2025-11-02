"""
Backtest Layer Demonstration - Registry-Based Strategy Evaluation

Demonstrates strategy backtesting using StrategyRegistry for governance:
1. Generate synthetic market data (504 trading days, ~2 years)
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
from example_data import generate_example_data
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


def main() -> None:
    """Run complete backtest demonstration with strategy registry."""
    print("=" * 70)
    print("BACKTEST LAYER DEMONSTRATION")
    print("Registry-Based Strategy Evaluation")
    print("=" * 70)
    print(f"Framework version: {aponyx.__version__}")

    # Generate market data
    print("\n" + "=" * 70)
    print("PART 1: Generate Market Data")
    print("=" * 70)
    
    cdx_df, vix_df, etf_df = generate_example_data(
        start_date="2023-01-01",
        periods=504,  # ~2 years
    )
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
        
        print(f"  OK Complete: {result.metadata['summary']['n_trades']} trades, "
              f"Total P&L: ${result.metadata['summary']['total_pnl']:,.0f}")

    # Compare strategy performance
    print("\n" + "=" * 70)
    print("PART 5: Strategy Performance Comparison")
    print("=" * 70)
    
    print("\n{:<15s} {:>10s} {:>10s} {:>12s} {:>8s} {:>8s}".format(
        "Strategy", "Sharpe", "Sortino", "Max DD", "Trades", "Hit Rate"
    ))
    print("-" * 70)
    
    for name, metrics in metrics_dict.items():
        print("{:<15s} {:>10.2f} {:>10.2f} ${:>10,.0f} {:>8d} {:>7.1%}".format(
            name,
            metrics.sharpe_ratio,
            metrics.sortino_ratio,
            metrics.max_drawdown,
            metrics.n_trades,
            metrics.hit_rate,
        ))

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
    print(f"\n  Configuration:")
    for key, value in metadata['config'].items():
        print(f"    {key}: {value}")
    
    print(f"\n  Summary:")
    for key, value in metadata['summary'].items():
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
    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("\nKey Features Demonstrated:")
    print("  OK StrategyRegistry initialization from JSON catalog")
    print("  OK Query enabled strategies and inspect metadata")
    print("  OK Convert StrategyMetadata to BacktestConfig via to_config()")
    print("  OK Run multiple backtests with different thresholds")
    print("  OK Compare performance across strategies")
    print("  OK Metadata tracking with framework version")
    print("  OK Reproducibility through metadata persistence")
    print("=" * 70)
    
    print("\nNext steps:")
    print("  -> Edit strategy_catalog.json to test new thresholds")
    print("  -> Compare signals by running with different signals")
    print("  -> Analyze trade-by-trade details in BacktestResult")
    print("  -> Use metadata for reproducibility audits")


if __name__ == "__main__":
    main()
