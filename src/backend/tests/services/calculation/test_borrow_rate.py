"""
Unit tests for the borrow rate calculation functionality in the Borrow Rate & Locate Fee Pricing Engine.

This module tests the accuracy, performance, and resilience of the borrow rate calculation service,
including volatility adjustments, event risk adjustments, and fallback mechanisms.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock, call

# Import functions being tested
from ...services.calculation.borrow_rate import (
    calculate_borrow_rate,
    get_real_time_borrow_rate,
    get_fallback_borrow_rate,
    get_borrow_rate_with_adjustments,
    get_borrow_rate_by_status
)

# Import functions for adjustments
from ...services.calculation.volatility import (
    calculate_volatility_adjustment,
    apply_volatility_adjustment
)
from ...services.calculation.event_risk import calculate_event_risk_adjustment

# Import external API functions for mocking
from ...services.external.seclend_api import get_borrow_rate
from ...services.external.market_api import get_market_volatility, get_stock_volatility
from ...services.external.event_api import get_event_risk_factor

# Import Redis cache for mocking
from ...services.cache.redis import RedisCache

# Import enums and constants
from ...core.constants import (
    BorrowStatus,
    DEFAULT_MINIMUM_BORROW_RATE,
    DEFAULT_VOLATILITY_FACTOR,
    DEFAULT_EVENT_RISK_FACTOR
)

# Import exceptions
from ...core.exceptions import ExternalAPIException

# Import fixtures
from ...tests.fixtures.stocks import (
    stock_data,
    easy_to_borrow_stock,
    hard_to_borrow_stock,
    medium_to_borrow_stock
)
from ...tests.fixtures.volatility import (
    volatility_data,
    low_volatility_data,
    high_volatility_data
)
from ...tests.fixtures.api_responses import (
    mock_seclend_response,
    mock_market_volatility_response,
    mock_stock_volatility_response,
    mock_event_calendar_response,
    mock_api_error_response
)


def test_calculate_borrow_rate_basic():
    """Tests the basic functionality of calculate_borrow_rate with mocked dependencies."""
    test_ticker = "AAPL"
    base_rate = Decimal('0.05')  # 5%
    volatility_adjustment = Decimal('0.01')  # 1%
    event_adjustment = Decimal('0.005')  # 0.5%
    
    # Mock dependencies
    with patch('src.backend.services.calculation.borrow_rate.get_real_time_borrow_rate') as mock_get_rate, \
         patch('src.backend.services.calculation.borrow_rate.get_stock_volatility') as mock_get_vol, \
         patch('src.backend.services.calculation.volatility.calculate_volatility_adjustment') as mock_calc_vol, \
         patch('src.backend.services.calculation.borrow_rate.get_event_risk_factor') as mock_get_event, \
         patch('src.backend.services.calculation.event_risk.calculate_event_risk_adjustment') as mock_calc_event:
        
        # Set up mocks
        mock_get_rate.return_value = base_rate
        mock_get_vol.return_value = {"volatility": 20.0}
        mock_calc_vol.return_value = volatility_adjustment
        mock_get_event.return_value = 2
        mock_calc_event.return_value = event_adjustment
        
        # Call function
        result = calculate_borrow_rate(test_ticker, use_cache=False)
        
        # Calculate expected result
        # Base rate + volatility adjustment + event risk adjustment
        vol_adjusted_rate = base_rate * (Decimal('1') + volatility_adjustment)
        expected_result = vol_adjusted_rate * (Decimal('1') + event_adjustment)
        expected_result = max(expected_result, DEFAULT_MINIMUM_BORROW_RATE)
        
        # Assert result matches expected
        assert result == pytest.approx(expected_result)
        
        # Verify mocks were called correctly
        mock_get_rate.assert_called_once_with(test_ticker, None)
        mock_get_vol.assert_called_once_with(test_ticker)
        mock_calc_vol.assert_called_once()
        mock_get_event.assert_called_once_with(test_ticker)
        mock_calc_event.assert_called_once()


def test_calculate_borrow_rate_with_volatility():
    """Tests that volatility adjustments are correctly applied to the borrow rate."""
    test_ticker = "TSLA"
    base_rate = Decimal('0.05')  # 5%
    high_volatility = Decimal('35.0')
    
    # Mock dependencies
    with patch('src.backend.services.calculation.borrow_rate.get_real_time_borrow_rate') as mock_get_rate, \
         patch('src.backend.services.calculation.borrow_rate.get_stock_volatility') as mock_get_vol, \
         patch('src.backend.services.calculation.borrow_rate.get_event_risk_factor') as mock_get_event, \
         patch('src.backend.services.calculation.borrow_rate.cache_borrow_rate') as mock_cache:
        
        # Set up mocks
        mock_get_rate.return_value = base_rate
        mock_get_vol.return_value = {"volatility": float(high_volatility)}
        mock_get_event.return_value = 0  # No event risk for this test
        
        # Call function
        result = calculate_borrow_rate(test_ticker, use_cache=False)
        
        # Calculate expected volatility adjustment
        vol_adjustment = high_volatility * DEFAULT_VOLATILITY_FACTOR
        expected_rate = base_rate * (Decimal('1') + vol_adjustment)
        expected_rate = max(expected_rate, DEFAULT_MINIMUM_BORROW_RATE)
        
        # Assert result is higher than base rate due to volatility
        assert result > base_rate
        assert result == pytest.approx(expected_rate)
        
        # Verify volatility was retrieved and used
        mock_get_vol.assert_called_once_with(test_ticker)


def test_calculate_borrow_rate_with_event_risk():
    """Tests that event risk adjustments are correctly applied to the borrow rate."""
    test_ticker = "AAPL"
    base_rate = Decimal('0.05')  # 5%
    high_risk_factor = 8  # High event risk (scale 0-10)
    
    # Mock dependencies
    with patch('src.backend.services.calculation.borrow_rate.get_real_time_borrow_rate') as mock_get_rate, \
         patch('src.backend.services.calculation.borrow_rate.get_stock_volatility') as mock_get_vol, \
         patch('src.backend.services.calculation.borrow_rate.get_event_risk_factor') as mock_get_event, \
         patch('src.backend.services.calculation.borrow_rate.cache_borrow_rate') as mock_cache:
        
        # Set up mocks
        mock_get_rate.return_value = base_rate
        mock_get_vol.return_value = {"volatility": 15.0}  # Low volatility for this test
        mock_get_event.return_value = high_risk_factor
        
        # Call function
        result = calculate_borrow_rate(test_ticker, use_cache=False)
        
        # Calculate expected event risk adjustment
        risk_ratio = Decimal(high_risk_factor) / Decimal('10')
        risk_adjustment = risk_ratio * DEFAULT_EVENT_RISK_FACTOR
        
        # First apply volatility adjustment
        vol_adjusted_rate = apply_volatility_adjustment(base_rate, Decimal('15.0'))
        # Then apply event risk adjustment
        expected_rate = vol_adjusted_rate * (Decimal('1') + risk_adjustment)
        expected_rate = max(expected_rate, DEFAULT_MINIMUM_BORROW_RATE)
        
        # Assert result is higher than base rate due to event risk
        assert result > base_rate
        assert result == pytest.approx(expected_rate)
        
        # Verify event risk was retrieved and used
        mock_get_event.assert_called_once_with(test_ticker)


def test_calculate_borrow_rate_with_min_rate():
    """Tests that the minimum borrow rate is enforced when specified."""
    test_ticker = "AAPL"
    base_rate = Decimal('0.01')  # 1%
    min_rate = Decimal('0.03')   # 3% minimum
    
    # Mock dependencies
    with patch('src.backend.services.calculation.borrow_rate.get_real_time_borrow_rate') as mock_get_rate, \
         patch('src.backend.services.calculation.borrow_rate.get_stock_volatility') as mock_get_vol, \
         patch('src.backend.services.calculation.borrow_rate.get_event_risk_factor') as mock_get_event, \
         patch('src.backend.services.calculation.borrow_rate.cache_borrow_rate') as mock_cache:
        
        # Set up mocks
        mock_get_rate.return_value = base_rate
        mock_get_vol.return_value = {"volatility": 10.0}  # Low volatility for this test
        mock_get_event.return_value = 0  # No event risk for this test
        
        # Call function with custom min_rate
        result = calculate_borrow_rate(test_ticker, min_rate=min_rate, use_cache=False)
        
        # Assert result equals the minimum rate (since calculated rate would be lower)
        assert result == min_rate
        
        # Verify min_rate was correctly passed to get_real_time_borrow_rate
        mock_get_rate.assert_called_once_with(test_ticker, min_rate)


def test_calculate_borrow_rate_with_cache():
    """Tests that the caching mechanism works correctly for borrow rates."""
    test_ticker = "AAPL"
    base_rate = Decimal('0.05')  # 5%
    cached_rate = Decimal('0.06')  # 6%
    
    # Mock cache operations
    with patch('src.backend.services.calculation.borrow_rate.get_cached_borrow_rate') as mock_get_cache, \
         patch('src.backend.services.calculation.borrow_rate.cache_borrow_rate') as mock_set_cache, \
         patch('src.backend.services.calculation.borrow_rate.get_real_time_borrow_rate') as mock_get_rate, \
         patch('src.backend.services.calculation.borrow_rate.get_stock_volatility') as mock_get_vol, \
         patch('src.backend.services.calculation.borrow_rate.get_event_risk_factor') as mock_get_event:
        
        # Test cache miss scenario
        mock_get_cache.return_value = None
        mock_get_rate.return_value = base_rate
        mock_get_vol.return_value = {"volatility": 15.0}
        mock_get_event.return_value = 2
        
        # Call function with use_cache=True (default)
        result1 = calculate_borrow_rate(test_ticker)
        
        # Verify cache was checked
        mock_get_cache.assert_called_once_with(test_ticker)
        
        # Verify get_real_time_borrow_rate was called (cache miss)
        mock_get_rate.assert_called_once()
        
        # Verify result was cached
        mock_set_cache.assert_called_once()
        
        # Reset mocks for cache hit scenario
        mock_get_cache.reset_mock()
        mock_get_rate.reset_mock()
        mock_set_cache.reset_mock()
        
        # Test cache hit scenario
        mock_get_cache.return_value = cached_rate
        
        # Call function again
        result2 = calculate_borrow_rate(test_ticker)
        
        # Verify cache was checked
        mock_get_cache.assert_called_once_with(test_ticker)
        
        # Verify get_real_time_borrow_rate was NOT called (cache hit)
        mock_get_rate.assert_not_called()
        
        # Verify result matches cached value
        assert result2 == cached_rate


def test_get_real_time_borrow_rate_success():
    """Tests successful retrieval of real-time borrow rate from external API."""
    test_ticker = "AAPL"
    expected_rate = Decimal('0.05')  # 5%
    
    # Mock external API call
    with patch('src.backend.services.external.seclend_api.get_borrow_rate') as mock_api:
        # Set up mock response
        mock_api.return_value = {
            'rate': float(expected_rate),
            'status': BorrowStatus.EASY.value
        }
        
        # Call function
        result = get_real_time_borrow_rate(test_ticker)
        
        # Assert result matches expected rate
        assert result == expected_rate
        
        # Verify API was called with correct parameters
        mock_api.assert_called_once_with(test_ticker)


def test_get_real_time_borrow_rate_failure():
    """Tests fallback mechanism when external API fails."""
    test_ticker = "AAPL"
    fallback_rate = Decimal('0.03')  # 3% (fallback rate)
    
    # Mock external API call to fail and fallback function
    with patch('src.backend.services.external.seclend_api.get_borrow_rate') as mock_api, \
         patch('src.backend.services.calculation.borrow_rate.get_fallback_borrow_rate') as mock_fallback:
        
        # Set up mock API to raise exception
        mock_api.side_effect = ExternalAPIException("SecLend API", "Connection timeout")
        
        # Set up mock fallback to return fallback rate
        mock_fallback.return_value = fallback_rate
        
        # Call function
        result = get_real_time_borrow_rate(test_ticker)
        
        # Assert result matches fallback rate
        assert result == fallback_rate
        
        # Verify fallback was called with correct parameters
        mock_fallback.assert_called_once_with(test_ticker, None)


def test_get_fallback_borrow_rate():
    """Tests the fallback borrow rate mechanism."""
    test_ticker = "AAPL"
    custom_min_rate = Decimal('0.02')  # 2%
    
    # Mock create_fallback_response
    with patch('src.backend.services.external.seclend_api.create_fallback_response') as mock_fallback:
        # Set up mock response
        mock_fallback.return_value = {
            'rate': 0.01,  # 1% fallback rate
            'status': BorrowStatus.HARD.value,
            'is_fallback': True
        }
        
        # Test with default min_rate
        result1 = get_fallback_borrow_rate(test_ticker)
        
        # Assert result is a valid Decimal
        assert isinstance(result1, Decimal)
        
        # Assert result is at least the DEFAULT_MINIMUM_BORROW_RATE
        assert result1 >= DEFAULT_MINIMUM_BORROW_RATE
        
        # Test with custom min_rate
        result2 = get_fallback_borrow_rate(test_ticker, custom_min_rate)
        
        # Assert result is at least the custom min_rate
        assert result2 >= custom_min_rate
        
        # Verify fallback response was requested
        mock_fallback.assert_called_with(test_ticker)


def test_get_borrow_rate_with_adjustments():
    """Tests the combined adjustment calculation function."""
    # Test parameters
    ticker = "AAPL"
    base_rate = Decimal('0.05')  # 5%
    volatility_index = Decimal('25.0')  # VIX at 25
    event_risk_factor = 5  # Medium event risk
    
    # Call function with test parameters
    result = get_borrow_rate_with_adjustments(
        ticker=ticker,
        base_rate=base_rate,
        volatility_index=volatility_index,
        event_risk_factor=event_risk_factor
    )
    
    # Assert result contains all expected keys
    expected_keys = [
        "original_rate", "adjusted_rate", "volatility_adjustment", 
        "event_risk_adjustment", "final_rate", "volatility_index", 
        "event_risk_factor"
    ]
    for key in expected_keys:
        assert key in result
    
    # Verify calculations are correct
    vol_adjustment = float(volatility_index * DEFAULT_VOLATILITY_FACTOR)
    event_ratio = event_risk_factor / 10
    event_adjustment = float(Decimal(event_ratio) * DEFAULT_EVENT_RISK_FACTOR)
    
    # Final rate should be higher than original due to adjustments
    assert result["adjusted_rate"] > result["original_rate"]
    assert result["volatility_adjustment"] == pytest.approx(vol_adjustment)
    assert result["event_risk_adjustment"] == pytest.approx(event_adjustment)


def test_get_borrow_rate_by_status():
    """Tests that appropriate default rates are returned based on borrow status."""
    # Test with EASY borrow status
    easy_rate = get_borrow_rate_by_status(BorrowStatus.EASY)
    
    # Test with MEDIUM borrow status
    medium_rate = get_borrow_rate_by_status(BorrowStatus.MEDIUM)
    
    # Test with HARD borrow status
    hard_rate = get_borrow_rate_by_status(BorrowStatus.HARD)
    
    # Assert rates are in ascending order (EASY < MEDIUM < HARD)
    assert easy_rate < medium_rate < hard_rate
    
    # Assert each rate is a Decimal
    assert isinstance(easy_rate, Decimal)
    assert isinstance(medium_rate, Decimal)
    assert isinstance(hard_rate, Decimal)
    
    # Verify specific values
    assert easy_rate == Decimal('0.005')  # 0.5%
    assert medium_rate == Decimal('0.02')  # 2%
    assert hard_rate == Decimal('0.05')  # 5%


def test_integration_calculate_borrow_rate(easy_to_borrow_stock, mock_seclend_response, mock_stock_volatility_response, mock_event_calendar_response):
    """Integration test for the full borrow rate calculation flow."""
    # Get ticker from fixture
    ticker = easy_to_borrow_stock["ticker"]
    
    # Mock external API calls
    with patch('src.backend.services.external.seclend_api.get_borrow_rate') as mock_seclend, \
         patch('src.backend.services.external.market_api.get_stock_volatility') as mock_volatility, \
         patch('src.backend.services.external.event_api.get_event_risk_factor') as mock_event:
        
        # Set up mock responses using fixtures
        mock_seclend.return_value = mock_seclend_response(ticker)
        mock_volatility.return_value = mock_stock_volatility_response(ticker)
        mock_event.return_value = int(mock_event_calendar_response(ticker).get('events', [{}])[0].get('risk_factor', 0) 
                                    if mock_event_calendar_response(ticker).get('events') else 0)
        
        # Call function with cache disabled
        result = calculate_borrow_rate(ticker, use_cache=False)
        
        # Assert result is a valid Decimal
        assert isinstance(result, Decimal)
        
        # Verify all expected API calls were made
        mock_seclend.assert_called_once_with(ticker)
        mock_volatility.assert_called_once_with(ticker)
        mock_event.assert_called_once_with(ticker)
        
        # For an easy-to-borrow stock, rate should be relatively low
        assert result < Decimal('0.1')  # Less than 10%


def test_integration_hard_to_borrow(hard_to_borrow_stock, mock_seclend_response, high_volatility_data):
    """Integration test for hard-to-borrow stocks with higher rates."""
    # Get ticker from fixture
    ticker = hard_to_borrow_stock["ticker"]
    
    # Mock external API calls
    with patch('src.backend.services.external.seclend_api.get_borrow_rate') as mock_seclend, \
         patch('src.backend.services.external.market_api.get_stock_volatility') as mock_volatility, \
         patch('src.backend.services.external.event_api.get_event_risk_factor') as mock_event:
        
        # Set up mock responses using fixtures
        mock_seclend.return_value = mock_seclend_response(ticker)
        mock_volatility.return_value = {
            "ticker": ticker,
            "volatility": float(high_volatility_data["vol_index"]),
            "timestamp": "2023-10-15T14:30:22Z"
        }
        mock_event.return_value = high_volatility_data["event_risk_factor"]
        
        # Call function with cache disabled
        result = calculate_borrow_rate(ticker, use_cache=False)
        
        # Assert result is a valid Decimal
        assert isinstance(result, Decimal)
        
        # For a hard-to-borrow stock with high volatility, rate should be high
        assert result > Decimal('0.2')  # More than 20%
        
        # Verify result reflects hard-to-borrow status and high volatility
        assert result > Decimal('0.5')  # Hard-to-borrow stocks should have higher rates


@pytest.mark.performance
def test_performance_calculate_borrow_rate():
    """Tests the performance of the borrow rate calculation."""
    import time
    test_ticker = "AAPL"
    
    # Mock dependencies to return quickly
    with patch('src.backend.services.calculation.borrow_rate.get_real_time_borrow_rate') as mock_get_rate, \
         patch('src.backend.services.calculation.borrow_rate.get_stock_volatility') as mock_get_vol, \
         patch('src.backend.services.calculation.borrow_rate.get_event_risk_factor') as mock_get_event, \
         patch('src.backend.services.calculation.borrow_rate.cache_borrow_rate') as mock_cache:
        
        # Set up mocks with simple return values
        mock_get_rate.return_value = Decimal('0.05')
        mock_get_vol.return_value = {"volatility": 15.0}
        mock_get_event.return_value = 2
        
        # Measure execution time
        start_time = time.time()
        calculate_borrow_rate(test_ticker, use_cache=False)
        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Assert execution time is below threshold (50ms)
        assert execution_time < 50, f"Calculation took {execution_time}ms, which exceeds the 50ms threshold"
        
        # Run multiple calculations to test consistency
        execution_times = []
        for _ in range(5):
            start_time = time.time()
            calculate_borrow_rate(test_ticker, use_cache=False)
            execution_times.append((time.time() - start_time) * 1000)
        
        # Assert all executions were within the threshold
        assert all(t < 50 for t in execution_times), "Not all calculations met the performance threshold"
        
        # Assert performance is consistent (standard deviation is low)
        if len(execution_times) > 1:
            import statistics
            std_dev = statistics.stdev(execution_times)
            assert std_dev < 10, f"Performance inconsistent: std dev = {std_dev}ms"


def test_error_handling_invalid_ticker():
    """Tests error handling when an invalid ticker is provided."""
    invalid_ticker = "INVALID123"
    
    # Mock get_borrow_rate to raise ExternalAPIException
    with patch('src.backend.services.external.seclend_api.get_borrow_rate') as mock_api, \
         patch('src.backend.services.calculation.borrow_rate.get_fallback_borrow_rate') as mock_fallback, \
         patch('src.backend.services.calculation.borrow_rate.get_stock_volatility') as mock_get_vol, \
         patch('src.backend.services.calculation.borrow_rate.get_event_risk_factor') as mock_get_event:
        
        # Set up mocks
        mock_api.side_effect = ExternalAPIException("SecLend API", "Ticker not found")
        mock_fallback.return_value = Decimal('0.03')
        mock_get_vol.return_value = {"volatility": 15.0}
        mock_get_event.return_value = 0
        
        # Call function - should not raise an exception
        result = calculate_borrow_rate(invalid_ticker, use_cache=False)
        
        # Assert that a fallback rate is returned
        assert isinstance(result, Decimal)
        assert result > Decimal('0')
        
        # Verify error handling logic was triggered
        mock_api.assert_called_once()
        mock_fallback.assert_called_once()


def test_error_handling_api_timeout():
    """Tests error handling when external API times out."""
    test_ticker = "AAPL"
    
    # Mock get_borrow_rate to raise ExternalAPIException for timeout
    with patch('src.backend.services.external.seclend_api.get_borrow_rate') as mock_api, \
         patch('src.backend.services.calculation.borrow_rate.get_fallback_borrow_rate') as mock_fallback, \
         patch('src.backend.services.calculation.borrow_rate.get_stock_volatility') as mock_get_vol, \
         patch('src.backend.services.calculation.borrow_rate.get_event_risk_factor') as mock_get_event:
        
        # Set up mocks
        mock_api.side_effect = ExternalAPIException("SecLend API", "Request timed out")
        mock_fallback.return_value = Decimal('0.03')
        mock_get_vol.return_value = {"volatility": 15.0}
        mock_get_event.return_value = 0
        
        # Call function - should not raise an exception
        result = calculate_borrow_rate(test_ticker, use_cache=False)
        
        # Assert that a fallback rate is returned
        assert isinstance(result, Decimal)
        assert result > Decimal('0')
        
        # Verify error handling logic was triggered
        mock_api.assert_called_once()
        mock_fallback.assert_called_once()


def test_cache_expiration():
    """Tests that cached values expire correctly after TTL."""
    test_ticker = "AAPL"
    ttl = 300  # 5 minutes
    
    # Mock dependencies
    with patch('src.backend.services.calculation.borrow_rate.get_cached_borrow_rate') as mock_get_cache, \
         patch('src.backend.services.calculation.borrow_rate.cache_borrow_rate') as mock_set_cache, \
         patch('src.backend.services.calculation.borrow_rate.get_real_time_borrow_rate') as mock_get_rate, \
         patch('src.backend.services.calculation.borrow_rate.get_stock_volatility') as mock_get_vol, \
         patch('src.backend.services.calculation.borrow_rate.get_event_risk_factor') as mock_get_event:
        
        # Set up mocks for first call (cache miss)
        mock_get_cache.return_value = None
        mock_get_rate.return_value = Decimal('0.05')
        mock_get_vol.return_value = {"volatility": 15.0}
        mock_get_event.return_value = 2
        
        # First call - should check cache, miss, and set new value
        calculate_borrow_rate(test_ticker)
        
        # Verify cache operations
        mock_get_cache.assert_called_once()
        mock_set_cache.assert_called_once()
        
        # Check TTL parameter
        mock_set_cache.assert_called_with(test_ticker, Decimal('0.0566'), ttl)
        
        # Reset mocks to simulate cache expiration
        mock_get_cache.reset_mock()
        mock_set_cache.reset_mock()
        mock_get_rate.reset_mock()
        
        # Set up mocks for second call (cache expired)
        mock_get_cache.return_value = None  # Simulate TTL expiration
        
        # Second call - should check cache, miss again, and trigger API call
        calculate_borrow_rate(test_ticker)
        
        # Verify cache was checked
        mock_get_cache.assert_called_once()
        
        # Verify API was called again since cache expired
        mock_get_rate.assert_called_once()
        
        # Verify result was cached again
        mock_set_cache.assert_called_once()