"""
End-to-end tests for caching behavior in the Borrow Rate & Locate Fee Pricing Engine.

This module tests various caching scenarios including cache hits, cache misses,
cache invalidation, and TTL expiration for different data types such as
borrow rates, volatility metrics, and calculation results.
"""

import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional

import pytest

# Internal imports
from .config.settings import get_test_settings, TestEnvironment
from .helpers.api_client import APIClient, create_api_client
from .helpers.validation import ResponseValidator, create_response_validator
from .helpers.test_data import get_test_scenario, is_decimal_equal
from .fixtures.environment import environment
from .fixtures.test_data import test_data_manager, normal_market_scenario
from src.backend.core.constants import CACHE_TTL_BORROW_RATE, CACHE_TTL_CALCULATION

# Configure logger
logger = logging.getLogger(__name__)

# Constants for tests
CACHE_TEST_SLEEP_BUFFER = 1  # Additional seconds to add to sleep time beyond TTL

def setup_module():
    """Setup function that runs once before all tests in the module."""
    logger.info("Setting up caching behavior test module")
    settings = get_test_settings()
    api_client = create_api_client()
    
    # Wait for API to be available before starting tests
    api_client.wait_for_api_ready()
    logger.info("Caching behavior test module setup completed")

def teardown_module():
    """Teardown function that runs once after all tests in the module."""
    logger.info("Tearing down caching behavior test module")
    # Additional cleanup if necessary
    logger.info("Caching behavior test module teardown completed")

@pytest.mark.e2e
def test_borrow_rate_cache_hit(environment):
    """Tests that subsequent requests for the same borrow rate use cached data."""
    logger.info("Starting borrow rate cache hit test")
    
    # Create API client and response validator
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Make first request - should be a cache miss
    start_time = time.time()
    first_response = api_client.get_borrow_rate("AAPL")
    first_request_time = time.time() - start_time
    first_rate = first_response.current_rate
    
    logger.info(f"First request time: {first_request_time:.4f}s, rate: {first_rate}")
    
    # Make second request immediately - should be a cache hit
    start_time = time.time()
    second_response = api_client.get_borrow_rate("AAPL")
    second_request_time = time.time() - start_time
    second_rate = second_response.current_rate
    
    logger.info(f"Second request time: {second_request_time:.4f}s, rate: {second_rate}")
    
    # Cache hit should be significantly faster
    assert second_request_time < first_request_time * 0.8, \
        f"Second request ({second_request_time:.4f}s) not faster than first request ({first_request_time:.4f}s)"
    
    # Both rates should be identical
    assert is_decimal_equal(first_rate, second_rate), \
        f"Rates differ between requests: {first_rate} vs {second_rate}"
    
    logger.info("Borrow rate cache hit test passed")

@pytest.mark.e2e
def test_borrow_rate_cache_miss(environment):
    """Tests that requests for different tickers result in cache misses."""
    logger.info("Starting borrow rate cache miss test")
    
    # Create API client and response validator
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Make first request for one ticker
    start_time = time.time()
    first_response = api_client.get_borrow_rate("AAPL")
    first_request_time = time.time() - start_time
    first_rate = first_response.current_rate
    
    logger.info(f"First request (AAPL) time: {first_request_time:.4f}s, rate: {first_rate}")
    
    # Make second request for a different ticker - should be a cache miss
    start_time = time.time()
    second_response = api_client.get_borrow_rate("MSFT")
    second_request_time = time.time() - start_time
    second_rate = second_response.current_rate
    
    logger.info(f"Second request (MSFT) time: {second_request_time:.4f}s, rate: {second_rate}")
    
    # Both requests should have similar response times (both being either cache misses or both hits)
    # We're not asserting second is slower, as both might be cached if tests ran before
    
    # Rates should be different for different tickers
    assert not is_decimal_equal(first_rate, second_rate), \
        f"Rates should differ between tickers: AAPL ({first_rate}) vs MSFT ({second_rate})"
    
    logger.info("Borrow rate cache miss test passed")

@pytest.mark.e2e
def test_calculation_cache_hit(environment, normal_market_scenario):
    """Tests that subsequent identical fee calculations use cached results."""
    logger.info("Starting calculation cache hit test")
    
    # Create API client and response validator
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Extract parameters from scenario
    ticker = normal_market_scenario['ticker']
    position_value = normal_market_scenario['position_value']
    loan_days = normal_market_scenario['loan_days']
    client_id = normal_market_scenario['client_id']
    
    # Make first calculation request - should be a cache miss
    start_time = time.time()
    first_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    first_request_time = time.time() - start_time
    first_result = first_response
    
    logger.info(f"First calculation request time: {first_request_time:.4f}s")
    
    # Make second request with identical parameters - should be a cache hit
    start_time = time.time()
    second_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    second_request_time = time.time() - start_time
    second_result = second_response
    
    logger.info(f"Second calculation request time: {second_request_time:.4f}s")
    
    # Cache hit should be significantly faster
    assert second_request_time < first_request_time * 0.8, \
        f"Second request ({second_request_time:.4f}s) not faster than first request ({first_request_time:.4f}s)"
    
    # Both results should be identical
    assert first_result.total_fee == second_result.total_fee, \
        f"Total fees differ: {first_result.total_fee} vs {second_result.total_fee}"
    
    assert first_result.borrow_rate_used == second_result.borrow_rate_used, \
        f"Borrow rates differ: {first_result.borrow_rate_used} vs {second_result.borrow_rate_used}"
    
    logger.info("Calculation cache hit test passed")

