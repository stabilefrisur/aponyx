"""
Bloomberg Terminal Integration Demonstration

Demonstrates Bloomberg Terminal data fetching with BloombergSource:
1. Initialize BloombergSource provider
2. Fetch CDX, VIX, and ETF data using Bloomberg Terminal
3. Use ticker registry for security lookup
4. Handle connection errors gracefully

**IMPORTANT**: This demo requires an active Bloomberg Terminal session.
If Terminal is not available, the demo will print a warning and exit gracefully.

Output:
  - DataFrames from Bloomberg Terminal (if available)
  - Graceful error handling when Terminal unavailable

Key Features:
  - BloombergSource provider for Bloomberg Terminal via xbbg
  - get_bloomberg_ticker() for security-to-ticker mapping
  - Unified fetch interface (same as FileSource)
  - Graceful handling when Terminal unavailable
"""

import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run Bloomberg Terminal integration demonstration."""
    print("=" * 70)
    print("BLOOMBERG TERMINAL INTEGRATION DEMONSTRATION")
    print("=" * 70)
    print("\nWARNING: This demo requires an active Bloomberg Terminal session")
    print("If Terminal is not available, demo will exit gracefully\n")
    
    try:
        # Import Bloomberg-specific modules
        from aponyx.data import BloombergSource, fetch_cdx, fetch_vix, fetch_etf
        from aponyx.data.bloomberg_config import get_bloomberg_ticker
        
        print("=" * 70)
        print("PART 1: Initialize Bloomberg Source")
        print("=" * 70)
        
        # Initialize Bloomberg source (will fail if Terminal not available)
        print("\nInitializing BloombergSource...")
        source = BloombergSource()
        print("  OK Bloomberg Terminal connection established")
        
        print("\n" + "=" * 70)
        print("PART 2: Ticker Lookup")
        print("=" * 70)
        
        # Demonstrate ticker lookup
        print("\nLooking up Bloomberg tickers...")
        
        cdx_ticker = get_bloomberg_ticker("cdx_ig_5y")
        print(f"  CDX IG 5Y: {cdx_ticker}")
        
        vix_ticker = get_bloomberg_ticker("vix")
        print(f"  VIX: {vix_ticker}")
        
        hyg_ticker = get_bloomberg_ticker("hyg")
        print(f"  HYG ETF: {hyg_ticker}")
        
        print("\n" + "=" * 70)
        print("PART 3: Fetch Data from Bloomberg")
        print("=" * 70)
        
        # Fetch CDX data (cache disabled to demonstrate Bloomberg fetch)
        print("\nFetching CDX IG 5Y data from Bloomberg...")
        cdx_df = fetch_cdx(
            source,
            security="cdx_ig_5y",
            start_date="2024-01-01",
            use_cache=False,
        )
        print(f"  OK Fetched {len(cdx_df)} rows")
        print(f"  Columns: {cdx_df.columns.tolist()}")
        print(f"  Date range: {cdx_df.index.min().date()} to {cdx_df.index.max().date()}")
        print(f"  Spread range: [{cdx_df['spread'].min():.2f}, {cdx_df['spread'].max():.2f}] bps")
        
        # Fetch VIX data (cache disabled to demonstrate Bloomberg fetch)
        print("\nFetching VIX data from Bloomberg...")
        vix_df = fetch_vix(
            source,
            start_date="2024-01-01",
            use_cache=False,
        )
        print(f"  OK Fetched {len(vix_df)} rows")
        print(f"  Columns: {vix_df.columns.tolist()}")
        print(f"  Date range: {vix_df.index.min().date()} to {vix_df.index.max().date()}")
        print(f"  Level range: [{vix_df['level'].min():.2f}, {vix_df['level'].max():.2f}]")
        
        # Fetch ETF data (cache disabled to demonstrate Bloomberg fetch)
        print("\nFetching HYG ETF data from Bloomberg...")
        etf_df = fetch_etf(
            source,
            security="hyg",
            start_date="2024-01-01",
            use_cache=False,
        )
        print(f"  OK Fetched {len(etf_df)} rows")
        print(f"  Columns: {etf_df.columns.tolist()}")
        print(f"  Date range: {etf_df.index.min().date()} to {etf_df.index.max().date()}")
        print(f"  Spread range: [{etf_df['spread'].min():.2f}, {etf_df['spread'].max():.2f}]")
        
        print("\n" + "=" * 70)
        print("DEMONSTRATION COMPLETE")
        print("=" * 70)
        print("\nKey Features Demonstrated:")
        print("  OK BloombergSource initialization")
        print("  OK Ticker registry lookup")
        print("  OK Fetch CDX data from Terminal")
        print("  OK Fetch VIX data from Terminal")
        print("  OK Fetch ETF data from Terminal")
        print("  OK Same API as FileSource (provider abstraction)")
        print("=" * 70)
        
    except (ImportError, ModuleNotFoundError) as e:
        print("\n" + "!" * 70)
        print("BLOOMBERG TERMINAL NOT AVAILABLE")
        print("!" * 70)
        print("\nReason: Missing xbbg dependency or Bloomberg Terminal not installed")
        print(f"Error: {e}")
        print("\nTo use Bloomberg integration:")
        print("  1. Install Bloomberg Terminal on your machine")
        print("  2. Ensure Terminal is running and logged in")
        print("  3. Install xbbg: pip install xbbg")
        print("\nDemo exiting gracefully...")
        print("!" * 70)
        sys.exit(0)
        
    except BaseException as e:
        # Catch pytest.Skipped and other xbbg errors (including non-Exception types)
        error_str = str(e).lower()
        error_type = str(type(e).__name__).lower()
        if "blpapi" in error_str or "could not import" in error_str or "skipped" in error_type:
            print("\n" + "!" * 70)
            print("BLOOMBERG TERMINAL NOT AVAILABLE")
            print("!" * 70)
            print("\nReason: Missing blpapi module (Bloomberg Terminal not installed)")
            print(f"Error: {type(e).__name__}: {e}")
            print("\nTo use Bloomberg integration:")
            print("  1. Install Bloomberg Terminal on your machine")
            print("  2. Ensure Terminal is running and logged in")
            print("  3. Install required Bloomberg Python API")
            print("\nDemo exiting gracefully...")
            print("!" * 70)
            sys.exit(0)
        
        print("\n" + "!" * 70)
        print("BLOOMBERG TERMINAL CONNECTION ERROR")
        print("!" * 70)
        print("\nReason: Terminal not running or authentication issue")
        print(f"Error: {type(e).__name__}: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure Bloomberg Terminal is running")
        print("  2. Log in to Terminal and accept terms")
        print("  3. Try fetching data manually in Terminal first")
        print("  4. Check xbbg installation: pip list | grep xbbg")
        print("\nDemo exiting gracefully...")
        print("!" * 70)
        sys.exit(0)


if __name__ == "__main__":
    main()
