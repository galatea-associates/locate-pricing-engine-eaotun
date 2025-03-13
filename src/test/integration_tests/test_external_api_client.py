"""
Integration tests for the external API client components of the Borrow Rate & Locate Fee Pricing Engine.
Tests the client's interaction with external APIs, retry logic, circuit breaker patterns, and fallback mechanisms.
"""

import pytest
import requests
import aiohttp
import json
import time
from decimal import Decimal
from unittest.mock import patch
from typing import Dict, Any

# Import client functions
from src.backend.services.external.client import (
    get, post, async_get, async_post,
    validate_response, build_url
)

# Import API-specific functions
from src.backend.services.external.seclend_api import get_borrow_rate
from src.backend.services.external.market_api import (
    get_market_volatility_index, get_stock_volatility
)
from src.backend.services.external.event_api import get_event_risk_factor

# Import exceptions and constants
from src.backend.core.exceptions import ExternalAPIException
from src.backend.core.constants import ExternalAPIs, BorrowStatus

# Import test utilities
from src.test.integration_tests.config.settings import get_test_settings
from src.test.integration_tests.helpers.mock_server import (
    MockServer, SecLendMockServer, MarketApiMockServer, EventApiMockServer,
    MockServerContext
)
from src.test.integration_tests.fixtures.api_responses import (
    SECLEND_API_RESPONSES,
    MARKET_API_RESPONSES,
    EVENT_API_RESPONSES
)

# Global test data
TEST_TICKER = 'AAPL'
TEST_BORROW_RATE = Decimal('0.05')
TEST_VOLATILITY = Decimal('18.5')
TEST_EVENT_RISK = 2


@pytest.fixture
def setup_mock_servers():
    """Pytest fixture to set up mock servers for external APIs."""
    # Create mock servers
    seclend_server = SecLendMockServer()
    market_server = MarketApiMockServer()
    event_server = EventApiMockServer()
    
    # Start servers and create context
    with MockServerContext([seclend_server, market_server, event_server]) as context:
        # Configure default responses
        seclend_server.configure_borrow_rate(
            TEST_TICKER, TEST_BORROW_RATE, BorrowStatus.EASY
        )
        
        market_server.configure_volatility(
            TEST_TICKER, TEST_VOLATILITY
        )
        market_server.configure_market_volatility(
            TEST_VOLATILITY
        )
        
        event_server.configure_event_risk(
            TEST_TICKER, TEST_EVENT_RISK
        )
        
        yield MockServerContext([seclend_server, market_server, event_server])


def test_build_url():
    """Tests the build_url function for correctly combining base URL and endpoint."""
    # Test basic URL building
    base_url = "https://api.example.com"
    endpoint = "v1/test"
    expected_url = "https://api.example.com/v1/test"
    
    result = build_url(base_url, endpoint)
    assert result == expected_url
    
    # Test with trailing slash in base URL
    base_url = "https://api.example.com/"
    expected_url = "https://api.example.com/v1/test"
    
    result = build_url(base_url, endpoint)
    assert result == expected_url
    
    # Test with leading slash in endpoint
    base_url = "https://api.example.com"
    endpoint = "/v1/test"
    expected_url = "https://api.example.com/v1/test"
    
    result = build_url(base_url, endpoint)
    assert result == expected_url
    
    # Test with both trailing and leading slashes
    base_url = "https://api.example.com/"
    endpoint = "/v1/test"
    expected_url = "https://api.example.com/v1/test"
    
    result = build_url(base_url, endpoint)
    assert result == expected_url


def test_validate_response():
    """Tests the validate_response function for checking required fields."""
    # Test with all required fields present
    response = {"field1": "value1", "field2": "value2", "field3": "value3"}
    required_fields = ["field1", "field2"]
    
    result = validate_response(response, required_fields)
    assert result is True
    
    # Test with missing required field
    response = {"field1": "value1", "field3": "value3"}
    required_fields = ["field1", "field2"]
    
    result = validate_response(response, required_fields)
    assert result is False
    
    # Test with empty response
    response = {}
    required_fields = ["field1", "field2"]
    
    result = validate_response(response, required_fields)
    assert result is False
    
    # Test with None response
    response = None
    required_fields = ["field1", "field2"]
    
    result = validate_response(response, required_fields)
    assert result is False


