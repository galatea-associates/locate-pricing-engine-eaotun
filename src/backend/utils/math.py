"""
Utility module providing mathematical functions for financial calculations in the Borrow Rate & 
Locate Fee Pricing Engine. This module contains precise decimal arithmetic operations, rounding
functions, and specialized financial math utilities to ensure accurate and consistent calculations
across the system.
"""

from decimal import Decimal, ROUND_HALF_UP
import logging
from typing import List, Optional, Union

from ..core.constants import DAYS_IN_YEAR

# Configure logger for math operations
logger = logging.getLogger(__name__)

# Number of decimal places to round financial calculations
ROUNDING_PRECISION = 4


def round_decimal(value: Optional[Decimal], precision: int = ROUNDING_PRECISION) -> Optional[Decimal]:
    """
    Rounds a Decimal value to the specified precision using ROUND_HALF_UP mode,
    which is the standard for financial calculations.
    
    Args:
        value: The Decimal value to round
        precision: The number of decimal places to round to (defaults to ROUNDING_PRECISION)
        
    Returns:
        Rounded decimal value, or None if input value is None
    """
    if value is None:
        return None
    
    try:
        quantize_exp = Decimal('0.1') ** precision
        return value.quantize(quantize_exp, rounding=ROUND_HALF_UP)
    except Exception as e:
        logger.error(f"Error rounding decimal value {value}: {str(e)}")
        raise


def calculate_percentage(value: Decimal, percentage: Decimal) -> Decimal:
    """
    Calculates a percentage of a value.
    
    Args:
        value: The base value
        percentage: The percentage to calculate (e.g., 5 for 5%)
        
    Returns:
        The calculated percentage amount
    """
    try:
        result = value * (percentage / Decimal('100'))
        return round_decimal(result)
    except Exception as e:
        logger.error(f"Error calculating percentage {percentage}% of {value}: {str(e)}")
        raise


def calculate_daily_rate(annual_rate: Decimal) -> Decimal:
    """
    Converts an annual rate to a daily rate by dividing by the number of days in a year.
    
    Args:
        annual_rate: The annual rate as a decimal (e.g., 0.05 for 5%)
        
    Returns:
        The equivalent daily rate
    """
    try:
        daily_rate = annual_rate / DAYS_IN_YEAR
        return round_decimal(daily_rate)
    except Exception as e:
        logger.error(f"Error calculating daily rate from annual rate {annual_rate}: {str(e)}")
        raise


def adjust_rate_for_volatility(
    base_rate: Decimal, 
    volatility_index: Decimal, 
    volatility_factor: Decimal
) -> Decimal:
    """
    Adjusts a base rate based on market volatility.
    
    Higher volatility leads to higher adjusted rates.
    
    Args:
        base_rate: The unadjusted base rate
        volatility_index: The market volatility index (e.g., VIX)
        volatility_factor: The factor to apply to the volatility index
        
    Returns:
        Volatility-adjusted rate
    """
    try:
        volatility_adjustment = volatility_index * volatility_factor
        adjusted_rate = base_rate + (base_rate * volatility_adjustment)
        # Ensure rate is not negative
        adjusted_rate = max(adjusted_rate, Decimal('0'))
        return round_decimal(adjusted_rate)
    except Exception as e:
        logger.error(f"Error adjusting rate for volatility (base_rate={base_rate}, "
                     f"volatility_index={volatility_index}, volatility_factor={volatility_factor}): {str(e)}")
        raise


def adjust_rate_for_event_risk(
    base_rate: Decimal, 
    event_risk_factor: int, 
    risk_multiplier: Decimal
) -> Decimal:
    """
    Adjusts a base rate based on event risk factor.
    
    Higher event risk leads to higher adjusted rates.
    
    Args:
        base_rate: The unadjusted base rate
        event_risk_factor: Integer from 0-10 representing event risk (10 being highest)
        risk_multiplier: The multiplier for the risk adjustment
        
    Returns:
        Risk-adjusted rate
    """
    try:
        # Convert event_risk_factor to a ratio (0-1)
        risk_ratio = Decimal(event_risk_factor) / Decimal('10')
        risk_adjustment = risk_ratio * risk_multiplier
        adjusted_rate = base_rate + (base_rate * risk_adjustment)
        return round_decimal(adjusted_rate)
    except Exception as e:
        logger.error(f"Error adjusting rate for event risk (base_rate={base_rate}, "
                     f"event_risk_factor={event_risk_factor}, risk_multiplier={risk_multiplier}): {str(e)}")
        raise


