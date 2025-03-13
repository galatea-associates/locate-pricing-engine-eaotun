"""
Initialization module for the performance tests package of the Borrow Rate & Locate Fee Pricing Engine.

This module exports key functionality from the performance testing framework, including configuration
settings, metrics collection, analysis tools, and reporting capabilities to support comprehensive
performance testing of the API.
"""

# Import from pytest for performance testing
import pytest  # pytest 7.4.0+

# Import configuration components
from .config import TestSettings, PerformanceThresholds, get_test_settings

# Import metrics collection and analysis helpers
from .helpers import (
    get_metrics_collector,
    get_api_metrics_collector,
    get_calculation_metrics_collector,
    metrics_collection,
    check_performance_thresholds,
    analyze_performance_results,
    generate_report
)

# Define version
__version__ = "1.0.0"

# Define exported symbols
__all__ = [
    "TestSettings",
    "PerformanceThresholds",
    "get_test_settings",
    "get_metrics_collector",
    "get_api_metrics_collector",
    "get_calculation_metrics_collector",
    "metrics_collection",
    "check_performance_thresholds",
    "analyze_performance_results",
    "generate_report"
]