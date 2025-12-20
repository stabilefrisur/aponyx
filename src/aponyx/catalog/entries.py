"""
Entry dataclasses for catalog items.

Defines frozen dataclasses for all catalog entry types:
- IndicatorTransformationEntry
- ScoreTransformationEntry
- SignalTransformationEntry
- SignalEntry
- StrategyEntry
- SecurityEntry
- ChannelConfig
- InstrumentEntry

All entries use frozen=True for immutability and include __post_init__
validation to fail fast on invalid data.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IndicatorTransformationEntry:
    """
    Indicator transformation definition.

    Maps to a single entry in indicator_transformation.json.

    Attributes
    ----------
    name : str
        Unique identifier for this transformation.
    description : str
        Human-readable description.
    compute_function_name : str
        Name of the Python function implementing this transformation.
    data_requirements : dict[str, str]
        Mapping of input name to required data channel.
    default_securities : dict[str, str]
        Mapping of input name to default security.
    output_units : str
        Unit of output values (e.g., "basis_points").
    parameters : dict[str, Any]
        Additional parameters for the compute function.
    enabled : bool
        Whether this transformation is active.
    """

    name: str
    description: str
    compute_function_name: str
    data_requirements: dict[str, str]
    default_securities: dict[str, str]
    output_units: str
    parameters: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate entry constraints."""
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.compute_function_name:
            raise ValueError("compute_function_name cannot be empty")
        if not self.data_requirements:
            raise ValueError("data_requirements cannot be empty")
        if not self.default_securities:
            raise ValueError("default_securities cannot be empty")


@dataclass(frozen=True)
class ScoreTransformationEntry:
    """
    Score transformation definition.

    Maps to a single entry in score_transformation.json.

    Attributes
    ----------
    name : str
        Unique identifier for this transformation.
    description : str
        Human-readable description.
    transform_type : str
        Type of transformation (e.g., "z_score", "normalized_change").
    parameters : dict[str, Any]
        Parameters for the transformation.
    enabled : bool
        Whether this transformation is active.
    """

    name: str
    description: str
    transform_type: str
    parameters: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate entry constraints."""
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.transform_type:
            raise ValueError("transform_type cannot be empty")


@dataclass(frozen=True)
class SignalTransformationEntry:
    """
    Signal transformation definition.

    Maps to a single entry in signal_transformation.json.

    Attributes
    ----------
    name : str
        Unique identifier for this transformation.
    description : str
        Human-readable description.
    scaling : float
        Scaling factor applied to signal.
    floor : float | None
        Minimum signal value (None for unbounded).
    cap : float | None
        Maximum signal value (None for unbounded).
    neutral_range : tuple[float, float] | None
        Range considered neutral (e.g., (-0.25, 0.25)).
    enabled : bool
        Whether this transformation is active.
    """

    name: str
    description: str
    scaling: float = 1.0
    floor: float | None = None
    cap: float | None = None
    neutral_range: tuple[float, float] | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate entry constraints."""
        if not self.name:
            raise ValueError("name cannot be empty")
        if self.floor is not None and self.cap is not None:
            if self.floor > self.cap:
                raise ValueError(f"floor ({self.floor}) cannot exceed cap ({self.cap})")
        if self.neutral_range is not None:
            if len(self.neutral_range) != 2:
                raise ValueError("neutral_range must have exactly 2 elements")
            if self.neutral_range[0] > self.neutral_range[1]:
                raise ValueError(
                    f"neutral_range[0] ({self.neutral_range[0]}) cannot exceed "
                    f"neutral_range[1] ({self.neutral_range[1]})"
                )


