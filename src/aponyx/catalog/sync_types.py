"""
Sync result types for YAML to JSON synchronization.

Defines dataclasses for sync operation results.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SyncResult:
    """
    Result of YAML to JSON sync operation.

    Attributes
    ----------
    success : bool
        True if all files synced successfully.
    files_written : tuple[Path, ...]
        Paths of JSON files that were written.
    files_unchanged : tuple[Path, ...]
        Paths of JSON files that were unchanged.
    errors : tuple[str, ...]
        Error messages for any failures.
    dry_run : bool
        Whether this was a dry-run (no files written).
    """

    success: bool
    files_written: tuple[Path, ...] = field(default_factory=tuple)
    files_unchanged: tuple[Path, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    dry_run: bool = False

    def __str__(self) -> str:
        """Format result for display."""
        if self.dry_run:
            prefix = "[DRY RUN] "
        else:
            prefix = ""

        if self.success:
            written = len(self.files_written)
            unchanged = len(self.files_unchanged)
            return f"{prefix}Sync complete: {written} files updated, {unchanged} unchanged"

        error_str = "\n  ".join(self.errors)
        return f"{prefix}Sync failed:\n  {error_str}"
