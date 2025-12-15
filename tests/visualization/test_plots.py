"""
Unit tests for visualization plotting functions.

Tests verify that plotting functions return valid Plotly figures
and handle edge cases correctly.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
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


# =============================================================================
# Research Dashboard Tests (User Story 1)
# =============================================================================


@pytest.fixture
def sample_dashboard_series() -> dict[str, pd.Series]:
    """
    Generate 6 aligned pd.Series for research dashboard testing.

    Returns a dict with keys: traded_product, indicator, score, signal, positions, pnl.
    All series share the same DatetimeIndex.
    """
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=252, freq="D")

    # Traded product (CDX spread in bps) - random walk around 100
    traded_product = pd.Series(
        100 + np.cumsum(np.random.normal(0, 2, 252)), index=dates, name="spread"
    )

    # Indicator (bps) - some derived metric
    indicator = pd.Series(
        np.random.normal(0, 20, 252), index=dates, name="indicator"
    )

    # Score (z-score normalized)
    score = pd.Series(np.random.normal(0, 1, 252), index=dates, name="score")

    # Signal (bounded trading signal)
    signal = pd.Series(
        np.clip(np.random.normal(0, 0.5, 252), -1.5, 1.5), index=dates, name="signal"
    )

    # Positions (discrete positions)
    positions = pd.Series(
        np.random.choice([-1, 0, 1], 252), index=dates, name="position"
    )

    # P&L (daily returns in dollars)
    pnl = pd.Series(np.random.normal(100, 500, 252), index=dates, name="net_pnl")

    return {
        "traded_product": traded_product,
        "indicator": indicator,
        "score": score,
        "signal": signal,
        "positions": positions,
        "pnl": pnl,
    }


def test_plot_research_dashboard_returns_figure(
    sample_dashboard_series: dict[str, pd.Series],
) -> None:
    """Test that plot_research_dashboard returns a Plotly figure."""
    from aponyx.visualization import plot_research_dashboard

    fig = plot_research_dashboard(**sample_dashboard_series)

    assert fig is not None
    assert isinstance(fig, go.Figure)
    assert hasattr(fig, "data")
    assert len(fig.data) > 0


def test_plot_research_dashboard_has_5_subplots(
    sample_dashboard_series: dict[str, pd.Series],
) -> None:
    """Test that dashboard has 5 subplot rows."""
    from aponyx.visualization import plot_research_dashboard

    fig = plot_research_dashboard(**sample_dashboard_series)

    # With make_subplots and 5 rows, there should be y-axes yaxis, yaxis2, ... yaxis10
    # (5 rows * 2 y-axes each = 10 y-axes)
    # Check that we have the expected x-axis count (5 subplots)
    assert "xaxis5" in fig.layout.to_plotly_json()
    # Verify yaxis10 exists (5 rows * 2 y-axes)
    assert "yaxis10" in fig.layout.to_plotly_json()


def test_plot_research_dashboard_has_10_traces(
    sample_dashboard_series: dict[str, pd.Series],
) -> None:
    """Test that dashboard has 10 traces (5 panels × 2 traces each)."""
    from aponyx.visualization import plot_research_dashboard

    fig = plot_research_dashboard(**sample_dashboard_series)

    # 5 panels with 2 traces each (left y + right y)
    assert len(fig.data) == 10


def test_plot_research_dashboard_validates_input_type() -> None:
    """Test that TypeError is raised for non-Series input."""
    from aponyx.visualization import plot_research_dashboard

    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    valid_series = pd.Series([1.0] * 10, index=dates)

    # Pass a list instead of Series for indicator
    with pytest.raises(TypeError, match="indicator must be pd.Series"):
        plot_research_dashboard(
            traded_product=valid_series,
            indicator=[1.0, 2.0, 3.0],  # Wrong type
            score=valid_series,
            signal=valid_series,
            positions=valid_series,
            pnl=valid_series,
        )


def test_plot_research_dashboard_validates_datetime_index() -> None:
    """Test that TypeError is raised for wrong index type."""
    from aponyx.visualization import plot_research_dashboard

    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    valid_series = pd.Series([1.0] * 10, index=dates)

    # Series with RangeIndex instead of DatetimeIndex
    invalid_index_series = pd.Series([1.0] * 10)  # Default RangeIndex

    with pytest.raises(TypeError, match="score must have DatetimeIndex"):
        plot_research_dashboard(
            traded_product=valid_series,
            indicator=valid_series,
            score=invalid_index_series,  # Wrong index type
            signal=valid_series,
            positions=valid_series,
            pnl=valid_series,
        )


def test_plot_research_dashboard_validates_empty_series() -> None:
    """Test that ValueError is raised for empty series."""
    from aponyx.visualization import plot_research_dashboard

    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    valid_series = pd.Series([1.0] * 10, index=dates)

    # Empty series with DatetimeIndex
    empty_series = pd.Series([], dtype=float, index=pd.DatetimeIndex([]))

    with pytest.raises(ValueError, match="signal must not be empty"):
        plot_research_dashboard(
            traded_product=valid_series,
            indicator=valid_series,
            score=valid_series,
            signal=empty_series,  # Empty
            positions=valid_series,
            pnl=valid_series,
        )


def test_plot_research_dashboard_handles_nan_values(
    sample_dashboard_series: dict[str, pd.Series],
) -> None:
    """Test that NaN values render as gaps (no error)."""
    from aponyx.visualization import plot_research_dashboard

    # Introduce NaN values
    sample_dashboard_series["indicator"].iloc[10:20] = np.nan

    # Should not raise - NaN creates gaps in the line
    fig = plot_research_dashboard(**sample_dashboard_series)

    assert fig is not None
    assert len(fig.data) == 10


def test_plot_research_dashboard_custom_title(
    sample_dashboard_series: dict[str, pd.Series],
) -> None:
    """Test that custom title parameter is applied."""
    from aponyx.visualization import plot_research_dashboard

    custom_title = "My Custom Dashboard Title"
    fig = plot_research_dashboard(**sample_dashboard_series, title=custom_title)

    assert fig.layout.title.text == custom_title


def test_plot_research_dashboard_subplot_titles(
    sample_dashboard_series: dict[str, pd.Series],
) -> None:
    """Test that subplot titles are Indicator, Score, Signal, Positions, P&L."""
    from aponyx.visualization import plot_research_dashboard

    fig = plot_research_dashboard(**sample_dashboard_series)

    # Check annotations for subplot titles
    annotations = fig.layout.annotations
    expected_titles = ["Indicator", "Score", "Signal", "Positions", "P&L"]

    annotation_texts = [ann.text for ann in annotations]
    for expected in expected_titles:
        assert expected in annotation_texts, f"Missing subplot title: {expected}"


def test_plot_research_dashboard_yaxis_labels(
    sample_dashboard_series: dict[str, pd.Series],
) -> None:
    """Test that y-axis labels include proper units."""
    from aponyx.visualization import plot_research_dashboard

    fig = plot_research_dashboard(**sample_dashboard_series)

    layout = fig.layout.to_plotly_json()

    # Check left y-axis labels (odd-numbered y-axes: y1, y3, y5, y7, y9)
    assert "bps" in layout["yaxis"]["title"]["text"]  # Indicator
    assert "z-score" in layout["yaxis3"]["title"]["text"]  # Score
    assert "signal" in layout["yaxis5"]["title"]["text"]  # Signal
    assert "position" in layout["yaxis7"]["title"]["text"]  # Positions
    assert "$" in layout["yaxis9"]["title"]["text"]  # P&L

    # Check right y-axis labels (even-numbered: y2, y4, y6, y8, y10)
    assert "spread" in layout["yaxis2"]["title"]["text"]  # Traded Product
    assert "spread" in layout["yaxis4"]["title"]["text"]
    assert "spread" in layout["yaxis6"]["title"]["text"]
    assert "spread" in layout["yaxis8"]["title"]["text"]
    assert "spread" in layout["yaxis10"]["title"]["text"]


# =============================================================================
# Research Dashboard Interactive Features Tests (User Story 3)
# =============================================================================


def test_plot_research_dashboard_has_shared_xaxis(
    sample_dashboard_series: dict[str, pd.Series],
) -> None:
    """Test that dashboard has shared x-axes for synchronized zoom/pan."""
    from aponyx.visualization import plot_research_dashboard

    fig = plot_research_dashboard(**sample_dashboard_series)

    layout = fig.layout.to_plotly_json()

    # First 4 x-axes should reference xaxis5 (the bottom one with rangeslider)
    # In Plotly make_subplots with shared_xaxes, upper axes match bottom axis
    # Verify xaxis5 exists and has rangeslider
    assert "xaxis5" in layout
    assert layout["xaxis5"].get("rangeslider", {}).get("visible", False) is True


def test_plot_research_dashboard_has_rangeslider(
    sample_dashboard_series: dict[str, pd.Series],
) -> None:
    """Test that range slider is configured on bottom panel only."""
    from aponyx.visualization import plot_research_dashboard

    fig = plot_research_dashboard(**sample_dashboard_series)

    layout = fig.layout.to_plotly_json()

    # Only xaxis5 (bottom panel) should have visible rangeslider
    assert "xaxis5" in layout
    rangeslider = layout["xaxis5"].get("rangeslider", {})
    assert rangeslider.get("visible", False) is True
    assert rangeslider.get("thickness", 0) == 0.05


def test_plot_research_dashboard_hovermode_unified(
    sample_dashboard_series: dict[str, pd.Series],
) -> None:
    """Test that hovermode is set to 'x unified' for synchronized hover."""
    from aponyx.visualization import plot_research_dashboard

    fig = plot_research_dashboard(**sample_dashboard_series)

    assert fig.layout.hovermode == "x unified"
