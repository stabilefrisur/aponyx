"""
Configuration for signal-product suitability evaluation.

Defines immutable configuration parameters for the suitability evaluation
process including lags, thresholds, and component weights.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SuitabilityConfig:
    """
    Configuration for signal-product suitability evaluation.

    This immutable dataclass defines all parameters controlling the evaluation
    process, including forecast horizons, sample requirements, decision thresholds,
    and component weights for composite scoring.

    Parameters
    ----------
    lags : list[int]
        Forecast horizons to test (e.g., [1, 3, 5] for 1-, 3-, and 5-day ahead).
        Must be non-empty list of positive integers.
    min_obs : int
        Minimum number of valid observations required for reliable inference.
        Must be at least 100. Default: 500.
    pass_threshold : float
        Composite score threshold for PASS decision (proceed to backtest).
        Must satisfy: 0 < hold_threshold < pass_threshold < 1.
        Default: 0.7.
    hold_threshold : float
        Composite score threshold for HOLD decision (marginal, requires judgment).
        Must satisfy: 0 < hold_threshold < pass_threshold < 1.
        Default: 0.4.
    data_health_weight : float
        Weight for data health component in composite score.
        Must be non-negative. All weights must sum to 1.0.
        Default: 0.2.
    predictive_weight : float
        Weight for predictive association component in composite score.
        Must be non-negative. All weights must sum to 1.0.
        Default: 0.4.
    economic_weight : float
        Weight for economic relevance component in composite score.
        Must be non-negative. All weights must sum to 1.0.
        Default: 0.2.
    stability_weight : float
        Weight for temporal stability component in composite score.
        Must be non-negative. All weights must sum to 1.0.
        Default: 0.2.

    Raises
    ------
    ValueError
        If any validation constraint is violated.

    Examples
    --------
    >>> config = SuitabilityConfig()  # Use defaults
    >>> config = SuitabilityConfig(lags=[1, 5, 10], min_obs=1000)
    >>> config = SuitabilityConfig(
    ...     pass_threshold=0.75,
    ...     hold_threshold=0.5,
    ...     predictive_weight=0.5,
    ...     economic_weight=0.3,
    ...     data_health_weight=0.1,
    ...     stability_weight=0.1,
    ... )
    """

    lags: list[int] = field(default_factory=lambda: [1, 3, 5])
    min_obs: int = 500
    pass_threshold: float = 0.7
    hold_threshold: float = 0.4
    data_health_weight: float = 0.2
    predictive_weight: float = 0.4
    economic_weight: float = 0.2
    stability_weight: float = 0.2

    def __post_init__(self) -> None:
        """
        Validate configuration parameters.

        Checks that lags are valid, thresholds are properly ordered,
        weights are non-negative and sum to 1.0, and minimum observations
        are sufficient.

        Raises
        ------
        ValueError
            If any validation constraint is violated.
        """
        # Validate lags
        if not self.lags:
            raise ValueError("lags must be a non-empty list")
        if not all(isinstance(lag, int) and lag > 0 for lag in self.lags):
            raise ValueError(f"All lags must be positive integers, got {self.lags}")

        # Validate thresholds ordering
        if not (0 < self.hold_threshold < self.pass_threshold < 1):
            raise ValueError(
                f"Thresholds must satisfy 0 < hold ({self.hold_threshold}) "
                f"< pass ({self.pass_threshold}) < 1"
            )

        # Validate weights
        weights = [
            self.data_health_weight,
            self.predictive_weight,
            self.economic_weight,
            self.stability_weight,
        ]
        if not all(w >= 0 for w in weights):
            raise ValueError(
                f"All weights must be non-negative, got {dict(zip(['data_health', 'predictive', 'economic', 'stability'], weights))}"
            )

        weight_sum = sum(weights)
        if abs(weight_sum - 1.0) > 1e-6:
            raise ValueError(
                f"Weights must sum to 1.0, got {weight_sum:.6f}. "
                f"Weights: data_health={self.data_health_weight}, "
                f"predictive={self.predictive_weight}, "
                f"economic={self.economic_weight}, "
                f"stability={self.stability_weight}"
            )

        # Validate minimum observations
        if self.min_obs < 100:
            raise ValueError(
                f"min_obs must be at least 100 for reliable inference, got {self.min_obs}"
            )
