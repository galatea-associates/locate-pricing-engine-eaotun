"""
Utility module providing helper functions for the calculation service in the Borrow Rate & Locate Fee Pricing Engine.
This module contains common utility functions for input validation, data conversion, and calculation operations
that are used across different calculation components.
"""

from decimal import Decimal
from typing import Union, Dict, Optional
import logging

from ...core.constants import DAYS_IN_YEAR, DEFAULT_MINIMUM_BORROW_RATE, TransactionFeeType
from ...core.exceptions import CalculationException
from ...utils.math import round_decimal
from ...utils.validation import (
    validate_position_value,
    validate_borrow_rate,
    validate_loan_days,
    convert_to_decimal,
    convert_to_int
)
from ...utils.timing import timed

# Configure logger
logger = logging.getLogger(__name__)

# Number of decimal places to round financial calculations
ROUNDING_PRECISION = 4


def validate_calculation_inputs(
    position_value: Union[str, float, Decimal],
    borrow_rate: Union[str, float, Decimal],
    loan_days: Union[str, int]
) -> tuple[Decimal, Decimal, int]:
    """
    Validates all inputs required for fee calculation and converts them to appropriate types
    
    Args:
        position_value: The monetary value of the position
        borrow_rate: The annual borrow rate as a decimal (e.g., 0.05 for 5%)
        loan_days: The duration of the loan in days
        
    Returns:
        tuple[Decimal, Decimal, int]: Validated and converted inputs (position_value, borrow_rate, loan_days)
        
    Raises:
        CalculationException: If any input fails validation
    """
    try:
        # Convert position_value to Decimal using convert_to_decimal
        position_value_decimal = convert_to_decimal(position_value)
        # Validate position_value using validate_position_value
        if not validate_position_value(position_value_decimal):
            raise CalculationException(
                f"Invalid position value: {position_value}. Must be a positive number.",
                {"position_value": position_value}
            )
            
        # Convert borrow_rate to Decimal using convert_to_decimal
        borrow_rate_decimal = convert_to_decimal(borrow_rate)
        # Validate borrow_rate using validate_borrow_rate
        if not validate_borrow_rate(borrow_rate_decimal):
            raise CalculationException(
                f"Invalid borrow rate: {borrow_rate}. Must be a positive number.",
                {"borrow_rate": borrow_rate}
            )
            
        # Convert loan_days to int using convert_to_int
        loan_days_int = convert_to_int(loan_days)
        # Validate loan_days using validate_loan_days
        if not validate_loan_days(loan_days_int):
            raise CalculationException(
                f"Invalid loan days: {loan_days}. Must be a positive integer.",
                {"loan_days": loan_days}
            )
            
        # Return tuple of validated inputs
        return position_value_decimal, borrow_rate_decimal, loan_days_int
    except Exception as e:
        if not isinstance(e, CalculationException):
            logger.error(f"Error validating calculation inputs: {str(e)}")
            raise CalculationException(
                "Error validating calculation inputs",
                {
                    "position_value": position_value,
                    "borrow_rate": borrow_rate,
                    "loan_days": loan_days
                }
            )
        raise


@timed
def calculate_daily_borrow_rate(annual_rate: Decimal) -> Decimal:
    """
    Calculates the daily borrow rate from an annual rate
    
    Args:
        annual_rate: Annual borrow rate as a decimal (e.g., 0.05 for 5%)
        
    Returns:
        Decimal: Daily borrow rate
    """
    # Divide annual_rate by DAYS_IN_YEAR to get daily rate
    daily_rate = annual_rate / DAYS_IN_YEAR
    # Round result to ROUNDING_PRECISION decimal places
    return round_decimal(daily_rate, ROUNDING_PRECISION)


@timed
def calculate_base_borrow_cost(
    position_value: Decimal,
    annual_borrow_rate: Decimal,
    loan_days: int
) -> Decimal:
    """
    Calculates the base cost of borrowing securities
    
    Args:
        position_value: Monetary value of the position
        annual_borrow_rate: Annual borrow rate as a decimal (e.g., 0.05 for 5%)
        loan_days: Duration of the loan in days
        
    Returns:
        Decimal: Base borrow cost
    """
    # Calculate daily borrow rate
    daily_rate = calculate_daily_borrow_rate(annual_borrow_rate)
    # Calculate borrow cost: position_value * daily_rate * loan_days
    borrow_cost = position_value * daily_rate * Decimal(loan_days)
    # Round result to ROUNDING_PRECISION decimal places
    return round_decimal(borrow_cost, ROUNDING_PRECISION)


