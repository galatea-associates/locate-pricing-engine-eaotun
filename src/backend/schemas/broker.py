"""
Defines Pydantic models for broker-related data structures used in the
Borrow Rate & Locate Fee Pricing Engine. These schemas provide data validation,
serialization, and documentation for broker information, including markup percentages
and transaction fee configurations.
"""

from decimal import Decimal
from datetime import datetime
import re
from typing import Optional

from pydantic import BaseModel, Field, validator  # pydantic version: 2.4.0+

from ..core.constants import TransactionFeeType

# Regular expression for validating client IDs
CLIENT_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{3,50}$')


class BrokerBase(BaseModel):
    """
    Base model for broker data with common fields.
    
    Contains the core fields needed for broker fee calculations, along with
    appropriate validation rules to ensure data integrity.
    """
    client_id: str = Field(
        description="Unique identifier for the broker or client",
        example="broker_123"
    )
    markup_percentage: Decimal = Field(
        description="Percentage markup applied over the base borrow rate",
        example=5.0,
        ge=0,
        le=100
    )
    transaction_fee_type: TransactionFeeType = Field(
        description="Type of transaction fee (FLAT or PERCENTAGE)",
        example=TransactionFeeType.FLAT
    )
    transaction_amount: Decimal = Field(
        description="Fee amount (interpreted according to transaction_fee_type)",
        example=25.0,
        ge=0
    )

    model_config = {
        "extra": "forbid",
        "str_strip_whitespace": True
    }

    @validator('client_id')
    def validate_client_id(cls, v):
        """
        Validates that the client ID is in the correct format.
        
        Args:
            v: The client ID to validate
            
        Returns:
            The validated client ID
            
        Raises:
            ValueError: If the client ID is invalid
        """
        if v is None or v.strip() == '':
            raise ValueError('client_id cannot be empty')
        
        if not CLIENT_ID_PATTERN.match(v):
            raise ValueError(
                'client_id must contain only alphanumeric characters, underscores, '
                'and hyphens, with length between 3-50 characters'
            )
        return v

    @validator('markup_percentage')
    def validate_markup_percentage(cls, v):
        """
        Validates that the markup percentage is within acceptable range.
        
        Args:
            v: The markup percentage to validate
            
        Returns:
            The validated markup percentage
            
        Raises:
            ValueError: If the markup percentage is out of range
        """
        if v < 0:
            raise ValueError('markup_percentage must be greater than or equal to 0')
        if v > 100:
            raise ValueError('markup_percentage must be less than or equal to 100')
        return v

    @validator('transaction_amount')
    def validate_transaction_amount(cls, v, values):
        """
        Validates that the transaction amount is within acceptable range.
        
        For percentage-based fees, also ensures the percentage is not greater than 100.
        
        Args:
            v: The transaction amount to validate
            values: The values dict containing other validated fields
            
        Returns:
            The validated transaction amount
            
        Raises:
            ValueError: If the transaction amount is invalid
        """
        if v < 0:
            raise ValueError('transaction_amount must be greater than or equal to 0')
        
        fee_type = values.get('transaction_fee_type')
        if fee_type is not None and fee_type == TransactionFeeType.PERCENTAGE and v > 100:
            raise ValueError('For percentage-based fees, transaction_amount must not exceed 100')
        
        return v


class BrokerSchema(BrokerBase):
    """
    Complete broker data schema with all fields.
    
    Extends the base model with additional fields such as active status and
    last updated timestamp, representing the full broker record.
    """
    active: bool = Field(
        default=True,
        description="Whether the broker is currently active",
        example=True
    )
    last_updated: datetime = Field(
        description="Timestamp when the broker record was last updated",
        example="2023-10-15T14:30:22Z"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "client_id": "broker_123",
                "markup_percentage": 5.0,
                "transaction_fee_type": TransactionFeeType.FLAT,
                "transaction_amount": 25.0,
                "active": True,
                "last_updated": "2023-10-15T14:30:22Z"
            }
        }
    }


class BrokerCreate(BrokerBase):
    """
    Schema for creating new broker records.
    
    Contains all the fields required to create a new broker record in the system.
    The last_updated field will be set automatically by the backend.
    """
    active: bool = Field(
        default=True,
        description="Whether the broker is currently active",
        example=True
    )


class BrokerUpdate(BaseModel):
    """
    Schema for updating existing broker records.
    
    All fields are optional since updates may modify only a subset of fields.
    The client_id cannot be updated as it is the primary identifier.
    """
    markup_percentage: Optional[Decimal] = Field(
        default=None, 
        description="Percentage markup applied over the base borrow rate",
        example=5.0,
        ge=0,
        le=100
    )
    transaction_fee_type: Optional[TransactionFeeType] = Field(
        default=None,
        description="Type of transaction fee (FLAT or PERCENTAGE)",
        example=TransactionFeeType.FLAT
    )
    transaction_amount: Optional[Decimal] = Field(
        default=None,
        description="Fee amount (interpreted according to transaction_fee_type)",
        example=25.0,
        ge=0
    )
    active: Optional[bool] = Field(
        default=None,
        description="Whether the broker is currently active",
        example=True
    )

    model_config = {
        "extra": "forbid"
    }


class BrokerInDB(BrokerSchema):
    """
    Schema representing broker data as stored in the database.
    
    This model mirrors the database schema for broker records and is used
    for retrieving broker data from the database.
    """
    pass  # All fields are inherited from BrokerSchema