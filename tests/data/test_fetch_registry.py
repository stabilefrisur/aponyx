"""
Tests for instrument fetch function registry.

Validates get_fetch_spec and list_instruments functions.
"""

import pytest

from aponyx.data.fetch_registry import get_fetch_spec, list_instruments, FetchSpec


def test_get_fetch_spec_cdx() -> None:
    """Test getting fetch spec for CDX instrument."""
    spec = get_fetch_spec("cdx")
    
    assert isinstance(spec, FetchSpec)
    assert spec.instrument == "cdx"
    assert spec.requires_security is True
    assert callable(spec.fetch_fn)


def test_get_fetch_spec_vix() -> None:
    """Test getting fetch spec for VIX instrument."""
    spec = get_fetch_spec("vix")
    
    assert isinstance(spec, FetchSpec)
    assert spec.instrument == "vix"
    assert spec.requires_security is False
    assert callable(spec.fetch_fn)


def test_get_fetch_spec_etf() -> None:
    """Test getting fetch spec for ETF instrument."""
    spec = get_fetch_spec("etf")
    
    assert isinstance(spec, FetchSpec)
    assert spec.instrument == "etf"
    assert spec.requires_security is True
    assert callable(spec.fetch_fn)


def test_get_fetch_spec_unknown_instrument() -> None:
    """Test error when requesting unknown instrument."""
    with pytest.raises(ValueError, match="Unknown instrument type: 'unknown'"):
        get_fetch_spec("unknown")


def test_list_instruments() -> None:
    """Test listing all registered instruments."""
    instruments = list_instruments()
    
    assert isinstance(instruments, list)
    assert "cdx" in instruments
    assert "vix" in instruments
    assert "etf" in instruments
    assert instruments == sorted(instruments)  # Should be sorted


def test_fetch_spec_immutable() -> None:
    """Test that FetchSpec is immutable (frozen dataclass)."""
    spec = get_fetch_spec("vix")
    
    with pytest.raises(AttributeError):
        spec.instrument = "cdx"


def test_registry_caching() -> None:
    """Test that registry is loaded once and cached."""
    # Call twice, should return same instance
    spec1 = get_fetch_spec("vix")
    spec2 = get_fetch_spec("vix")
    
    # Same fetch function reference (cached registry)
    assert spec1.fetch_fn is spec2.fetch_fn
