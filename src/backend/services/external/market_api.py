"""
Implementation of the Market Volatility API client for the Borrow Rate & Locate Fee Pricing Engine.

This module provides functions to fetch real-time market volatility data, which is used
to adjust borrow rates based on market conditions. It handles API authentication, request
formatting, response parsing, and implements fallback mechanisms for when the external
API is unavailable.
"""

from decimal import Decimal
from typing import Dict, Optional, Any, Union

from .client import get, async_get, validate_response, build_url
from ...core.exceptions import ExternalAPIException
from ...config.settings import get_settings
from ...utils.logging import setup_logger
from ...core.constants import ExternalAPIs
from ..cache.redis import RedisCache

# Initialize logger
logger = setup_logger('market_api')

# Cache key prefix for market volatility data
CACHE_KEY_PREFIX = 'market_volatility:'

# Default value for when volatility data is unavailable
DEFAULT_VOLATILITY_VALUE = Decimal('20.0')

# Required fields for API response validation
REQUIRED_VOLATILITY_FIELDS = ['value', 'timestamp']
REQUIRED_TICKER_VOLATILITY_FIELDS = ['ticker', 'volatility', 'timestamp']

# Global cache instance
_redis_cache = None


def get_redis_cache() -> RedisCache:
    """
    Gets or initializes the Redis cache instance.
    
    Returns:
        RedisCache: Redis cache instance
    """
    global _redis_cache
    if _redis_cache is None:
        # Get Redis configuration from settings
        settings = get_settings()
        redis_config = settings.redis_url
        
        # Parse Redis URL or use configuration directly
        # This would depend on the actual implementation of RedisCache
        # For now, we'll pass the URL directly and let RedisCache handle it
        _redis_cache = RedisCache(
            host=redis_config,
            port=None,  # Not needed if URL contains port
            prefix=CACHE_KEY_PREFIX
        )
        logger.info("Initialized Redis cache for market volatility data")
    
    return _redis_cache


def get_market_volatility_index(use_cache: Optional[bool] = True) -> Dict[str, Any]:
    """
    Fetches the current market volatility index (e.g., VIX).
    
    Args:
        use_cache: Whether to use cached data if available. Defaults to True.
        
    Returns:
        Dict[str, Any]: Volatility data including value and timestamp
        
    Raises:
        ExternalAPIException: If the external API is unavailable and no fallback data exists
    """
    cache_key = "market_index"
    
    # Try to get from cache if use_cache is True
    if use_cache:
        cache = get_redis_cache()
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("Cache hit for market volatility index")
            return cached_data
    
    # If not in cache or use_cache is False, fetch from API
    try:
        # Get API configuration from settings
        settings = get_settings()
        api_config = settings.get_external_api_config(ExternalAPIs.MARKET_VOLATILITY)
        
        # Build the API URL
        base_url = api_config.get('base_url')
        endpoint = 'market/volatility/index'
        url = build_url(base_url, endpoint)
        
        # Prepare headers with API key
        headers = {
            'X-API-Key': api_config.get('api_key'),
            'Content-Type': 'application/json'
        }
        
        # Make the API request
        response = get(
            url=url,
            service_name=ExternalAPIs.MARKET_VOLATILITY,
            headers=headers,
            timeout=api_config.get('timeout_seconds', 30)
        )
        
        # Validate response contains required fields
        if not validate_response(response, REQUIRED_VOLATILITY_FIELDS):
            logger.error("Invalid response from market volatility API")
            raise ExternalAPIException(
                ExternalAPIs.MARKET_VOLATILITY,
                "Missing required fields in API response"
            )
        
        # Cache the response if valid
        if use_cache:
            cache = get_redis_cache()
            cache.set(
                cache_key, 
                response, 
                ttl=settings.get_cache_ttl('volatility')
            )
        
        logger.info(f"Successfully fetched market volatility index: {response.get('value')}")
        return response
        
    except ExternalAPIException as e:
        logger.error(f"Failed to fetch market volatility index: {str(e)}")
        raise


