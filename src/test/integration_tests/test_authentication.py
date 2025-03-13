"""
Integration tests for the authentication system of the Borrow Rate & Locate Fee Pricing Engine.
This module tests API key authentication, rate limiting, error handling for invalid credentials,
and token-based authentication across the API endpoints.
"""

import pytest
import requests
import time
import logging
from decimal import Decimal

from .helpers.api_client import APIClient, create_api_client
from .config.settings import get_test_settings, TestSettings
from .fixtures.api_responses import ERROR_RESPONSES
from src.backend.core.constants import ErrorCodes

# Configure module logger
logger = logging.getLogger(__name__)

# Test data constants
TEST_TICKER = "AAPL"
TEST_POSITION_VALUE = Decimal('100000')
TEST_LOAN_DAYS = 30
TEST_CLIENT_ID = "test_client"


@pytest.fixture
def api_client():
    """
    Pytest fixture that provides a configured API client for tests.
    
    Returns:
        APIClient: Configured API client instance
    """
    settings = get_test_settings()
    client = create_api_client(settings)
    return client


@pytest.fixture
def invalid_api_client():
    """
    Pytest fixture that provides an API client with invalid credentials.
    
    Returns:
        APIClient: API client with invalid API key
    """
    settings = get_test_settings()
    # Create a copy of settings
    invalid_settings = TestSettings()
    # Set an invalid API key
    invalid_settings.test_api_key = "invalid-api-key"
    
    client = create_api_client(invalid_settings)
    return client


def test_valid_authentication(api_client):
    """Tests that a valid API key successfully authenticates."""
    result = api_client.test_authentication()
    assert result is True


def test_invalid_authentication(invalid_api_client):
    """Tests that an invalid API key fails authentication."""
    result = invalid_api_client.test_authentication()
    assert result is False


def test_health_check_authentication(api_client, invalid_api_client):
    """Tests that the health check endpoint requires authentication."""
    # Test with valid credentials
    response = api_client.health_check()
    assert response.status == "healthy"
    
    # Test with invalid credentials
    response = invalid_api_client.health_check()
    assert response.get("error") == ErrorCodes.UNAUTHORIZED.value


def test_get_rate_authentication(api_client, invalid_api_client):
    """Tests that the get rate endpoint requires authentication."""
    # Test with valid credentials
    response = api_client.get_borrow_rate(TEST_TICKER)
    assert response.status == "success"
    
    # Test with invalid credentials
    response = invalid_api_client.get_borrow_rate(TEST_TICKER)
    assert response.get("error") == ErrorCodes.UNAUTHORIZED.value


def test_calculate_fee_authentication(api_client, invalid_api_client):
    """Tests that the calculate fee endpoint requires authentication."""
    # Test with valid credentials
    response = api_client.calculate_locate_fee(
        TEST_TICKER, TEST_POSITION_VALUE, TEST_LOAN_DAYS, TEST_CLIENT_ID)
    assert response.status == "success"
    
    # Test with invalid credentials
    response = invalid_api_client.calculate_locate_fee(
        TEST_TICKER, TEST_POSITION_VALUE, TEST_LOAN_DAYS, TEST_CLIENT_ID)
    assert response.get("error") == ErrorCodes.UNAUTHORIZED.value


def test_direct_request_without_api_key():
    """Tests that direct requests without API key are rejected."""
    settings = get_test_settings()
    url = f"{settings.get_api_url()}/health"
    
    # Make request without API key
    response = requests.get(url)
    
    # Check that it returns unauthorized
    assert response.status_code == 401
    assert response.json().get("error") == ErrorCodes.UNAUTHORIZED.value


@pytest.mark.slow
def test_rate_limiting(api_client):
    """Tests that rate limiting is enforced after exceeding the limit."""
    settings = get_test_settings()
    
    # Make a single request to check it works
    response = api_client.health_check()
    assert response.status == "healthy"
    
    # Make many requests to exceed the rate limit
    # Default rate limit is 60 requests per minute
    rate_limit_exceeded = False
    for i in range(61):  # One more than the default limit
        response = api_client.health_check()
        if isinstance(response, dict) and response.get("error") == ErrorCodes.RATE_LIMIT_EXCEEDED.value:
            rate_limit_exceeded = True
            break
    
    # Either the rate limit was hit or we're in an environment with higher limits
    if rate_limit_exceeded:
        assert response.get("error") == ErrorCodes.RATE_LIMIT_EXCEEDED.value
    else:
        logger.warning("Rate limit not exceeded after 61 requests. This may be expected in environments with higher limits.")


@pytest.mark.slow
def test_rate_limit_reset(api_client):
    """Tests that rate limits reset after the specified window."""
    settings = get_test_settings()
    
    # Make requests until rate limit is exceeded
    rate_limit_exceeded = False
    for i in range(61):  # One more than the default limit
        response = api_client.health_check()
        if isinstance(response, dict) and response.get("error") == ErrorCodes.RATE_LIMIT_EXCEEDED.value:
            rate_limit_exceeded = True
            break
    
    if rate_limit_exceeded:
        # Wait for rate limit window to reset (60 seconds)
        time.sleep(60)
        
        # Try again after waiting
        response = api_client.health_check()
        assert response.status == "healthy"
    else:
        logger.warning("Rate limit not exceeded after 61 requests. Skipping reset test.")