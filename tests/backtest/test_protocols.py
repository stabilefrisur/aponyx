"""
Tests for backtest protocol conformance.

Verifies that our backtest engine and performance calculators
conform to the defined protocols, enabling future adapter implementations.
"""

import numpy as np
import pandas as pd

from aponyx.backtest import BacktestConfig, run_backtest
from aponyx.backtest.engine import BacktestResult
from aponyx.backtest.protocols import BacktestEngine
from aponyx.evaluation.performance import compute_all_metrics


class SimpleBacktestEngine:
    """
    Minimal implementation of BacktestEngine protocol for testing.
    
    This verifies that the protocol can be implemented with minimal code
    and that our main engine follows the same interface.
    """

    def run(
        self,
        signal: pd.Series,
        spread: pd.Series,
        config: BacktestConfig | None = None,
    ) -> BacktestResult:
        """
        Simple backtest that just tracks signals without P&L calculation.
        
        Used to test protocol conformance only.
        """
        if config is None:
            config = BacktestConfig()

        # Minimal implementation - just create result structure
        dates = signal.index
        positions_df = pd.DataFrame(
            {
                "signal": signal,
                "position": 0,
                "days_held": 0,
                "spread": spread,
            },
            index=dates,
        )

        pnl_df = pd.DataFrame(
            {
                "spread_pnl": 0.0,
                "cost": 0.0,
                "net_pnl": 0.0,
                "cumulative_pnl": 0.0,
            },
            index=dates,
        )

        metadata = {
            "config": config.__dict__,
            "summary": {
                "n_trades": 0,
                "total_pnl": 0.0,
            },
        }

        return BacktestResult(
            positions=positions_df,
            pnl=pnl_df,
            metadata=metadata,
        )


class SimplePerformanceCalculator:
    """
    Minimal implementation of PerformanceCalculator protocol for testing.
    """

    def compute(
        self,
        pnl_df: pd.DataFrame,
        positions_df: pd.DataFrame,
    ) -> dict:
        """Simple metrics calculation."""
        return {
            "total_pnl": pnl_df["net_pnl"].sum(),
            "n_days": len(pnl_df),
        }


def test_backtest_engine_protocol_conformance() -> None:
    """Test that run_backtest conforms to BacktestEngine protocol."""
    # Create test data
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    signal = pd.Series(np.random.randn(50), index=dates)
    spread = pd.Series(100 + np.random.randn(50), index=dates)
    config = BacktestConfig()

    # Our function should work as protocol implementation
    # (functions with compatible signatures satisfy Protocol)
    result = run_backtest(signal, spread, config)

    # Verify result structure matches protocol expectations
    assert isinstance(result, BacktestResult)
    assert hasattr(result, "positions")
    assert hasattr(result, "pnl")
    assert hasattr(result, "metadata")


def test_simple_engine_protocol_conformance() -> None:
    """Test that minimal engine implementation satisfies protocol."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    signal = pd.Series(np.random.randn(50), index=dates)
    spread = pd.Series(100 + np.random.randn(50), index=dates)

    engine = SimpleBacktestEngine()
    result = engine.run(signal, spread)

    # Should return BacktestResult
    assert isinstance(result, BacktestResult)
    assert len(result.positions) == 50
    assert len(result.pnl) == 50


def test_performance_calculator_protocol_conformance() -> None:
    """Test that compute_all_metrics can satisfy PerformanceCalculator protocol."""
    # Create test data
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    pnl_df = pd.DataFrame(
        {
            "net_pnl": np.random.randn(50) * 100,
            "cumulative_pnl": np.cumsum(np.random.randn(50) * 100),
        },
        index=dates,
    )
    positions_df = pd.DataFrame(
        {
            "position": np.random.choice([0, 1, -1], size=50),
            "days_held": np.random.randint(0, 10, size=50),
        },
        index=dates,
    )

    # Our function should work
    metrics = compute_all_metrics(pnl_df, positions_df)

    # Verify it returns expected structure
    assert hasattr(metrics, "sharpe_ratio")
    assert hasattr(metrics, "total_return")


def test_simple_calculator_protocol_conformance() -> None:
    """Test that minimal calculator implementation satisfies protocol."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    pnl_df = pd.DataFrame(
        {
            "net_pnl": np.random.randn(50) * 100,
            "cumulative_pnl": np.cumsum(np.random.randn(50) * 100),
        },
        index=dates,
    )
    positions_df = pd.DataFrame(
        {
            "position": np.random.choice([0, 1, -1], size=50),
            "days_held": np.random.randint(0, 10, size=50),
        },
        index=dates,
    )

    calc = SimplePerformanceCalculator()
    result = calc.compute(pnl_df, positions_df)

    # Should return dict with metrics
    assert isinstance(result, dict)
    assert "total_pnl" in result
    assert "n_days" in result


def test_protocol_allows_swapping_implementations() -> None:
    """
    Test that different BacktestEngine implementations can be used interchangeably.
    
    This verifies that the protocol design enables future integration
    of libraries like vectorbt or backtrader.
    """
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    signal = pd.Series(np.random.randn(30), index=dates)
    spread = pd.Series(100 + np.random.randn(30), index=dates)
    config = BacktestConfig()

    # Different engines that satisfy protocol
    engines: list[BacktestEngine] = [
        SimpleBacktestEngine(),
        # When adapters are implemented, add here:
        # VectorBTEngine(),
        # BacktraderEngine(),
    ]

    for engine in engines:
        result = engine.run(signal, spread, config)
        # All should return compatible result structure
        assert isinstance(result, BacktestResult)
        assert isinstance(result.positions, pd.DataFrame)
        assert isinstance(result.pnl, pd.DataFrame)
        assert isinstance(result.metadata, dict)


def test_backtest_result_immutability_expectation() -> None:
    """
    Test that BacktestResult components are separate from inputs.
    
    Modifying result should not affect original data.
    """
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    signal = pd.Series([1.0] * 30, index=dates)
    spread = pd.Series([100.0] * 30, index=dates)

    result = run_backtest(signal, spread, BacktestConfig(signal_lag=0))

    # Modify result
    result.positions.iloc[0, 0] = 999.0

    # Original signal should be unchanged
    assert signal.iloc[0] == 1.0


def test_protocol_type_annotations() -> None:
    """
    Test that protocol implementations have correct type signatures.
    
    This is mainly for documentation - mypy would catch type violations.
    """
    # Verify our function signature matches protocol
    import inspect

    # Check run_backtest signature
    sig = inspect.signature(run_backtest)
    params = sig.parameters

    assert "signal" in params
    assert "spread" in params
    assert "config" in params

    # Config should have default None
    assert params["config"].default is None


def test_metadata_structure_consistency() -> None:
    """
    Test that metadata follows consistent structure across implementations.
    
    This enables downstream tools to reliably parse backtest metadata.
    """
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    signal = pd.Series(np.random.randn(50), index=dates)
    spread = pd.Series(100 + np.random.randn(50), index=dates)

    # Test with our main engine
    result = run_backtest(signal, spread, BacktestConfig(signal_lag=0))

    # Verify expected metadata structure
    assert "config" in result.metadata
    assert "summary" in result.metadata
    assert "timestamp" in result.metadata

    # Config should be dict-like
    assert isinstance(result.metadata["config"], dict)
    assert "entry_threshold" in result.metadata["config"]
    assert "signal_lag" in result.metadata["config"]

    # Summary should have key stats
    assert "n_trades" in result.metadata["summary"]
    assert "total_pnl" in result.metadata["summary"]
    assert "start_date" in result.metadata["summary"]
    assert "end_date" in result.metadata["summary"]
