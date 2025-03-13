# Third-party imports
import pytest  # pytest 7.4.0+
from unittest.mock import patch, MagicMock  # standard library
from decimal import Decimal  # standard library
import httpx  # httpx 0.25.0+

# Internal imports
from ...tests.fixtures.api_responses import mock_event_calendar_response, mock_high_event_risk_response, mock_no_event_risk_response, mock_api_error_response
from ...tests.conftest import mock_event_calendar_api, mock_redis_cache
from ...core.constants import DEFAULT_EVENT_RISK_FACTOR
from ...core.exceptions import CalculationException, ExternalAPIException
from ...services.calculation.event_risk import get_default_event_risk_factor, get_cached_event_risk_factor, cache_event_risk_factor, fetch_event_risk_factor_from_api, validate_event_risk_factor, calculate_event_risk_adjustment, apply_event_risk_adjustment, get_event_risk_data, format_event_risk_adjustment

def test_get_default_event_risk_factor():
    """Tests that the default event risk factor is returned correctly"""
    assert get_default_event_risk_factor() == 0

def test_get_cached_event_risk_factor_hit(mock_redis_cache):
    """Tests retrieving an event risk factor from cache when it exists"""
    ticker = "AAPL"
    mock_redis_cache.set(f"event_risk:{ticker}", "5")
    assert get_cached_event_risk_factor(ticker) == 5

def test_get_cached_event_risk_factor_miss(mock_redis_cache):
    """Tests retrieving an event risk factor from cache when it doesn't exist"""
    ticker = "AAPL"
    assert get_cached_event_risk_factor(ticker) is None

def test_cache_event_risk_factor(mock_redis_cache):
    """Tests caching an event risk factor"""
    ticker = "AAPL"
    risk_factor = 5
    assert cache_event_risk_factor(ticker, risk_factor) is True
    cached_value = mock_redis_cache.get(f"event_risk:{ticker}")
    assert cached_value == str(risk_factor)

@pytest.mark.asyncio
async def test_fetch_event_risk_factor_from_api(mock_event_calendar_api):
    """Tests fetching event risk factor directly from the API"""
    ticker = "AAPL"
    mock_event_calendar_api.get(f"https://event-calendar-api.example.com/api/events?ticker={ticker}").mock(return_value=httpx.Response(200, json={"events": [{"risk_factor": 3}], "count": 1, "timestamp": "2023-11-19T12:00:00Z"}))
    risk_factor = await fetch_event_risk_factor_from_api(ticker)
    assert risk_factor == 3

@pytest.mark.asyncio
async def test_fetch_event_risk_factor_from_api_error(mock_event_calendar_api):
    """Tests handling of API errors when fetching event risk factor"""
    ticker = "AAPL"
    mock_event_calendar_api.get(f"https://event-calendar-api.example.com/api/events?ticker={ticker}").mock(return_value=httpx.Response(500, json={"error": "API Error"}))
    with pytest.raises(ExternalAPIException):
        await fetch_event_risk_factor_from_api(ticker)

def test_validate_event_risk_factor_valid():
    """Tests validation of valid event risk factors"""
    assert validate_event_risk_factor(0) == 0
    assert validate_event_risk_factor(5) == 5
    assert validate_event_risk_factor("3") == 3

def test_validate_event_risk_factor_none():
    """Tests validation when event risk factor is None"""
    assert validate_event_risk_factor(None) == 0

def test_validate_event_risk_factor_negative():
    """Tests validation of negative event risk factors"""
    with pytest.raises(CalculationException):
        validate_event_risk_factor(-1)

def test_validate_event_risk_factor_too_high():
    """Tests validation of event risk factors that exceed the maximum"""
    assert validate_event_risk_factor(15) == 10

def test_calculate_event_risk_adjustment():
    """Tests calculation of event risk adjustment factor"""
    assert calculate_event_risk_adjustment(5) == Decimal('0.0025')
    assert calculate_event_risk_adjustment(0) == Decimal('0.0000')
    assert calculate_event_risk_adjustment(5, risk_multiplier=Decimal('0.01')) == Decimal('0.0050')

def test_apply_event_risk_adjustment():
    """Tests applying event risk adjustment to a base rate"""
    base_rate = Decimal('0.10')
    assert apply_event_risk_adjustment(base_rate, 5) == Decimal('0.1025')
    assert apply_event_risk_adjustment(base_rate, 0) == Decimal('0.1000')
    assert apply_event_risk_adjustment(base_rate, 5, risk_multiplier=Decimal('0.01')) == Decimal('0.1050')

