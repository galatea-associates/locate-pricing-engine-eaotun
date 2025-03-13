"""
Core logging module that provides centralized logging functionality for the Borrow Rate & Locate Fee Pricing Engine.

This module implements correlation ID management, structured logging, and specialized loggers 
for different components including API requests, calculations, and audit trails. It serves as 
the foundation for the application's comprehensive logging strategy, ensuring consistent 
log formats and proper context across all system components.
"""

import logging
import contextvars
import uuid
import typing
import json
import datetime
from typing import Dict, Any, Optional

from ..config.settings import get_settings
from ..config.logging_config import configure_logging

# Context variable for correlation ID
correlation_id_var = contextvars.ContextVar('correlation_id', default=None)

# Logger name constants
LOGGER_NAMES = {
    "api": "api",
    "calculation": "calculation",
    "data": "data",
    "cache": "cache",
    "audit": "audit",
    "external": "external"
}


def init_logging() -> None:
    """
    Initialize the logging system for the application.
    
    This function sets up the Python logging system with appropriate handlers,
    formatters, and log levels based on the application configuration.
    """
    configure_logging()


def get_correlation_id() -> str:
    """
    Get the current correlation ID from context.
    
    If no correlation ID exists in the current context, a new one is generated.
    
    Returns:
        str: Current correlation ID or a new one if none exists
    """
    correlation_id = correlation_id_var.get()
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
        correlation_id_var.set(correlation_id)
    return correlation_id


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID in the current context.
    
    Args:
        correlation_id: Correlation ID to set
    """
    correlation_id_var.set(correlation_id)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for a specific component.
    
    Args:
        name: Name of the logger
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


def get_api_logger() -> logging.Logger:
    """
    Get the specialized API logger.
    
    Returns:
        logging.Logger: API logger instance
    """
    return get_logger(LOGGER_NAMES["api"])


def get_calculation_logger() -> logging.Logger:
    """
    Get the specialized calculation logger.
    
    Returns:
        logging.Logger: Calculation logger instance
    """
    return get_logger(LOGGER_NAMES["calculation"])


def get_data_logger() -> logging.Logger:
    """
    Get the specialized data service logger.
    
    Returns:
        logging.Logger: Data service logger instance
    """
    return get_logger(LOGGER_NAMES["data"])


def get_cache_logger() -> logging.Logger:
    """
    Get the specialized cache service logger.
    
    Returns:
        logging.Logger: Cache service logger instance
    """
    return get_logger(LOGGER_NAMES["cache"])


def get_audit_logger() -> logging.Logger:
    """
    Get the specialized audit logger.
    
    Returns:
        logging.Logger: Audit logger instance
    """
    return get_logger(LOGGER_NAMES["audit"])


def get_external_logger() -> logging.Logger:
    """
    Get the specialized external API logger.
    
    Returns:
        logging.Logger: External API logger instance
    """
    return get_logger(LOGGER_NAMES["external"])


class CorrelationIdFilter(logging.Filter):
    """
    Log filter that adds correlation ID to all log records.
    
    This filter ensures that each log record has a correlation_id attribute,
    which helps in tracing related log entries across different components.
    """
    
    def __init__(self):
        """Initialize the correlation ID filter."""
        super().__init__()
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add correlation ID to the log record if not present.
        
        Args:
            record: The log record to process
            
        Returns:
            bool: Always True to include the record
        """
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = get_correlation_id()
        return True


class StructuredLogAdapter(logging.LoggerAdapter):
    """
    Adapter that adds structured logging capabilities to standard loggers.
    
    This adapter ensures that all logs include the correlation ID and can
    easily include structured data in a consistent format.
    """
    
    def __init__(self, logger: logging.Logger, extra: Dict[str, Any] = None):
        """
        Initialize the structured log adapter.
        
        Args:
            logger: The logger to adapt
            extra: Extra context to include in all logs
        """
        super().__init__(logger, extra or {})
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """
        Process the log message and add structured context.
        
        Args:
            msg: The log message
            kwargs: Additional logging parameters
            
        Returns:
            tuple: (msg, kwargs) with enhanced context
        """
        # Ensure extra dict exists
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        # Add correlation ID if not present
        if 'correlation_id' not in kwargs['extra']:
            kwargs['extra']['correlation_id'] = get_correlation_id()
            
        # Add any extra context from adapter initialization
        for key, value in self.extra.items():
            if key not in kwargs['extra']:
                kwargs['extra'][key] = value
        
        return msg, kwargs
    
    def structured(self, level: int, msg: str, data: Dict[str, Any] = None) -> None:
        """
        Log a message with structured data.
        
        Args:
            level: Log level (e.g., logging.INFO)
            msg: The log message
            data: Structured data to include in the log
        """
        if data is not None:
            self.log(level, msg, extra=data)
        else:
            self.log(level, msg)


