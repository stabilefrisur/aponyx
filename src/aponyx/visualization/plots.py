"""
Core plotting functions for backtest analysis and signal visualization.

All functions return Plotly figure objects for flexible rendering
(Streamlit, Jupyter, HTML export, etc.).
"""

import logging
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


def _validate_dashboard_series(series: pd.Series, name: str) -> None:
    """
    Validate series for dashboard input.

    Parameters
    ----------
    series : pd.Series
        Input series to validate.
    name : str
        Parameter name for error messages.

    Raises
    ------
    TypeError
        If series is not pd.Series or lacks DatetimeIndex.
    ValueError
        If series is empty.
    """
    if not isinstance(series, pd.Series):
        raise TypeError(f"{name} must be pd.Series, got {type(series).__name__}")
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError(
            f"{name} must have DatetimeIndex, got {type(series.index).__name__}"
        )
    if len(series) == 0:
        raise ValueError(f"{name} must not be empty")


# Color scheme for research dashboard
_TRADED_PRODUCT_COLOR = "#4682B4"  # Steel Blue
_INDICATOR_COLOR = "#FF8C00"  # Dark Orange
_SCORE_COLOR = "#228B22"  # Forest Green
_SIGNAL_COLOR = "#9932CC"  # Purple
_POSITIONS_COLOR = "#DC143C"  # Crimson
_PNL_COLOR = "#FFD700"  # Gold

# Layout defaults
_DEFAULT_HEIGHT = 1500
_DEFAULT_VERTICAL_SPACING = 0.03
_DEFAULT_TITLE = "Research Dashboard"

# Y-axis labels
_INDICATOR_YAXIS = "Indicator (bps)"
_SCORE_YAXIS = "Score (z-score)"
_SIGNAL_YAXIS = "Signal (signal)"
_POSITIONS_YAXIS = "Position (position)"
_PNL_YAXIS = "P&L ($)"
_TRADED_PRODUCT_YAXIS = "Traded Product (spread)"


