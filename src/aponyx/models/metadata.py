"""
Signal metadata dataclass for catalog management.

This module defines the metadata structure for signal definitions stored
in the signal catalog JSON file.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SignalMetadata:
    """
    Metadata for a registered signal computation.

    Attributes
    ----------
    name : str
        Unique signal identifier (e.g., "cdx_etf_basis").
    description : str
        Human-readable description of signal purpose and logic.
    compute_function_name : str
        Name of the compute function in signals module (e.g., "compute_cdx_etf_basis").
    data_requirements : dict[str, str]
        Mapping from market data keys to required column names.
        Example: {"cdx": "spread", "etf": "spread"}

        The keys define what DataFrames must be present in the market_data dict
        when calling compute_registered_signals(). The values specify which
        columns must exist in those DataFrames.
    arg_mapping : list[str]
        Ordered list of data keys to pass as positional arguments to compute function.
        Example: ["cdx", "etf"] means call compute_fn(market_data["cdx"], market_data["etf"], config)

        Design Note: Uses positional arguments for simplicity in pilot phase.
        Alternative keyword-based approach considered but rejected to avoid
        complexity. Must contain exactly the same keys as data_requirements.
    enabled : bool
        Whether signal should be included in computation.
    sign_multiplier : int
        Multiplier to apply to signal output for sign correction.
        Use -1 to invert signals with negative Sharpe ratios.
        Default is 1 (no inversion).

    Notes
    -----
    The data_requirements and arg_mapping pattern enables catalog-driven computation:
    - Different signals can require different data combinations
    - Catalog defines requirements declaratively in JSON
    - Orchestrator resolves data dynamically from market_data dict

    This adds a layer of indirection but provides flexibility to add new signals
    without changing the orchestration code.
    """

    name: str
    description: str
    compute_function_name: str
    data_requirements: dict[str, str]
    arg_mapping: list[str]
    enabled: bool = True
    sign_multiplier: int = 1

    def __post_init__(self) -> None:
        """Validate signal metadata."""
        if not self.name:
            raise ValueError("Signal name cannot be empty")
        if not self.compute_function_name:
            raise ValueError("Compute function name cannot be empty")
        if not self.arg_mapping:
            raise ValueError("arg_mapping cannot be empty")

        # Validate arg_mapping contains exactly the same keys as data_requirements
        arg_set = set(self.arg_mapping)
        req_set = set(self.data_requirements.keys())
        if arg_set != req_set:
            raise ValueError(
                f"arg_mapping {self.arg_mapping} must contain exactly the same keys "
                f"as data_requirements {list(self.data_requirements.keys())}. "
                f"Missing: {req_set - arg_set}, Extra: {arg_set - req_set}"
            )

        # Validate sign_multiplier is ±1
        if self.sign_multiplier not in (-1, 1):
            raise ValueError(f"sign_multiplier must be -1 or 1, got {self.sign_multiplier}")
