"""
Audit schemas for the Borrow Rate & Locate Fee Pricing Engine.

This module defines Pydantic models that provide data validation, serialization,
and documentation for audit logs, data sources, and calculation breakdowns to
support regulatory compliance and troubleshooting.
"""

from decimal import Decimal  # standard library
from datetime import datetime  # standard library
from typing import Dict, List, Optional  # standard library
from uuid import UUID  # standard library

from pydantic import BaseModel, Field  # version: 2.4.0+

from .calculation import FeeBreakdownSchema


class DataSourceSchema(BaseModel):
    """Schema for tracking data sources used in calculations."""
    
    borrow_rate: str = Field(
        ...,
        description="Source of borrow rate data",
        example="SecLend API"
    )
    
    volatility: str = Field(
        ...,
        description="Source of market volatility data",
        example="Market Data API"
    )
    
    event_risk: str = Field(
        ...,
        description="Source of event risk data",
        example="Event Calendar API"
    )
    
    @classmethod
    def model_config(cls):
        """Pydantic model configuration."""
        return {
            "extra": "forbid",  # Prevent extra fields
            "json_schema_extra": {
                "example": {
                    "borrow_rate": "SecLend API",
                    "volatility": "Market Data API",
                    "event_risk": "Event Calendar API"
                }
            }
        }


class CalculationBreakdownSchema(BaseModel):
    """Schema for detailed breakdown of fee calculation steps."""
    
    fee_components: FeeBreakdownSchema = Field(
        ...,
        description="Breakdown of fee components including borrow cost, markup, and transaction fees"
    )
    
    base_borrow_rate: Decimal = Field(
        ...,
        description="Initial borrow rate before adjustments",
        example=0.15
    )
    
    volatility_adjustment: Optional[Decimal] = Field(
        None,
        description="Adjustment applied to borrow rate based on market volatility",
        example=0.025
    )
    
    event_risk_adjustment: Optional[Decimal] = Field(
        None,
        description="Adjustment applied to borrow rate based on event risk",
        example=0.015
    )
    
    final_borrow_rate: Decimal = Field(
        ...,
        description="Final borrow rate after all adjustments",
        example=0.19
    )
    
    annualized_rate: Decimal = Field(
        ...,
        description="Annualized rate used for calculations",
        example=0.19
    )
    
    time_factor: Decimal = Field(
        ...,
        description="Time factor applied to convert annualized rate to the specific loan period",
        example=0.0822
    )
    
    @classmethod
    def model_config(cls):
        """Pydantic model configuration."""
        return {
            "extra": "forbid",
            "json_schema_extra": {
                "example": {
                    "fee_components": {
                        "borrow_cost": 3195.34,
                        "markup": 188.53,
                        "transaction_fees": 40.90
                    },
                    "base_borrow_rate": 0.15,
                    "volatility_adjustment": 0.025,
                    "event_risk_adjustment": 0.015,
                    "final_borrow_rate": 0.19,
                    "annualized_rate": 0.19,
                    "time_factor": 0.0822
                }
            }
        }


