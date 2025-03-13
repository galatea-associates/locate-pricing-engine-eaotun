"""
Module responsible for calculating event risk adjustments for borrow rates in the Borrow Rate & Locate Fee Pricing Engine.

This module processes event risk data from the Event Calendar API and applies appropriate adjustments
to base borrow rates to account for upcoming corporate events like earnings announcements, dividend 
payments, or regulatory decisions.
"""

# Standard library imports
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, Union

# Third-party imports
import httpx  # httpx 0.25.0+
from httpx import AsyncClient, Response
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type  # tenacity 8.2.0+

# Internal imports
from ...core.constants import DEFAULT_EVENT_RISK_FACTOR
from ...core.exceptions import CalculationException, ExternalAPIException
from ...utils.math import round_decimal
from ...utils.validation import convert_to_decimal
from ...utils.timing import timed
from ..cache.redis import RedisCache

# Configure logger
logger = logging.getLogger(__name__)

# Constants
ROUNDING_PRECISION = 4
EVENT_RISK_CACHE_KEY_PREFIX = 'event_risk'
EVENT_RISK_CACHE_TTL = 3600  # 1 hour
DEFAULT_EVENT_RISK_MULTIPLIER = Decimal('0.005')  # 0.5% adjustment per risk level
MAX_EVENT_RISK_FACTOR = 10  # Maximum event risk factor (scale of 0-10)
EVENT_API_TIMEOUT = 5.0  # Timeout for API calls in seconds
EVENT_API_BASE_URL = 'https://event-calendar-api.example.com/api'
EVENT_API_ENDPOINT = '/events'


def get_default_event_risk_factor() -> int:
    """
    Provides a default event risk factor when the external API is unavailable.
    
    Returns:
        int: Default event risk factor (0)
    """
    logger.info("Using default event risk factor (0)")
    return 0  # Default to no event risk


def get_cached_event_risk_factor(ticker: str) -> Optional[int]:
    """
    Attempts to retrieve a cached event risk factor for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Optional[int]: Cached event risk factor if available, None otherwise
    """
    cache_key = f"{EVENT_RISK_CACHE_KEY_PREFIX}:{ticker}"
    
    try:
        cache = RedisCache()
        cached_value = cache.get(cache_key)
        
        if cached_value is not None:
            logger.debug(f"Cache hit for event risk factor - Ticker: {ticker}")
            return int(cached_value)
        else:
            logger.debug(f"Cache miss for event risk factor - Ticker: {ticker}")
            return None
    except Exception as e:
        logger.warning(f"Error retrieving cached event risk factor for {ticker}: {e}")
        return None


def cache_event_risk_factor(ticker: str, risk_factor: int, ttl: Optional[int] = None) -> bool:
    """
    Caches an event risk factor for future use.
    
    Args:
        ticker: Stock ticker symbol
        risk_factor: Event risk factor to cache
        ttl: Optional custom TTL in seconds (defaults to EVENT_RISK_CACHE_TTL)
        
    Returns:
        bool: True if caching was successful, False otherwise
    """
    cache_key = f"{EVENT_RISK_CACHE_KEY_PREFIX}:{ticker}"
    
    try:
        cache = RedisCache()
        ttl_value = ttl if ttl is not None else EVENT_RISK_CACHE_TTL
        
        # Convert int to string for caching
        result = cache.set(cache_key, str(risk_factor), ttl_value)
        
        if result:
            logger.debug(f"Cached event risk factor for {ticker}: {risk_factor} (TTL: {ttl_value}s)")
        else:
            logger.warning(f"Failed to cache event risk factor for {ticker}")
            
        return result
    except Exception as e:
        logger.warning(f"Error caching event risk factor for {ticker}: {e}")
        return False


@retry(stop=stop_after_attempt(3), 
       retry=retry_if_exception_type(httpx.HTTPError), 
       wait=wait_exponential(multiplier=1, min=1, max=10))
