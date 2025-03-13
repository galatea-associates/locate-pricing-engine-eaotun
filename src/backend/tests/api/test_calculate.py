"""
Unit tests for the calculate API endpoint in the Borrow Rate & Locate Fee Pricing Engine.
This module tests the functionality of the locate fee calculation endpoint, including
successful calculations, error handling, parameter validation, and fallback mechanisms.
"""

import json  # standard library
from decimal import Decimal  # standard library

import pytest  # pytest 7.0.0+
import httpx  # httpx 0.25.0+
import respx  # respx 0.20.0+

from ..conftest import (  # src/backend/tests/conftest.py
    api_client,
    test_db,
    mock_redis_cache,
    mock_external_apis,
    seed_test_data,
    test_calculation_inputs,
    test_api_key_header
)
from ..fixtures.stocks import (  # src/backend/tests/fixtures/stocks.py
    easy_to_borrow_stock,
    hard_to_borrow_stock,
    invalid_ticker
)
from ..fixtures.brokers import (  # src/backend/tests/fixtures/brokers.py
    standard_broker,
    premium_broker,
    invalid_client_id
)
from ..fixtures.api_responses import mock_seclend_response, mock_api_error_response  # src/backend/tests/fixtures/api_responses.py
from ...schemas.request import CalculateLocateRequest  # src/backend/schemas/request.py
from ...schemas.response import CalculateLocateResponse  # src/backend/schemas/response.py
from ...schemas.calculation import FeeBreakdownSchema  # src/backend/schemas/calculation.py
from ...core.constants import ErrorCodes  # src/backend/core/constants.py


@pytest.mark.parametrize('method', ['GET', 'POST'])
def test_calculate_locate_fee_success(api_client: httpx.Client, test_calculation_inputs: dict, test_api_key_header: dict, test_db, seed_test_data):
    """Tests successful calculation of locate fee with valid parameters"""
    # Extract parameters from test_calculation_inputs
    ticker = test_calculation_inputs['ticker']
    position_value = test_calculation_inputs['position_value']
    loan_days = test_calculation_inputs['loan_days']
    client_id = test_calculation_inputs['client_id']

    # Make request to /api/v1/calculate-locate endpoint using specified method
    if method == 'GET':
        response = api_client.get(f"/api/v1/calculate-locate?ticker={ticker}&position_value={position_value}&loan_days={loan_days}&client_id={client_id}", headers=test_api_key_header)
    else:  # POST
        response = api_client.post("/api/v1/calculate-locate", json=test_calculation_inputs, headers=test_api_key_header)

    # Assert response status code is 200
    assert response.status_code == 200

    # Parse response JSON
    response_json = response.json()

    # Assert response status is 'success'
    assert response_json['status'] == 'success'

    # Assert total_fee is a positive Decimal
    total_fee = Decimal(str(response_json['total_fee']))
    assert total_fee > 0

    # Assert breakdown contains expected components (borrow_cost, markup, transaction_fees)
    breakdown = response_json['breakdown']
    assert 'borrow_cost' in breakdown
    assert 'markup' in breakdown
    assert 'transaction_fees' in breakdown

    # Assert borrow_rate_used is a positive Decimal
    borrow_rate_used = Decimal(str(response_json['borrow_rate_used']))
    assert borrow_rate_used > 0

    # Assert all fee components are positive Decimal values
    borrow_cost = Decimal(str(breakdown['borrow_cost']))
    markup = Decimal(str(breakdown['markup']))
    transaction_fees = Decimal(str(breakdown['transaction_fees']))
    assert borrow_cost >= 0
    assert markup >= 0
    assert transaction_fees >= 0


def test_calculate_locate_fee_with_hard_to_borrow(api_client: httpx.Client, hard_to_borrow_stock: dict, standard_broker: dict, test_api_key_header: dict, test_db, seed_test_data):
    """Tests calculation of locate fee with a hard-to-borrow stock"""
    # Create request parameters with hard-to-borrow stock ticker
    request_params = {
        "ticker": hard_to_borrow_stock['ticker'],
        "position_value": 10000,
        "loan_days": 30,
        "client_id": standard_broker['client_id']
    }

    # Make POST request to /api/v1/calculate-locate endpoint
    response = api_client.post("/api/v1/calculate-locate", json=request_params, headers=test_api_key_header)

    # Assert response status code is 200
    assert response.status_code == 200

    # Parse response JSON
    response_json = response.json()

    # Assert response status is 'success'
    assert response_json['status'] == 'success'

    # Assert borrow_rate_used is higher than for easy-to-borrow stocks
    borrow_rate_used = Decimal(str(response_json['borrow_rate_used']))
    assert borrow_rate_used > 0.05  # Assuming easy-to-borrow is around 5%

    # Assert total_fee is higher than for easy-to-borrow stocks
    total_fee = Decimal(str(response_json['total_fee']))
    assert total_fee > 100  # Assuming a reasonable fee


