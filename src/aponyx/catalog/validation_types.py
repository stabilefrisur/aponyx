"""
Validation result types for catalog validation.

Defines dataclasses for validation results, errors, warnings, and summaries.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ValidationError:
    """
    A validation error that blocks sync.

    Attributes
    ----------
    category : str
        Category where error occurred (e.g., "signals").
    entry_name : str
        Name of entry with error.
    field : str
        Field name that failed validation.
    message : str
        Human-readable error description.
    suggestion : str | None
        Optional suggestion for fixing the error.
    line_number : int | None
        Line number in YAML file (if available).
    """

    category: str
    entry_name: str
    field: str
    message: str
    suggestion: str | None = None
    line_number: int | None = None

    def __str__(self) -> str:
        """Format error for display."""
        location = f" (line {self.line_number})" if self.line_number else ""
        base = f"[{self.category}] {self.entry_name}.{self.field}: {self.message}{location}"
        if self.suggestion:
            return f"{base}\n  Suggestion: {self.suggestion}"
        return base


@dataclass(frozen=True)
class ValidationWarning:
    """
    A validation warning (non-blocking).

    Attributes
    ----------
    category : str
        Category where warning occurred.
    entry_name : str
        Name of entry with warning.
    field : str
        Field name that triggered warning.
    message : str
        Human-readable warning description.
    """

    category: str
    entry_name: str
    field: str
    message: str

    def __str__(self) -> str:
        """Format warning for display."""
        return f"[{self.category}] {self.entry_name}.{self.field}: {self.message}"


@dataclass(frozen=True)
class ValidationSummary:
    """
    Statistics about validated entries.

    Attributes
    ----------
    total_entries : int
        Total number of entries validated.
    indicator_transformations : int
        Number of indicator transformations.
    score_transformations : int
        Number of score transformations.
    signal_transformations : int
        Number of signal transformations.
    signals : int
        Number of signals.
    strategies : int
        Number of strategies.
    securities : int
        Number of securities.
    instruments : int
        Number of instruments.
    """

    total_entries: int
    indicator_transformations: int
    score_transformations: int
    signal_transformations: int
    signals: int
    strategies: int
    securities: int
    instruments: int


@dataclass(frozen=True)
class ValidationResult:
    """
    Result of catalog validation.

    Attributes
    ----------
    passed : bool
        True if no errors found.
    errors : list[ValidationError]
        List of validation errors (block sync).
    warnings : list[ValidationWarning]
        List of validation warnings (informational).
    summary : ValidationSummary
        Statistics about validated entries.
    """

    passed: bool
    errors: tuple[ValidationError, ...] = field(default_factory=tuple)
    warnings: tuple[ValidationWarning, ...] = field(default_factory=tuple)
    summary: ValidationSummary | None = None

    def __str__(self) -> str:
        """Format result for display."""
        if self.passed:
            total = self.summary.total_entries if self.summary else 0
            return f"Validation passed: {total} entries validated"

        error_str = "\n".join(str(e) for e in self.errors)
        warning_str = "\n".join(str(w) for w in self.warnings) if self.warnings else ""

        parts = [f"Validation failed: {len(self.errors)} error(s)"]
        if self.errors:
            parts.append(f"\nErrors:\n{error_str}")
        if warning_str:
            parts.append(f"\nWarnings:\n{warning_str}")

        return "\n".join(parts)
