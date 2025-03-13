"""
Base model definitions for the Borrow Rate & Locate Fee Pricing Engine.

This module defines the SQLAlchemy declarative base and base model class that provides
common functionality for all database models, such as primary key generation,
timestamp tracking, and serialization methods.
"""

from datetime import datetime
from typing import Dict, Any, Optional, Type
from sqlalchemy import Column, Integer, DateTime, func  # sqlalchemy v2.0.0+
from sqlalchemy.orm import declarative_base, as_declarative, declared_attr  # sqlalchemy v2.0.0+

# Create the SQLAlchemy declarative base
Base = declarative_base()

@as_declarative()
class BaseModel:
    """
    Base model class that provides common functionality for all database models.
    
    All models in the application should inherit from this class to get:
    - Automatic primary key (id)
    - Creation and update timestamps
    - Serialization methods (to_dict, from_dict)
    - Table name generation from class name
    """
    
    # Primary key for all models
    id = Column(Integer, primary_key=True, index=True)
    
    # Timestamps for auditing
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    def __init__(self, **kwargs):
        """
        Initialize a model instance with provided attributes.
        
        Args:
            **kwargs: Any model attributes to set during initialization.
        """
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model instance to dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary with model attributes.
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Handle datetime conversion to ISO format for JSON serialization
            if isinstance(value, datetime):
                value = value.isoformat()
                
            result[column.name] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseModel":
        """
        Create or update a model instance from a dictionary.
        
        Args:
            data: Dictionary containing model attributes.
            
        Returns:
            Instance of the model with values set from the dictionary.
        """
        instance = cls()
        for column in instance.__table__.columns:
            if column.name in data:
                setattr(instance, column.name, data[column.name])
        return instance
    
    @declared_attr
    @classmethod
    def __tablename__(cls) -> str:
        """
        Generate table name from class name.
        
        Returns:
            str: Lowercase class name as table name.
        """
        return cls.__name__.lower()