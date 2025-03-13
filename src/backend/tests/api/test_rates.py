"""
Contains unit tests for the borrow rates API endpoints in the Borrow Rate & Locate Fee Pricing Engine.
These tests verify the functionality of retrieving current borrow rates for securities,
including proper error handling, authentication, and response formatting.
"""

import pytest  # version: 7.4.0+
import respx  # version: 0.20.0+
import httpx  # version: 0.25.0+
from decimal import Decimal  # standard library
from fastapi import status  # version: 0.103.0+

from ...schemas.response import BorrowRateResponse
from ...core.constants import BorrowStatus
from ..fixtures.stocks import (
    easy_to_borrow_stock,
    hard_to_borrow_stock,
    medium_to_borrow_stock,
    invalid_ticker,
    stock_with_volatility,
)
from ..fixtures.api_responses import (
    mock_seclend_response,
    mock_stock_volatility_response,
    mock_market_volatility_response,
    mock_event_calendar_response,
    mock_api_error_response,
)


def test_get_borrow_rate_success(
    api_client, easy_to_borrow_stock, test_api_key_header, test_db, seed_test_data
):
    """Tests successful retrieval of borrow rate for a valid ticker."""
    # Get ticker from easy_to_borrow_stock fixture
    ticker = easy_to_borrow_stock["ticker"]
    
    # Make GET request to /api/v1/rates/{ticker} with test API key header
    response = api_client.get(
        f"/api/v1/rates/{ticker}", 
        headers=test_api_key_header
    )
    
    # Assert response status code is 200
    assert response.status_code == status.HTTP_200_OK
    
    # Parse response JSON
    data = response.json()
    
    # Validate response against BorrowRateResponse schema
    response_model = BorrowRateResponse(**data)
    
    # Assert status is 'success'
    assert response_model.status == "success"
    # Assert ticker matches requested ticker
    assert response_model.ticker == ticker
    # Assert current_rate is a positive Decimal
    assert response_model.current_rate > Decimal('0')
    # Assert borrow_status is 'EASY'
    assert response_model.borrow_status == BorrowStatus.EASY.value


def test_get_borrow_rate_hard_to_borrow(
    api_client, hard_to_borrow_stock, test_api_key_header, test_db, seed_test_data
):
    """Tests retrieval of borrow rate for a hard-to-borrow stock."""
    # Get ticker from hard_to_borrow_stock fixture
    ticker = hard_to_borrow_stock["ticker"]
    
    # Make GET request to /api/v1/rates/{ticker} with test API key header
    response = api_client.get(
        f"/api/v1/rates/{ticker}", 
        headers=test_api_key_header
    )
    
    # Assert response status code is 200
    assert response.status_code == status.HTTP_200_OK
    
    # Parse response JSON
    data = response.json()
    
    # Validate response against BorrowRateResponse schema
    response_model = BorrowRateResponse(**data)
    
    # Assert status is 'success'
    assert response_model.status == "success"
    # Assert ticker matches requested ticker
    assert response_model.ticker == ticker
    # Assert current_rate is a positive Decimal
    assert response_model.current_rate > Decimal('0')
    # Assert current_rate is higher than for easy-to-borrow stocks
    assert response_model.current_rate > Decimal('0.1')
    # Assert borrow_status is 'HARD'
    assert response_model.borrow_status == BorrowStatus.HARD.value


def test_get_borrow_rate_with_volatility(
    api_client, stock_with_volatility, test_api_key_header, test_db, seed_test_data,
    mock_market_volatility_api, mock_seclend_api
):
    """Tests that borrow rate includes volatility adjustments when available."""
    # Get ticker from stock_with_volatility fixture
    ticker = stock_with_volatility["ticker"]
    
    # Make GET request to /api/v1/rates/{ticker} with test API key header
    response = api_client.get(
        f"/api/v1/rates/{ticker}", 
        headers=test_api_key_header
    )
    
    # Assert response status code is 200
    assert response.status_code == status.HTTP_200_OK
    
    # Parse response JSON
    data = response.json()
    
    # Validate response against BorrowRateResponse schema
    response_model = BorrowRateResponse(**data)
    
    # Assert status is 'success'
    assert response_model.status == "success"
    # Assert volatility_index is not None
    assert response_model.volatility_index is not None
    # Assert volatility_index is a positive Decimal
    assert response_model.volatility_index > Decimal('0')
    # Assert current_rate reflects volatility adjustment
    assert response_model.current_rate > Decimal(stock_with_volatility["min_borrow_rate"])


