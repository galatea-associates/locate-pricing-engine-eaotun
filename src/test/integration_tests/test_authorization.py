"""
Integration tests for the authorization system of the Borrow Rate & Locate Fee Pricing Engine.
This module tests role-based access control, permission enforcement, and resource authorization
across different API endpoints to ensure that clients can only access resources they are authorized to use.
"""

import pytest
import requests
import logging
from decimal import Decimal

from .helpers.api_client import APIClient, create_api_client
from .config.settings import get_test_settings, TestSettings
from .fixtures.api_responses import ERROR_RESPONSES
from src.backend.core.constants import ErrorCodes

# Set up logger
logger = logging.getLogger(__name__)

# Test constants
TEST_TICKER = "AAPL"
TEST_POSITION_VALUE = Decimal('100000')
TEST_LOAN_DAYS = 30
TEST_CLIENT_ID = "test_client"
UNAUTHORIZED_CLIENT_ID = "unauthorized_client"


@pytest.fixture
def api_client():
    """
    Pytest fixture that provides a configured API client for tests
    """
    settings = get_test_settings()
    client = create_api_client(settings)
    yield client


@pytest.fixture
def unauthorized_api_client():
    """
    Pytest fixture that provides an API client with valid credentials but insufficient permissions
    """
    settings = get_test_settings()
    # Create a copy of settings
    unauthorized_settings = TestSettings()
    # Set an unauthorized client ID on the settings copy
    client = create_api_client(unauthorized_settings)
    # Override the API key to simulate a client with different permissions
    client._default_headers["X-API-Key"] = "unauthorized-api-key"
    yield client


def test_rate_endpoint_authorization(api_client, unauthorized_api_client):
    """
    Tests that clients can only access borrow rates for tickers they are authorized to view
    """
    # Authorized client should be able to access the rate
    response = api_client.get_borrow_rate(TEST_TICKER)
    assert response.status == "success"
    
    # Unauthorized client should receive a forbidden error
    response = unauthorized_api_client.get_borrow_rate(TEST_TICKER)
    assert response.get("error") == ErrorCodes.FORBIDDEN.value


def test_calculate_fee_authorization(api_client, unauthorized_api_client):
    """
    Tests that clients can only calculate fees for tickers they are authorized to use
    """
    # Authorized client should be able to calculate the fee
    response = api_client.calculate_locate_fee(
        ticker=TEST_TICKER,
        position_value=TEST_POSITION_VALUE,
        loan_days=TEST_LOAN_DAYS,
        client_id=TEST_CLIENT_ID
    )
    assert response.status == "success"
    
    # Unauthorized client should receive a forbidden error
    response = unauthorized_api_client.calculate_locate_fee(
        ticker=TEST_TICKER,
        position_value=TEST_POSITION_VALUE,
        loan_days=TEST_LOAN_DAYS,
        client_id=TEST_CLIENT_ID
    )
    assert response.get("error") == ErrorCodes.FORBIDDEN.value


def test_client_specific_data_access(api_client, unauthorized_api_client):
    """
    Tests that clients can only access their own broker configuration data
    """
    # Authorized client should be able to access their own data
    response = api_client.calculate_locate_fee(
        ticker=TEST_TICKER,
        position_value=TEST_POSITION_VALUE,
        loan_days=TEST_LOAN_DAYS,
        client_id=TEST_CLIENT_ID
    )
    assert response.status == "success"
    
    # Unauthorized client should not be able to access another client's data
    response = unauthorized_api_client.calculate_locate_fee(
        ticker=TEST_TICKER,
        position_value=TEST_POSITION_VALUE,
        loan_days=TEST_LOAN_DAYS,
        client_id=TEST_CLIENT_ID  # Trying to access another client's data
    )
    assert response.get("error") == ErrorCodes.FORBIDDEN.value


def test_role_based_access_control(api_client):
    """
    Tests that different client roles have appropriate access levels to API endpoints
    """
    settings = get_test_settings()
    
    # Create clients with different role-based API keys
    admin_client = create_api_client(settings)
    admin_client._default_headers["X-API-Key"] = "admin-api-key"
    
    regular_client = create_api_client(settings)
    regular_client._default_headers["X-API-Key"] = "client-api-key"
    
    auditor_client = create_api_client(settings)
    auditor_client._default_headers["X-API-Key"] = "auditor-api-key"
    
    # Test admin access (should have full access)
    admin_response = admin_client.get_borrow_rate(TEST_TICKER)
    assert admin_response.status == "success"
    
    admin_fee_response = admin_client.calculate_locate_fee(
        ticker=TEST_TICKER,
        position_value=TEST_POSITION_VALUE,
        loan_days=TEST_LOAN_DAYS,
        client_id=TEST_CLIENT_ID
    )
    assert admin_fee_response.status == "success"
    
    # Test regular client access (should have limited access)
    client_response = regular_client.get_borrow_rate(TEST_TICKER)
    assert client_response.status == "success"
    
    # Assume regular clients can't access other clients' data
    other_client_response = regular_client.calculate_locate_fee(
        ticker=TEST_TICKER,
        position_value=TEST_POSITION_VALUE,
        loan_days=TEST_LOAN_DAYS,
        client_id="different_client_id"
    )
    assert other_client_response.get("error") == ErrorCodes.FORBIDDEN.value
    
    # Test auditor access (should have read-only access)
    auditor_response = auditor_client.get_borrow_rate(TEST_TICKER)
    assert auditor_response.status == "success"
    
    # Assume auditors can't perform fee calculations
    auditor_fee_response = auditor_client.calculate_locate_fee(
        ticker=TEST_TICKER,
        position_value=TEST_POSITION_VALUE,
        loan_days=TEST_LOAN_DAYS,
        client_id=TEST_CLIENT_ID
    )
    assert auditor_fee_response.get("error") == ErrorCodes.FORBIDDEN.value


def test_direct_request_with_insufficient_permissions():
    """
    Tests that direct requests with insufficient permissions are rejected
    """
    settings = get_test_settings()
    api_url = f"{settings.get_api_url()}/rates/{TEST_TICKER}"
    
    # Make a direct request with valid but insufficient permissions API key
    headers = {"X-API-Key": "insufficient-permissions-key"}
    response = requests.get(api_url, headers=headers)
    
    # Should return 403 Forbidden
    assert response.status_code == 403
    
    # Response should contain the expected error
    error_data = response.json()
    assert error_data.get("error") == ErrorCodes.FORBIDDEN.value


def test_resource_level_authorization(api_client, unauthorized_api_client):
    """
    Tests that authorization is enforced at the resource level for specific tickers
    """
    # Authorized client with access to TEST_TICKER
    response = api_client.get_borrow_rate(TEST_TICKER)
    assert response.status == "success"
    
    # Authorized client without access to a specific ticker
    restricted_ticker = "RESTRICTED"
    response = api_client.get_borrow_rate(restricted_ticker)
    assert response.get("error") == ErrorCodes.FORBIDDEN.value
    
    # Same test with calculate_locate_fee endpoint
    response = api_client.calculate_locate_fee(
        ticker=TEST_TICKER,
        position_value=TEST_POSITION_VALUE,
        loan_days=TEST_LOAN_DAYS,
        client_id=TEST_CLIENT_ID
    )
    assert response.status == "success"
    
    response = api_client.calculate_locate_fee(
        ticker=restricted_ticker,
        position_value=TEST_POSITION_VALUE,
        loan_days=TEST_LOAN_DAYS,
        client_id=TEST_CLIENT_ID
    )
    assert response.get("error") == ErrorCodes.FORBIDDEN.value