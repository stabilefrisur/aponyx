"""
Tests for signal data requirements resolution.

Validates get_required_data_keys function.
"""

import json
from pathlib import Path

import pytest

from aponyx.data.requirements import get_required_data_keys


@pytest.fixture
def sample_catalog(tmp_path: Path) -> Path:
    """Create sample signal catalog for testing."""
    catalog_data = [
        {
            "name": "cdx_etf_basis",
            "enabled": True,
            "data_requirements": {"cdx": "spread", "etf": "spread"},
            "compute_function_name": "compute_cdx_etf_basis",
            "arg_mapping": ["cdx", "etf"],
            "sign_multiplier": 1,
        },
        {
            "name": "cdx_vix_gap",
            "enabled": True,
            "data_requirements": {"cdx": "spread", "vix": "level"},
            "compute_function_name": "compute_cdx_vix_gap",
            "arg_mapping": ["cdx", "vix"],
            "sign_multiplier": 1,
        },
        {
            "name": "disabled_signal",
            "enabled": False,
            "data_requirements": {"unknown": "field"},
            "compute_function_name": "compute_disabled",
            "arg_mapping": ["unknown"],
            "sign_multiplier": 1,
        },
    ]
    
    catalog_path = tmp_path / "test_signal_catalog.json"
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog_data, f)
    
    return catalog_path


def test_get_required_data_keys_all_enabled(sample_catalog: Path) -> None:
    """Test getting required data keys from enabled signals."""
    result = get_required_data_keys(sample_catalog)
    
    assert result == {"cdx", "etf", "vix"}


def test_get_required_data_keys_skips_disabled(sample_catalog: Path) -> None:
    """Test that disabled signals are skipped."""
    result = get_required_data_keys(sample_catalog)
    
    assert "unknown" not in result


def test_get_required_data_keys_file_not_found(tmp_path: Path) -> None:
    """Test error when catalog file not found."""
    missing_path = tmp_path / "missing.json"
    
    with pytest.raises(FileNotFoundError, match="Signal catalog not found"):
        get_required_data_keys(missing_path)


def test_get_required_data_keys_invalid_json(tmp_path: Path) -> None:
    """Test error when catalog is not a JSON array."""
    invalid_path = tmp_path / "invalid.json"
    with open(invalid_path, "w", encoding="utf-8") as f:
        json.dump({"not": "an array"}, f)
    
    with pytest.raises(ValueError, match="Signal catalog must be a JSON array"):
        get_required_data_keys(invalid_path)


def test_get_required_data_keys_invalid_requirements(tmp_path: Path) -> None:
    """Test error when data_requirements is not a dict."""
    catalog_data = [
        {
            "name": "bad_signal",
            "enabled": True,
            "data_requirements": "not a dict",
            "compute_function_name": "compute_bad",
            "arg_mapping": [],
            "sign_multiplier": 1,
        }
    ]
    
    catalog_path = tmp_path / "bad_catalog.json"
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog_data, f)
    
    with pytest.raises(ValueError, match="invalid data_requirements"):
        get_required_data_keys(catalog_path)


def test_get_required_data_keys_empty_catalog(tmp_path: Path) -> None:
    """Test getting data keys from empty catalog."""
    catalog_path = tmp_path / "empty.json"
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump([], f)
    
    result = get_required_data_keys(catalog_path)
    
    assert result == set()