async def fetch_event_risk_factor_from_api(ticker: str) -> int:
    """
    Directly calls the Event Calendar API to retrieve event risk factor for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        int: Event risk factor from the API or default if API call fails
        
    Raises:
        ExternalAPIException: If the API call fails
    """
    logger.info(f"Fetching event risk factor from API for ticker: {ticker}")
    
    url = f"{EVENT_API_BASE_URL}{EVENT_API_ENDPOINT}"
    params = {"ticker": ticker}
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "YOUR_API_KEY_HERE"  # Should be loaded from config/env in production
    }
    
    try:
        async with AsyncClient() as client:
            response: Response = await client.get(
                url, 
                params=params, 
                headers=headers, 
                timeout=EVENT_API_TIMEOUT
            )
            
        if response.status_code != 200:
            error_message = f"API Error: {response.status_code} - {response.text}"
            logger.error(error_message)
            raise ExternalAPIException("Event Calendar API", error_message)
            
        data = response.json()
        
        if not data or "events" not in data:
            logger.warning(f"No event data returned for ticker: {ticker}")
            return 0
            
        # Extract event risk from API response
        events = data.get("events", [])
        if not events:
            return 0
            
        # Find highest risk factor among upcoming events
        max_risk = 0
        for event in events:
            risk_factor = event.get("risk_factor", 0)
            max_risk = max(max_risk, risk_factor)
            
        logger.info(f"Event risk factor for {ticker}: {max_risk}")
        return max_risk
        
    except httpx.TimeoutException:
        error_message = f"Timeout while fetching event risk for {ticker}"
        logger.error(error_message)
        raise ExternalAPIException("Event Calendar API", "Timeout")
        
    except httpx.HTTPError as e:
        error_message = f"HTTP error while fetching event risk for {ticker}: {str(e)}"
        logger.error(error_message)
        raise ExternalAPIException("Event Calendar API", str(e))
        
    except Exception as e:
        error_message = f"Error fetching event risk for {ticker}: {str(e)}"
        logger.error(error_message)
        raise ExternalAPIException("Event Calendar API", str(e))


def validate_event_risk_factor(risk_factor: Union[int, str, None]) -> int:
    """
    Validates that an event risk factor is within acceptable range.
    
    Args:
        risk_factor: Event risk factor to validate
        
    Returns:
        int: Validated event risk factor
        
    Raises:
        CalculationException: If the risk factor is invalid
    """
    if risk_factor is None:
        return 0
    
    # Convert to int if it's a string
    if isinstance(risk_factor, str):
        try:
            risk_factor = int(risk_factor)
        except ValueError:
            raise CalculationException(f"Invalid event risk factor: {risk_factor}. Must be an integer.")
    
    # Ensure it's an int
    if not isinstance(risk_factor, int):
        try:
            risk_factor = int(risk_factor)
        except (ValueError, TypeError):
            raise CalculationException(f"Invalid event risk factor: {risk_factor}. Must be an integer.")
    
    # Check for negative values
    if risk_factor < 0:
        logger.warning(f"Negative event risk factor received: {risk_factor}. Setting to 0.")
        return 0
    
    # Cap to maximum value
    if risk_factor > MAX_EVENT_RISK_FACTOR:
        logger.warning(f"Event risk factor {risk_factor} exceeds maximum ({MAX_EVENT_RISK_FACTOR}). Capping value.")
        return MAX_EVENT_RISK_FACTOR
    
    return risk_factor


@timed
def calculate_event_risk_adjustment(
    risk_factor: Union[int, str, None], 
    risk_multiplier: Optional[Decimal] = None
) -> Decimal:
    """
    Calculates the adjustment factor based on event risk factor.
    
    Args:
        risk_factor: Event risk factor (0-10)
        risk_multiplier: Optional custom risk multiplier (defaults to DEFAULT_EVENT_RISK_MULTIPLIER)
        
    Returns:
        Decimal: Event risk adjustment factor
    """
    logger.debug(f"Calculating event risk adjustment for risk factor: {risk_factor}")
    
    # Validate risk factor
    validated_risk_factor = validate_event_risk_factor(risk_factor)
    
    # Use default multiplier if none provided
    multiplier = risk_multiplier if risk_multiplier is not None else DEFAULT_EVENT_RISK_MULTIPLIER
    
    # Calculate adjustment factor
    # Formula: (risk_factor / MAX_EVENT_RISK_FACTOR) * risk_multiplier
    risk_ratio = Decimal(validated_risk_factor) / Decimal(MAX_EVENT_RISK_FACTOR)
    adjustment = risk_ratio * multiplier
    
    # Round to appropriate precision
    rounded_adjustment = round_decimal(adjustment, ROUNDING_PRECISION)
    
    logger.debug(f"Event risk adjustment calculated: {rounded_adjustment} (risk factor: {validated_risk_factor}, multiplier: {multiplier})")
    
    return rounded_adjustment


