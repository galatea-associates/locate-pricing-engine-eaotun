"""
Initialization module for the performance tests configuration package.

This module exports the configuration settings and utilities needed for performance testing 
of the Borrow Rate & Locate Fee Pricing Engine, providing a centralized access point for 
test settings, thresholds, and environment-specific configurations.
"""

from .settings import TestSettings, PerformanceThresholds, get_test_settings

# Export all components for easy import
__all__ = [
    'TestSettings',
    'PerformanceThresholds',
    'get_test_settings',
]