"""
Catalog validation for cross-references and field constraints.

Provides validation functions that check:
- Duplicate names within categories
- Cross-references between signals and transformations
- Field constraint validation (sign_multiplier, sizing_mode, etc.)
- Security references from indicator default_securities
"""

import logging
from typing import Any

from aponyx.catalog.data import CatalogsData, SecuritiesData
from aponyx.catalog.entries import (
    IndicatorTransformationEntry,
    ScoreTransformationEntry,
    SecurityEntry,
    SignalEntry,
    SignalTransformationEntry,
    StrategyEntry,
)
from aponyx.catalog.validation_types import (
    ValidationError,
    ValidationResult,
    ValidationSummary,
    ValidationWarning,
)

logger = logging.getLogger(__name__)


def check_duplicates(
    entries: list[Any],
    category: str,
) -> list[ValidationError]:
    """
    Check for duplicate names within a category.

    Parameters
    ----------
    entries : list[Any]
        List of entries with `name` attribute.
    category : str
        Category name for error messages.

    Returns
    -------
    list[ValidationError]
        List of duplicate name errors.
    """
    errors: list[ValidationError] = []
    seen: dict[str, int] = {}

    for entry in entries:
        name = entry.name
        if name in seen:
            errors.append(
                ValidationError(
                    category=category,
                    entry_name=name,
                    field="name",
                    message=f"Duplicate name: '{name}' appears multiple times",
                    suggestion="Each entry name must be unique within its category",
                )
            )
        else:
            seen[name] = 1

    return errors


def validate_signal_references(
    signals: list[SignalEntry],
    indicator_transformations: list[IndicatorTransformationEntry],
    score_transformations: list[ScoreTransformationEntry],
    signal_transformations: list[SignalTransformationEntry],
) -> list[ValidationError]:
    """
    Validate signal transformation references.

    Checks that each signal references valid:
    - indicator_transformation
    - score_transformation
    - signal_transformation

    Parameters
    ----------
    signals : list[SignalEntry]
        List of signal entries to validate.
    indicator_transformations : list[IndicatorTransformationEntry]
        Available indicator transformations.
    score_transformations : list[ScoreTransformationEntry]
        Available score transformations.
    signal_transformations : list[SignalTransformationEntry]
        Available signal transformations.

    Returns
    -------
    list[ValidationError]
        List of reference errors.
    """
    errors: list[ValidationError] = []

    # Build lookup sets
    indicator_names = {t.name for t in indicator_transformations}
    score_names = {t.name for t in score_transformations}
    signal_transform_names = {t.name for t in signal_transformations}

    for signal in signals:
        # Check indicator_transformation reference
        if signal.indicator_transformation not in indicator_names:
            errors.append(
                ValidationError(
                    category="signals",
                    entry_name=signal.name,
                    field="indicator_transformation",
                    message=f"Unknown indicator_transformation: '{signal.indicator_transformation}'",
                    suggestion=f"Available: {sorted(indicator_names)}",
                )
            )

        # Check score_transformation reference
        if signal.score_transformation not in score_names:
            errors.append(
                ValidationError(
                    category="signals",
                    entry_name=signal.name,
                    field="score_transformation",
                    message=f"Unknown score_transformation: '{signal.score_transformation}'",
                    suggestion=f"Available: {sorted(score_names)}",
                )
            )

        # Check signal_transformation reference
        if signal.signal_transformation not in signal_transform_names:
            errors.append(
                ValidationError(
                    category="signals",
                    entry_name=signal.name,
                    field="signal_transformation",
                    message=f"Unknown signal_transformation: '{signal.signal_transformation}'",
                    suggestion=f"Available: {sorted(signal_transform_names)}",
                )
            )

    return errors


def validate_indicator_securities(
    indicators: list[IndicatorTransformationEntry],
    securities: dict[str, SecurityEntry],
) -> list[ValidationWarning]:
    """
    Validate indicator default_securities references.

    Returns warnings (not errors) for missing securities since
    securities may be dynamically provided at runtime.

    Parameters
    ----------
    indicators : list[IndicatorTransformationEntry]
        List of indicator transformations.
    securities : dict[str, SecurityEntry]
        Available securities keyed by name.

    Returns
    -------
    list[ValidationWarning]
        List of reference warnings.
    """
    warnings: list[ValidationWarning] = []
    security_names = set(securities.keys())

    for indicator in indicators:
        for key, security_name in indicator.default_securities.items():
            if security_name not in security_names:
                warnings.append(
                    ValidationWarning(
                        category="indicator_transformations",
                        entry_name=indicator.name,
                        field=f"default_securities.{key}",
                        message=f"Unknown security: '{security_name}'",
                    )
                )

    return warnings


