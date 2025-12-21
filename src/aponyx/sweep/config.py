"""
Configuration dataclasses and utilities for parameter sweeps.

Provides frozen dataclasses for sweep configuration with validation,
YAML parsing, and parameter path validation.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

logger = logging.getLogger(__name__)

# Valid parameter path prefixes for validation
VALID_PATH_PREFIXES: tuple[str, ...] = (
    "indicator_transformation.parameters.",
    "score_transformation.parameters.",
    "signal_transformation.parameters.",
    "strategy.",
)


@dataclass(frozen=True)
class ParameterOverride:
    """
    Single parameter path with values to sweep.

    Attributes
    ----------
    path : str
        Dot notation path to parameter (e.g., "indicator_transformation.parameters.lookback").
    values : tuple[float | int | str, ...]
        Values to test (immutable tuple for frozen dataclass).

    Raises
    ------
    ValueError
        If path is empty or values is empty.

    Examples
    --------
    >>> override = ParameterOverride(
    ...     path="indicator_transformation.parameters.lookback",
    ...     values=(10, 20, 40),
    ... )
    """

    path: str
    values: tuple[float | int | str, ...]

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("path cannot be empty")
        if not self.values:
            raise ValueError("values cannot be empty")


@dataclass(frozen=True)
class BaseConfig:
    """
    Base configuration references for sweep.

    Attributes
    ----------
    signal : str
        Signal name from signal catalog.
    strategy : str | None
        Strategy name from strategy catalog (required for backtest mode).
    data_source : str
        Data source type ("synthetic", "bloomberg", or custom sources).

    Raises
    ------
    ValueError
        If signal is empty.

    Examples
    --------
    >>> base = BaseConfig(signal="cdx_etf_basis", strategy="balanced")
    >>> base = BaseConfig(signal="cdx_etf_basis", strategy="balanced", data_source="bloomberg")
    """

    signal: str
    strategy: str | None = None
    data_source: str = "synthetic"

    def __post_init__(self) -> None:
        if not self.signal:
            raise ValueError("signal cannot be empty")


@dataclass(frozen=True)
class SweepConfig:
    """
    Complete sweep experiment configuration.

    Attributes
    ----------
    name : str
        Sweep experiment identifier (used in output directory name).
    description : str
        Human-readable description of the experiment.
    mode : Literal["indicator", "backtest"]
        Evaluation mode.
    base : BaseConfig
        Base configuration references.
    parameters : tuple[ParameterOverride, ...]
        Parameter overrides to sweep (immutable tuple).
    max_combinations : int | None
        Maximum combinations to test (None = unlimited).

    Raises
    ------
    ValueError
        If validation fails (empty name, invalid mode, missing strategy for backtest, etc.).

    Examples
    --------
    >>> config = SweepConfig(
    ...     name="lookback_sweep",
    ...     description="Test lookback window impact",
    ...     mode="indicator",
    ...     base=BaseConfig(signal="cdx_etf_basis"),
    ...     parameters=(
    ...         ParameterOverride(
    ...             path="indicator_transformation.parameters.lookback",
    ...             values=(10, 20, 40),
    ...         ),
    ...     ),
    ... )
    """

    name: str
    description: str
    mode: Literal["indicator", "backtest"]
    base: BaseConfig
    parameters: tuple[ParameterOverride, ...]
    max_combinations: int | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name cannot be empty")
        if self.mode not in ("indicator", "backtest"):
            raise ValueError(
                f"mode must be 'indicator' or 'backtest', got '{self.mode}'"
            )
        if self.mode == "backtest" and self.base.strategy is None:
            raise ValueError("strategy required for backtest mode")
        if not self.parameters:
            raise ValueError("at least one parameter override required")
        if self.max_combinations is not None and self.max_combinations < 1:
            raise ValueError("max_combinations must be positive")


def validate_parameter_path(path: str, mode: str) -> None:
    """
    Validate a parameter override path against known patterns.

    Parameters
    ----------
    path : str
        Dot notation parameter path to validate.
    mode : str
        Sweep mode ("indicator" or "backtest").

    Raises
    ------
    ValueError
        If path doesn't match any valid pattern or strategy path used in indicator mode.

    Examples
    --------
    >>> validate_parameter_path("indicator_transformation.parameters.lookback", "indicator")
    >>> validate_parameter_path("strategy.stop_loss_pct", "backtest")
    >>> validate_parameter_path("strategy.stop_loss_pct", "indicator")
    ValueError: Strategy parameters only valid in backtest mode
    """
    if not any(path.startswith(prefix) for prefix in VALID_PATH_PREFIXES):
        raise ValueError(
            f"Invalid parameter path: '{path}'. "
            f"Path must start with one of: {', '.join(VALID_PATH_PREFIXES)}"
        )

    if path.startswith("strategy.") and mode != "backtest":
        raise ValueError("Strategy parameters only valid in backtest mode")


def validate_parameter_types(parameters: tuple[ParameterOverride, ...]) -> None:
    """
    Validate that parameter values have consistent types.

    Parameters
    ----------
    parameters : tuple[ParameterOverride, ...]
        Parameter overrides to validate.

    Raises
    ------
    ValueError
        If values within a parameter have inconsistent types.

    Examples
    --------
    >>> params = (ParameterOverride(path="a.b.c", values=(10, 20, 30)),)
    >>> validate_parameter_types(params)  # OK

    >>> params = (ParameterOverride(path="a.b.c", values=(10, "invalid", 30)),)
    >>> validate_parameter_types(params)
    ValueError: Inconsistent types in parameter 'a.b.c': found int, str
    """
    for param in parameters:
        types_found = set(type(v).__name__ for v in param.values)
        # Allow int and float to be mixed (common case for numeric parameters)
        numeric_types = {"int", "float"}
        if types_found <= numeric_types:
            continue
        if len(types_found) > 1:
            raise ValueError(
                f"Inconsistent types in parameter '{param.path}': "
                f"found {', '.join(sorted(types_found))}"
            )


def load_sweep_config(config_path: str | Path) -> SweepConfig:
    """
    Load and parse a sweep configuration from YAML file.

    Parameters
    ----------
    config_path : str | Path
        Path to YAML configuration file.

    Returns
    -------
    SweepConfig
        Parsed and validated sweep configuration.

    Raises
    ------
    FileNotFoundError
        If config file doesn't exist.
    ValueError
        If YAML is invalid or missing required fields.

    Examples
    --------
    >>> config = load_sweep_config("examples/sweep_lookback.yaml")
    >>> print(f"Sweep: {config.name}, mode: {config.mode}")
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Sweep config not found: {config_path}")

    logger.info("Loading sweep config from: %s", config_path)

    with open(config_path, "r", encoding="utf-8") as f:
        raw_config: dict[str, Any] = yaml.safe_load(f) or {}

    # Validate required fields
    required_fields = ["name", "description", "mode", "base", "parameters"]
    missing = [f for f in required_fields if f not in raw_config]
    if missing:
        raise ValueError(
            f"Missing required field(s) in sweep config: {', '.join(missing)}"
        )

    # Parse base config
    base_dict = raw_config["base"]
    if "signal" not in base_dict:
        raise ValueError("base.signal is required")

    base = BaseConfig(
        signal=base_dict["signal"],
        strategy=base_dict.get("strategy"),
        data_source=base_dict.get("data_source", "synthetic"),
    )

    # Parse parameters
    param_list = raw_config["parameters"]
    if not isinstance(param_list, list) or len(param_list) == 0:
        raise ValueError("parameters must be a non-empty list")

    parameters: list[ParameterOverride] = []
    for i, param_dict in enumerate(param_list):
        if "path" not in param_dict:
            raise ValueError(f"parameters[{i}].path is required")
        if "values" not in param_dict:
            raise ValueError(f"parameters[{i}].values is required")

        values_raw = param_dict["values"]
        if not isinstance(values_raw, list) or len(values_raw) == 0:
            raise ValueError(f"parameters[{i}].values must be a non-empty list")

        parameters.append(
            ParameterOverride(
                path=param_dict["path"],
                values=tuple(values_raw),
            )
        )

    # Create config
    mode = raw_config["mode"]
    config = SweepConfig(
        name=raw_config["name"],
        description=raw_config["description"],
        mode=mode,
        base=base,
        parameters=tuple(parameters),
        max_combinations=raw_config.get("max_combinations"),
    )

    # Validate parameter paths
    for param in config.parameters:
        validate_parameter_path(param.path, mode)

    # Validate parameter types
    validate_parameter_types(config.parameters)

    logger.info(
        "Loaded sweep config: name=%s, mode=%s, parameters=%d",
        config.name,
        config.mode,
        len(config.parameters),
    )

    return config
