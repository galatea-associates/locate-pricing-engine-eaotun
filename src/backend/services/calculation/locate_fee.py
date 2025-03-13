"""
Core module responsible for calculating locate fees for securities borrowing transactions in the Borrow Rate & 
Locate Fee Pricing Engine. This module implements the formulas and business logic for determining the total fee 
charged to clients, including base borrow cost, broker markup, and transaction fees.
"""

import logging
from decimal import Decimal
from typing import Dict, Optional, Union, Any, List
import json

# Import constants
from ...core.constants import (
    DAYS_IN_YEAR,
    DEFAULT_MARKUP_PERCENTAGE,
    DEFAULT_TRANSACTION_FEE_FLAT,
    DEFAULT_TRANSACTION_FEE_PERCENTAGE,
    TransactionFeeType
)

# Import exceptions
from ...core.exceptions import CalculationException

# Import utility functions
from ...utils.math import round_decimal
from ...utils.validation import convert_to_decimal
from ...utils.timing import timed

# Import calculation functions
from .borrow_rate import calculate_borrow_rate
from .formulas import (
    calculate_borrow_cost,
    calculate_markup_amount,
    calculate_fee,
    sum_fee_components
)

# Import cache
from ..cache.redis import RedisCache

# Set up logger
logger = logging.getLogger(__name__)

# Constants
ROUNDING_PRECISION = 4
LOCATE_FEE_CACHE_PREFIX = 'locate_fee'
LOCATE_FEE_CACHE_TTL = 60  # 60 seconds


@timed
def calculate_locate_fee(
    ticker: str,
    position_value: Decimal,
    loan_days: int,
    markup_percentage: Decimal,
    fee_type: TransactionFeeType,
    fee_amount: Decimal,
    borrow_rate: Optional[Decimal] = None,
    use_cache: Optional[bool] = True
) -> Dict[str, Any]:
    """
    Main function to calculate the total locate fee for a securities borrowing transaction.
    
    Args:
        ticker: Stock symbol
        position_value: Monetary value of the position
        loan_days: Duration of the loan in days
        markup_percentage: Percentage markup applied by the broker
        fee_type: Type of transaction fee (FLAT or PERCENTAGE)
        fee_amount: Amount of transaction fee
        borrow_rate: Optional pre-determined borrow rate; if not provided, will be calculated
        use_cache: Whether to check and use cached results
        
    Returns:
        Dict[str, Any]: Dictionary containing total fee and breakdown of fee components
    """
    logger.info(f"Calculating locate fee for ticker: {ticker}, position_value: {position_value}, "
               f"loan_days: {loan_days}, markup_percentage: {markup_percentage}, "
               f"fee_type: {fee_type}, fee_amount: {fee_amount}")
    
    # Check if use_cache is True (default) and try to get cached result
    if use_cache:
        cached_result = get_cached_locate_fee(
            ticker, position_value, loan_days, markup_percentage, fee_type, fee_amount
        )
        if cached_result is not None:
            logger.info(f"Using cached locate fee result for {ticker}")
            return cached_result
    
    # If borrow_rate is not provided, calculate it using calculate_borrow_rate
    if borrow_rate is None:
        logger.info(f"Borrow rate not provided, calculating it for {ticker}")
        borrow_rate = calculate_borrow_rate(ticker)
    
    # Calculate base borrow cost
    base_borrow_cost = calculate_borrow_cost(position_value, borrow_rate, loan_days)
    logger.debug(f"Base borrow cost calculated: {base_borrow_cost}")
    
    # Calculate markup amount
    markup_amount = calculate_markup_amount(base_borrow_cost, markup_percentage)
    logger.debug(f"Markup amount calculated: {markup_amount}")
    
    # Calculate transaction fee
    transaction_fee = calculate_fee(position_value, fee_type, fee_amount)
    logger.debug(f"Transaction fee calculated: {transaction_fee}")
    
    # Calculate total fee
    total_fee = sum_fee_components([base_borrow_cost, markup_amount, transaction_fee])
    logger.debug(f"Total fee calculated: {total_fee}")
    
    # Create result dictionary
    result = {
        "total_fee": float(total_fee),
        "breakdown": {
            "borrow_cost": float(base_borrow_cost),
            "markup": float(markup_amount),
            "transaction_fees": float(transaction_fee)
        },
        "borrow_rate_used": float(borrow_rate)
    }
    
    # Cache the calculation result if use_cache is True
    if use_cache:
        cache_locate_fee(
            ticker, position_value, loan_days, markup_percentage, fee_type, fee_amount, result
        )
    
    logger.info(f"Locate fee calculation completed for {ticker}: {total_fee}")
    return result


