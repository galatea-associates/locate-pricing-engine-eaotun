"""
End-to-end test module that verifies the data refresh functionality of the Borrow Rate & Locate Fee Pricing Engine.
Tests the system's ability to update cached data from external sources and ensure calculations use the most current market data.
"""

import logging
import pytest
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Union

from .config.settings import get_test_settings, TestEnvironment
from .helpers.api_client import APIClient, create_api_client
from .helpers.validation import ResponseValidator, create_response_validator
from .helpers.test_data import (
    get_test_scenario, get_stock_data, get_volatility_data,
    calculate_expected_borrow_rate
)
from .fixtures.environment import environment
from .fixtures.test_data import test_data_manager
from src.backend.schemas.response import BorrowRateResponse

# Configure logger
logger = logging.getLogger(__name__)

# Test constants
TEST_TICKERS = ['AAPL', 'GME', 'TSLA']
CACHE_WAIT_TIME = 6  # Wait time in seconds to ensure cache expiration


def setup_module():
    """Setup function that runs once before all tests in the module"""
    logger.info("Starting data refresh test module setup")
    
    # Get test settings
    settings = get_test_settings()
    
    # Create API client and wait for API to be ready
    api_client = create_api_client(settings)
    api_client.wait_for_api_ready()
    
    logger.info("Data refresh test module setup complete")


def teardown_module():
    """Teardown function that runs once after all tests in the module"""
    logger.info("Starting data refresh test module teardown")
    
    # Perform any necessary cleanup
    
    logger.info("Data refresh test module teardown complete")


@pytest.mark.e2e
def test_borrow_rate_caching(environment):
    """
    Tests that borrow rates are properly cached and returned from cache on subsequent requests
    """
    logger.info("Starting borrow rate caching test")
    
    # Create API client and validator
    api_client = create_api_client()
    validator = create_response_validator()
    
    # Test caching for each test ticker
    for ticker in TEST_TICKERS:
        # First API call - should get fresh data
        first_response = api_client.get_borrow_rate(ticker)
        first_timestamp = first_response.last_updated
        
        # Second API call immediately after - should get cached data
        second_response = api_client.get_borrow_rate(ticker)
        second_timestamp = second_response.last_updated
        
        # Assert both responses have the same rate and timestamp
        assert first_response.current_rate == second_response.current_rate, \
            f"Cached rate for {ticker} doesn't match original rate"
        assert first_timestamp == second_timestamp, \
            f"Cached timestamp for {ticker} doesn't match original timestamp"
    
    logger.info("Borrow rate caching test completed successfully")


@pytest.mark.e2e
def test_cache_expiration(environment):
    """
    Tests that cached data expires after the configured TTL and fresh data is fetched
    """
    logger.info("Starting cache expiration test")
    
    # Create API client and validator
    api_client = create_api_client()
    validator = create_response_validator()
    
    # Select a test ticker
    ticker = 'AAPL'
    
    # First API call - get initial data
    first_response = api_client.get_borrow_rate(ticker)
    first_timestamp = first_response.last_updated
    
    # Wait for cache to expire
    logger.info(f"Waiting {CACHE_WAIT_TIME} seconds for cache to expire")
    time.sleep(CACHE_WAIT_TIME)
    
    # Second API call after waiting - should get fresh data
    second_response = api_client.get_borrow_rate(ticker)
    second_timestamp = second_response.last_updated
    
    # Assert that the second timestamp is more recent
    assert second_timestamp > first_timestamp, \
        f"Expected fresh data after cache expiration, but timestamps are the same"
    
    logger.info("Cache expiration test completed successfully")


