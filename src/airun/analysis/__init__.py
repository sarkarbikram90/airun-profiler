"""Analysis package."""

from airun.analysis.analyzer import analyze_spans
from airun.analysis.comparator import StepDiff, TraceComparison, compare_traces
from airun.analysis.waste import (
    MFUReport,
    WasteAnalysisReport,
    WasteCategory,
    WasteComponent,
    calculate_mfu,
    detect_compute_waste,
)

__all__ = [
    "analyze_spans",
    "compare_traces",
    "TraceComparison",
    "StepDiff",
    "calculate_mfu",
    "detect_compute_waste",
    "WasteCategory",
    "WasteComponent",
    "WasteAnalysisReport",
    "MFUReport",
]
