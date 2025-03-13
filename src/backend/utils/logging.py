"""
Utility module that provides enhanced logging capabilities for the Borrow Rate & Locate Fee Pricing Engine.

This module includes decorators for logging execution time and exceptions, context managers for 
structured logging, and utility functions for setting up loggers with consistent configuration.
It serves as a bridge between application code and the core logging infrastructure, making it
easier to implement standardized logging practices across the application.
"""

import logging
import functools
import time
import typing
from typing import Callable, Dict, Any, Optional, TypeVar, cast
import contextlib
import traceback

from ..core.logging import get_logger, get_correlation_id

# Default log level for loggers
DEFAULT_LOG_LEVEL = logging.INFO

def setup_logger(name: str, level: int = None) -> logging.Logger:
    """
    Set up a configured logger with the specified name.
    
    Args:
        name: Logger name
        level: Optional log level to set (defaults to DEFAULT_LOG_LEVEL)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = get_logger(name)
    if level is not None:
        logger.setLevel(level)
    else:
        logger.setLevel(DEFAULT_LOG_LEVEL)
    return logger

def log_execution_time(logger: logging.Logger) -> Callable:
    """
    Decorator that logs the execution time of a function.
    
    Args:
        logger: Logger to use for logging
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Function {func.__name__} executed in {execution_time:.4f} seconds")
            return result
        return wrapper
    return decorator

def log_exceptions(logger: logging.Logger) -> Callable:
    """
    Decorator that logs exceptions raised by a function.
    
    Args:
        logger: Logger to use for logging
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Get traceback info
                tb = traceback.format_exc()
                logger.error(f"Exception in {func.__name__}: {str(e)}\n{tb}")
                raise  # Re-raise the exception
        return wrapper
    return decorator

def log_api_call(logger: logging.Logger, service_name: str) -> Callable:
    """
    Decorator that logs external API calls with timing information.
    
    Args:
        logger: Logger to use for logging
        service_name: Name of the external service being called
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Try to extract the endpoint from args or kwargs
            endpoint = "unknown"
            if len(args) > 0 and isinstance(args[0], str):
                endpoint = args[0]
            elif "endpoint" in kwargs:
                endpoint = kwargs["endpoint"]
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(
                    f"API call to {service_name} endpoint '{endpoint}' completed in {execution_time:.4f} seconds",
                    extra={"service": service_name, "endpoint": endpoint, "duration": execution_time}
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"API call to {service_name} endpoint '{endpoint}' failed after {execution_time:.4f} seconds: {str(e)}",
                    extra={"service": service_name, "endpoint": endpoint, "duration": execution_time, "error": str(e)}
                )
                raise  # Re-raise the exception
        return wrapper
    return decorator

def log_fallback_usage(
    logger: logging.Logger, 
    service_name: str, 
    fallback_type: str, 
    context: Dict[str, Any] = None
) -> None:
    """
    Log when a fallback mechanism is used due to external API failure.
    
    Args:
        logger: Logger to use for logging
        service_name: Name of the service that failed
        fallback_type: Type of fallback mechanism used
        context: Additional context for the fallback
    """
    correlation_id = get_correlation_id()
    log_data = {
        "service_name": service_name,
        "fallback_type": fallback_type,
        "correlation_id": correlation_id
    }
    
    if context:
        log_data["context"] = context
    
    logger.warning(
        f"Using fallback mechanism for {service_name} - Type: {fallback_type}",
        extra=log_data
    )

def log_calculation(
    logger: logging.Logger,
    ticker: str,
    position_value: float,
    loan_days: int,
    client_id: str,
    borrow_rate: float,
    total_fee: float,
    breakdown: Dict[str, Any],
    data_sources: Dict[str, Any]
) -> None:
    """
    Log a fee calculation for audit purposes.
    
    Args:
        logger: Logger to use for logging
        ticker: Stock symbol
        position_value: Position value in USD
        loan_days: Loan duration in days
        client_id: Client identifier
        borrow_rate: Applied borrow rate
        total_fee: Total calculated fee
        breakdown: Detailed fee breakdown
        data_sources: Sources of data used in calculation
    """
    correlation_id = get_correlation_id()
    
    log_data = {
        "ticker": ticker,
        "position_value": position_value,
        "loan_days": loan_days,
        "client_id": client_id,
        "borrow_rate": borrow_rate,
        "total_fee": total_fee,
        "breakdown": breakdown,
        "data_sources": data_sources,
        "correlation_id": correlation_id
    }
    
    logger.info(
        f"Fee calculation for {ticker} - Client: {client_id} - Rate: {borrow_rate} - Fee: {total_fee}",
        extra=log_data
    )

class LoggingContext:
    """
    Context manager for adding additional context to log records.
    """
    
    def __init__(self, logger: logging.Logger, extra: Dict[str, Any]):
        """
        Initialize the logging context.
        
        Args:
            logger: Logger to enhance with context
            extra: Extra context to add to log records
        """
        self.logger = logger
        self.extra = extra
        self.original_extra = None
    
    def __enter__(self):
        """
        Enter the context and add extra context to the logger.
        
        Returns:
            LoggingContext: Self reference for context manager
        """
        if hasattr(self.logger, 'extra'):
            self.original_extra = self.logger.extra.copy()
            self.logger.extra.update(self.extra)
        else:
            setattr(self.logger, 'extra', self.extra)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context and restore original logger context.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
            
        Returns:
            None: Context manager cleanup
        """
        if self.original_extra is not None:
            self.logger.extra = self.original_extra
        elif hasattr(self.logger, 'extra'):
            delattr(self.logger, 'extra')
        # Don't suppress exceptions
        return False

class PerformanceTimer:
    """
    Context manager for timing and logging the execution of code blocks.
    """
    
    def __init__(self, logger: logging.Logger, operation: str, extra: Dict[str, Any] = None):
        """
        Initialize the performance timer.
        
        Args:
            logger: Logger to use for logging
            operation: Name of the operation being timed
            extra: Additional context to include in logs
        """
        self.logger = logger
        self.operation = operation
        self.start_time = None
        self.extra = extra or {}
    
    def __enter__(self):
        """
        Enter the context and start the timer.
        
        Returns:
            PerformanceTimer: Self reference for context manager
        """
        self.start_time = time.time()
        self.logger.info(f"Starting operation: {self.operation}", extra=self.extra)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context, stop the timer, and log the duration.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
            
        Returns:
            None: Context manager cleanup
        """
        elapsed_time = time.time() - self.start_time
        
        if exc_type is not None:
            # An exception occurred
            self.logger.error(
                f"Operation {self.operation} failed after {elapsed_time:.4f} seconds: {str(exc_val)}",
                extra={**self.extra, "duration": elapsed_time, "error": str(exc_val)}
            )
        else:
            # Operation completed successfully
            self.logger.info(
                f"Operation {self.operation} completed in {elapsed_time:.4f} seconds",
                extra={**self.extra, "duration": elapsed_time}
            )
        
        # Don't suppress exceptions
        return False