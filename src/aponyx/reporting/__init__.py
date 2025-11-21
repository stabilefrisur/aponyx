"""
Report generation for systematic macro credit research.

Provides functionality for aggregating workflow results into
comprehensive analysis reports in multiple formats.
"""

from .generator import generate_report, ReportFormat

__all__ = ["generate_report", "ReportFormat"]
