"""
Package initialization module for integration tests of the Borrow Rate & Locate Fee Pricing Engine.
Exports key testing utilities, configuration, and helper classes to simplify test implementation
and provide a consistent testing interface across all integration test modules.
"""

import logging
import pytest  # version: 7.4.0+

# Import test settings and configuration
from .config.settings import get_test_settings, TestSettings, TestEnvironment

# Import API client helpers
from .helpers.api_client import APIClient, create_api_client

# Import mock server utilities
from .helpers.mock_server import (
    MockServer,
    SecLendMockServer,
    MarketApiMockServer,
    EventApiMockServer,
    MockServerContext
)

# Import assertion helpers
from .helpers.assertions import (
    Assertions,
    assert_decimal_equality,
    assert_json_response,
    assert_status_code
)

# Configure module logger
logger = logging.getLogger(__name__)

# Module version
VERSION = '1.0.0'


def setup_integration_test_environment(use_mock_servers: bool) -> TestSettings:
    """
    Sets up the integration test environment with proper configuration
    
    Args:
        use_mock_servers: Whether to use mock servers for external APIs
        
    Returns:
        Configured test settings
    """
    # Load test environment variables
    logger.info("Setting up integration test environment")
    
    # Get test settings
    settings = get_test_settings()
    
    # Configure logging for integration tests
    logging_level = logging.INFO
    logging.basicConfig(
        level=logging_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set up mock servers if requested
    if use_mock_servers:
        logger.info("Configuring environment to use mock servers")
        # This doesn't start the mock servers, just configures the settings
        # to use them when they're started
        settings.use_mock_servers = True
    
    logger.info(f"Integration test environment setup complete (environment: {settings.environment})")
    return settings


def create_test_client(settings: Optional[TestSettings] = None) -> APIClient:
    """
    Creates a configured API client for integration tests
    
    Args:
        settings: Test settings (will use default if None)
        
    Returns:
        Configured API client
    """
    # Get test settings if not provided
    if settings is None:
        settings = get_test_settings()
    
    logger.info(f"Creating test API client for {settings.get_api_url()}")
    
    # Create API client
    client = create_api_client(settings=settings)
    
    # Configure mock servers if needed
    if settings.is_using_mock_servers():
        client.configure_mock_servers()
    
    # Wait for API to be ready
    logger.info("Waiting for API to be ready...")
    if not client.wait_for_api_ready():
        logger.warning("API readiness check timed out")
    
    return client


def create_mock_servers(settings: Optional[TestSettings] = None) -> Dict[str, MockServer]:
    """
    Creates and configures mock servers for external APIs
    
    Args:
        settings: Test settings (will use default if None)
        
    Returns:
        Dictionary of configured mock servers
    """
    # Get test settings if not provided
    if settings is None:
        settings = get_test_settings()
    
    logger.info("Creating mock servers for external APIs")
    
    # Create mock servers
    seclend_server = SecLendMockServer(settings=settings)
    market_server = MarketApiMockServer(settings=settings)
    event_server = EventApiMockServer(settings=settings)
    
    # Return dictionary with all mock servers
    return {
        'seclend': seclend_server,
        'market': market_server,
        'event': event_server
    }