def get_cached_locate_fee(
    ticker: str,
    position_value: Decimal,
    loan_days: int,
    markup_percentage: Decimal,
    fee_type: TransactionFeeType,
    fee_amount: Decimal
) -> Optional[Dict[str, Any]]:
    """
    Attempts to retrieve a cached locate fee calculation result.
    
    Args:
        ticker: Stock symbol
        position_value: Monetary value of the position
        loan_days: Duration of the loan in days
        markup_percentage: Percentage markup applied by the broker
        fee_type: Type of transaction fee (FLAT or PERCENTAGE)
        fee_amount: Amount of transaction fee
        
    Returns:
        Optional[Dict[str, Any]]: Cached calculation result if available, None otherwise
    """
    # Generate cache key
    cache_key = generate_cache_key(
        ticker, position_value, loan_days, markup_percentage, fee_type, fee_amount
    )
    
    # Get Redis cache instance
    cache = RedisCache()
    
    try:
        # Try to get value from cache
        cached_value = cache.get(cache_key)
        
        # If value exists in cache, deserialize and return
        if cached_value is not None:
            # Deserialize JSON to dictionary
            result = json.loads(cached_value)
            
            logger.debug(f"Cache hit for locate fee calculation - Key: {cache_key}")
            return result
        
        # If value doesn't exist or cache is unavailable, return None
        logger.debug(f"Cache miss for locate fee calculation - Key: {cache_key}")
        return None
            
    except Exception as e:
        logger.warning(f"Error retrieving cached locate fee: {str(e)}")
        return None


def cache_locate_fee(
    ticker: str,
    position_value: Decimal,
    loan_days: int,
    markup_percentage: Decimal,
    fee_type: TransactionFeeType,
    fee_amount: Decimal,
    result: Dict[str, Any],
    ttl: Optional[int] = None
) -> bool:
    """
    Caches a locate fee calculation result for future use.
    
    Args:
        ticker: Stock symbol
        position_value: Monetary value of the position
        loan_days: Duration of the loan in days
        markup_percentage: Percentage markup applied by the broker
        fee_type: Type of transaction fee (FLAT or PERCENTAGE)
        fee_amount: Amount of transaction fee
        result: Calculation result to cache
        ttl: Time-to-live in seconds (default: LOCATE_FEE_CACHE_TTL)
        
    Returns:
        bool: True if caching was successful, False otherwise
    """
    # Generate cache key
    cache_key = generate_cache_key(
        ticker, position_value, loan_days, markup_percentage, fee_type, fee_amount
    )
    
    # Get Redis cache instance
    cache = RedisCache()
    
    try:
        # Convert result to JSON string
        result_json = json.dumps(result)
        
        # Set value in cache with TTL
        ttl_value = ttl if ttl is not None else LOCATE_FEE_CACHE_TTL
        success = cache.set(cache_key, result_json, ttl_value)
        
        if success:
            logger.debug(f"Cached locate fee calculation - Key: {cache_key}, TTL: {ttl_value}s")
        else:
            logger.warning(f"Failed to cache locate fee calculation - Key: {cache_key}")
            
        return success
        
    except Exception as e:
        logger.warning(f"Error caching locate fee calculation: {str(e)}")
        return False


