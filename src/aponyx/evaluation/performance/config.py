"""
Configuration for backtest performance evaluation.

Defines immutable configuration parameters for performance analysis
including subperiod analysis, rolling metrics, and reporting options.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PerformanceConfig:
    """
    Configuration for backtest performance evaluation.

    This immutable dataclass defines all parameters controlling the performance
    evaluation process, including minimum observations, subperiod stability checks,
    rolling metric windows, and reporting preferences.

    Parameters
    ----------
    min_obs : int
        Minimum number of observations required for reliable analysis.
        Must be at least 100. Default: 252 (one trading year).
    n_subperiods : int
        Number of equal subperiods for stability analysis.
        Must be at least 2. Default: 4 (quarterly).
    risk_free_rate : float
        Annual risk-free rate for Sharpe/Sortino calculations.
        Must be non-negative. Default: 0.0.
    rolling_window : int
        Window length (days) for rolling metric calculations.
        Must be at least 20. Default: 63 (3 months).
    report_format : str
        Output format for performance reports.
        Must be 'markdown', 'json', or 'html'. Default: 'markdown'.
    attribution_quantiles : int
        Number of signal quantile buckets for attribution analysis.
        Must be at least 2. Default: 3 (terciles: low/mid/high).

    Raises
    ------
    ValueError
        If any validation constraint is violated.

    Examples
    --------
    >>> config = PerformanceConfig()  # Use defaults
    >>> config = PerformanceConfig(n_subperiods=6, rolling_window=126)
    >>> config = PerformanceConfig(
    ...     min_obs=500,
    ...     risk_free_rate=0.02,
    ...     attribution_quantiles=5,
    ... )
    """

    min_obs: int = 252
    n_subperiods: int = 4
    risk_free_rate: float = 0.0
    rolling_window: int = 63
    report_format: str = "markdown"
    attribution_quantiles: int = 3

    def __post_init__(self) -> None:
        """
        Validate configuration parameters.

        Checks that observation counts are sufficient, subperiod and window
        settings are valid, risk-free rate is non-negative, and report format
        is supported.

        Raises
        ------
        ValueError
            If any validation constraint is violated.
        """
        # Validate minimum observations
        if self.min_obs < 100:
            raise ValueError(
                f"min_obs must be at least 100 for reliable analysis, got {self.min_obs}"
            )

        # Validate subperiods
        if self.n_subperiods < 2:
            raise ValueError(
                f"n_subperiods must be at least 2 for stability analysis, got {self.n_subperiods}"
            )

        # Validate risk-free rate
        if self.risk_free_rate < 0:
            raise ValueError(f"risk_free_rate must be non-negative, got {self.risk_free_rate}")

        # Validate rolling window
        if self.rolling_window < 20:
            raise ValueError(f"rolling_window must be at least 20 days, got {self.rolling_window}")

        # Validate report format
        valid_formats = {"markdown", "json", "html"}
        if self.report_format not in valid_formats:
            raise ValueError(
                f"report_format must be one of {valid_formats}, got '{self.report_format}'"
            )

        # Validate attribution quantiles
        if self.attribution_quantiles < 2:
            raise ValueError(
                f"attribution_quantiles must be at least 2, got {self.attribution_quantiles}"
            )


@dataclass
class PerformanceResult:
    """
    Container for performance evaluation results.

    This dataclass stores all outputs from a backtest performance analysis,
    including extended metrics, subperiod stability assessment, attribution
    breakdown, and interpretive summary.

    Attributes
    ----------
    metrics : dict[str, float]
        Extended performance metrics beyond basic backtest statistics.
        Includes rolling Sharpe, drawdown recovery time, tail ratios,
        profit factor, and consistency metrics.
    subperiod_analysis : dict[str, Any]
        Stability assessment across temporal subperiods.
        Contains per-period metrics and consistency scores.
    attribution : dict[str, dict[str, float]]
        Return attribution by various dimensions.
        Includes breakdown by trade direction, signal quantile,
        and win/loss decomposition.
    stability_score : float
        Overall stability metric (0-1 scale) measuring consistency
        of performance across subperiods.
    summary : str
        Interpretive text summarizing key findings and recommendations.
    timestamp : str
        ISO 8601 timestamp of evaluation execution.
    config : PerformanceConfig
        Configuration used for this evaluation.
    metadata : dict[str, Any]
        Additional context including signal_id, strategy_id, and
        evaluator version.

    Notes
    -----
    This structure is designed for easy serialization to JSON and
    integration with visualization and reporting layers.
    """

    metrics: dict[str, float]
    subperiod_analysis: dict[str, Any]
    attribution: dict[str, dict[str, float]]
    stability_score: float
    summary: str
    timestamp: str
    config: PerformanceConfig
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert result to dictionary for JSON serialization.

        Returns
        -------
        dict[str, Any]
            Complete result as nested dictionary with all fields.

        Notes
        -----
        Config is converted to dict using dataclass asdict functionality.
        """
        from dataclasses import asdict

        return {
            "metrics": self.metrics,
            "subperiod_analysis": self.subperiod_analysis,
            "attribution": self.attribution,
            "stability_score": self.stability_score,
            "summary": self.summary,
            "timestamp": self.timestamp,
            "config": asdict(self.config),
            "metadata": self.metadata,
        }