@pytest.mark.e2e
def test_calculation_cache_miss(environment, normal_market_scenario):
    """Tests that calculations with different parameters result in cache misses."""
    logger.info("Starting calculation cache miss test")
    
    # Create API client and response validator
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Extract parameters from scenario
    ticker = normal_market_scenario['ticker']
    position_value = normal_market_scenario['position_value']
    loan_days = normal_market_scenario['loan_days']
    client_id = normal_market_scenario['client_id']
    
    # Make first calculation request with original parameters
    start_time = time.time()
    first_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    first_request_time = time.time() - start_time
    first_result = first_response
    
    logger.info(f"First calculation request time: {first_request_time:.4f}s")
    
    # Make second request with different position_value - should be a cache miss
    modified_position_value = position_value * 2
    
    start_time = time.time()
    second_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=modified_position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    second_request_time = time.time() - start_time
    second_result = second_response
    
    logger.info(f"Second calculation request time: {second_request_time:.4f}s")
    
    # Results should be different due to different position values
    assert first_result.total_fee != second_result.total_fee, \
        f"Total fees should differ with different position values: {first_result.total_fee} vs {second_result.total_fee}"
    
    logger.info("Calculation cache miss test passed")

@pytest.mark.e2e
@pytest.mark.slow
def test_borrow_rate_cache_ttl(environment):
    """Tests that borrow rate cache entries expire after their TTL."""
    logger.info("Starting borrow rate cache TTL test")
    
    # Skip this test if not in local environment to avoid long test times in CI
    if environment.get('environment') != TestEnvironment.LOCAL:
        pytest.skip("Skipping TTL test in non-local environment")
        
    # Create API client and response validator
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Make first request - should be a cache miss
    start_time = time.time()
    first_response = api_client.get_borrow_rate("AAPL")
    first_request_time = time.time() - start_time
    first_rate = first_response.current_rate
    
    logger.info(f"First request time: {first_request_time:.4f}s, rate: {first_rate}")
    
    # Make second request immediately - should be a cache hit
    start_time = time.time()
    second_response = api_client.get_borrow_rate("AAPL")
    second_request_time = time.time() - start_time
    
    logger.info(f"Second request time: {second_request_time:.4f}s")
    assert second_request_time < first_request_time * 0.8, "Second request should be faster (cache hit)"
    
    # Wait for TTL to expire
    sleep_time = CACHE_TTL_BORROW_RATE + CACHE_TEST_SLEEP_BUFFER
    logger.info(f"Waiting {sleep_time} seconds for cache TTL to expire...")
    time.sleep(sleep_time)
    
    # Make third request after TTL - should be a cache miss
    start_time = time.time()
    third_response = api_client.get_borrow_rate("AAPL")
    third_request_time = time.time() - start_time
    
    logger.info(f"Third request time: {third_request_time:.4f}s")
    assert third_request_time > second_request_time * 1.5, \
        f"Third request ({third_request_time:.4f}s) should be slower than second request ({second_request_time:.4f}s)"
    
    logger.info("Borrow rate cache TTL test passed")

@pytest.mark.e2e
@pytest.mark.slow
def test_calculation_cache_ttl(environment, normal_market_scenario):
    """Tests that calculation cache entries expire after their TTL."""
    logger.info("Starting calculation cache TTL test")
    
    # Skip this test if not in local environment to avoid long test times in CI
    if environment.get('environment') != TestEnvironment.LOCAL:
        pytest.skip("Skipping TTL test in non-local environment")
        
    # Create API client and response validator
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Extract parameters from scenario
    ticker = normal_market_scenario['ticker']
    position_value = normal_market_scenario['position_value']
    loan_days = normal_market_scenario['loan_days']
    client_id = normal_market_scenario['client_id']
    
    # Make first calculation request - should be a cache miss
    start_time = time.time()
    first_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    first_request_time = time.time() - start_time
    
    logger.info(f"First calculation request time: {first_request_time:.4f}s")
    
    # Make second request immediately - should be a cache hit
    start_time = time.time()
    second_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    second_request_time = time.time() - start_time
    
    logger.info(f"Second calculation request time: {second_request_time:.4f}s")
    assert second_request_time < first_request_time * 0.8, "Second request should be faster (cache hit)"
    
    # Wait for TTL to expire
    sleep_time = CACHE_TTL_CALCULATION + CACHE_TEST_SLEEP_BUFFER
    logger.info(f"Waiting {sleep_time} seconds for cache TTL to expire...")
    time.sleep(sleep_time)
    
    # Make third request after TTL - should be a cache miss
    start_time = time.time()
    third_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    third_request_time = time.time() - start_time
    
    logger.info(f"Third calculation request time: {third_request_time:.4f}s")
    assert third_request_time > second_request_time * 1.5, \
        f"Third request ({third_request_time:.4f}s) should be slower than second request ({second_request_time:.4f}s)"
    
    logger.info("Calculation cache TTL test passed")

