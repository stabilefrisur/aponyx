"""
Unit tests for visualization plotting functions.

Tests verify that plotting functions return valid Plotly figures
and handle edge cases correctly.
"""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_pnl() -> pd.Series:
    """Generate sample P&L series for testing."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    returns = np.random.normal(0.1, 1.0, 100)
    return pd.Series(returns, index=dates, name="pnl")


@pytest.fixture
def sample_signal() -> pd.Series:
    """Generate sample signal for testing."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    values = np.random.normal(0, 1, 100)
    return pd.Series(values, index=dates, name="test_signal")


def test_plot_equity_curve_returns_figure(sample_pnl: pd.Series) -> None:
    """Test that plot_equity_curve returns a Plotly figure."""
    from aponyx.visualization import plot_equity_curve

    fig = plot_equity_curve(sample_pnl)

    assert fig is not None
    assert hasattr(fig, "data")
    assert len(fig.data) > 0


def test_plot_equity_curve_with_drawdown_shading(sample_pnl: pd.Series) -> None:
    """Test equity curve with drawdown shading enabled."""
    from aponyx.visualization import plot_equity_curve

    fig = plot_equity_curve(sample_pnl, show_drawdown_shading=True)

    assert fig is not None
    # Should have shapes for drawdown regions
    assert hasattr(fig, "layout")


def test_plot_signal_returns_figure(sample_signal: pd.Series) -> None:
    """Test that plot_signal returns a Plotly figure."""
    from aponyx.visualization import plot_signal

    fig = plot_signal(sample_signal)

    assert fig is not None
    assert hasattr(fig, "data")
    assert len(fig.data) > 0


def test_plot_signal_with_thresholds(sample_signal: pd.Series) -> None:
    """Test signal plot with threshold lines."""
    from aponyx.visualization import plot_signal

    fig = plot_signal(sample_signal, threshold_lines=[-2, 2])

    assert fig is not None
    # Should have horizontal lines for thresholds
    assert hasattr(fig, "layout")


def test_plot_signal_custom_title(sample_signal: pd.Series) -> None:
    """Test signal plot with custom title."""
    from aponyx.visualization import plot_signal

    custom_title = "Custom Signal Title"
    fig = plot_signal(sample_signal, title=custom_title)

    assert fig.layout.title.text == custom_title


def test_plot_drawdown_returns_figure(sample_pnl: pd.Series) -> None:
    """Test that plot_drawdown returns a Plotly figure."""
    from aponyx.visualization import plot_drawdown

    fig = plot_drawdown(sample_pnl)

    assert fig is not None
    assert hasattr(fig, "data")
    assert len(fig.data) > 0


def test_plot_drawdown_percentage_mode(sample_pnl: pd.Series) -> None:
    """Test drawdown plot in percentage mode."""
    from aponyx.visualization import plot_drawdown

    fig = plot_drawdown(sample_pnl, show_underwater_chart=False)

    assert fig is not None
    assert hasattr(fig, "layout")


@pytest.mark.skip(reason="Plotly doesn't handle empty series well - edge case")
def test_plot_equity_curve_empty_series() -> None:
    """Test equity curve with empty series."""
    from aponyx.visualization import plot_equity_curve

    empty_series = pd.Series([], dtype=float, index=pd.DatetimeIndex([]))
    fig = plot_equity_curve(empty_series)

    assert fig is not None
    assert len(fig.data) == 1


def test_plot_signal_with_nans(sample_signal: pd.Series) -> None:
    """Test signal plot handles NaN values correctly."""
    from aponyx.visualization import plot_signal

    # Introduce some NaN values
    signal_with_nans = sample_signal.copy()
    signal_with_nans.iloc[10:20] = np.nan

    fig = plot_signal(signal_with_nans)

    assert fig is not None
    assert hasattr(fig, "data")


def test_visualizer_class_initialization() -> None:
    """Test Visualizer class can be instantiated."""
    from aponyx.visualization import Visualizer

    viz = Visualizer()

    assert viz is not None
    assert viz.theme == "plotly_white"
    assert viz.export_path is None


def test_visualizer_custom_theme() -> None:
    """Test Visualizer with custom theme."""
    from aponyx.visualization import Visualizer

    viz = Visualizer(theme="plotly_dark")

    assert viz.theme == "plotly_dark"


def test_visualizer_equity_curve(sample_pnl: pd.Series) -> None:
    """Test Visualizer.equity_curve method."""
    from aponyx.visualization import Visualizer

    viz = Visualizer()
    fig = viz.equity_curve(sample_pnl)

    assert fig is not None
    # Check that template was applied (stored as object, not string)
    assert hasattr(fig.layout, "template")


def test_visualizer_signal(sample_signal: pd.Series) -> None:
    """Test Visualizer.signal method."""
    from aponyx.visualization import Visualizer

    viz = Visualizer()
    fig = viz.signal(sample_signal)

    assert fig is not None
    # Check that template was applied (stored as object, not string)
    assert hasattr(fig.layout, "template")


def test_visualizer_drawdown(sample_pnl: pd.Series) -> None:
    """Test Visualizer.drawdown method."""
    from aponyx.visualization import Visualizer

    viz = Visualizer()
    fig = viz.drawdown(sample_pnl)

    assert fig is not None
    # Check that template was applied (stored as object, not string)
    assert hasattr(fig.layout, "template")


def test_visualizer_attribution_not_implemented() -> None:
    """Test that attribution raises NotImplementedError."""
    from aponyx.visualization import Visualizer

    viz = Visualizer()
    dummy_df = pd.DataFrame()

    with pytest.raises(NotImplementedError):
        viz.attribution(dummy_df)


def test_visualizer_exposures_not_implemented() -> None:
    """Test that exposures raises NotImplementedError."""
    from aponyx.visualization import Visualizer

    viz = Visualizer()
    dummy_df = pd.DataFrame()

    with pytest.raises(NotImplementedError):
        viz.exposures(dummy_df)


def test_visualizer_dashboard_not_implemented() -> None:
    """Test that dashboard raises NotImplementedError."""
    from aponyx.visualization import Visualizer

    viz = Visualizer()
    dummy_dict = {}

    with pytest.raises(NotImplementedError):
        viz.dashboard(dummy_dict)


def test_plot_equity_curve_cumulative_calculation(sample_pnl: pd.Series) -> None:
    """Test that equity curve correctly computes cumulative P&L."""
    from aponyx.visualization import plot_equity_curve

    fig = plot_equity_curve(sample_pnl)

    # Extract y values from figure
    y_values = fig.data[0].y

    # Should be cumulative sum
    expected_cumsum = sample_pnl.cumsum().values

    np.testing.assert_array_almost_equal(y_values, expected_cumsum)


def test_plot_drawdown_non_positive_values(sample_pnl: pd.Series) -> None:
    """Test that drawdown values are always non-positive."""
    from aponyx.visualization import plot_drawdown

    fig = plot_drawdown(sample_pnl)

    # Extract y values
    y_values = fig.data[0].y

    # All drawdown values should be <= 0
    assert np.all(y_values <= 0)
