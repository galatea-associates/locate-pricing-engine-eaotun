"""
Volatility model for the Borrow Rate & Locate Fee Pricing Engine.

This module defines the SQLAlchemy ORM model for volatility data, which represents
time-series volatility metrics and event risk factors for stocks. These metrics
are used to adjust borrow rates based on market conditions and upcoming events.
"""

from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, func, Index  # sqlalchemy v2.0.0+
from sqlalchemy.orm import relationship  # sqlalchemy v2.0.0+
from .base import Base, BaseModel

# Define indexes for the Volatility table for efficient queries
idx_volatility_stock = Index('idx_volatility_stock', 'stock_id')
idx_volatility_time = Index('idx_volatility_time', 'timestamp')
idx_volatility_stock_time = Index('idx_volatility_stock_time', 'stock_id', 'timestamp')


class Volatility(Base):
    """
    SQLAlchemy ORM model representing volatility and event risk data for a stock.
    
    This model stores time-series data for volatility metrics and event risk factors,
    which are used to adjust borrow rates based on market conditions and upcoming events.
    """
    __tablename__ = 'volatility'
    
    # Foreign key to the Stock model - part of a composite primary key
    stock_id = Column(String(10), ForeignKey('stock.ticker'), primary_key=True, index=True)
    
    # Volatility index (typically a value like VIX)
    vol_index = Column(Numeric(5, 2), nullable=False)
    
    # Risk factor for upcoming events (0-10 scale)
    event_risk_factor = Column(Integer, nullable=False, default=0)
    
    # Timestamp for the volatility data point - part of a composite primary key for time-series
    timestamp = Column(DateTime, nullable=False, server_default=func.now(), primary_key=True, index=True)
    
    # Relationship to the Stock model
    stock = relationship('Stock', back_populates='volatility_data')
    
    def __init__(self, **kwargs):
        """
        Default constructor for the Volatility model.
        
        Args:
            **kwargs: Any model attributes to set
        """
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __repr__(self):
        """
        String representation of the Volatility instance.
        
        Returns:
            str: String representation with stock_id, vol_index, and event_risk_factor
        """
        return f"Volatility(stock_id={self.stock_id}, vol_index={self.vol_index}, event_risk_factor={self.event_risk_factor})"
    
    def to_dict(self):
        """
        Convert the model to a dictionary.
        
        Returns:
            dict: Dictionary representation of the model.
        """
        from datetime import datetime
        
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Handle datetime conversion for JSON serialization
            if isinstance(value, datetime):
                value = value.isoformat()
                
            result[column.name] = value
        return result
    
    @classmethod
    def from_dict(cls, data):
        """
        Create a model instance from a dictionary.
        
        Args:
            data (dict): Dictionary containing model data.
            
        Returns:
            Volatility: Instance created from the dictionary.
        """
        instance = cls()
        for column in instance.__table__.columns:
            if column.name in data:
                setattr(instance, column.name, data[column.name])
        return instance