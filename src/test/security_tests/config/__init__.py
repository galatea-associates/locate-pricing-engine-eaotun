"""
Initialization module for the security tests configuration package.

This module imports and exposes key configuration components from the settings module
to provide a centralized access point for security test configuration across the test suite.
It includes test environment types, security tool configurations, test payload definitions,
and utility functions for accessing these settings.
"""

from .settings import (
    TestEnvironment,
    TestSettings,
    SecurityToolsConfig,
    TestPayloadsConfig,
    get_test_settings,
    load_test_env
)

# Create a singleton instance of TestSettings for convenience
settings = get_test_settings()

# Export all components for easy access
__all__ = [
    'TestEnvironment',  # Includes LOCAL, DEVELOPMENT, STAGING, PRODUCTION, get_env
    'TestSettings',     # Includes api_base_url, api_version, test_api_key, invalid_api_key,
                        # environment, security_scan_timeout, use_tls_verification, zap_api_url,
                        # rate_limit_threshold, get_api_url, get_security_tool_config, get_test_payload
    'SecurityToolsConfig',  # Includes zap, jwt_analyzer, fuzzer, dependency_scanner
    'TestPayloadsConfig',   # Includes sql_injection, xss, authentication_bypass, input_validation
    'get_test_settings',
    'load_test_env',
    'settings'
]