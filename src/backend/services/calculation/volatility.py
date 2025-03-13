"""
Module responsible for calculating volatility adjustments for borrow rates in the 
Borrow Rate & Locate Fee Pricing Engine. This module processes market volatility data 
and applies appropriate adjustments to base borrow rates to account for market conditions 
and stock-specific volatility.
"""

from decimal import Decimal
import logging
from typing import Union, Optional, Dict, Any

from ...core.constants import DEFAULT_VOLATILITY_FACTOR
from ...core.exceptions import CalculationException
from ...utils.math import round_decimal
from ...utils.validation import convert_to_decimal
from ...utils.timing import timed
from ..external.market_api import (
    get_market_volatility,
    get_stock_volatility,
    get_default_volatility
)

# Set up logger
logger = logging.getLogger(__name__)

# Constants
ROUNDING_PRECISION = 4
VOLATILITY_CACHE_KEY_PREFIX = 'volatility'
DEFAULT_VOLATILITY_MULTIPLIER = Decimal('0.01')
NORMAL_VOLATILITY_THRESHOLD = Decimal('20.0')
HIGH_VOLATILITY_THRESHOLD = Decimal('30.0')


@timed
def get_volatility_data(ticker: Optional[str] = None, use_cache: Optional[bool] = True) -> Dict[str, Any]:
    """
    Retrieves volatility data for a specific ticker or general market.
    
    Args:
        ticker: Optional ticker symbol. If provided, gets stock-specific volatility,
               otherwise gets general market volatility.
        use_cache: Whether to use cached data if available.
    
    Returns:
        Dict with volatility data including value and timestamp.
    """
    logger.info(f"Retrieving volatility data for {'ticker: ' + ticker if ticker else 'general market'}")
    
    try:
        if ticker:
            # Get stock-specific volatility
            volatility_data = get_stock_volatility(ticker, use_cache=use_cache)
            logger.info(f"Retrieved stock-specific volatility for {ticker}: {volatility_data.get('volatility')}")
        else:
            # Get general market volatility
            volatility_data = get_market_volatility(use_cache=use_cache)
            logger.info(f"Retrieved market volatility index: {volatility_data.get('value')}")
            
        return volatility_data
        
    except Exception as e:
        logger.warning(f"Error retrieving volatility data: {str(e)}. Using default volatility.")
        # Get default volatility as fallback
        default_data = get_default_volatility()
        return default_data


def validate_volatility_index(volatility_index: Union[Decimal, float, str, None]) -> Decimal:
    """
    Validates that a volatility index is within acceptable range.
    
    Args:
        volatility_index: The volatility index to validate.
        
    Returns:
        Validated volatility index as Decimal.
        
    Raises:
        CalculationException: If validation fails.
    """
    if volatility_index is None:
        logger.info("Volatility index is None, using default factor")
        return DEFAULT_VOLATILITY_FACTOR
    
    try:
        # Convert to Decimal for precise calculation
        vol_decimal = convert_to_decimal(volatility_index)
        
        # Check if volatility index is negative
        if vol_decimal < Decimal('0'):
            error_msg = f"Volatility index cannot be negative: {volatility_index}"
            logger.error(error_msg)
            raise CalculationException(error_msg)
            
        return vol_decimal
    except (ValueError, TypeError) as e:
        error_msg = f"Invalid volatility index format: {volatility_index}, error: {str(e)}"
        logger.error(error_msg)
        raise CalculationException(error_msg)