def test_get_borrow_rate_with_event_risk(
    api_client, stock_with_volatility, test_api_key_header, test_db, seed_test_data,
    mock_event_calendar_api, mock_seclend_api
):
    """Tests that borrow rate includes event risk adjustments when available."""
    # Get ticker from stock_with_volatility fixture
    ticker = stock_with_volatility["ticker"]
    
    # Make GET request to /api/v1/rates/{ticker} with test API key header
    response = api_client.get(
        f"/api/v1/rates/{ticker}", 
        headers=test_api_key_header
    )
    
    # Assert response status code is 200
    assert response.status_code == status.HTTP_200_OK
    
    # Parse response JSON
    data = response.json()
    
    # Validate response against BorrowRateResponse schema
    response_model = BorrowRateResponse(**data)
    
    # Assert status is 'success'
    assert response_model.status == "success"
    # Assert event_risk_factor is not None
    assert response_model.event_risk_factor is not None
    # Assert event_risk_factor is a non-negative integer
    assert response_model.event_risk_factor >= 0
    # Assert current_rate reflects event risk adjustment
    assert response_model.current_rate > Decimal(stock_with_volatility["min_borrow_rate"])


def test_get_borrow_rate_invalid_ticker(
    api_client, invalid_ticker, test_api_key_header, test_db, seed_test_data
):
    """Tests error handling for invalid ticker symbols."""
    # Make GET request to /api/v1/rates/{invalid_ticker} with test API key header
    response = api_client.get(
        f"/api/v1/rates/{invalid_ticker}", 
        headers=test_api_key_header
    )
    
    # Assert response status code is 404
    assert response.status_code == status.HTTP_404_NOT_FOUND
    
    # Parse response JSON
    data = response.json()
    
    # Assert status is 'error'
    assert data["status"] == "error"
    # Assert error message indicates ticker not found
    assert "ticker not found" in data["error"].lower() or "not found" in data["error"].lower()


def test_get_borrow_rate_unauthorized(
    api_client, easy_to_borrow_stock, test_db, seed_test_data
):
    """Tests authentication failure when API key is missing or invalid."""
    # Get ticker from easy_to_borrow_stock fixture
    ticker = easy_to_borrow_stock["ticker"]
    
    # Make GET request to /api/v1/rates/{ticker} without API key header
    response = api_client.get(f"/api/v1/rates/{ticker}")
    
    # Assert response status code is 401
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # Parse response JSON
    data = response.json()
    
    # Assert status is 'error'
    assert data["status"] == "error"
    # Assert error message indicates authentication failure
    assert any(term in data["error"].lower() for term in ["authentication", "unauthorized", "api key"])


def test_get_borrow_rate_external_api_failure(
    api_client, easy_to_borrow_stock, test_api_key_header, test_db, seed_test_data,
    mock_seclend_api
):
    """Tests fallback mechanism when external APIs are unavailable."""
    # Get ticker from easy_to_borrow_stock fixture
    ticker = easy_to_borrow_stock["ticker"]
    
    # Configure mock_seclend_api to return a 500 error
    mock_seclend_api.side_effect = httpx.HTTPStatusError(
        "Internal Server Error", 
        request=httpx.Request("GET", f"https://api.seclend.com/rates/{ticker}"),
        response=httpx.Response(status_code=500)
    )
    
    # Make GET request to /api/v1/rates/{ticker} with test API key header
    response = api_client.get(
        f"/api/v1/rates/{ticker}", 
        headers=test_api_key_header
    )
    
    # Assert response status code is 200 (fallback mechanism works)
    assert response.status_code == status.HTTP_200_OK
    
    # Parse response JSON
    data = response.json()
    
    # Validate response against BorrowRateResponse schema
    response_model = BorrowRateResponse(**data)
    
    # Assert status is 'success'
    assert response_model.status == "success"
    # Assert current_rate is equal to the minimum borrow rate from the database
    assert response_model.current_rate == Decimal(easy_to_borrow_stock["min_borrow_rate"])