@dataclass(frozen=True)
class SignalEntry:
    """
    Signal definition.

    Maps to a single entry in signal_catalog.json.

    Attributes
    ----------
    name : str
        Unique identifier for this signal.
    description : str
        Human-readable description.
    indicator_transformation : str
        Reference to IndicatorTransformationEntry.name.
    score_transformation : str
        Reference to ScoreTransformationEntry.name.
    signal_transformation : str
        Reference to SignalTransformationEntry.name.
    sign_multiplier : int
        Signal sign adjustment (1 or -1).
    enabled : bool
        Whether this signal is active.
    """

    name: str
    description: str
    indicator_transformation: str
    score_transformation: str
    signal_transformation: str
    sign_multiplier: int = 1
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate entry constraints."""
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.indicator_transformation:
            raise ValueError("indicator_transformation cannot be empty")
        if not self.score_transformation:
            raise ValueError("score_transformation cannot be empty")
        if not self.signal_transformation:
            raise ValueError("signal_transformation cannot be empty")
        if self.sign_multiplier not in {1, -1}:
            raise ValueError(
                f"sign_multiplier must be 1 or -1, got {self.sign_multiplier}"
            )


@dataclass(frozen=True)
class StrategyEntry:
    """
    Strategy definition.

    Maps to a single entry in strategy_catalog.json.

    Attributes
    ----------
    name : str
        Unique identifier for this strategy.
    description : str
        Human-readable description.
    position_size_mm : float
        Position size in millions.
    sizing_mode : str
        Sizing mode ("binary" or "proportional").
    stop_loss_pct : float | None
        Stop loss percentage.
    take_profit_pct : float | None
        Take profit percentage.
    max_holding_days : int | None
        Maximum holding period.
    entry_threshold : float | None
        Signal threshold for entry.
    enabled : bool
        Whether this strategy is active.
    """

    name: str
    description: str
    position_size_mm: float = 10.0
    sizing_mode: str = "proportional"
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    max_holding_days: int | None = None
    entry_threshold: float | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate entry constraints."""
        if not self.name:
            raise ValueError("name cannot be empty")
        if self.position_size_mm <= 0:
            raise ValueError("position_size_mm must be positive")
        if self.sizing_mode not in {"binary", "proportional"}:
            raise ValueError("sizing_mode must be 'binary' or 'proportional'")
        if self.stop_loss_pct is not None and not (0 < self.stop_loss_pct <= 100):
            raise ValueError("stop_loss_pct must be in (0, 100]")
        if self.take_profit_pct is not None and not (0 < self.take_profit_pct <= 100):
            raise ValueError("take_profit_pct must be in (0, 100]")


@dataclass(frozen=True)
class ChannelConfig:
    """
    Channel configuration for a security.

    Maps to a single channel entry in bloomberg_securities.json.

    Attributes
    ----------
    bloomberg_ticker : str
        Bloomberg ticker symbol.
    field : str
        Bloomberg field name (e.g., "PX_LAST", "YAS_ISPREAD").
    column : str | None
        Output column name (optional, used for display/documentation).
    validation : dict[str, float] | None
        Validation constraints (e.g., {"min": 0, "max": 10000}).
    """

    bloomberg_ticker: str
    field: str
    column: str | None = None
    validation: dict[str, float] | None = None

    def __post_init__(self) -> None:
        """Validate entry constraints."""
        if not self.bloomberg_ticker:
            raise ValueError("bloomberg_ticker cannot be empty")
        if not self.field:
            raise ValueError("field cannot be empty")


@dataclass(frozen=True)
class SecurityEntry:
    """
    Security definition.

    Maps to a single entry in bloomberg_securities.json.

    Attributes
    ----------
    name : str
        Unique identifier for this security (key in YAML).
    description : str
        Human-readable description.
    instrument_type : str
        Type of instrument (e.g., "cdx", "etf", "vix").
    quote_type : str
        Primary quote type ("spread" or "price").
    channels : dict[str, ChannelConfig]
        Available data channels and their configurations.
    dv01_per_million : float | None
        DV01 per million notional.
    transaction_cost_bps : float | None
        Transaction cost in basis points.
    """

    name: str
    description: str
    instrument_type: str
    quote_type: str
    channels: dict[str, ChannelConfig]
    dv01_per_million: float | None = None
    transaction_cost_bps: float | None = None

    def __post_init__(self) -> None:
        """Validate entry constraints."""
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.instrument_type:
            raise ValueError("instrument_type cannot be empty")
        if not self.quote_type:
            raise ValueError("quote_type cannot be empty")
        if not self.channels:
            raise ValueError("channels cannot be empty")


@dataclass(frozen=True)
class InstrumentEntry:
    """
    Instrument type configuration.

    Maps to a single entry in bloomberg_instruments.json.

    Attributes
    ----------
    name : str
        Unique identifier for this instrument type (key in YAML).
    description : str
        Human-readable description.
    bloomberg_fields : list[str]
        List of Bloomberg fields to fetch.
    field_mapping : dict[str, str]
        Mapping from Bloomberg field to output column.
    requires_security_metadata : bool
        Whether security-level metadata is required.
    """

    name: str
    description: str
    bloomberg_fields: tuple[str, ...]
    field_mapping: dict[str, str]
    requires_security_metadata: bool = True

    def __post_init__(self) -> None:
        """Validate entry constraints."""
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.bloomberg_fields:
            raise ValueError("bloomberg_fields cannot be empty")
        if not self.field_mapping:
            raise ValueError("field_mapping cannot be empty")
