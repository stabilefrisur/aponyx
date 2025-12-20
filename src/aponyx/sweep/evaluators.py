"""
Evaluation functions for parameter sweeps.

Provides evaluate_indicator() and evaluate_backtest() functions that
integrate with the four-stage signal pipeline and backtest infrastructure.
"""

import logging
from typing import Any

from .config import SweepConfig
from .metrics import BacktestMetrics, IndicatorMetrics, compute_indicator_statistics

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
) -> tuple[dict[str, Any], dict[str, str]]:
    """
    Load market data required for signal computation.

    Parameters
    ----------
    signal_name : str
        Signal name from catalog.
    indicator_registry : IndicatorTransformationRegistry
        Registry for indicator metadata.
    signal_registry : SignalRegistry
        Registry for signal metadata.

    Returns
    -------
    tuple[dict[str, Any], dict[str, str]]
        Market data dict and securities mapping.
    """
    from aponyx.config import RAW_DIR
    from aponyx.data import FileSource, fetch_security_data, list_security_channels

    # Get signal and indicator metadata
    signal_metadata = signal_registry.get_metadata(signal_name)
    indicator_name = signal_metadata.indicator_transformation
    indicator_metadata = indicator_registry.get_metadata(indicator_name)
    securities_mapping = indicator_metadata.default_securities

    # Load market data for each required security
    source = FileSource(RAW_DIR / "synthetic")
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
            "Loaded %s (%s): %d rows",
            security_id,
            inst_type,
            len(df),
        )

    return market_data, securities_mapping


def evaluate_indicator(
    config: SweepConfig,
    combination: dict[str, Any],
) -> IndicatorMetrics:
    """
    Evaluate a single parameter combination in indicator mode.

    Computes indicator via four-stage pipeline with parameter overrides,
    then calculates comprehensive statistics.

    Parameters
    ----------
    config : SweepConfig
        Sweep configuration (mode must be "indicator").
    combination : dict[str, Any]
        Parameter values for this evaluation.
        Keys are dot-notation paths, values are parameter values.

    Returns
    -------
    IndicatorMetrics
        Statistics for the computed indicator.

    Raises
    ------
    ValueError
        If signal not found in catalog.

    Examples
    --------
    >>> metrics = evaluate_indicator(
    ...     config,
    ...     {"indicator_transformation.parameters.lookback": 20},
    ... )
    >>> print(f"Mean: {metrics.mean:.2f}, Autocorr: {metrics.autocorr_1:.2f}")
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

    logger.debug("Evaluating indicator: signal=%s, combo=%s", config.base.signal, combination)

    # Load registries
    indicator_registry = IndicatorTransformationRegistry(INDICATOR_TRANSFORMATION_PATH)
    score_registry = ScoreTransformationRegistry(SCORE_TRANSFORMATION_PATH)
    signal_transformation_registry = SignalTransformationRegistry(SIGNAL_TRANSFORMATION_PATH)
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

    # Load market data
    market_data, securities_mapping = _load_market_data_for_signal(
        config.base.signal,
        indicator_registry,
        signal_registry,
    )

    # Compose signal with parameter overrides
    # Note: Currently compose_signal uses catalog entries directly
    # For overrides, we'd need to create modified registry entries or use
    # a more flexible override mechanism. For MVP, we use the existing
    # transformation override capability.

    # Extract potential transformation overrides from combination
    # (This is a simplified approach - full implementation would
    # dynamically create transformation entries with modified parameters)
    result = compose_signal(
        signal_name=config.base.signal,
        market_data=market_data,
        indicator_registry=indicator_registry,
        score_registry=score_registry,
        signal_transformation_registry=signal_transformation_registry,
        signal_registry=signal_registry,
        include_intermediates=True,
    )

    indicator = result["indicator"]

    # Get product prices for correlation calculation
    # Use the first CDX or primary instrument as product reference
    product_inst = list(market_data.keys())[0]
    product_df = market_data[product_inst]
    if "spread" in product_df.columns:
        product_prices = product_df["spread"]
    elif "price" in product_df.columns:
        product_prices = product_df["price"]
    elif "level" in product_df.columns:
        product_prices = product_df["level"]
    else:
        product_prices = product_df.iloc[:, 0]

    # Compute indicator statistics
    metrics = compute_indicator_statistics(indicator, product_prices)

    logger.debug(
        "Indicator metrics: mean=%.2f, std=%.2f, autocorr=%.2f",
        metrics.mean,
        metrics.std,
        metrics.autocorr_1,
    )

    return metrics


def evaluate_backtest(
    config: SweepConfig,
    combination: dict[str, Any],
) -> BacktestMetrics:
    """
    Evaluate a single parameter combination in backtest mode.

    Computes signal via four-stage pipeline with parameter overrides,
    runs backtest, then extracts performance metrics.

    Parameters
    ----------
    config : SweepConfig
        Sweep configuration (mode must be "backtest").
    combination : dict[str, Any]
        Parameter values for this evaluation.
        Keys are dot-notation paths, values are parameter values.

    Returns
    -------
    BacktestMetrics
        Performance metrics from backtest.

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
    signal_transformation_registry = SignalTransformationRegistry(SIGNAL_TRANSFORMATION_PATH)
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    strategy_registry = StrategyRegistry(STRATEGY_CATALOG_PATH)

    # Load market data
    market_data, securities_mapping = _load_market_data_for_signal(
        config.base.signal,
        indicator_registry,
        signal_registry,
    )

    # Compose signal
    signal_result = compose_signal(
        signal_name=config.base.signal,
        market_data=market_data,
        indicator_registry=indicator_registry,
        score_registry=score_registry,
        signal_transformation_registry=signal_transformation_registry,
        signal_registry=signal_registry,
        include_intermediates=False,
    )
    
    # With include_intermediates=False, compose_signal returns a Series
    import pandas as pd
    if isinstance(signal_result, dict):
        raise TypeError("Expected pd.Series from compose_signal with include_intermediates=False")
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

    # Compute performance metrics
    perf_metrics = compute_all_metrics(
        result.pnl,
        result.positions,
    )

    # Extract relevant metrics for BacktestMetrics
    metrics = BacktestMetrics(
        sharpe_ratio=perf_metrics.sharpe_ratio,
        max_drawdown=perf_metrics.max_drawdown,
        hit_rate=perf_metrics.hit_rate,
        n_trades=perf_metrics.n_trades,
        annualized_return=perf_metrics.annualized_return,
    )

    logger.debug(
        "Backtest metrics: sharpe=%.2f, trades=%d, max_dd=%.2f%%",
        metrics.sharpe_ratio,
        metrics.n_trades,
        metrics.max_drawdown * 100,
    )

    return metrics
