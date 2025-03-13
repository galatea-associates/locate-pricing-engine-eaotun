"""
Initialization module for the integration tests configuration package.

Provides centralized access to test settings and configuration for integration tests of the 
Borrow Rate & Locate Fee Pricing Engine. This module exports the necessary configuration 
components for test setup, mock server configuration, and test environment management.
"""

import os
import logging

from .settings import (
    TestSettings,
    MockServerConfig,
    get_test_settings,
    get_mock_server_url
)
from src.backend.config.environment import Environment

# Configure module logger
logger = logging.getLogger(__name__)

def configure_test_environment() -> TestSettings:
    """
    Configures the test environment based on environment variables or defaults.
    
    Returns:
        TestSettings: Configured test settings instance
    """
    # Get test settings using get_test_settings()
    settings = get_test_settings()
    
    # Log the test environment configuration
    logger.info(
        f"Configured test environment: "
        f"environment={settings.environment}, "
        f"api_url={settings.get_api_url()}, "
        f"use_mock_servers={settings.is_using_mock_servers()}"
    )
    
    # Return the test settings instance
    return settings

# Make DEVELOPMENT environment enum directly importable
DEVELOPMENT = Environment.DEVELOPMENT

# Export necessary components
__all__ = [
    'TestSettings',
    'MockServerConfig',
    'get_test_settings',
    'get_mock_server_url',
    'configure_test_environment',
    'Environment',
    'DEVELOPMENT',
]