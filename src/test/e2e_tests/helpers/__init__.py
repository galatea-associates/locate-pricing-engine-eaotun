"""
Entry point for the end-to-end test helpers module that exposes key functionality from individual helper modules.
Provides a simplified interface for test files to access API client, test data management, and validation utilities
for the Borrow Rate & Locate Fee Pricing Engine.
"""

import logging

# Import helpers from API client module
from .api_client import APIClient, parse_response

# Import helpers from test data module
from .test_data import (
    TestDataManager, create_test_data, cleanup_test_data,
    get_test_scenario, calculate_expected_fee
)

# Import helpers from validation module
from .validation import (
    ResponseValidator, validate_calculation_response,
    validate_borrow_rate_response, assert_calculation_accuracy,
    run_calculation_test
)

# Import settings utilities
from ..config.settings import get_test_settings

# Configure logger
logger = logging.getLogger(__name__)

# Define exported symbols
__all__ = [
    'APIClient', 
    'TestDataManager', 
    'ResponseValidator', 
    'get_test_settings',
    'create_test_data',
    'cleanup_test_data',
    'get_test_scenario',
    'calculate_expected_fee',
    'validate_calculation_response',
    'validate_borrow_rate_response',
    'assert_calculation_accuracy',
    'run_calculation_test'
]