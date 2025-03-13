"""
Initialization module for the services test package in the Borrow Rate & Locate Fee Pricing Engine.

This module makes the directory a proper Python package and provides common imports,
utilities, and configurations for testing service components across calculation,
data, external API, and cache services.

The module offers standardized mock response creation, test environment setup,
and common constants used throughout the service tests.
"""

import pytest  # pytest 7.4.0+
from unittest.mock import MagicMock, patch  # standard library

# Import test utilities from parent package
from ...__init__ import setup_test_environment

# List of service test packages for discovery and organization
SERVICE_TEST_PACKAGES = ['calculation', 'data', 'external', 'cache', 'audit']

# Define decimal precision for financial calculation testing
TEST_DECIMAL_PRECISION = 10

def setup_service_test_environment():
    """
    Sets up the test environment specifically for service tests.
    
    This function extends the base test environment setup with service-specific
    configurations and mocks commonly needed across service tests.
    
    Returns:
        None
    """
    # Set up base test environment
    setup_test_environment()
    
    # Configure additional service-specific test settings
    # (This allows for future extension of service-specific setup)
    
    # Initialize common mocks for external dependencies
    # These could be expanded based on specific service test needs

def create_mock_response(data, status_code=200):
    """
    Creates a standardized mock response object for testing service components.
    
    This utility function provides a consistent way to create mock responses
    for testing HTTP requests in service components, particularly for external API 
    integrations.
    
    Args:
        data (dict): The response data to be returned by the json() method
        status_code (int): HTTP status code for the response, defaults to 200
        
    Returns:
        MagicMock: A mock response object with the specified data and status code
    """
    mock_response = MagicMock()
    mock_response.json.return_value = data
    mock_response.status_code = status_code
    return mock_response

# Define exports
__all__ = [
    "setup_service_test_environment",
    "create_mock_response",
    "SERVICE_TEST_PACKAGES",
    "TEST_DECIMAL_PRECISION",
    "pytest",
    "MagicMock",
    "patch"
]