def test_calculate_locate_fee_with_premium_broker(api_client: httpx.Client, easy_to_borrow_stock: dict, premium_broker: dict, test_api_key_header: dict, test_db, seed_test_data):
    """Tests calculation of locate fee with a premium broker using percentage fees"""
    # Create request parameters with premium broker client_id
    request_params = {
        "ticker": easy_to_borrow_stock['ticker'],
        "position_value": 10000,
        "loan_days": 30,
        "client_id": premium_broker['client_id']
    }

    # Make POST request to /api/v1/calculate-locate endpoint
    response = api_client.post("/api/v1/calculate-locate", json=request_params, headers=test_api_key_header)

    # Assert response status code is 200
    assert response.status_code == 200

    # Parse response JSON
    response_json = response.json()

    # Assert response status is 'success'
    assert response_json['status'] == 'success'

    # Assert breakdown.transaction_fees is calculated as a percentage of position_value
    breakdown = response_json['breakdown']
    transaction_fees = Decimal(str(breakdown['transaction_fees']))
    expected_transaction_fees = request_params['position_value'] * premium_broker['transaction_amount'] / 100
    assert transaction_fees == pytest.approx(expected_transaction_fees)

    # Assert total_fee includes the percentage-based transaction fee
    total_fee = Decimal(str(response_json['total_fee']))
    assert total_fee > 0


def test_calculate_locate_fee_invalid_ticker(api_client: httpx.Client, invalid_ticker: str, test_calculation_inputs: dict, test_api_key_header: dict, test_db, seed_test_data):
    """Tests error handling for invalid ticker parameter"""
    # Create request parameters with invalid ticker
    request_params = test_calculation_inputs.copy()
    request_params['ticker'] = invalid_ticker

    # Make POST request to /api/v1/calculate-locate endpoint
    response = api_client.post("/api/v1/calculate-locate", json=request_params, headers=test_api_key_header)

    # Assert response status code is 400
    assert response.status_code == 400

    # Parse response JSON
    response_json = response.json()

    # Assert response status is 'error'
    assert response_json['status'] == 'error'

    # Assert error code is INVALID_PARAMETER
    assert response_json['error'].startswith("Invalid parameter")

    # Assert error message mentions 'ticker'
    assert 'ticker' in response_json['error']


@pytest.mark.parametrize('position_value', [-1000, 0, 'invalid'])
def test_calculate_locate_fee_invalid_position_value(api_client: httpx.Client, test_calculation_inputs: dict, test_api_key_header: dict, test_db, seed_test_data, position_value):
    """Tests error handling for invalid position_value parameter"""
    # Create request parameters with invalid position_value
    request_params = test_calculation_inputs.copy()
    request_params['position_value'] = position_value

    # Make POST request to /api/v1/calculate-locate endpoint
    response = api_client.post("/api/v1/calculate-locate", json=request_params, headers=test_api_key_header)

    # Assert response status code is 400
    assert response.status_code == 400

    # Parse response JSON
    response_json = response.json()

    # Assert response status is 'error'
    assert response_json['status'] == 'error'

    # Assert error code is INVALID_PARAMETER
    assert response_json['error'].startswith("Invalid parameter")

    # Assert error message mentions 'position_value'
    assert 'position_value' in response_json['error']


@pytest.mark.parametrize('loan_days', [-1, 0, 'invalid'])
def test_calculate_locate_fee_invalid_loan_days(api_client: httpx.Client, test_calculation_inputs: dict, test_api_key_header: dict, test_db, seed_test_data, loan_days):
    """Tests error handling for invalid loan_days parameter"""
    # Create request parameters with invalid loan_days
    request_params = test_calculation_inputs.copy()
    request_params['loan_days'] = loan_days

    # Make POST request to /api/v1/calculate-locate endpoint
    response = api_client.post("/api/v1/calculate-locate", json=request_params, headers=test_api_key_header)

    # Assert response status code is 400
    assert response.status_code == 400

    # Parse response JSON
    response_json = response.json()

    # Assert response status is 'error'
    assert response_json['status'] == 'error'

    # Assert error code is INVALID_PARAMETER
    assert response_json['error'].startswith("Invalid parameter")

    # Assert error message mentions 'loan_days'
    assert 'loan_days' in response_json['error']