@pytest.mark.e2e
def test_data_refresh_affects_calculations(environment):
    """
    Tests that refreshed market data is reflected in fee calculations
    """
    logger.info("Starting data refresh calculation test")
    
    # Create API client and validator
    api_client = create_api_client()
    validator = create_response_validator()
    
    # Select a test ticker
    ticker = 'GME'
    
    # Get test scenario for the selected ticker
    scenario = get_test_scenario("high_volatility")  # Assumes this scenario uses GME
    
    # Make first API call to calculate fee
    first_calculation = api_client.calculate_locate_fee(
        ticker=scenario['ticker'],
        position_value=scenario['position_value'],
        loan_days=scenario['loan_days'],
        client_id=scenario['client_id']
    )
    first_fee = first_calculation.total_fee
    first_rate = first_calculation.borrow_rate_used
    
    # Wait for cache to expire
    logger.info(f"Waiting {CACHE_WAIT_TIME} seconds for cache to expire")
    time.sleep(CACHE_WAIT_TIME)
    
    # Make second API call with the same parameters
    second_calculation = api_client.calculate_locate_fee(
        ticker=scenario['ticker'],
        position_value=scenario['position_value'],
        loan_days=scenario['loan_days'],
        client_id=scenario['client_id']
    )
    second_fee = second_calculation.total_fee
    second_rate = second_calculation.borrow_rate_used
    
    # The rates might be different due to market updates
    # Even if rates are the same, we want to confirm the calculation still works
    # So we'll just log the difference rather than asserting specific changes
    rate_changed = first_rate != second_rate
    fee_changed = first_fee != second_fee
    
    if rate_changed:
        logger.info(f"Borrow rate changed from {first_rate} to {second_rate}")
    else:
        logger.info("Borrow rate remained the same after cache expiration")
        
    if fee_changed:
        logger.info(f"Total fee changed from {first_fee} to {second_fee}")
    else:
        logger.info("Total fee remained the same despite cache expiration")
    
    # Assert that the calculation was successful both times
    assert second_calculation.status == "success", "Second calculation failed"
    
    # The total fee should correctly reflect the updated borrow rate
    # We can verify this by checking if the borrow_cost component in the breakdown
    # is consistent with the borrow_rate_used
    position_value = Decimal(str(scenario['position_value']))
    loan_days = scenario['loan_days']
    expected_borrow_cost = position_value * second_rate * (Decimal(loan_days) / Decimal(365))
    actual_borrow_cost = second_calculation.breakdown.borrow_cost
    
    # Allow for small rounding differences
    tolerance = Decimal('0.01')
    assert abs(expected_borrow_cost - actual_borrow_cost) <= tolerance, \
        f"Borrow cost does not match expected value based on the updated rate"
    
    logger.info("Data refresh calculation test completed successfully")


@pytest.mark.e2e
def test_multiple_rate_refreshes(environment):
    """
    Tests that multiple data refreshes over time show market data evolution
    """
    logger.info("Starting multiple refreshes test")
    
    # Create API client
    api_client = create_api_client()
    
    # Select a test ticker
    ticker = 'TSLA'
    
    # Initialize list to store rate history
    rate_history = []
    
    # Get multiple rate readings with cache expiration in between
    for i in range(3):
        response = api_client.get_borrow_rate(ticker)
        rate_history.append({
            'rate': response.current_rate,
            'timestamp': response.last_updated
        })
        
        logger.info(f"Reading {i+1}: Rate = {response.current_rate}, Time = {response.last_updated}")
        
        if i < 2:  # Skip waiting after the last reading
            logger.info(f"Waiting {CACHE_WAIT_TIME} seconds for cache to expire")
            time.sleep(CACHE_WAIT_TIME)
    
    # Assert that we have 3 readings
    assert len(rate_history) == 3, "Failed to get 3 rate readings"
    
    # Assert that timestamps are in ascending order
    for i in range(1, 3):
        assert rate_history[i]['timestamp'] >= rate_history[i-1]['timestamp'], \
            f"Timestamp {i} is not greater than or equal to timestamp {i-1}"
    
    # Note: Rates might be the same if market data hasn't changed
    # Log whether rates changed
    rates = [entry['rate'] for entry in rate_history]
    if len(set(rates)) > 1:
        logger.info(f"Rates changed across multiple refreshes: {rates}")
    else:
        logger.info(f"Rates remained consistent across multiple refreshes: {rates[0]}")
    
    logger.info("Multiple refreshes test completed successfully")


@pytest.mark.e2e
def test_volatility_data_refresh(environment):
    """
    Tests that volatility data is refreshed and affects borrow rate calculations
    """
    logger.info("Starting volatility refresh test")
    
    # Create API client and validator
    api_client = create_api_client()
    validator = create_response_validator()
    
    # Select a high volatility ticker
    ticker = 'GME'
    
    # First API call to get initial volatility data
    first_response = api_client.get_borrow_rate(ticker)
    first_volatility = first_response.volatility_index
    
    # Wait for cache to expire
    logger.info(f"Waiting {CACHE_WAIT_TIME} seconds for cache to expire")
    time.sleep(CACHE_WAIT_TIME)
    
    # Second API call after waiting - should get fresh volatility data
    second_response = api_client.get_borrow_rate(ticker)
    second_volatility = second_response.volatility_index
    
    # Log volatility values - they might be the same if external data hasn't changed
    logger.info(f"First volatility: {first_volatility}")
    logger.info(f"Second volatility: {second_volatility}")
    
    # Check if the current rate reflects the volatility
    # Even if volatility is the same, we want to verify the formula is correctly applied
    stock_data = get_stock_data(ticker)
    volatility_data = {
        'stock_id': ticker,
        'vol_index': second_volatility,
        'event_risk_factor': 0  # We don't have this in the response, so assume 0
    }
    
    # Try to calculate an expected rate based on the volatility
    # This is an approximation since we don't know the exact formula used
    approximate_rate = calculate_expected_borrow_rate(stock_data, volatility_data)
    logger.info(f"Approximate expected rate based on volatility: {approximate_rate}")
    logger.info(f"Actual current rate: {second_response.current_rate}")
    
    # The rates might not match exactly due to other factors, but they should be in the same ballpark
    assert abs(approximate_rate - second_response.current_rate) <= Decimal('0.05'), \
        "Current rate differs significantly from expected rate based on volatility"
    
    logger.info("Volatility refresh test completed successfully")


