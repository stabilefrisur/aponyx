"""
Evaluation functions for parameter sweeps.

Provides evaluate_indicator() and evaluate_backtest() functions that
integrate with the four-stage signal pipeline and backtest infrastructure.
Reuses evaluation modules (suitability, performance) for consistent metrics.
"""

import logging
from typing import Any

from aponyx.evaluation.performance.config import PerformanceMetrics
from aponyx.evaluation.suitability.evaluator import (
    SuitabilityResult,
    evaluate_signal_suitability,
)

from .config import SweepConfig

logger = logging.getLogger(__name__)


def _apply_parameter_overrides(
    base_params: dict[str, Any],
    combination: dict[str, Any],
    path_prefix: str,
) -> dict[str, Any]:
    """
    Apply parameter overrides matching a specific path prefix.

    Parameters
    ----------
    base_params : dict[str, Any]
        Original parameters to modify.
    combination : dict[str, Any]
        Parameter combination with full path keys.
    path_prefix : str
        Path prefix to filter by (e.g., "indicator_transformation.parameters.").

    Returns
    -------
    dict[str, Any]
        Modified parameters with overrides applied.
    """
    result = dict(base_params)
    for path, value in combination.items():
        if path.startswith(path_prefix):
            param_name = path[len(path_prefix) :]
            result[param_name] = value
            logger.debug("Override: %s = %s", path, value)
    return result


def _load_market_data_for_signal(
    signal_name: str,
    indicator_registry: Any,
    signal_registry: Any,
    data_source: str = "synthetic",
) -> tuple[dict[str, Any], dict[str, str]]:
    """
    Load market data required for signal computation.

    When using Bloomberg data source, ALL securities in the catalog are fetched
    to ensure they stay synced together. This prevents partial updates where only
    some securities are refreshed. For file sources, only required securities are loaded.

    Parameters
    ----------
    signal_name : str
        Signal name from catalog.
    indicator_registry : IndicatorTransformationRegistry
        Registry for indicator metadata.
    signal_registry : SignalRegistry
        Registry for signal metadata.
    data_source : str
        Data source type ("synthetic", "bloomberg", or custom sources).

    Returns
    -------
    tuple[dict[str, Any], dict[str, str]]
        Market data dict (keyed by instrument type for required securities) and securities mapping.

    Notes
    -----
    Bloomberg behavior: Fetches ALL securities from bloomberg_securities.json
    to keep them synced, then returns only the subset required for the indicator.
    File behavior: Fetches only the securities required for the indicator.
    """
    from aponyx.config import RAW_DIR
    from aponyx.data import fetch_security_data, list_security_channels
    from aponyx.data.sources import FileSource, BloombergSource

    # Get signal and indicator metadata
    signal_metadata = signal_registry.get_metadata(signal_name)
    indicator_name = signal_metadata.indicator_transformation
    indicator_metadata = indicator_registry.get_metadata(indicator_name)
    securities_mapping = indicator_metadata.default_securities

    # Create appropriate data source
    source: FileSource | BloombergSource
    if data_source == "bloomberg":
        source = BloombergSource()
        logger.info("Using Bloomberg data source - fetching ALL securities")
    else:
        # File-based source (synthetic or custom directory)
        raw_data_dir = RAW_DIR / data_source
        source = FileSource(raw_data_dir)
        logger.info("Using file data source: %s", raw_data_dir)

    # When using Bloomberg, fetch ALL securities to keep them synced
    # For file sources, only fetch required securities
    from aponyx.data.bloomberg_config import list_securities

    if data_source == "bloomberg":
        all_securities = list_securities()
        logger.info("Fetching all %d securities from Bloomberg", len(all_securities))

        # Fetch all securities (this updates cache/raw storage for all)
        for security_id in sorted(all_securities):
            all_channels = list_security_channels(security_id)
            df = fetch_security_data(
                source=source,
                security_id=security_id,
                channels=all_channels,
                use_cache=True,
            )
            logger.debug(
                "Fetched %s: %d rows, channels: %s",
                security_id,
                len(df),
                [c.value for c in all_channels],
            )

    # Load market data for securities required by this indicator
    market_data: dict[str, Any] = {}

    for inst_type, security_id in securities_mapping.items():
        all_channels = list_security_channels(security_id)
        df = fetch_security_data(
            source=source,
            security_id=security_id,
            channels=all_channels,
            use_cache=True,
        )
        market_data[inst_type] = df
        logger.debug(
            "Loaded %s (%s) for indicator: %d rows",
            security_id,
            inst_type,
            len(df),
        )

    return market_data, securities_mapping


