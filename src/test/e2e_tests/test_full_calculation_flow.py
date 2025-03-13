"""
End-to-end test module that verifies the complete calculation flow of the Borrow Rate & Locate Fee Pricing Engine.
Tests the entire process from retrieving borrow rates to calculating locate fees with various market conditions
and client configurations.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional

import pytest

from .config.settings import get_test_settings, TestEnvironment
from .helpers.api_client import APIClient, create_api_client
from .helpers.validation import ResponseValidator, create_response_validator
from .helpers.test_data import get_test_scenario, calculate_expected_fee
from .fixtures.environment import environment
from .fixtures.test_data import (
    test_data_manager, normal_market_scenario, high_volatility_scenario,
    corporate_event_scenario, hard_to_borrow_scenario, long_term_loan_scenario
)
from src.backend.schemas.response import CalculateLocateResponse, BorrowRateResponse

# Configure logger
logger = logging.getLogger(__name__)


def setup_module():
    """Setup function that runs once before all tests in the module."""
    logger.info("Starting end-to-end tests for the Borrow Rate & Locate Fee Pricing Engine")
    settings = get_test_settings()
    api_client = create_api_client()
    api_client.wait_for_api_ready()
    logger.info("End-to-end test setup complete")


def teardown_module():
    """Teardown function that runs once after all tests in the module."""
    logger.info("End-to-end tests completed")


@pytest.mark.e2e
def test_api_health(environment):
    """Tests that the API is healthy and responding correctly."""
    logger.info("Testing API health")
    api_client = create_api_client()
    response = api_client.health_check()
    
    assert response.status == "healthy"
    assert "version" in response.__dict__
    assert "components" in response.__dict__
    assert "timestamp" in response.__dict__
    
    logger.info("API health test passed")


@pytest.mark.e2e
def test_get_borrow_rate(environment):
    """Tests retrieving borrow rates for different securities."""
    logger.info("Testing borrow rate retrieval")
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Test stocks with different characteristics
    test_stocks = ["AAPL", "GME", "TSLA"]
    
    for ticker in test_stocks:
        logger.info(f"Testing borrow rate for {ticker}")
        response = api_client.get_borrow_rate(ticker)
        
        assert response.status == "success"
        assert response.ticker == ticker
        assert isinstance(response.current_rate, Decimal)
        
        # For AAPL (normal market), do additional validation with expected rate
        if ticker == "AAPL":
            validator.assert_borrow_rate(ticker)
    
    logger.info("Borrow rate tests passed")


@pytest.mark.e2e
def test_calculate_locate_fee_normal_market(environment, normal_market_scenario):
    """Tests fee calculation under normal market conditions."""
    logger.info("Testing fee calculation under normal market conditions")
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Extract parameters from scenario
    ticker = normal_market_scenario["ticker"]
    position_value = normal_market_scenario["position_value"]
    loan_days = normal_market_scenario["loan_days"]
    client_id = normal_market_scenario["client_id"]
    
    # Call API to calculate fee
    response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    # Assert basic response properties
    assert response.status == "success"
    
    # Use validator to verify calculation against expected result
    validator.assert_calculation(normal_market_scenario)
    
    logger.info("Normal market fee calculation test passed")


@pytest.mark.e2e
def test_calculate_locate_fee_high_volatility(environment, high_volatility_scenario):
    """Tests fee calculation under high volatility conditions."""
    logger.info("Testing fee calculation under high volatility conditions")
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Extract parameters from scenario
    ticker = high_volatility_scenario["ticker"]
    position_value = high_volatility_scenario["position_value"]
    loan_days = high_volatility_scenario["loan_days"]
    client_id = high_volatility_scenario["client_id"]
    
    # Call API to calculate fee
    response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    # Assert basic response properties
    assert response.status == "success"
    
    # Use validator to verify calculation against expected result
    validator.assert_calculation(high_volatility_scenario)
    
    # Verify that borrow rate is higher due to volatility
    # We can get a borrow rate for a low volatility stock for comparison
    low_vol_rate = api_client.get_borrow_rate("AAPL").current_rate
    high_vol_rate = response.borrow_rate_used
    assert high_vol_rate > low_vol_rate, "High volatility borrow rate should be higher"
    
    logger.info("High volatility fee calculation test passed")


@pytest.mark.e2e
def test_calculate_locate_fee_corporate_event(environment, corporate_event_scenario):
    """Tests fee calculation with corporate event risk factors."""
    logger.info("Testing fee calculation with corporate event risk factors")
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Extract parameters from scenario
    ticker = corporate_event_scenario["ticker"]
    position_value = corporate_event_scenario["position_value"]
    loan_days = corporate_event_scenario["loan_days"]
    client_id = corporate_event_scenario["client_id"]
    
    # Call API to calculate fee
    response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    # Assert basic response properties
    assert response.status == "success"
    
    # Use validator to verify calculation against expected result
    validator.assert_calculation(corporate_event_scenario)
    
    # Verify that borrow rate includes event risk adjustment
    borrow_rate_response = api_client.get_borrow_rate(ticker)
    assert hasattr(borrow_rate_response, "event_risk_factor") and borrow_rate_response.event_risk_factor > 0, \
        "Event risk factor should be present and positive"
    
    logger.info("Corporate event fee calculation test passed")


@pytest.mark.e2e
def test_calculate_locate_fee_hard_to_borrow(environment, hard_to_borrow_scenario):
    """Tests fee calculation with hard-to-borrow securities."""
    logger.info("Testing fee calculation with hard-to-borrow securities")
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Extract parameters from scenario
    ticker = hard_to_borrow_scenario["ticker"]
    position_value = hard_to_borrow_scenario["position_value"]
    loan_days = hard_to_borrow_scenario["loan_days"]
    client_id = hard_to_borrow_scenario["client_id"]
    
    # Call API to calculate fee
    response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    # Assert basic response properties
    assert response.status == "success"
    
    # Use validator to verify calculation against expected result
    validator.assert_calculation(hard_to_borrow_scenario)
    
    # Verify that borrow rate is significantly higher
    easy_to_borrow_rate = api_client.get_borrow_rate("AAPL").current_rate
    hard_to_borrow_rate = response.borrow_rate_used
    
    assert hard_to_borrow_rate > easy_to_borrow_rate * Decimal('3'), \
        "Hard-to-borrow rate should be significantly higher than easy-to-borrow rate"
    
    logger.info("Hard-to-borrow fee calculation test passed")


@pytest.mark.e2e
def test_calculate_locate_fee_long_term_loan(environment, long_term_loan_scenario):
    """Tests fee calculation with long-term loan duration."""
    logger.info("Testing fee calculation with long-term loan duration")
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Extract parameters from scenario
    ticker = long_term_loan_scenario["ticker"]
    position_value = long_term_loan_scenario["position_value"]
    loan_days = long_term_loan_scenario["loan_days"]
    client_id = long_term_loan_scenario["client_id"]
    
    # Call API to calculate fee
    response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    # Assert basic response properties
    assert response.status == "success"
    
    # Use validator to verify calculation against expected result
    validator.assert_calculation(long_term_loan_scenario)
    
    # Verify that fee is proportional to loan duration
    # We'll create a modified scenario with half the loan days and check that the fee is roughly half
    modified_scenario = long_term_loan_scenario.copy()
    modified_scenario["loan_days"] = loan_days // 2
    
    half_duration_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=modified_scenario["loan_days"],
        client_id=client_id
    )
    
    # The borrow cost should be roughly proportional to loan days (other fees may not be)
    borrow_cost_ratio = response.breakdown["borrow_cost"] / half_duration_response.breakdown["borrow_cost"]
    expected_ratio = Decimal(loan_days) / Decimal(modified_scenario["loan_days"])
    
    # Allow for some small numerical differences
    assert abs(borrow_cost_ratio - expected_ratio) < Decimal('0.01'), \
        f"Borrow cost should be proportional to loan days. Expected ratio: {expected_ratio}, Actual: {borrow_cost_ratio}"
    
    logger.info("Long-term loan fee calculation test passed")


@pytest.mark.e2e
def test_full_calculation_flow(environment):
    """Tests the complete calculation flow from borrow rate to fee calculation."""
    logger.info("Testing full calculation flow")
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Get test scenario for normal market conditions
    scenario = get_test_scenario("normal_market")
    ticker = scenario["ticker"]
    
    # Step 1: Get borrow rate for the stock
    borrow_rate_response = api_client.get_borrow_rate(ticker)
    assert borrow_rate_response.status == "success", "Failed to retrieve borrow rate"
    
    # Step 2: Calculate locate fee using the scenario parameters
    fee_response = api_client.calculate_locate_fee(
        ticker=scenario["ticker"],
        position_value=scenario["position_value"],
        loan_days=scenario["loan_days"],
        client_id=scenario["client_id"]
    )
    assert fee_response.status == "success", "Failed to calculate locate fee"
    
    # Step 3: Verify that the borrow rate used in the fee calculation matches the retrieved rate
    assert abs(fee_response.borrow_rate_used - borrow_rate_response.current_rate) < Decimal('0.0001'), \
        f"Borrow rate mismatch: {fee_response.borrow_rate_used} vs {borrow_rate_response.current_rate}"
    
    # Step 4: Verify that the fee breakdown components sum to the total fee
    breakdown_sum = sum(fee_response.breakdown.values())
    assert abs(breakdown_sum - fee_response.total_fee) < Decimal('0.01'), \
        f"Fee breakdown components ({breakdown_sum}) don't sum to total fee ({fee_response.total_fee})"
    
    logger.info("Full calculation flow test passed")


@pytest.mark.e2e
def test_multiple_calculations_consistency(environment, normal_market_scenario):
    """Tests that multiple calculations for the same parameters yield consistent results."""
    logger.info("Testing calculation consistency")
    api_client = create_api_client()
    
    # Extract parameters from scenario
    ticker = normal_market_scenario["ticker"]
    position_value = normal_market_scenario["position_value"]
    loan_days = normal_market_scenario["loan_days"]
    client_id = normal_market_scenario["client_id"]
    
    # Perform multiple calculations with the same parameters
    response1 = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    response2 = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    response3 = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    # Assert that all responses have the same values
    assert response1.total_fee == response2.total_fee == response3.total_fee, \
        "Total fee should be consistent across multiple calculations"
    
    assert response1.borrow_rate_used == response2.borrow_rate_used == response3.borrow_rate_used, \
        "Borrow rate should be consistent across multiple calculations"
    
    for key in response1.breakdown:
        assert response1.breakdown[key] == response2.breakdown[key] == response3.breakdown[key], \
            f"Breakdown component {key} should be consistent across multiple calculations"
    
    logger.info("Calculation consistency test passed")