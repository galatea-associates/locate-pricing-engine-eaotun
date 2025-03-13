"""
Defines Pydantic models for standardized error responses in the Borrow Rate & Locate Fee Pricing Engine.

This module provides consistent error response formatting across all API endpoints,
ensuring clear communication of error conditions to clients.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field  # pydantic v2.4.0+

from ..core.constants import ErrorCodes


class ErrorResponse(BaseModel):
    """
    Standardized error response model for API errors.
    
    Provides a consistent structure for all API error responses, including
    the error message, error code, and optional additional details.
    """
    status: str = Field(
        "error",
        description="Response status indicating an error occurred"
    )
    error: str = Field(
        ...,
        description="Human-readable error message describing the issue"
    )
    error_code: str = Field(
        ...,
        description="Machine-readable error code for programmatic handling",
        examples=[
            ErrorCodes.TICKER_NOT_FOUND.value,
            ErrorCodes.EXTERNAL_API_UNAVAILABLE.value,
            ErrorCodes.CALCULATION_ERROR.value
        ]
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional additional error details for debugging or context"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "error",
                "error": "Ticker not found: INVALID",
                "error_code": ErrorCodes.TICKER_NOT_FOUND.value,
                "details": {
                    "requested_ticker": "INVALID",
                    "timestamp": "2023-10-15T14:30:22Z"
                }
            }
        }
    }


class ValidationError(BaseModel):
    """
    Specialized error response model for validation errors.
    
    Extends the standard error response with specific fields for validation errors,
    including a list of validation issues and valid parameter formats.
    """
    status: str = Field(
        "error",
        description="Response status indicating a validation error occurred"
    )
    error: str = Field(
        ...,
        description="Human-readable error message describing the validation issue"
    )
    error_code: str = Field(
        ErrorCodes.INVALID_PARAMETER.value,
        description="Error code indicating a validation failure"
    )
    validation_errors: List[Dict[str, Any]] = Field(
        ...,
        description="List of specific validation errors with details about each failed field"
    )
    valid_params: List[str] = Field(
        ...,
        description="List of valid parameter formats to guide the client on correct submission"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "error",
                "error": "Invalid parameter: position_value",
                "error_code": ErrorCodes.INVALID_PARAMETER.value,
                "validation_errors": [
                    {
                        "field": "position_value",
                        "location": "query",
                        "message": "Value must be greater than 0"
                    }
                ],
                "valid_params": [
                    "ticker (string, valid symbol)",
                    "position_value (number > 0)",
                    "loan_days (integer > 0)",
                    "client_id (string)"
                ]
            }
        }
    }