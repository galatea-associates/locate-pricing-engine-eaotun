"""
Centralized logging configuration for the Borrow Rate & Locate Fee Pricing Engine.

This module configures the Python logging system with appropriate handlers, formatters,
and log levels based on the environment. It provides structured logging capabilities
with correlation IDs, supports different log destinations (console, file, cloud services),
and implements specialized loggers for different components of the system including
audit logging for financial transactions.
"""

import os
import sys
import json
import logging
import logging.config
import logging.handlers
from datetime import datetime
from typing import Dict, Any, Optional

from .settings import get_settings

# Default logging configuration values
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_LOG_LEVEL = logging.INFO
LOG_DIRECTORY = 'logs'
AUDIT_LOG_FILE = 'audit.log'
APP_LOG_FILE = 'app.log'
ERROR_LOG_FILE = 'error.log'
MAX_BYTES = 10485760  # 10MB
BACKUP_COUNT = 10


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
        # Import here to avoid circular import
        from ..core.context import get_correlation_id
        
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = get_correlation_id() or 'NONE'
        return True


class JsonFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as JSON objects.
    
    This formatter converts log records to JSON format, making them easier
    to parse and analyze with log management tools.
    """
    
    def __init__(self):
        """Initialize the JSON formatter."""
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.
        
        Args:
            record: The log record to format
            
        Returns:
            str: JSON-formatted log entry
        """
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'correlation_id': getattr(record, 'correlation_id', 'NONE'),
            'message': record.getMessage()
        }
        
        # Add any extra attributes set on the log record
        for key, value in record.__dict__.items():
            if key not in ('args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
                          'funcName', 'id', 'levelname', 'levelno', 'lineno', 'module',
                          'msecs', 'message', 'msg', 'name', 'pathname', 'process',
                          'processName', 'relativeCreated', 'stack_info', 'thread',
                          'threadName', 'correlation_id'):
                try:
                    # Try to convert value to JSON-serializable format
                    json.dumps({key: value})
                    log_data[key] = value
                except (TypeError, OverflowError):
                    # If value is not JSON-serializable, convert to string
                    log_data[key] = str(value)
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)
    
    def formatException(self, exc_info) -> str:
        """
        Format an exception for inclusion in a log record.
        
        Args:
            exc_info: Exception information
            
        Returns:
            str: Formatted exception information
        """
        # Use the standard formatter to get exception text
        return logging.Formatter().formatException(exc_info)


def create_console_handler(log_format: str, date_format: str, log_level: int) -> logging.StreamHandler:
    """
    Create a console log handler with appropriate formatter.
    
    Args:
        log_format: Format string for log messages
        date_format: Format string for timestamps
        log_level: Logging level (e.g., logging.INFO)
        
    Returns:
        logging.StreamHandler: Configured console handler
    """
    # Create a stream handler that writes to stderr
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(log_level)
    
    # Create and set formatter
    formatter = logging.Formatter(log_format, date_format)
    handler.setFormatter(formatter)
    
    return handler


def create_file_handler(filename: str, log_format: str, date_format: str, log_level: int,
                        max_bytes: int, backup_count: int) -> logging.handlers.RotatingFileHandler:
    """
    Create a rotating file log handler with appropriate formatter.
    
    Args:
        filename: Name of the log file
        log_format: Format string for log messages
        date_format: Format string for timestamps
        log_level: Logging level (e.g., logging.INFO)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        logging.handlers.RotatingFileHandler: Configured file handler
    """
    # Create logs directory if it doesn't exist
    os.makedirs(LOG_DIRECTORY, exist_ok=True)
    
    # Create full path for log file
    log_path = os.path.join(LOG_DIRECTORY, filename)
    
    # Create a rotating file handler
    handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count
    )
    handler.setLevel(log_level)
    
    # Create and set formatter
    formatter = logging.Formatter(log_format, date_format)
    handler.setFormatter(formatter)
    
    return handler


def create_json_formatter() -> logging.Formatter:
    """
    Create a formatter that outputs logs in JSON format.
    
    Returns:
        logging.Formatter: JSON formatter
    """
    return JsonFormatter()


def configure_logging() -> None:
    """
    Configure the Python logging system based on application settings.
    
    This function sets up the entire logging system, including handlers,
    formatters, and loggers for different components of the application.
    The configuration is based on the current environment settings.
    """
    # Get settings
    settings = get_settings()
    logging_config = settings.get_logging_config()
    
    # Ensure log directory exists
    os.makedirs(LOG_DIRECTORY, exist_ok=True)
    
    # Determine log level
    log_level_name = logging_config.get('level', 'INFO')
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    
    # Determine log format and date format
    log_format = logging_config.get('format', DEFAULT_LOG_FORMAT)
    date_format = logging_config.get('date_format', DEFAULT_DATE_FORMAT)
    
    # Create logging configuration dictionary
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': log_format,
                'datefmt': date_format
            },
            'json': {
                '()': 'src.backend.config.logging_config.JsonFormatter'
            }
        },
        'filters': {
            'correlation_id': {
                '()': 'src.backend.config.logging_config.CorrelationIdFilter'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'standard',
                'filters': ['correlation_id'],
                'stream': 'ext://sys.stdout'
            },
            'app_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': log_level,
                'formatter': 'json',
                'filters': ['correlation_id'],
                'filename': os.path.join(LOG_DIRECTORY, APP_LOG_FILE),
                'maxBytes': MAX_BYTES,
                'backupCount': BACKUP_COUNT
            },
            'audit_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': logging.INFO,
                'formatter': 'json',
                'filters': ['correlation_id'],
                'filename': os.path.join(LOG_DIRECTORY, AUDIT_LOG_FILE),
                'maxBytes': MAX_BYTES,
                'backupCount': BACKUP_COUNT
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': logging.ERROR,
                'formatter': 'json',
                'filters': ['correlation_id'],
                'filename': os.path.join(LOG_DIRECTORY, ERROR_LOG_FILE),
                'maxBytes': MAX_BYTES,
                'backupCount': BACKUP_COUNT
            }
        },
        'loggers': {
            '': {  # Root logger
                'handlers': ['console', 'app_file', 'error_file'],
                'level': log_level,
                'propagate': True
            },
            'audit': {  # Specialized audit logger
                'handlers': ['console', 'audit_file'],
                'level': logging.INFO,
                'propagate': False
            },
            'calculation': {  # Logger for calculation module
                'handlers': ['console', 'app_file', 'error_file'],
                'level': log_level,
                'propagate': False
            },
            'api': {  # Logger for API module
                'handlers': ['console', 'app_file', 'error_file'],
                'level': log_level,
                'propagate': False
            },
            'data': {  # Logger for data module
                'handlers': ['console', 'app_file', 'error_file'],
                'level': log_level,
                'propagate': False
            },
            'external': {  # Logger for external API calls
                'handlers': ['console', 'app_file', 'error_file'],
                'level': log_level,
                'propagate': False
            }
        }
    }
    
    # Apply the configuration
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance for a specific component.
    
    Args:
        name: Name of the logger to retrieve or create
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)