async def async_get_market_volatility_index(use_cache: Optional[bool] = True) -> Dict[str, Any]:
    """
    Asynchronously fetches the current market volatility index.
    
    Args:
        use_cache: Whether to use cached data if available. Defaults to True.
        
    Returns:
        Dict[str, Any]: Volatility data including value and timestamp
        
    Raises:
        ExternalAPIException: If the external API is unavailable and no fallback data exists
    """
    cache_key = "market_index"
    
    # Try to get from cache if use_cache is True
    if use_cache:
        cache = get_redis_cache()
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("Cache hit for market volatility index (async)")
            return cached_data
    
    # If not in cache or use_cache is False, fetch from API
    try:
        # Get API configuration from settings
        settings = get_settings()
        api_config = settings.get_external_api_config(ExternalAPIs.MARKET_VOLATILITY)
        
        # Build the API URL
        base_url = api_config.get('base_url')
        endpoint = 'market/volatility/index'
        url = build_url(base_url, endpoint)
        
        # Prepare headers with API key
        headers = {
            'X-API-Key': api_config.get('api_key'),
            'Content-Type': 'application/json'
        }
        
        # Make the API request asynchronously
        response = await async_get(
            url=url,
            service_name=ExternalAPIs.MARKET_VOLATILITY,
            headers=headers,
            timeout=api_config.get('timeout_seconds', 30)
        )
        
        # Validate response contains required fields
        if not validate_response(response, REQUIRED_VOLATILITY_FIELDS):
            logger.error("Invalid response from market volatility API (async)")
            raise ExternalAPIException(
                ExternalAPIs.MARKET_VOLATILITY,
                "Missing required fields in API response"
            )
        
        # Cache the response if valid
        if use_cache:
            cache = get_redis_cache()
            cache.set(
                cache_key, 
                response, 
                ttl=settings.get_cache_ttl('volatility')
            )
        
        logger.info(f"Successfully fetched market volatility index (async): {response.get('value')}")
        return response
        
    except ExternalAPIException as e:
        logger.error(f"Failed to fetch market volatility index (async): {str(e)}")
        raise


def get_stock_volatility(ticker: str, use_cache: Optional[bool] = True) -> Dict[str, Any]:
    """
    Fetches volatility metrics for a specific stock.
    
    Args:
        ticker: Stock symbol
        use_cache: Whether to use cached data if available. Defaults to True.
        
    Returns:
        Dict[str, Any]: Stock-specific volatility data
        
    Raises:
        ExternalAPIException: If the external API is unavailable and no fallback data exists
    """
    cache_key = f"stock:{ticker}"
    
    # Try to get from cache if use_cache is True
    if use_cache:
        cache = get_redis_cache()
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for stock volatility: {ticker}")
            return cached_data
    
    # If not in cache or use_cache is False, fetch from API
    try:
        # Get API configuration from settings
        settings = get_settings()
        api_config = settings.get_external_api_config(ExternalAPIs.MARKET_VOLATILITY)
        
        # Build the API URL
        base_url = api_config.get('base_url')
        endpoint = f'market/volatility/stock/{ticker}'
        url = build_url(base_url, endpoint)
        
        # Prepare headers with API key
        headers = {
            'X-API-Key': api_config.get('api_key'),
            'Content-Type': 'application/json'
        }
        
        # Make the API request
        response = get(
            url=url,
            service_name=ExternalAPIs.MARKET_VOLATILITY,
            headers=headers,
            timeout=api_config.get('timeout_seconds', 30)
        )
        
        # Validate response contains required fields
        if not validate_response(response, REQUIRED_TICKER_VOLATILITY_FIELDS):
            logger.error(f"Invalid response from stock volatility API for {ticker}")
            raise ExternalAPIException(
                ExternalAPIs.MARKET_VOLATILITY,
                f"Missing required fields in API response for {ticker}"
            )
        
        # Cache the response if valid
        if use_cache:
            cache = get_redis_cache()
            cache.set(
                cache_key, 
                response, 
                ttl=settings.get_cache_ttl('volatility')
            )
        
        logger.info(f"Successfully fetched stock volatility for {ticker}: {response.get('volatility')}")
        return response
        
    except ExternalAPIException as e:
        logger.error(f"Failed to fetch stock volatility for {ticker}: {str(e)}")
        raise


