"""
Configuration dataclasses for indicator and signal generation.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class IndicatorConfig:
    """
    Runtime configuration parameters for indicator computation.

    Note: Most indicator parameters are defined at catalog-time in IndicatorMetadata.
    This config is for runtime overrides and caching behavior.

    Attributes
    ----------
    use_cache : bool
        Whether to use cached indicator values if available.
    force_recompute : bool
        Force recomputation even if cache exists.
    """

    use_cache: bool = True
    force_recompute: bool = False

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.use_cache and self.force_recompute:
            raise ValueError("Cannot set both use_cache and force_recompute to True")


@dataclass(frozen=True)
class TransformationConfig:
    """
    Runtime configuration parameters for signal transformations.

    Note: Most transformation parameters are defined at catalog-time in
    TransformationMetadata. This config is for runtime behavior.

    Attributes
    ----------
    min_valid_pct : float
        Minimum percentage of valid (non-NaN) values required after transformation.
        Values between 0.0 and 1.0. Default: 0.5 (50%)
    """

    min_valid_pct: float = 0.5

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if not 0.0 <= self.min_valid_pct <= 1.0:
            raise ValueError(
                f"min_valid_pct must be between 0.0 and 1.0, got {self.min_valid_pct}"
            )


@dataclass(frozen=True)
class SignalConfig:
    """
    Configuration parameters for individual signal computation.

    Attributes
    ----------
    lookback : int
        Rolling window size for normalization and statistics.
    min_periods : int
        Minimum observations required for valid calculation.
    """

    lookback: int = 20
    min_periods: int = 10

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.lookback <= 0:
            raise ValueError(f"lookback must be positive, got {self.lookback}")
        if self.min_periods <= 0:
            raise ValueError(f"min_periods must be positive, got {self.min_periods}")
        if self.min_periods > self.lookback:
            raise ValueError(
                f"min_periods ({self.min_periods}) cannot exceed lookback ({self.lookback})"
            )