def test_get_event_risk_data_from_cache(mock_redis_cache):
    """Tests retrieving event risk data from cache"""
    ticker = "AAPL"
    mock_redis_cache.set(f"event_risk:{ticker}", "5")
    assert get_event_risk_data(ticker, use_cache=True) == 5

@pytest.mark.asyncio
async def test_get_event_risk_data_from_api(mock_redis_cache, mock_event_calendar_api):
    """Tests retrieving event risk data from API when not in cache"""
    ticker = "AAPL"
    mock_event_calendar_api.get(f"https://event-calendar-api.example.com/api/events?ticker={ticker}").mock(return_value=httpx.Response(200, json={"events": [{"risk_factor": 3}], "count": 1, "timestamp": "2023-11-19T12:00:00Z"}))
    risk_factor = get_event_risk_data(ticker)
    assert risk_factor == 3
    cached_value = mock_redis_cache.get(f"event_risk:{ticker}")
    assert cached_value == "3"

@pytest.mark.asyncio
async def test_get_event_risk_data_api_error(mock_redis_cache, mock_event_calendar_api):
    """Tests fallback to default when API fails"""
    ticker = "AAPL"
    mock_event_calendar_api.get(f"https://event-calendar-api.example.com/api/events?ticker={ticker}").mock(return_value=httpx.Response(500, json={"error": "API Error"}))
    risk_factor = get_event_risk_data(ticker)
    assert risk_factor == 0
    cached_value = mock_redis_cache.get(f"event_risk:{ticker}")
    assert cached_value is None

@pytest.mark.asyncio
async def test_get_event_risk_data_bypass_cache(mock_redis_cache, mock_event_calendar_api):
    """Tests retrieving event risk data directly from API bypassing cache"""
    ticker = "AAPL"
    mock_redis_cache.set(f"event_risk:{ticker}", "5")
    mock_event_calendar_api.get(f"https://event-calendar-api.example.com/api/events?ticker={ticker}").mock(return_value=httpx.Response(200, json={"events": [{"risk_factor": 3}], "count": 1, "timestamp": "2023-11-19T12:00:00Z"}))
    risk_factor = get_event_risk_data(ticker, use_cache=False)
    assert risk_factor == 3
    cached_value = mock_redis_cache.get(f"event_risk:{ticker}")
    assert cached_value == "3"

def test_format_event_risk_adjustment():
    """Tests formatting of event risk adjustment for reporting"""
    original_rate = Decimal('0.10')
    adjusted_rate = Decimal('0.11')
    risk_factor = 5
    formatted = format_event_risk_adjustment(original_rate, adjusted_rate, risk_factor)
    assert formatted['original_rate'] == 0.10
    assert formatted['adjusted_rate'] == 0.11
    assert formatted['risk_factor'] == 5
    assert formatted['risk_level'] == "MEDIUM"
    assert formatted['adjustment_amount'] == 0.01
    assert formatted['adjustment_percentage'] == Decimal('10.00')

@pytest.mark.asyncio
async def test_integration_event_risk_adjustment(mock_redis_cache, mock_event_calendar_api):
    """Integration test for the complete event risk adjustment flow"""
    ticker = "AAPL"
    base_rate = Decimal('0.10')
    mock_event_calendar_api.get(f"https://event-calendar-api.example.com/api/events?ticker={ticker}").mock(return_value=httpx.Response(200, json={"events": [{"risk_factor": 5}], "count": 1, "timestamp": "2023-11-19T12:00:00Z"}))
    
    risk_factor = get_event_risk_data(ticker)
    adjusted_rate = apply_event_risk_adjustment(base_rate, risk_factor)
    formatted = format_event_risk_adjustment(base_rate, adjusted_rate, risk_factor)
    
    assert adjusted_rate == Decimal('0.1025')
    assert formatted['original_rate'] == 0.10
    assert formatted['adjusted_rate'] == 0.1025
    assert formatted['risk_factor'] == 5
    assert formatted['risk_level'] == "MEDIUM"
    assert formatted['adjustment_amount'] == 0.0025
    assert formatted['adjustment_percentage'] == Decimal('2.50')