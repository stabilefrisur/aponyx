"""
Unit tests for calculator factory resolution.

Tests for resolve_calculator() factory function.
"""

import pytest

from aponyx.backtest.calculator_factory import resolve_calculator
from aponyx.backtest.calculators import (
    SpreadReturnCalculator,
    PriceReturnCalculator,
)


class TestResolveCalculator:
    """Tests for resolve_calculator() factory function."""

    def test_spread_quote_type_returns_spread_calculator(self) -> None:
        """Test T027: quote_type='spread' returns SpreadReturnCalculator."""
        calc = resolve_calculator(
            quote_type="spread",
            dv01_per_million=475.0,
        )

        assert isinstance(calc, SpreadReturnCalculator)
        assert calc.dv01_per_million == 475.0

    def test_price_quote_type_returns_price_calculator(self) -> None:
        """Test T027: quote_type='price' returns PriceReturnCalculator."""
        calc = resolve_calculator(quote_type="price")

        assert isinstance(calc, PriceReturnCalculator)

    def test_price_quote_type_ignores_dv01_parameter(self) -> None:
        """Test T027: PriceReturnCalculator ignores dv01_per_million if provided."""
        calc = resolve_calculator(
            quote_type="price",
            dv01_per_million=475.0,  # Should be ignored
        )

        assert isinstance(calc, PriceReturnCalculator)

    def test_unknown_quote_type_raises_value_error(self) -> None:
        """Test T028: Unknown quote_type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            resolve_calculator(quote_type="futures")

        error_msg = str(exc_info.value)
        assert "Unknown quote_type" in error_msg
        assert "'futures'" in error_msg
        assert "spread" in error_msg
        assert "price" in error_msg

    def test_empty_quote_type_raises_value_error(self) -> None:
        """Test T028: Empty quote_type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown quote_type"):
            resolve_calculator(quote_type="")

    def test_spread_product_missing_dv01_raises_value_error(self) -> None:
        """Test T029: Spread product without dv01_per_million raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            resolve_calculator(quote_type="spread", dv01_per_million=None)

        error_msg = str(exc_info.value)
        assert "dv01_per_million is required" in error_msg
        assert "spread-based products" in error_msg

    def test_spread_product_with_zero_dv01_raises_value_error(self) -> None:
        """Test T029: Spread product with zero DV01 raises ValueError (from calculator)."""
        with pytest.raises(ValueError, match="dv01_per_million must be positive"):
            resolve_calculator(quote_type="spread", dv01_per_million=0.0)

    def test_spread_product_with_negative_dv01_raises_value_error(self) -> None:
        """Test T029: Spread product with negative DV01 raises ValueError (from calculator)."""
        with pytest.raises(ValueError, match="dv01_per_million must be positive"):
            resolve_calculator(quote_type="spread", dv01_per_million=-100.0)


class TestResolveCalculatorIntegration:
    """Integration tests for resolve_calculator with product metadata."""

    def test_resolve_for_cdx_product(self) -> None:
        """Test resolver works with typical CDX parameters."""
        from aponyx.data import get_product_microstructure

        micro = get_product_microstructure("cdx_ig_5y")
        calc = resolve_calculator(
            quote_type=micro.quote_type,
            dv01_per_million=micro.dv01_per_million,
        )

        assert isinstance(calc, SpreadReturnCalculator)
        assert calc.dv01_per_million == 475.0

    def test_resolve_for_etf_product(self) -> None:
        """Test resolver works with ETF product."""
        from aponyx.data import get_product_microstructure

        micro = get_product_microstructure("lqd")
        calc = resolve_calculator(
            quote_type=micro.quote_type,
            dv01_per_million=micro.dv01_per_million,
        )

        assert isinstance(calc, PriceReturnCalculator)

    def test_resolve_for_all_cdx_products(self) -> None:
        """Test resolver works for all CDX products in catalog."""
        from aponyx.data import get_product_microstructure

        cdx_products = [
            "cdx_ig_5y",
            "cdx_ig_10y",
            "cdx_hy_5y",
            "itrx_eur_5y",
            "itrx_xover_5y",
        ]

        for product in cdx_products:
            micro = get_product_microstructure(product)
            calc = resolve_calculator(
                quote_type=micro.quote_type,
                dv01_per_million=micro.dv01_per_million,
            )
            assert isinstance(calc, SpreadReturnCalculator), f"Failed for {product}"

    def test_resolve_for_all_price_products(self) -> None:
        """Test resolver works for all price-quoted products in catalog."""
        from aponyx.data import get_product_microstructure

        price_products = ["hyg", "lqd", "vix"]

        for product in price_products:
            micro = get_product_microstructure(product)
            calc = resolve_calculator(
                quote_type=micro.quote_type,
                dv01_per_million=micro.dv01_per_million,
            )
            assert isinstance(calc, PriceReturnCalculator), f"Failed for {product}"