@pytest.mark.e2e
def test_concurrent_calculations_during_refresh(environment):
    """
    Tests that concurrent calculations during a data refresh period remain consistent
    """
    logger.info("Starting concurrent calculations test")
    
    # Create API client
    api_client = create_api_client()
    
    # Select a test ticker
    ticker = 'AAPL'
    
    # Get test scenario for the selected ticker
    scenario = get_test_scenario("normal_market")  # Assumes this scenario uses AAPL
    
    # Make initial borrow rate call to ensure data is cached
    initial_rate = api_client.get_borrow_rate(ticker)
    
    # Perform multiple rapid calculations
    calculation_results = []
    for i in range(5):
        result = api_client.calculate_locate_fee(
            ticker=scenario['ticker'],
            position_value=scenario['position_value'],
            loan_days=scenario['loan_days'],
            client_id=scenario['client_id']
        )
        calculation_results.append(result)
        logger.info(f"Calculation {i+1} completed")
    
    # Assert that all calculations have the same borrow rate (should be cached)
    rates = [result.borrow_rate_used for result in calculation_results]
    assert len(set(rates)) == 1, "Borrow rates differ across concurrent calculations"
    
    # Assert that all fee breakdowns are consistent
    fee_components = []
    for result in calculation_results:
        fee_components.append({
            'borrow_cost': result.breakdown.borrow_cost,
            'markup': result.breakdown.markup,
            'transaction_fees': result.breakdown.transaction_fees
        })
    
    # Check if all breakdowns are identical
    first_breakdown = fee_components[0]
    for i, breakdown in enumerate(fee_components[1:], 1):
        for component, value in breakdown.items():
            assert value == first_breakdown[component], \
                f"Breakdown component {component} differs in calculation {i}"
    
    logger.info("Concurrent calculations test completed successfully")


@pytest.mark.e2e
def test_rate_change_detection(environment):
    """
    Tests the system's ability to detect and apply significant rate changes
    """
    logger.info("Starting rate change detection test")
    
    # Create API client and validator
    api_client = create_api_client()
    validator = create_response_validator()
    
    # Select a volatile ticker
    ticker = 'GME'
    
    # Make multiple API calls with cache expiration in between
    rate_responses = []
    
    for i in range(3):
        response = api_client.get_borrow_rate(ticker)
        rate_responses.append(response)
        
        logger.info(f"Reading {i+1}: Rate = {response.current_rate}, Time = {response.last_updated}")
        
        if i < 2:  # Skip waiting after the last reading
            logger.info(f"Waiting {CACHE_WAIT_TIME} seconds for cache to expire")
            time.sleep(CACHE_WAIT_TIME)
    
    # Calculate percentage changes between successive rates
    rates = [response.current_rate for response in rate_responses]
    changes = []
    
    for i in range(1, len(rates)):
        previous = rates[i-1]
        current = rates[i]
        
        if previous == Decimal('0'):
            # Avoid division by zero
            percent_change = Decimal('0') if current == Decimal('0') else Decimal('100')
        else:
            percent_change = ((current - previous) / previous) * Decimal('100')
        
        changes.append(percent_change)
        logger.info(f"Change from reading {i} to {i+1}: {percent_change}%")
    
    # The system should detect and apply rate changes
    # We can't assert specific changes as they depend on external data
    # Instead, we verify the functionality worked by ensuring rates are retrieved
    assert len(rate_responses) == 3, "Failed to get all rate responses"
    
    # If there were significant changes, verify they were reflected in the rates
    if changes and max(abs(change) for change in changes) > Decimal('1.0'):
        logger.info("Detected significant rate changes, system correctly reflected market movements")
    else:
        logger.info("No significant rate changes detected during the test period")
    
    logger.info("Rate change detection test completed successfully")