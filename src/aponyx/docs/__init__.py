"""Documentation files for aponyx framework."""

from pathlib import Path

__all__ = ["get_docs_dir"]


def get_docs_dir() -> Path:
    """
    Return the path to installed documentation directory.

    Returns
    -------
    Path
        Absolute path to docs directory.

    Examples
    --------
    >>> from aponyx.docs import get_docs_dir
    >>> docs = get_docs_dir()
    >>> list(docs.glob("*.md"))
    [PosixPath('.../python_guidelines.md'), ...]
    """
    return Path(__file__).parent
