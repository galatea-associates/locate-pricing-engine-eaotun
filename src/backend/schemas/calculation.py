"""
Calculation schemas for the Borrow Rate & Locate Fee Pricing Engine.

This module defines Pydantic models that provide data validation, serialization,
and documentation for fee calculations, including request/response formats,
internal data structures, and database representations.
"""

from decimal import Decimal
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field  # version: 2.4.0+

from ..core.constants import TransactionFeeType, FLAT, PERCENTAGE


class CalculationBase(BaseModel):
    """Base model for calculation data with common fields."""
    
    ticker: str = Field(
        ...,
        description="Stock symbol for the calculation (e.g., 'AAPL')",
        example="GME",
        min_length=1,
        max_length=10
    )
    
    position_value: Decimal = Field(
        ...,
        description="Notional value of the short position in USD",
        example=50000.00,
        gt=0
    )
    
    loan_days: int = Field(
        ...,
        description="Duration of the borrow in days",
        example=30,
        gt=0
    )
    
    client_id: str = Field(
        ...,
        description="Client identifier for fee structure",
        example="big_fund_007",
        min_length=1
    )
    
    @classmethod
    def model_config(cls):
        """Pydantic model configuration."""
        return {
            "extra": "forbid",  # Prevent extra fields
            "str_strip_whitespace": True  # Strip whitespace from string fields
        }


class FeeBreakdownSchema(BaseModel):
    """Schema for detailed fee breakdown components."""
    
    borrow_cost: Decimal = Field(
        ...,
        description="Base cost of borrowing the security",
        example=3195.34
    )
    
    markup: Decimal = Field(
        ...,
        description="Broker-specific markup applied to the base cost",
        example=188.53
    )
    
    transaction_fees: Decimal = Field(
        ...,
        description="Additional transaction fees (flat or percentage-based)",
        example=40.90
    )
    
    @classmethod
    def model_config(cls):
        """Pydantic model configuration."""
        return {
            "extra": "forbid",
            "json_schema_extra": {
                "example": {
                    "borrow_cost": 3195.34,
                    "markup": 188.53,
                    "transaction_fees": 40.90
                }
            }
        }


class CalculationSchema(BaseModel):
    """Complete calculation data schema with all fields."""
    
    ticker: str = Field(
        ...,
        description="Stock symbol for the calculation",
        example="GME"
    )
    
    position_value: Decimal = Field(
        ...,
        description="Notional value of the short position in USD",
        example=50000.00
    )
    
    loan_days: int = Field(
        ..., 
        description="Duration of the borrow in days",
        example=60
    )
    
    client_id: str = Field(
        ...,
        description="Client identifier for fee structure",
        example="big_fund_007"
    )
    
    borrow_rate: Decimal = Field(
        ...,
        description="Annualized borrow rate used for the calculation",
        example=0.19
    )
    
    total_fee: Decimal = Field(
        ...,
        description="Total fee calculated for the borrow",
        example=3428.77
    )
    
    fee_breakdown: FeeBreakdownSchema = Field(
        ...,
        description="Detailed breakdown of fee components"
    )
    
    data_sources: Optional[Dict[str, str]] = Field(
        None,
        description="Sources of data used for the calculation",
        example={
            "borrow_rate": "SecLend API",
            "volatility": "Market Data API",
            "event_risk": "Event Calendar API"
        }
    )
    
    @classmethod
    def model_config(cls):
        """Pydantic model configuration."""
        return {
            "extra": "forbid",
            "json_schema_extra": {
                "example": {
                    "ticker": "GME",
                    "position_value": 50000.00,
                    "loan_days": 60,
                    "client_id": "big_fund_007",
                    "borrow_rate": 0.19,
                    "total_fee": 3428.77,
                    "fee_breakdown": {
                        "borrow_cost": 3195.34,
                        "markup": 188.53,
                        "transaction_fees": 40.90
                    },
                    "data_sources": {
                        "borrow_rate": "SecLend API",
                        "volatility": "Market Data API",
                        "event_risk": "Event Calendar API"
                    }
                }
            }
        }


