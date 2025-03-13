"""
Initialization module for the end-to-end tests configuration package.

This module exports configuration components for the end-to-end tests,
including environment settings, test data configuration, and helper functions.
It centralizes access to test configuration to ensure consistent test execution
across different environments.
"""

from .settings import (
    TestEnvironment,
    TestSettings,
    MockServerConfig,
    TestDataConfig,
    get_test_settings,
    load_test_env
)

# Default configuration values
DEFAULT_TEST_ENV_FILE = '.env.test'
DEFAULT_TEST_TIMEOUT = 30
DEFAULT_API_VERSION = 'v1'

__all__ = [
    'TestEnvironment',
    'TestSettings',
    'MockServerConfig',
    'TestDataConfig',
    'get_test_settings',
    'load_test_env',
    'DEFAULT_TEST_ENV_FILE',
    'DEFAULT_TEST_TIMEOUT',
    'DEFAULT_API_VERSION',
]