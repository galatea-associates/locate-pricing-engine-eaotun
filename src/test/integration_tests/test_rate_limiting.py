"""
Integration tests for the rate limiting functionality of the Borrow Rate & Locate Fee Pricing Engine API.
Tests verify that the API correctly enforces rate limits, returns appropriate headers, and handles rate
limit exceeded scenarios properly.
"""

import pytest
import requests
import time
from typing import Dict, Any

from .helpers.api_client import APIClient, create_api_client
from .helpers.assertions import Assertions
from .config.settings import get_test_settings
from src.backend.core.constants import ErrorCodes, API_RATE_LIMIT_DEFAULT


def setup_module():
    """Setup function that runs once before all tests in the module"""
    # Create an API client instance
    api_client = create_api_client()
    
    # Wait for the API to be ready before running tests
    api_client.wait_for_api_ready()
    
    # Verify that authentication is working properly
    assert api_client.test_authentication()


def test_rate_limit_headers():
    """Test that API responses include the correct rate limit headers"""
    # Create an API client instance
    api_client = create_api_client()
    
    # Make a request to the health endpoint
    response = api_client.get("/health")
    
    # Verify that the response includes rate limit headers
    assert 'X-RateLimit-Limit' in response.headers
    assert 'X-RateLimit-Remaining' in response.headers
    assert 'X-RateLimit-Reset' in response.headers
    
    # Verify that the limit header matches the expected rate limit
    assert int(response.headers.get('X-RateLimit-Limit')) == API_RATE_LIMIT_DEFAULT
    
    # Verify that the remaining header is less than the limit
    assert int(response.headers.get('X-RateLimit-Remaining')) < API_RATE_LIMIT_DEFAULT


def test_rate_limit_decrement():
    """Test that the remaining requests counter decrements with each request"""
    # Create an API client instance
    api_client = create_api_client()
    
    # Make an initial request to the health endpoint
    response1 = api_client.get("/health")
    remaining1 = int(response1.headers.get('X-RateLimit-Remaining', 0))
    
    # Make a second request to the health endpoint
    response2 = api_client.get("/health")
    remaining2 = int(response2.headers.get('X-RateLimit-Remaining', 0))
    
    # Verify that the remaining count has decreased by 1
    assert remaining2 == remaining1 - 1


def test_rate_limit_exceeded():
    """Test that the API returns a 429 error when rate limit is exceeded"""
    # Create an API client instance with a very low rate limit
    settings = get_test_settings()
    api_client = create_api_client(settings)
    assertions = Assertions()
    
    # Make requests in a loop until rate limit is exceeded
    response = None
    max_requests = API_RATE_LIMIT_DEFAULT + 10  # Safety margin
    
    for _ in range(max_requests):
        response = api_client.health_check()
        if response.status_code == 429:
            break
    
    # Verify that the final response has a 429 status code
    assertions.assert_error_response(
        response=response,
        expected_status_code=429,
        expected_error_code=ErrorCodes.RATE_LIMIT_EXCEEDED.value
    )
    
    # Verify that the response includes a Retry-After header
    assert 'Retry-After' in response.headers


@pytest.mark.slow
def test_rate_limit_reset():
    """Test that the rate limit counter resets after the specified window"""
    # Create an API client instance with a low rate limit
    api_client = create_api_client()
    
    # Make requests until close to the limit
    limit = API_RATE_LIMIT_DEFAULT
    for _ in range(limit - 5):
        api_client.health_check()
    
    # Extract the reset time from the response headers
    response = api_client.health_check()
    reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
    current_time = int(time.time())
    
    # Calculate the seconds until reset
    wait_time = max(reset_time - current_time + 1, 1)
    
    # Wait for the rate limit window to reset
    time.sleep(wait_time)
    
    # Make another request after the reset
    response = api_client.health_check()
    
    # Verify that the request succeeds
    assert response.status_code == 200
    
    # Verify that the remaining requests count has been reset to near the limit
    remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
    assert remaining > limit - 10


