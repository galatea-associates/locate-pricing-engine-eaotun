"""
Defines Pydantic models for validating API request data in the Borrow Rate & Locate Fee Pricing Engine.
These schemas ensure that all incoming requests are properly validated before processing,
providing clear error messages when validation fails.
"""

import re
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, validator

from ..utils.validation import MIN_POSITION_VALUE, MAX_POSITION_VALUE, MIN_LOAN_DAYS, MAX_LOAN_DAYS
from ..core.constants import ErrorCodes

# Compile regex patterns for validation
TICKER_PATTERN = re.compile(r'^[A-Z]{1,5}$')
CLIENT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,50}$')


class CalculateLocateRequest(BaseModel):
    """Pydantic model for validating locate fee calculation requests"""
    ticker: str
    position_value: Decimal
    loan_days: int
    client_id: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "ticker": "AAPL",
                "position_value": 100000,
                "loan_days": 30,
                "client_id": "xyz123"
            }
        }
    }

    @validator('ticker')
    def validate_ticker(cls, v):
        """Validates that the ticker symbol is in the correct format"""
        if v is None or not v:
            raise ValueError("Ticker symbol is required")
        
        v = v.upper()
        if not TICKER_PATTERN.match(v):
            raise ValueError("Invalid ticker format. Must be 1-5 uppercase letters.")
        
        return v
    
    @validator('position_value')
    def validate_position_value(cls, v):
        """Validates that the position value is within acceptable range"""
        if v is None:
            raise ValueError("Position value is required")
        
        # Convert to Decimal if it's not already
        if not isinstance(v, Decimal):
            try:
                v = Decimal(str(v))
            except (ValueError, TypeError, ArithmeticError):
                raise ValueError("Invalid position value format")
        
        if not (MIN_POSITION_VALUE <= v <= MAX_POSITION_VALUE):
            raise ValueError(f"Position value must be between {MIN_POSITION_VALUE} and {MAX_POSITION_VALUE}")
        
        return v
    
    @validator('loan_days')
    def validate_loan_days(cls, v):
        """Validates that loan days is within acceptable range"""
        if v is None:
            raise ValueError("Loan days is required")
        
        # Convert to int if it's not already
        if not isinstance(v, int):
            try:
                v = int(v)
            except (ValueError, TypeError):
                raise ValueError("Invalid loan days format")
        
        if not (MIN_LOAN_DAYS <= v <= MAX_LOAN_DAYS):
            raise ValueError(f"Loan days must be between {MIN_LOAN_DAYS} and {MAX_LOAN_DAYS}")
        
        return v
    
    @validator('client_id')
    def validate_client_id(cls, v):
        """Validates that the client ID is in the correct format"""
        if v is None or not v:
            raise ValueError("Client ID is required")
        
        if not CLIENT_ID_PATTERN.match(v):
            raise ValueError("Invalid client ID format. Must be 3-50 alphanumeric characters, underscores, or hyphens.")
        
        return v


class GetRateRequest(BaseModel):
    """Pydantic model for validating borrow rate retrieval requests"""
    ticker: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "ticker": "AAPL"
            }
        }
    }

    @validator('ticker')
    def validate_ticker(cls, v):
        """Validates that the ticker symbol is in the correct format"""
        if v is None or not v:
            raise ValueError("Ticker symbol is required")
        
        v = v.upper()
        if not TICKER_PATTERN.match(v):
            raise ValueError("Invalid ticker format. Must be 1-5 uppercase letters.")
        
        return v


class RefreshRateRequest(BaseModel):
    """Pydantic model for validating rate refresh requests"""
    ticker: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "ticker": "AAPL"
            }
        }
    }

    @validator('ticker')
    def validate_ticker(cls, v):
        """Validates that the ticker symbol is in the correct format"""
        if v is None or not v:
            raise ValueError("Ticker symbol is required")
        
        v = v.upper()
        if not TICKER_PATTERN.match(v):
            raise ValueError("Invalid ticker format. Must be 1-5 uppercase letters.")
        
        return v