"""
Configuration module for paths, constants, and environment settings.

Defines project-wide constants including data paths and caching configuration.
"""

from pathlib import Path
from typing import Final

# Package root (where this config module is installed)
# From src/aponyx/config/__init__.py -> src/aponyx
PACKAGE_ROOT: Final[Path] = Path(__file__).parent.parent

# Config directory (package-relative, included in distribution)
CONFIG_DIR: Final[Path] = PACKAGE_ROOT / "config"

# Project root for development (when working in repo)
# From src/aponyx/config/__init__.py -> src/aponyx -> src -> project_root
PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent.parent.parent

# Data directories (project-level, not package-level)
DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
LOGS_DIR: Final[Path] = PROJECT_ROOT / "logs"

# Cache configuration
CACHE_ENABLED: Final[bool] = True
CACHE_TTL_DAYS: Final[int] = 1  # Daily refresh for market data
CACHE_DIR: Final[Path] = DATA_DIR / "cache"

# Raw data and workflow directories
RAW_DIR: Final[Path] = DATA_DIR / "raw"
DATA_WORKFLOWS_DIR: Final[Path] = DATA_DIR / "workflows"
DATA_REGISTRIES_DIR: Final[Path] = DATA_DIR / ".registries"

# Registry paths (project-level, mutable)
REGISTRY_PATH: Final[Path] = DATA_REGISTRIES_DIR / "registry.json"

# Catalog paths (package-relative, included in distribution)
SIGNAL_CATALOG_PATH: Final[Path] = PACKAGE_ROOT / "models/signal_catalog.json"
STRATEGY_CATALOG_PATH: Final[Path] = PACKAGE_ROOT / "backtest/strategy_catalog.json"

# Bloomberg configuration paths (package-relative, included in distribution)
BLOOMBERG_SECURITIES_PATH: Final[Path] = PACKAGE_ROOT / "data/bloomberg_securities.json"
BLOOMBERG_INSTRUMENTS_PATH: Final[Path] = (
    PACKAGE_ROOT / "data/bloomberg_instruments.json"
)

# Evaluation layer registry paths (project-level, mutable)
SUITABILITY_REGISTRY_PATH: Final[Path] = DATA_REGISTRIES_DIR / "suitability.json"
PERFORMANCE_REGISTRY_PATH: Final[Path] = DATA_REGISTRIES_DIR / "performance.json"


def ensure_directories() -> None:
    """
    Create required directories if they don't exist.

    Creates data, logs, cache, and other necessary directories for the project.
    Safe to call multiple times.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DATA_WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_REGISTRIES_DIR.mkdir(parents=True, exist_ok=True)


# Initialize directories on module import
ensure_directories()
