"""
Utility functions for the Borrow Rate & Locate Fee Pricing Engine API.

This module provides common helper functions used across API endpoints for request
processing, response formatting, parameter validation, and error handling.
"""

import re
from typing import Dict, Any, Optional, Union

from fastapi import HTTPException, status, Request, Response
# fastapi 0.103.0+

from ..core.errors import create_error_response, get_error_message, get_http_status_code
from ..core.constants import ErrorCodes
from ..utils.logging import setup_logger

# Set up module logger
logger = setup_logger('api.utils')

# Regex pattern for ticker symbol validation
TICKER_PATTERN = re.compile(r'^[A-Z0-9]{1,10}$')


def validate_ticker_format(ticker: str) -> bool:
    """
    Validates the format of a ticker symbol.
    
    Args:
        ticker: Ticker symbol to validate
        
    Returns:
        bool: True if ticker format is valid, False otherwise
    """
    if ticker is None or ticker == "":
        return False
    
    return bool(TICKER_PATTERN.match(ticker))


def extract_api_key(request: Request) -> Optional[str]:
    """
    Extracts API key from request headers or query parameters.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Optional[str]: API key if found, None otherwise
    """
    # Try to get API key from header
    api_key = request.headers.get("X-API-Key")
    
    # If not in header, try to get from query parameters
    if not api_key and "api_key" in request.query_params:
        api_key = request.query_params["api_key"]
    
    return api_key


def set_rate_limit_headers(response: Response, limit: int, remaining: int, reset: int) -> None:
    """
    Sets rate limit headers in the response.
    
    Args:
        response: FastAPI Response object
        limit: Maximum requests allowed in the time window
        remaining: Remaining requests in the current time window
        reset: Seconds until the rate limit resets
        
    Returns:
        None
    """
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset)


def parse_query_params(request: Request) -> Dict[str, Any]:
    """
    Parses and validates query parameters for calculate endpoint.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Dict[str, Any]: Dictionary of validated parameters
        
    Raises:
        HTTPException: If any parameter is invalid
    """
    params = dict(request.query_params)
    
    # Extract and validate ticker
    ticker = params.get("ticker")
    if not ticker or not validate_ticker_format(ticker):
        error_msg = get_error_message(
            ErrorCodes.INVALID_PARAMETER, 
            {"param": "'ticker' must be a valid stock symbol"}
        )
        error_response = create_error_response(
            error_msg,
            ErrorCodes.INVALID_PARAMETER,
            {"valid_params": ["ticker", "position_value>0", "loan_days>0", "client_id"]}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response
        )
    
    # Extract and validate position_value
    position_value_str = params.get("position_value")
    try:
        position_value = float(position_value_str) if position_value_str else None
        if position_value is None or position_value <= 0:
            raise ValueError("Position value must be positive")
    except ValueError:
        error_msg = get_error_message(
            ErrorCodes.INVALID_PARAMETER, 
            {"param": "'position_value' must be a positive number"}
        )
        error_response = create_error_response(
            error_msg,
            ErrorCodes.INVALID_PARAMETER,
            {"valid_params": ["ticker", "position_value>0", "loan_days>0", "client_id"]}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response
        )
    
    # Extract and validate loan_days
    loan_days_str = params.get("loan_days")
    try:
        loan_days = int(loan_days_str) if loan_days_str else None
        if loan_days is None or loan_days <= 0:
            raise ValueError("Loan days must be positive")
    except ValueError:
        error_msg = get_error_message(
            ErrorCodes.INVALID_PARAMETER, 
            {"param": "'loan_days' must be a positive integer"}
        )
        error_response = create_error_response(
            error_msg,
            ErrorCodes.INVALID_PARAMETER,
            {"valid_params": ["ticker", "position_value>0", "loan_days>0", "client_id"]}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response
        )
    
    # Extract client_id
    client_id = params.get("client_id")
    if not client_id:
        error_msg = get_error_message(
            ErrorCodes.INVALID_PARAMETER, 
            {"param": "'client_id' is required"}
        )
        error_response = create_error_response(
            error_msg,
            ErrorCodes.INVALID_PARAMETER,
            {"valid_params": ["ticker", "position_value>0", "loan_days>0", "client_id"]}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response
        )
    
    # Return validated parameters
    return {
        "ticker": ticker.upper(),
        "position_value": position_value,
        "loan_days": loan_days,
        "client_id": client_id
    }


def create_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a standardized success response.
    
    Args:
        data: Response data to include
        
    Returns:
        Dict[str, Any]: Success response with status and data
    """
    response = {"status": "success"}
    response.update(data)
    return response


def handle_calculation_error(exc: Exception) -> HTTPException:
    """
    Handles calculation errors and returns appropriate HTTP exception.
    
    Args:
        exc: Exception that occurred during calculation
        
    Returns:
        HTTPException: HTTP exception with appropriate status code and details
    """
    logger.error(f"Calculation error: {str(exc)}", exc_info=True)
    
    # Determine error code based on exception type
    if isinstance(exc, ValueError) and "ticker" in str(exc).lower():
        error_code = ErrorCodes.TICKER_NOT_FOUND
        params = {"ticker": str(exc).split(":")[-1].strip()}
    elif isinstance(exc, ValueError) and "client" in str(exc).lower():
        error_code = ErrorCodes.CLIENT_NOT_FOUND
        params = {"client_id": str(exc).split(":")[-1].strip()}
    else:
        error_code = ErrorCodes.CALCULATION_ERROR
        params = {"detail": str(exc)}
    
    # Get appropriate error message and HTTP status code
    error_msg = get_error_message(error_code, params)
    status_code = get_http_status_code(error_code)
    
    # Create error response
    error_response = create_error_response(error_msg, error_code)
    
    # Return HTTP exception
    return HTTPException(status_code=status_code, detail=error_response)


def log_api_request(request: Request, params: Dict[str, Any]) -> None:
    """
    Logs API request details for auditing and debugging.
    
    Args:
        request: FastAPI Request object
        params: Request parameters
        
    Returns:
        None
    """
    # Get client IP address
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    # Log request details
    method = request.method
    url = str(request.url)
    
    # Make a copy of params to avoid modifying the original
    log_params = params.copy()
    
    # Mask sensitive data if present
    if "api_key" in log_params:
        log_params["api_key"] = "***"
    
    logger.info(
        f"API Request: {method} {url} from {client_ip}",
        extra={
            "method": method,
            "url": url,
            "client_ip": client_ip,
            "params": log_params
        }
    )


def log_api_response(request: Request, response: Dict[str, Any], duration: float) -> None:
    """
    Logs API response details for auditing and debugging.
    
    Args:
        request: FastAPI Request object
        response: Response data
        duration: Request processing duration in seconds
        
    Returns:
        None
    """
    method = request.method
    url = str(request.url)
    status = response.get("status", "unknown")
    
    log_data = {
        "method": method,
        "url": url,
        "status": status,
        "duration_ms": round(duration * 1000, 2)
    }
    
    if status == "error":
        log_data["error"] = response.get("error")
        log_data["error_code"] = response.get("error_code")
        logger.warning(
            f"API Response: {method} {url} - Status: {status} - Error: {log_data['error']} - Duration: {log_data['duration_ms']}ms",
            extra=log_data
        )
    else:
        logger.info(
            f"API Response: {method} {url} - Status: {status} - Duration: {log_data['duration_ms']}ms",
            extra=log_data
        )