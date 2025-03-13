"""
Integration tests for the API Gateway component of the Borrow Rate & Locate Fee Pricing Engine.
Tests the API endpoints, authentication, rate limiting, error handling, and integration with external services.
"""

import pytest  # version: 7.4.0+
import requests  # version: 2.28.0+
import time  # standard library
import logging  # standard library
from decimal import Decimal  # standard library
from typing import Tuple  # standard library

from .helpers.api_client import APIClient, create_api_client
from .helpers.assertions import Assertions
from .config.settings import get_test_settings
from .helpers.mock_server import (
    SecLendMockServer,
    MarketApiMockServer,
    EventApiMockServer,
    MockServerContext
)
from .fixtures.api_responses import (
    SECLEND_API_RESPONSES,
    MARKET_API_RESPONSES,
    EVENT_API_RESPONSES
)
from .fixtures.stocks import TEST_STOCKS
from .fixtures.brokers import TEST_BROKERS

# Configure logger
logger = logging.getLogger(__name__)

# Default timeout for tests
TEST_TIMEOUT = 30


def setup_mock_servers() -> Tuple[SecLendMockServer, MarketApiMockServer, EventApiMockServer]:
    """
    Sets up mock servers for external APIs with default responses
    
    Returns:
        Tuple of mock server instances (seclend, market, event)
    """
    # Create mock server instances
    seclend_server = SecLendMockServer()
    market_server = MarketApiMockServer()
    event_server = EventApiMockServer()
    
    # Start the mock servers
    seclend_server.start()
    market_server.start()
    event_server.start()
    
    # Configure default responses for each server
    # SecLend API - configure rates for test stocks
    for stock in TEST_STOCKS:
        ticker = stock['ticker']
        borrow_status = stock['borrow_status'].value
        min_rate = stock['min_borrow_rate']
        seclend_server.configure_borrow_rate(ticker, min_rate * Decimal('1.5'), borrow_status)
    
    # Market API - configure volatility for test stocks
    for vol_data in TEST_STOCKS:
        ticker = vol_data['ticker']
        market_server.configure_volatility(ticker, Decimal('20.0'))
    
    # Event API - configure event risk for test stocks
    for stock in TEST_STOCKS:
        ticker = stock['ticker']
        event_server.configure_event_risk(ticker, 2)
    
    return seclend_server, market_server, event_server


@pytest.fixture
def api_client() -> APIClient:
    """
    Fixture that provides an APIClient instance for tests
    
    Returns:
        Configured API client for testing
    """
    # Create API client using the factory function
    client = create_api_client()
    
    # Wait for API to be ready
    client.wait_for_api_ready()
    
    # Return the client for test use
    return client


@pytest.fixture
def assertions() -> Assertions:
    """
    Fixture that provides an Assertions instance for response validation
    
    Returns:
        Assertions helper for validating API responses
    """
    return Assertions()


@pytest.fixture
def mock_servers() -> Tuple[SecLendMockServer, MarketApiMockServer, EventApiMockServer]:
    """
    Fixture that provides mock servers for external APIs
    
    Returns:
        Tuple of mock server instances (seclend, market, event)
    """
    # Check if mock servers should be used
    settings = get_test_settings()
    if not settings.use_mock_servers:
        # Return None values if mock servers are not enabled
        yield None, None, None
        return
    
    # Setup mock servers
    seclend_server, market_server, event_server = setup_mock_servers()
    
    # Yield the servers for test use
    yield seclend_server, market_server, event_server
    
    # Stop the servers after tests
    seclend_server.stop()
    market_server.stop()
    event_server.stop()


def test_api_health_check(api_client: APIClient, assertions: Assertions):
    """
    Tests that the API health check endpoint returns a healthy status
    """
    # Call the health check endpoint
    response = api_client.health_check()
    
    # Validate the response
    assertions.assert_health_check(response)
    
    # Verify that all components are reported as healthy
    assert response.status == "healthy", f"Expected status 'healthy', got '{response.status}'"
    assert all(status == "connected" or status == "available" for status in response.components.values()), \
        f"Not all components are healthy: {response.components}"


def test_api_authentication():
    """
    Tests that the API requires valid authentication
    """
    # Create client with invalid API key
    invalid_settings = get_test_settings()
    invalid_settings.test_api_key = "invalid-api-key"
    invalid_client = create_api_client(invalid_settings)
    
    # Make request with invalid key - should fail
    response = invalid_client.request("GET", "/health")
    assert response.status_code == 401, f"Expected 401 Unauthorized, got {response.status_code}"
    
    # Create client with valid API key
    valid_client = create_api_client()
    
    # Make request with valid key - should succeed
    response = valid_client.request("GET", "/health")
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"


