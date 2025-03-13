"""
Defines Pydantic models for API key-related data structures used in the Borrow Rate & Locate Fee Pricing Engine.

These schemas provide data validation, serialization, and documentation for API keys,
including creation, update, and response models.
"""
from datetime import datetime, timedelta
from typing import Optional
import re

from pydantic import BaseModel, Field, validator  # pydantic 2.4.0+

from ..core.constants import ErrorCodes, API_KEY_EXPIRY_DAYS

# Regular expression pattern for validating API keys
API_KEY_PATTERN = re.compile(r'^[A-Za-z0-9_\-]{32,64}$')


class ApiKeyBase(BaseModel):
    """Base model for API key data with common fields."""
    
    client_id: str = Field(..., description="Unique identifier for the client/broker")
    rate_limit: int = Field(..., description="Maximum number of API requests allowed per minute")
    
    @validator('client_id')
    def validate_client_id(cls, v):
        """Validates that the client ID is in the correct format."""
        if not v or not isinstance(v, str):
            raise ValueError('client_id must be a non-empty string')
        return v
    
    @validator('rate_limit')
    def validate_rate_limit(cls, v):
        """Validates that the rate limit is within acceptable range."""
        if v < 1:
            raise ValueError('rate_limit must be at least 1')
        if v > 1000:
            raise ValueError('rate_limit cannot exceed 1000')
        return v
    
    model_config = {
        "extra": "forbid",
        "str_strip_whitespace": True,
    }


class ApiKeyCreate(ApiKeyBase):
    """Schema for creating new API keys."""
    
    expiry_days: Optional[int] = Field(None, description="Number of days until the API key expires")
    
    @validator('expiry_days')
    def validate_expiry_days(cls, v):
        """Validates that the expiry days is within acceptable range."""
        if v is None:
            return API_KEY_EXPIRY_DAYS
        if v < 1:
            raise ValueError('expiry_days must be at least 1')
        if v > 365:
            raise ValueError('expiry_days cannot exceed 365')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "client_id": "broker_123",
                "rate_limit": 60,
                "expiry_days": 90
            }
        }
    }


class ApiKeyUpdate(BaseModel):
    """Schema for updating existing API keys."""
    
    rate_limit: Optional[int] = Field(None, description="Maximum number of API requests allowed per minute")
    active: Optional[bool] = Field(None, description="Whether the API key is active")
    expires_at: Optional[datetime] = Field(None, description="Timestamp when the API key will expire")
    
    @validator('rate_limit')
    def validate_rate_limit(cls, v):
        """Validates that the rate limit is within acceptable range."""
        if v is None:
            return None
        if v < 1:
            raise ValueError('rate_limit must be at least 1')
        if v > 1000:
            raise ValueError('rate_limit cannot exceed 1000')
        return v
    
    @validator('expires_at')
    def validate_expires_at(cls, v):
        """Validates that the expiration date is in the future."""
        if v is None:
            return None
        if v < datetime.now():
            raise ValueError('expires_at must be in the future')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "rate_limit": 120,
                "active": True,
                "expires_at": (datetime.now() + timedelta(days=90)).isoformat()
            }
        }
    }


class ApiKeyInDB(BaseModel):
    """Schema representing API key data as stored in the database."""
    
    key_id: str = Field(..., description="Unique identifier for the API key")
    client_id: str = Field(..., description="Unique identifier for the client/broker")
    rate_limit: int = Field(..., description="Maximum number of API requests allowed per minute")
    created_at: datetime = Field(..., description="Timestamp when the API key was created")
    expires_at: Optional[datetime] = Field(None, description="Timestamp when the API key will expire")
    active: bool = Field(..., description="Whether the API key is active")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "key_id": "abc123",
                "client_id": "broker_123",
                "rate_limit": 60,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=90)).isoformat(),
                "active": True
            }
        }
    }


class ApiKeyResponse(BaseModel):
    """Schema for API key data returned to clients."""
    
    key_id: str = Field(..., description="Unique identifier for the API key")
    client_id: str = Field(..., description="Unique identifier for the client/broker")
    rate_limit: int = Field(..., description="Maximum number of API requests allowed per minute")
    created_at: datetime = Field(..., description="Timestamp when the API key was created")
    expires_at: Optional[datetime] = Field(None, description="Timestamp when the API key will expire")
    active: bool = Field(..., description="Whether the API key is active")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "key_id": "abc123",
                "client_id": "broker_123",
                "rate_limit": 60,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=90)).isoformat(),
                "active": True
            }
        }
    }


class ApiKeyWithSecret(ApiKeyResponse):
    """Schema for API key response that includes the plaintext secret key."""
    
    api_key: str = Field(..., description="The plaintext API key that should be kept secret")
    
    @validator('api_key')
    def validate_api_key(cls, v):
        """Validates that the API key is in the correct format."""
        if not v:
            raise ValueError('api_key cannot be empty')
        if not API_KEY_PATTERN.match(v):
            raise ValueError('api_key must be 32-64 characters of letters, numbers, underscores or hyphens')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "key_id": "abc123",
                "client_id": "broker_123",
                "rate_limit": 60,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=90)).isoformat(),
                "active": True,
                "api_key": "abcdef1234567890abcdef1234567890abcdef12"
            }
        }
    }