@timed
def calculate_broker_markup(base_cost: Decimal, markup_percentage: Decimal) -> Decimal:
    """
    Calculates the broker markup amount based on base cost and markup percentage
    
    Args:
        base_cost: Base cost of borrowing
        markup_percentage: Percentage markup to apply (e.g., 5.0 for 5%)
        
    Returns:
        Decimal: Markup amount
    """
    # Calculate markup amount: base_cost * (markup_percentage / 100)
    markup_amount = base_cost * (markup_percentage / Decimal('100'))
    # Round result to ROUNDING_PRECISION decimal places
    return round_decimal(markup_amount, ROUNDING_PRECISION)


@timed
def calculate_transaction_fee(
    position_value: Decimal,
    fee_type: TransactionFeeType,
    fee_amount: Decimal
) -> Decimal:
    """
    Calculates the transaction fee based on fee type and amount
    
    Args:
        position_value: Monetary value of the position
        fee_type: Type of fee (FLAT or PERCENTAGE)
        fee_amount: Fee amount (flat amount or percentage)
        
    Returns:
        Decimal: Transaction fee amount
    """
    # If fee_type is FLAT, return fee_amount directly
    if fee_type == TransactionFeeType.FLAT:
        return fee_amount
    # If fee_type is PERCENTAGE, calculate fee as position_value * (fee_amount / 100)
    elif fee_type == TransactionFeeType.PERCENTAGE:
        fee = position_value * (fee_amount / Decimal('100'))
        # Round result to ROUNDING_PRECISION decimal places
        return round_decimal(fee, ROUNDING_PRECISION)
    else:
        logger.error(f"Unknown fee type: {fee_type}")
        raise CalculationException(
            f"Unknown fee type: {fee_type}",
            {"fee_type": str(fee_type)}
        )


@timed
def calculate_total_fee(
    base_cost: Decimal,
    markup_amount: Decimal,
    transaction_fee: Decimal
) -> Decimal:
    """
    Calculates the total locate fee including base cost, markup, and transaction fees
    
    Args:
        base_cost: Base cost of borrowing
        markup_amount: Broker markup amount
        transaction_fee: Transaction fee amount
        
    Returns:
        Decimal: Total fee amount
    """
    # Sum base_cost, markup_amount, and transaction_fee
    total = base_cost + markup_amount + transaction_fee
    # Round result to ROUNDING_PRECISION decimal places
    return round_decimal(total, ROUNDING_PRECISION)


def create_fee_breakdown(
    base_cost: Decimal,
    markup_amount: Decimal,
    transaction_fee: Decimal,
    total_fee: Decimal
) -> Dict:
    """
    Creates a detailed breakdown of fee components for API response
    
    Args:
        base_cost: Base cost of borrowing
        markup_amount: Broker markup amount
        transaction_fee: Transaction fee amount
        total_fee: Total fee amount
        
    Returns:
        Dict: Dictionary containing fee breakdown components
    """
    # Create dictionary with all fee components
    # Convert all Decimal values to float for JSON serialization
    return {
        "borrow_cost": float(base_cost),
        "markup": float(markup_amount),
        "transaction_fees": float(transaction_fee),
        "total_fee": float(total_fee)
    }


def format_rate_percentage(rate: Decimal) -> str:
    """
    Formats a rate as a percentage string for display purposes
    
    Args:
        rate: Rate as a decimal (e.g., 0.05 for 5%)
        
    Returns:
        str: Formatted percentage string
    """
    # Multiply rate by 100 to convert to percentage
    percentage = rate * Decimal('100')
    # Round to ROUNDING_PRECISION decimal places
    rounded_percentage = round_decimal(percentage, ROUNDING_PRECISION)
    # Format as string with % symbol
    return f"{rounded_percentage}%"


def apply_minimum_borrow_rate(borrow_rate: Decimal, min_rate: Optional[Decimal] = None) -> Decimal:
    """
    Ensures the borrow rate is not below the minimum allowed rate
    
    Args:
        borrow_rate: The calculated borrow rate
        min_rate: Optional minimum rate to apply (defaults to DEFAULT_MINIMUM_BORROW_RATE)
        
    Returns:
        Decimal: Borrow rate with minimum applied
    """
    # If min_rate is None, use DEFAULT_MINIMUM_BORROW_RATE
    if min_rate is None:
        min_rate = DEFAULT_MINIMUM_BORROW_RATE
    
    # Return the maximum of borrow_rate and min_rate
    result = max(borrow_rate, min_rate)
    # Ensure the result is properly rounded
    return round_decimal(result, ROUNDING_PRECISION)