def generate_cache_key(
    ticker: str,
    position_value: Decimal,
    loan_days: int,
    markup_percentage: Decimal,
    fee_type: TransactionFeeType,
    fee_amount: Decimal
) -> str:
    """
    Generates a cache key for locate fee calculations.
    
    Args:
        ticker: Stock symbol
        position_value: Monetary value of the position
        loan_days: Duration of the loan in days
        markup_percentage: Percentage markup applied by the broker
        fee_type: Type of transaction fee (FLAT or PERCENTAGE)
        fee_amount: Amount of transaction fee
        
    Returns:
        str: Cache key string
    """
    # Normalize ticker to uppercase
    ticker_normalized = ticker.upper()
    
    # Format numeric values to consistent strings
    position_str = f"{float(position_value):.2f}"
    loan_days_str = str(loan_days)
    markup_str = f"{float(markup_percentage):.2f}"
    fee_type_str = fee_type.value
    fee_amount_str = f"{float(fee_amount):.2f}"
    
    # Combine all parameters into a key
    key = f"{LOCATE_FEE_CACHE_PREFIX}:{ticker_normalized}:{position_str}:{loan_days_str}:{markup_str}:{fee_type_str}:{fee_amount_str}"
    
    return key


def get_default_broker_config() -> Dict[str, Any]:
    """
    Provides default broker configuration when specific broker data is unavailable.
    
    Returns:
        Dict[str, Any]: Dictionary with default markup percentage and fee configuration
    """
    default_config = {
        "markup_percentage": DEFAULT_MARKUP_PERCENTAGE,
        "fee_type": TransactionFeeType.FLAT,
        "fee_amount": DEFAULT_TRANSACTION_FEE_FLAT
    }
    
    logger.info(f"Using default broker configuration: {default_config}")
    return default_config


@timed
def calculate_fee_breakdown(
    ticker: str,
    position_value: Decimal,
    loan_days: int,
    borrow_rate: Decimal,
    markup_percentage: Decimal,
    fee_type: TransactionFeeType,
    fee_amount: Decimal
) -> Dict[str, Any]:
    """
    Calculates a detailed breakdown of all fee components.
    
    Args:
        ticker: Stock symbol
        position_value: Monetary value of the position
        loan_days: Duration of the loan in days
        borrow_rate: Annual borrow rate as a decimal
        markup_percentage: Percentage markup applied by the broker
        fee_type: Type of transaction fee (FLAT or PERCENTAGE)
        fee_amount: Amount of transaction fee
        
    Returns:
        Dict[str, Any]: Dictionary with detailed breakdown of all fee components
    """
    logger.info(f"Calculating detailed fee breakdown for ticker: {ticker}")
    
    # Calculate base borrow cost
    base_borrow_cost = calculate_borrow_cost(position_value, borrow_rate, loan_days)
    
    # Calculate markup amount
    markup_amount = calculate_markup_amount(base_borrow_cost, markup_percentage)
    
    # Calculate transaction fee
    transaction_fee = calculate_fee(position_value, fee_type, fee_amount)
    
    # Calculate total fee
    total_fee = sum_fee_components([base_borrow_cost, markup_amount, transaction_fee])
    
    # Create detailed breakdown
    daily_rate = borrow_rate / DAYS_IN_YEAR
    
    breakdown = {
        "inputs": {
            "ticker": ticker,
            "position_value": float(position_value),
            "loan_days": loan_days,
            "borrow_rate_annual": float(borrow_rate),
            "borrow_rate_daily": float(daily_rate),
            "markup_percentage": float(markup_percentage),
            "fee_type": fee_type.value,
            "fee_amount": float(fee_amount)
        },
        "calculations": {
            "base_borrow_cost": {
                "formula": "position_value × daily_rate × loan_days",
                "calculation": f"{float(position_value)} × {float(daily_rate)} × {loan_days}",
                "result": float(base_borrow_cost)
            },
            "markup": {
                "formula": "base_borrow_cost × (markup_percentage / 100)",
                "calculation": f"{float(base_borrow_cost)} × ({float(markup_percentage)} / 100)",
                "result": float(markup_amount)
            },
            "transaction_fee": {
                "fee_type": fee_type.value,
                "formula": "flat amount" if fee_type == TransactionFeeType.FLAT else "position_value × (fee_percentage / 100)",
                "calculation": f"{float(fee_amount)}" if fee_type == TransactionFeeType.FLAT else f"{float(position_value)} × ({float(fee_amount)} / 100)",
                "result": float(transaction_fee)
            }
        },
        "totals": {
            "base_borrow_cost": float(base_borrow_cost),
            "markup": float(markup_amount),
            "transaction_fee": float(transaction_fee),
            "total_fee": float(total_fee)
        }
    }
    
    logger.info(f"Fee breakdown calculation completed for {ticker}")
    return breakdown