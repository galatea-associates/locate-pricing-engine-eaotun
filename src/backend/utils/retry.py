"""
Utility module implementing retry logic for handling transient failures when communicating with external APIs.

This module provides decorators for both synchronous and asynchronous functions, with configurable retry attempts,
backoff strategies, and fallback mechanisms.
"""

import time
import random
import functools
import asyncio
from typing import Callable, TypeVar, Any, Optional, Tuple, Type

from ..utils.logging import setup_logger
from ..utils.timing import get_current_time_ms

# Set up logger
logger = setup_logger('retry')

# Type variable for generic function types
T = TypeVar('T')

# Default retry parameters
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 2
DEFAULT_INITIAL_WAIT = 0.1  # 100ms
DEFAULT_MAX_WAIT = 30.0  # 30 seconds
DEFAULT_JITTER_FACTOR = 0.1  # 10% jitter


def calculate_wait_time(
    attempt: int,
    backoff_factor: float,
    initial_wait: float,
    max_wait: float,
    jitter_factor: float
) -> float:
    """
    Calculate the wait time for the next retry attempt using exponential backoff with jitter.
    
    Args:
        attempt: Current attempt number (starting from 0)
        backoff_factor: Factor to multiply wait time by for each attempt
        initial_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds
        jitter_factor: Factor to determine jitter amount (0-1)
        
    Returns:
        float: Wait time in seconds for the next retry attempt
    """
    # Calculate base wait time using exponential backoff
    wait_time = initial_wait * (backoff_factor ** attempt)
    
    # Apply maximum wait time cap
    wait_time = min(wait_time, max_wait)
    
    # Apply jitter to prevent thundering herd problem
    jitter = wait_time * jitter_factor * (2 * random.random() - 1)
    wait_time += jitter
    
    # Ensure wait time is not negative
    wait_time = max(0, wait_time)
    
    return wait_time


def retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    initial_wait: float = DEFAULT_INITIAL_WAIT,
    max_wait: float = DEFAULT_MAX_WAIT,
    exceptions_to_retry: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator that retries a function on specified exceptions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Factor to multiply wait time by for each attempt
        initial_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds
        exceptions_to_retry: Tuple of exception types to retry on
        
    Returns:
        Callable: Decorator function that implements retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions_to_retry as e:
                    attempt += 1
                    
                    if attempt > max_retries:
                        logger.error(
                            f"Maximum retries ({max_retries}) reached for {func.__name__}. "
                            f"Last error: {str(e)}"
                        )
                        raise  # Re-raise the last exception
                    
                    wait_time = calculate_wait_time(
                        attempt, backoff_factor, initial_wait, max_wait, DEFAULT_JITTER_FACTOR
                    )
                    
                    logger.warning(
                        f"Retry attempt {attempt}/{max_retries} for {func.__name__} "
                        f"after {wait_time:.2f}s. Error: {str(e)}"
                    )
                    
                    time.sleep(wait_time)
        
        return wrapper
    
    return decorator


def retry_async(
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    initial_wait: float = DEFAULT_INITIAL_WAIT,
    max_wait: float = DEFAULT_MAX_WAIT,
    exceptions_to_retry: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator that retries an async function on specified exceptions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Factor to multiply wait time by for each attempt
        initial_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds
        exceptions_to_retry: Tuple of exception types to retry on
        
    Returns:
        Callable: Decorator function that implements async retry logic
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions_to_retry as e:
                    attempt += 1
                    
                    if attempt > max_retries:
                        logger.error(
                            f"Maximum retries ({max_retries}) reached for {func.__name__}. "
                            f"Last error: {str(e)}"
                        )
                        raise  # Re-raise the last exception
                    
                    wait_time = calculate_wait_time(
                        attempt, backoff_factor, initial_wait, max_wait, DEFAULT_JITTER_FACTOR
                    )
                    
                    logger.warning(
                        f"Retry attempt {attempt}/{max_retries} for {func.__name__} "
                        f"after {wait_time:.2f}s. Error: {str(e)}"
                    )
                    
                    await asyncio.sleep(wait_time)
        
        return wrapper
    
    return decorator


def retry_with_fallback(
    fallback_value: Any,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    initial_wait: float = DEFAULT_INITIAL_WAIT,
    max_wait: float = DEFAULT_MAX_WAIT,
    exceptions_to_retry: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator that retries a function and returns a fallback value if all retries fail.
    
    Args:
        fallback_value: Value to return if all retries fail
        max_retries: Maximum number of retry attempts
        backoff_factor: Factor to multiply wait time by for each attempt
        initial_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds
        exceptions_to_retry: Tuple of exception types to retry on
        
    Returns:
        Callable: Decorator function that implements retry with fallback logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions_to_retry as e:
                    attempt += 1
                    
                    if attempt > max_retries:
                        logger.error(
                            f"Maximum retries ({max_retries}) reached for {func.__name__}. "
                            f"Returning fallback value. Last error: {str(e)}"
                        )
                        return fallback_value
                    
                    wait_time = calculate_wait_time(
                        attempt, backoff_factor, initial_wait, max_wait, DEFAULT_JITTER_FACTOR
                    )
                    
                    logger.warning(
                        f"Retry attempt {attempt}/{max_retries} for {func.__name__} "
                        f"after {wait_time:.2f}s. Error: {str(e)}"
                    )
                    
                    time.sleep(wait_time)
        
        return wrapper
    
    return decorator


def retry_async_with_fallback(
    fallback_value: Any,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    initial_wait: float = DEFAULT_INITIAL_WAIT,
    max_wait: float = DEFAULT_MAX_WAIT,
    exceptions_to_retry: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator that retries an async function and returns a fallback value if all retries fail.
    
    Args:
        fallback_value: Value to return if all retries fail
        max_retries: Maximum number of retry attempts
        backoff_factor: Factor to multiply wait time by for each attempt
        initial_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds
        exceptions_to_retry: Tuple of exception types to retry on
        
    Returns:
        Callable: Decorator function that implements async retry with fallback logic
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions_to_retry as e:
                    attempt += 1
                    
                    if attempt > max_retries:
                        logger.error(
                            f"Maximum retries ({max_retries}) reached for {func.__name__}. "
                            f"Returning fallback value. Last error: {str(e)}"
                        )
                        return fallback_value
                    
                    wait_time = calculate_wait_time(
                        attempt, backoff_factor, initial_wait, max_wait, DEFAULT_JITTER_FACTOR
                    )
                    
                    logger.warning(
                        f"Retry attempt {attempt}/{max_retries} for {func.__name__} "
                        f"after {wait_time:.2f}s. Error: {str(e)}"
                    )
                    
                    await asyncio.sleep(wait_time)
        
        return wrapper
    
    return decorator