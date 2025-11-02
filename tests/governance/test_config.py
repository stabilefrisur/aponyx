"""
Unit tests for governance config pillar.
"""

from pathlib import Path

from aponyx.config import (
    PROJECT_ROOT,
    DATA_DIR,
    LOGS_DIR,
    CACHE_DIR,
    REGISTRY_PATH,
    SIGNAL_CATALOG_PATH,
    STRATEGY_CATALOG_PATH,
    BLOOMBERG_SECURITIES_PATH,
    BLOOMBERG_INSTRUMENTS_PATH,
    CACHE_ENABLED,
    CACHE_TTL_DAYS,
)


def test_config_paths_are_absolute() -> None:
    """Test that all config paths are absolute paths."""
    assert PROJECT_ROOT.is_absolute()
    assert DATA_DIR.is_absolute()
    assert LOGS_DIR.is_absolute()
    assert CACHE_DIR.is_absolute()
    assert REGISTRY_PATH.is_absolute()
    assert SIGNAL_CATALOG_PATH.is_absolute()
    assert STRATEGY_CATALOG_PATH.is_absolute()
    assert BLOOMBERG_SECURITIES_PATH.is_absolute()
    assert BLOOMBERG_INSTRUMENTS_PATH.is_absolute()


def test_config_paths_exist() -> None:
    """Test that configured paths exist or can be created."""
    # Directories created by ensure_directories()
    assert DATA_DIR.exists()
    assert LOGS_DIR.exists()
    assert CACHE_DIR.exists()
    assert (DATA_DIR / "raw").exists()
    assert (DATA_DIR / "processed").exists()


def test_catalog_files_exist() -> None:
    """Test that catalog JSON files exist."""
    assert SIGNAL_CATALOG_PATH.exists(), f"Signal catalog not found: {SIGNAL_CATALOG_PATH}"
    assert STRATEGY_CATALOG_PATH.exists(), f"Strategy catalog not found: {STRATEGY_CATALOG_PATH}"
    assert BLOOMBERG_SECURITIES_PATH.exists(), f"Bloomberg securities not found: {BLOOMBERG_SECURITIES_PATH}"
    assert BLOOMBERG_INSTRUMENTS_PATH.exists(), f"Bloomberg instruments not found: {BLOOMBERG_INSTRUMENTS_PATH}"


def test_config_constants_are_correct_types() -> None:
    """Test that config constants have correct types."""
    assert isinstance(PROJECT_ROOT, Path)
    assert isinstance(DATA_DIR, Path)
    assert isinstance(CACHE_ENABLED, bool)
    assert isinstance(CACHE_TTL_DAYS, int)


def test_cache_config_values() -> None:
    """Test cache configuration values."""
    assert CACHE_ENABLED is True
    assert CACHE_TTL_DAYS == 1
    assert CACHE_DIR == DATA_DIR / "cache"
