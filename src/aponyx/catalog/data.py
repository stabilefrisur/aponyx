"""
Container dataclasses for catalog data.

Defines data structures that hold parsed YAML content with
comment preservation for round-trip editing.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruamel.yaml import CommentedMap

    from aponyx.catalog.entries import (
        IndicatorTransformationEntry,
        InstrumentEntry,
        ScoreTransformationEntry,
        SecurityEntry,
        SignalEntry,
        SignalTransformationEntry,
        StrategyEntry,
    )


@dataclass
class CatalogsData:
    """
    Parsed content of catalogs.yaml.

    Preserves YAML comments and structure for round-trip editing.

    Attributes
    ----------
    raw : CommentedMap
        Raw ruamel.yaml object preserving comments.
    indicator_transformations : list[IndicatorTransformationEntry]
        Parsed indicator transformation entries.
    score_transformations : list[ScoreTransformationEntry]
        Parsed score transformation entries.
    signal_transformations : list[SignalTransformationEntry]
        Parsed signal transformation entries.
    signals : list[SignalEntry]
        Parsed signal entries.
    strategies : list[StrategyEntry]
        Parsed strategy entries.
    """

    raw: "CommentedMap"
    indicator_transformations: list["IndicatorTransformationEntry"]
    score_transformations: list["ScoreTransformationEntry"]
    signal_transformations: list["SignalTransformationEntry"]
    signals: list["SignalEntry"]
    strategies: list["StrategyEntry"]


@dataclass
class SecuritiesData:
    """
    Parsed content of securities.yaml.

    Preserves YAML comments and structure for round-trip editing.

    Attributes
    ----------
    raw : CommentedMap
        Raw ruamel.yaml object preserving comments.
    securities : dict[str, SecurityEntry]
        Parsed security entries keyed by name.
    instruments : dict[str, InstrumentEntry]
        Parsed instrument entries keyed by type.
    """

    raw: "CommentedMap"
    securities: dict[str, "SecurityEntry"]
    instruments: dict[str, "InstrumentEntry"]
