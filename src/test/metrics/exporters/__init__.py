"""
Initialization module for the metrics exporters package, providing a unified interface
for various metrics exporters used during testing of the Borrow Rate & Locate Fee Pricing Engine.
"""

import logging
import abc

from .prometheus import BaseExporter, PrometheusExporter
from .csv import CSVExporter
from .json import JSONExporter

# Configure logger
logger = logging.getLogger(__name__)

class MetricsExporter(BaseExporter):
    """
    Alias for BaseExporter to provide a more intuitive name for the base class.
    """
    pass

# Define what should be exported from this module
__all__ = ['BaseExporter', 'PrometheusExporter', 'CSVExporter', 'JSONExporter', 'MetricsExporter']