"""
Core module responsible for calculating borrow rates for securities in the Borrow Rate & Locate Fee Pricing Engine.
This module implements the formulas and business logic for determining the base borrow rate, applying volatility
and event risk adjustments, and handling fallback scenarios when external data sources are unavailable.
"""

import logging
from decimal import Decimal
from typing import Dict, Optional, Union, Any

# Import constants
from ...core.constants import (
    DEFAULT_MINIMUM_BORROW_RATE,
    DEFAULT_VOLATILITY_FACTOR,
    DEFAULT_EVENT_RISK_FACTOR,
    BorrowStatus
)

# Import exceptions
from ...core.exceptions import CalculationException, ExternalAPIException

# Import utility functions
from ...utils.math import round_decimal
from ...utils.validation import convert_to_decimal
from ...utils.timing import timed
from ...utils.retry import retry_with_fallback
from ...utils.circuit_breaker import circuit_breaker

# Import external API functions
from ..external.seclend_api import get_borrow_rate, create_fallback_response
from ..external.market_api import (
    get_market_volatility,
    get_stock_volatility,
    get_default_volatility
)
from ..external.event_api import get_event_risk_factor

# Import calculation functions
from .volatility import (
    calculate_volatility_adjustment,
    apply_volatility_adjustment
)
from .event_risk import calculate_event_risk_adjustment
from .utils import apply_minimum_borrow_rate

# Import cache
from ..cache.redis import RedisCache

# Set up logger
logger = logging.getLogger(__name__)

# Constants
ROUNDING_PRECISION = 4
BORROW_RATE_CACHE_PREFIX = 'borrow_rate'
BORROW_RATE_CACHE_TTL = 300  # 5 minutes


@timed
def calculate_borrow_rate(ticker: str, min_rate: Optional[Decimal] = None, use_cache: Optional[bool] = True) -> Decimal:
    """
    Main function to calculate the borrow rate for a security with all adjustments applied.
    
    Args:
        ticker: Stock symbol
        min_rate: Optional minimum rate to apply (defaults to DEFAULT_MINIMUM_BORROW_RATE)
        use_cache: Whether to check and use cached rates (default: True)
        
    Returns:
        Decimal: Fully adjusted borrow rate as a decimal
    """
    logger.info(f"Calculating borrow rate for ticker: {ticker}")
    
    # Check if use_cache is True (default) and try to get cached rate
    if use_cache:
        cached_rate = get_cached_borrow_rate(ticker)
        if cached_rate is not None:
            logger.info(f"Using cached borrow rate for {ticker}: {cached_rate}")
            return cached_rate
    
    # Get real-time base borrow rate by calling get_real_time_borrow_rate
    base_rate = get_real_time_borrow_rate(ticker, min_rate)
    
    try:
        # Get volatility data for the ticker
        volatility_data = get_stock_volatility(ticker)
        volatility_index = convert_to_decimal(volatility_data.get('volatility'))
        
        # Calculate volatility adjustment using calculate_volatility_adjustment
        volatility_adjustment = calculate_volatility_adjustment(volatility_index)
        
        # Apply volatility adjustment to base rate using apply_volatility_adjustment
        volatility_adjusted_rate = apply_volatility_adjustment(base_rate, volatility_index)
        
        # Get event risk factor for the ticker
        event_risk_factor = get_event_risk_factor(ticker)
        
        # Apply event risk adjustment using calculate_event_risk_adjustment
        event_adjustment = calculate_event_risk_adjustment(event_risk_factor)
        event_adjusted_rate = volatility_adjusted_rate * (Decimal('1') + event_adjustment)
        
        # Apply minimum borrow rate threshold using apply_minimum_borrow_rate
        final_rate = apply_minimum_borrow_rate(event_adjusted_rate, min_rate)
        
        # Round the final rate to ROUNDING_PRECISION decimal places
        final_rate = round_decimal(final_rate, ROUNDING_PRECISION)
        
        # If use_cache is True, cache the calculated rate
        if use_cache:
            cache_borrow_rate(ticker, final_rate)
        
        # Log the final calculated rate
        logger.info(f"Calculated borrow rate for {ticker}: {final_rate}")
        
        # Return the calculated borrow rate
        return final_rate
        
    except Exception as e:
        logger.error(f"Error calculating borrow rate for {ticker}: {str(e)}")
        # Apply minimum rate to base rate if adjustments fail
        return apply_minimum_borrow_rate(base_rate, min_rate)


