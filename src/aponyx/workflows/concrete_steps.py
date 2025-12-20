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
from aponyx.data import DataRegistry, get_product_microstructure
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
from aponyx.backtest import run_backtest, resolve_calculator
from aponyx.backtest.registry import StrategyRegistry
from aponyx.visualization import (
    plot_equity_curve,
    plot_drawdown,
    plot_signal,
    plot_research_dashboard,
)
from aponyx.persistence import load_parquet, save_parquet
from .steps import BaseWorkflowStep

logger = logging.getLogger(__name__)


class DataStep(BaseWorkflowStep):
    """Load all required market data from registry or raw files.

    Uses the unified fetch_security_data() interface for channel-aware
    data fetching. All channels are loaded for each security to support
    different purposes (indicator, P&L, display).
    """

    @property
    def name(self) -> str:
        return "data"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()

        # Get all securities from Bloomberg securities config
        from aponyx.data.bloomberg_config import list_securities

        all_securities = list_securities()  # Get all security IDs

        # Initialize registry
        data_registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        market_data = {}

        for security_id in sorted(all_securities):
            # When force_rerun is enabled, skip registry lookup and fetch fresh data
            if not self.config.force_rerun:
                # Try loading from registry first (cached/processed data)
                matching_datasets = data_registry.list_datasets(instrument=security_id)

                if matching_datasets:
                    # Use most recent dataset from registry
                    dataset_name = sorted(matching_datasets)[-1]
                    info = data_registry.get_dataset_info(dataset_name)
                    df = load_parquet(info["file_path"])
                    market_data[security_id] = df
                    logger.debug(
                        "Loaded %s from registry: %d rows", security_id, len(df)
                    )
                    continue

            # Registry empty or force_rerun enabled - use unified fetch_security_data
            df = self._fetch_security(security_id)
            market_data[security_id] = df

        output = {"market_data": market_data}
        self._log_complete(output)
        return output

    def _fetch_security(self, security_id: str) -> pd.DataFrame:
        """
        Fetch security data using the unified fetch_security_data interface.

        Fetches ALL available channels for the security to support
        different downstream purposes (indicator, P&L, display).

        Parameters
        ----------
        security_id : str
            Security identifier (e.g., "cdx_ig_5y", "hyg", "vix").

        Returns
        -------
        pd.DataFrame
            DataFrame with all available channels as columns.
        """
        from aponyx.data.fetch import fetch_security_data, list_security_channels
        from aponyx.data.sources import FileSource, BloombergSource

        if self.config.data_source == "bloomberg":
            # Bloomberg source
            source = BloombergSource()
            logger.info(
                "Fetching %s from Bloomberg (all channels)",
                security_id,
            )
        else:
            # File/synthetic source
            raw_data_dir = RAW_DIR / self.config.data_source

            if not raw_data_dir.exists():
                raise ValueError(f"Raw data directory does not exist: {raw_data_dir}")

            source = FileSource(raw_data_dir)
            logger.info(
                "Loading %s from %s (all channels)",
                security_id,
                raw_data_dir,
            )

        # Fetch ALL available channels for this security
        # This allows downstream consumers (indicator, backtest, visualization)
        # to select the appropriate channel for their purpose
        all_channels = list_security_channels(security_id)

        df = fetch_security_data(
            source=source,
            security_id=security_id,
            channels=all_channels,  # Fetch all available channels
            use_cache=True,
        )

        logger.info(
            "Fetched %s: %d rows, channels: %s",
            security_id,
            len(df),
            [c.value for c in all_channels],
        )

        return df

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

        # Load all registries for four-stage pipeline
        from aponyx.config import (
            INDICATOR_TRANSFORMATION_PATH,
            SCORE_TRANSFORMATION_PATH,
            SIGNAL_CATALOG_PATH,
            SIGNAL_TRANSFORMATION_PATH,
        )
        from aponyx.models.registry import (
            IndicatorTransformationRegistry,
            ScoreTransformationRegistry,
            SignalRegistry,
            SignalTransformationRegistry,
        )

        indicator_registry = IndicatorTransformationRegistry(
            INDICATOR_TRANSFORMATION_PATH
        )
        score_registry = ScoreTransformationRegistry(SCORE_TRANSFORMATION_PATH)
        signal_transformation_registry = SignalTransformationRegistry(
            SIGNAL_TRANSFORMATION_PATH
        )
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

        # Get the specific signal metadata for this workflow
        signal_metadata = signal_registry.get_metadata(self.config.signal_name)

        # Build securities mapping from indicator's default_securities
        # (or use config override if provided)
        if self.config.security_mapping:
            securities_to_use = self.config.security_mapping
            logger.info(
                "Using custom security mapping for signal '%s': %s",
                self.config.signal_name,
                securities_to_use,
            )
        else:
            # Get default_securities from the indicator
            indicator_name = signal_metadata.indicator_transformation
            indicator_metadata = indicator_registry.get_metadata(indicator_name)
            securities_to_use = indicator_metadata.default_securities
            logger.info(
                "Using default securities from indicator '%s' for signal '%s': %s",
                indicator_name,
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

        # Compute the specific signal for this workflow using four-stage pipeline
        from aponyx.models.signal_composer import compose_signal

        result = compose_signal(
            signal_name=self.config.signal_name,
            market_data=market_data,
            indicator_registry=indicator_registry,
            score_registry=score_registry,
            signal_transformation_registry=signal_transformation_registry,
            signal_registry=signal_registry,
            indicator_transformation_override=self.config.indicator_transformation_override,
            score_transformation_override=self.config.score_transformation_override,
            signal_transformation_override=self.config.signal_transformation_override,
            include_intermediates=True,
        )

        # Extract intermediates from result
        indicator = result["indicator"]
        score = result["score"]
        signal = result["signal"]

        logger.info(
            "Computed signal '%s': %d values, %.2f%% non-null",
            self.config.signal_name,
            len(signal),
            100 * signal.notna().sum() / len(signal),
        )

        # Save all intermediates to output directory
        output_dir = context.get("output_dir", self.config.output_dir) / "signals"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save indicator, score, and signal parquet files
        save_parquet(indicator.to_frame(name="value"), output_dir / "indicator.parquet")
        save_parquet(score.to_frame(name="value"), output_dir / "score.parquet")
        save_parquet(signal.to_frame(name="value"), output_dir / "signal.parquet")
        logger.debug(
            "Saved indicator, score, signal to %s",
            output_dir,
        )

        # Return intermediates and securities used for downstream steps
        output = {
            "indicator": indicator,
            "score": score,
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
        # Get indicator metadata which has default_securities
        from aponyx.config import INDICATOR_TRANSFORMATION_PATH
        from aponyx.models.registry import IndicatorTransformationRegistry

        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
        signal_metadata = signal_registry.get_metadata(self.config.signal_name)

        # Get default securities from the indicator
        indicator_registry = IndicatorTransformationRegistry(
            INDICATOR_TRANSFORMATION_PATH
        )
        indicator_metadata = indicator_registry.get_metadata(
            signal_metadata.indicator_transformation
        )
        securities_used = (
            self.config.security_mapping or indicator_metadata.default_securities
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

        # Load spread data for product from DataStep context
        market_data = context["data"]["market_data"]
        spread_df = self._load_spread_for_product(market_data, product)

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
        self, market_data: dict[str, pd.DataFrame], product: str
    ) -> pd.DataFrame:
        """
        Load spread data for product from market data context.

        Parameters
        ----------
        market_data : dict[str, pd.DataFrame]
            Market data from DataStep context.
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
        if product not in market_data:
            available = sorted(market_data.keys())
            raise ValueError(
                f"No dataset found for security '{product}'. "
                f"Available datasets: {available}"
            )
        return market_data[product]


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

        # Load product microstructure parameters
        try:
            microstructure = get_product_microstructure(product)
        except ValueError as e:
            raise ValueError(f"Cannot run backtest for product '{product}': {e}") from e

        # Apply DV01 runtime override
        dv01 = (
            self.config.dv01_per_million_override
            if self.config.dv01_per_million_override is not None
            else microstructure.dv01_per_million
        )

        # Resolve calculator based on product quote_type
        calculator = resolve_calculator(
            quote_type=microstructure.quote_type,
            dv01_per_million=dv01,
        )

        # Transaction cost handling: pct mode vs bps mode
        if self.config.transaction_cost_pct_override is not None:
            # Use percentage-based transaction cost mode
            transaction_cost_bps: float | None = None
            transaction_cost_pct: float | None = (
                self.config.transaction_cost_pct_override
            )
        else:
            # Use fixed bps mode (override or product default)
            transaction_cost_bps = (
                self.config.transaction_cost_bps_override
                if self.config.transaction_cost_bps_override is not None
                else microstructure.transaction_cost_bps
            )
            transaction_cost_pct = None

        # Load spread/price data for backtest from DataStep context
        market_data = context["data"]["market_data"]
        product_df = self._load_spread_for_product(market_data, product)

        # Use appropriate column based on quote_type
        if microstructure.quote_type == "spread":
            price_series = product_df["spread"]
        elif "price" in product_df.columns:
            price_series = product_df["price"]
        elif "level" in product_df.columns:
            # Some price products may use 'level' column (e.g., VIX)
            price_series = product_df["level"]
        else:
            # Fallback to spread column if it exists
            price_series = product_df["spread"]

        # Align signal and price data to common dates
        common_idx = signal.index.intersection(price_series.index)
        signal = signal.loc[common_idx]
        price_series = price_series.loc[common_idx]

        logger.debug(
            "Aligned data: %d rows from %s to %s",
            len(common_idx),
            common_idx[0].date(),
            common_idx[-1].date(),
        )

        # Get strategy config from catalog
        strategy_registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
        strategy_metadata = strategy_registry.get_metadata(self.config.strategy_name)

        # Convert to backtest config (without DV01, now in calculator)
        backtest_config = strategy_metadata.to_config(
            transaction_cost_bps=transaction_cost_bps
            if transaction_cost_bps is not None
            else 0.0,
            transaction_cost_pct=transaction_cost_pct,
        )

        # Log configuration
        if transaction_cost_pct is not None:
            logger.info(
                "Backtest config: product=%s, quote_type=%s, calculator=%s, tcost=%.2f%% (pct mode)",
                product,
                microstructure.quote_type,
                type(calculator).__name__,
                transaction_cost_pct * 100,
            )
        else:
            logger.info(
                "Backtest config: product=%s, quote_type=%s, calculator=%s, tcost=%.1fbps",
                product,
                microstructure.quote_type,
                type(calculator).__name__,
                backtest_config.transaction_cost_bps,
            )

        # Run backtest with calculator injection
        result = run_backtest(signal, price_series, backtest_config, calculator)

        # Compute quick Sharpe for debug logging (handle zero std)
        pnl_std = result.pnl["net_pnl"].std()
        quick_sharpe = (
            result.pnl["net_pnl"].mean() / pnl_std * (252**0.5) if pnl_std > 0 else 0.0
        )
        logger.debug(
            "Backtest complete: %d trades, sharpe=%.2f",
            result.positions["position"].diff().abs().sum() / 2,
            quick_sharpe,
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
        self, market_data: dict[str, pd.DataFrame], product: str
    ) -> pd.DataFrame:
        """
        Load spread data for product from market data context.

        Parameters
        ----------
        market_data : dict[str, pd.DataFrame]
            Market data from DataStep context.
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
        if product not in market_data:
            available = sorted(market_data.keys())
            raise ValueError(
                f"No dataset found for security '{product}'. "
                f"Available datasets: {available}"
            )
        return market_data[product]


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

        # Get signal intermediates from signal step
        indicator = context["signal"]["indicator"]
        score = context["signal"]["score"]
        signal = context["signal"]["signal"]

        # T029: Resolve display channel from config or use default
        from aponyx.data.channels import DataChannel, UsagePurpose
        from aponyx.data.fetch import resolve_channel_for_purpose

        if self.config.display_channel is not None:
            # Use explicit display_channel from config
            display_channel = DataChannel(self.config.display_channel)
        else:
            # Use default for instrument type via UsagePurpose.DISPLAY
            display_channel = resolve_channel_for_purpose(
                self.config.product, UsagePurpose.DISPLAY
            )

        # Get traded product data using the resolved display channel
        market_data = context["data"]["market_data"]
        product_data = market_data[self.config.product]
        display_data = product_data[display_channel.value]
        logger.debug(
            "Using display channel '%s' for product '%s'",
            display_channel.value,
            self.config.product,
        )

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

        # Generate research dashboard with all pipeline stages
        research_dashboard_fig = plot_research_dashboard(
            traded_product=display_data,
            indicator=indicator,
            score=score,
            signal=signal,
            positions=positions["position"],
            pnl=pnl["net_pnl"],
            title=f"Research Dashboard: {self.config.signal_name}",
        )

        logger.debug("Generated 4 visualization charts including research dashboard")

        # Save charts (HTML)
        output_dir = (
            context.get("output_dir", self.config.output_dir) / "visualizations"
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        equity_fig.write_html(output_dir / "equity_curve.html")
        drawdown_fig.write_html(output_dir / "drawdown.html")
        signal_fig.write_html(output_dir / "signal.html")
        research_dashboard_fig.write_html(output_dir / "research_dashboard.html")

        output = {
            "equity_fig": equity_fig,
            "drawdown_fig": drawdown_fig,
            "signal_fig": signal_fig,
            "research_dashboard_fig": research_dashboard_fig,
        }
        self._log_complete(output)
        return output

    def output_exists(self) -> bool:
        output_path = self.get_output_path()
        equity_path = output_path / "equity_curve.html"
        dashboard_path = output_path / "research_dashboard.html"
        return equity_path.exists() and dashboard_path.exists()

    def get_output_path(self) -> Path:
        # Use workflow output_dir from config (timestamped folder)
        return self.config.output_dir / "visualization"

    def load_cached_output(self) -> dict[str, Any]:
        """Load cached visualizations (charts only, no in-memory figures)."""
        # Charts exist as HTML files on disk but we don't load them back
        return {"equity_fig": None, "drawdown_fig": None, "signal_fig": None}
