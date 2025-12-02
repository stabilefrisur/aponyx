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
    DATA_DIR,
    RAW_DIR,
    REGISTRY_PATH,
    SIGNAL_CATALOG_PATH,
    STRATEGY_CATALOG_PATH,
)
from aponyx.data import DataRegistry
from aponyx.data.fetch_registry import get_fetch_spec
from aponyx.data.loaders import load_instrument_from_raw
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

        # Get all securities from Bloomberg securities config
        # Download all configured securities regardless of signal requirements
        from aponyx.data.bloomberg_config import list_securities

        all_securities = list_securities()  # Get all security IDs

        # Initialize registry
        data_registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        market_data = {}

        for security_id in sorted(all_securities):
            # Try loading from registry first (cached/processed data)
            matching_datasets = data_registry.list_datasets(instrument=security_id)

            if matching_datasets:
                # Use most recent dataset from registry
                dataset_name = sorted(matching_datasets)[-1]
                info = data_registry.get_dataset_info(dataset_name)
                df = load_parquet(info["file_path"])
                market_data[security_id] = df
                logger.debug("Loaded %s from registry: %d rows", security_id, len(df))
                continue

            # Registry empty - handle bloomberg vs file/synthetic sources differently
            if self.config.data_source == "bloomberg":
                # Bloomberg source: fetch fresh data or update current day
                logger.info(
                    "No cached data for %s - fetching from Bloomberg",
                    security_id,
                )

                from aponyx.data import fetch_cdx, fetch_vix, fetch_etf, BloombergSource
                from aponyx.data.bloomberg_config import get_security_spec

                source = BloombergSource()

                # Get instrument type for this security
                spec = get_security_spec(security_id)
                instrument_type = spec.instrument_type

                # Determine which fetch function to use based on instrument type
                if instrument_type == "vix":
                    df = fetch_vix(
                        source,
                        update_current_day=self.config.force_rerun,
                    )
                elif instrument_type == "etf":
                    df = fetch_etf(
                        source,
                        security=security_id,
                        update_current_day=self.config.force_rerun,
                    )
                elif instrument_type == "cdx":
                    df = fetch_cdx(
                        source,
                        security=security_id,
                        update_current_day=self.config.force_rerun,
                    )
                else:
                    raise ValueError(f"Unknown instrument type: {instrument_type}")

                market_data[security_id] = df
                logger.info(
                    "Fetched %s from Bloomberg: %d rows",
                    security_id,
                    len(df),
                )
                continue

            # For file/synthetic sources, try to load from raw directory
            raw_data_dir = RAW_DIR / self.config.data_source

            if not raw_data_dir.exists():
                raise ValueError(
                    f"No datasets found for security '{security_id}'. "
                    f"Raw data directory does not exist: {raw_data_dir}"
                )

            logger.info(
                "No cached data for %s - attempting to load from %s",
                security_id,
                raw_data_dir,
            )

            # Get instrument type for this security
            from aponyx.data.bloomberg_config import get_security_spec

            spec = get_security_spec(security_id)
            instrument_type = spec.instrument_type

            # Get fetch specification from registry
            fetch_spec = get_fetch_spec(instrument_type)

            # Load instrument data using generic loader with specific security
            # VIX doesn't require security parameter (single instrument)
            securities = [security_id] if fetch_spec.requires_security else None
            df = load_instrument_from_raw(
                raw_data_dir,
                instrument_type,
                fetch_spec.fetch_fn,
                securities,
            )

            market_data[security_id] = df

        output = {"market_data": market_data}
        self._log_complete(output)
        return output

    def output_exists(self) -> bool:
        # Data step doesn't cache (always loads from registry)
        return False

    def get_output_path(self) -> Path:
        return self.config.output_dir / "data"

    def load_cached_output(self) -> dict[str, Any]:
        """Load cached market data (always reload from registry)."""
        # Data step always reloads from registry, never uses cache
        return self.execute({})


