"""Example scripts demonstrating aponyx framework usage."""

from pathlib import Path

__all__ = ["get_examples_dir"]


def get_examples_dir() -> Path:
    """
    Return the path to installed examples directory.

    Returns
    -------
    Path
        Absolute path to examples directory.

    Examples
    --------
    >>> from aponyx.examples import get_examples_dir
    >>> examples = get_examples_dir()
    >>> list(examples.glob("*.py"))
    [PosixPath('.../data_demo.py'), ...]
    """
    return Path(__file__).parent
