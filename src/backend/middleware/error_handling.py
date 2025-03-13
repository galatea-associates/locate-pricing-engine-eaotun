"""
Error handling middleware for the Borrow Rate & Locate Fee Pricing Engine API.

This middleware intercepts exceptions raised during request processing, converts them
into standardized error responses, and ensures proper logging of all errors. It provides
consistent error handling across the application, improving client experience and system reliability.
"""

from fastapi import Request, Response, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from typing import Callable, Dict, List, Any, Optional
import traceback
from pydantic import ValidationError

from ..core.exceptions import (
    BaseAPIException, ValidationException, AuthenticationException,
    TickerNotFoundException, ClientNotFoundException, RateLimitExceededException,
    CalculationException, ExternalAPIException
)
from ..core.constants import ErrorCodes
from ..core.errors import (
    get_error_message, get_http_status_code, create_error_response
)
from ..core.logging import (
    get_api_logger, log_error, get_correlation_id
)
from ..schemas.error import ErrorResponse, ValidationError as ValidationErrorSchema

# Get API logger instance
logger = get_api_logger()


def format_validation_errors(errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Formats validation errors from Pydantic or FastAPI into a standardized format.
    
    Args:
        errors: List of validation error dictionaries
        
    Returns:
        List of formatted validation errors
    """
    formatted_errors = []
    
    for error in errors:
        # Extract field name, location, and error message
        field = error.get("loc", ["unknown"])[-1]
        location = "body"
        if len(error.get("loc", [])) > 1:
            location = error.get("loc", ["unknown"])[0]
        
        message = error.get("msg", "Unknown validation error")
        
        # Create standardized error format
        formatted_error = {
            "field": field,
            "location": location,
            "message": message
        }
        
        formatted_errors.append(formatted_error)
    
    return formatted_errors


def get_request_details(request: Request) -> Dict[str, Any]:
    """
    Extracts relevant details from the request for error logging.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Dictionary containing request details
    """
    # Extract basic information
    method = request.method
    url = str(request.url)
    client_ip = request.client.host if request.client else "unknown"
    
    # Extract client ID if available
    client_id = "unknown"
    if hasattr(request.state, "client_id"):
        client_id = request.state.client_id
    
    # Get correlation ID
    correlation_id = get_correlation_id()
    
    return {
        "method": method,
        "url": url,
        "client_ip": client_ip,
        "client_id": client_id,
        "correlation_id": correlation_id
    }


class ErrorHandlingMiddleware:
    """
    Middleware for handling exceptions and converting them to standardized error responses.
    
    This middleware intercepts exceptions raised during request processing and converts
    them into appropriate HTTP responses with standardized JSON error bodies. It also
    ensures all errors are properly logged with context information.
    """
    
    def __init__(self):
        """Initialize the error handling middleware."""
        logger.info("ErrorHandlingMiddleware initialized")
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request through the error handling middleware.
        
        Args:
            request: FastAPI Request object
            call_next: Next middleware or endpoint handler
            
        Returns:
            Response: HTTP response
        """
        try:
            # Try to process the request
            return await call_next(request)
        
        except BaseAPIException as exc:
            # Handle application-specific exceptions
            return self.handle_api_exception(exc, request)
        
        except RequestValidationError as exc:
            # Handle FastAPI request validation errors
            return self.handle_validation_error(exc, request)
        
        except ValidationError as exc:
            # Handle Pydantic validation errors
            return self.handle_pydantic_error(exc, request)
        
        except HTTPException as exc:
            # Handle FastAPI HTTP exceptions
            return self.handle_http_exception(exc, request)
        
        except Exception as exc:
            # Handle unexpected exceptions
            return self.handle_unexpected_error(exc, request)
    
    def handle_api_exception(self, exc: BaseAPIException, request: Request) -> Response:
        """
        Handle exceptions derived from BaseAPIException.
        
        Args:
            exc: The exception that was raised
            request: FastAPI Request object
            
        Returns:
            JSONResponse with appropriate error details
        """
        # Get HTTP status code based on error code
        status_code = get_http_status_code(exc.error_code)
        
        # Create error response
        error_response = create_error_response(
            message=exc.message,
            error_code=exc.error_code,
            details=exc.params
        )
        
        # Log the error
        request_details = get_request_details(request)
        log_error(
            logger=logger,
            error=exc,
            message=f"API Exception: {exc.error_code.value}",
            context={
                "request": request_details,
                "error_details": exc.params
            }
        )
        
        # Return JSON response
        return JSONResponse(
            status_code=status_code,
            content=error_response
        )
    
    def handle_validation_error(self, exc: RequestValidationError, request: Request) -> Response:
        """
        Handle FastAPI request validation errors.
        
        Args:
            exc: The validation error
            request: FastAPI Request object
            
        Returns:
            JSONResponse with validation error details
        """
        # Format validation errors
        formatted_errors = format_validation_errors(exc.errors())
        
        # Determine the parameter that had the first error
        param = formatted_errors[0]["field"] if formatted_errors else "unknown"
        
        # Create error message
        error_message = f"Invalid parameter: '{param}'"
        
        # Create validation error response
        error_response = {
            "status": "error",
            "error": error_message,
            "error_code": ErrorCodes.INVALID_PARAMETER.value,
            "validation_errors": formatted_errors,
            "valid_params": ["ticker", "position_value>0", "loan_days>0", "client_id"]
        }
        
        # Log the validation error
        request_details = get_request_details(request)
        log_error(
            logger=logger,
            error=exc,
            message=f"Validation Error: {error_message}",
            context={
                "request": request_details,
                "validation_errors": formatted_errors
            }
        )
        
        # Return JSON response
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response
        )
    
    def handle_pydantic_error(self, exc: ValidationError, request: Request) -> Response:
        """
        Handle Pydantic validation errors.
        
        Args:
            exc: The validation error
            request: FastAPI Request object
            
        Returns:
            JSONResponse with validation error details
        """
        # Format validation errors
        formatted_errors = format_validation_errors(exc.errors())
        
        # Determine the parameter that had the first error
        param = formatted_errors[0]["field"] if formatted_errors else "unknown"
        
        # Create error message
        error_message = f"Invalid parameter: '{param}'"
        
        # Create validation error response
        error_response = {
            "status": "error",
            "error": error_message,
            "error_code": ErrorCodes.INVALID_PARAMETER.value,
            "validation_errors": formatted_errors,
            "valid_params": ["ticker", "position_value>0", "loan_days>0", "client_id"]
        }
        
        # Log the validation error
        request_details = get_request_details(request)
        log_error(
            logger=logger,
            error=exc,
            message=f"Pydantic Validation Error: {error_message}",
            context={
                "request": request_details,
                "validation_errors": formatted_errors
            }
        )
        
        # Return JSON response
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response
        )
    
    def handle_http_exception(self, exc: HTTPException, request: Request) -> Response:
        """
        Handle FastAPI HTTPException.
        
        Args:
            exc: The HTTP exception
            request: FastAPI Request object
            
        Returns:
            JSONResponse with error details
        """
        # Create error response
        error_response = {
            "status": "error",
            "error": exc.detail,
            "error_code": ErrorCodes.CALCULATION_ERROR.value
        }
        
        # Log the HTTP exception
        request_details = get_request_details(request)
        log_error(
            logger=logger,
            error=exc,
            message=f"HTTP Exception: {exc.status_code}",
            context={
                "request": request_details,
                "status_code": exc.status_code,
                "detail": exc.detail
            }
        )
        
        # Return JSON response
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response
        )
    
    def handle_unexpected_error(self, exc: Exception, request: Request) -> Response:
        """
        Handle unexpected exceptions not covered by other handlers.
        
        Args:
            exc: The unexpected exception
            request: FastAPI Request object
            
        Returns:
            JSONResponse with generic error details
        """
        # Capture traceback for logging
        tb = traceback.format_exc()
        
        # Create generic error message (don't expose internal details to client)
        error_message = "An unexpected error occurred while processing your request"
        
        # Create error response
        error_response = create_error_response(
            message=error_message,
            error_code=ErrorCodes.CALCULATION_ERROR,
            details=None  # Don't include internal details in the response
        )
        
        # Log the unexpected error with full traceback
        request_details = get_request_details(request)
        log_error(
            logger=logger,
            error=exc,
            message=f"Unexpected Error: {type(exc).__name__}",
            context={
                "request": request_details,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback": tb
            }
        )
        
        # Return JSON response
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        )