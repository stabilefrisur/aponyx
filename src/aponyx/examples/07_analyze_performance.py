"""
Compute comprehensive performance metrics for backtest results.

Prerequisites
-------------
Backtest results saved from backtest execution (06_run_backtest.py):
- Positions file: data/processed/backtests/{signal}_{strategy}_positions.parquet
- P&L file: data/processed/backtests/{signal}_{strategy}_pnl.parquet

Outputs
-------
PerformanceResult with comprehensive metrics:
- All 21+ performance metrics (Sharpe, drawdown, profit factor, tail ratio, etc.)
- Subperiod stability analysis (quarterly breakdown with full metrics per period)
- Return attribution (directional, signal strength, win/loss decomposition)
- Overall stability score and interpretive summary
Performance report saved to reports/performance/{signal}_{strategy}_{timestamp}.md.

Examples
--------
Run from project root:
    python -m aponyx.examples.07_analyze_performance

Expected output: PerformanceResult with stability score ~0.7, profit factor ~1.5.
Markdown report saved to reports/performance/spread_momentum_balanced_{timestamp}.md.
"""

from aponyx.config import PROCESSED_DIR, PERFORMANCE_REPORTS_DIR
from aponyx.backtest import BacktestResult
from aponyx.evaluation.performance import (
    analyze_backtest_performance,
    PerformanceConfig,
    PerformanceResult,
    generate_performance_report,
    save_report,
)
from aponyx.persistence import load_parquet


def main() -> PerformanceResult:
    """
    Execute performance analysis workflow.

    Loads backtest results, computes comprehensive metrics,
    generates interpretive report, and saves outputs.

    Returns
    -------
    PerformanceResult
        Performance evaluation with metrics, attribution, and summary.
    """
    signal_name, strategy_name = define_analysis_parameters()
    backtest_result = load_backtest_result(signal_name, strategy_name)
    config = define_performance_config()
    performance = compute_performance_metrics(backtest_result, config)
    save_performance_report(performance, signal_name, strategy_name)
    return performance


def define_analysis_parameters() -> tuple[str, str]:
    """
    Define analysis parameters.

    Returns
    -------
    tuple[str, str]
        Signal name and strategy name.

    Notes
    -----
    Must match the signal-strategy combination from backtest step.
    """
    signal_name = "spread_momentum"
    strategy_name = "balanced"
    return signal_name, strategy_name


def load_backtest_result(
    signal_name: str,
    strategy_name: str,
) -> BacktestResult:
    """
    Load backtest results from processed directory.

    Parameters
    ----------
    signal_name : str
        Name of signal.
    strategy_name : str
        Name of strategy.

    Returns
    -------
    BacktestResult
        Backtest result with positions and P&L DataFrames.

    Notes
    -----
    Loads positions and P&L from separate parquet files saved
    by previous step (06_run_backtest.py). Reconstructs BacktestResult
    with minimal metadata for analysis.
    """
    backtests_dir = PROCESSED_DIR / "backtests"

    positions_path = backtests_dir / f"{signal_name}_{strategy_name}_positions.parquet"
    pnl_path = backtests_dir / f"{signal_name}_{strategy_name}_pnl.parquet"

    positions = load_parquet(positions_path)
    pnl = load_parquet(pnl_path)

    metadata = {
        "signal_id": signal_name,
        "strategy_id": strategy_name,
    }

    return BacktestResult(
        positions=positions,
        pnl=pnl,
        metadata=metadata,
    )


def define_performance_config() -> PerformanceConfig:
    """
    Define performance evaluation configuration.

    Returns
    -------
    PerformanceConfig
        Configuration with analysis parameters.

    Notes
    -----
    Uses quarterly subperiod analysis (n_subperiods=4) and
    3-month rolling window (rolling_window=63) for stability metrics.
    Attribution uses terciles (attribution_quantiles=3) for
    low/medium/high signal strength decomposition.
    """
    return PerformanceConfig(
        min_obs=252,
        n_subperiods=4,
        risk_free_rate=0.0,
        rolling_window=63,
        report_format="markdown",
        attribution_quantiles=3,
    )


def compute_performance_metrics(
    backtest_result: BacktestResult,
    config: PerformanceConfig,
) -> PerformanceResult:
    """
    Compute comprehensive performance metrics.

    Parameters
    ----------
    backtest_result : BacktestResult
        Backtest output with positions and P&L.
    config : PerformanceConfig
        Performance evaluation configuration.

    Returns
    -------
    PerformanceResult
        Complete performance analysis with metrics, attribution, and summary.

    Notes
    -----
    Orchestrates all performance computations:
    - Basic metrics: Sharpe, max drawdown, hit rate, trades
    - Extended metrics: rolling Sharpe stability, recovery time, tail ratios
    - Subperiod analysis: quarterly breakdown with full metrics per period
    - Attribution: directional, signal strength, win/loss decomposition
    - Stability score: consistency across subperiods
    - Summary: interpretive text with key findings
    """
    return analyze_backtest_performance(backtest_result, config)


def save_performance_report(
    performance: PerformanceResult,
    signal_name: str,
    strategy_name: str,
) -> None:
    """
    Generate and save performance report.

    Parameters
    ----------
    performance : PerformanceResult
        Performance analysis results.
    signal_name : str
        Name of signal.
    strategy_name : str
        Name of strategy.

    Notes
    -----
    Generates markdown report with formatted tables and saves to
    reports/performance/{signal}_{strategy}_{timestamp}.md.
    Report includes all metrics, attribution breakdown, and summary.
    """
    report = generate_performance_report(
        performance,
        signal_id=signal_name,
        strategy_id=strategy_name,
        generate_tearsheet=False,
    )
    save_report(report, signal_name, strategy_name, PERFORMANCE_REPORTS_DIR)


if __name__ == "__main__":
    main()
