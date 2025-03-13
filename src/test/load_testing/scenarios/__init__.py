"""
Load Testing Scenarios Package for Borrow Rate & Locate Fee Pricing Engine.

This package contains various user scenarios for load testing the API endpoints 
of the Borrow Rate & Locate Fee Pricing Engine. These scenarios are designed to
support performance testing requirements including load testing (1000 requests/second), 
stress testing (2000+ requests/second), endurance testing (sustained load for 24 hours),
and spike testing (sudden increase to 3000 requests/second).
"""

import logging

# Set up module logger
logger = logging.getLogger(__name__)

# Import all scenario classes
from .borrow_rate_scenario import BorrowRateScenario
from .calculate_fee_scenario import CalculateFeeScenario
from .mixed_workload_scenario import MixedWorkloadScenario

logger.info("Load testing scenarios module initialized")

# Define public API for the scenarios package
__all__ = [
    'BorrowRateScenario',
    'CalculateFeeScenario',
    'MixedWorkloadScenario',
]