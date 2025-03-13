"""
Core module containing the fundamental financial formulas used throughout the Borrow Rate & 
Locate Fee Pricing Engine. This module centralizes all mathematical formulas for calculating 
borrow rates, locate fees, and related financial metrics, ensuring consistency and accuracy 
across the system.
"""

from decimal import Decimal
from typing import List, Optional
import logging

# Internal imports
from ../../core.constants import (
    DAYS_IN_YEAR,
    DEFAULT_MINIMUM_BORROW_RATE,
    DEFAULT_VOLATILITY_FACTOR,
    DEFAULT_EVENT_RISK_FACTOR,
    TransactionFeeType
)
from ../../core.exceptions import CalculationException
from ../../utils.math import round_decimal
from ../../utils.timing import timed

# Set up logger
logger = logging.getLogger(__name__)

# Global constants
ROUNDING_PRECISION = 4


@timed()
def calculate_annualized_rate(daily_rate: Decimal) -> Decimal:
    """
    Calculates the annualized rate from a daily rate.
    
    Args:
        daily_rate: The daily rate as a decimal
        
    Returns:
        Decimal: The annualized rate
    """
    try:
        annual_rate = daily_rate * DAYS_IN_YEAR
        return round_decimal(annual_rate, ROUNDING_PRECISION)
    except Exception as e:
        logger.error(f"Error calculating annualized rate: {str(e)}")
        raise CalculationException(
            f"Failed to calculate annualized rate: {str(e)}", 
            {"daily_rate": str(daily_rate)}
        )


@timed()
def calculate_daily_rate(annual_rate: Decimal) -> Decimal:
    """
    Calculates the daily rate from an annualized rate.
    
    Args:
        annual_rate: The annual rate as a decimal
        
    Returns:
        Decimal: The daily rate
    """
    try:
        daily_rate = annual_rate / DAYS_IN_YEAR
        return round_decimal(daily_rate, ROUNDING_PRECISION)
    except Exception as e:
        logger.error(f"Error calculating daily rate: {str(e)}")
        raise CalculationException(
            f"Failed to calculate daily rate: {str(e)}", 
            {"annual_rate": str(annual_rate)}
        )


@timed()
def calculate_borrow_cost(position_value: Decimal, annual_rate: Decimal, days: int) -> Decimal:
    """
    Calculates the cost of borrowing securities for a specific period.
    
    Args:
        position_value: The value of the borrowed position
        annual_rate: The annual interest rate as a decimal
        days: The number of days for the loan
        
    Returns:
        Decimal: The calculated borrow cost
    """
    try:
        daily_rate = calculate_daily_rate(annual_rate)
        borrow_cost = position_value * daily_rate * Decimal(days)
        return round_decimal(borrow_cost, ROUNDING_PRECISION)
    except Exception as e:
        logger.error(f"Error calculating borrow cost: {str(e)}")
        raise CalculationException(
            f"Failed to calculate borrow cost: {str(e)}", 
            {
                "position_value": str(position_value),
                "annual_rate": str(annual_rate),
                "days": days
            }
        )


@timed()
def calculate_markup_amount(base_value: Decimal, markup_percentage: Decimal) -> Decimal:
    """
    Calculates the markup amount based on a base value and markup percentage.
    
    Args:
        base_value: The base value to apply the markup to
        markup_percentage: The percentage markup to apply
        
    Returns:
        Decimal: The calculated markup amount
    """
    try:
        markup_amount = base_value * (markup_percentage / Decimal('100'))
        return round_decimal(markup_amount, ROUNDING_PRECISION)
    except Exception as e:
        logger.error(f"Error calculating markup amount: {str(e)}")
        raise CalculationException(
            f"Failed to calculate markup amount: {str(e)}", 
            {
                "base_value": str(base_value),
                "markup_percentage": str(markup_percentage)
            }
        )


@timed()
def calculate_fee(base_value: Decimal, fee_type: TransactionFeeType, fee_amount: Decimal) -> Decimal:
    """
    Calculates a fee based on fee type (flat or percentage).
    
    Args:
        base_value: The base value for percentage-based fees
        fee_type: The type of fee (FLAT or PERCENTAGE)
        fee_amount: The fee amount (flat amount or percentage)
        
    Returns:
        Decimal: The calculated fee amount
    """
    try:
        if fee_type == TransactionFeeType.FLAT:
            return round_decimal(fee_amount, ROUNDING_PRECISION)
        elif fee_type == TransactionFeeType.PERCENTAGE:
            fee = base_value * (fee_amount / Decimal('100'))
            return round_decimal(fee, ROUNDING_PRECISION)
        else:
            raise ValueError(f"Unknown fee type: {fee_type}")
    except Exception as e:
        logger.error(f"Error calculating fee: {str(e)}")
        raise CalculationException(
            f"Failed to calculate fee: {str(e)}", 
            {
                "base_value": str(base_value),
                "fee_type": str(fee_type),
                "fee_amount": str(fee_amount)
            }
        )


