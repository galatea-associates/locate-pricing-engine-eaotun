"""
Custom exception classes for the Borrow Rate & Locate Fee Pricing Engine.

This module defines a hierarchy of exception classes that provide standardized 
error handling throughout the application, ensuring consistent error responses 
and proper error classification.
"""

from typing import Dict, Any, Optional
from .constants import ErrorCodes


class BaseAPIException(Exception):
    """Base exception class for all API-related exceptions in the application."""

    def __init__(
        self, 
        message: str, 
        error_code: ErrorCodes, 
        params: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the base API exception with message, error code, and parameters.
        
        Args:
            message: Human-readable description of the error
            error_code: Standardized error code from ErrorCodes enum
            params: Additional error-specific parameters for context
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.params = params or {}

    def __str__(self) -> str:
        """String representation of the exception."""
        return self.message


class ValidationException(BaseAPIException):
    """Exception raised when input validation fails."""

    def __init__(self, message: str, params: Optional[Dict[str, Any]] = None):
        """
        Initialize a validation exception.
        
        Args:
            message: Description of the validation error
            params: Additional parameters like validation rules or permitted values
        """
        super().__init__(message, ErrorCodes.INVALID_PARAMETER, params)


class AuthenticationException(BaseAPIException):
    """Exception raised when authentication fails."""

    def __init__(self, message: str, params: Optional[Dict[str, Any]] = None):
        """
        Initialize an authentication exception.
        
        Args:
            message: Description of the authentication error
            params: Additional authentication context (e.g., client ID)
        """
        super().__init__(message, ErrorCodes.UNAUTHORIZED, params)


class TickerNotFoundException(BaseAPIException):
    """Exception raised when a requested ticker is not found."""

    def __init__(self, ticker: str):
        """
        Initialize a ticker not found exception.
        
        Args:
            ticker: The stock symbol that was not found
        """
        message = f"Ticker symbol '{ticker}' not found"
        params = {"ticker": ticker}
        super().__init__(message, ErrorCodes.TICKER_NOT_FOUND, params)


class ClientNotFoundException(BaseAPIException):
    """Exception raised when a requested client is not found."""

    def __init__(self, client_id: str):
        """
        Initialize a client not found exception.
        
        Args:
            client_id: The client identifier that was not found
        """
        message = f"Client ID '{client_id}' not found"
        params = {"client_id": client_id}
        super().__init__(message, ErrorCodes.CLIENT_NOT_FOUND, params)


class RateLimitExceededException(BaseAPIException):
    """Exception raised when a client exceeds their API rate limit."""

    def __init__(self, client_id: str, retry_after: int):
        """
        Initialize a rate limit exceeded exception.
        
        Args:
            client_id: The client identifier that exceeded their rate limit
            retry_after: Number of seconds until the rate limit resets
        """
        message = f"Rate limit exceeded for client '{client_id}'"
        params = {"client_id": client_id, "retry_after": retry_after}
        super().__init__(message, ErrorCodes.RATE_LIMIT_EXCEEDED, params)


class CalculationException(BaseAPIException):
    """Exception raised when a calculation error occurs."""

    def __init__(self, message: str, params: Optional[Dict[str, Any]] = None):
        """
        Initialize a calculation exception.
        
        Args:
            message: Description of the calculation error
            params: Additional calculation context (e.g., input values)
        """
        super().__init__(message, ErrorCodes.CALCULATION_ERROR, params)


class ExternalAPIException(BaseAPIException):
    """Exception raised when an external API call fails."""

    def __init__(self, service: str, detail: Optional[str] = None):
        """
        Initialize an external API exception.
        
        Args:
            service: The name of the external service that failed
            detail: Optional additional error details
        """
        message = f"External service '{service}' is unavailable"
        if detail:
            message += f": {detail}"
        
        params = {"service": service}
        if detail:
            params["detail"] = detail
            
        super().__init__(message, ErrorCodes.EXTERNAL_API_UNAVAILABLE, params)