class SignalStep(BaseWorkflowStep):
    """Compute signal values using indicator + transformation composition."""

    @property
    def name(self) -> str:
        return "signal"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()

        # Get all market data from previous step (keyed by security ID)
        raw_market_data = context["data"]["market_data"]

        # Load signal registry
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

        # Get the specific signal metadata for this workflow
        signal_metadata = signal_registry.get_metadata(self.config.signal_name)

        # Load indicator registry to get default_securities from indicators
        from aponyx.config import INDICATOR_CATALOG_PATH
        from aponyx.models.registry import IndicatorRegistry

        indicator_registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)

        # Build securities mapping from first indicator's default_securities
        # (or use config override if provided)
        if self.config.security_mapping:
            securities_to_use = self.config.security_mapping
            logger.info(
                "Using custom security mapping for signal '%s': %s",
                self.config.signal_name,
                securities_to_use,
            )
        else:
            # Get default_securities from the first indicator
            first_indicator_name = signal_metadata.indicator_dependencies[0]
            first_indicator_metadata = indicator_registry.get_metadata(
                first_indicator_name
            )
            securities_to_use = first_indicator_metadata.default_securities
            logger.info(
                "Using default securities from indicator '%s' for signal '%s': %s",
                first_indicator_name,
                self.config.signal_name,
                securities_to_use,
            )

        # Build instrument-type-keyed market data dict for signal computation
        # Map instrument types (cdx, etf, vix) to actual security data
        market_data = {}
        for inst_type, security_id in securities_to_use.items():
            if security_id not in raw_market_data:
                raise ValueError(
                    f"Signal '{self.config.signal_name}' requires security '{security_id}' "
                    f"(instrument type '{inst_type}'), but it was not loaded. "
                    f"Available: {sorted(raw_market_data.keys())}"
                )
            market_data[inst_type] = raw_market_data[security_id]
            logger.debug(
                "Mapped %s -> %s (%d rows)",
                inst_type,
                security_id,
                len(raw_market_data[security_id]),
            )

        # Compute the specific signal for this workflow
        from aponyx.models.orchestrator import _compute_signal

        signal = _compute_signal(signal_metadata, market_data)

        logger.info(
            "Computed signal '%s': %d values, %.2f%% non-null",
            self.config.signal_name,
            len(signal),
            100 * signal.notna().sum() / len(signal),
        )

        # Save signal to output directory
        output_dir = context.get("output_dir", self.config.output_dir) / "signals"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / "signal.parquet"
        signal_df = signal.to_frame(name="value")
        save_parquet(signal_df, output_path)
        logger.debug(
            "Saved signal to %s",
            output_path,
        )

        # Return the signal and the securities used for downstream steps
        output = {
            "signal": signal,
            "securities_used": securities_to_use,
        }
        self._log_complete(output)
        return output

    def output_exists(self) -> bool:
        """Check if signals directory exists and has signal files."""
        signal_dir = self.get_output_path()
        if not signal_dir.exists():
            return False
        # Check if there are any signal files
        signal_files = list(signal_dir.glob("*.parquet"))
        return len(signal_files) > 0

    def get_output_path(self) -> Path:
        # Use workflow output_dir from config (timestamped folder)
        return self.config.output_dir / "signals"

    def load_cached_output(self) -> dict[str, Any]:
        """Load cached signal from disk."""
        signal_dir = self.get_output_path()
        signal_file = signal_dir / f"{self.config.signal_name}.parquet"

        if not signal_file.exists():
            raise FileNotFoundError(f"Cached signal file not found: {signal_file}")

        signal_df = load_parquet(signal_file)
        signal = signal_df["value"]

        logger.info(
            "Loaded cached signal '%s': %d values",
            self.config.signal_name,
            len(signal),
        )

        # Securities used info is not cached, will use defaults
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
        signal_metadata = signal_registry.get_metadata(self.config.signal_name)
        securities_used = (
            self.config.security_mapping or signal_metadata.default_securities
        )

        return {
            "signal": signal,
            "securities_used": securities_used,
        }


