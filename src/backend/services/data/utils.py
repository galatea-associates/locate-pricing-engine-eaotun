"""
Utility module for data services in the Borrow Rate & Locate Fee Pricing Engine.

Provides common functionality for data access, validation, caching, and error handling
used across all data service components. Serves as a foundation for implementing
consistent data access patterns and business logic.
"""

import logging
import functools
import re
from typing import Any, Dict, Callable, Optional, TypeVar, cast

import httpx
from sqlalchemy import exc

from ...db.session import get_db
from ...core.exceptions import (
    ValidationException,
    TickerNotFoundException,
    ClientNotFoundException,
    ExternalAPIException
)
from ..cache.redis import redis_cache
from ...config.settings import get_settings

# Configure module logger
logger = logging.getLogger(__name__)

# Default cache TTL (5 minutes)
DEFAULT_CACHE_TTL = 300

# Regex patterns for validation
TICKER_PATTERN = re.compile(r'^[A-Z]{1,5}$')
CLIENT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,50}$')


def validate_ticker(ticker: str) -> str:
    """
    Validates ticker symbol format.
    
    Args:
        ticker: Stock symbol to validate
        
    Returns:
        Normalized ticker symbol (uppercase)
        
    Raises:
        ValidationException: If ticker is invalid
    """
    if not ticker:
        raise ValidationException("Ticker symbol is required")
    
    ticker = ticker.upper()
    
    if not TICKER_PATTERN.match(ticker):
        raise ValidationException(
            "Invalid ticker symbol format. Must be 1-5 uppercase letters.",
            {"ticker": ticker, "pattern": TICKER_PATTERN.pattern}
        )
    
    return ticker


def validate_client_id(client_id: str) -> str:
    """
    Validates client ID format.
    
    Args:
        client_id: Client identifier to validate
        
    Returns:
        Validated client ID
        
    Raises:
        ValidationException: If client_id is invalid
    """
    if not client_id:
        raise ValidationException("Client ID is required")
    
    if not CLIENT_ID_PATTERN.match(client_id):
        raise ValidationException(
            "Invalid client ID format. Must be 3-50 alphanumeric characters, underscores, or hyphens.",
            {"client_id": client_id, "pattern": CLIENT_ID_PATTERN.pattern}
        )
    
    return client_id


T = TypeVar('T')

def cache_result(ttl: int = DEFAULT_CACHE_TTL):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time-to-live in seconds for cached results
        
    Returns:
        Decorated function with caching
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Generate cache key based on function name and arguments
            cache_key = get_cache_key(func.__name__, args, kwargs)
            
            # Try to get result from cache
            cached_result = redis_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cast(T, cached_result)
            
            # Cache miss, call original function
            logger.debug(f"Cache miss for key: {cache_key}")
            result = func(*args, **kwargs)
            
            # Cache the result
            redis_cache.set(cache_key, result, ttl)
            logger.debug(f"Cached result for key: {cache_key}, TTL: {ttl}")
            
            return result
        return wrapper
    return decorator


def get_cache_key(prefix: str, args: tuple, kwargs: dict) -> str:
    """
    Generates a cache key from function name and arguments.
    
    Args:
        prefix: Prefix for the cache key (usually function name)
        args: Positional arguments
        kwargs: Keyword arguments
        
    Returns:
        Cache key string
    """
    # Convert args to string representation
    args_str = ':'.join(str(arg) for arg in args) if args else ''
    
    # Convert kwargs to sorted string representation
    kwargs_items = sorted(kwargs.items())
    kwargs_str = ':'.join(f"{k}={v}" for k, v in kwargs_items) if kwargs_items else ''
    
    # Combine prefix, args, and kwargs with separators
    if args_str and kwargs_str:
        return f"{prefix}:{args_str}:{kwargs_str}"
    elif args_str:
        return f"{prefix}:{args_str}"
    elif kwargs_str:
        return f"{prefix}:{kwargs_str}"
    else:
        return prefix


class DataServiceBase:
    """
    Base class for all data services with common functionality.
    
    Provides shared methods for database access, logging, and error handling
    that can be used across different data service implementations.
    """
    
    def __init__(self):
        """Initialize the data service base class."""
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def _get_db_session(self):
        """
        Get a database session using context manager.
        
        Returns:
            Database session context manager
        """
        return get_db()
    
    def _log_operation(self, operation: str, message: str, level: str = "INFO"):
        """
        Log a service operation with appropriate level.
        
        Args:
            operation: Name of the operation
            message: Log message
            level: Log level (default: INFO)
        """
        log_msg = f"{operation}: {message}"
        
        if level.upper() == "DEBUG":
            self._logger.debug(log_msg)
        elif level.upper() == "INFO":
            self._logger.info(log_msg)
        elif level.upper() == "WARNING":
            self._logger.warning(log_msg)
        elif level.upper() == "ERROR":
            self._logger.error(log_msg)
        elif level.upper() == "CRITICAL":
            self._logger.critical(log_msg)
        else:
            # Default to INFO if unknown level
            self._logger.info(log_msg)
    
    def _handle_db_error(self, error: Exception, operation: str):
        """
        Handle database errors with appropriate logging and exception translation.
        
        Args:
            error: Original database exception
            operation: Description of the database operation
            
        Raises:
            Appropriate API exception based on the type of database error
        """
        self._logger.error(f"Database error during {operation}: {str(error)}")
        
        # Translate SQLAlchemy exceptions to appropriate API exceptions
        if isinstance(error, exc.NoResultFound):
            if "ticker" in operation.lower():
                ticker = operation.split()[-1]
                raise TickerNotFoundException(ticker)
            elif "client" in operation.lower():
                client_id = operation.split()[-1]
                raise ClientNotFoundException(client_id)
            else:
                raise ValidationException(f"Resource not found: {operation}")
        
        elif isinstance(error, exc.IntegrityError):
            raise ValidationException(f"Database integrity error: {str(error)}")
        
        else:
            # Re-raise the original exception if no specific translation
            raise error
    
    def _handle_external_api_error(self, error: Exception, service_name: str, operation: str):
        """
        Handle external API errors with appropriate logging and exception translation.
        
        Args:
            error: Original API exception
            service_name: Name of the external service
            operation: Description of the API operation
            
        Raises:
            ExternalAPIException with details about the failure
        """
        self._logger.error(f"External API error during {operation} to {service_name}: {str(error)}")
        
        # Create detailed error message
        detail = f"Failed during {operation}: {str(error)}"
        
        # Raise appropriate exception
        raise ExternalAPIException(service_name, detail)