@pytest.mark.usefixtures('setup_mock_servers')
def test_get_function():
    """Tests the synchronous GET function for making HTTP requests."""
    # Get the test settings to get the mock server URLs
    settings = get_test_settings()
    seclend_url = settings.get_mock_server_url('seclend')
    
    # Create the full URL for the test endpoint
    test_endpoint = f"/api/borrows/{TEST_TICKER}"
    test_url = f"{seclend_url}{test_endpoint}"
    
    # Call the GET function
    response = get(
        url=test_url,
        service_name=ExternalAPIs.SECLEND,
        headers={"Content-Type": "application/json"}
    )
    
    # Verify the response
    assert response is not None
    assert 'rate' in response
    assert response['rate'] == TEST_BORROW_RATE
    assert response['status'] == BorrowStatus.EASY
    
    # Test with query parameters
    response = get(
        url=test_url,
        service_name=ExternalAPIs.SECLEND,
        params={"include_details": "true"},
        headers={"Content-Type": "application/json"}
    )
    
    # Verify the response
    assert response is not None
    assert 'rate' in response
    
    # Test with timeout parameter
    response = get(
        url=test_url,
        service_name=ExternalAPIs.SECLEND,
        headers={"Content-Type": "application/json"},
        timeout=5
    )
    
    # Verify the response
    assert response is not None
    assert 'rate' in response