@pytest.mark.slow
def test_rate_limiting(api_client: APIClient):
    """
    Tests that the API enforces rate limits
    """
    # Make rapid requests to exceed rate limit
    responses = []
    for _ in range(100):  # Attempt to exceed the default rate limit
        responses.append(api_client.get("/rates/AAPL"))
        if responses[-1].status_code == 429:
            break
    
    # Verify that a 429 Too Many Requests response was received
    assert any(r.status_code == 429 for r in responses), \
        "Rate limit was not enforced, no 429 response received"
    
    # Find the 429 response
    rate_limited_response = next(r for r in responses if r.status_code == 429)
    
    # Verify that Retry-After header is present
    assert "Retry-After" in rate_limited_response.headers, \
        "Retry-After header missing in rate limit response"
    
    # Wait for the rate limit to reset
    retry_after = int(rate_limited_response.headers["Retry-After"])
    time.sleep(retry_after + 1)
    
    # Verify that requests succeed after waiting
    response = api_client.get("/rates/AAPL")
    assert response.status_code == 200, \
        f"Request after waiting still failed: {response.status_code}"


def test_calculate_locate_fee_success(api_client: APIClient, assertions: Assertions):
    """
    Tests successful calculation of locate fee
    """
    # Call the calculate locate fee endpoint with valid parameters
    response = api_client.calculate_locate_fee(
        ticker="AAPL",
        position_value=100000,
        loan_days=30,
        client_id="standard_broker"
    )
    
    # Validate the response
    assertions.assert_calculation_result(response)
    
    # Verify total fee, breakdown, and borrow rate are present and correct
    assert response.total_fee > 0, f"Expected positive total fee, got {response.total_fee}"
    assert response.breakdown is not None, "Fee breakdown missing in response"
    assert response.borrow_rate_used > 0, f"Expected positive borrow rate, got {response.borrow_rate_used}"
    
    # Verify breakdown sums to total fee (allowing for small rounding differences)
    breakdown_sum = sum([
        response.breakdown.borrow_cost,
        response.breakdown.markup,
        response.breakdown.transaction_fees
    ])
    assert abs(breakdown_sum - response.total_fee) < Decimal('0.02'), \
        f"Fee breakdown sum ({breakdown_sum}) doesn't match total fee ({response.total_fee})"


def test_calculate_locate_fee_invalid_parameters(api_client: APIClient, assertions: Assertions):
    """
    Tests validation of invalid parameters in locate fee calculation
    """
    # Test with invalid position_value (negative)
    response = api_client.post(
        "/calculate-locate",
        json_data={
            "ticker": "AAPL",
            "position_value": -100000,
            "loan_days": 30,
            "client_id": "standard_broker"
        }
    )
    assertions.assert_validation_error(response, "position_value")
    
    # Test with invalid loan_days (zero)
    response = api_client.post(
        "/calculate-locate",
        json_data={
            "ticker": "AAPL",
            "position_value": 100000,
            "loan_days": 0,
            "client_id": "standard_broker"
        }
    )
    assertions.assert_validation_error(response, "loan_days")
    
    # Test with invalid ticker (empty)
    response = api_client.post(
        "/calculate-locate",
        json_data={
            "ticker": "",
            "position_value": 100000,
            "loan_days": 30,
            "client_id": "standard_broker"
        }
    )
    assertions.assert_validation_error(response, "ticker")


def test_calculate_locate_fee_ticker_not_found(
    api_client: APIClient,
    assertions: Assertions,
    mock_servers: Tuple[SecLendMockServer, MarketApiMockServer, EventApiMockServer]
):
    """
    Tests error handling when ticker is not found
    """
    # Unpack mock servers
    seclend_server, _, _ = mock_servers
    
    # Configure SecLend mock server to return ticker not found
    if seclend_server:
        seclend_server.configure_ticker_not_found("NONEXISTENT")
    
    # Call the calculate locate fee endpoint with non-existent ticker
    response = api_client.post(
        "/calculate-locate",
        json_data={
            "ticker": "NONEXISTENT",
            "position_value": 100000,
            "loan_days": 30,
            "client_id": "standard_broker"
        }
    )
    
    # Validate the response
    assertions.assert_ticker_not_found(response, "NONEXISTENT")


def test_calculate_locate_fee_client_not_found(api_client: APIClient, assertions: Assertions):
    """
    Tests error handling when client is not found
    """
    # Call the calculate locate fee endpoint with non-existent client_id
    response = api_client.post(
        "/calculate-locate",
        json_data={
            "ticker": "AAPL",
            "position_value": 100000,
            "loan_days": 30,
            "client_id": "nonexistent_client"
        }
    )
    
    # Validate the response
    assertions.assert_client_not_found(response, "nonexistent_client")