@timed
@retry_with_fallback(fallback_function='get_fallback_borrow_rate', max_retries=3)
@circuit_breaker(name='seclend_api', failure_threshold=5, recovery_timeout=60, success_threshold=3)
def get_real_time_borrow_rate(ticker: str, min_rate: Optional[Decimal] = None) -> Decimal:
    """
    Retrieves the real-time borrow rate from the SecLend API with fallback handling.
    
    Args:
        ticker: Stock symbol
        min_rate: Optional minimum rate to apply
        
    Returns:
        Decimal: Base borrow rate from external API or fallback
    """
    # Log attempt to get real-time borrow rate for ticker
    logger.info(f"Getting real-time borrow rate for ticker: {ticker}")
    
    # Call get_borrow_rate from seclend_api module
    response = get_borrow_rate(ticker)
    
    # Extract rate value from the response
    rate = response.get('rate')
    
    # Convert rate to Decimal using convert_to_decimal
    rate_decimal = convert_to_decimal(rate)
    
    # Log the retrieved rate
    logger.info(f"Retrieved real-time borrow rate for {ticker}: {rate_decimal}")
    
    # Return the borrow rate
    return rate_decimal
    
    # Note: If API call fails, retry_with_fallback decorator will call get_fallback_borrow_rate


def get_fallback_borrow_rate(ticker: str, min_rate: Optional[Decimal] = None) -> Decimal:
    """
    Provides a fallback borrow rate when the external API is unavailable.
    
    Args:
        ticker: Stock symbol
        min_rate: Optional minimum rate to apply
        
    Returns:
        Decimal: Fallback borrow rate
    """
    # Log that fallback borrow rate is being used for ticker
    logger.warning(f"Using fallback borrow rate for ticker: {ticker}")
    
    # Call create_fallback_response from seclend_api module
    fallback_response = create_fallback_response(ticker)
    
    # Extract rate value from the fallback response
    fallback_rate = fallback_response.get('rate')
    
    # Convert rate to Decimal using convert_to_decimal
    rate_decimal = convert_to_decimal(fallback_rate)
    
    # If min_rate is provided, use the maximum of fallback rate and min_rate
    if min_rate is not None:
        rate_decimal = max(rate_decimal, min_rate)
    
    # Log the fallback rate being used
    logger.info(f"Using fallback borrow rate for {ticker}: {rate_decimal}")
    
    # Return the fallback borrow rate
    return rate_decimal


def get_cached_borrow_rate(ticker: str) -> Optional[Decimal]:
    """
    Attempts to retrieve a cached borrow rate for a ticker.
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Optional[Decimal]: Cached borrow rate if available, None otherwise
    """
    # Generate cache key using ticker and BORROW_RATE_CACHE_PREFIX
    cache_key = f"{BORROW_RATE_CACHE_PREFIX}:{ticker}"
    
    # Get Redis cache instance
    cache = RedisCache()
    
    try:
        # Try to get value from cache using the key
        cached_value = cache.get(cache_key)
        
        # If value exists in cache, convert to Decimal and return
        if cached_value is not None:
            rate = Decimal(str(cached_value))
            logger.debug(f"Cache hit for borrow rate - Ticker: {ticker}, Rate: {rate}")
            return rate
        
        # If value doesn't exist or cache is unavailable, return None
        logger.debug(f"Cache miss for borrow rate - Ticker: {ticker}")
        return None
            
    except Exception as e:
        # Log cache hit or miss
        logger.warning(f"Error retrieving cached borrow rate for {ticker}: {str(e)}")
        return None


def cache_borrow_rate(ticker: str, rate: Decimal, ttl: Optional[int] = None) -> bool:
    """
    Caches a calculated borrow rate for future use.
    
    Args:
        ticker: Stock symbol
        rate: Borrow rate to cache
        ttl: Optional time-to-live in seconds (default: BORROW_RATE_CACHE_TTL)
        
    Returns:
        bool: True if caching was successful, False otherwise
    """
    # Generate cache key using ticker and BORROW_RATE_CACHE_PREFIX
    cache_key = f"{BORROW_RATE_CACHE_PREFIX}:{ticker}"
    
    # Get Redis cache instance
    cache = RedisCache()
    
    try:
        # Convert Decimal rate to string for caching
        rate_str = str(rate)
        
        # Set value in cache with specified TTL (default to BORROW_RATE_CACHE_TTL)
        ttl_value = ttl if ttl is not None else BORROW_RATE_CACHE_TTL
        result = cache.set(cache_key, rate_str, ttl_value)
        
        # Log cache operation result
        if result:
            logger.debug(f"Cached borrow rate for {ticker}: {rate} (TTL: {ttl_value}s)")
        else:
            logger.warning(f"Failed to cache borrow rate for {ticker}")
            
        # Return True if successful, False otherwise
        return result
        
    except Exception as e:
        logger.warning(f"Error caching borrow rate for {ticker}: {str(e)}")
        return False


