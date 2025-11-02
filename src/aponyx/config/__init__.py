"""
Configuration module for paths, constants, and environment settings.

Defines project-wide constants including data paths and caching configuration.
"""

from pathlib import Path
from typing import Final

# Project root and data directories
# From src/aponyx/config/__init__.py -> src/aponyx -> src -> project_root
PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent.parent.parent
DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
REGISTRY_PATH: Final[Path] = DATA_DIR / "registry.json"
LOGS_DIR: Final[Path] = PROJECT_ROOT / "logs"

# Cache configuration
CACHE_ENABLED: Final[bool] = True
CACHE_TTL_DAYS: Final[int] = 1  # Daily refresh for market data


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


# Initialize directories on module import
ensure_directories()