def test_get_borrow_rates_by_status(
    api_client, test_api_key_header, test_db, seed_test_data
):
    """Tests retrieval of borrow rates filtered by borrow status."""
    # Make GET request to /api/v1/rates/status/EASY with test API key header
    response = api_client.get(
        "/api/v1/rates/status/EASY", 
        headers=test_api_key_header
    )
    
    # Assert response status code is 200
    assert response.status_code == status.HTTP_200_OK
    
    # Parse response JSON
    data = response.json()
    
    # Assert response is a list
    assert isinstance(data, list)
    # Assert all items in the list have borrow_status 'EASY'
    for item in data:
        assert item["borrow_status"] == BorrowStatus.EASY.value
    
    # Make GET request to /api/v1/rates/status/HARD with test API key header
    response = api_client.get(
        "/api/v1/rates/status/HARD", 
        headers=test_api_key_header
    )
    
    # Assert response status code is 200
    assert response.status_code == status.HTTP_200_OK
    
    # Parse response JSON
    data = response.json()
    
    # Assert response is a list
    assert isinstance(data, list)
    # Assert all items in the list have borrow_status 'HARD'
    for item in data:
        assert item["borrow_status"] == BorrowStatus.HARD.value


def test_calculate_custom_rate(
    api_client, easy_to_borrow_stock, test_api_key_header, test_db, seed_test_data
):
    """Tests calculation of custom borrow rate with specific parameters."""
    # Get ticker from easy_to_borrow_stock fixture
    ticker = easy_to_borrow_stock["ticker"]
    
    # Make GET request to /api/v1/rates/{ticker}/calculate with custom volatility_index and event_risk_factor parameters
    response = api_client.get(
        f"/api/v1/rates/{ticker}/calculate",
        params={
            "volatility_index": 25.0,
            "event_risk_factor": 5
        },
        headers=test_api_key_header
    )
    
    # Assert response status code is 200
    assert response.status_code == status.HTTP_200_OK
    
    # Parse response JSON
    data = response.json()
    
    # Validate response against BorrowRateResponse schema
    response_model = BorrowRateResponse(**data)
    
    # Assert status is 'success'
    assert response_model.status == "success"
    # Assert volatility_index matches the provided custom value
    assert response_model.volatility_index == Decimal('25.0')
    # Assert event_risk_factor matches the provided custom value
    assert response_model.event_risk_factor == 5
    # Assert current_rate reflects the custom parameters
    assert response_model.current_rate > Decimal(easy_to_borrow_stock["min_borrow_rate"])


def test_cache_usage(
    api_client, easy_to_borrow_stock, test_api_key_header, test_db, seed_test_data,
    mock_redis_cache, mock_seclend_api
):
    """Tests that the API uses cached values when available."""
    # Get ticker from easy_to_borrow_stock fixture
    ticker = easy_to_borrow_stock["ticker"]
    
    # Make first GET request to /api/v1/rates/{ticker} with test API key header
    response = api_client.get(
        f"/api/v1/rates/{ticker}", 
        headers=test_api_key_header
    )
    
    # Assert response status code is 200
    assert response.status_code == status.HTTP_200_OK
    
    # Verify that mock_seclend_api was called
    assert mock_seclend_api.called
    
    # Reset mock for the next request
    mock_seclend_api.reset()
    
    # Make second GET request to /api/v1/rates/{ticker} with test API key header
    response = api_client.get(
        f"/api/v1/rates/{ticker}", 
        headers=test_api_key_header
    )
    
    # Assert response status code is 200
    assert response.status_code == status.HTTP_200_OK
    
    # Verify that mock_seclend_api was not called again (cached value used)
    assert not mock_seclend_api.called
    
    # Make GET request to /api/v1/rates/{ticker}?use_cache=false with test API key header
    response = api_client.get(
        f"/api/v1/rates/{ticker}",
        params={"use_cache": "false"},
        headers=test_api_key_header
    )
    
    # Assert response status code is 200
    assert response.status_code == status.HTTP_200_OK
    
    # Verify that mock_seclend_api was called again (cache bypass)
    assert mock_seclend_api.called