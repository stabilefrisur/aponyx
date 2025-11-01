"""
Configuration module for paths, constants, and environment settings.

Defines project-wide constants including instrument universe, data paths,
and default parameters for the CDX overlay strategy.
"""

from pathlib import Path
from typing import Final, Any

# Project root and data directories
# From src/aponyx/config/__init__.py -> src/aponyx -> src -> project_root
PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent.parent.parent
DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
REGISTRY_PATH: Final[Path] = DATA_DIR / "registry.json"
LOGS_DIR: Final[Path] = PROJECT_ROOT / "logs"

# Instrument universe for CDX overlay strategy
# Security identifiers for use with Bloomberg ticker registry
CDX_SECURITIES: Final[list[str]] = [
    "cdx_ig_5y",
    "cdx_ig_10y",
    "cdx_hy_5y",
    "itrx_xover_5y",
    "itrx_eur_5y",
]

# ETF securities for signal generation (not direct trading)
ETF_SECURITIES: Final[list[str]] = ["hyg", "lqd"]

# Market data identifiers
MARKET_DATA_TICKERS: Final[dict[str, str]] = {
    "VIX": "^VIX",
    "SPX": "^GSPC",
}

# Default signal parameters
DEFAULT_SIGNAL_PARAMS: Final[dict[str, int | float]] = {
    "momentum_window": 5,
    "volatility_window": 20,
    "z_score_window": 60,
    "basis_threshold": 0.5,
}

# Data versioning
DATA_VERSION: Final[str] = "0.1.0"

# Cache configuration
CACHE_ENABLED: Final[bool] = True
CACHE_TTL_DAYS: Final[dict[str, int | None]] = {
    "cdx": 1,  # Daily refresh for market data
    "vix": 1,
    "etf": 1,
}

# Default data sources (can be overridden per fetch call)
# Set to None to require explicit source in fetch calls
DEFAULT_DATA_SOURCES: Final[dict[str, Any]] = {
    "cdx": None,
    "vix": None,
    "etf": None,
}


def ensure_directories() -> None:
    """
    Create required directories if they don't exist.

    Creates data, logs, and other necessary directories for the project.
    Safe to call multiple times.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "raw").mkdir(exist_ok=True)
    (DATA_DIR / "processed").mkdir(exist_ok=True)
    (DATA_DIR / "cache").mkdir(exist_ok=True)


# Initialize directories on module import
ensure_directories()
