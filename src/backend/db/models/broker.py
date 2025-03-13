"""
Broker model for the Borrow Rate & Locate Fee Pricing Engine.

Defines the SQLAlchemy ORM model for broker data, storing configurations 
for client-specific fee calculations including markup percentages and 
transaction fee structures.
"""

from sqlalchemy import Column, String, Numeric, Boolean, Enum, DateTime, func, Index  # sqlalchemy v2.0.0+
from .base import Base, BaseModel
from ...core.constants import TransactionFeeType


class Broker(BaseModel):
    """
    SQLAlchemy ORM model for broker data in the database.
    
    This model stores broker-specific configuration data used for calculating
    client fees, including markup percentages and transaction fee structures.
    It corresponds to the 'broker' table in the database.
    """
    
    # Override the primary key to use client_id instead of the id from BaseModel
    __tablename__ = 'broker'
    
    # Primary identifier for the broker (typically a client code)
    client_id = Column(String(50), primary_key=True, index=True)
    
    # Percentage markup over base borrow rate (stored as decimal, e.g., 5.0 for 5%)
    markup_percentage = Column(Numeric(5, 2), nullable=False)
    
    # Fee calculation method (FLAT or PERCENTAGE)
    transaction_fee_type = Column(Enum(TransactionFeeType), nullable=False)
    
    # Fee amount - interpretation depends on transaction_fee_type
    # For FLAT: dollar amount (e.g., $25.00)
    # For PERCENTAGE: percentage value (e.g., 0.5 for 0.5%)
    transaction_amount = Column(Numeric(10, 2), nullable=False)
    
    # Whether this broker configuration is currently active
    active = Column(Boolean, nullable=False, default=True)
    
    # Timestamp of last update to this configuration
    last_updated = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Create an index on active status for efficient queries of active brokers
    __table_args__ = (
        Index('idx_broker_active', 'active'),
    )
    
    def __init__(self, **kwargs):
        """
        Initialize a Broker instance with provided attributes.
        
        Args:
            **kwargs: Any model attributes to set during initialization.
                     These can include client_id, markup_percentage,
                     transaction_fee_type, transaction_amount, and active.
        """
        # Call the parent constructor to handle common fields
        super().__init__(**kwargs)
    
    def __repr__(self):
        """
        String representation of the Broker instance.
        
        Returns:
            str: A string showing the broker's client_id and markup_percentage.
        """
        return f"Broker(client_id='{self.client_id}', markup_percentage={self.markup_percentage})"