def plot_research_dashboard(
    traded_product: pd.Series,
    indicator: pd.Series,
    score: pd.Series,
    signal: pd.Series,
    positions: pd.Series,
    pnl: pd.Series,
    title: str | None = None,
) -> go.Figure:
    """
    Generate 5-panel research dashboard for signal pipeline visualization.

    Creates vertically-stacked subplots showing each stage of the four-stage
    transformation pipeline alongside the traded product for correlation analysis.

    Parameters
    ----------
    traded_product : pd.Series
        Traded instrument price/spread with DatetimeIndex.
        Displayed on right y-axis of all panels.
    indicator : pd.Series
        Raw indicator output (Stage 1) with DatetimeIndex.
        Economic values in natural units (typically bps).
    score : pd.Series
        Normalized score (Stage 2) with DatetimeIndex.
        Typically z-score normalized values.
    signal : pd.Series
        Trading signal (Stage 3) with DatetimeIndex.
        Final signal after trading rules applied.
    positions : pd.Series
        Position series from backtest with DatetimeIndex.
    pnl : pd.Series
        Daily P&L series from backtest with DatetimeIndex.
    title : str or None, optional
        Dashboard title. Defaults to "Research Dashboard" if None.

    Returns
    -------
    go.Figure
        Plotly figure with 5 subplots:
        - Row 1: Indicator vs Traded Product
        - Row 2: Score vs Traded Product
        - Row 3: Signal vs Traded Product
        - Row 4: Positions vs Traded Product
        - Row 5: P&L vs Traded Product

    Raises
    ------
    TypeError
        If any input is not a pd.Series with DatetimeIndex.
    ValueError
        If any input series is empty.

    Notes
    -----
    - All subplots share synchronized x-axis
    - Range slider on bottom panel controls all panels
    - Hover shows coordinated values across all panels
    - Caller controls rendering (fig.show(), fig.write_html(), etc.)

    Examples
    --------
    >>> from aponyx.visualization import plot_research_dashboard
    >>> fig = plot_research_dashboard(
    ...     traded_product=cdx_spread,
    ...     indicator=result["indicator"],
    ...     score=result["score"],
    ...     signal=result["signal"],
    ...     positions=positions_series,
    ...     pnl=pnl_series,
    ...     title="CDX-ETF Basis Signal Analysis",
    ... )
    >>> fig.show()  # Interactive display
    >>> fig.write_html("dashboard.html")  # Export to file
    """
    # Validate all inputs
    _validate_dashboard_series(traded_product, "traded_product")
    _validate_dashboard_series(indicator, "indicator")
    _validate_dashboard_series(score, "score")
    _validate_dashboard_series(signal, "signal")
    _validate_dashboard_series(positions, "positions")
    _validate_dashboard_series(pnl, "pnl")

    logger.info(
        "Generating research dashboard: %d observations", len(traded_product)
    )

    # Create figure with 5 subplots, each with secondary y-axis
    fig = make_subplots(
        rows=5,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=_DEFAULT_VERTICAL_SPACING,
        specs=[
            [{"secondary_y": True}],  # Indicator row
            [{"secondary_y": True}],  # Score row
            [{"secondary_y": True}],  # Signal row
            [{"secondary_y": True}],  # Positions row
            [{"secondary_y": True}],  # P&L row
        ],
        subplot_titles=("Indicator", "Score", "Signal", "Positions", "P&L"),
    )

    # Row 1: Indicator vs Traded Product
    fig.add_trace(
        go.Scatter(
            x=indicator.index,
            y=indicator.values,
            name="Indicator",
            line={"color": _INDICATOR_COLOR, "width": 1.5},
        ),
        row=1,
        col=1,
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=traded_product.index,
            y=traded_product.values,
            name="Traded Product",
            line={"color": _TRADED_PRODUCT_COLOR, "width": 1.5},
        ),
        row=1,
        col=1,
        secondary_y=True,
    )

    # Row 2: Score vs Traded Product
    fig.add_trace(
        go.Scatter(
            x=score.index,
            y=score.values,
            name="Score",
            line={"color": _SCORE_COLOR, "width": 1.5},
        ),
        row=2,
        col=1,
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=traded_product.index,
            y=traded_product.values,
            name="Traded Product",
            line={"color": _TRADED_PRODUCT_COLOR, "width": 1.5},
            showlegend=False,
        ),
        row=2,
        col=1,
        secondary_y=True,
    )

    # Row 3: Signal vs Traded Product
    fig.add_trace(
        go.Scatter(
            x=signal.index,
            y=signal.values,
            name="Signal",
            line={"color": _SIGNAL_COLOR, "width": 1.5},
        ),
        row=3,
        col=1,
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=traded_product.index,
            y=traded_product.values,
            name="Traded Product",
            line={"color": _TRADED_PRODUCT_COLOR, "width": 1.5},
            showlegend=False,
        ),
        row=3,
        col=1,
        secondary_y=True,
    )

    # Row 4: Positions vs Traded Product
    fig.add_trace(
        go.Scatter(
            x=positions.index,
            y=positions.values,
            name="Positions",
            line={"color": _POSITIONS_COLOR, "width": 1.5},
        ),
        row=4,
        col=1,
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=traded_product.index,
            y=traded_product.values,
            name="Traded Product",
            line={"color": _TRADED_PRODUCT_COLOR, "width": 1.5},
            showlegend=False,
        ),
        row=4,
        col=1,
        secondary_y=True,
    )

    # Row 5: P&L vs Traded Product
    fig.add_trace(
        go.Scatter(
            x=pnl.index,
            y=pnl.values,
            name="P&L",
            line={"color": _PNL_COLOR, "width": 1.5},
        ),
        row=5,
        col=1,
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=traded_product.index,
            y=traded_product.values,
            name="Traded Product",
            line={"color": _TRADED_PRODUCT_COLOR, "width": 1.5},
            showlegend=False,
        ),
        row=5,
        col=1,
        secondary_y=True,
    )

    # Update y-axis titles for each row
    fig.update_yaxes(title_text=_INDICATOR_YAXIS, row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text=_TRADED_PRODUCT_YAXIS, row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text=_SCORE_YAXIS, row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text=_TRADED_PRODUCT_YAXIS, row=2, col=1, secondary_y=True)
    fig.update_yaxes(title_text=_SIGNAL_YAXIS, row=3, col=1, secondary_y=False)
    fig.update_yaxes(title_text=_TRADED_PRODUCT_YAXIS, row=3, col=1, secondary_y=True)
    fig.update_yaxes(title_text=_POSITIONS_YAXIS, row=4, col=1, secondary_y=False)
    fig.update_yaxes(title_text=_TRADED_PRODUCT_YAXIS, row=4, col=1, secondary_y=True)
    fig.update_yaxes(title_text=_PNL_YAXIS, row=5, col=1, secondary_y=False)
    fig.update_yaxes(title_text=_TRADED_PRODUCT_YAXIS, row=5, col=1, secondary_y=True)

    # Configure layout
    dashboard_title = title if title is not None else _DEFAULT_TITLE
    fig.update_layout(
        title=dashboard_title,
        height=_DEFAULT_HEIGHT,
        hovermode="x unified",
        template="plotly_white",
    )

    # Add range slider to bottom panel only
    fig.update_xaxes(rangeslider={"visible": True, "thickness": 0.05}, row=5, col=1)

    logger.debug("Research dashboard generated successfully")
    return fig