def test_get_borrow_rate_success(api_client: APIClient, assertions: Assertions):
    """
    Tests successful retrieval of borrow rate
    """
    # Call the get borrow rate endpoint with valid ticker
    response = api_client.get_borrow_rate("AAPL")
    
    # Validate the response
    assertions.assert_rate_response(response, "AAPL")
    
    # Verify ticker, current_rate, and borrow_status are present and correct
    assert response.current_rate > 0, f"Expected positive borrow rate, got {response.current_rate}"
    assert response.borrow_status in ["EASY", "MEDIUM", "HARD"], \
        f"Unexpected borrow status: {response.borrow_status}"
    assert response.last_updated is not None, "Missing last_updated timestamp"


def test_get_borrow_rate_ticker_not_found(
    api_client: APIClient,
    assertions: Assertions,
    mock_servers: Tuple[SecLendMockServer, MarketApiMockServer, EventApiMockServer]
):
    """
    Tests error handling when ticker is not found for borrow rate
    """
    # Unpack mock servers
    seclend_server, _, _ = mock_servers
    
    # Configure SecLend mock server to return ticker not found
    if seclend_server:
        seclend_server.configure_ticker_not_found("NONEXISTENT")
    
    # Call the get borrow rate endpoint with non-existent ticker
    response = api_client.get("/rates/NONEXISTENT")
    
    # Validate the response
    assertions.assert_ticker_not_found(response, "NONEXISTENT")


def test_external_api_fallback(
    api_client: APIClient,
    assertions: Assertions,
    mock_servers: Tuple[SecLendMockServer, MarketApiMockServer, EventApiMockServer]
):
    """
    Tests fallback mechanism when external APIs are unavailable
    """
    # Unpack mock servers
    seclend_server, _, _ = mock_servers
    
    # Configure SecLend mock server to timeout
    if seclend_server:
        seclend_server.configure_timeout("AAPL")
    
    # Call the calculate locate fee endpoint with valid parameters
    response = api_client.calculate_locate_fee(
        ticker="AAPL",
        position_value=100000,
        loan_days=30,
        client_id="standard_broker"
    )
    
    # Verify that calculation still succeeds using fallback data
    if isinstance(response, dict):
        assert response.get('status') == 'success', f"Expected status 'success', got '{response.get('status')}'"
        # Verify warning about fallback data is present
        assert 'using_fallback_data' in response or 'warning' in response, \
            "Response should indicate fallback data was used"
    else:
        assert response.status == 'success', f"Expected status 'success', got '{response.status}'"
        # Verify that response includes a warning about using fallback data
        assert hasattr(response, 'using_fallback_data') or hasattr(response, 'warning'), \
            "Response should indicate fallback data was used"


def test_all_external_apis_unavailable(
    api_client: APIClient,
    assertions: Assertions,
    mock_servers: Tuple[SecLendMockServer, MarketApiMockServer, EventApiMockServer]
):
    """
    Tests error handling when all external APIs are unavailable
    """
    # Unpack mock servers
    seclend_server, market_server, event_server = mock_servers
    
    # Configure all mock servers to timeout
    if all([seclend_server, market_server, event_server]):
        seclend_server.configure_timeout("AAPL")
        market_server.configure_timeout("AAPL")
        event_server.configure_timeout("AAPL")
    
    # Call the calculate locate fee endpoint with valid parameters
    response = api_client.post(
        "/calculate-locate",
        json_data={
            "ticker": "AAPL",
            "position_value": 100000,
            "loan_days": 30,
            "client_id": "standard_broker"
        }
    )
    
    # Validate that the response indicates external API unavailable
    assertions.assert_external_api_unavailable(response)


def test_api_versioning():
    """
    Tests API versioning support
    """
    # Create APIClient with explicit API version v1
    settings = get_test_settings()
    settings.api_version = "v1"
    v1_client = create_api_client(settings)
    
    # Verify that requests succeed with correct version
    response = v1_client.health_check()
    if isinstance(response, dict):
        assert response.get('status') == 'healthy', f"Expected status 'healthy', got '{response.get('status')}'"
    else:
        assert response.status == 'healthy', f"Expected status 'healthy', got '{response.status}'"
    
    # Create APIClient with invalid API version
    settings.api_version = "v999"
    invalid_version_client = create_api_client(settings)
    
    # Verify that requests fail with appropriate error
    response = invalid_version_client.request("GET", "/health")
    assert response.status_code in [404, 400], \
        f"Expected 404 Not Found or 400 Bad Request for invalid API version, got {response.status_code}"