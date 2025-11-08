"""
Models Layer Demonstration - Registry-Based Signal Workflow

Demonstrates signal generation using SignalRegistry for governance:
1. Fetch market data from Bloomberg Terminal (primary) or synthetic fallback
2. Initialize SignalRegistry from JSON catalog
3. Query enabled signals and inspect metadata
4. Compute all signals in batch using compute_registered_signals()
5. Analyze individual signal statistics and characteristics
6. Show signal cross-correlations

The registry pattern enables:
- Centralized signal catalog management
- Easy enable/disable for experiments
- Clear metadata and data requirements
- Batch signal computation with error handling

Output: Signal statistics, correlations, and sample values

Note: All signals follow the convention:
  - Positive values -> Long credit risk (buy CDX/sell protection)
  - Negative values -> Short credit risk (sell CDX/buy protection)
"""

import logging
from pathlib import Path

from .example_data import generate_example_data
from aponyx.data import fetch_cdx, fetch_vix, fetch_etf
from aponyx.models import (
    SignalRegistry,
    SignalConfig,
    compute_registered_signals,
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
    """Run the models layer demonstration with registry pattern."""
    global _using_bloomberg

    print("=" * 70)
    print("MODELS LAYER DEMONSTRATION")
    print("Registry-Based Signal Workflow")
    print("=" * 70)

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
        print(f"  OK CDX IG 5Y: {len(cdx_df)} rows, spread mean={cdx_df['spread'].mean():.2f} bps")
        print(f"  OK VIX: {len(vix_df)} rows, level mean={vix_df['level'].mean():.2f}")
        print(f"  OK HYG ETF: {len(etf_df)} rows, spread mean={etf_df['spread'].mean():.2f}")

    except (ImportError, ModuleNotFoundError) as e:
        logger.warning("Bloomberg Terminal not available: missing xbbg or blpapi module")
        print("  ! Bloomberg Terminal not installed")
        print(f"    Reason: {e}")
        print("\n  Falling back to synthetic data...")
        _using_bloomberg = False

        cdx_df, vix_df, etf_df = generate_example_data(periods=252)
        logger.info("Generated %d days of synthetic data", len(cdx_df))
        print(f"  OK CDX IG 5Y: {len(cdx_df)} rows, spread mean={cdx_df['spread'].mean():.2f} bps")
        print(f"  OK VIX: {len(vix_df)} rows, level mean={vix_df['level'].mean():.2f}")
        print(f"  OK HYG ETF: {len(etf_df)} rows, spread mean={etf_df['spread'].mean():.2f}")

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

        cdx_df, vix_df, etf_df = generate_example_data(periods=252)
        logger.info("Generated %d days of synthetic data", len(cdx_df))
        print(f"  OK CDX IG 5Y: {len(cdx_df)} rows, spread mean={cdx_df['spread'].mean():.2f} bps")
        print(f"  OK VIX: {len(vix_df)} rows, level mean={vix_df['level'].mean():.2f}")
        print(f"  OK HYG ETF: {len(etf_df)} rows, spread mean={etf_df['spread'].mean():.2f}")

    # Initialize signal registry
    print("\n" + "=" * 70)
    print("PART 2: Initialize Signal Registry")
    print("=" * 70)

    catalog_path = Path("src/aponyx/models/signal_catalog.json")
    print(f"\nLoading signal catalog from: {catalog_path}")

    registry = SignalRegistry(catalog_path)
    print("  OK Loaded signal registry")

    # Query enabled signals
    print("\nQuerying enabled signals...")
    enabled_signals = registry.get_enabled()

    print(f"  Found {len(enabled_signals)} enabled signals:")
    for name, metadata in enabled_signals.items():
        print(f"\n  {name}:")
        print(f"    Description: {metadata.description}")
        print(f"    Function: {metadata.compute_function_name}")
        print(f"    Data requirements: {metadata.data_requirements}")
        print(f"    Enabled: {metadata.enabled}")

    # Prepare market data dict
    print("\n" + "=" * 70)
    print("PART 3: Compute All Signals via Registry")
    print("=" * 70)

    market_data = {
        "cdx": cdx_df,
        "vix": vix_df,
        "etf": etf_df,
    }

    print("\nPrepared market data dict:")
    for key, df in market_data.items():
        print(f"  {key}: {len(df)} rows, columns={df.columns.tolist()}")

    # Configure signal parameters
    signal_config = SignalConfig(lookback=20, min_periods=10)
    print("\nSignal configuration:")
    print(f"  Lookback: {signal_config.lookback}")
    print(f"  Min periods: {signal_config.min_periods}")

    # Compute all signals
    print("\nComputing signals via registry...")
    signals = compute_registered_signals(registry, market_data, signal_config)

    print(f"  OK Computed {len(signals)} signals")
    for name in signals.keys():
        print(f"    - {name}")

    # Analyze signal statistics
    print("\n" + "=" * 70)
    print("PART 4: Signal Statistics")
    print("=" * 70)

    for name, signal in signals.items():
        valid = signal.dropna()
        print(f"\n{name}:")
        print(f"  Valid observations: {len(valid)}")
        print(f"  Mean: {valid.mean():.3f}")
        print(f"  Std: {valid.std():.3f}")
        print(f"  Range: [{valid.min():.2f}, {valid.max():.2f}]")
        print(f"  Null values: {signal.isna().sum()}")

    # Signal correlations
    print("\n" + "=" * 70)
    print("PART 5: Signal Cross-Correlations")
    print("=" * 70)

    import pandas as pd

    signal_df = pd.DataFrame(signals)

    print("\nCorrelation matrix:")
    corr_matrix = signal_df.corr()
    print(corr_matrix.to_string(float_format="%.3f"))

    # Identify high correlations
    print("\nHigh correlations (|r| > 0.5):")
    for i in range(len(corr_matrix.columns)):
        for j in range(i + 1, len(corr_matrix.columns)):
            corr = corr_matrix.iloc[i, j]
            if abs(corr) > 0.5:
                sig1 = corr_matrix.columns[i]
                sig2 = corr_matrix.columns[j]
                print(f"  {sig1} <-> {sig2}: {corr:.3f}")

    # Sample signal values
    print("\n" + "=" * 70)
    print("PART 6: Sample Signal Values (Last 10 Days)")
    print("=" * 70)

    print("\n" + signal_df.tail(10).to_string(float_format="%.3f"))

    # Signal distribution summary
    print("\n" + "=" * 70)
    print("PART 7: Signal Distribution Summary")
    print("=" * 70)

    threshold = 1.5
    print(f"\nUsing entry threshold: +/-{threshold}")

    for name, signal in signals.items():
        long_signals = (signal > threshold).sum()
        short_signals = (signal < -threshold).sum()
        neutral_signals = ((signal >= -threshold) & (signal <= threshold)).sum()

        total = long_signals + short_signals + neutral_signals

        print(f"\n{name}:")
        print(f"  Long (>{threshold}):      {long_signals:4d} ({long_signals/total:5.1%})")
        print(f"  Short (<-{threshold}):    {short_signals:4d} ({short_signals/total:5.1%})")
        print(
            f"  Neutral ({-threshold} to {threshold}): {neutral_signals:4d} ({neutral_signals/total:5.1%})"
        )

    # Summary
    data_source = "Bloomberg Terminal" if _using_bloomberg else "Synthetic data"
    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print(f"\nData source used: {data_source}")
    print("\nKey Features Demonstrated:")
    if _using_bloomberg:
        print("  OK Real market data from Bloomberg Terminal")
        print("  OK Signals computed on live credit/equity data")
    else:
        print("  OK Graceful fallback when Bloomberg unavailable")
    print("  OK SignalRegistry initialization from JSON catalog")
    print("  OK Query enabled signals and inspect metadata")
    print("  OK Batch signal computation via compute_registered_signals()")
    print("  OK Individual signal statistics and distributions")
    print("  OK Signal cross-correlation analysis")
    print("  OK Governance through centralized catalog")
    print("=" * 70)

    print("\nNext steps:")
    if not _using_bloomberg:
        print("  -> Install Bloomberg Terminal and xbbg to use real data")
    print("  -> See backtest_demo.py for strategy evaluation")
    print("  -> Edit signal_catalog.json to enable/disable signals")
    print("  -> Adjust SignalConfig parameters for different lookbacks")


if __name__ == "__main__":
    main()
