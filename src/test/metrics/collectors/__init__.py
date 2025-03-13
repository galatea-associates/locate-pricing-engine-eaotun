"""
Initialization module for metrics collectors package, providing a unified interface for
various metrics collectors used during testing of the Borrow Rate & Locate Fee Pricing Engine.
"""

import logging

# Import collector classes from submodules
from .api_metrics import BaseMetricsCollector, APIMetricsCollector
from .calculation_metrics import CalculationMetricsCollector
from .resource_metrics import ResourceMetricsCollector

# Configure logging for the metrics collectors package
logger = logging.getLogger(__name__)

# Define MetricsCollector as an alias for BaseMetricsCollector
# This provides a more intuitive name for the base class
MetricsCollector = BaseMetricsCollector

# Define what's exported from the package
__all__ = [
    'BaseMetricsCollector',
    'APIMetricsCollector',
    'CalculationMetricsCollector',
    'ResourceMetricsCollector',
    'MetricsCollector'
]