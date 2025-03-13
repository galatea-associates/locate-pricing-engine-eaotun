"""
Constants and enumerations for the Borrow Rate & Locate Fee Pricing Engine.

This module centralizes all constant values used throughout the application to ensure
consistency. It includes financial parameters, cache TTLs, error codes, and other
configuration values needed for the pricing engine's operation.
"""

from enum import Enum
from decimal import Decimal

# Financial constants
DAYS_IN_YEAR = Decimal('365')  # Used for annualized rate calculations

# Default values for calculation parameters
DEFAULT_MINIMUM_BORROW_RATE = Decimal('0.0001')  # 0.01% minimum rate
DEFAULT_VOLATILITY_FACTOR = Decimal('0.01')      # 1% factor for volatility adjustment
DEFAULT_EVENT_RISK_FACTOR = Decimal('0.05')      # 5% factor for event risk adjustment

# Default broker configuration values
DEFAULT_MARKUP_PERCENTAGE = Decimal('5.0')            # 5% default markup
DEFAULT_TRANSACTION_FEE_FLAT = Decimal('25.0')        # $25 default flat fee
DEFAULT_TRANSACTION_FEE_PERCENTAGE = Decimal('0.5')   # 0.5% default percentage fee

# API rate limits (requests per minute)
API_RATE_LIMIT_DEFAULT = 60   # Standard client rate limit
API_RATE_LIMIT_PREMIUM = 300  # Premium client rate limit

# Cache time-to-live values (in seconds)
CACHE_TTL_BORROW_RATE = 300      # 5 minutes for borrow rates
CACHE_TTL_VOLATILITY = 900       # 15 minutes for volatility data
CACHE_TTL_EVENT_RISK = 3600      # 1 hour for event risk data
CACHE_TTL_BROKER_CONFIG = 1800   # 30 minutes for broker configurations
CACHE_TTL_CALCULATION = 60       # 1 minute for calculation results
CACHE_TTL_MIN_RATE = 86400       # 24 hours for minimum rates

# Security settings
API_KEY_EXPIRY_DAYS = 90  # Default API key expiration period in days


class ErrorCodes(Enum):
    """
    Enumeration of error codes used throughout the application.
    
    These error codes provide standardized identifiers for different error conditions
    that may occur during API requests or calculations.
    """
    INVALID_PARAMETER = "INVALID_PARAMETER"        # Missing or invalid request parameter
    UNAUTHORIZED = "UNAUTHORIZED"                  # Authentication failure
    TICKER_NOT_FOUND = "TICKER_NOT_FOUND"          # Requested stock symbol not found
    CLIENT_NOT_FOUND = "CLIENT_NOT_FOUND"          # Client ID not found in the system
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"    # API rate limit exceeded
    CALCULATION_ERROR = "CALCULATION_ERROR"        # Error during fee calculation
    EXTERNAL_API_UNAVAILABLE = "EXTERNAL_API_UNAVAILABLE"  # External data source unavailable


class TransactionFeeType(Enum):
    """
    Enumeration of transaction fee types for broker configurations.
    
    Defines the possible fee structures that can be applied when calculating
    client-specific locate fees.
    """
    FLAT = "FLAT"              # Fixed amount per transaction
    PERCENTAGE = "PERCENTAGE"  # Percentage of position value


class BorrowStatus(Enum):
    """
    Enumeration of borrow status categories for stocks.
    
    Categorizes securities based on their availability for borrowing, which
    may affect the borrow rate calculation.
    """
    EASY = "EASY"      # Readily available for borrowing
    MEDIUM = "MEDIUM"  # Moderately available for borrowing
    HARD = "HARD"      # Difficult to borrow, typically higher rates