async def async_get_stock_volatility(ticker: str, use_cache: Optional[bool] = True) -> Dict[str, Any]:
    """
    Asynchronously fetches volatility metrics for a specific stock.
    
    Args:
        ticker: Stock symbol
        use_cache: Whether to use cached data if available. Defaults to True.
        
    Returns:
        Dict[str, Any]: Stock-specific volatility data
        
    Raises:
        ExternalAPIException: If the external API is unavailable and no fallback data exists
    """
    cache_key = f"stock:{ticker}"
    
    # Try to get from cache if use_cache is True
    if use_cache:
        cache = get_redis_cache()
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for stock volatility (async): {ticker}")
            return cached_data
    
    # If not in cache or use_cache is False, fetch from API
    try:
        # Get API configuration from settings
        settings = get_settings()
        api_config = settings.get_external_api_config(ExternalAPIs.MARKET_VOLATILITY)
        
        # Build the API URL
        base_url = api_config.get('base_url')
        endpoint = f'market/volatility/stock/{ticker}'
        url = build_url(base_url, endpoint)
        
        # Prepare headers with API key
        headers = {
            'X-API-Key': api_config.get('api_key'),
            'Content-Type': 'application/json'
        }
        
        # Make the API request asynchronously
        response = await async_get(
            url=url,
            service_name=ExternalAPIs.MARKET_VOLATILITY,
            headers=headers,
            timeout=api_config.get('timeout_seconds', 30)
        )
        
        # Validate response contains required fields
        if not validate_response(response, REQUIRED_TICKER_VOLATILITY_FIELDS):
            logger.error(f"Invalid response from stock volatility API for {ticker} (async)")
            raise ExternalAPIException(
                ExternalAPIs.MARKET_VOLATILITY,
                f"Missing required fields in API response for {ticker}"
            )
        
        # Cache the response if valid
        if use_cache:
            cache = get_redis_cache()
            cache.set(
                cache_key, 
                response, 
                ttl=settings.get_cache_ttl('volatility')
            )
        
        logger.info(f"Successfully fetched stock volatility for {ticker} (async): {response.get('volatility')}")
        return response
        
    except ExternalAPIException as e:
        logger.error(f"Failed to fetch stock volatility for {ticker} (async): {str(e)}")
        raise


def get_volatility_adjustment_factor(ticker: str, use_cache: Optional[bool] = True) -> Decimal:
    """
    Calculates the volatility adjustment factor for a stock.
    
    This factor is used to adjust the borrow rate based on market volatility.
    
    Args:
        ticker: Stock symbol
        use_cache: Whether to use cached data if available. Defaults to True.
        
    Returns:
        Decimal: Volatility adjustment factor for borrow rate calculation
    """
    settings = get_settings()
    volatility_value = None
    source = None
    
    # Try to get stock-specific volatility first
    try:
        stock_volatility = get_stock_volatility(ticker, use_cache=use_cache)
        volatility_value = stock_volatility.get('volatility')
        source = f"stock-specific volatility for {ticker}"
    except ExternalAPIException:
        logger.warning(f"Failed to get stock-specific volatility for {ticker}, falling back to market index")
        # If stock-specific volatility fails, try market index
        try:
            market_volatility = get_market_volatility_index(use_cache=use_cache)
            volatility_value = market_volatility.get('value')
            source = "market volatility index"
        except ExternalAPIException:
            logger.warning("Failed to get market volatility index, using default value")
            # If both APIs fail, use DEFAULT_VOLATILITY_VALUE
            volatility_value = float(DEFAULT_VOLATILITY_VALUE)
            source = "default value"
    
    logger.info(f"Using {source} ({volatility_value}) for volatility adjustment")
    
    # Convert to Decimal for precise calculation
    # Handle different possible types (int, float, Decimal, str)
    if isinstance(volatility_value, (int, float)):
        volatility_decimal = Decimal(str(volatility_value))
    elif isinstance(volatility_value, Decimal):
        volatility_decimal = volatility_value
    elif isinstance(volatility_value, str):
        try:
            volatility_decimal = Decimal(volatility_value)
        except Exception:
            logger.error(f"Failed to convert volatility value '{volatility_value}' to Decimal, using default")
            volatility_decimal = DEFAULT_VOLATILITY_VALUE
    else:
        logger.error(f"Unexpected volatility value type: {type(volatility_value)}, using default")
        volatility_decimal = DEFAULT_VOLATILITY_VALUE
    
    # Get volatility factor from settings
    try:
        volatility_factor = Decimal(str(settings.get_calculation_setting('default_volatility_factor')))
    except Exception as e:
        logger.error(f"Failed to get volatility factor from settings: {str(e)}, using default")
        # Default factor - typically 0.01 (1% adjustment per point of volatility)
        volatility_factor = Decimal('0.01')
    
    # Calculate adjustment factor
    adjustment_factor = volatility_decimal * volatility_factor
    
    logger.info(f"Calculated volatility adjustment factor for {ticker}: {adjustment_factor}")
    return adjustment_factor