def safe_divide(
    numerator: Decimal, 
    denominator: Decimal, 
    default: Decimal = Decimal('0')
) -> Decimal:
    """
    Safely divides two numbers, handling division by zero.
    
    Args:
        numerator: The number to divide
        denominator: The number to divide by
        default: The default value to return if denominator is zero
        
    Returns:
        Division result or default value if denominator is zero
    """
    try:
        if denominator == Decimal('0'):
            logger.warning(f"Division by zero attempted: {numerator} / {denominator}. "
                          f"Returning default value {default}.")
            return default
        return numerator / denominator
    except Exception as e:
        logger.error(f"Error in safe_divide operation ({numerator} / {denominator}): {str(e)}")
        raise


def calculate_weighted_average(values: List[Decimal], weights: List[Decimal]) -> Decimal:
    """
    Calculates weighted average of values with corresponding weights.
    
    Args:
        values: List of values
        weights: List of weights corresponding to the values
        
    Returns:
        Weighted average
    
    Raises:
        ValueError: If input lists have different lengths
    """
    try:
        if len(values) != len(weights):
            error_msg = f"Length mismatch: values list ({len(values)}) and weights list ({len(weights)})"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if len(values) == 0:
            logger.warning("Empty lists provided to calculate_weighted_average. Returning 0.")
            return Decimal('0')
        
        # Calculate sum of (value * weight) for all items
        weighted_sum = sum(v * w for v, w in zip(values, weights))
        weights_sum = sum(weights)
        
        # Calculate weighted average using safe division (returns default if weights_sum is 0)
        weighted_average = safe_divide(weighted_sum, weights_sum)
        
        return round_decimal(weighted_average)
    except Exception as e:
        if not isinstance(e, ValueError):  # Don't log again if we already raised a ValueError
            logger.error(f"Error calculating weighted average: {str(e)}")
        raise


def clamp(value: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    """
    Constrains a value between minimum and maximum bounds.
    
    Args:
        value: The value to constrain
        minimum: The lower bound
        maximum: The upper bound
        
    Returns:
        Clamped value
    """
    try:
        if value < minimum:
            return minimum
        if value > maximum:
            return maximum
        return value
    except Exception as e:
        logger.error(f"Error clamping value {value} between {minimum} and {maximum}: {str(e)}")
        raise


def format_currency(amount: Decimal, currency_symbol: str = '$') -> str:
    """
    Formats a decimal value as a currency string.
    
    Args:
        amount: The decimal amount to format
        currency_symbol: The currency symbol to use (default: $)
        
    Returns:
        Formatted currency string (e.g., "$1,234.56")
    """
    try:
        # Round to 2 decimal places for currency display
        rounded_amount = round_decimal(amount, precision=2)
        # Convert to string with thousands separator and 2 decimal places
        amount_str = f"{rounded_amount:,.2f}"
        return f"{currency_symbol}{amount_str}"
    except Exception as e:
        logger.error(f"Error formatting currency amount {amount}: {str(e)}")
        raise


def format_percentage(rate: Decimal) -> str:
    """
    Formats a decimal rate as a percentage string.
    
    Args:
        rate: The decimal rate to format (e.g., 0.0525 for 5.25%)
        
    Returns:
        Formatted percentage string (e.g., "5.25%")
    """
    try:
        # Convert to percentage (multiply by 100)
        percentage = rate * Decimal('100')
        # Round to ROUNDING_PRECISION decimal places
        rounded_percentage = round_decimal(percentage)
        # Format as string with % symbol
        return f"{rounded_percentage}%"
    except Exception as e:
        logger.error(f"Error formatting percentage rate {rate}: {str(e)}")
        raise