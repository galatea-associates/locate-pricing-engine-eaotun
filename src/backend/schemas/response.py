"""
Response schemas for the Borrow Rate & Locate Fee Pricing Engine.

This module defines standardized Pydantic models for API responses, ensuring consistent
formatting across all endpoints. These response models include common status fields,
detailed fee breakdowns, and appropriate data validation for financial information.
"""

from datetime import datetime
from decimal import Decimal  # standard library
from typing import Dict, Optional  # standard library

from pydantic import BaseModel, Field  # version: 2.4.0+

from ..core.constants import BorrowStatus
from .calculation import FeeBreakdownSchema


class BaseResponse(BaseModel):
    """Base model for all API responses with common status field."""
    
    status: str = Field(
        ...,
        description="Response status indicating success or error",
        example="success"
    )
    
    @classmethod
    def model_config(cls):
        """Pydantic model configuration."""
        return {
            "extra": "forbid",  # Prevent extra fields
            "str_strip_whitespace": True  # Strip whitespace from string fields
        }


class CalculateLocateResponse(BaseResponse):
    """Response model for locate fee calculation endpoint."""
    
    total_fee: Decimal = Field(
        ...,
        description="Total fee calculated for the borrow",
        example=3428.77
    )
    
    breakdown: FeeBreakdownSchema = Field(
        ...,
        description="Detailed breakdown of fee components"
    )
    
    borrow_rate_used: Decimal = Field(
        ...,
        description="Annualized borrow rate used for the calculation",
        example=0.19
    )
    
    @classmethod
    def model_config(cls):
        """Pydantic model configuration."""
        return {
            "extra": "forbid",
            "json_schema_extra": {
                "example": {
                    "status": "success",
                    "total_fee": 3428.77,
                    "breakdown": {
                        "borrow_cost": 3195.34,
                        "markup": 188.53,
                        "transaction_fees": 40.90
                    },
                    "borrow_rate_used": 0.19
                }
            }
        }


class BorrowRateResponse(BaseResponse):
    """Response model for borrow rate endpoint."""
    
    ticker: str = Field(
        ...,
        description="Stock symbol (e.g., 'AAPL')",
        example="AAPL"
    )
    
    current_rate: Decimal = Field(
        ...,
        description="Current borrow rate as a decimal percentage",
        example=0.05
    )
    
    borrow_status: str = Field(
        ...,
        description="Borrowing difficulty tier (EASY, MEDIUM, HARD)",
        example="EASY"
    )
    
    volatility_index: Optional[Decimal] = Field(
        None,
        description="Market volatility index affecting the rate",
        example=18.5
    )
    
    event_risk_factor: Optional[int] = Field(
        None,
        description="Risk factor (0-10) for upcoming corporate events",
        example=2,
        ge=0,
        le=10
    )
    
    last_updated: datetime = Field(
        ...,
        description="Timestamp when rate was last updated",
        example="2023-10-15T14:30:22Z"
    )
    
    @classmethod
    def model_config(cls):
        """Pydantic model configuration."""
        return {
            "extra": "forbid",
            "json_schema_extra": {
                "example": {
                    "status": "success",
                    "ticker": "AAPL",
                    "current_rate": 0.05,
                    "borrow_status": "EASY",
                    "volatility_index": 18.5,
                    "event_risk_factor": 2,
                    "last_updated": "2023-10-15T14:30:22Z"
                }
            }
        }


class HealthResponse(BaseResponse):
    """Response model for health check endpoint."""
    
    version: str = Field(
        ...,
        description="API version number",
        example="1.0.0"
    )
    
    components: Dict[str, str] = Field(
        ...,
        description="Status of system components",
        example={
            "database": "connected",
            "cache": "connected",
            "external_apis": "available"
        }
    )
    
    timestamp: datetime = Field(
        ...,
        description="Current server timestamp",
        example="2023-10-16T08:45:12Z"
    )
    
    @classmethod
    def model_config(cls):
        """Pydantic model configuration."""
        return {
            "extra": "forbid",
            "json_schema_extra": {
                "example": {
                    "status": "healthy",
                    "version": "1.0.0",
                    "components": {
                        "database": "connected",
                        "cache": "connected",
                        "external_apis": "available"
                    },
                    "timestamp": "2023-10-16T08:45:12Z"
                }
            }
        }


class ConfigResponse(BaseResponse):
    """Response model for configuration endpoint."""
    
    config: Dict[str, Dict] = Field(
        ...,
        description="System configuration parameters",
        example={
            "api_version": {"current": "1.0", "deprecated": []},
            "supported_features": {"rate_calculation": True, "fee_proration": True},
            "rate_limits": {"standard": 60, "premium": 300}
        }
    )
    
    @classmethod
    def model_config(cls):
        """Pydantic model configuration."""
        return {
            "extra": "forbid",
            "json_schema_extra": {
                "example": {
                    "status": "success",
                    "config": {
                        "api_version": {"current": "1.0", "deprecated": []},
                        "supported_features": {"rate_calculation": True, "fee_proration": True},
                        "rate_limits": {"standard": 60, "premium": 300}
                    }
                }
            }
        }