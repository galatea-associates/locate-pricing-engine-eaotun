"""
Implementation of the SecLend API client for retrieving real-time borrow rates for securities.

This module provides functions to fetch current borrow rates, check stock availability,
and handle API failures with appropriate fallback mechanisms.
"""

from typing import Dict, Optional, Any
from decimal import Decimal

# Import HTTP client functions with retry and circuit-breaker patterns
from .client import get, async_get, build_url, validate_response

# Import exceptions and constants
from ...core.exceptions import ExternalAPIException
from ...core.constants import ExternalAPIs, BorrowStatus, DEFAULT_MINIMUM_BORROW_RATE

# Import settings and logging
from ...config.settings import get_settings
from ...utils.logging import setup_logger

# Import Redis cache
from ..cache.redis import RedisCache

# Set up logger
logger = setup_logger('seclend_api')

# Constants for API response validation
REQUIRED_RATE_FIELDS = ['rate', 'status']

# Cache key prefix for borrow rates
CACHE_KEY_PREFIX = 'seclend_rate:'

# Initialize Redis cache
redis_cache = RedisCache()

def get_borrow_rate(ticker: str) -> Dict[str, Any]:
    """
    Retrieves the current borrow rate for a specific ticker from SecLend API.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Dict[str, Any]: Dictionary containing borrow rate and status
    """
    # Generate cache key for this ticker
    cache_key = get_cache_key(ticker)
    
    # Check if we have this rate in cache
    try:
        cached_data = redis_cache.get(cache_key)
        if cached_data:
            logger.info(f"Using cached borrow rate for {ticker}")
            return cached_data
    except Exception as e:
        logger.warning(f"Error accessing cache for {ticker}: {str(e)}")
    
    # Get API configuration from settings
    settings = get_settings()
    seclend_config = settings.get_external_api_config(ExternalAPIs.SECLEND)
    
    # Build API URL
    base_url = seclend_config['base_url']
    endpoint = f"api/borrows/{ticker}"
    url = build_url(base_url, endpoint)
    
    # Set up API headers
    headers = {
        'X-API-Key': seclend_config['api_key'],
        'Content-Type': 'application/json'
    }
    
    try:
        # Call the SecLend API
        logger.info(f"Fetching borrow rate for {ticker} from SecLend API")
        response_data = get(
            url=url,
            service_name=ExternalAPIs.SECLEND,
            headers=headers,
            timeout=seclend_config.get('timeout_seconds', 10),
            fallback_value=None
        )
        
        # If the request failed and returned None, use fallback
        if response_data is None:
            return get_fallback_rate(ticker)
        
        # Validate the response contains required fields
        if not validate_response(response_data, REQUIRED_RATE_FIELDS):
            logger.error(f"Invalid response from SecLend API for {ticker}: missing required fields")
            return get_fallback_rate(ticker)
        
        # Map API status to BorrowStatus enum
        api_status = response_data['status']
        borrow_status = map_borrow_status(api_status)
        
        # Create the result dictionary
        result = {
            'rate': Decimal(str(response_data['rate'])),
            'status': borrow_status,
            'ticker': ticker,
            'source': 'seclend_api'
        }
        
        # Cache the result
        try:
            cache_ttl = settings.get_cache_ttl('borrow_rate')
            redis_cache.set(cache_key, result, ttl=cache_ttl)
        except Exception as e:
            logger.warning(f"Error caching borrow rate for {ticker}: {str(e)}")
        
        logger.info(f"Successfully retrieved borrow rate for {ticker}: rate={result['rate']}, status={borrow_status}")
        return result
        
    except ExternalAPIException as e:
        logger.error(f"SecLend API error for {ticker}: {str(e)}")
        return get_fallback_rate(ticker)
    except Exception as e:
        logger.error(f"Unexpected error fetching borrow rate for {ticker}: {str(e)}")
        return get_fallback_rate(ticker)