@timed
def apply_event_risk_adjustment(
    base_rate: Decimal, 
    risk_factor: Union[int, str, None], 
    risk_multiplier: Optional[Decimal] = None
) -> Decimal:
    """
    Applies event risk adjustment to a base borrow rate.
    
    Args:
        base_rate: Base borrow rate to adjust
        risk_factor: Event risk factor (0-10)
        risk_multiplier: Optional custom risk multiplier
        
    Returns:
        Decimal: Event risk-adjusted borrow rate
    """
    logger.debug(f"Applying event risk adjustment to base rate {base_rate} with risk factor {risk_factor}")
    
    # Calculate adjustment factor
    adjustment_factor = calculate_event_risk_adjustment(risk_factor, risk_multiplier)
    
    # Apply adjustment to base rate
    # Formula: base_rate * (1 + adjustment_factor)
    adjusted_rate = base_rate * (Decimal('1') + adjustment_factor)
    
    # Round to appropriate precision
    rounded_rate = round_decimal(adjusted_rate, ROUNDING_PRECISION)
    
    logger.debug(f"Rate adjusted for event risk: {base_rate} → {rounded_rate} (adjustment factor: {adjustment_factor})")
    
    return rounded_rate


@timed
def get_event_risk_data(ticker: str, use_cache: Optional[bool] = True) -> int:
    """
    Retrieves event risk data for a specific ticker with caching.
    
    Args:
        ticker: Stock ticker symbol
        use_cache: Whether to use cached values if available (default: True)
        
    Returns:
        int: Event risk factor for the ticker
    """
    logger.info(f"Getting event risk data for ticker: {ticker}")
    
    # Check cache first if enabled
    if use_cache:
        cached_risk_factor = get_cached_event_risk_factor(ticker)
        if cached_risk_factor is not None:
            logger.info(f"Using cached event risk factor for {ticker}: {cached_risk_factor}")
            return cached_risk_factor
    
    # If we get here, need to fetch from API
    try:
        # In a synchronous context, we'd need to run this in an event loop
        import asyncio
        event_loop = asyncio.get_event_loop()
        risk_factor = event_loop.run_until_complete(fetch_event_risk_factor_from_api(ticker))
    except ExternalAPIException as e:
        logger.warning(f"Failed to fetch event risk from API: {e}")
        risk_factor = get_default_event_risk_factor()
    
    # Validate before returning
    validated_risk_factor = validate_event_risk_factor(risk_factor)
    
    # Cache the result if caching is enabled
    if use_cache:
        cache_event_risk_factor(ticker, validated_risk_factor)
    
    logger.info(f"Event risk factor for {ticker}: {validated_risk_factor}")
    return validated_risk_factor


def format_event_risk_adjustment(original_rate: Decimal, adjusted_rate: Decimal, risk_factor: int) -> Dict[str, Any]:
    """
    Formats the event risk adjustment for reporting purposes.
    
    Args:
        original_rate: Original borrow rate before adjustment
        adjusted_rate: Adjusted borrow rate after applying event risk
        risk_factor: Event risk factor used for adjustment
        
    Returns:
        Dict[str, Any]: Dictionary with formatted adjustment details
    """
    # Calculate adjustment amount and percentage
    adjustment_amount = adjusted_rate - original_rate
    adjustment_percentage = ((adjusted_rate / original_rate) - Decimal('1')) * Decimal('100') if original_rate != 0 else Decimal('0')
    
    # Determine risk level based on factor
    if risk_factor <= 3:
        risk_level = "LOW"
    elif risk_factor <= 6:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"
    
    # Format the response
    result = {
        "original_rate": float(original_rate),
        "adjusted_rate": float(adjusted_rate),
        "risk_factor": risk_factor,
        "risk_level": risk_level,
        "adjustment_amount": float(adjustment_amount),
        "adjustment_percentage": float(adjustment_percentage)
    }
    
    return result