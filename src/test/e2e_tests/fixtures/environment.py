"""
Provides pytest fixtures for test environment configuration in end-to-end tests of the Borrow Rate & Locate Fee Pricing Engine.
This module creates and manages test environments with appropriate settings for different deployment targets and test scenarios.
"""

import os
import logging
import pytest
import requests
from typing import Dict, Optional, List, Any, Union

from ..config.settings import get_test_settings, TestEnvironment
from ..fixtures.test_data import setup_test_data, cleanup_test_data

# Configure logger
logger = logging.getLogger(__name__)


def setup_environment(env_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sets up the test environment based on configuration.
    
    Args:
        env_config: Environment configuration dictionary
        
    Returns:
        Environment configuration with additional runtime information
    """
    logger.info(f"Setting up test environment: {env_config.get('environment', 'unknown')}")
    
    # Get test settings
    settings = get_test_settings()
    
    # Determine if we should mock external APIs
    use_mocks = settings.mock_external_apis
    
    # Set up mock servers if needed
    mock_servers = []
    if use_mocks:
        logger.info("Setting up mock servers for external APIs")
        # In a real implementation, this would start mock servers
        # For now, just log the intention
        mock_servers = []  # Would contain references to started mock servers
    
    # Verify API availability
    api_url = settings.get_api_url()
    api_key = settings.api_key
    if not verify_api_availability(api_url, api_key, timeout=settings.test_timeout):
        logger.warning(f"API not available at {api_url}")
    
    # Set up test data
    test_data_refs = setup_test_data(env_config)
    
    # Update environment config with runtime information
    env_config.update({
        'mock_servers': mock_servers,
        'test_data_refs': test_data_refs,
        'api_url': api_url,
        'api_key': api_key
    })
    
    logger.info("Test environment setup complete")
    return env_config


def teardown_environment(env_config: Dict[str, Any], test_data_refs: Dict[str, List[str]]) -> None:
    """
    Tears down the test environment and cleans up resources.
    
    Args:
        env_config: Environment configuration dictionary
        test_data_refs: References to test data created during setup
    """
    logger.info(f"Tearing down test environment: {env_config.get('environment', 'unknown')}")
    
    # Clean up test data
    cleanup_test_data(env_config, test_data_refs)
    
    # Stop mock servers if they were started
    for server in env_config.get('mock_servers', []):
        logger.info(f"Stopping mock server: {server}")
        # In a real implementation, this would stop the mock server
        # For now, just log the intention
    
    logger.info("Test environment teardown complete")


def verify_api_availability(api_url: str, api_key: str, timeout: int = 30) -> bool:
    """
    Verifies that the API is available and responding correctly.
    
    Args:
        api_url: Base URL of the API
        api_key: API key for authentication
        timeout: Request timeout in seconds
        
    Returns:
        True if API is available, False otherwise
    """
    health_url = f"{api_url}/health"
    headers = {"X-API-Key": api_key}
    
    logger.info(f"Verifying API availability at {health_url}")
    
    try:
        response = requests.get(health_url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            # Check if response contains expected health check data
            data = response.json()
            if data.get("status") == "healthy":
                logger.info("API health check successful")
                return True
            else:
                logger.warning(f"API returned unexpected health status: {data.get('status')}")
                return False
        else:
            logger.warning(f"API health check failed with status code: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error during API health check: {str(e)}")
        return False


class TestEnvironmentManager:
    """
    Manages test environment setup and teardown for end-to-end tests.
    """
    
    def __init__(self):
        """
        Initializes the TestEnvironmentManager with default values.
        """
        self._env_config: Dict[str, Any] = {}
        self._test_data_refs: Dict[str, List[str]] = {}
        self._mock_servers: List[Any] = []
        self._is_setup: bool = False
    
    def setup(self) -> Dict[str, Any]:
        """
        Sets up the test environment.
        
        Returns:
            Environment configuration
        """
        if self._is_setup:
            logger.warning("Environment is already set up. Skipping setup.")
            return self._env_config
        
        # Get test settings
        settings = get_test_settings()
        
        # Create initial environment config
        self._env_config = {
            'environment': settings.environment,
            'settings': settings,
            'api_base_url': settings.api_base_url,
            'api_version': settings.api_version,
            'api_key': settings.api_key,
            'mock_external_apis': settings.mock_external_apis,
            'test_timeout': settings.test_timeout
        }
        
        # Set up mock servers if needed
        if settings.mock_external_apis:
            logger.info("Setting up mock servers for external APIs")
            # In a real implementation, this would start mock servers
            self._mock_servers = []  # Would contain references to started mock servers
            self._env_config['mock_servers'] = self._mock_servers
        
        # Verify API availability
        api_url = settings.get_api_url()
        api_key = settings.api_key
        
        if not verify_api_availability(api_url, api_key, timeout=settings.test_timeout):
            logger.warning(f"API not available at {api_url}")
        
        # Set up test data
        self._test_data_refs = setup_test_data(self._env_config)
        self._env_config['test_data_refs'] = self._test_data_refs
        
        self._is_setup = True
        logger.info("Test environment setup complete")
        return self._env_config
    
    def teardown(self) -> None:
        """
        Tears down the test environment.
        """
        if not self._is_setup:
            logger.warning("Environment is not set up. Skipping teardown.")
            return
        
        # Clean up test data
        cleanup_test_data(self._env_config, self._test_data_refs)
        
        # Stop mock servers if they were started
        for server in self._mock_servers:
            logger.info(f"Stopping mock server: {server}")
            # In a real implementation, this would stop the mock server
        
        # Reset environment state
        self._test_data_refs = {}
        self._mock_servers = []
        self._is_setup = False
        
        logger.info("Test environment teardown complete")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Gets the current environment configuration.
        
        Returns:
            Current environment configuration
        """
        return self._env_config.copy()
    
    def get_test_data_refs(self) -> Dict[str, List[str]]:
        """
        Gets references to test data created during setup.
        
        Returns:
            Test data references
        """
        return self._test_data_refs.copy()
    
    def is_local(self) -> bool:
        """
        Checks if the current environment is local.
        
        Returns:
            True if environment is local
        """
        return self._env_config.get('environment') == TestEnvironment.LOCAL
    
    def is_development(self) -> bool:
        """
        Checks if the current environment is development.
        
        Returns:
            True if environment is development
        """
        return self._env_config.get('environment') == TestEnvironment.DEVELOPMENT
    
    def is_staging(self) -> bool:
        """
        Checks if the current environment is staging.
        
        Returns:
            True if environment is staging
        """
        return self._env_config.get('environment') == TestEnvironment.STAGING
    
    def is_production(self) -> bool:
        """
        Checks if the current environment is production.
        
        Returns:
            True if environment is production
        """
        return self._env_config.get('environment') == TestEnvironment.PRODUCTION


@pytest.fixture(scope="session")
def environment_manager() -> TestEnvironmentManager:
    """
    Pytest fixture that provides the TestEnvironmentManager instance.
    
    Returns:
        TestEnvironmentManager: Instance that manages the test environment
    """
    manager = TestEnvironmentManager()
    manager.setup()
    yield manager
    manager.teardown()


@pytest.fixture(scope="session")
def environment(environment_manager: TestEnvironmentManager) -> Dict[str, Any]:
    """
    Pytest fixture that provides a configured test environment.
    
    Args:
        environment_manager: The TestEnvironmentManager instance
        
    Returns:
        Dict: Environment configuration dictionary
    """
    return environment_manager.get_config()