@timed()
def calculate_volatility_adjustment(
    base_rate: Decimal, 
    volatility_index: Decimal, 
    volatility_factor: Optional[Decimal] = None
) -> Decimal:
    """
    Calculates the rate adjustment based on market volatility.
    
    Higher volatility leads to higher adjusted rates.
    
    Args:
        base_rate: The unadjusted base rate
        volatility_index: The market volatility index (e.g., VIX)
        volatility_factor: The factor to apply to the volatility (default: DEFAULT_VOLATILITY_FACTOR)
        
    Returns:
        Decimal: The volatility-adjusted rate
    """
    try:
        if volatility_factor is None:
            volatility_factor = DEFAULT_VOLATILITY_FACTOR
            
        volatility_adjustment = volatility_index * volatility_factor
        adjusted_rate = base_rate * (Decimal('1') + volatility_adjustment)
        # Ensure adjusted rate is not negative
        adjusted_rate = max(adjusted_rate, Decimal('0'))
        
        return round_decimal(adjusted_rate, ROUNDING_PRECISION)
    except Exception as e:
        logger.error(f"Error calculating volatility adjustment: {str(e)}")
        raise CalculationException(
            f"Failed to calculate volatility adjustment: {str(e)}", 
            {
                "base_rate": str(base_rate),
                "volatility_index": str(volatility_index),
                "volatility_factor": str(volatility_factor)
            }
        )


@timed()
def calculate_event_risk_adjustment(
    base_rate: Decimal, 
    event_risk_factor: int, 
    risk_multiplier: Optional[Decimal] = None
) -> Decimal:
    """
    Calculates the rate adjustment based on event risk.
    
    Higher event risk leads to higher adjusted rates.
    
    Args:
        base_rate: The unadjusted base rate
        event_risk_factor: Integer from 0-10 representing event risk (10 being highest)
        risk_multiplier: The multiplier for the risk adjustment (default: DEFAULT_EVENT_RISK_FACTOR)
        
    Returns:
        Decimal: The risk-adjusted rate
    """
    try:
        if risk_multiplier is None:
            risk_multiplier = DEFAULT_EVENT_RISK_FACTOR
            
        risk_adjustment = (Decimal(event_risk_factor) / Decimal('10')) * risk_multiplier
        adjusted_rate = base_rate * (Decimal('1') + risk_adjustment)
        
        return round_decimal(adjusted_rate, ROUNDING_PRECISION)
    except Exception as e:
        logger.error(f"Error calculating event risk adjustment: {str(e)}")
        raise CalculationException(
            f"Failed to calculate event risk adjustment: {str(e)}", 
            {
                "base_rate": str(base_rate),
                "event_risk_factor": event_risk_factor,
                "risk_multiplier": str(risk_multiplier)
            }
        )


def apply_minimum_rate(rate: Decimal, min_rate: Optional[Decimal] = None) -> Decimal:
    """
    Ensures a rate is not below the specified minimum.
    
    Args:
        rate: The rate to check
        min_rate: The minimum rate to apply (default: DEFAULT_MINIMUM_BORROW_RATE)
        
    Returns:
        Decimal: Rate with minimum applied
    """
    try:
        if min_rate is None:
            min_rate = DEFAULT_MINIMUM_BORROW_RATE
            
        result = max(rate, min_rate)
        return round_decimal(result, ROUNDING_PRECISION)
    except Exception as e:
        logger.error(f"Error applying minimum rate: {str(e)}")
        raise CalculationException(
            f"Failed to apply minimum rate: {str(e)}", 
            {
                "rate": str(rate),
                "min_rate": str(min_rate)
            }
        )


@timed()
def prorate_fee(annual_fee: Decimal, days: int) -> Decimal:
    """
    Prorates a fee based on the number of days.
    
    Args:
        annual_fee: The annual fee amount
        days: The number of days to prorate for
        
    Returns:
        Decimal: The prorated fee
    """
    try:
        prorated_fee = annual_fee * (Decimal(days) / DAYS_IN_YEAR)
        return round_decimal(prorated_fee, ROUNDING_PRECISION)
    except Exception as e:
        logger.error(f"Error prorating fee: {str(e)}")
        raise CalculationException(
            f"Failed to prorate fee: {str(e)}", 
            {
                "annual_fee": str(annual_fee),
                "days": days
            }
        )


def sum_fee_components(components: List[Decimal]) -> Decimal:
    """
    Sums multiple fee components into a total fee.
    
    Args:
        components: List of fee components to sum
        
    Returns:
        Decimal: The total sum of all components
    """
    try:
        total = sum(components, Decimal('0'))
        return round_decimal(total, ROUNDING_PRECISION)
    except Exception as e:
        logger.error(f"Error summing fee components: {str(e)}")
        raise CalculationException(
            f"Failed to sum fee components: {str(e)}", 
            {"components_count": len(components)}
        )