def test_different_endpoints_share_limit():
    """Test that different API endpoints share the same rate limit counter"""
    # Create an API client instance
    api_client = create_api_client()
    
    # Make a request to the health endpoint
    response1 = api_client.health_check()
    remaining1 = int(response1.headers.get('X-RateLimit-Remaining', 0))
    
    # Make a request to the borrow rate endpoint
    response2 = api_client.get_borrow_rate("AAPL")
    remaining2 = int(response2.headers.get('X-RateLimit-Remaining', 0))
    
    # Verify that the remaining count has decreased
    assert remaining2 == remaining1 - 1
    
    # Make a request to the calculate-locate endpoint
    response3 = api_client.calculate_locate_fee("AAPL", 10000, 30, "test_broker_1")
    remaining3 = int(response3.headers.get('X-RateLimit-Remaining', 0))
    
    # Verify that the remaining count has decreased again
    assert remaining3 == remaining2 - 1


def test_exempt_paths_not_rate_limited():
    """Test that exempt paths are not subject to rate limiting"""
    # Create an API client instance
    api_client = create_api_client()
    settings = get_test_settings()
    
    # Make multiple requests to exempt paths (e.g., /health, /docs)
    base_url = settings.api_base_url
    exempt_paths = ['/docs', '/redoc', '/openapi.json']
    
    for path in exempt_paths:
        # Make several requests to the potentially exempt path
        for _ in range(5):
            response = requests.get(f"{base_url}{path}")
            assert response.status_code == 200
            
            # Exempt paths should not have rate limit headers
            if 'X-RateLimit-Limit' not in response.headers:
                break
    
    # Make a request to a non-exempt path
    response = api_client.health_check()
    
    # Verify that the rate limit headers are present for non-exempt paths
    assert 'X-RateLimit-Limit' in response.headers


class TestRateLimiting:
    """Test class for rate limiting functionality"""
    
    @classmethod
    def setup_class(cls):
        """Setup method that runs once before all tests in the class"""
        # Create an API client instance
        cls.settings = get_test_settings()
        cls.api_client = create_api_client(cls.settings)
        cls.assertions = Assertions()
    
    def setup_method(self):
        """Setup method that runs before each test method"""
        # Create a fresh API client for each test
        self.api_client = create_api_client(self.settings)
        # Reset any test-specific state
    
    def test_rate_limit_headers_present(self):
        """Test that API responses include rate limit headers"""
        # Make a request to the API
        response = self.api_client.health_check()
        
        # Verify that X-RateLimit-Limit header is present
        assert 'X-RateLimit-Limit' in response.headers
        
        # Verify that X-RateLimit-Remaining header is present
        assert 'X-RateLimit-Remaining' in response.headers
        
        # Verify that X-RateLimit-Reset header is present
        assert 'X-RateLimit-Reset' in response.headers
    
    def test_rate_limit_exceeded_response(self):
        """Test the API response when rate limit is exceeded"""
        # Make multiple requests to exceed the rate limit
        limit = API_RATE_LIMIT_DEFAULT
        response = None
        
        for _ in range(limit + 5):  # Add some margin to ensure we hit the limit
            response = self.api_client.health_check()
            if response.status_code == 429:
                break
        
        # Verify that the response has 429 status code
        self.assertions.assert_error_response(
            response=response,
            expected_status_code=429,
            expected_error_code=ErrorCodes.RATE_LIMIT_EXCEEDED.value
        )
        
        # Verify that the response has Retry-After header
        assert 'Retry-After' in response.headers
    
    @pytest.mark.slow
    def test_rate_limit_window_reset(self):
        """Test that rate limit resets after the time window"""
        # Make requests to approach the rate limit
        limit = API_RATE_LIMIT_DEFAULT
        for _ in range(limit - 5):
            self.api_client.health_check()
        
        # Wait for the rate limit window to reset
        response = self.api_client.health_check()
        reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
        current_time = int(time.time())
        wait_time = max(reset_time - current_time + 1, 1)
        time.sleep(wait_time)
        
        # Make another request after reset
        response = self.api_client.health_check()
        
        # Verify that the rate limit has been reset
        remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
        assert remaining > limit - 10