"""
Unit tests for the SecLend API client implementation that retrieves real-time borrow rates for securities.

These tests verify the behavior of the SecLend API client under various scenarios including 
successful API calls, error handling, fallback mechanisms, and caching behavior.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from decimal import Decimal
import respx
import httpx
import pytest_asyncio

# Import functions to test
from src.backend.services.external.seclend_api import (
    get_borrow_rate,
    async_get_borrow_rate,
    get_fallback_rate,
    map_borrow_status,
    get_cache_key,
    CACHE_KEY_PREFIX
)

# Import necessary constants and exceptions
from src.backend.core.exceptions import ExternalAPIException
from src.backend.core.constants import BorrowStatus, DEFAULT_MINIMUM_BORROW_RATE, CACHE_TTL_BORROW_RATE

# Import test fixtures
from src.backend.tests.fixtures.api_responses import mock_seclend_response, mock_api_error_response


def test_get_cache_key():
    """Tests that the get_cache_key function correctly formats cache keys."""
    # Test lowercase to uppercase conversion
    assert get_cache_key("aapl") == f"{CACHE_KEY_PREFIX}AAPL"
    
    # Test uppercase remains uppercase
    assert get_cache_key("MSFT") == f"{CACHE_KEY_PREFIX}MSFT"
    
    # Test prefix is correctly prepended
    assert get_cache_key("TSLA").startswith(CACHE_KEY_PREFIX)
    
    # Test different ticker symbols
    assert get_cache_key("IBM") == f"{CACHE_KEY_PREFIX}IBM"
    assert get_cache_key("F") == f"{CACHE_KEY_PREFIX}F"
    assert get_cache_key("BRK.A") == f"{CACHE_KEY_PREFIX}BRK.A"
    

def test_map_borrow_status():
    """Tests that the map_borrow_status function correctly maps API status strings to BorrowStatus enum values."""
    # Test mapping API status strings to BorrowStatus enum
    assert map_borrow_status("EASY_TO_BORROW") == BorrowStatus.EASY
    assert map_borrow_status("MEDIUM_TO_BORROW") == BorrowStatus.MEDIUM
    assert map_borrow_status("HARD_TO_BORROW") == BorrowStatus.HARD
    
    # Test case insensitivity
    assert map_borrow_status("easy_to_borrow") == BorrowStatus.EASY
    assert map_borrow_status("medium_to_borrow") == BorrowStatus.MEDIUM
    assert map_borrow_status("hard_to_borrow") == BorrowStatus.HARD
    
    # Test shorthand versions
    assert map_borrow_status("EASY") == BorrowStatus.EASY
    assert map_borrow_status("MEDIUM") == BorrowStatus.MEDIUM
    assert map_borrow_status("HARD") == BorrowStatus.HARD
    
    # Test default to HARD for unknown status
    assert map_borrow_status("UNKNOWN") == BorrowStatus.HARD
    assert map_borrow_status("") == BorrowStatus.HARD


def test_get_fallback_rate():
    """Tests that the get_fallback_rate function returns the correct fallback rate structure."""
    # Test with standard ticker
    fallback = get_fallback_rate("AAPL")
    assert fallback["rate"] == DEFAULT_MINIMUM_BORROW_RATE
    assert fallback["status"] == BorrowStatus.HARD
    assert fallback["ticker"] == "AAPL"
    assert fallback["source"] == "fallback"
    assert fallback["is_fallback"] is True
    
    # Test with another ticker
    fallback = get_fallback_rate("MSFT")
    assert fallback["rate"] == DEFAULT_MINIMUM_BORROW_RATE
    assert fallback["status"] == BorrowStatus.HARD
    assert fallback["ticker"] == "MSFT"
    assert fallback["source"] == "fallback"
    assert fallback["is_fallback"] is True


@respx.mock
@pytest.fixture
def mock_seclend_api():
    """Fixture to mock the SecLend API."""
    return respx.get("https://api.seclend.com/api/borrows/AAPL").mock(
        return_value=httpx.Response(200, json={"rate": 0.05, "status": "EASY_TO_BORROW"})
    )


@pytest.fixture
def mock_redis_cache():
    """Fixture to mock the Redis cache."""
    with patch("src.backend.services.external.seclend_api.redis_cache") as mock_cache:
        mock_cache.get.return_value = None  # Default to cache miss
        mock_cache.set.return_value = True
        yield mock_cache


def test_get_borrow_rate_success(mock_seclend_api, mock_redis_cache, mock_seclend_response):
    """Tests successful retrieval of borrow rate from SecLend API."""
    # Configure mock response for AAPL
    response_data = mock_seclend_response("AAPL")
    mock_seclend_api.return_value = httpx.Response(200, json=response_data)
    
    # Configure settings mock
    with patch("src.backend.services.external.seclend_api.get_settings") as mock_settings:
        settings_instance = MagicMock()
        settings_instance.get_external_api_config.return_value = {
            "base_url": "https://api.seclend.com",
            "api_key": "test_key"
        }
        settings_instance.get_cache_ttl.return_value = CACHE_TTL_BORROW_RATE
        mock_settings.return_value = settings_instance
        
        # Test get_borrow_rate
        result = get_borrow_rate("AAPL")
        
        # Verify the result
        assert result["rate"] == Decimal(str(response_data["rate"]))
        assert result["status"] == map_borrow_status(response_data["status"])
        assert result["ticker"] == "AAPL"
        assert result["source"] == "seclend_api"
        assert "is_fallback" not in result
        
        # Verify cache interaction
        mock_redis_cache.get.assert_called_once()
        mock_redis_cache.set.assert_called_once()


def test_get_borrow_rate_cache_hit(mock_redis_cache):
    """Tests that borrow rate is retrieved from cache when available."""
    # Set up cached data
    cached_data = {
        "rate": Decimal("0.05"),
        "status": BorrowStatus.EASY,
        "ticker": "AAPL",
        "source": "seclend_api"
    }
    mock_redis_cache.get.return_value = cached_data
    
    # Test get_borrow_rate with cache hit
    result = get_borrow_rate("AAPL")
    
    # Verify result is from cache
    assert result == cached_data
    mock_redis_cache.get.assert_called_once()
    
    # Verify no API call was made
    mock_redis_cache.set.assert_not_called()


@respx.mock
def test_get_borrow_rate_cache_miss(mock_seclend_api, mock_redis_cache, mock_seclend_response):
    """Tests that borrow rate is fetched from API when not in cache."""
    # Configure mock response for TSLA
    response_data = mock_seclend_response("TSLA")
    
    # Set up the mock API endpoint
    api_url = "https://api.seclend.com/api/borrows/TSLA"
    respx.get(api_url).mock(return_value=httpx.Response(200, json=response_data))
    
    # Ensure cache miss
    mock_redis_cache.get.return_value = None
    
    # Configure settings mock
    with patch("src.backend.services.external.seclend_api.get_settings") as mock_settings:
        settings_instance = MagicMock()
        settings_instance.get_external_api_config.return_value = {
            "base_url": "https://api.seclend.com",
            "api_key": "test_key"
        }
        settings_instance.get_cache_ttl.return_value = CACHE_TTL_BORROW_RATE
        mock_settings.return_value = settings_instance
        
        # Test get_borrow_rate
        result = get_borrow_rate("TSLA")
        
        # Verify API was called
        assert respx.get(api_url).called
        
        # Verify the result
        assert result["rate"] == Decimal(str(response_data["rate"]))
        assert result["status"] == map_borrow_status(response_data["status"])
        assert result["ticker"] == "TSLA"
        assert result["source"] == "seclend_api"
        
        # Verify cache interactions
        mock_redis_cache.get.assert_called_once()
        mock_redis_cache.set.assert_called_once()
        
        # Verify correct cache TTL was used
        mock_redis_cache.set.assert_called_with(
            get_cache_key("TSLA"), 
            result, 
            ttl=CACHE_TTL_BORROW_RATE
        )


@respx.mock
def test_get_borrow_rate_api_error(mock_seclend_api, mock_redis_cache, mock_api_error_response):
    """Tests fallback behavior when SecLend API returns an error."""
    # Configure mock error response for GME
    error_data = mock_api_error_response("server_error")
    api_url = "https://api.seclend.com/api/borrows/GME"
    respx.get(api_url).mock(return_value=httpx.Response(500, json=error_data))
    
    # Configure settings mock
    with patch("src.backend.services.external.seclend_api.get_settings") as mock_settings:
        settings_instance = MagicMock()
        settings_instance.get_external_api_config.return_value = {
            "base_url": "https://api.seclend.com",
            "api_key": "test_key"
        }
        mock_settings.return_value = settings_instance
        
        # Test get_borrow_rate with API error
        result = get_borrow_rate("GME")
        
        # Verify the fallback result
        assert result["rate"] == DEFAULT_MINIMUM_BORROW_RATE
        assert result["status"] == BorrowStatus.HARD
        assert result["ticker"] == "GME"
        assert result["source"] == "fallback"
        assert result["is_fallback"] is True
        
        # Verify API was called but cache was not updated
        assert respx.get(api_url).called
        mock_redis_cache.get.assert_called_once()
        mock_redis_cache.set.assert_not_called()


@respx.mock
def test_get_borrow_rate_api_timeout(mock_seclend_api, mock_redis_cache):
    """Tests fallback behavior when SecLend API times out."""
    # Configure mock timeout for AMC
    api_url = "https://api.seclend.com/api/borrows/AMC"
    respx.get(api_url).mock(side_effect=httpx.TimeoutException("Connection timeout"))
    
    # Configure settings mock
    with patch("src.backend.services.external.seclend_api.get_settings") as mock_settings:
        settings_instance = MagicMock()
        settings_instance.get_external_api_config.return_value = {
            "base_url": "https://api.seclend.com",
            "api_key": "test_key"
        }
        mock_settings.return_value = settings_instance
        
        # Test get_borrow_rate with API timeout
        result = get_borrow_rate("AMC")
        
        # Verify the fallback result
        assert result["rate"] == DEFAULT_MINIMUM_BORROW_RATE
        assert result["status"] == BorrowStatus.HARD
        assert result["ticker"] == "AMC"
        assert result["source"] == "fallback"
        assert result["is_fallback"] is True
        
        # Verify API was called but cache was not updated
        assert respx.get(api_url).called
        mock_redis_cache.get.assert_called_once()
        mock_redis_cache.set.assert_not_called()


@respx.mock
def test_get_borrow_rate_invalid_response(mock_seclend_api, mock_redis_cache):
    """Tests fallback behavior when SecLend API returns invalid data."""
    # Configure mock invalid JSON response
    api_url = "https://api.seclend.com/api/borrows/INVALID"
    respx.get(api_url).mock(return_value=httpx.Response(200, content="Not a JSON"))
    
    # Configure settings mock
    with patch("src.backend.services.external.seclend_api.get_settings") as mock_settings:
        settings_instance = MagicMock()
        settings_instance.get_external_api_config.return_value = {
            "base_url": "https://api.seclend.com",
            "api_key": "test_key"
        }
        mock_settings.return_value = settings_instance
        
        # Test get_borrow_rate with invalid response
        result = get_borrow_rate("INVALID")
        
        # Verify the fallback result
        assert result["rate"] == DEFAULT_MINIMUM_BORROW_RATE
        assert result["status"] == BorrowStatus.HARD
        assert result["ticker"] == "INVALID"
        assert result["source"] == "fallback"
        assert result["is_fallback"] is True
        
        # Verify API was called but cache was not updated
        assert respx.get(api_url).called
        mock_redis_cache.get.assert_called_once()
        mock_redis_cache.set.assert_not_called()


@respx.mock
def test_get_borrow_rate_missing_fields(mock_seclend_api, mock_redis_cache):
    """Tests fallback behavior when SecLend API response is missing required fields."""
    # Configure mock response missing required fields
    api_url = "https://api.seclend.com/api/borrows/MISSING"
    respx.get(api_url).mock(return_value=httpx.Response(200, json={"ticker": "MISSING"}))
    
    # Configure settings mock
    with patch("src.backend.services.external.seclend_api.get_settings") as mock_settings:
        settings_instance = MagicMock()
        settings_instance.get_external_api_config.return_value = {
            "base_url": "https://api.seclend.com",
            "api_key": "test_key"
        }
        mock_settings.return_value = settings_instance
        
        # Test get_borrow_rate with missing fields
        result = get_borrow_rate("MISSING")
        
        # Verify the fallback result
        assert result["rate"] == DEFAULT_MINIMUM_BORROW_RATE
        assert result["status"] == BorrowStatus.HARD
        assert result["ticker"] == "MISSING"
        assert result["source"] == "fallback"
        assert result["is_fallback"] is True
        
        # Verify API was called but cache was not updated
        assert respx.get(api_url).called
        mock_redis_cache.get.assert_called_once()
        mock_redis_cache.set.assert_not_called()


@pytest.mark.asyncio
@respx.mock
async def test_async_get_borrow_rate_success(mock_seclend_api, mock_redis_cache, mock_seclend_response):
    """Tests successful asynchronous retrieval of borrow rate from SecLend API."""
    # Configure mock response for AAPL
    response_data = mock_seclend_response("AAPL")
    api_url = "https://api.seclend.com/api/borrows/AAPL"
    respx.get(api_url).mock(return_value=httpx.Response(200, json=response_data))
    
    # Configure settings mock
    with patch("src.backend.services.external.seclend_api.get_settings") as mock_settings:
        settings_instance = MagicMock()
        settings_instance.get_external_api_config.return_value = {
            "base_url": "https://api.seclend.com",
            "api_key": "test_key"
        }
        settings_instance.get_cache_ttl.return_value = CACHE_TTL_BORROW_RATE
        mock_settings.return_value = settings_instance
        
        # Test async_get_borrow_rate
        result = await async_get_borrow_rate("AAPL")
        
        # Verify the result
        assert result["rate"] == Decimal(str(response_data["rate"]))
        assert result["status"] == map_borrow_status(response_data["status"])
        assert result["ticker"] == "AAPL"
        assert result["source"] == "seclend_api"
        assert "is_fallback" not in result
        
        # Verify cache interaction
        mock_redis_cache.get.assert_called_once()
        mock_redis_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_async_get_borrow_rate_cache_hit(mock_redis_cache):
    """Tests that borrow rate is retrieved from cache when available in async mode."""
    # Set up cached data
    cached_data = {
        "rate": Decimal("0.05"),
        "status": BorrowStatus.EASY,
        "ticker": "AAPL",
        "source": "seclend_api"
    }
    mock_redis_cache.get.return_value = cached_data
    
    # Test async_get_borrow_rate with cache hit
    result = await async_get_borrow_rate("AAPL")
    
    # Verify result is from cache
    assert result == cached_data
    mock_redis_cache.get.assert_called_once()
    
    # Verify no API call was made
    mock_redis_cache.set.assert_not_called()


@pytest.mark.asyncio
@respx.mock
async def test_async_get_borrow_rate_api_error(mock_seclend_api, mock_redis_cache, mock_api_error_response):
    """Tests fallback behavior when SecLend API returns an error in async mode."""
    # Configure mock error response for GME
    error_data = mock_api_error_response("server_error")
    api_url = "https://api.seclend.com/api/borrows/GME"
    respx.get(api_url).mock(return_value=httpx.Response(500, json=error_data))
    
    # Configure settings mock
    with patch("src.backend.services.external.seclend_api.get_settings") as mock_settings:
        settings_instance = MagicMock()
        settings_instance.get_external_api_config.return_value = {
            "base_url": "https://api.seclend.com",
            "api_key": "test_key"
        }
        mock_settings.return_value = settings_instance
        
        # Test async_get_borrow_rate with API error
        result = await async_get_borrow_rate("GME")
        
        # Verify the fallback result
        assert result["rate"] == DEFAULT_MINIMUM_BORROW_RATE
        assert result["status"] == BorrowStatus.HARD
        assert result["ticker"] == "GME"
        assert result["source"] == "fallback"
        assert result["is_fallback"] is True
        
        # Verify API was called but cache was not updated
        assert respx.get(api_url).called
        mock_redis_cache.get.assert_called_once()
        mock_redis_cache.set.assert_not_called()


@respx.mock
def test_redis_connection_failure(mock_seclend_api, mock_seclend_response):
    """Tests fallback behavior when Redis connection fails."""
    # Configure mock response for AAPL
    response_data = mock_seclend_response("AAPL")
    api_url = "https://api.seclend.com/api/borrows/AAPL"
    respx.get(api_url).mock(return_value=httpx.Response(200, json=response_data))
    
    # Mock Redis to raise an exception
    with patch("src.backend.services.external.seclend_api.redis_cache") as mock_cache:
        mock_cache.get.side_effect = Exception("Redis connection failure")
        mock_cache.set.side_effect = Exception("Redis connection failure")
        
        # Configure settings mock
        with patch("src.backend.services.external.seclend_api.get_settings") as mock_settings:
            settings_instance = MagicMock()
            settings_instance.get_external_api_config.return_value = {
                "base_url": "https://api.seclend.com",
                "api_key": "test_key"
            }
            settings_instance.get_cache_ttl.return_value = CACHE_TTL_BORROW_RATE
            mock_settings.return_value = settings_instance
            
            # Test get_borrow_rate with Redis failure
            result = get_borrow_rate("AAPL")
            
            # Verify API was called
            assert respx.get(api_url).called
            
            # Verify the result comes from API
            assert result["rate"] == Decimal(str(response_data["rate"]))
            assert result["status"] == map_borrow_status(response_data["status"])
            assert result["ticker"] == "AAPL"
            assert result["source"] == "seclend_api"
            
            # Verify Redis interactions happened but failed
            mock_cache.get.assert_called_once()
            assert not mock_cache.set.called  # Should not try to cache due to earlier error