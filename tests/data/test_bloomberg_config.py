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
        assert result.quote_type == "spread"
        assert result.dv01_per_million == 475.0
        assert result.transaction_cost_bps == 1.5

    def test_valid_cdx_ig_10y_returns_microstructure(self) -> None:
        """Test get_product_microstructure returns correct values for cdx_ig_10y."""
        result = get_product_microstructure("cdx_ig_10y")

        assert isinstance(result, ProductMicrostructure)
        assert result.quote_type == "spread"
        assert result.dv01_per_million == 875.0
        assert result.transaction_cost_bps == 2.0

    def test_valid_cdx_hy_5y_returns_higher_transaction_cost(self) -> None:
        """Test T004: cdx_hy_5y has higher transaction costs than IG."""
        result = get_product_microstructure("cdx_hy_5y")

        assert isinstance(result, ProductMicrostructure)
        assert result.quote_type == "spread"
        assert result.dv01_per_million == 425.0
        assert result.transaction_cost_bps == 8.0
        # HY should have higher tcost than IG
        ig_result = get_product_microstructure("cdx_ig_5y")
        assert result.transaction_cost_bps > ig_result.transaction_cost_bps

    def test_valid_itrx_eur_5y_returns_microstructure(self) -> None:
        """Test get_product_microstructure returns correct values for itrx_eur_5y."""
        result = get_product_microstructure("itrx_eur_5y")

        assert isinstance(result, ProductMicrostructure)
        assert result.quote_type == "spread"
        assert result.dv01_per_million == 475.0
        assert result.transaction_cost_bps == 1.5

    def test_valid_itrx_xover_5y_returns_microstructure(self) -> None:
        """Test get_product_microstructure returns correct values for itrx_xover_5y."""
        result = get_product_microstructure("itrx_xover_5y")

        assert isinstance(result, ProductMicrostructure)
        assert result.quote_type == "spread"
        assert result.dv01_per_million == 425.0
        assert result.transaction_cost_bps == 7.0

    def test_etf_hyg_returns_price_quote_type(self) -> None:
        """Test T007: get_product_microstructure returns quote_type='price' for ETF products."""
        result = get_product_microstructure("hyg")

        assert isinstance(result, ProductMicrostructure)
        assert result.quote_type == "price"
        assert result.dv01_per_million is None
        # ETFs may have default 0 transaction cost
        assert result.transaction_cost_bps >= 0

    def test_etf_lqd_returns_price_quote_type(self) -> None:
        """Test get_product_microstructure returns quote_type='price' for LQD ETF."""
        result = get_product_microstructure("lqd")

        assert isinstance(result, ProductMicrostructure)
        assert result.quote_type == "price"
        assert result.dv01_per_million is None

    def test_vix_returns_price_quote_type(self) -> None:
        """Test get_product_microstructure returns quote_type='price' for VIX."""
        result = get_product_microstructure("vix")

        assert isinstance(result, ProductMicrostructure)
        assert result.quote_type == "price"
        assert result.dv01_per_million is None

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
            assert result.quote_type == "spread", f"{product} should have quote_type='spread'"
            assert result.dv01_per_million is not None, f"{product} should have DV01"
            assert result.dv01_per_million > 0, f"{product} should have positive DV01"
            assert result.transaction_cost_bps >= 0, f"{product} should have non-negative tcost"

    def test_microstructure_values_are_reasonable(self) -> None:
        """Test microstructure values are within expected ranges."""
        for product in ["cdx_ig_5y", "cdx_ig_10y", "cdx_hy_5y"]:
            result = get_product_microstructure(product)

            assert result.dv01_per_million is not None
            # DV01 should be in reasonable range (100-1000 for credit indices)
            assert 100 <= result.dv01_per_million <= 1000, (
                f"{product} DV01 {result.dv01_per_million} outside expected range"
            )

            # Transaction cost should be in reasonable range (0.5-20 bps)
            assert 0.5 <= result.transaction_cost_bps <= 20.0, (
                f"{product} tcost {result.transaction_cost_bps} outside expected range"
            )


class TestProductMicrostructureValidation:
    """Tests for ProductMicrostructure validation."""

    def test_missing_quote_type_raises_value_error(self) -> None:
        """Test T008: ProductMicrostructure raises ValueError for missing quote_type."""
        # We cannot easily test missing quote_type in JSON without modifying the file,
        # so we test the dataclass validation directly
        with pytest.raises(ValueError) as exc_info:
            ProductMicrostructure(
                quote_type="invalid",
                dv01_per_million=475.0,
                transaction_cost_bps=1.5,
            )

        assert "quote_type must be 'spread' or 'price'" in str(exc_info.value)

    def test_spread_product_without_dv01_raises_value_error(self) -> None:
        """Test T008: spread product without dv01_per_million raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ProductMicrostructure(
                quote_type="spread",
                dv01_per_million=None,
                transaction_cost_bps=1.5,
            )

        assert "dv01_per_million is required for spread-based products" in str(exc_info.value)

    def test_negative_dv01_raises_value_error(self) -> None:
        """Test ProductMicrostructure raises ValueError for negative DV01."""
        with pytest.raises(ValueError) as exc_info:
            ProductMicrostructure(
                quote_type="spread",
                dv01_per_million=-100.0,
                transaction_cost_bps=1.5,
            )

        assert "dv01_per_million must be positive" in str(exc_info.value)

    def test_price_product_without_dv01_is_valid(self) -> None:
        """Test price product without DV01 is valid."""
        result = ProductMicrostructure(
            quote_type="price",
            dv01_per_million=None,
            transaction_cost_bps=0.0,
        )

        assert result.quote_type == "price"
        assert result.dv01_per_million is None
        assert result.transaction_cost_bps == 0.0