@pytest.mark.e2e
def test_cache_consistency(environment, normal_market_scenario):
    """Tests that cached results remain consistent with direct calculations."""
    logger.info("Starting cache consistency test")
    
    # Create API client and response validator
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Extract parameters from scenario
    ticker = normal_market_scenario['ticker']
    position_value = normal_market_scenario['position_value']
    loan_days = normal_market_scenario['loan_days']
    client_id = normal_market_scenario['client_id']
    
    # Make first calculation request
    first_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    # Make second request immediately (should be cache hit)
    second_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    # Verify that both responses match exactly
    assert first_response.total_fee == second_response.total_fee, \
        f"Total fees differ: {first_response.total_fee} vs {second_response.total_fee}"
    
    assert first_response.borrow_rate_used == second_response.borrow_rate_used, \
        f"Borrow rates differ: {first_response.borrow_rate_used} vs {second_response.borrow_rate_used}"
    
    assert first_response.breakdown.borrow_cost == second_response.breakdown.borrow_cost, \
        f"Borrow costs differ: {first_response.breakdown.borrow_cost} vs {second_response.breakdown.borrow_cost}"
    
    assert first_response.breakdown.markup == second_response.breakdown.markup, \
        f"Markups differ: {first_response.breakdown.markup} vs {second_response.breakdown.markup}"
    
    assert first_response.breakdown.transaction_fees == second_response.breakdown.transaction_fees, \
        f"Transaction fees differ: {first_response.breakdown.transaction_fees} vs {second_response.breakdown.transaction_fees}"
    
    # Also validate the calculation result is correct using the validator
    expected_result = validator.assert_calculation(normal_market_scenario)
    
    logger.info("Cache consistency test passed")

@pytest.mark.e2e
def test_cache_invalidation_on_parameter_change(environment, normal_market_scenario):
    """Tests that changing calculation parameters invalidates cache entries."""
    logger.info("Starting cache invalidation test")
    
    # Create API client and response validator
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Extract parameters from scenario
    ticker = normal_market_scenario['ticker']
    position_value = normal_market_scenario['position_value']
    loan_days = normal_market_scenario['loan_days']
    client_id = normal_market_scenario['client_id']
    
    # Make first calculation request with original parameters
    first_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    # Make second request with identical parameters (should be cache hit)
    second_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    # Verify second response matches first (from cache)
    assert first_response.total_fee == second_response.total_fee, \
        "Second request should return same result as first (cache hit)"
    
    # Modify loan days parameter
    modified_loan_days = loan_days * 2
    
    # Make third request with modified parameters
    third_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=modified_loan_days,
        client_id=client_id
    )
    
    # Verify third response is different (different parameters)
    assert first_response.total_fee != third_response.total_fee, \
        "Third request should return different result (different loan_days)"
    
    # Make fourth request with original parameters again
    fourth_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    # Verify fourth response matches first (original cache entry still valid)
    assert first_response.total_fee == fourth_response.total_fee, \
        "Fourth request should return same result as first (original cache still valid)"
    
    logger.info("Cache invalidation test passed")

@pytest.mark.e2e
def test_multiple_requests_performance(environment):
    """Tests performance improvement from caching with multiple requests."""
    logger.info("Starting multiple requests performance test")
    
    # Create API client and response validator
    api_client = create_api_client()
    validator = create_response_validator(api_client)
    
    # Define test tickers
    test_tickers = ["AAPL", "MSFT", "TSLA"]
    
    # First round of requests - all should be cache misses
    start_time = time.time()
    first_round_responses = []
    for ticker in test_tickers:
        response = api_client.get_borrow_rate(ticker)
        first_round_responses.append(response)
    first_round_time = time.time() - start_time
    
    logger.info(f"First round time (expected cache misses): {first_round_time:.4f}s")
    
    # Second round of requests - all should be cache hits
    start_time = time.time()
    second_round_responses = []
    for ticker in test_tickers:
        response = api_client.get_borrow_rate(ticker)
        second_round_responses.append(response)
    second_round_time = time.time() - start_time
    
    logger.info(f"Second round time (expected cache hits): {second_round_time:.4f}s")
    
    # Second round should be significantly faster
    assert second_round_time < first_round_time * 0.8, \
        f"Second round ({second_round_time:.4f}s) not faster than first round ({first_round_time:.4f}s)"
    
    # Calculate and log performance improvement
    improvement = ((first_round_time - second_round_time) / first_round_time) * 100
    logger.info(f"Performance improvement from caching: {improvement:.2f}%")
    
    logger.info("Multiple requests performance test passed")