async def async_get_volatility_adjustment_factor(ticker: str, use_cache: Optional[bool] = True) -> Decimal:
    """
    Asynchronously calculates the volatility adjustment factor for a stock.
    
    This factor is used to adjust the borrow rate based on market volatility.
    
    Args:
        ticker: Stock symbol
        use_cache: Whether to use cached data if available. Defaults to True.
        
    Returns:
        Decimal: Volatility adjustment factor for borrow rate calculation
    """
    settings = get_settings()
    volatility_value = None
    source = None
    
    # Try to get stock-specific volatility first
    try:
        stock_volatility = await async_get_stock_volatility(ticker, use_cache=use_cache)
        volatility_value = stock_volatility.get('volatility')
        source = f"stock-specific volatility for {ticker}"
    except ExternalAPIException:
        logger.warning(f"Failed to get stock-specific volatility for {ticker}, falling back to market index (async)")
        # If stock-specific volatility fails, try market index
        try:
            market_volatility = await async_get_market_volatility_index(use_cache=use_cache)
            volatility_value = market_volatility.get('value')
            source = "market volatility index"
        except ExternalAPIException:
            logger.warning("Failed to get market volatility index, using default value (async)")
            # If both APIs fail, use DEFAULT_VOLATILITY_VALUE
            volatility_value = float(DEFAULT_VOLATILITY_VALUE)
            source = "default value"
    
    logger.info(f"Using {source} ({volatility_value}) for volatility adjustment (async)")
    
    # Convert to Decimal for precise calculation
    # Handle different possible types (int, float, Decimal, str)
    if isinstance(volatility_value, (int, float)):
        volatility_decimal = Decimal(str(volatility_value))
    elif isinstance(volatility_value, Decimal):
        volatility_decimal = volatility_value
    elif isinstance(volatility_value, str):
        try:
            volatility_decimal = Decimal(volatility_value)
        except Exception:
            logger.error(f"Failed to convert volatility value '{volatility_value}' to Decimal, using default (async)")
            volatility_decimal = DEFAULT_VOLATILITY_VALUE
    else:
        logger.error(f"Unexpected volatility value type: {type(volatility_value)}, using default (async)")
        volatility_decimal = DEFAULT_VOLATILITY_VALUE
    
    # Get volatility factor from settings
    try:
        volatility_factor = Decimal(str(settings.get_calculation_setting('default_volatility_factor')))
    except Exception as e:
        logger.error(f"Failed to get volatility factor from settings: {str(e)}, using default (async)")
        # Default factor - typically 0.01 (1% adjustment per point of volatility)
        volatility_factor = Decimal('0.01')
    
    # Calculate adjustment factor
    adjustment_factor = volatility_decimal * volatility_factor
    
    logger.info(f"Calculated volatility adjustment factor for {ticker} (async): {adjustment_factor}")
    return adjustment_factor


def clear_volatility_cache(ticker: Optional[str] = None) -> bool:
    """
    Clears cached volatility data for a specific ticker or all volatility data.
    
    Args:
        ticker: Stock symbol to clear cache for. If None, all volatility cache will be cleared.
        
    Returns:
        bool: True if cache was successfully cleared
    """
    cache = get_redis_cache()
    
    if ticker:
        # Clear cache for specific ticker
        cache_key = f"stock:{ticker}"
        success = cache.delete(cache_key)
        logger.info(f"Cleared volatility cache for {ticker}: {success}")
        return success
    else:
        # Clear all volatility cache
        try:
            # Try to use the flush method if available
            if hasattr(cache, 'flush') and callable(getattr(cache, 'flush')):
                success = cache.flush()
                logger.info("Cleared all volatility cache")
                return success
            else:
                # Get all keys with the prefix and delete them
                keys = cache._client.keys(f"{CACHE_KEY_PREFIX}*")
                if keys:
                    for key in keys:
                        cache.delete(key)
                    logger.info(f"Cleared all volatility cache ({len(keys)} keys)")
                    return True
                else:
                    logger.info("No volatility cache found to clear")
                    return True
        except Exception as e:
            logger.error(f"Failed to clear all volatility cache: {str(e)}")
            return False