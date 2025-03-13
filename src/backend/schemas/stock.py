"""
Stock data schemas for the Borrow Rate & Locate Fee Pricing Engine.

This module defines Pydantic models for stock-related data structures used in the
pricing engine. These schemas provide data validation, serialization, and documentation
for stock information, including borrow status and rates.
"""

import re
from datetime import datetime
from decimal import Decimal  # standard library
from typing import Optional  # standard library

from pydantic import BaseModel, Field, validator  # pydantic 2.4.0+

from ..core.constants import BorrowStatus

# Regex pattern for ticker symbol validation
TICKER_PATTERN = re.compile(r'^[A-Z]{1,5}$')


class StockBase(BaseModel):
    """Base model for stock data with common fields."""
    
    ticker: str = Field(
        ...,
        description="Stock ticker symbol (1-5 uppercase letters)",
        example="AAPL"
    )
    borrow_status: BorrowStatus = Field(
        ...,
        description="Borrowing difficulty category",
        example=BorrowStatus.EASY
    )
    lender_api_id: Optional[str] = Field(
        None,
        description="External API identifier for this stock",
        example="SEC123"
    )
    
    @validator('ticker')
    def validate_ticker(cls, v):
        """Validates that the ticker symbol is in the correct format."""
        if not v:
            raise ValueError("Ticker symbol cannot be empty")
        
        v = v.upper()
        if not TICKER_PATTERN.match(v):
            raise ValueError("Ticker must be 1-5 uppercase letters")
        
        return v
    
    model_config = {
        "extra": "forbid",
        "str_strip_whitespace": True
    }


class StockSchema(StockBase):
    """Complete stock data schema with all fields."""
    
    min_borrow_rate: Decimal = Field(
        ...,
        description="Minimum borrow rate when external data unavailable",
        ge=0,
        example=0.01
    )
    last_updated: datetime = Field(
        ...,
        description="Last data refresh time",
        example=datetime.now().isoformat()
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "ticker": "AAPL",
                "borrow_status": BorrowStatus.EASY,
                "lender_api_id": "SEC123",
                "min_borrow_rate": 0.01,
                "last_updated": datetime.now().isoformat()
            }
        }
    }


class StockCreate(StockBase):
    """Schema for creating new stock records."""
    
    min_borrow_rate: Decimal = Field(
        ...,
        description="Minimum borrow rate when external data unavailable",
        ge=0,
        example=0.01
    )


class StockUpdate(BaseModel):
    """Schema for updating existing stock records."""
    
    borrow_status: Optional[BorrowStatus] = Field(
        None,
        description="Borrowing difficulty category",
        example=BorrowStatus.EASY
    )
    lender_api_id: Optional[str] = Field(
        None,
        description="External API identifier for this stock",
        example="SEC123"
    )
    min_borrow_rate: Optional[Decimal] = Field(
        None,
        description="Minimum borrow rate when external data unavailable",
        ge=0,
        example=0.01
    )
    
    model_config = {
        "extra": "forbid"
    }


class StockInDB(StockSchema):
    """Schema representing stock data as stored in the database."""
    pass


class RateResponse(BaseModel):
    """Schema for current borrow rate response."""
    
    ticker: str = Field(
        ...,
        description="Stock ticker symbol",
        example="AAPL"
    )
    current_rate: Decimal = Field(
        ...,
        description="Current borrow rate as a decimal percentage",
        ge=0,
        example=0.05
    )
    borrow_status: BorrowStatus = Field(
        ...,
        description="Borrowing difficulty category",
        example=BorrowStatus.EASY
    )
    volatility_index: Optional[Decimal] = Field(
        None,
        description="Market volatility index used in calculation",
        ge=0,
        example=18.5
    )
    event_risk_factor: Optional[int] = Field(
        None,
        description="Risk score (0-10) for upcoming events",
        ge=0,
        le=10,
        example=2
    )
    last_updated: datetime = Field(
        ...,
        description="When this rate was last updated",
        example=datetime.now().isoformat()
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "ticker": "AAPL",
                "current_rate": 0.05,
                "borrow_status": BorrowStatus.EASY,
                "volatility_index": 18.5,
                "event_risk_factor": 2,
                "last_updated": datetime.now().isoformat()
            }
        }
    }