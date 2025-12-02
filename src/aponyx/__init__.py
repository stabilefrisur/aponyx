"""
Aponyx - Systematic Macro Credit Strategy Framework.

A modular Python framework for developing and backtesting systematic credit strategies.
"""

try:
    from importlib.metadata import version
    __version__ = version("aponyx")
except Exception:
    __version__ = "0.1.14"  # Fallback version


def hello() -> str:
    """Return greeting message."""
    return "Hello from aponyx!"
