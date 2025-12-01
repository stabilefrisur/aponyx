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

    Signals are trading signals derived from one or more indicators via transformations.
    Supports both legacy pattern (compute_function_name) and new composition pattern
    (indicator_dependencies + transformations).

    Attributes
    ----------
    name : str
        Unique signal identifier (e.g., "cdx_etf_basis").
    description : str
        Human-readable description of signal purpose and logic.

    # New composition pattern fields
    indicator_dependencies : list[str] | None
        List of indicator names required for this signal.
        Example: ["cdx_etf_spread_diff"]
    transformations : list[str] | None
        List of transformation names to apply to indicators.
        Example: ["z_score_20d"]
    composition_logic : str | None
        Optional Python expression for combining multiple indicators.
        Example: "cdx_spread / etf_spread"

    # Legacy pattern fields (deprecated)
    compute_function_name : str | None
        Name of the compute function in signals module (DEPRECATED).
        Maintained for backward compatibility only.
    data_requirements : dict[str, str] | None
        Mapping from market data keys to required column names (DEPRECATED).
        Moved to indicators in new pattern.
    arg_mapping : list[str] | None
        Ordered list of data keys to pass as positional arguments (DEPRECATED).
        Moved to indicators in new pattern.
    default_securities : dict[str, str] | None
        Default security IDs to use for each instrument type (DEPRECATED).
        Moved to indicators in new pattern.

    # Common fields
    enabled : bool
        Whether signal should be included in computation.
    sign_multiplier : int
        Multiplier to apply to signal output for sign correction.
        Use -1 to invert signals with negative Sharpe ratios.
        Default is 1 (no inversion).

    Notes
    -----
    Migration Strategy:
    - Legacy signals have compute_function_name (facade pattern)
    - New signals have indicator_dependencies + transformations (composition)
    - Both patterns coexist during migration period
    """

    name: str
    description: str

    # New composition pattern (preferred)
    indicator_dependencies: list[str] | None = None
    transformations: list[str] | None = None
    composition_logic: str | None = None

    # Legacy pattern (deprecated, for backward compatibility)
    compute_function_name: str | None = None
    data_requirements: dict[str, str] | None = None
    arg_mapping: list[str] | None = None
    default_securities: dict[str, str] | None = None

    enabled: bool = True
    sign_multiplier: int = 1

    def __post_init__(self) -> None:
        """Validate signal metadata."""
        if not self.name:
            raise ValueError("Signal name cannot be empty")

        # Either legacy or new pattern required
        has_legacy = self.compute_function_name is not None
        has_new = self.indicator_dependencies is not None

        if not has_legacy and not has_new:
            raise ValueError(
                f"Signal {self.name} must specify either compute_function_name (legacy) "
                "or indicator_dependencies (new pattern)"
            )

        # Validate legacy pattern if used
        if has_legacy:
            if not self.arg_mapping:
                raise ValueError(f"Legacy signal {self.name} requires arg_mapping")

            # Validate arg_mapping matches data_requirements
            if self.data_requirements:
                arg_set = set(self.arg_mapping)
                req_set = set(self.data_requirements.keys())
                if arg_set != req_set:
                    raise ValueError(
                        f"arg_mapping {self.arg_mapping} must match "
                        f"data_requirements {list(self.data_requirements.keys())}"
                    )

        # Validate new pattern if used
        if has_new:
            if not self.indicator_dependencies:
                raise ValueError(
                    f"New pattern signal {self.name} requires indicator_dependencies"
                )

        # Validate sign_multiplier is ±1
        if self.sign_multiplier not in (-1, 1):
            raise ValueError(
                f"sign_multiplier must be -1 or 1, got {self.sign_multiplier}"
            )
