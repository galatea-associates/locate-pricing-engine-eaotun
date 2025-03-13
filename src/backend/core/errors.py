"""
Error handling utilities for the Borrow Rate & Locate Fee Pricing Engine.

This module provides standardized error handling functions and error response formatting
to ensure consistent error responses across the application. It centralizes error message
formatting, HTTP status code mapping, and error response creation.
"""

from typing import Dict, Any, Optional
from fastapi import status

from ..core.constants import ErrorCodes


# Map error codes to HTTP status codes
ERROR_CODE_TO_HTTP_STATUS: Dict[ErrorCodes, int] = {
    ErrorCodes.INVALID_PARAMETER: status.HTTP_400_BAD_REQUEST,
    ErrorCodes.UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
    ErrorCodes.TICKER_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCodes.CLIENT_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCodes.RATE_LIMIT_EXCEEDED: status.HTTP_429_TOO_MANY_REQUESTS,
    ErrorCodes.CALCULATION_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCodes.EXTERNAL_API_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE
}

# Error message templates
ERROR_MESSAGES: Dict[ErrorCodes, str] = {
    ErrorCodes.INVALID_PARAMETER: 'Invalid parameter: {param}',
    ErrorCodes.UNAUTHORIZED: 'Authentication failed',
    ErrorCodes.TICKER_NOT_FOUND: 'Ticker not found: {ticker}',
    ErrorCodes.CLIENT_NOT_FOUND: 'Client not found: {client_id}',
    ErrorCodes.RATE_LIMIT_EXCEEDED: 'Rate limit exceeded. Try again in {retry_after} seconds',
    ErrorCodes.CALCULATION_ERROR: 'Error during calculation: {detail}',
    ErrorCodes.EXTERNAL_API_UNAVAILABLE: 'External service unavailable: {service}'
}


def get_error_message(error_code: ErrorCodes, params: Optional[Dict[str, Any]] = None) -> str:
    """
    Format an error message by substituting parameters into a template.
    
    Args:
        error_code: The error code to get the message template for
        params: Optional dictionary of parameters to substitute into the template
        
    Returns:
        Formatted error message with parameters substituted
    """
    message_template = ERROR_MESSAGES.get(error_code)
    if not params:
        return message_template
    
    try:
        return message_template.format(**params)
    except KeyError as e:
        # Fall back to unformatted template if required parameter is missing
        return f"{message_template} (Missing format parameter: {e})"


def get_http_status_code(error_code: ErrorCodes) -> int:
    """
    Map an error code to its corresponding HTTP status code.
    
    Args:
        error_code: The error code to map to an HTTP status code
        
    Returns:
        HTTP status code as an integer
    """
    return ERROR_CODE_TO_HTTP_STATUS.get(
        error_code, 
        status.HTTP_500_INTERNAL_SERVER_ERROR  # Default to 500 if mapping not found
    )


def create_error_response(message: str, error_code: ErrorCodes, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a standardized error response dictionary.
    
    Args:
        message: The error message to include in the response
        error_code: The error code to include in the response
        details: Optional dictionary of additional details to include
        
    Returns:
        Standardized error response dictionary with status, error message, 
        error code and optional details
    """
    response = {
        "status": "error",
        "error": message,
        "error_code": error_code.value
    }
    
    if details:
        response["details"] = details
        
    return response