@timed
def get_borrow_rate_with_adjustments(
    ticker: str,
    base_rate: Optional[Decimal] = None,
    volatility_index: Optional[Decimal] = None,
    event_risk_factor: Optional[int] = None,
    min_rate: Optional[Decimal] = None
) -> Dict[str, Any]:
    """
    Calculates a borrow rate with all adjustments in a single function call.
    
    Args:
        ticker: Stock symbol
        base_rate: Optional pre-determined base rate (if not provided, will be fetched)
        volatility_index: Optional pre-determined volatility index (if not provided, will be fetched)
        event_risk_factor: Optional pre-determined event risk factor (if not provided, will be fetched)
        min_rate: Optional minimum rate to apply
        
    Returns:
        Dict[str, Any]: Dictionary with adjusted rate and adjustment details
    """
    # If base_rate is not provided, get real-time rate by calling get_real_time_borrow_rate
    if base_rate is None:
        base_rate = get_real_time_borrow_rate(ticker, min_rate)
    
    # If volatility_index is not provided, get volatility data from market API
    if volatility_index is None:
        volatility_data = get_stock_volatility(ticker)
        volatility_index = convert_to_decimal(volatility_data.get('volatility'))
    
    # Calculate volatility adjustment using calculate_volatility_adjustment
    volatility_adjustment = calculate_volatility_adjustment(volatility_index)
    
    # Apply volatility adjustment to base rate using apply_volatility_adjustment
    volatility_adjusted_rate = apply_volatility_adjustment(base_rate, volatility_index)
    
    # If event_risk_factor is not provided, get event risk factor from event API
    if event_risk_factor is None:
        event_risk_factor = get_event_risk_factor(ticker)
    
    # Apply event risk adjustment using calculate_event_risk_adjustment
    event_adjustment = calculate_event_risk_adjustment(event_risk_factor)
    event_adjusted_rate = volatility_adjusted_rate * (Decimal('1') + event_adjustment)
    
    # Apply minimum borrow rate threshold using apply_minimum_borrow_rate
    final_rate = apply_minimum_borrow_rate(event_adjusted_rate, min_rate)
    
    # Create and return dictionary with original_rate, adjusted_rate, volatility_adjustment, 
    # event_risk_adjustment, and final_rate
    result = {
        "original_rate": float(base_rate),
        "adjusted_rate": float(final_rate),
        "volatility_adjustment": float(volatility_adjustment),
        "event_risk_adjustment": float(event_adjustment),
        "final_rate": float(final_rate),
        "volatility_index": float(volatility_index),
        "event_risk_factor": event_risk_factor
    }
    
    return result


def get_borrow_rate_by_status(status: BorrowStatus) -> Decimal:
    """
    Provides a default borrow rate based on the borrow status when other data is unavailable.
    
    Args:
        status: BorrowStatus enum value (EASY, MEDIUM, HARD)
        
    Returns:
        Decimal: Default borrow rate for the given status
    """
    # Match the BorrowStatus enum value
    if status == BorrowStatus.EASY:
        # For BorrowStatus.EASY, return a low rate (e.g., 0.005)
        rate = Decimal('0.005')  # 0.5%
    elif status == BorrowStatus.MEDIUM:
        # For BorrowStatus.MEDIUM, return a medium rate (e.g., 0.02)
        rate = Decimal('0.02')  # 2%
    elif status == BorrowStatus.HARD:
        # For BorrowStatus.HARD, return a high rate (e.g., 0.05)
        rate = Decimal('0.05')  # 5%
    else:
        # For any other value, return DEFAULT_MINIMUM_BORROW_RATE
        rate = DEFAULT_MINIMUM_BORROW_RATE
        
    # Log the default rate being used
    logger.info(f"Default borrow rate for status {status}: {rate}")
    
    return rate