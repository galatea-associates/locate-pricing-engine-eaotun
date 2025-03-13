"""
Unit tests for the Market Volatility API client implementation.

This module tests the functionality of fetching market volatility data, 
handling API errors, caching mechanisms, and fallback strategies when 
the external API is unavailable.
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import patch, MagicMock

from src.backend.services.external.market_api import (
    get_market_volatility_index,
    async_get_market_volatility_index,
    get_stock_volatility,
    async_get_stock_volatility,
    get_volatility_adjustment_factor,
    async_get_volatility_adjustment_factor,
    clear_volatility_cache,
    DEFAULT_VOLATILITY_VALUE,
    CACHE_KEY_PREFIX
)
from src.backend.core.exceptions import ExternalAPIException
from src.backend.tests.fixtures.api_responses import (
    mock_market_volatility_response,
    mock_stock_volatility_response,
    mock_high_volatility_response,
    mock_low_volatility_response,
    mock_api_error_response
)


@pytest.mark.parametrize('use_cache', [True, False])
def test_get_market_volatility_index_success(mock_market_volatility_response, use_cache):
    """Tests successful retrieval of market volatility index."""
    # Mock the get function from client module
    with patch('src.backend.services.external.client.get') as mock_get:
        # Set up the mock to return the mock response
        mock_get.return_value = mock_market_volatility_response
        
        # Mock the Redis cache
        with patch('src.backend.services.external.market_api.get_redis_cache') as mock_redis:
            # Set up cache to return None (cache miss)
            mock_redis.return_value = MagicMock()
            mock_redis.return_value.get.return_value = None
            
            # Call the function under test
            result = get_market_volatility_index(use_cache=use_cache)
            
            # Verify the result
            assert 'value' in result
            assert 'timestamp' in result
            assert result['value'] == mock_market_volatility_response['value']
            
            # Verify the client.get function was called
            mock_get.assert_called_once()
            
            # Verify cache behavior
            if use_cache:
                mock_redis.return_value.get.assert_called_once()
                mock_redis.return_value.set.assert_called_once()


def test_get_market_volatility_index_cache_hit(mock_market_volatility_response):
    """Tests retrieval of market volatility index from cache."""
    # Mock the Redis cache to return cached data
    with patch('src.backend.services.external.market_api.get_redis_cache') as mock_redis:
        # Set up cache to return the mock response (cache hit)
        mock_redis.return_value = MagicMock()
        mock_redis.return_value.get.return_value = mock_market_volatility_response
        
        # Mock client.get to ensure it's not called
        with patch('src.backend.services.external.client.get') as mock_get:
            # Call the function under test
            result = get_market_volatility_index(use_cache=True)
            
            # Verify the result
            assert 'value' in result
            assert 'timestamp' in result
            assert result['value'] == mock_market_volatility_response['value']
            
            # Verify cache was checked
            mock_redis.return_value.get.assert_called_once()
            
            # Verify client.get was not called (because we got a cache hit)
            mock_get.assert_not_called()


def test_get_market_volatility_index_api_error(mock_api_error_response):
    """Tests handling of API errors when fetching market volatility index."""
    # Mock the client.get function to raise an exception
    with patch('src.backend.services.external.client.get') as mock_get:
        mock_get.side_effect = ExternalAPIException("MARKET_VOLATILITY", "API Error")
        
        # Mock the Redis cache
        with patch('src.backend.services.external.market_api.get_redis_cache') as mock_redis:
            # Set up cache to return None (cache miss)
            mock_redis.return_value = MagicMock()
            mock_redis.return_value.get.return_value = None
            
            # Call the function and expect an exception
            with pytest.raises(ExternalAPIException):
                get_market_volatility_index()
            
            # Verify the client.get function was called
            mock_get.assert_called_once()
            
            # Verify cache was checked
            mock_redis.return_value.get.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize('use_cache', [True, False])
async def test_async_get_market_volatility_index_success(mock_market_volatility_response, use_cache):
    """Tests successful asynchronous retrieval of market volatility index."""
    # Mock the async_get function from client module
    with patch('src.backend.services.external.client.async_get') as mock_async_get:
        # Set up the mock to return the mock response
        mock_async_get.return_value = mock_market_volatility_response
        
        # Mock the Redis cache
        with patch('src.backend.services.external.market_api.get_redis_cache') as mock_redis:
            # Set up cache to return None (cache miss)
            mock_redis.return_value = MagicMock()
            mock_redis.return_value.get.return_value = None
            
            # Call the function under test
            result = await async_get_market_volatility_index(use_cache=use_cache)
            
            # Verify the result
            assert 'value' in result
            assert 'timestamp' in result
            assert result['value'] == mock_market_volatility_response['value']
            
            # Verify the client.async_get function was called
            mock_async_get.assert_called_once()
            
            # Verify cache behavior
            if use_cache:
                mock_redis.return_value.get.assert_called_once()
                mock_redis.return_value.set.assert_called_once()


@pytest.mark.parametrize('ticker', ['AAPL', 'TSLA', 'GME'])
@pytest.mark.parametrize('use_cache', [True, False])
def test_get_stock_volatility_success(mock_stock_volatility_response, ticker, use_cache):
    """Tests successful retrieval of stock-specific volatility."""
    # Mock the get function from client module
    with patch('src.backend.services.external.client.get') as mock_get:
        # Set up the mock to return the mock response
        mock_get.return_value = mock_stock_volatility_response(ticker)
        
        # Mock the Redis cache
        with patch('src.backend.services.external.market_api.get_redis_cache') as mock_redis:
            # Set up cache to return None (cache miss)
            mock_redis.return_value = MagicMock()
            mock_redis.return_value.get.return_value = None
            
            # Call the function under test
            result = get_stock_volatility(ticker=ticker, use_cache=use_cache)
            
            # Verify the result
            assert 'ticker' in result
            assert 'volatility' in result
            assert 'timestamp' in result
            assert result['ticker'] == ticker.upper()
            
            # Verify the client.get function was called
            mock_get.assert_called_once()
            
            # Verify cache behavior
            if use_cache:
                mock_redis.return_value.get.assert_called_once()
                mock_redis.return_value.set.assert_called_once()


@pytest.mark.parametrize('ticker', ['AAPL', 'TSLA', 'GME'])
def test_get_stock_volatility_cache_hit(mock_stock_volatility_response, ticker):
    """Tests retrieval of stock-specific volatility from cache."""
    # Mock the Redis cache to return cached data
    with patch('src.backend.services.external.market_api.get_redis_cache') as mock_redis:
        # Set up cache to return the mock response (cache hit)
        mock_redis.return_value = MagicMock()
        mock_redis.return_value.get.return_value = mock_stock_volatility_response(ticker)
        
        # Mock client.get to ensure it's not called
        with patch('src.backend.services.external.client.get') as mock_get:
            # Call the function under test
            result = get_stock_volatility(ticker=ticker, use_cache=True)
            
            # Verify the result
            assert 'ticker' in result
            assert 'volatility' in result
            assert 'timestamp' in result
            assert result['ticker'] == ticker.upper()
            
            # Verify cache was checked
            mock_redis.return_value.get.assert_called_once()
            
            # Verify client.get was not called (because we got a cache hit)
            mock_get.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('ticker', ['AAPL', 'TSLA', 'GME'])
@pytest.mark.parametrize('use_cache', [True, False])
async def test_async_get_stock_volatility_success(mock_stock_volatility_response, ticker, use_cache):
    """Tests successful asynchronous retrieval of stock-specific volatility."""
    # Mock the async_get function from client module
    with patch('src.backend.services.external.client.async_get') as mock_async_get:
        # Set up the mock to return the mock response
        mock_async_get.return_value = mock_stock_volatility_response(ticker)
        
        # Mock the Redis cache
        with patch('src.backend.services.external.market_api.get_redis_cache') as mock_redis:
            # Set up cache to return None (cache miss)
            mock_redis.return_value = MagicMock()
            mock_redis.return_value.get.return_value = None
            
            # Call the function under test
            result = await async_get_stock_volatility(ticker=ticker, use_cache=use_cache)
            
            # Verify the result
            assert 'ticker' in result
            assert 'volatility' in result
            assert 'timestamp' in result
            assert result['ticker'] == ticker.upper()
            
            # Verify the client.async_get function was called
            mock_async_get.assert_called_once()
            
            # Verify cache behavior
            if use_cache:
                mock_redis.return_value.get.assert_called_once()
                mock_redis.return_value.set.assert_called_once()


@pytest.mark.parametrize('ticker', ['AAPL', 'TSLA', 'GME'])
def test_get_volatility_adjustment_factor_stock_specific(mock_stock_volatility_response, ticker):
    """Tests calculation of volatility adjustment factor using stock-specific volatility."""
    # Mock get_stock_volatility to return the stock specific volatility
    with patch('src.backend.services.external.market_api.get_stock_volatility') as mock_get_stock_vol:
        mock_get_stock_vol.return_value = mock_stock_volatility_response(ticker)
        
        # Mock get_market_volatility_index to ensure it's not called
        with patch('src.backend.services.external.market_api.get_market_volatility_index') as mock_get_market_vol:
            # Mock get_settings to return a config with volatility_factor
            with patch('src.backend.services.external.market_api.get_settings') as mock_settings:
                mock_settings.return_value.get_calculation_setting.return_value = 0.01  # 1% per point
                
                # Call the function under test
                result = get_volatility_adjustment_factor(ticker=ticker)
                
                # Verify the result is a Decimal
                assert isinstance(result, Decimal)
                
                # Verify the calculation is correct
                # The adjustment factor is volatility * volatility_factor
                expected_volatility = Decimal(str(mock_stock_volatility_response(ticker)['volatility']))
                expected_adjustment = expected_volatility * Decimal('0.01')
                assert result == expected_adjustment
                
                # Verify get_stock_volatility was called
                mock_get_stock_vol.assert_called_once_with(ticker, use_cache=True)
                
                # Verify get_market_volatility_index was not called
                mock_get_market_vol.assert_not_called()


@pytest.mark.parametrize('ticker', ['AAPL', 'TSLA', 'GME'])
def test_get_volatility_adjustment_factor_fallback_to_market(mock_market_volatility_response, ticker):
    """Tests fallback to market volatility when stock-specific volatility is unavailable."""
    # Mock get_stock_volatility to raise an exception
    with patch('src.backend.services.external.market_api.get_stock_volatility') as mock_get_stock_vol:
        mock_get_stock_vol.side_effect = ExternalAPIException("MARKET_VOLATILITY", "API Error")
        
        # Mock get_market_volatility_index to return market volatility
        with patch('src.backend.services.external.market_api.get_market_volatility_index') as mock_get_market_vol:
            mock_get_market_vol.return_value = mock_market_volatility_response
            
            # Mock get_settings to return a config with volatility_factor
            with patch('src.backend.services.external.market_api.get_settings') as mock_settings:
                mock_settings.return_value.get_calculation_setting.return_value = 0.01  # 1% per point
                
                # Call the function under test
                result = get_volatility_adjustment_factor(ticker=ticker)
                
                # Verify the result is a Decimal
                assert isinstance(result, Decimal)
                
                # Verify the calculation is correct
                # The adjustment factor is volatility * volatility_factor
                expected_volatility = Decimal(str(mock_market_volatility_response['value']))
                expected_adjustment = expected_volatility * Decimal('0.01')
                assert result == expected_adjustment
                
                # Verify get_stock_volatility was called
                mock_get_stock_vol.assert_called_once_with(ticker, use_cache=True)
                
                # Verify get_market_volatility_index was called as a fallback
                mock_get_market_vol.assert_called_once_with(use_cache=True)


@pytest.mark.parametrize('ticker', ['AAPL', 'TSLA', 'GME'])
def test_get_volatility_adjustment_factor_default_value(ticker):
    """Tests use of default volatility value when both stock-specific and market volatility are unavailable."""
    # Mock get_stock_volatility to raise an exception
    with patch('src.backend.services.external.market_api.get_stock_volatility') as mock_get_stock_vol:
        mock_get_stock_vol.side_effect = ExternalAPIException("MARKET_VOLATILITY", "API Error")
        
        # Mock get_market_volatility_index to also raise an exception
        with patch('src.backend.services.external.market_api.get_market_volatility_index') as mock_get_market_vol:
            mock_get_market_vol.side_effect = ExternalAPIException("MARKET_VOLATILITY", "API Error")
            
            # Mock get_settings to return a config with volatility_factor
            with patch('src.backend.services.external.market_api.get_settings') as mock_settings:
                mock_settings.return_value.get_calculation_setting.return_value = 0.01  # 1% per point
                
                # Call the function under test
                result = get_volatility_adjustment_factor(ticker=ticker)
                
                # Verify the result is a Decimal
                assert isinstance(result, Decimal)
                
                # Verify the calculation is correct using DEFAULT_VOLATILITY_VALUE
                expected_adjustment = DEFAULT_VOLATILITY_VALUE * Decimal('0.01')
                assert result == expected_adjustment
                
                # Verify both APIs were attempted
                mock_get_stock_vol.assert_called_once_with(ticker, use_cache=True)
                mock_get_market_vol.assert_called_once_with(use_cache=True)


@pytest.mark.asyncio
@pytest.mark.parametrize('ticker', ['AAPL', 'TSLA', 'GME'])
async def test_async_get_volatility_adjustment_factor(mock_stock_volatility_response, ticker):
    """Tests asynchronous calculation of volatility adjustment factor."""
    # Mock async_get_stock_volatility to return the stock specific volatility
    with patch('src.backend.services.external.market_api.async_get_stock_volatility') as mock_async_get_stock_vol:
        mock_async_get_stock_vol.return_value = mock_stock_volatility_response(ticker)
        
        # Mock async_get_market_volatility_index to ensure it's not called
        with patch('src.backend.services.external.market_api.async_get_market_volatility_index') as mock_async_get_market_vol:
            # Mock get_settings to return a config with volatility_factor
            with patch('src.backend.services.external.market_api.get_settings') as mock_settings:
                mock_settings.return_value.get_calculation_setting.return_value = 0.01  # 1% per point
                
                # Call the function under test
                result = await async_get_volatility_adjustment_factor(ticker=ticker)
                
                # Verify the result is a Decimal
                assert isinstance(result, Decimal)
                
                # Verify the calculation is correct
                # The adjustment factor is volatility * volatility_factor
                expected_volatility = Decimal(str(mock_stock_volatility_response(ticker)['volatility']))
                expected_adjustment = expected_volatility * Decimal('0.01')
                assert result == expected_adjustment
                
                # Verify async_get_stock_volatility was called
                mock_async_get_stock_vol.assert_called_once_with(ticker, use_cache=True)
                
                # Verify async_get_market_volatility_index was not called
                mock_async_get_market_vol.assert_not_called()


def test_clear_volatility_cache_specific_ticker():
    """Tests clearing cache for a specific ticker."""
    # Mock the Redis cache
    with patch('src.backend.services.external.market_api.get_redis_cache') as mock_redis:
        # Set up mock to return True for delete
        mock_redis.return_value = MagicMock()
        mock_redis.return_value.delete.return_value = True
        
        # Call the function under test with a specific ticker
        ticker = "AAPL"
        result = clear_volatility_cache(ticker)
        
        # Verify the Redis delete method was called with the correct key
        mock_redis.return_value.delete.assert_called_once_with(f"stock:{ticker}")
        
        # Verify the result is True
        assert result is True


def test_clear_volatility_cache_all():
    """Tests clearing all volatility cache entries."""
    # Mock the Redis cache
    with patch('src.backend.services.external.market_api.get_redis_cache') as mock_redis:
        # Create a mock Redis client
        mock_client = MagicMock()
        
        # Set up the cache keys to return when scanning
        cache_keys = [
            f"{CACHE_KEY_PREFIX}stock:AAPL",
            f"{CACHE_KEY_PREFIX}stock:TSLA",
            f"{CACHE_KEY_PREFIX}market_index"
        ]
        mock_client.keys.return_value = cache_keys
        
        # Set the mock client on the mock cache instance
        mock_redis.return_value._client = mock_client
        mock_redis.return_value.delete.return_value = True
        
        # Call the function under test without a specific ticker
        result = clear_volatility_cache()
        
        # Verify the Redis keys method was called to scan for keys
        mock_client.keys.assert_called_once()
        
        # Verify the Redis delete method was called for each key
        assert mock_redis.return_value.delete.call_count == len(cache_keys)
        
        # Verify the result is True
        assert result is True