async def async_get_borrow_rate(ticker: str) -> Dict[str, Any]:
    """
    Asynchronously retrieves the current borrow rate for a specific ticker from SecLend API.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Dict[str, Any]: Dictionary containing borrow rate and status
    """
    # Generate cache key for this ticker
    cache_key = get_cache_key(ticker)
    
    # Check if we have this rate in cache
    try:
        cached_data = redis_cache.get(cache_key)
        if cached_data:
            logger.info(f"Using cached borrow rate for {ticker}")
            return cached_data
    except Exception as e:
        logger.warning(f"Error accessing cache for {ticker}: {str(e)}")
    
    # Get API configuration from settings
    settings = get_settings()
    seclend_config = settings.get_external_api_config(ExternalAPIs.SECLEND)
    
    # Build API URL
    base_url = seclend_config['base_url']
    endpoint = f"api/borrows/{ticker}"
    url = build_url(base_url, endpoint)
    
    # Set up API headers
    headers = {
        'X-API-Key': seclend_config['api_key'],
        'Content-Type': 'application/json'
    }
    
    try:
        # Call the SecLend API
        logger.info(f"Fetching borrow rate for {ticker} from SecLend API (async)")
        response_data = await async_get(
            url=url,
            service_name=ExternalAPIs.SECLEND,
            headers=headers,
            timeout=seclend_config.get('timeout_seconds', 10),
            fallback_value=None
        )
        
        # If the request failed and returned None, use fallback
        if response_data is None:
            return get_fallback_rate(ticker)
        
        # Validate the response contains required fields
        if not validate_response(response_data, REQUIRED_RATE_FIELDS):
            logger.error(f"Invalid response from SecLend API for {ticker}: missing required fields")
            return get_fallback_rate(ticker)
        
        # Map API status to BorrowStatus enum
        api_status = response_data['status']
        borrow_status = map_borrow_status(api_status)
        
        # Create the result dictionary
        result = {
            'rate': Decimal(str(response_data['rate'])),
            'status': borrow_status,
            'ticker': ticker,
            'source': 'seclend_api'
        }
        
        # Cache the result
        try:
            cache_ttl = settings.get_cache_ttl('borrow_rate')
            redis_cache.set(cache_key, result, ttl=cache_ttl)
        except Exception as e:
            logger.warning(f"Error caching borrow rate for {ticker}: {str(e)}")
        
        logger.info(f"Successfully retrieved borrow rate for {ticker}: rate={result['rate']}, status={borrow_status}")
        return result
        
    except ExternalAPIException as e:
        logger.error(f"SecLend API error for {ticker}: {str(e)}")
        return get_fallback_rate(ticker)
    except Exception as e:
        logger.error(f"Unexpected error fetching borrow rate for {ticker}: {str(e)}")
        return get_fallback_rate(ticker)

def get_fallback_rate(ticker: str) -> Dict[str, Any]:
    """
    Returns a fallback borrow rate when the SecLend API is unavailable.
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Dict[str, Any]: Dictionary containing fallback borrow rate and status
    """
    logger.warning(f"Using fallback borrow rate for {ticker}")
    
    # Return the minimum borrow rate with HARD status
    return {
        'rate': DEFAULT_MINIMUM_BORROW_RATE,
        'status': BorrowStatus.HARD,
        'ticker': ticker,
        'source': 'fallback',
        'is_fallback': True
    }

def map_borrow_status(status: str) -> str:
    """
    Maps the SecLend API status string to BorrowStatus enum.
    
    Args:
        status: Status string from SecLend API
        
    Returns:
        BorrowStatus: Mapped BorrowStatus enum value
    """
    # Convert to uppercase to handle case insensitively
    status = status.upper()
    
    # Map API status to BorrowStatus enum
    if status == 'EASY_TO_BORROW' or status == 'EASY':
        return BorrowStatus.EASY
    elif status == 'MEDIUM_TO_BORROW' or status == 'MEDIUM':
        return BorrowStatus.MEDIUM
    elif status == 'HARD_TO_BORROW' or status == 'HARD':
        return BorrowStatus.HARD
    else:
        # Default to HARD for unknown status
        logger.warning(f"Unknown borrow status: {status}, defaulting to HARD")
        return BorrowStatus.HARD

def get_cache_key(ticker: str) -> str:
    """
    Generates a cache key for a ticker's borrow rate.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        str: Cache key string
    """
    # Convert ticker to uppercase for consistency
    ticker = ticker.upper()
    
    # Combine prefix with ticker
    return f"{CACHE_KEY_PREFIX}{ticker}"