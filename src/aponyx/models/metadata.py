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


class CatalogValidationError(ValueError):
    """
    Validation error with structured information for catalog entries.

    Attributes
    ----------
    catalog : str
        Name of the catalog file (e.g., "signal_transformation.json")
    entry : str
        Name of the entry being validated
    field : str
        Field that failed validation
    value : Any
        Invalid value provided
    constraint : str
        Description of the constraint that was violated
    suggestion : str
        Suggested fix for the validation error
    """

    def __init__(
        self,
        catalog: str,
        entry: str,
        field: str,
        value: Any,
        constraint: str,
        suggestion: str,
    ):
        self.catalog = catalog
        self.entry = entry
        self.field = field
        self.value = value
        self.constraint = constraint
        self.suggestion = suggestion

        message = (
            f"Validation failed in {catalog} entry '{entry}': "
            f"field '{field}' has value '{value}'. "
            f"Constraint: {constraint}. "
            f"Suggestion: {suggestion}"
        )
        super().__init__(message)


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
class SignalTransformationMetadata:
    """
    Metadata for signal transformation stage.

    Applies trading rules to convert scores into bounded trading signals.
    Operations applied in order: scale → floor/cap → neutral_range.

    Attributes
    ----------
    name : str
        Unique identifier (lowercase with underscores).
        Example: "bounded_1_5", "passthrough"
    description : str
        Human-readable explanation of transformation behavior.
        Minimum 10 characters.
    scaling : float
        Multiplier applied first to the score.
        Must be non-zero.
        Default: 1.0
    floor : float | None
        Lower bound after scaling.
        None = no lower bound (-inf).
        Must be <= cap (if both specified).
        Default: None
    cap : float | None
        Upper bound after scaling.
        None = no upper bound (+inf).
        Must be >= floor (if both specified).
        Default: None
    neutral_range : tuple[float, float] | None
        Values within [low, high] set to zero.
        None = no neutral zone.
        Must satisfy neutral_range[0] <= neutral_range[1].
        Default: None
    enabled : bool
        Whether transformation is available for use.
        Default: True
    """

    name: str
    description: str
    scaling: float = 1.0
    floor: float | None = None
    cap: float | None = None
    neutral_range: tuple[float, float] | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate signal transformation metadata."""
        # Validate name format
        if not self.name or not re.match(r"^[a-z][a-z0-9_]*$", self.name):
            raise CatalogValidationError(
                catalog="signal_transformation.json",
                entry=self.name,
                field="name",
                value=self.name,
                constraint="Name must be lowercase with underscores only (^[a-z][a-z0-9_]*$)",
                suggestion="Use lowercase letters, numbers, and underscores only",
            )

        # Validate description
        if not self.description or len(self.description) < 10:
            raise CatalogValidationError(
                catalog="signal_transformation.json",
                entry=self.name,
                field="description",
                value=self.description,
                constraint="Description must be at least 10 characters",
                suggestion="Provide a clear description of the transformation behavior",
            )

        # Validate scaling is non-zero
        if self.scaling == 0.0:
            raise CatalogValidationError(
                catalog="signal_transformation.json",
                entry=self.name,
                field="scaling",
                value=self.scaling,
                constraint="Scaling must be non-zero",
                suggestion="Use scaling != 0.0 (typically 1.0 for no scaling)",
            )

        # Validate floor <= cap (if both specified)
        if self.floor is not None and self.cap is not None and self.floor > self.cap:
            raise CatalogValidationError(
                catalog="signal_transformation.json",
                entry=self.name,
                field="floor",
                value=self.floor,
                constraint=f"floor must be <= cap ({self.cap})",
                suggestion=f"Set floor <= {self.cap} or cap >= {self.floor}",
            )

        # Validate neutral_range[0] <= neutral_range[1]
        if self.neutral_range is not None:
            if len(self.neutral_range) != 2:
                raise CatalogValidationError(
                    catalog="signal_transformation.json",
                    entry=self.name,
                    field="neutral_range",
                    value=self.neutral_range,
                    constraint="neutral_range must be a tuple of exactly 2 floats",
                    suggestion="Use [low, high] format, e.g., [-0.25, 0.25]",
                )
            low, high = self.neutral_range
            if low > high:
                raise CatalogValidationError(
                    catalog="signal_transformation.json",
                    entry=self.name,
                    field="neutral_range",
                    value=self.neutral_range,
                    constraint=f"neutral_range[0] ({low}) must be <= neutral_range[1] ({high})",
                    suggestion=f"Use [{high}, {low}] or swap the values",
                )


@dataclass(frozen=True)
class SignalMetadata:
    """
    Metadata for a registered signal computation.

    FOUR-STAGE TRANSFORMATION PIPELINE
    -----------------------------------
    Security → Indicator → Score → Signal → Position

    Each signal references exactly one transformation from each stage (1:1:1 relationship):
    1. Indicator Transformation - Computes economic metric from securities (e.g., spread difference in bps)
    2. Score Transformation - Normalizes indicator to common scale (e.g., z-score)
    3. Signal Transformation - Applies trading rules (floor, cap, neutral_range, scaling)

    This structure enables:
    - Clear separation of economic logic, normalization, and trading rules
    - Independent inspection of each transformation stage for debugging
    - Runtime overrides at any stage without recomputing upstream stages (caching efficiency)
    - Explicit specification of all transformation parameters in catalog

    EXAMPLE: cdx_etf_basis signal
    - Indicator: "cdx_etf_spread_diff" (basis in raw bps)
    - Score: "z_score_20d" (normalize to dimensionless score)
    - Signal: "passthrough" (no additional trading rules)
    - Result: Tradeable signal with positive = long credit risk

    Attributes
    ----------
    name : str
        Unique signal identifier (lowercase with underscores).
        Example: "cdx_etf_basis", "spread_momentum"
    description : str
        Human-readable description of signal purpose and logic.
        Minimum 10 characters.
    indicator_transformation : str
        Reference to indicator_transformation.json entry (REQUIRED).
        Must exist in IndicatorTransformationRegistry.
        Example: "cdx_etf_spread_diff"
    score_transformation : str
        Reference to score_transformation.json entry (REQUIRED).
        Must exist in ScoreTransformationRegistry.
        Example: "z_score_20d"
    signal_transformation : str
        Reference to signal_transformation.json entry (REQUIRED).
        Must exist in SignalTransformationRegistry.
        Example: "passthrough", "bounded_1_5"
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
    All three transformation references are MANDATORY (no defaults).
    Signals must explicitly specify all stages of the transformation pipeline.

    Runtime overrides (via WorkflowConfig):
    - indicator_transformation_override: Swap indicator while keeping score/signal transformations
    - score_transformation_override: Swap score transformation while keeping indicator/signal
    - signal_transformation_override: Swap signal transformation while keeping indicator/score
    - security_mapping: Override which securities to load for indicator data requirements
    """

    name: str
    description: str
    indicator_transformation: str
    score_transformation: str
    signal_transformation: str
    enabled: bool = True
    sign_multiplier: int = 1

    def __post_init__(self) -> None:
        """Validate signal metadata."""
        # Validate name format
        if not self.name or not re.match(r"^[a-z][a-z0-9_]*$", self.name):
            raise CatalogValidationError(
                catalog="signal_catalog.json",
                entry=self.name,
                field="name",
                value=self.name,
                constraint="Name must be lowercase with underscores only (^[a-z][a-z0-9_]*$)",
                suggestion="Use lowercase letters, numbers, and underscores only",
            )

        # Validate description
        if not self.description or len(self.description) < 10:
            raise CatalogValidationError(
                catalog="signal_catalog.json",
                entry=self.name,
                field="description",
                value=self.description,
                constraint="Description must be at least 10 characters",
                suggestion="Provide a clear description of signal purpose and logic",
            )

        # Enforce explicit transformation references (REQUIRED, no defaults)
        if not self.indicator_transformation:
            raise CatalogValidationError(
                catalog="signal_catalog.json",
                entry=self.name,
                field="indicator_transformation",
                value=self.indicator_transformation,
                constraint="indicator_transformation is required (cannot be empty)",
                suggestion="Specify an indicator from indicator_transformation.json",
            )

        if not self.score_transformation:
            raise CatalogValidationError(
                catalog="signal_catalog.json",
                entry=self.name,
                field="score_transformation",
                value=self.score_transformation,
                constraint="score_transformation is required (cannot be empty)",
                suggestion="Specify a transformation from score_transformation.json",
            )

        if not self.signal_transformation:
            raise CatalogValidationError(
                catalog="signal_catalog.json",
                entry=self.name,
                field="signal_transformation",
                value=self.signal_transformation,
                constraint="signal_transformation is required (cannot be empty)",
                suggestion="Specify a transformation from signal_transformation.json (e.g., 'passthrough')",
            )

        # Validate sign_multiplier is ±1
        if self.sign_multiplier not in (-1, 1):
            raise CatalogValidationError(
                catalog="signal_catalog.json",
                entry=self.name,
                field="sign_multiplier",
                value=self.sign_multiplier,
                constraint="sign_multiplier must be -1 or 1",
                suggestion="Use 1 (no inversion) or -1 (invert sign)",
            )