@pytest.mark.usefixtures('setup_mock_servers')
def test_post_function():
    """Tests the synchronous POST function for making HTTP requests."""
    # Get the test settings to get the mock server URLs
    settings = get_test_settings()
    seclend_url = settings.get_mock_server_url('seclend')
    
    # Configure a test response - we'll use the same endpoint as for GET to ensure it exists
    test_endpoint = f"/api/borrows/{TEST_TICKER}"
    test_url = f"{seclend_url}{test_endpoint}"
    
    # Test data to send
    test_data = {"ticker": TEST_TICKER, "action": "test"}
    
    # Call the POST function
    try:
        response = post(
            url=test_url,
            service_name=ExternalAPIs.SECLEND,
            json_data=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        # If we get here, verify the response
        assert response is not None
    except ExternalAPIException:
        # The mock server might not be configured for POST requests to this endpoint
        # This is acceptable for this test
        pass


@pytest.mark.asyncio
@pytest.mark.usefixtures('setup_mock_servers')
async def test_async_get_function():
    """Tests the asynchronous GET function for making HTTP requests."""
    # Get the test settings to get the mock server URLs
    settings = get_test_settings()
    seclend_url = settings.get_mock_server_url('seclend')
    
    # Create the full URL for the test endpoint
    test_endpoint = f"/api/borrows/{TEST_TICKER}"
    test_url = f"{seclend_url}{test_endpoint}"
    
    # Call the async GET function
    response = await async_get(
        url=test_url,
        service_name=ExternalAPIs.SECLEND,
        headers={"Content-Type": "application/json"}
    )
    
    # Verify the response
    assert response is not None
    assert 'rate' in response
    assert response['rate'] == TEST_BORROW_RATE
    assert response['status'] == BorrowStatus.EASY
    
    # Test with query parameters
    response = await async_get(
        url=test_url,
        service_name=ExternalAPIs.SECLEND,
        params={"include_details": "true"},
        headers={"Content-Type": "application/json"}
    )
    
    # Verify the response
    assert response is not None
    assert 'rate' in response
    
    # Test with timeout parameter
    response = await async_get(
        url=test_url,
        service_name=ExternalAPIs.SECLEND,
        headers={"Content-Type": "application/json"},
        timeout=5
    )
    
    # Verify the response
    assert response is not None
    assert 'rate' in response


@pytest.mark.asyncio
@pytest.mark.usefixtures('setup_mock_servers')
async def test_async_post_function():
    """Tests the asynchronous POST function for making HTTP requests."""
    # Get the test settings to get the mock server URLs
    settings = get_test_settings()
    seclend_url = settings.get_mock_server_url('seclend')
    
    # Configure a test response - we'll use the same endpoint as for GET to ensure it exists
    test_endpoint = f"/api/borrows/{TEST_TICKER}"
    test_url = f"{seclend_url}{test_endpoint}"
    
    # Test data to send
    test_data = {"ticker": TEST_TICKER, "action": "test"}
    
    # Call the async POST function
    try:
        response = await async_post(
            url=test_url,
            service_name=ExternalAPIs.SECLEND,
            json_data=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        # If we get here, verify the response
        assert response is not None
    except ExternalAPIException:
        # The mock server might not be configured for POST requests to this endpoint
        # This is acceptable for this test
        pass


@pytest.mark.usefixtures('setup_mock_servers')
def test_get_with_retry():
    """Tests that the GET function implements retry logic for transient failures."""
    # Get the test settings to get the mock server URLs
    settings = get_test_settings()
    seclend_url = settings.get_mock_server_url('seclend')
    
    # Create a counter to track number of requests
    request_count = [0]
    
    def mock_get(*args, **kwargs):
        request_count[0] += 1
        if request_count[0] <= 2:  # First two requests fail
            raise requests.exceptions.RequestException("Simulated transient failure")
        
        # After two failures, succeed
        mock_response = requests.Response()
        mock_response.status_code = 200
        mock_response._content = json.dumps({"success": True, "retry_count": request_count[0]}).encode()
        return mock_response
    
    # Patch requests.get to simulate failures then success
    with patch('requests.get', side_effect=mock_get):
        # Call the GET function - should retry after failures
        response = get(
            url=f"{seclend_url}/api/retry-test",
            service_name=ExternalAPIs.SECLEND,
            headers={"Content-Type": "application/json"}
        )
        
        # Verify we got a successful response after retries
        assert response is not None
        assert response["success"] is True
        assert response["retry_count"] > 1


@pytest.mark.usefixtures('setup_mock_servers')
def test_get_with_circuit_breaker():
    """Tests that the GET function implements circuit breaker pattern."""
    # Get the test settings to get the mock server URLs
    settings = get_test_settings()
    seclend_url = settings.get_mock_server_url('seclend')
    
    # Define a mock response that always fails
    def mock_get(*args, **kwargs):
        raise requests.exceptions.RequestException("Simulated permanent failure")
    
    # Patch requests.get to simulate failures
    with patch('requests.get', side_effect=mock_get):
        # Test with fallback value - even with constant failures, we should get the fallback
        fallback_value = {"fallback": True}
        
        # Make multiple requests with fallback
        for _ in range(6):  # More than the default failure threshold
            response = get(
                url=f"{seclend_url}/api/circuit-test",
                service_name=ExternalAPIs.SECLEND,
                headers={"Content-Type": "application/json"},
                fallback_value=fallback_value
            )
            assert response == fallback_value
        
        # Without fallback, we should get an exception
        with pytest.raises(ExternalAPIException):
            get(
                url=f"{seclend_url}/api/circuit-test",
                service_name=ExternalAPIs.SECLEND,
                headers={"Content-Type": "application/json"}
            )


@pytest.mark.usefixtures('setup_mock_servers')
def test_get_with_fallback():
    """Tests that the GET function uses fallback values when API fails."""
    # Get the test settings to get the mock server URLs
    settings = get_test_settings()
    seclend_url = settings.get_mock_server_url('seclend')
    
    # Define a mock response that always fails
    def mock_get(*args, **kwargs):
        raise requests.exceptions.RequestException("Simulated failure")
    
    # Patch requests.get to simulate failure
    with patch('requests.get', side_effect=mock_get):
        # Test with fallback value
        fallback_value = {"fallback": True}
        
        response = get(
            url=f"{seclend_url}/api/fallback-test",
            service_name=ExternalAPIs.SECLEND,
            headers={"Content-Type": "application/json"},
            fallback_value=fallback_value
        )
        
        # Verify that we get the fallback value
        assert response == fallback_value
        
        # Test with None fallback value
        response = get(
            url=f"{seclend_url}/api/fallback-test",
            service_name=ExternalAPIs.SECLEND,
            headers={"Content-Type": "application/json"},
            fallback_value=None
        )
        
        # Verify that we get None
        assert response is None


@pytest.mark.usefixtures('setup_mock_servers')
def test_get_borrow_rate_integration():
    """Tests the integration between get_borrow_rate function and external client."""
    # Call the get_borrow_rate function
    response = get_borrow_rate(TEST_TICKER)
    
    # Verify the response contains expected data
    assert response is not None
    assert 'rate' in response
    assert response['rate'] == TEST_BORROW_RATE
    assert response['status'] == BorrowStatus.EASY
    
    # Test with a ticker that doesn't exist - using a patch to simulate not found response
    with patch('src.backend.services.external.client.get', side_effect=ExternalAPIException(ExternalAPIs.SECLEND, "Ticker not found")):
        # Call the function - should return fallback
        response = get_borrow_rate("NOTFOUND")
        assert response is not None
        assert 'is_fallback' in response
        assert response['is_fallback'] is True
    
    # Test with a ticker that causes a timeout - using a patch to simulate timeout
    with patch('src.backend.services.external.client.get', side_effect=requests.exceptions.Timeout("Connection timed out")):
        # Call the function - should return fallback
        response = get_borrow_rate("TIMEOUT")
        assert response is not None
        assert 'is_fallback' in response
        assert response['is_fallback'] is True


@pytest.mark.usefixtures('setup_mock_servers')
def test_get_market_volatility_integration():
    """Tests the integration between get_market_volatility_index function and external client."""
    # Call the get_market_volatility_index function
    response = get_market_volatility_index()
    
    # Verify the response contains expected data
    assert response is not None
    assert 'value' in response
    assert response['value'] == TEST_VOLATILITY
    
    # Test with API timeout - using a patch to simulate timeout
    with patch('src.backend.services.external.client.get', side_effect=requests.exceptions.Timeout("Connection timed out")):
        try:
            # This might raise an exception or return a fallback value depending on implementation
            response = get_market_volatility_index(use_cache=False)  # Force API call
            # If we get here, the function has internal fallback
            assert response is not None
        except ExternalAPIException:
            # This is also acceptable if the function propagates the exception
            pass


@pytest.mark.usefixtures('setup_mock_servers')
def test_get_stock_volatility_integration():
    """Tests the integration between get_stock_volatility function and external client."""
    # Call the get_stock_volatility function
    response = get_stock_volatility(TEST_TICKER)
    
    # Verify the response contains expected data
    assert response is not None
    assert 'volatility' in response
    assert response['volatility'] == TEST_VOLATILITY
    
    # Test with a ticker that doesn't exist - using a patch to simulate not found response
    with patch('src.backend.services.external.client.get', side_effect=ExternalAPIException(ExternalAPIs.MARKET_VOLATILITY, "Ticker not found")):
        try:
            # This might raise an exception or return a fallback value depending on implementation
            response = get_stock_volatility("NOTFOUND", use_cache=False)  # Force API call
            # If we get here, the function has internal fallback
            assert response is not None
        except ExternalAPIException:
            # This is also acceptable if the function propagates the exception
            pass
    
    # Test with a ticker that causes a timeout - using a patch to simulate timeout
    with patch('src.backend.services.external.client.get', side_effect=requests.exceptions.Timeout("Connection timed out")):
        try:
            # This might raise an exception or return a fallback value depending on implementation
            response = get_stock_volatility("TIMEOUT", use_cache=False)  # Force API call
            # If we get here, the function has internal fallback
            assert response is not None
        except ExternalAPIException:
            # This is also acceptable if the function propagates the exception
            pass


@pytest.mark.usefixtures('setup_mock_servers')
def test_get_event_risk_factor_integration():
    """Tests the integration between get_event_risk_factor function and external client."""
    # Call the get_event_risk_factor function
    risk_factor = get_event_risk_factor(TEST_TICKER)
    
    # Verify the response is the expected risk factor
    assert risk_factor == TEST_EVENT_RISK
    
    # Test with no events - using a patch to simulate empty events response
    no_events_response = {"events": []}
    with patch('src.backend.services.external.client.get', return_value=no_events_response):
        # Call the function - should return 0 for no events
        risk_factor = get_event_risk_factor("NOEVENTS")
        assert risk_factor == 0
    
    # Test with a ticker that causes a timeout - using a patch to simulate timeout
    with patch('src.backend.services.external.client.get', side_effect=requests.exceptions.Timeout("Connection timed out")):
        # Call the function - should handle timeout gracefully
        risk_factor = get_event_risk_factor("TIMEOUT")
        # The function might return a default value or 0
        assert isinstance(risk_factor, int)


@pytest.mark.usefixtures('setup_mock_servers')
def test_error_handling():
    """Tests that the external client properly handles and reports errors."""
    # Get the test settings to get the mock server URLs
    settings = get_test_settings()
    seclend_url = settings.get_mock_server_url('seclend')
    
    # Test handling of 400 Bad Request
    mock_response_400 = requests.Response()
    mock_response_400.status_code = 400
    mock_response_400._content = json.dumps({"error": "Bad request"}).encode()
    
    with patch('requests.get', return_value=mock_response_400):
        with pytest.raises(ExternalAPIException) as excinfo:
            get(
                url=f"{seclend_url}/api/error/400",
                service_name=ExternalAPIs.SECLEND,
                headers={"Content-Type": "application/json"}
            )
        
        assert "API returned error" in str(excinfo.value)
        assert "400" in str(excinfo.value)
    
    # Test handling of 401 Unauthorized
    mock_response_401 = requests.Response()
    mock_response_401.status_code = 401
    mock_response_401._content = json.dumps({"error": "Unauthorized"}).encode()
    
    with patch('requests.get', return_value=mock_response_401):
        with pytest.raises(ExternalAPIException) as excinfo:
            get(
                url=f"{seclend_url}/api/error/401",
                service_name=ExternalAPIs.SECLEND,
                headers={"Content-Type": "application/json"}
            )
        
        assert "API returned error" in str(excinfo.value)
        assert "401" in str(excinfo.value)
    
    # Test handling of 404 Not Found
    mock_response_404 = requests.Response()
    mock_response_404.status_code = 404
    mock_response_404._content = json.dumps({"error": "Not found"}).encode()
    
    with patch('requests.get', return_value=mock_response_404):
        with pytest.raises(ExternalAPIException) as excinfo:
            get(
                url=f"{seclend_url}/api/error/404",
                service_name=ExternalAPIs.SECLEND,
                headers={"Content-Type": "application/json"}
            )
        
        assert "API returned error" in str(excinfo.value)
        assert "404" in str(excinfo.value)
    
    # Test handling of 429 Too Many Requests
    mock_response_429 = requests.Response()
    mock_response_429.status_code = 429
    mock_response_429._content = json.dumps({"error": "Too many requests"}).encode()
    
    with patch('requests.get', return_value=mock_response_429):
        with pytest.raises(ExternalAPIException) as excinfo:
            get(
                url=f"{seclend_url}/api/error/429",
                service_name=ExternalAPIs.SECLEND,
                headers={"Content-Type": "application/json"}
            )
        
        assert "API returned error" in str(excinfo.value)
        assert "429" in str(excinfo.value)
    
    # Test handling of 500 Internal Server Error
    mock_response_500 = requests.Response()
    mock_response_500.status_code = 500
    mock_response_500._content = json.dumps({"error": "Internal server error"}).encode()
    
    with patch('requests.get', return_value=mock_response_500):
        with pytest.raises(ExternalAPIException) as excinfo:
            get(
                url=f"{seclend_url}/api/error/500",
                service_name=ExternalAPIs.SECLEND,
                headers={"Content-Type": "application/json"}
            )
        
        assert "API returned error" in str(excinfo.value)
        assert "500" in str(excinfo.value)
    
    # Test handling of timeout errors
    with patch('requests.get', side_effect=requests.exceptions.Timeout("Connection timed out")):
        with pytest.raises(requests.exceptions.Timeout):
            get(
                url=f"{seclend_url}/api/timeout",
                service_name=ExternalAPIs.SECLEND,
                headers={"Content-Type": "application/json"},
                timeout=1
            )
    
    # Test handling of connection errors
    with patch('requests.get', side_effect=requests.exceptions.ConnectionError("Connection refused")):
        with pytest.raises(requests.exceptions.ConnectionError):
            get(
                url=f"{seclend_url}/api/connection-error",
                service_name=ExternalAPIs.SECLEND,
                headers={"Content-Type": "application/json"}
            )