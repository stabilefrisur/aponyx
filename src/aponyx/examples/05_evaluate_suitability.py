"""
Evaluate signal-product suitability before backtesting.

Prerequisites
-------------
Signals saved from previous step (04_compute_signal.py):
- Signal files exist in data/processed/signals/{signal_name}.parquet
- CDX spread data available from registry

Outputs
-------
SuitabilityResult with decision and component scores:
- Decision: PASS, HOLD, or FAIL
- Component scores: data_health, predictive, economic, stability
- Suitability report saved to reports/suitability/{signal_name}_{product}.md
- Evaluation registered in suitability_registry.json

Examples
--------
Run from project root:
    python -m aponyx.examples.05_evaluate_suitability

Expected output: SuitabilityResult with PASS/HOLD/FAIL decision.
Report saved to reports/suitability/spread_momentum_cdx_ig_5y.md.
"""

import pandas as pd

from aponyx.config import (
    REGISTRY_PATH,
    DATA_DIR,
    PROCESSED_DIR,
    EVALUATION_DIR,
    SUITABILITY_REGISTRY_PATH,
)
from aponyx.data.registry import DataRegistry
from aponyx.evaluation.suitability import (
    SuitabilityConfig,
    SuitabilityResult,
    evaluate_signal_suitability,
    compute_forward_returns,
    generate_suitability_report,
    save_report,
    SuitabilityRegistry,
)
from aponyx.persistence import load_parquet


def main() -> SuitabilityResult:
    """
    Execute suitability evaluation workflow.

    Evaluates one signal against its target product using
    4-component scoring framework.

    Returns
    -------
    SuitabilityResult
        Evaluation result with decision and component scores.
    """
    signal_name, product = define_evaluation_pair()
    signal, target_change = prepare_evaluation_data(signal_name, product)
    config = define_evaluation_config()
    result = evaluate_suitability(signal, target_change, config)
    save_and_register_evaluation(result, signal_name, product)
    return result


def define_evaluation_pair() -> tuple[str, str]:
    """
    Define signal-product pair for evaluation.

    Returns
    -------
    tuple[str, str]
        Signal name and product identifier.

    Notes
    -----
    Choose one signal from catalog for demonstration.
    In practice, evaluate all enabled signals separately.
    """
    signal_name = "spread_momentum"
    product = "cdx_ig_5y"
    return signal_name, product


def prepare_evaluation_data(
    signal_name: str,
    product: str,
) -> tuple[pd.Series, pd.Series]:
    """
    Load signal and compute target returns for evaluation.

    Parameters
    ----------
    signal_name : str
        Name of signal to load from processed directory.
    product : str
        Product identifier for target returns.

    Returns
    -------
    tuple[pd.Series, pd.Series]
        Signal series and target change series (aligned).

    Notes
    -----
    Loads signal saved by previous step (04_compute_signal.py).
    Target is forward spread change (positive = widening).
    """
    signal = load_signal(signal_name)
    spread_df = load_spread_data(product)

    # Compute forward returns for 1-day ahead (default evaluation horizon)
    forward_returns = compute_forward_returns(spread_df["spread"], lags=[1])
    target_change = forward_returns[1]

    return signal, target_change


def load_signal(signal_name: str) -> pd.Series:
    """
    Load signal from processed directory.

    Parameters
    ----------
    signal_name : str
        Name of signal file (without .parquet extension).

    Returns
    -------
    pd.Series
        Signal series with DatetimeIndex.
    """
    signal_path = PROCESSED_DIR / "signals" / f"{signal_name}.parquet"
    signal_df = load_parquet(signal_path)
    return signal_df["value"]


def load_spread_data(product: str) -> pd.DataFrame:
    """
    Load spread data for target product.

    Parameters
    ----------
    product : str
        Product identifier (e.g., "cdx_ig_5y").

    Returns
    -------
    pd.DataFrame
        Spread data with DatetimeIndex.

    Notes
    -----
    Searches registry for datasets with matching security in metadata.
    """
    data_registry = DataRegistry(REGISTRY_PATH, DATA_DIR)

    all_datasets = data_registry.list_datasets()

    for dataset_name in all_datasets:
        info = data_registry.get_dataset_info(dataset_name)
        metadata = info.get("metadata", {})
        params = metadata.get("params", {})

        if params.get("security") == product:
            return load_parquet(info["file_path"])

    raise ValueError(f"No dataset found for product: {product}")


def define_evaluation_config() -> SuitabilityConfig:
    """
    Define suitability evaluation configuration.

    Returns
    -------
    SuitabilityConfig
        Configuration with test parameters and thresholds.
    """
    return SuitabilityConfig()


def evaluate_suitability(
    signal: pd.Series,
    target_change: pd.Series,
    config: SuitabilityConfig,
) -> SuitabilityResult:
    """
    Run suitability evaluation with 4-component scoring.

    Parameters
    ----------
    signal : pd.Series
        Signal to evaluate.
    target_change : pd.Series
        Forward target returns.
    config : SuitabilityConfig
        Evaluation configuration.

    Returns
    -------
    SuitabilityResult
        Evaluation result with decision and component scores.
    """
    return evaluate_signal_suitability(signal, target_change, config)


def save_and_register_evaluation(
    result: SuitabilityResult,
    signal_name: str,
    product: str,
) -> None:
    """
    Save markdown report and register evaluation.

    Parameters
    ----------
    result : SuitabilityResult
        Evaluation result.
    signal_name : str
        Name of evaluated signal.
    product : str
        Product identifier.
    """
    report = generate_suitability_report(result, signal_name, product)
    save_report(report, signal_name, product, EVALUATION_DIR)

    registry = SuitabilityRegistry(SUITABILITY_REGISTRY_PATH)
    registry.register_evaluation(result, signal_name, product)


if __name__ == "__main__":
    main()
