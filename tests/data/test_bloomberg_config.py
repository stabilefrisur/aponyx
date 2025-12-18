"""
Unit tests for Bloomberg configuration and product microstructure lookup.
"""

import pytest

from aponyx.data.bloomberg_config import (
    get_product_microstructure,
    ProductMicrostructure,
)


class TestGetProductMicrostructure:
    """Tests for get_product_microstructure() function."""

    def test_valid_cdx_ig_5y_returns_microstructure(self) -> None:
        """Test T004: get_product_microstructure returns correct values for cdx_ig_5y."""
        result = get_product_microstructure("cdx_ig_5y")

        assert isinstance(result, ProductMicrostructure)
        assert result.dv01_per_million == 475.0
        assert result.transaction_cost_bps == 1.5

    def test_valid_cdx_ig_10y_returns_microstructure(self) -> None:
        """Test get_product_microstructure returns correct values for cdx_ig_10y."""
        result = get_product_microstructure("cdx_ig_10y")

        assert isinstance(result, ProductMicrostructure)
        assert result.dv01_per_million == 875.0
        assert result.transaction_cost_bps == 2.0

    def test_valid_cdx_hy_5y_returns_higher_transaction_cost(self) -> None:
        """Test T004: cdx_hy_5y has higher transaction costs than IG."""
        result = get_product_microstructure("cdx_hy_5y")

        assert isinstance(result, ProductMicrostructure)
        assert result.dv01_per_million == 425.0
        assert result.transaction_cost_bps == 8.0
        # HY should have higher tcost than IG
        ig_result = get_product_microstructure("cdx_ig_5y")
        assert result.transaction_cost_bps > ig_result.transaction_cost_bps

    def test_valid_itrx_eur_5y_returns_microstructure(self) -> None:
        """Test get_product_microstructure returns correct values for itrx_eur_5y."""
        result = get_product_microstructure("itrx_eur_5y")

        assert isinstance(result, ProductMicrostructure)
        assert result.dv01_per_million == 475.0
        assert result.transaction_cost_bps == 1.5

    def test_valid_itrx_xover_5y_returns_microstructure(self) -> None:
        """Test get_product_microstructure returns correct values for itrx_xover_5y."""
        result = get_product_microstructure("itrx_xover_5y")

        assert isinstance(result, ProductMicrostructure)
        assert result.dv01_per_million == 425.0
        assert result.transaction_cost_bps == 7.0

    def test_etf_raises_value_error(self) -> None:
        """Test T004: get_product_microstructure raises ValueError for ETF products."""
        with pytest.raises(ValueError) as exc_info:
            get_product_microstructure("hyg")

        error_msg = str(exc_info.value)
        assert "hyg" in error_msg
        assert "does not have microstructure parameters" in error_msg
        assert "Only CDX products can be backtested" in error_msg

    def test_vix_raises_value_error(self) -> None:
        """Test T004: get_product_microstructure raises ValueError for VIX."""
        with pytest.raises(ValueError) as exc_info:
            get_product_microstructure("vix")

        error_msg = str(exc_info.value)
        assert "vix" in error_msg
        assert "does not have microstructure parameters" in error_msg

    def test_lqd_etf_raises_value_error(self) -> None:
        """Test get_product_microstructure raises ValueError for LQD ETF."""
        with pytest.raises(ValueError) as exc_info:
            get_product_microstructure("lqd")

        error_msg = str(exc_info.value)
        assert "lqd" in error_msg
        assert "does not have microstructure parameters" in error_msg

    def test_unknown_product_raises_value_error(self) -> None:
        """Test get_product_microstructure raises ValueError for unknown products."""
        with pytest.raises(ValueError) as exc_info:
            get_product_microstructure("nonexistent_product")

        error_msg = str(exc_info.value)
        assert "nonexistent_product" in error_msg
        assert "not found in catalog" in error_msg

    def test_product_microstructure_is_frozen(self) -> None:
        """Test ProductMicrostructure is immutable (frozen dataclass)."""
        result = get_product_microstructure("cdx_ig_5y")

        with pytest.raises(AttributeError):
            result.dv01_per_million = 500.0  # type: ignore

    def test_all_cdx_products_have_microstructure(self) -> None:
        """Test all CDX products in catalog have microstructure parameters."""
        cdx_products = ["cdx_ig_5y", "cdx_ig_10y", "cdx_hy_5y", "itrx_eur_5y", "itrx_xover_5y"]

        for product in cdx_products:
            result = get_product_microstructure(product)
            assert result.dv01_per_million > 0, f"{product} should have positive DV01"
            assert result.transaction_cost_bps >= 0, f"{product} should have non-negative tcost"

    def test_microstructure_values_are_reasonable(self) -> None:
        """Test microstructure values are within expected ranges."""
        for product in ["cdx_ig_5y", "cdx_ig_10y", "cdx_hy_5y"]:
            result = get_product_microstructure(product)

            # DV01 should be in reasonable range (100-1000 for credit indices)
            assert 100 <= result.dv01_per_million <= 1000, (
                f"{product} DV01 {result.dv01_per_million} outside expected range"
            )

            # Transaction cost should be in reasonable range (0.5-20 bps)
            assert 0.5 <= result.transaction_cost_bps <= 20.0, (
                f"{product} tcost {result.transaction_cost_bps} outside expected range"
            )