def evaluate_indicator(
    config: SweepConfig,
    combination: dict[str, Any],
) -> SuitabilityResult:
    """
    Evaluate a single parameter combination in indicator mode.

    Computes indicator via four-stage pipeline with parameter overrides,
    then evaluates signal-product suitability using the evaluation module.

    Parameters
    ----------
    config : SweepConfig
        Sweep configuration (mode must be "indicator").
    combination : dict[str, Any]
        Parameter values for this evaluation.
        Keys are dot-notation paths, values are parameter values.

    Returns
    -------
    SuitabilityResult
        Comprehensive suitability evaluation with decision, scores, and diagnostics.

    Raises
    ------
    ValueError
        If signal not found in catalog.

    Examples
    --------
    >>> result = evaluate_indicator(
    ...     config,
    ...     {"indicator_transformation.parameters.lookback": 20},
    ... )
    >>> print(f"Decision: {result.decision}, Score: {result.composite_score:.2f}")
    """
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
    from aponyx.models.signal_composer import compose_signal

    logger.debug(
        "Evaluating indicator: signal=%s, combo=%s", config.base.signal, combination
    )

    # Load registries
    indicator_registry = IndicatorTransformationRegistry(INDICATOR_TRANSFORMATION_PATH)
    score_registry = ScoreTransformationRegistry(SCORE_TRANSFORMATION_PATH)
    signal_transformation_registry = SignalTransformationRegistry(
        SIGNAL_TRANSFORMATION_PATH
    )
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

    # Load market data
    market_data, securities_mapping = _load_market_data_for_signal(
        config.base.signal,
        indicator_registry,
        signal_registry,
        data_source=config.base.data_source,
    )

    # Compose signal with parameter overrides
    # Note: Currently compose_signal uses catalog entries directly
    # For overrides, we'd need to create modified registry entries or use
    # a more flexible override mechanism. For MVP, we use the existing
    # transformation override capability.

    # Extract potential transformation overrides from combination
    # (This is a simplified approach - full implementation would
    # dynamically create transformation entries with modified parameters)

    # Extract parameter overrides for each transformation stage
    indicator_params_override = _apply_parameter_overrides(
        {}, combination, "indicator_transformation.parameters."
    )
    score_params_override = _apply_parameter_overrides(
        {}, combination, "score_transformation.parameters."
    )
    signal_transformation_params_override = _apply_parameter_overrides(
        {}, combination, "signal_transformation.parameters."
    )

    result = compose_signal(
        signal_name=config.base.signal,
        market_data=market_data,
        indicator_registry=indicator_registry,
        score_registry=score_registry,
        signal_transformation_registry=signal_transformation_registry,
        signal_registry=signal_registry,
        indicator_params_override=indicator_params_override or None,
        score_params_override=score_params_override or None,
        signal_transformation_params_override=signal_transformation_params_override
        or None,
        include_intermediates=True,
    )

    indicator = result["indicator"]

    # Get product spread/price for suitability evaluation
    # Use the first CDX or primary instrument as target reference
    product_inst = list(market_data.keys())[0]
    product_df = market_data[product_inst]
    if "spread" in product_df.columns:
        target_series = product_df["spread"]
    elif "price" in product_df.columns:
        target_series = product_df["price"]
    elif "level" in product_df.columns:
        target_series = product_df["level"]
    else:
        target_series = product_df.iloc[:, 0]

    # Evaluate signal-product suitability using evaluation module
    # Uses default SuitabilityConfig for consistent evaluation
    suitability_result = evaluate_signal_suitability(
        signal=indicator,
        target_change=target_series,
    )

    logger.debug(
        "Suitability result: decision=%s, score=%.2f, t_stat=%.2f",
        suitability_result.decision,
        suitability_result.composite_score,
        list(suitability_result.t_stats.values())[0]
        if suitability_result.t_stats
        else 0.0,
    )

    return suitability_result


