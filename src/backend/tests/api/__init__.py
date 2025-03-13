"""
Initialization file for the API tests package in the Borrow Rate & Locate Fee Pricing Engine.
This file makes the API test modules importable and provides common test utilities, fixtures, and configurations specific to API testing.
"""

import pytest  # pytest 7.4.0+
from fastapi.testclient import TestClient  # fastapi.testclient 0.103.0+

from .. import setup_test_environment  # Import the test environment setup function from parent package
from ...main import app  # Import the FastAPI application for test client creation

# Create a test client for the FastAPI application
API_TEST_CLIENT = TestClient(app)

# Define a test API key for authentication purposes
TEST_API_KEY = "test_api_key"

# Define a header containing the test API key
API_KEY_HEADER = {"X-API-Key": TEST_API_KEY}


def setup_api_test_environment():
    """
    Helper function to set up API test environment with necessary configurations
    """
    # Call the parent setup_test_environment function
    setup_test_environment()

    # Configure API test specific settings
    # Set up mock authentication for tests
    pass


# Export the TestClient instance for use in API test modules
__all__ = ["API_TEST_CLIENT"]

# Export the test API key constant for authentication in tests
__all__ += ["TEST_API_KEY"]

# Export the API key header dictionary for use in test requests
__all__ += ["API_KEY_HEADER"]

# Export the API test environment setup function
__all__ += ["setup_api_test_environment"]