class AuditLogSchema(BaseModel):
    """Schema for comprehensive audit log entries of all fee calculations."""
    
    audit_id: UUID = Field(
        ...,
        description="Unique identifier for the audit record",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    timestamp: datetime = Field(
        ...,
        description="When the calculation occurred",
        example="2023-10-15T14:30:22Z"
    )
    
    client_id: str = Field(
        ...,
        description="Client that requested the calculation",
        example="client123"
    )
    
    ticker: str = Field(
        ...,
        description="Stock symbol used in the calculation",
        example="AAPL"
    )
    
    position_value: Decimal = Field(
        ...,
        description="Notional value of the short position in USD",
        example=100000.00
    )
    
    loan_days: int = Field(
        ...,
        description="Duration of borrow in days",
        example=30
    )
    
    borrow_rate_used: Decimal = Field(
        ...,
        description="Borrow rate applied in the calculation",
        example=0.19
    )
    
    total_fee: Decimal = Field(
        ...,
        description="Total fee calculated",
        example=3428.77
    )
    
    data_sources: Dict[str, str] = Field(
        ...,
        description="Sources of data used in the calculation",
        example={
            "borrow_rate": "SecLend API",
            "volatility": "Market Data API",
            "event_risk": "Event Calendar API"
        }
    )
    
    calculation_breakdown: CalculationBreakdownSchema = Field(
        ...,
        description="Detailed breakdown of calculation steps"
    )
    
    request_id: Optional[str] = Field(
        None,
        description="Identifier for the API request that triggered the calculation",
        example="req-12345-abcde"
    )
    
    user_agent: Optional[str] = Field(
        None,
        description="User agent of the client that made the request",
        example="Mozilla/5.0 (compatible; TradingPlatform/1.0)"
    )
    
    ip_address: Optional[str] = Field(
        None,
        description="IP address of the client that made the request",
        example="192.168.1.1"
    )
    
    @classmethod
    def model_config(cls):
        """Pydantic model configuration."""
        return {
            "extra": "forbid",
            "json_schema_extra": {
                "example": {
                    "audit_id": "123e4567-e89b-12d3-a456-426614174000",
                    "timestamp": "2023-10-15T14:30:22Z",
                    "client_id": "client123",
                    "ticker": "AAPL",
                    "position_value": 100000.00,
                    "loan_days": 30,
                    "borrow_rate_used": 0.19,
                    "total_fee": 3428.77,
                    "data_sources": {
                        "borrow_rate": "SecLend API",
                        "volatility": "Market Data API",
                        "event_risk": "Event Calendar API"
                    },
                    "calculation_breakdown": {
                        "fee_components": {
                            "borrow_cost": 3195.34,
                            "markup": 188.53,
                            "transaction_fees": 40.90
                        },
                        "base_borrow_rate": 0.15,
                        "volatility_adjustment": 0.025,
                        "event_risk_adjustment": 0.015,
                        "final_borrow_rate": 0.19,
                        "annualized_rate": 0.19,
                        "time_factor": 0.0822
                    },
                    "request_id": "req-12345-abcde",
                    "user_agent": "Mozilla/5.0 (compatible; TradingPlatform/1.0)",
                    "ip_address": "192.168.1.1"
                }
            }
        }


class AuditLogFilterSchema(BaseModel):
    """Schema for filtering audit log entries in queries."""
    
    client_id: Optional[str] = Field(
        None,
        description="Filter by client identifier",
        example="client123"
    )
    
    ticker: Optional[str] = Field(
        None,
        description="Filter by stock symbol",
        example="AAPL"
    )
    
    start_date: Optional[datetime] = Field(
        None,
        description="Filter for records after this date/time",
        example="2023-10-01T00:00:00Z"
    )
    
    end_date: Optional[datetime] = Field(
        None,
        description="Filter for records before this date/time",
        example="2023-10-31T23:59:59Z"
    )
    
    min_position_value: Optional[Decimal] = Field(
        None,
        description="Filter for position values greater than or equal to this amount",
        example=50000.00
    )
    
    max_position_value: Optional[Decimal] = Field(
        None,
        description="Filter for position values less than or equal to this amount",
        example=200000.00
    )
    
    min_borrow_rate: Optional[Decimal] = Field(
        None,
        description="Filter for borrow rates greater than or equal to this rate",
        example=0.1
    )
    
    max_borrow_rate: Optional[Decimal] = Field(
        None,
        description="Filter for borrow rates less than or equal to this rate",
        example=0.5
    )
    
    page: Optional[int] = Field(
        1,
        description="Page number for pagination",
        example=1,
        ge=1
    )
    
    page_size: Optional[int] = Field(
        50,
        description="Number of items per page",
        example=50,
        ge=1,
        le=100
    )
    
    @classmethod
    def model_config(cls):
        """Pydantic model configuration."""
        return {
            "extra": "forbid",
            "json_schema_extra": {
                "example": {
                    "client_id": "client123",
                    "ticker": "AAPL",
                    "start_date": "2023-10-01T00:00:00Z",
                    "end_date": "2023-10-31T23:59:59Z",
                    "min_position_value": 50000.00,
                    "max_position_value": 200000.00,
                    "min_borrow_rate": 0.1,
                    "max_borrow_rate": 0.5,
                    "page": 1,
                    "page_size": 50
                }
            }
        }


class AuditLogResponseSchema(BaseModel):
    """Schema for paginated audit log query responses."""
    
    items: List[AuditLogSchema] = Field(
        ...,
        description="List of audit log entries matching the query"
    )
    
    total: int = Field(
        ...,
        description="Total number of records matching the query",
        example=157
    )
    
    page: int = Field(
        ...,
        description="Current page number",
        example=1
    )
    
    page_size: int = Field(
        ...,
        description="Number of items per page",
        example=50
    )
    
    pages: int = Field(
        ...,
        description="Total number of pages available",
        example=4
    )
    
    @classmethod
    def model_config(cls):
        """Pydantic model configuration."""
        return {
            "extra": "forbid",
            "json_schema_extra": {
                "example": {
                    "items": [
                        {
                            "audit_id": "123e4567-e89b-12d3-a456-426614174000",
                            "timestamp": "2023-10-15T14:30:22Z",
                            "client_id": "client123",
                            "ticker": "AAPL",
                            "position_value": 100000.00,
                            "loan_days": 30,
                            "borrow_rate_used": 0.19,
                            "total_fee": 3428.77,
                            "data_sources": {
                                "borrow_rate": "SecLend API",
                                "volatility": "Market Data API",
                                "event_risk": "Event Calendar API"
                            },
                            "calculation_breakdown": {
                                "fee_components": {
                                    "borrow_cost": 3195.34,
                                    "markup": 188.53,
                                    "transaction_fees": 40.90
                                },
                                "base_borrow_rate": 0.15,
                                "volatility_adjustment": 0.025,
                                "event_risk_adjustment": 0.015,
                                "final_borrow_rate": 0.19,
                                "annualized_rate": 0.19,
                                "time_factor": 0.0822
                            },
                            "request_id": "req-12345-abcde",
                            "user_agent": "Mozilla/5.0 (compatible; TradingPlatform/1.0)",
                            "ip_address": "192.168.1.1"
                        }
                    ],
                    "total": 157,
                    "page": 1,
                    "page_size": 50,
                    "pages": 4
                }
            }
        }