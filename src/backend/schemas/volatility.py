"""
Volatility and Event Risk Schemas for the Borrow Rate & Locate Fee Pricing Engine.

This module defines Pydantic models for volatility and event risk data, which are
critical components for calculating borrow rates based on market conditions and
upcoming corporate events. These schemas handle data validation, serialization,
and provide structure for API documentation.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, validator, ConfigDict  # pydantic v2.4.0+

from ..db.models.base import Base


class VolatilityBase(BaseModel):
    """
    Base Pydantic model for volatility data with common fields.
    
    Contains the core fields required for volatility metrics, including
    stock identifier, volatility index value, and event risk factor.
    All volatility-related schemas extend this base model.
    """
    stock_id: str = Field(..., description="Stock ticker symbol", min_length=1, max_length=10)
    vol_index: Decimal = Field(..., description="Volatility index value", ge=0)
    event_risk_factor: int = Field(0, description="Risk factor (0-10) based on upcoming events", ge=0, le=10)
    
    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "stock_id": "AAPL",
                "vol_index": 18.5,
                "event_risk_factor": 2
            }
        }
    )
    
    @validator('vol_index')
    def validate_vol_index(cls, vol_index):
        """
        Validates that vol_index is a positive decimal value.
        
        Args:
            vol_index: The volatility index value to validate
            
        Returns:
            The validated vol_index value
            
        Raises:
            ValueError: If vol_index is negative
        """
        if vol_index < 0:
            raise ValueError("Volatility index must be a non-negative value")
        return vol_index
    
    @validator('event_risk_factor')
    def validate_event_risk_factor(cls, event_risk_factor):
        """
        Validates that event_risk_factor is between 0 and 10.
        
        Args:
            event_risk_factor: The risk factor value to validate
            
        Returns:
            The validated event_risk_factor value
            
        Raises:
            ValueError: If event_risk_factor is outside the valid range
        """
        if event_risk_factor < 0:
            raise ValueError("Event risk factor cannot be negative")
        if event_risk_factor > 10:
            raise ValueError("Event risk factor cannot exceed 10")
        return event_risk_factor


class VolatilitySchema(VolatilityBase):
    """
    Complete volatility schema with all fields including timestamp.
    
    Extends VolatilityBase to include a timestamp field for tracking
    when the volatility data was recorded or updated.
    """
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of when volatility data was recorded")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "stock_id": "AAPL",
                "vol_index": 18.5,
                "event_risk_factor": 2,
                "timestamp": "2023-10-15T14:30:22Z"
            }
        }
    )


class VolatilityCreate(VolatilityBase):
    """
    Schema for creating new volatility records.
    
    Uses the base volatility fields for creating new records in the system.
    The timestamp will be automatically generated upon creation.
    """
    pass


class VolatilityUpdate(BaseModel):
    """
    Schema for updating existing volatility records.
    
    Contains optional fields for updating volatility data, allowing
    partial updates of existing records.
    """
    vol_index: Optional[Decimal] = Field(None, description="Updated volatility index value", ge=0)
    event_risk_factor: Optional[int] = Field(None, description="Updated risk factor (0-10) based on upcoming events", ge=0, le=10)
    
    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "vol_index": 22.3,
                "event_risk_factor": 5
            }
        }
    )


class VolatilityInDB(VolatilityBase):
    """
    Schema representing volatility data as stored in the database.
    
    Extends the base model to include database-specific fields like
    the timestamp for when the record was created or updated.
    """
    timestamp: datetime = Field(..., description="Timestamp of when volatility data was recorded")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "stock_id": "AAPL",
                "vol_index": 18.5,
                "event_risk_factor": 2,
                "timestamp": "2023-10-15T14:30:22Z"
            }
        }
    )


class VolatilityResponse(BaseModel):
    """
    Schema for volatility data response in API.
    
    Represents how volatility data is returned through the API,
    including a categorization of the volatility level.
    """
    stock_id: str = Field(..., description="Stock ticker symbol")
    vol_index: float = Field(..., description="Volatility index value")
    event_risk_factor: int = Field(..., description="Risk factor (0-10) based on upcoming events")
    timestamp: datetime = Field(..., description="Timestamp of when volatility data was recorded")
    volatility_tier: str = Field(..., description="Categorization of volatility level (LOW, MEDIUM, HIGH, EXTREME)")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "stock_id": "AAPL",
                "vol_index": 18.5,
                "event_risk_factor": 2,
                "timestamp": "2023-10-15T14:30:22Z",
                "volatility_tier": "MEDIUM"
            }
        }
    )


class MarketVolatilityResponse(BaseModel):
    """
    Schema for market-wide volatility data response.
    
    Represents market-wide volatility metrics such as VIX,
    which are used as baseline adjustments for individual stocks.
    """
    value: float = Field(..., description="Market volatility index value (e.g., VIX)")
    timestamp: datetime = Field(..., description="Timestamp of when the data was recorded")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "value": 25.7,
                "timestamp": "2023-10-15T14:30:22Z"
            }
        }
    )


class EventSchema(BaseModel):
    """
    Schema for individual event data affecting event risk.
    
    Represents specific events (earnings, dividends, etc.) that
    contribute to a stock's overall event risk factor.
    """
    type: str = Field(..., description="Event type (e.g., 'earnings', 'dividend', 'corporate_action')")
    date: datetime = Field(..., description="Date and time of the event")
    risk_factor: int = Field(..., description="Risk factor (0-10) for this specific event", ge=0, le=10)
    description: Optional[str] = Field(None, description="Optional description of the event")
    
    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "type": "earnings",
                "date": "2023-11-01T20:00:00Z",
                "risk_factor": 7,
                "description": "Q4 Earnings Call"
            }
        }
    )
    
    @validator('risk_factor')
    def validate_risk_factor(cls, risk_factor):
        """
        Validates that risk_factor is between 0 and 10.
        
        Args:
            risk_factor: The risk factor value to validate
            
        Returns:
            The validated risk_factor value
            
        Raises:
            ValueError: If risk_factor is outside the valid range
        """
        if risk_factor < 0:
            raise ValueError("Risk factor cannot be negative")
        if risk_factor > 10:
            raise ValueError("Risk factor cannot exceed 10")
        return risk_factor


class EventRiskResponse(BaseModel):
    """
    Schema for event risk data response in API.
    
    Aggregates all events for a particular stock and provides
    the overall risk factor along with individual event details.
    """
    ticker: str = Field(..., description="Stock ticker symbol")
    risk_factor: int = Field(..., description="Overall risk factor (0-10) based on all events", ge=0, le=10)
    events: List[EventSchema] = Field(default_factory=list, description="List of upcoming events affecting the stock")
    timestamp: datetime = Field(..., description="Timestamp of when the data was retrieved")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticker": "AAPL",
                "risk_factor": 5,
                "events": [
                    {
                        "type": "earnings",
                        "date": "2023-11-01T20:00:00Z",
                        "risk_factor": 7,
                        "description": "Q4 Earnings Call"
                    },
                    {
                        "type": "dividend",
                        "date": "2023-10-25T00:00:00Z",
                        "risk_factor": 3,
                        "description": "Quarterly Dividend"
                    }
                ],
                "timestamp": "2023-10-15T14:30:22Z"
            }
        }
    )