def evaluate_backtest(
    config: SweepConfig,
    combination: dict[str, Any],
) -> PerformanceMetrics:
    """
    Evaluate a single parameter combination in backtest mode.

    Computes signal via four-stage pipeline with parameter overrides,
    runs backtest, then computes full performance metrics.

    Parameters
    ----------
    config : SweepConfig
        Sweep configuration (mode must be "backtest").
    combination : dict[str, Any]
        Parameter values for this evaluation.
        Keys are dot-notation paths, values are parameter values.

    Returns
    -------
    PerformanceMetrics
        Comprehensive performance metrics (21+ fields) from backtest.

    Raises
    ------
    ValueError
        If signal or strategy not found in catalogs.

    Examples
    --------
    >>> metrics = evaluate_backtest(
    ...     config,
    ...     {"strategy.stop_loss_pct": 5.0},
    ... )
    >>> print(f"Sharpe: {metrics.sharpe_ratio:.2f}, Trades: {metrics.n_trades}")
    """
    from aponyx.backtest import run_backtest, StrategyRegistry, resolve_calculator
    from aponyx.config import (
        INDICATOR_TRANSFORMATION_PATH,
        SCORE_TRANSFORMATION_PATH,
        SIGNAL_CATALOG_PATH,
        SIGNAL_TRANSFORMATION_PATH,
        STRATEGY_CATALOG_PATH,
    )
    from aponyx.data import get_product_microstructure
    from aponyx.evaluation.performance import compute_all_metrics
    from aponyx.models.registry import (
        IndicatorTransformationRegistry,
        ScoreTransformationRegistry,
        SignalRegistry,
        SignalTransformationRegistry,
    )
    from aponyx.models.signal_composer import compose_signal

    logger.debug(
        "Evaluating backtest: signal=%s, strategy=%s, combo=%s",
        config.base.signal,
        config.base.strategy,
        combination,
    )

    # Load registries
    indicator_registry = IndicatorTransformationRegistry(INDICATOR_TRANSFORMATION_PATH)
    score_registry = ScoreTransformationRegistry(SCORE_TRANSFORMATION_PATH)
    signal_transformation_registry = SignalTransformationRegistry(
        SIGNAL_TRANSFORMATION_PATH
    )
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    strategy_registry = StrategyRegistry(STRATEGY_CATALOG_PATH)

    # Load market data
    market_data, securities_mapping = _load_market_data_for_signal(
        config.base.signal,
        indicator_registry,
        signal_registry,
        data_source=config.base.data_source,
    )

    # Extract parameter overrides for each transformation stage
    indicator_params_override = _apply_parameter_overrides(
        {}, combination, "indicator_transformation.parameters."
    )
    score_params_override = _apply_parameter_overrides(
        {}, combination, "score_transformation.parameters."
    )
    signal_transformation_params_override = _apply_parameter_overrides(
        {}, combination, "signal_transformation.parameters."
    )

    # Compose signal with parameter overrides
    signal_result = compose_signal(
        signal_name=config.base.signal,
        market_data=market_data,
        indicator_registry=indicator_registry,
        score_registry=score_registry,
        signal_transformation_registry=signal_transformation_registry,
        signal_registry=signal_registry,
        indicator_params_override=indicator_params_override or None,
        score_params_override=score_params_override or None,
        signal_transformation_params_override=signal_transformation_params_override
        or None,
        include_intermediates=False,
    )

    # With include_intermediates=False, compose_signal returns a Series
    import pandas as pd

    if isinstance(signal_result, dict):
        raise TypeError(
            "Expected pd.Series from compose_signal with include_intermediates=False"
        )
    signal: pd.Series = signal_result

    # Get product for backtest (use first CDX instrument as default)
    # A more sophisticated implementation would read from config

    # Find the primary CDX product for backtesting
    product = None
    for inst_type, security_id in securities_mapping.items():
        if inst_type == "cdx":
            product = security_id
            break

    if product is None:
        # Fallback to first available security
        product = list(securities_mapping.values())[0]

    # Get product microstructure
    microstructure = get_product_microstructure(product)

    # Get price/spread series for backtest
    if "cdx" in market_data:
        product_df = market_data["cdx"]
    else:
        product_df = market_data[list(market_data.keys())[0]]

    if "spread" in product_df.columns:
        price_series = product_df["spread"]
    elif "price" in product_df.columns:
        price_series = product_df["price"]
    else:
        price_series = product_df.iloc[:, 0]

    # Get strategy config
    if config.base.strategy is None:
        raise ValueError("Strategy must be specified for backtest mode")
    strategy_metadata = strategy_registry.get_metadata(config.base.strategy)

    # Apply strategy parameter overrides from combination
    # Extract strategy.* parameters
    strategy_overrides = {}
    for path, value in combination.items():
        if path.startswith("strategy."):
            param_name = path[len("strategy.") :]
            strategy_overrides[param_name] = value

    # Create backtest config with overrides
    backtest_config = strategy_metadata.to_config(
        transaction_cost_bps=microstructure.transaction_cost_bps,
    )

    # Apply any strategy overrides
    if strategy_overrides:
        # Use dataclasses.replace for type-safe override application
        from dataclasses import replace

        backtest_config = replace(backtest_config, **strategy_overrides)

    # Get calculator
    calculator = resolve_calculator(
        quote_type=microstructure.quote_type,
        dv01_per_million=microstructure.dv01_per_million,
    )

    # Align signal and price
    common_idx = signal.index.intersection(price_series.index)
    signal = signal.loc[common_idx]
    price_series = price_series.loc[common_idx]

    # Run backtest
    result = run_backtest(signal, price_series, backtest_config, calculator)

    # Compute comprehensive performance metrics using evaluation module
    metrics = compute_all_metrics(
        result.pnl,
        result.positions,
    )

    logger.debug(
        "Backtest metrics: sharpe=%.2f, trades=%d, max_dd=%.2f%%",
        metrics.sharpe_ratio,
        metrics.n_trades,
        metrics.max_drawdown * 100,
    )

    return metrics
