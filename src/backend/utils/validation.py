"""
Utility module providing validation functions for input parameters in the Borrow Rate & Locate Fee Pricing Engine.
This module ensures that all API inputs meet the required format and value constraints before processing,
providing clear error messages when validation fails.
"""

import re
import logging
from decimal import Decimal
from typing import Dict, Any, Optional

from ..core.constants import ErrorCodes
from ..core.exceptions import ValidationException

# Set up logger
logger = logging.getLogger(__name__)

# Validation constants and patterns
TICKER_PATTERN = re.compile(r'^[A-Z]{1,5}$')
CLIENT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,50}$')

# Validation limits
MIN_POSITION_VALUE = Decimal('0.01')
MAX_POSITION_VALUE = Decimal('1000000000')  # 1 billion
MIN_LOAN_DAYS = 1
MAX_LOAN_DAYS = 365
MIN_BORROW_RATE = Decimal('0.0001')  # 0.01%
MAX_BORROW_RATE = Decimal('1.0')     # 100%


class ValidationError(Exception):
    """
    Custom exception class for validation errors that provides structured error information
    """
    
    def __init__(self, errors: Dict[str, str]):
        """
        Initialize the validation error with a dictionary of field errors
        
        Args:
            errors: Dictionary mapping field names to error descriptions
        """
        super().__init__("Validation error occurred")
        self.errors = errors
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert validation errors to a dictionary format for API responses
        
        Returns:
            Dictionary representation of validation errors
        """
        return {
            "status": "error",
            "errors": self.errors
        }


def validate_ticker(ticker: str) -> bool:
    """
    Validates that a ticker symbol is in the correct format
    
    Args:
        ticker: Stock ticker symbol to validate
        
    Returns:
        True if ticker is valid, False otherwise
    """
    if ticker is None or not ticker:
        return False
    
    ticker = ticker.upper()
    return bool(TICKER_PATTERN.match(ticker))


def validate_position_value(position_value: Decimal) -> bool:
    """
    Validates that a position value is within acceptable range
    
    Args:
        position_value: The monetary value of the position to validate
        
    Returns:
        True if position value is valid, False otherwise
    """
    if position_value is None:
        return False
    
    # Convert to Decimal if it's not already
    if not isinstance(position_value, Decimal):
        try:
            position_value = Decimal(str(position_value))
        except (ValueError, TypeError, ArithmeticError):
            return False
    
    return MIN_POSITION_VALUE <= position_value <= MAX_POSITION_VALUE


def validate_loan_days(loan_days: int) -> bool:
    """
    Validates that loan days is within acceptable range
    
    Args:
        loan_days: Number of days for the loan to validate
        
    Returns:
        True if loan days is valid, False otherwise
    """
    if loan_days is None:
        return False
    
    # Convert to int if it's not already
    if not isinstance(loan_days, int):
        try:
            loan_days = int(loan_days)
        except (ValueError, TypeError):
            return False
    
    return MIN_LOAN_DAYS <= loan_days <= MAX_LOAN_DAYS


def validate_client_id(client_id: str) -> bool:
    """
    Validates that a client ID is in the correct format
    
    Args:
        client_id: Client identifier to validate
        
    Returns:
        True if client ID is valid, False otherwise
    """
    if client_id is None or not client_id:
        return False
    
    return bool(CLIENT_ID_PATTERN.match(client_id))


def validate_borrow_rate(borrow_rate: Decimal) -> bool:
    """
    Validates that a borrow rate is within acceptable range
    
    Args:
        borrow_rate: The borrow rate to validate
        
    Returns:
        True if borrow rate is valid, False otherwise
    """
    if borrow_rate is None:
        return False
    
    # Convert to Decimal if it's not already
    if not isinstance(borrow_rate, Decimal):
        try:
            borrow_rate = Decimal(str(borrow_rate))
        except (ValueError, TypeError, ArithmeticError):
            return False
    
    return MIN_BORROW_RATE <= borrow_rate <= MAX_BORROW_RATE


def validate_calculation_parameters(
    ticker: str,
    position_value: Decimal,
    loan_days: int,
    client_id: str
) -> Dict[str, Any]:
    """
    Validates all parameters required for fee calculation
    
    Args:
        ticker: Stock ticker symbol
        position_value: Monetary value of the position
        loan_days: Number of days for the loan
        client_id: Client identifier
        
    Returns:
        Dictionary of validation errors, empty if all valid
    """
    errors = {}
    
    if not validate_ticker(ticker):
        errors['ticker'] = f"Invalid ticker format. Must be 1-5 uppercase letters."
    
    if not validate_position_value(position_value):
        errors['position_value'] = f"Invalid position value. Must be between {MIN_POSITION_VALUE} and {MAX_POSITION_VALUE}."
    
    if not validate_loan_days(loan_days):
        errors['loan_days'] = f"Invalid loan days. Must be between {MIN_LOAN_DAYS} and {MAX_LOAN_DAYS}."
    
    if not validate_client_id(client_id):
        errors['client_id'] = f"Invalid client ID format. Must be 3-50 alphanumeric characters, underscores, or hyphens."
    
    return errors


def raise_validation_error(param: str, detail: str) -> None:
    """
    Raises a ValidationException with appropriate error details
    
    Args:
        param: Parameter name that failed validation
        detail: Detailed explanation of the validation failure
        
    Raises:
        ValidationException: Always raised with the specified details
    """
    logger.warning(f"Validation error for parameter '{param}': {detail}")
    raise ValidationException(
        message=f"Invalid parameter: {detail}",
        params={"parameter": param, "detail": detail}
    )