def validate_field_constraints(
    signals: list[SignalEntry],
    strategies: list[StrategyEntry],
    signal_transformations: list[SignalTransformationEntry],
) -> list[ValidationError]:
    """
    Validate field-level constraints.

    Checks:
    - SignalEntry.sign_multiplier is 1 or -1
    - StrategyEntry.sizing_mode is 'binary' or 'proportional'
    - StrategyEntry.position_size_mm is > 0
    - SignalTransformationEntry.floor <= cap if both set

    Note: Most constraints are already enforced by dataclass __post_init__,
    but we validate here to catch any data loaded from external sources.

    Parameters
    ----------
    signals : list[SignalEntry]
        Signal entries.
    strategies : list[StrategyEntry]
        Strategy entries.
    signal_transformations : list[SignalTransformationEntry]
        Signal transformation entries.

    Returns
    -------
    list[ValidationError]
        List of constraint violation errors.
    """
    errors: list[ValidationError] = []

    # Signal constraints
    for signal in signals:
        if signal.sign_multiplier not in {1, -1}:
            errors.append(
                ValidationError(
                    category="signals",
                    entry_name=signal.name,
                    field="sign_multiplier",
                    message=f"Invalid sign_multiplier: {signal.sign_multiplier}",
                    suggestion="sign_multiplier must be 1 or -1",
                )
            )

    # Strategy constraints
    for strategy in strategies:
        if strategy.sizing_mode not in {"binary", "proportional"}:
            errors.append(
                ValidationError(
                    category="strategies",
                    entry_name=strategy.name,
                    field="sizing_mode",
                    message=f"Invalid sizing_mode: '{strategy.sizing_mode}'",
                    suggestion="sizing_mode must be 'binary' or 'proportional'",
                )
            )

        if strategy.position_size_mm <= 0:
            errors.append(
                ValidationError(
                    category="strategies",
                    entry_name=strategy.name,
                    field="position_size_mm",
                    message=f"Invalid position_size_mm: {strategy.position_size_mm}",
                    suggestion="position_size_mm must be > 0",
                )
            )

    # Signal transformation constraints
    for transform in signal_transformations:
        if transform.floor is not None and transform.cap is not None:
            if transform.floor > transform.cap:
                errors.append(
                    ValidationError(
                        category="signal_transformations",
                        entry_name=transform.name,
                        field="floor/cap",
                        message=f"floor ({transform.floor}) > cap ({transform.cap})",
                        suggestion="floor must be <= cap",
                    )
                )

    return errors


def validate_catalogs(
    catalogs: CatalogsData,
    securities: SecuritiesData,
) -> ValidationResult:
    """
    Validate catalog entries and cross-references.

    Performs all validation checks:
    - Duplicate name detection
    - Signal reference validation
    - Indicator security reference validation (warnings)
    - Field constraint validation

    Parameters
    ----------
    catalogs : CatalogsData
        Loaded catalogs data.
    securities : SecuritiesData
        Loaded securities data.

    Returns
    -------
    ValidationResult
        Validation result with errors, warnings, and summary.
    """
    errors: list[ValidationError] = []
    warnings: list[ValidationWarning] = []

    # Check for duplicates in each category
    errors.extend(
        check_duplicates(
            catalogs.indicator_transformations, "indicator_transformations"
        )
    )
    errors.extend(
        check_duplicates(catalogs.score_transformations, "score_transformations")
    )
    errors.extend(
        check_duplicates(catalogs.signal_transformations, "signal_transformations")
    )
    errors.extend(check_duplicates(catalogs.signals, "signals"))
    errors.extend(check_duplicates(catalogs.strategies, "strategies"))

    # Check duplicates in securities (convert dict values to list)
    securities_list = [
        type("Entry", (), {"name": name})() for name in securities.securities.keys()
    ]
    errors.extend(check_duplicates(securities_list, "securities"))

    instruments_list = [
        type("Entry", (), {"name": name})() for name in securities.instruments.keys()
    ]
    errors.extend(check_duplicates(instruments_list, "instruments"))

    # Validate signal references
    errors.extend(
        validate_signal_references(
            signals=catalogs.signals,
            indicator_transformations=catalogs.indicator_transformations,
            score_transformations=catalogs.score_transformations,
            signal_transformations=catalogs.signal_transformations,
        )
    )

    # Validate indicator securities (warnings only)
    warnings.extend(
        validate_indicator_securities(
            indicators=catalogs.indicator_transformations,
            securities=securities.securities,
        )
    )

    # Validate field constraints
    errors.extend(
        validate_field_constraints(
            signals=catalogs.signals,
            strategies=catalogs.strategies,
            signal_transformations=catalogs.signal_transformations,
        )
    )

    # Build summary
    summary = ValidationSummary(
        total_entries=(
            len(catalogs.indicator_transformations)
            + len(catalogs.score_transformations)
            + len(catalogs.signal_transformations)
            + len(catalogs.signals)
            + len(catalogs.strategies)
            + len(securities.securities)
            + len(securities.instruments)
        ),
        indicator_transformations=len(catalogs.indicator_transformations),
        score_transformations=len(catalogs.score_transformations),
        signal_transformations=len(catalogs.signal_transformations),
        signals=len(catalogs.signals),
        strategies=len(catalogs.strategies),
        securities=len(securities.securities),
        instruments=len(securities.instruments),
    )

    passed = len(errors) == 0

    if passed:
        logger.info("Validation passed: %d entries validated", summary.total_entries)
    else:
        logger.warning("Validation failed: %d error(s)", len(errors))

    return ValidationResult(
        passed=passed,
        errors=tuple(errors),
        warnings=tuple(warnings),
        summary=summary,
    )