def test_calculate_locate_fee_invalid_client_id(api_client: httpx.Client, invalid_client_id: str, test_calculation_inputs: dict, test_api_key_header: dict, test_db, seed_test_data):
    """Tests error handling for invalid client_id parameter"""
    # Create request parameters with invalid client_id
    request_params = test_calculation_inputs.copy()
    request_params['client_id'] = invalid_client_id

    # Make POST request to /api/v1/calculate-locate endpoint
    response = api_client.post("/api/v1/calculate-locate", json=request_params, headers=test_api_key_header)

    # Assert response status code is 404
    assert response.status_code == 404

    # Parse response JSON
    response_json = response.json()

    # Assert response status is 'error'
    assert response_json['status'] == 'error'

    # Assert error code is CLIENT_NOT_FOUND
    assert response_json['error'].startswith("Client ID")

    # Assert error message mentions 'client'
    assert 'client' in response_json['error']


@pytest.mark.parametrize('missing_param', ['ticker', 'position_value', 'loan_days', 'client_id'])
def test_calculate_locate_fee_missing_parameters(api_client: httpx.Client, test_api_key_header: dict, missing_param):
    """Tests error handling for missing required parameters"""
    # Create request parameters with one parameter missing
    request_params = {
        "ticker": "AAPL",
        "position_value": 10000,
        "loan_days": 30,
        "client_id": "xyz123"
    }
    del request_params[missing_param]

    # Make POST request to /api/v1/calculate-locate endpoint
    response = api_client.post("/api/v1/calculate-locate", json=request_params, headers=test_api_key_header)

    # Assert response status code is 422 (Unprocessable Entity)
    assert response.status_code == 422

    # Parse response JSON
    response_json = response.json()

    # Assert response contains validation error for missing parameter
    assert "detail" in response_json
    assert isinstance(response_json["detail"], list)
    assert len(response_json["detail"]) > 0
    assert response_json["detail"][0]["loc"][1] == missing_param


def test_calculate_locate_fee_external_api_failure(api_client: httpx.Client, test_calculation_inputs: dict, test_api_key_header: dict, test_db, seed_test_data, mock_external_apis: respx.MockRouter):
    """Tests fallback mechanism when external API fails"""
    # Configure mock_external_apis to simulate SecLend API failure
    seclend_url = "https://api.seclend.com/borrow/AAPL"
    mock_external_apis.get(seclend_url).mock(side_effect=Exception("Simulated API failure"))

    # Create request parameters
    request_params = test_calculation_inputs

    # Make POST request to /api/v1/calculate-locate endpoint
    response = api_client.post("/api/v1/calculate-locate", json=request_params, headers=test_api_key_header)

    # Assert response status code is 200 (fallback mechanism should handle the failure)
    assert response.status_code == 200

    # Parse response JSON
    response_json = response.json()

    # Assert response status is 'success'
    assert response_json['status'] == 'success'

    # Assert calculation was performed using fallback borrow rate
    borrow_rate_used = Decimal(str(response_json['borrow_rate_used']))
    assert borrow_rate_used > 0


def test_calculate_locate_fee_cache_hit(api_client: httpx.Client, test_calculation_inputs: dict, test_api_key_header: dict, test_db, seed_test_data, mock_redis_cache, mock_external_apis: respx.MockRouter):
    """Tests that calculation results are cached and reused"""
    # Make first request to /api/v1/calculate-locate endpoint
    first_response = api_client.post("/api/v1/calculate-locate", json=test_calculation_inputs, headers=test_api_key_header)

    # Assert response status code is 200
    assert first_response.status_code == 200

    # Store first response
    first_response_json = first_response.json()

    # Configure mock_external_apis to track API calls
    seclend_url = "https://api.seclend.com/borrow/AAPL"
    market_volatility_url = "https://api.marketvolatility.com/market/volatility/index"
    mock_external_apis.get(seclend_url).pass_through()
    mock_external_apis.get(market_volatility_url).pass_through()

    # Make second identical request
    second_response = api_client.post("/api/v1/calculate-locate", json=test_calculation_inputs, headers=test_api_key_header)

    # Assert response status code is 200
    assert second_response.status_code == 200

    # Assert second response matches first response
    second_response_json = second_response.json()
    assert second_response_json == first_response_json

    # Assert external APIs were not called for the second request (cache hit)
    assert mock_external_apis.get(seclend_url).call_count == 0
    assert mock_external_apis.get(market_volatility_url).call_count == 0


def test_calculate_locate_fee_unauthorized(api_client: httpx.Client, test_calculation_inputs: dict):
    """Tests authentication failure when API key is missing or invalid"""
    # Make request to /api/v1/calculate-locate endpoint without API key header
    response = api_client.post("/api/v1/calculate-locate", json=test_calculation_inputs)

    # Assert response status code is 401 (Unauthorized)
    assert response.status_code == 401

    # Parse response JSON
    response_json = response.json()

    # Assert response contains authentication error message
    assert "detail" in response_json
    assert response_json["detail"] == "Not authenticated"