"""
Metadata dataclasses for catalog management.

This module defines the metadata structures for indicator, transformation,
and signal definitions stored in their respective catalog JSON files.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IndicatorMetadata:
    """
    Metadata for a registered indicator computation.

    Indicators compute economically interpretable market metrics (spread differences,
    ratios, momentum) without signal-level normalization.

    Attributes
    ----------
    name : str
        Unique indicator identifier (lowercase, underscores only).
        Example: "cdx_etf_spread_diff", "spread_momentum_5d"
    description : str
        Human-readable explanation of economic meaning.
    compute_function_name : str
        Name of the compute function in indicators module.
    data_requirements : dict[str, str]
        Mapping from instrument types to required data fields.
        Example: {"cdx": "spread", "etf": "spread"}
    default_securities : dict[str, str]
        Default security identifiers for each instrument type.
        Example: {"cdx": "cdx_ig_5y", "etf": "lqd"}
    output_units : str
        Units of output values for economic interpretation.
        Valid values: "basis_points", "ratio", "percentage", "index_level", "volatility_points"
    parameters : dict[str, Any]
        Fixed computation parameters for this indicator.
        Example: {"lookback": 5, "method": "simple"}
    enabled : bool
        Whether indicator is available for use.
    """

    name: str
    description: str
    compute_function_name: str
    data_requirements: dict[str, str]
    default_securities: dict[str, str]
    output_units: str
    parameters: dict[str, Any]
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate indicator metadata."""
        if not self.name or not re.match(r"^[a-z][a-z0-9_]*$", self.name):
            raise ValueError(
                f"Indicator name must be lowercase with underscores, got: {self.name}"
            )
        if not self.compute_function_name:
            raise ValueError("compute_function_name cannot be empty")
        if not self.data_requirements:
            raise ValueError(f"Indicator {self.name} has no data requirements")

        # Validate output_units
        valid_units = {
            "basis_points",
            "ratio",
            "percentage",
            "index_level",
            "volatility_points",
        }
        if self.output_units not in valid_units:
            raise ValueError(
                f"Invalid output_units '{self.output_units}', must be one of: {valid_units}"
            )


@dataclass(frozen=True)
class TransformationMetadata:
    """
    Metadata for a registered signal transformation.

    Transformations are reusable operations (z-score, volatility adjustment, filters)
    applied to indicator outputs during signal composition.

    Attributes
    ----------
    name : str
        Unique transformation identifier (lowercase, underscores only).
        Example: "z_score_20d", "volatility_adjust_5d"
    description : str
        Human-readable explanation of transformation.
    transform_type : str
        Type of transformation from data.transforms module.
        Valid values: "z_score", "normalized_change", "diff", "pct_change", "log_return"
    parameters : dict[str, Any]
        Fixed transformation parameters.
        Example: {"window": 20, "min_periods": 10} for z_score
    enabled : bool
        Whether transformation is available for use.
    """

    name: str
    description: str
    transform_type: str
    parameters: dict[str, Any]
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate transformation metadata."""
        if not self.name or not re.match(r"^[a-z][a-z0-9_]*$", self.name):
            raise ValueError(
                f"Transformation name must be lowercase with underscores, got: {self.name}"
            )

        # Validate transform_type
        valid_types = {
            "z_score",
            "normalized_change",
            "diff",
            "pct_change",
            "log_return",
        }
        if self.transform_type not in valid_types:
            raise ValueError(
                f"Invalid transform_type '{self.transform_type}', must be one of: {valid_types}"
            )

        # Validate parameters for specific transform types
        if self.transform_type in ("z_score", "normalized_change"):
            if "window" not in self.parameters:
                raise ValueError(
                    f"Transformation {self.name} of type {self.transform_type} requires 'window' parameter"
                )


@dataclass(frozen=True)
class SignalMetadata:
    """
    Metadata for a registered signal computation.

    SIGNAL COMPOSITION PATTERN
    --------------------------
    Every signal is ALWAYS composed from two components:
    1. Indicator(s) - Economically interpretable metrics (spread differences, momentum, etc.)
    2. Transformation(s) - Signal processing operations (z-score, volatility adjustment, etc.)

    This separation enables:
    - Reusing indicators across multiple signals with different transformations
    - Swapping transformations without recomputing indicators (caching efficiency)
    - Clear attribution of signal behavior to economic driver vs. processing
    - Runtime experimentation via indicator_override/transformation_override

    EXAMPLE: cdx_etf_basis signal
    - Indicator: "cdx_etf_spread_diff" (basis in raw bps)
    - Transformation: "z_score_20d" (normalize to trading signal)
    - Result: Tradeable signal with positive = long credit risk

    Attributes
    ----------
    name : str
        Unique signal identifier (lowercase with underscores).
        Example: "cdx_etf_basis", "spread_momentum"
    description : str
        Human-readable description of signal purpose and logic.
        Minimum 10 characters.
    indicator_dependencies : list[str]
        List of indicator names required for this signal (REQUIRED, cannot be empty).
        All indicators must exist in indicator_catalog.json.
        For single-indicator signals: ["cdx_etf_spread_diff"]
        For multi-indicator signals: ["indicator_a", "indicator_b"]
    transformations : list[str]
        List of transformation names to apply to indicators (REQUIRED, cannot be empty).
        All transformations must exist in transformation_catalog.json.
        For single-indicator signals: ["z_score_20d"] (applied to indicator)
        For multi-indicator signals: ["z_score_20d", "z_score_60d"] (one per indicator)
    composition_logic : str | None
        Optional Python expression for combining multiple indicators.
        ONLY used for multi-indicator signals (len(indicator_dependencies) > 1).
        Example: "(indicator_a + indicator_b) / 2"
        Default: None (single indicator, transformation applied directly)
    enabled : bool
        Whether signal should be included in computation.
        Default: True
    sign_multiplier : int
        Multiplier to apply to final signal output for sign convention alignment.
        Positive signal = long credit risk (buy CDX).
        Use -1 to invert signals that naturally produce opposite signs.
        Must be -1 or 1.
        Default: 1 (no inversion)

    Notes
    -----
    The indicator + transformation pattern is MANDATORY for all signals.
    Signals without this structure will fail validation at registry load time.

    Runtime overrides (via WorkflowConfig):
    - indicator_override: Swap indicator while keeping transformation
    - transformation_override: Swap transformation while keeping indicator
    - security_mapping: Override which securities to load for indicator data requirements
    """

    name: str
    description: str
    indicator_dependencies: list[str]
    transformations: list[str]
    composition_logic: str | None = None
    enabled: bool = True
    sign_multiplier: int = 1

    def __post_init__(self) -> None:
        """Validate signal metadata."""
        # Validate name format
        if not self.name or not re.match(r"^[a-z][a-z0-9_]*$", self.name):
            raise ValueError(
                f"Signal name must be lowercase with underscores, got: {self.name}"
            )

        # Validate description
        if not self.description or len(self.description) < 10:
            raise ValueError(
                f"Signal description must be at least 10 characters, got: {len(self.description)}"
            )

        # Enforce indicator + transformation pattern (REQUIRED)
        if not self.indicator_dependencies:
            raise ValueError(
                f"Signal '{self.name}' requires indicator_dependencies (cannot be empty)"
            )

        if not self.transformations:
            raise ValueError(
                f"Signal '{self.name}' requires transformations (cannot be empty)"
            )

        # Validate sign_multiplier is ±1
        if self.sign_multiplier not in (-1, 1):
            raise ValueError(
                f"sign_multiplier must be -1 or 1, got {self.sign_multiplier}"
            )
