"""
SQLAlchemy ORM model for API keys in the Borrow Rate & Locate Fee Pricing Engine.

This module defines the API key model which is used for authenticating client requests,
enforcing rate limits, and managing API key lifecycle including expiration
and validation.
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Index  # sqlalchemy v2.0.0+
from sqlalchemy.orm import relationship  # sqlalchemy v2.0.0+

from .base import Base, BaseModel
from ...core.constants import API_KEY_EXPIRY_DAYS


class APIKey(BaseModel):
    """
    SQLAlchemy ORM model for API key data in the database.
    
    This model represents the API keys used for authentication and rate limiting.
    It tracks the key identifier, associated client, rate limits, expiration date,
    and active status.
    """
    
    # Primary key and identifier for the API key
    key_id = Column(String(64), primary_key=True, index=True)
    
    # Reference to the associated broker/client
    client_id = Column(String(50), ForeignKey('broker.client_id'), nullable=False, index=True)
    
    # Number of requests allowed per minute
    rate_limit = Column(Integer, nullable=False, default=60)
    
    # When the API key expires
    expires_at = Column(DateTime, nullable=True)
    
    # Whether the key is currently active
    active = Column(Boolean, nullable=False, default=True)
    
    # Securely stored hash of the actual API key
    hashed_key = Column(String(128), nullable=False)
    
    # Relationship to the Broker model
    broker = relationship('Broker', back_populates='api_keys')
    
    def __init__(self, **kwargs):
        """
        Initialize a new API key record.
        
        Args:
            **kwargs: Keyword arguments for setting model attributes.
        """
        super().__init__(**kwargs)
        
        # Set default expiration date if not provided
        if not self.expires_at and API_KEY_EXPIRY_DAYS > 0:
            self.expires_at = datetime.now() + timedelta(days=API_KEY_EXPIRY_DAYS)
    
    def __repr__(self):
        """
        String representation of the API key for debugging purposes.
        
        Returns:
            str: String representation of the API key.
        """
        return f"APIKey(key_id={self.key_id[:8]}..., client_id={self.client_id})"
    
    def is_valid(self):
        """
        Check if the API key is valid (active and not expired).
        
        Returns:
            bool: True if the key is valid, False otherwise.
        """
        if not self.active:
            return False
            
        return not self.is_expired()
    
    def is_expired(self):
        """
        Check if the API key has expired.
        
        Returns:
            bool: True if the key is expired, False otherwise.
        """
        # If expires_at is None, the key never expires
        if self.expires_at is None:
            return False
            
        return datetime.now() > self.expires_at
    
    def extend_expiration(self, days):
        """
        Extend the expiration date of the API key.
        
        Args:
            days (int): Number of days to extend the expiration.
            
        Returns:
            datetime: The new expiration date.
        """
        # If no current expiration, start from now
        if self.expires_at is None:
            self.expires_at = datetime.now()
            
        # Add the specified number of days
        self.expires_at = self.expires_at + timedelta(days=days)
        return self.expires_at


# Create indexes for performance optimization
Index('ix_api_key_client_id', APIKey.client_id)
Index('ix_api_key_active', APIKey.active)