def plot_equity_curve(
    pnl: pd.Series,
    title: str = "Cumulative P&L",
    show_drawdown_shading: bool = False,
) -> go.Figure:
    """
    Plot cumulative P&L equity curve over time.

    Parameters
    ----------
    pnl : pd.Series
        Daily P&L series with DatetimeIndex.
    title : str, default "Cumulative P&L"
        Chart title.
    show_drawdown_shading : bool, default False
        If True, shade drawdown regions in red.

    Returns
    -------
    go.Figure
        Plotly figure object ready for display or export.

    Notes
    -----
    Cumulative P&L is computed as cumsum of input series.
    Returns interactive chart with hover tooltips and zoom controls.
    """
    logger.info("Plotting equity curve: %d observations", len(pnl))

    cumulative_pnl = pnl.cumsum()

    fig = px.line(
        x=cumulative_pnl.index,
        y=cumulative_pnl.values,
        labels={"x": "Date", "y": "Cumulative P&L"},
        title=title,
    )

    fig.update_traces(line=dict(color="steelblue", width=2))
    fig.update_layout(
        hovermode="x unified",
        template="plotly_white",
        showlegend=False,
    )

    if show_drawdown_shading:
        running_max = cumulative_pnl.cummax()
        drawdown = cumulative_pnl - running_max
        in_drawdown = drawdown < 0

        # Add shaded regions for drawdowns
        for start_idx in range(len(in_drawdown)):
            if in_drawdown.iloc[start_idx] and (
                start_idx == 0 or not in_drawdown.iloc[start_idx - 1]
            ):
                # Find end of drawdown period
                end_idx = start_idx
                while end_idx < len(in_drawdown) and in_drawdown.iloc[end_idx]:
                    end_idx += 1

                fig.add_vrect(
                    x0=cumulative_pnl.index[start_idx],
                    x1=cumulative_pnl.index[min(end_idx, len(in_drawdown) - 1)],
                    fillcolor="red",
                    opacity=0.1,
                    layer="below",
                    line_width=0,
                )

    logger.debug("Equity curve plot generated successfully")
    return fig


def plot_signal(
    signal: pd.Series,
    title: str | None = None,
    threshold_lines: list[float] | None = None,
) -> go.Figure:
    """
    Plot time series of a single signal (typically z-score normalized).

    Parameters
    ----------
    signal : pd.Series
        Signal values with DatetimeIndex.
    title : str | None
        Chart title. Defaults to signal name if available.
    threshold_lines : list[float] | None
        Horizontal reference lines (e.g., [-2, 2] for z-score thresholds).

    Returns
    -------
    go.Figure
        Plotly figure object with signal trace and optional threshold lines.

    Notes
    -----
    Designed for z-score normalized signals with typical ranges [-3, 3].
    Use threshold_lines to mark regime boundaries or trading rules.
    """
    logger.info("Plotting signal: %d observations", len(signal))

    if title is None:
        title = getattr(signal, "name", "Signal")

    fig = px.line(
        x=signal.index,
        y=signal.values,
        labels={"x": "Date", "y": "Signal Value"},
        title=title,
    )

    fig.update_traces(line=dict(color="darkorange", width=1.5))
    fig.update_layout(
        hovermode="x unified",
        template="plotly_white",
        showlegend=False,
    )

    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    # Add threshold lines if specified
    if threshold_lines:
        for threshold in threshold_lines:
            fig.add_hline(
                y=threshold,
                line_dash="dot",
                line_color="red",
                opacity=0.4,
                annotation_text=f"±{abs(threshold)}",
            )

    logger.debug("Signal plot generated successfully")
    return fig


