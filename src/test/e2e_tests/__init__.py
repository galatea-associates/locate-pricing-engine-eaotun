"""
Initialization module for end-to-end tests of the Borrow Rate & Locate Fee Pricing Engine.
This module exposes key components and utilities needed for E2E testing, making them easily 
importable by test modules.
"""

import pytest  # version: 7.4.0+
import logging  # standard library

from .config.settings import TestSettings, TestEnvironment, get_test_settings
from .helpers.api_client import APIClient, create_api_client
from .helpers.validation import ResponseValidator

# Configure logger
logger = logging.getLogger(__name__)

# Define end-to-end test marker
E2E_TEST_MARKER = pytest.mark.e2e

def setup_e2e_test_environment():
    """
    Sets up the environment for end-to-end tests
    
    Returns:
        dict: Dictionary with test environment configuration
    """
    # Get test settings
    settings = get_test_settings()
    
    # Log test environment setup
    logger.info(f"Setting up E2E test environment for: {settings.environment.name}")
    
    # Return dictionary with test environment configuration
    return {
        "environment": settings.environment,
        "api_base_url": settings.api_base_url,
        "api_version": settings.api_version,
        "mock_external_apis": settings.mock_external_apis
    }