"""
Visualizer class wrapping plotting functions for extensibility.

Provides object-oriented interface for future enhancements like
theming, caching, export utilities, and Streamlit integration.
"""

import logging
from typing import Any

import pandas as pd
import plotly.graph_objects as go

from .plots import (
    plot_attribution,
    plot_dashboard,
    plot_drawdown,
    plot_equity_curve,
    plot_exposures,
    plot_research_dashboard,
    plot_signal,
)

logger = logging.getLogger(__name__)


class Visualizer:
    """
    Wrapper class for visualization functions with extensibility hooks.

    Provides unified interface for all plotting operations and future
    enhancements like custom themes, batch exports, or caching.

    Parameters
    ----------
    theme : str, default "plotly_white"
        Plotly template name for consistent styling.
    export_path : str | None
        Optional directory for automatic HTML/PNG export.

    Examples
    --------
    >>> viz = Visualizer()
    >>> fig = viz.equity_curve(daily_pnl)
    >>> fig.show()
    """

    def __init__(
        self,
        theme: str = "plotly_white",
        export_path: str | None = None,
    ) -> None:
        """Initialize visualizer with configuration."""
        self.theme = theme
        self.export_path = export_path
        logger.info("Visualizer initialized: theme=%s", theme)

    def equity_curve(
        self,
        pnl: pd.Series,
        title: str = "Cumulative P&L",
        show_drawdown_shading: bool = False,
    ) -> go.Figure:
        """
        Plot cumulative P&L equity curve.

        Delegates to plot_equity_curve with instance configuration.

        Parameters
        ----------
        pnl : pd.Series
            Daily P&L series with DatetimeIndex.
        title : str, default "Cumulative P&L"
            Chart title.
        show_drawdown_shading : bool, default False
            If True, shade drawdown regions.

        Returns
        -------
        go.Figure
            Plotly figure object.
        """
        fig = plot_equity_curve(pnl, title, show_drawdown_shading)
        fig.update_layout(template=self.theme)
        self._maybe_export(fig, "equity_curve")
        return fig

    def signal(
        self,
        signal: pd.Series,
        title: str | None = None,
        threshold_lines: list[float] | None = None,
    ) -> go.Figure:
        """
        Plot time series of a signal.

        Delegates to plot_signal with instance configuration.

        Parameters
        ----------
        signal : pd.Series
            Signal values with DatetimeIndex.
        title : str | None
            Chart title.
        threshold_lines : list[float] | None
            Horizontal reference lines.

        Returns
        -------
        go.Figure
            Plotly figure object.
        """
        fig = plot_signal(signal, title, threshold_lines)
        fig.update_layout(template=self.theme)
        self._maybe_export(fig, "signal")
        return fig

    def drawdown(
        self,
        pnl: pd.Series,
        title: str = "Drawdown",
        show_underwater_chart: bool = True,
    ) -> go.Figure:
        """
        Plot drawdown curve.

        Delegates to plot_drawdown with instance configuration.

        Parameters
        ----------
        pnl : pd.Series
            Daily P&L series with DatetimeIndex.
        title : str, default "Drawdown"
            Chart title.
        show_underwater_chart : bool, default True
            If True, displays as underwater chart.

        Returns
        -------
        go.Figure
            Plotly figure object.
        """
        fig = plot_drawdown(pnl, title, show_underwater_chart)
        fig.update_layout(template=self.theme)
        self._maybe_export(fig, "drawdown")
        return fig

    def attribution(
        self,
        signal_contributions: pd.DataFrame,
        title: str = "Signal Attribution",
    ) -> go.Figure:
        """
        Plot signal-level P&L attribution (placeholder).

        Parameters
        ----------
        signal_contributions : pd.DataFrame
            DatetimeIndex with columns for each signal's P&L.
        title : str, default "Signal Attribution"
            Chart title.

        Returns
        -------
        go.Figure
            Plotly figure object.

        Raises
        ------
        NotImplementedError
            Feature not yet implemented.
        """
        return plot_attribution(signal_contributions, title)

    def exposures(
        self,
        positions: pd.DataFrame,
        title: str = "Position Exposures",
    ) -> go.Figure:
        """
        Plot strategy exposures over time (placeholder).

        Parameters
        ----------
        positions : pd.DataFrame
            DatetimeIndex with exposure metrics.
        title : str, default "Position Exposures"
            Chart title.

        Returns
        -------
        go.Figure
            Plotly figure object.

        Raises
        ------
        NotImplementedError
            Feature not yet implemented.
        """
        return plot_exposures(positions, title)

    def dashboard(
        self,
        backtest_results: dict[str, Any],
    ) -> go.Figure:
        """
        Generate comprehensive multi-panel dashboard (placeholder).

        Parameters
        ----------
        backtest_results : dict[str, Any]
            Dictionary with P&L, signals, positions, and metrics.

        Returns
        -------
        go.Figure
            Plotly figure with subplots.

        Raises
        ------
        NotImplementedError
            Feature not yet implemented.
        """
        return plot_dashboard(backtest_results)

    def research_dashboard(
        self,
        traded_product: pd.Series,
        indicator: pd.Series,
        score: pd.Series,
        signal: pd.Series,
        positions: pd.Series,
        pnl: pd.Series,
        title: str | None = None,
    ) -> go.Figure:
        """
        Generate research dashboard with instance theme applied.

        Delegates to plot_research_dashboard with Visualizer configuration.

        Parameters
        ----------
        traded_product : pd.Series
            Traded instrument price/spread with DatetimeIndex.
        indicator : pd.Series
            Raw indicator output (Stage 1) with DatetimeIndex.
        score : pd.Series
            Normalized score (Stage 2) with DatetimeIndex.
        signal : pd.Series
            Trading signal (Stage 3) with DatetimeIndex.
        positions : pd.Series
            Position series from backtest with DatetimeIndex.
        pnl : pd.Series
            Daily P&L series from backtest with DatetimeIndex.
        title : str or None, optional
            Dashboard title.

        Returns
        -------
        go.Figure
            Plotly figure with instance theme applied.
        """
        fig = plot_research_dashboard(
            traded_product=traded_product,
            indicator=indicator,
            score=score,
            signal=signal,
            positions=positions,
            pnl=pnl,
            title=title,
        )
        fig.update_layout(template=self.theme)
        self._maybe_export(fig, "research_dashboard")
        return fig

    def _maybe_export(self, fig: go.Figure, name: str) -> None:
        """
        Export figure to HTML if export_path is configured.

        Parameters
        ----------
        fig : go.Figure
            Plotly figure to export.
        name : str
            Base filename (without extension).

        Notes
        -----
        Future enhancement for batch export and archival.
        """
        if self.export_path is not None:
            # Placeholder for export logic
            logger.debug("Export path configured but not yet implemented: %s", name)
