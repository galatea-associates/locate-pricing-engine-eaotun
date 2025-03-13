"""
Utility functions for the cache service in the Borrow Rate & Locate Fee Pricing Engine.

This module provides helper functions for cache key generation, serialization/deserialization,
TTL management, and cache operation logging to support the multi-level caching strategy.
"""

import json
import time
from typing import Any, Dict, Optional, List

from ...core.constants import (
    CACHE_TTL_BORROW_RATE,
    CACHE_TTL_VOLATILITY,
    CACHE_TTL_EVENT_RISK,
    CACHE_TTL_BROKER_CONFIG,
    CACHE_TTL_CALCULATION
)
from ...core.logging import get_logger

# Initialize logger for cache operations
logger = get_logger(__name__)


def generate_cache_key(prefix: str, *components: Any) -> str:
    """
    Generates a standardized cache key from components.
    
    Args:
        prefix: Prefix for the cache key
        components: Variable arguments to include in the key
        
    Returns:
        Formatted cache key with prefix and components
    """
    # Convert all components to strings
    str_components = [str(component) for component in components]
    
    # Join components with colon separator
    components_str = ':'.join(str_components)
    
    # Create the full key with prefix
    cache_key = f"{prefix}:{components_str}" if components_str else prefix
    
    return cache_key


def get_borrow_rate_key(ticker: str) -> str:
    """
    Generates a cache key for borrow rate data.
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Cache key for borrow rate data
    """
    return generate_cache_key('borrow_rate', ticker)


def get_volatility_key(ticker: str) -> str:
    """
    Generates a cache key for volatility data.
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Cache key for volatility data
    """
    return generate_cache_key('volatility', ticker)


def get_event_risk_key(ticker: str) -> str:
    """
    Generates a cache key for event risk data.
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Cache key for event risk data
    """
    return generate_cache_key('event_risk', ticker)


def get_broker_config_key(client_id: str) -> str:
    """
    Generates a cache key for broker configuration data.
    
    Args:
        client_id: Unique client identifier
        
    Returns:
        Cache key for broker configuration data
    """
    return generate_cache_key('broker_config', client_id)


def get_calculation_key(ticker: str, client_id: str, position_value: float, loan_days: int) -> str:
    """
    Generates a cache key for calculation results.
    
    Args:
        ticker: Stock symbol
        client_id: Unique client identifier
        position_value: Position value in USD
        loan_days: Loan duration in days
        
    Returns:
        Cache key for calculation results
    """
    return generate_cache_key('calculation', ticker, client_id, position_value, loan_days)


def get_ttl_for_data_type(data_type: str) -> int:
    """
    Returns the appropriate TTL for different data types.
    
    Args:
        data_type: Type of data (borrow_rate, volatility, event_risk, broker_config, calculation)
        
    Returns:
        TTL in seconds for the specified data type
    """
    ttl_mapping = {
        'borrow_rate': CACHE_TTL_BORROW_RATE,
        'volatility': CACHE_TTL_VOLATILITY,
        'event_risk': CACHE_TTL_EVENT_RISK,
        'broker_config': CACHE_TTL_BROKER_CONFIG,
        'calculation': CACHE_TTL_CALCULATION
    }
    
    return ttl_mapping.get(data_type, CACHE_TTL_CALCULATION)  # Default to calculation TTL if type not found


def serialize_cache_value(value: Any) -> str:
    """
    Serializes a value for storage in cache.
    
    Args:
        value: Value to serialize
        
    Returns:
        JSON string representation of the value
    """
    try:
        # Handle special types that aren't directly JSON serializable
        if hasattr(value, 'to_dict') and callable(getattr(value, 'to_dict')):
            value = value.to_dict()
        
        # Convert Decimal objects to float before serialization
        if hasattr(value, '__class__') and value.__class__.__name__ == 'Decimal':
            value = float(value)
            
        return json.dumps(value)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize cache value: {e}")
        # Return a serialized version of the string representation as a fallback
        return json.dumps(str(value))


def deserialize_cache_value(serialized_value: str, value_type: Optional[str] = None) -> Any:
    """
    Deserializes a value retrieved from cache.
    
    Args:
        serialized_value: JSON string to deserialize
        value_type: Optional type hint for conversion
        
    Returns:
        Deserialized value
    """
    try:
        value = json.loads(serialized_value)
        
        # Apply type conversion if specified
        if value_type:
            if value_type == 'float':
                return float(value)
            elif value_type == 'int':
                return int(value)
            elif value_type == 'bool':
                return bool(value)
        
        return value
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to deserialize cache value: {e}")
        return None


def wrap_cache_value(value: Any) -> Dict[str, Any]:
    """
    Wraps a value with metadata for caching.
    
    Args:
        value: Value to wrap
        
    Returns:
        Dictionary with value and metadata
    """
    wrapped = {
        'value': value,
        'timestamp': time.time(),
        'source': 'cache'
    }
    
    # Add source information if available
    if isinstance(value, dict) and 'source' in value:
        wrapped['original_source'] = value['source']
    
    return wrapped


def unwrap_cache_value(wrapped_value: Dict[str, Any]) -> Any:
    """
    Extracts the actual value from a wrapped cache entry.
    
    Args:
        wrapped_value: Dictionary with value and metadata
        
    Returns:
        The original value without metadata
    """
    return wrapped_value.get('value')


def is_cache_stale(wrapped_value: Dict[str, Any], ttl: int) -> bool:
    """
    Checks if a cached value has expired based on TTL.
    
    Args:
        wrapped_value: Dictionary with value and timestamp
        ttl: Time-to-live in seconds
        
    Returns:
        True if the value is stale, False otherwise
    """
    timestamp = wrapped_value.get('timestamp', 0)
    current_time = time.time()
    age = current_time - timestamp
    
    return age > ttl


def log_cache_operation(operation: str, key: str, success: Optional[bool] = None, details: Optional[str] = None) -> None:
    """
    Logs cache operations with standardized format.
    
    Args:
        operation: Type of cache operation (get, set, delete, etc.)
        key: Cache key
        success: Whether operation was successful
        details: Additional details about the operation
    """
    log_message = f"Cache {operation} - Key: {key}"
    
    if success is not None:
        log_message += f" - Success: {success}"
    
    if details:
        log_message += f" - Details: {details}"
    
    if success is False:
        logger.warning(log_message)
    else:
        logger.info(log_message)