def plot_drawdown(
    pnl: pd.Series,
    title: str = "Drawdown",
    show_underwater_chart: bool = True,
) -> go.Figure:
    """
    Plot drawdown curve over time (peak-to-trough decline).

    Parameters
    ----------
    pnl : pd.Series
        Daily P&L series with DatetimeIndex.
    title : str, default "Drawdown"
        Chart title.
    show_underwater_chart : bool, default True
        If True, displays as underwater equity chart (negative values).
        If False, displays as percentage decline from peak.

    Returns
    -------
    go.Figure
        Plotly figure object showing drawdown evolution.

    Notes
    -----
    Drawdown is computed as current cumulative P&L minus running maximum.
    Always non-positive (zero at peaks, negative in drawdown).
    """
    logger.info("Plotting drawdown: %d observations", len(pnl))

    cumulative_pnl = pnl.cumsum()
    running_max = cumulative_pnl.cummax()
    drawdown = cumulative_pnl - running_max

    if not show_underwater_chart:
        # Convert to percentage decline
        drawdown = (drawdown / running_max.replace(0, 1)) * 100

    fig = px.area(
        x=drawdown.index,
        y=drawdown.values,
        labels={
            "x": "Date",
            "y": "Drawdown (%)" if not show_underwater_chart else "Drawdown",
        },
        title=title,
    )

    fig.update_traces(
        line=dict(color="crimson", width=1),
        fillcolor="rgba(220, 20, 60, 0.3)",
    )

    fig.update_layout(
        hovermode="x unified",
        template="plotly_white",
        showlegend=False,
    )

    # Add zero line
    fig.add_hline(y=0, line_dash="solid", line_color="black", opacity=0.3)

    max_dd = drawdown.min()
    logger.debug("Drawdown plot generated: max_dd=%.2f", max_dd)
    return fig


def plot_attribution(
    signal_contributions: pd.DataFrame,
    title: str = "Signal Attribution",
) -> go.Figure:
    """
    Plot signal-level P&L attribution over time.

    Parameters
    ----------
    signal_contributions : pd.DataFrame
        DatetimeIndex with columns for each signal's P&L contribution.
    title : str, default "Signal Attribution"
        Chart title.

    Returns
    -------
    go.Figure
        Plotly figure object with stacked area chart.

    Implementation Status
    ---------------------
    Not implemented — raises NotImplementedError.

    Notes
    -----
    Placeholder for future implementation.
    Intended for decomposing composite strategy P&L by signal.
    """
    raise NotImplementedError("Signal attribution plotting not yet implemented")


def plot_exposures(
    positions: pd.DataFrame,
    title: str = "Position Exposures",
) -> go.Figure:
    """
    Plot strategy exposures over time (notional, delta, etc.).

    Parameters
    ----------
    positions : pd.DataFrame
        DatetimeIndex with columns for exposure metrics.
    title : str, default "Position Exposures"
        Chart title.

    Returns
    -------
    go.Figure
        Plotly figure object with multi-line chart.

    Implementation Status
    ---------------------
    Not implemented — raises NotImplementedError.

    Notes
    -----
    Placeholder for future implementation.
    Intended for risk management and position monitoring.
    """
    raise NotImplementedError("Exposure plotting not yet implemented")


def plot_dashboard(
    backtest_results: dict[str, Any],
) -> go.Figure:
    """
    Generate comprehensive multi-panel dashboard.

    Parameters
    ----------
    backtest_results : dict[str, Any]
        Dictionary containing P&L, signals, positions, and metrics.

    Returns
    -------
    go.Figure
        Plotly figure with subplots (equity, drawdown, signals, exposures).

    Implementation Status
    ---------------------
    Not implemented — raises NotImplementedError.

    Notes
    -----
    Placeholder for future implementation.
    Intended for integrated view of all backtest outputs.
    """
    raise NotImplementedError("Dashboard plotting not yet implemented")