@timed
def calculate_volatility_adjustment(
    volatility_index: Union[Decimal, float, str, None], 
    volatility_multiplier: Optional[Decimal] = None
) -> Decimal:
    """
    Calculates the adjustment factor based on volatility index.
    
    Args:
        volatility_index: Volatility index value (e.g., VIX)
        volatility_multiplier: Factor to multiply volatility by, defaults to DEFAULT_VOLATILITY_MULTIPLIER
    
    Returns:
        Volatility adjustment factor
    """
    logger.info(f"Calculating volatility adjustment for index: {volatility_index}")
    
    # Validate volatility index
    vol_decimal = validate_volatility_index(volatility_index)
    
    # Use default multiplier if none provided
    if volatility_multiplier is None:
        volatility_multiplier = DEFAULT_VOLATILITY_MULTIPLIER
        
    # Basic adjustment is volatility times multiplier
    adjustment_factor = vol_decimal * volatility_multiplier
    
    # Apply progressive scaling for higher volatility
    if vol_decimal >= HIGH_VOLATILITY_THRESHOLD:
        # For high volatility, add additional adjustment
        additional = (vol_decimal - HIGH_VOLATILITY_THRESHOLD) * volatility_multiplier * Decimal('0.5')
        adjustment_factor += additional
        logger.info(f"Applied high volatility scaling, additional adjustment: {additional}")
    elif vol_decimal >= NORMAL_VOLATILITY_THRESHOLD:
        # For normal-high volatility, add smaller additional adjustment
        additional = (vol_decimal - NORMAL_VOLATILITY_THRESHOLD) * volatility_multiplier * Decimal('0.25')
        adjustment_factor += additional
        logger.info(f"Applied normal-high volatility scaling, additional adjustment: {additional}")
    
    # Round to specified precision
    adjustment_factor = round_decimal(adjustment_factor, ROUNDING_PRECISION)
    
    logger.info(f"Calculated volatility adjustment factor: {adjustment_factor}")
    return adjustment_factor


@timed
def apply_volatility_adjustment(
    base_rate: Decimal,
    volatility_index: Union[Decimal, float, str, None],
    volatility_multiplier: Optional[Decimal] = None
) -> Decimal:
    """
    Applies volatility adjustment to a base borrow rate.
    
    Args:
        base_rate: The initial borrow rate before adjustment
        volatility_index: Volatility index value (e.g., VIX)
        volatility_multiplier: Factor to multiply volatility by, defaults to DEFAULT_VOLATILITY_MULTIPLIER
    
    Returns:
        Volatility-adjusted borrow rate
    """
    logger.info(f"Applying volatility adjustment to base rate: {base_rate}")
    
    # Calculate the volatility adjustment factor
    adjustment_factor = calculate_volatility_adjustment(volatility_index, volatility_multiplier)
    
    # Apply the adjustment to the base rate
    adjusted_rate = base_rate * (Decimal('1') + adjustment_factor)
    
    # Round to specified precision
    adjusted_rate = round_decimal(adjusted_rate, ROUNDING_PRECISION)
    
    logger.info(f"Original rate: {base_rate}, Adjustment factor: {adjustment_factor}, Adjusted rate: {adjusted_rate}")
    return adjusted_rate


def get_volatility_tier(volatility_index: Decimal) -> str:
    """
    Determines the volatility tier based on volatility index.
    
    Args:
        volatility_index: The volatility index value
    
    Returns:
        String representing volatility tier (LOW, NORMAL, HIGH, EXTREME)
    """
    if volatility_index < NORMAL_VOLATILITY_THRESHOLD:
        tier = 'LOW'
    elif volatility_index < HIGH_VOLATILITY_THRESHOLD:
        tier = 'NORMAL'
    elif volatility_index < Decimal('40.0'):
        tier = 'HIGH'
    else:
        tier = 'EXTREME'
    
    logger.info(f"Volatility index {volatility_index} classified as {tier} tier")
    return tier


def format_volatility_adjustment(
    original_rate: Decimal,
    adjusted_rate: Decimal,
    volatility_index: Decimal
) -> Dict[str, Any]:
    """
    Formats the volatility adjustment for reporting purposes.
    
    Args:
        original_rate: The original borrow rate before adjustment
        adjusted_rate: The adjusted borrow rate after volatility adjustment
        volatility_index: The volatility index used for adjustment
    
    Returns:
        Dictionary with formatted adjustment details
    """
    # Calculate absolute adjustment amount
    adjustment_amount = adjusted_rate - original_rate
    
    # Calculate percentage adjustment
    adjustment_percentage = ((adjusted_rate / original_rate) - Decimal('1')) * Decimal('100')
    
    # Get volatility tier
    volatility_tier = get_volatility_tier(volatility_index)
    
    # Create the formatted adjustment dictionary
    adjustment_details = {
        'original_rate': float(original_rate),
        'adjusted_rate': float(adjusted_rate),
        'volatility_index': float(volatility_index),
        'volatility_tier': volatility_tier,
        'adjustment_amount': float(adjustment_amount),
        'adjustment_percentage': float(adjustment_percentage)
    }
    
    return adjustment_details