class CalculationCreate(BaseModel):
    """Schema for creating new calculation records."""
    
    ticker: str = Field(
        ...,
        description="Stock symbol for the calculation",
        example="GME"
    )
    
    position_value: Decimal = Field(
        ...,
        description="Notional value of the short position in USD",
        example=50000.00
    )
    
    loan_days: int = Field(
        ..., 
        description="Duration of the borrow in days",
        example=60
    )
    
    client_id: str = Field(
        ...,
        description="Client identifier for fee structure",
        example="big_fund_007"
    )
    
    borrow_rate: Decimal = Field(
        ...,
        description="Annualized borrow rate used for the calculation",
        example=0.19
    )
    
    total_fee: Decimal = Field(
        ...,
        description="Total fee calculated for the borrow",
        example=3428.77
    )
    
    fee_breakdown: Dict = Field(
        ...,
        description="Detailed breakdown of fee components"
    )


class CalculationInDB(BaseModel):
    """Schema representing calculation data as stored in the database."""
    
    id: UUID = Field(
        ...,
        description="Unique identifier for the calculation record"
    )
    
    ticker: str = Field(
        ...,
        description="Stock symbol for the calculation"
    )
    
    position_value: Decimal = Field(
        ...,
        description="Notional value of the short position in USD"
    )
    
    loan_days: int = Field(
        ..., 
        description="Duration of the borrow in days"
    )
    
    client_id: str = Field(
        ...,
        description="Client identifier for fee structure"
    )
    
    borrow_rate: Decimal = Field(
        ...,
        description="Annualized borrow rate used for the calculation"
    )
    
    total_fee: Decimal = Field(
        ...,
        description="Total fee calculated for the borrow"
    )
    
    fee_breakdown: Dict = Field(
        ...,
        description="Detailed breakdown of fee components"
    )
    
    data_sources: Dict[str, str] = Field(
        ...,
        description="Sources of data used for the calculation"
    )


class BorrowRateCalculationSchema(BaseModel):
    """Schema for borrow rate calculation components."""
    
    base_rate: Decimal = Field(
        ...,
        description="Base borrow rate from the source API",
        example=0.15
    )
    
    volatility_adjustment: Optional[Decimal] = Field(
        None,
        description="Adjustment based on market volatility",
        example=0.025
    )
    
    event_risk_adjustment: Optional[Decimal] = Field(
        None,
        description="Adjustment based on event risk factors",
        example=0.015
    )
    
    final_rate: Decimal = Field(
        ...,
        description="Final calculated borrow rate after all adjustments",
        example=0.19
    )
    
    data_sources: Optional[Dict[str, str]] = Field(
        None,
        description="Sources of data used for rate calculation",
        example={
            "base_rate": "SecLend API",
            "volatility": "Market Data API",
            "event_risk": "Event Calendar API"
        }
    )
    
    @classmethod
    def model_config(cls):
        """Pydantic model configuration."""
        return {
            "extra": "forbid",
            "json_schema_extra": {
                "example": {
                    "base_rate": 0.15,
                    "volatility_adjustment": 0.025,
                    "event_risk_adjustment": 0.015,
                    "final_rate": 0.19,
                    "data_sources": {
                        "base_rate": "SecLend API",
                        "volatility": "Market Data API",
                        "event_risk": "Event Calendar API"
                    }
                }
            }
        }


class TimeFactor(BaseModel):
    """Schema for time factor calculation in fee formulas."""
    
    loan_days: int = Field(
        ...,
        description="Duration of the borrow in days",
        example=30
    )
    
    annualized_rate: Decimal = Field(
        ...,
        description="Annualized borrow rate",
        example=0.19
    )
    
    daily_rate: Decimal = Field(
        ...,
        description="Daily rate derived from annualized rate",
        example=0.00052
    )
    
    time_factor: Decimal = Field(
        ...,
        description="Final time factor used in fee calculations",
        example=0.0156
    )
    
    @classmethod
    def model_config(cls):
        """Pydantic model configuration."""
        return {
            "extra": "forbid",
            "json_schema_extra": {
                "example": {
                    "loan_days": 30,
                    "annualized_rate": 0.19,
                    "daily_rate": 0.00052,
                    "time_factor": 0.0156
                }
            }
        }