class SuitabilityStep(BaseWorkflowStep):
    """Evaluate signal-product suitability."""

    @property
    def name(self) -> str:
        return "suitability"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()

        # Get signal from previous step
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

        # Get workflow output directory from context (timestamped folder)
        workflow_output_dir = context.get("output_dir", self.config.output_dir)
        output_dir = workflow_output_dir / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Extract timestamp from workflow output directory name
        workflow_dir_name = workflow_output_dir.name
        # Expected format: {signal}_{strategy}_{YYYYMMDD}_{HHMMSS}
        parts = workflow_dir_name.split("_")
        timestamp = f"{parts[-2]}_{parts[-1]}"  # YYYYMMDD_HHMMSS

        save_suitability_report(
            report, self.config.signal_name, product, output_dir, timestamp
        )

        output = {"suitability_result": result, "product": product}
        self._log_complete(output)
        return output

    def output_exists(self) -> bool:
        # Check for suitability report markdown file
        output_dir = self.get_output_path()
        report_files = list(output_dir.glob(f"{self.config.signal_name}_*.md"))
        return len(report_files) > 0

    def get_output_path(self) -> Path:
        # Use workflow output_dir from config (timestamped folder)
        return self.config.output_dir / "reports"

    def load_cached_output(self) -> dict[str, Any]:
        """Load cached suitability evaluation (report only, re-run for full data)."""
        # Get product from workflow config
        product = self.config.product

        # We only cache the product info, not the full evaluation result
        # Report exists on disk but we don't load it back into memory
        return {"suitability_result": None, "product": product}

    def _load_spread_for_product(
        self, data_registry: DataRegistry, product: str
    ) -> pd.DataFrame:
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
        return data_registry.load_dataset_by_security(product)


class BacktestStep(BaseWorkflowStep):
    """Run strategy backtest."""

    @property
    def name(self) -> str:
        return "backtest"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()

        # Get signal from previous step
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
        output_dir = context.get("output_dir", self.config.output_dir) / "backtest"
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
        # Use workflow output_dir from config (timestamped folder)
        return self.config.output_dir / "backtest"

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

    def _load_spread_for_product(
        self, data_registry: DataRegistry, product: str
    ) -> pd.DataFrame:
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
        return data_registry.load_dataset_by_security(product)


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

        # Get workflow output directory from context (timestamped folder)
        workflow_output_dir = context.get("output_dir", self.config.output_dir)
        output_dir = workflow_output_dir / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Extract timestamp from workflow output directory name
        workflow_dir_name = workflow_output_dir.name
        # Expected format: {signal}_{strategy}_{YYYYMMDD}_{HHMMSS}
        parts = workflow_dir_name.split("_")
        timestamp = f"{parts[-2]}_{parts[-1]}"  # YYYYMMDD_HHMMSS

        save_performance_report(
            report,
            self.config.signal_name,
            self.config.strategy_name,
            output_dir,
            timestamp,
        )

        output = {"performance": performance}
        self._log_complete(output)
        return output

    def output_exists(self) -> bool:
        # Check for performance report markdown file
        output_dir = self.get_output_path()
        report_files = list(
            output_dir.glob(
                f"{self.config.signal_name}_{self.config.strategy_name}_*.md"
            )
        )
        return len(report_files) > 0

    def get_output_path(self) -> Path:
        # Use workflow output_dir from config (timestamped folder)
        return self.config.output_dir / "reports"

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
        output_dir = (
            context.get("output_dir", self.config.output_dir) / "visualizations"
        )
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
        # Use workflow output_dir from config (timestamped folder)
        return self.config.output_dir / "visualization"

    def load_cached_output(self) -> dict[str, Any]:
        """Load cached visualizations (charts only, no in-memory figures)."""
        # Charts exist as HTML files on disk but we don't load them back
        return {"equity_fig": None, "drawdown_fig": None, "signal_fig": None}