def log_api_request(logger: logging.Logger, method: str, path: str, 
                   params: Dict[str, Any], client_id: str,
                   correlation_id: str) -> None:
    """
    Log an incoming API request with context.
    
    Args:
        logger: Logger to use
        method: HTTP method (GET, POST, etc.)
        path: Request path
        params: Request parameters
        client_id: Client identifier
        correlation_id: Correlation ID for request tracing
    """
    set_correlation_id(correlation_id)
    
    log_data = {
        "method": method,
        "path": path,
        "params": params,
        "client_id": client_id,
        "correlation_id": correlation_id
    }
    
    logger.info(f"API Request: {method} {path}", extra=log_data)


def log_api_response(logger: logging.Logger, method: str, path: str, 
                    status_code: int, duration: float,
                    correlation_id: str) -> None:
    """
    Log an API response with timing information.
    
    Args:
        logger: Logger to use
        method: HTTP method (GET, POST, etc.)
        path: Request path
        status_code: HTTP status code
        duration: Request duration in seconds
        correlation_id: Correlation ID for request tracing
    """
    set_correlation_id(correlation_id)
    
    log_data = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration * 1000, 2),
        "correlation_id": correlation_id
    }
    
    logger.info(f"API Response: {method} {path} - Status: {status_code} - Duration: {log_data['duration_ms']}ms", 
                extra=log_data)


def log_error(logger: logging.Logger, error: Exception, message: str, 
             context: Dict[str, Any] = None) -> None:
    """
    Log an error with context information.
    
    Args:
        logger: Logger to use
        error: Exception that occurred
        message: Error message
        context: Additional context for the error
    """
    correlation_id = get_correlation_id()
    
    log_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "correlation_id": correlation_id
    }
    
    if context:
        log_data["context"] = context
    
    logger.error(f"{message}: {log_data['error_type']} - {log_data['error_message']}", 
                 exc_info=True, extra=log_data)


def log_calculation(logger: logging.Logger, ticker: str, position_value: float,
                   loan_days: int, client_id: str, borrow_rate: float,
                   total_fee: float, breakdown: Dict[str, Any],
                   data_sources: Dict[str, Any]) -> None:
    """
    Log a fee calculation for audit purposes.
    
    Args:
        logger: Logger to use
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
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "correlation_id": correlation_id
    }
    
    logger.info(f"Fee calculation for {ticker} - Client: {client_id} - Rate: {borrow_rate} - Fee: {total_fee}", 
                extra=log_data)


def log_fallback_usage(logger: logging.Logger, service_name: str, 
                      fallback_type: str, context: Dict[str, Any] = None) -> None:
    """
    Log when a fallback mechanism is used due to external API failure.
    
    Args:
        logger: Logger to use
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
    
    logger.warning(f"Using fallback mechanism for {service_name} - Type: {fallback_type}", 
                   extra=log_data)


def log_external_api_call(logger: logging.Logger, service_name: str, 
                         endpoint: str, method: str, duration: float,
                         success: bool, context: Dict[str, Any] = None) -> None:
    """
    Log an external API call with timing information.
    
    Args:
        logger: Logger to use
        service_name: Name of the external service
        endpoint: API endpoint called
        method: HTTP method used
        duration: Call duration in seconds
        success: Whether the call was successful
        context: Additional context for the API call
    """
    correlation_id = get_correlation_id()
    
    log_data = {
        "service_name": service_name,
        "endpoint": endpoint,
        "method": method,
        "duration_ms": round(duration * 1000, 2),
        "success": success,
        "correlation_id": correlation_id
    }
    
    if context:
        log_data["context"] = context
    
    log_message = f"External API call to {service_name} - Endpoint: {endpoint} - Success: {success} - Duration: {log_data['duration_ms']}ms"
    
    if success:
        logger.info(log_message, extra=log_data)
    else:
        logger.error(log_message, extra=log_data)