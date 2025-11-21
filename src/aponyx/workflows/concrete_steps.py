"""
Concrete workflow step implementations.

Each step wraps existing functionality from aponyx modules:
- DataStep: Fetches/generates data (wraps data providers)
- SignalStep: Computes signals (wraps models.signals)
- SuitabilityStep: Evaluates signal quality (wraps evaluation.suitability)
- BacktestStep: Runs strategy backtest (wraps backtest.engine)
- PerformanceStep: Computes extended metrics (wraps evaluation.performance)
- VisualizationStep: Generates charts (wraps visualization.plots)
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from aponyx.config import (
    PROCESSED_DIR,
    REGISTRY_PATH,
    DATA_DIR,
    RAW_DIR,
    SIGNAL_CATALOG_PATH,
    STRATEGY_CATALOG_PATH,
    EVALUATION_DIR,
    PERFORMANCE_REPORTS_DIR,
)
from aponyx.data import DataRegistry
from aponyx.data.requirements import get_required_data_keys
from aponyx.data.fetch_registry import get_fetch_spec
from aponyx.data.loaders import load_instrument_from_raw
from aponyx.data.bloomberg_config import list_securities
from aponyx.models import (
    compute_registered_signals,
    SignalConfig,
)
from aponyx.models.registry import SignalRegistry
from aponyx.evaluation.suitability import (
    evaluate_signal_suitability,
    compute_forward_returns,
    SuitabilityConfig,
    generate_suitability_report,
    save_report as save_suitability_report,
)
from aponyx.evaluation.performance import (
    analyze_backtest_performance,
    PerformanceConfig,
    generate_performance_report,
    save_report as save_performance_report,
)
from aponyx.backtest import run_backtest
from aponyx.backtest.registry import StrategyRegistry
from aponyx.visualization import plot_equity_curve, plot_drawdown, plot_signal
from aponyx.persistence import load_parquet, save_parquet
from .steps import BaseWorkflowStep

logger = logging.getLogger(__name__)


class DataStep(BaseWorkflowStep):
    """Load all required market data from registry or raw files."""

    @property
    def name(self) -> str:
        return "data"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()

        # Get required data keys from ALL enabled signals in catalog
        required_keys = get_required_data_keys(SIGNAL_CATALOG_PATH)

        # Initialize registry
        data_registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        market_data = {}

        for data_key in sorted(required_keys):
            # Try loading from registry first (cached/processed data)
            matching_datasets = data_registry.list_datasets(instrument=data_key)

            if matching_datasets:
                # Use most recent dataset from registry
                dataset_name = sorted(matching_datasets)[-1]
                info = data_registry.get_dataset_info(dataset_name)
                df = load_parquet(info["file_path"])
                market_data[data_key] = df
                logger.debug("Loaded %s from registry: %d rows", data_key, len(df))
                continue

            # Registry empty - try loading from raw files
            if self.config.data_source == "bloomberg":
                raise ValueError(
                    f"No datasets found for instrument '{data_key}'. "
                    f"Bloomberg data source requires running data download workflow first. "
                    f"See notebooks/01_data_download.ipynb"
                )

            # For file/synthetic sources, try to load from raw directory
            raw_data_dir = RAW_DIR / self.config.data_source

            if not raw_data_dir.exists():
                raise ValueError(
                    f"No datasets found for instrument '{data_key}'. "
                    f"Raw data directory does not exist: {raw_data_dir}"
                )

            logger.info(
                "No cached data for %s - attempting to load from %s",
                data_key,
                raw_data_dir,
            )

            # Get fetch specification from registry
            fetch_spec = get_fetch_spec(data_key)

            # Determine securities if needed
            securities = None
            if fetch_spec.requires_security:
                securities = list_securities(instrument_type=data_key)

            # Load instrument data using generic loader
            df = load_instrument_from_raw(
                raw_data_dir,
                data_key,
                fetch_spec.fetch_fn,
                securities,
            )

            market_data[data_key] = df

        output = {"market_data": market_data}
        self._log_complete(output)
        return output

    def output_exists(self) -> bool:
        # Data step doesn't cache (always loads from registry)
        return False

    def get_output_path(self) -> Path:
        return PROCESSED_DIR / "workflows" / "data" / self.config.signal_name

    def load_cached_output(self) -> dict[str, Any]:
        """Load cached market data (always reload from registry)."""
        # Data step always reloads from registry, never uses cache
        return self.execute({})


class SignalStep(BaseWorkflowStep):
    """Compute signal values."""

    @property
    def name(self) -> str:
        return "signal"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()

        # Get market data from previous step
        market_data = context["data"]["market_data"]

        # Compute all enabled signals using registry
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
        config = SignalConfig(lookback=20, min_periods=10)
        all_signals = compute_registered_signals(signal_registry, market_data, config)

        # Extract target signal for this workflow
        signal = all_signals[self.config.signal_name]
        logger.debug(
            "Computed signal %s: %d values, %.2f%% non-null",
            self.config.signal_name,
            len(signal),
            100 * signal.notna().sum() / len(signal),
        )

        # Save signal
        output_path = self.get_output_path() / f"{self.config.signal_name}.parquet"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        signal_df = signal.to_frame(name="value")
        save_parquet(signal_df, output_path)

        output = {"signal": signal}
        self._log_complete(output)
        return output

    def output_exists(self) -> bool:
        signal_path = self.get_output_path() / f"{self.config.signal_name}.parquet"
        return signal_path.exists()

    def get_output_path(self) -> Path:
        return PROCESSED_DIR / "workflows" / "signals" / self.config.signal_name

    def load_cached_output(self) -> dict[str, Any]:
        """Load cached signal from disk."""
        signal_path = self.get_output_path() / f"{self.config.signal_name}.parquet"
        signal_df = load_parquet(signal_path)
        signal = signal_df["value"]
        return {"signal": signal}


class SuitabilityStep(BaseWorkflowStep):
    """Evaluate signal-product suitability."""

    @property
    def name(self) -> str:
        return "suitability"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()

        signal = context["signal"]["signal"]

        # Get product from workflow config
        product = self.config.product

        # Load spread data for product
        data_registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        spread_df = self._load_spread_for_product(data_registry, product)

        # Compute forward returns for evaluation
        forward_returns = compute_forward_returns(spread_df["spread"], lags=[1])
        target_change = forward_returns[1]

        # Run suitability evaluation
        config = SuitabilityConfig()
        result = evaluate_signal_suitability(signal, target_change, config)

        logger.debug(
            "Suitability: %s, score=%.2f",
            result.decision,
            result.composite_score,
        )

        # Generate and save report
        report = generate_suitability_report(result, self.config.signal_name, product)
        save_suitability_report(report, self.config.signal_name, product, EVALUATION_DIR)

        output = {"suitability_result": result, "product": product}
        self._log_complete(output)
        return output

    def output_exists(self) -> bool:
        # Check for suitability report markdown file
        report_files = list(EVALUATION_DIR.glob(f"{self.config.signal_name}_*.md"))
        return len(report_files) > 0

    def get_output_path(self) -> Path:
        return EVALUATION_DIR

    def load_cached_output(self) -> dict[str, Any]:
        """Load cached suitability evaluation (report only, re-run for full data)."""
        # Get product from workflow config
        product = self.config.product

        # We only cache the product info, not the full evaluation result
        # Report exists on disk but we don't load it back into memory
        return {"suitability_result": None, "product": product}

    def _load_spread_for_product(self, data_registry: DataRegistry, product: str) -> pd.DataFrame:
        """
        Load spread data for product from registry.

        Parameters
        ----------
        data_registry : DataRegistry
            Data registry instance.
        product : str
            Product identifier (e.g., "cdx_ig_5y").

        Returns
        -------
        pd.DataFrame
            Spread data with DatetimeIndex.

        Raises
        ------
        ValueError
            If no dataset found for product.
        """
        all_datasets = data_registry.list_datasets()

        for dataset_name in all_datasets:
            info = data_registry.get_dataset_info(dataset_name)
            metadata = info.get("metadata", {})
            params = metadata.get("params", {})

            if params.get("security") == product:
                logger.debug("Found product data: %s", dataset_name)
                return load_parquet(info["file_path"])

        raise ValueError(f"No dataset found for product: {product}")


class BacktestStep(BaseWorkflowStep):
    """Run strategy backtest."""

    @property
    def name(self) -> str:
        return "backtest"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()

        signal = context["signal"]["signal"]
        # Get product from config, or from suitability step if available
        product = context.get("suitability", {}).get("product") or self.config.product

        # Load spread data for backtest
        data_registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        spread_df = self._load_spread_for_product(data_registry, product)
        spread = spread_df["spread"]

        # Align signal and spread to common dates
        common_idx = signal.index.intersection(spread.index)
        signal = signal.loc[common_idx]
        spread = spread.loc[common_idx]

        logger.debug(
            "Aligned data: %d rows from %s to %s",
            len(common_idx),
            common_idx[0].date(),
            common_idx[-1].date(),
        )

        # Get strategy config from catalog
        strategy_registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
        strategy_metadata = strategy_registry.get_metadata(self.config.strategy_name)
        backtest_config = strategy_metadata.to_config()

        # Run backtest using function (not class)
        result = run_backtest(signal, spread, backtest_config)

        logger.debug(
            "Backtest complete: %d trades, sharpe=%.2f",
            result.positions["position"].diff().abs().sum() / 2,
            result.pnl["net_pnl"].mean() / result.pnl["net_pnl"].std() * (252**0.5),
        )

        # Save results
        output_dir = self.get_output_path()
        output_dir.mkdir(parents=True, exist_ok=True)

        save_parquet(result.pnl, output_dir / "pnl.parquet")
        save_parquet(result.positions, output_dir / "positions.parquet")

        output = {"backtest_result": result}
        self._log_complete(output)
        return output

    def output_exists(self) -> bool:
        pnl_path = self.get_output_path() / "pnl.parquet"
        positions_path = self.get_output_path() / "positions.parquet"
        return pnl_path.exists() and positions_path.exists()

    def get_output_path(self) -> Path:
        return (
            PROCESSED_DIR
            / "workflows"
            / "backtests"
            / f"{self.config.signal_name}_{self.config.strategy_name}"
        )

    def load_cached_output(self) -> dict[str, Any]:
        """Load cached backtest results from disk."""
        from aponyx.backtest import BacktestResult

        output_dir = self.get_output_path()
        pnl = load_parquet(output_dir / "pnl.parquet")
        positions = load_parquet(output_dir / "positions.parquet")

        # Create minimal metadata for cached results
        metadata = {
            "signal_name": self.config.signal_name,
            "strategy_name": self.config.strategy_name,
            "product": self.config.product,
            "cached": True,
        }

        result = BacktestResult(pnl=pnl, positions=positions, metadata=metadata)
        return {"backtest_result": result}

    def _load_spread_for_product(self, data_registry: DataRegistry, product: str) -> pd.DataFrame:
        """
        Load spread data for product from registry.

        Parameters
        ----------
        data_registry : DataRegistry
            Data registry instance.
        product : str
            Product identifier (e.g., "cdx_ig_5y").

        Returns
        -------
        pd.DataFrame
            Spread data with DatetimeIndex.

        Raises
        ------
        ValueError
            If no dataset found for product.
        """
        all_datasets = data_registry.list_datasets()

        for dataset_name in all_datasets:
            info = data_registry.get_dataset_info(dataset_name)
            metadata = info.get("metadata", {})
            params = metadata.get("params", {})

            if params.get("security") == product:
                return load_parquet(info["file_path"])

        raise ValueError(f"No dataset found for product: {product}")


class PerformanceStep(BaseWorkflowStep):
    """Compute extended performance metrics."""

    @property
    def name(self) -> str:
        return "performance"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()

        backtest_result = context["backtest"]["backtest_result"]

        # Compute comprehensive performance metrics
        config = PerformanceConfig(
            n_subperiods=4,
            rolling_window=63,
            attribution_quantiles=3,
        )
        performance = analyze_backtest_performance(backtest_result, config)

        logger.debug(
            "Performance metrics: sharpe=%.2f, max_dd=%.2f%%",
            performance.metrics.sharpe_ratio,
            performance.metrics.max_drawdown * 100,
        )

        # Generate and save report
        report = generate_performance_report(
            performance,
            signal_id=self.config.signal_name,
            strategy_id=self.config.strategy_name,
            generate_tearsheet=False,
        )
        save_performance_report(
            report,
            self.config.signal_name,
            self.config.strategy_name,
            PERFORMANCE_REPORTS_DIR,
        )

        output = {"performance": performance}
        self._log_complete(output)
        return output

    def output_exists(self) -> bool:
        # Check for performance report markdown file
        report_files = list(
            PERFORMANCE_REPORTS_DIR.glob(
                f"{self.config.signal_name}_{self.config.strategy_name}_*.md"
            )
        )
        return len(report_files) > 0

    def get_output_path(self) -> Path:
        return PERFORMANCE_REPORTS_DIR

    def load_cached_output(self) -> dict[str, Any]:
        """Load cached performance evaluation (report only, no in-memory data)."""
        # Performance report exists on disk but we don't load it back
        return {"performance": None}


class VisualizationStep(BaseWorkflowStep):
    """Generate visualization charts."""

    @property
    def name(self) -> str:
        return "visualization"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()

        backtest_result = context["backtest"]["backtest_result"]
        pnl = backtest_result.pnl
        positions = backtest_result.positions

        # Generate charts with descriptive titles
        title_prefix = f"{self.config.signal_name} ({self.config.strategy_name})"
        equity_fig = plot_equity_curve(
            pnl["net_pnl"],
            title=f"Equity Curve: {title_prefix}",
            show_drawdown_shading=True,
        )
        drawdown_fig = plot_drawdown(
            pnl["net_pnl"],
            title=f"Drawdown: {title_prefix}",
        )
        signal_fig = plot_signal(
            positions["signal"],
            title=f"Signal: {self.config.signal_name}",
        )

        logger.debug("Generated 3 visualization charts")

        # Save charts (HTML)
        output_dir = self.get_output_path()
        output_dir.mkdir(parents=True, exist_ok=True)

        equity_fig.write_html(output_dir / "equity_curve.html")
        drawdown_fig.write_html(output_dir / "drawdown.html")
        signal_fig.write_html(output_dir / "signal.html")

        output = {
            "equity_fig": equity_fig,
            "drawdown_fig": drawdown_fig,
            "signal_fig": signal_fig,
        }
        self._log_complete(output)
        return output

    def output_exists(self) -> bool:
        equity_path = self.get_output_path() / "equity_curve.html"
        return equity_path.exists()

    def get_output_path(self) -> Path:
        return (
            PROCESSED_DIR
            / "workflows"
            / "visualizations"
            / f"{self.config.signal_name}_{self.config.strategy_name}"
        )

    def load_cached_output(self) -> dict[str, Any]:
        """Load cached visualizations (charts only, no in-memory figures)."""
        # Charts exist as HTML files on disk but we don't load them back
        return {"equity_fig": None, "drawdown_fig": None, "signal_fig": None}
