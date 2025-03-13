"""
Database models package for the Borrow Rate & Locate Fee Pricing Engine.

This package contains all SQLAlchemy ORM models for the pricing engine's database.
This __init__.py file serves as a central import point for all models, simplifying
imports throughout the application and ensuring proper model registration with SQLAlchemy.
"""

# Import base classes and utilities
from .base import Base, BaseModel

# Import model classes
from .stock import Stock
from .broker import Broker
from .volatility import Volatility, idx_volatility_stock, idx_volatility_date
from .api_key import APIKey
from .audit import AuditLog

# Import or define utility functions
try:
    from .base import generate_uuid
except ImportError:
    import uuid
    def generate_uuid():
        """Generate a new UUID for use as a primary key."""
        return uuid.uuid4()

# Import or define audit indexes
try:
    from .audit import idx_audit_client, idx_audit_ticker, idx_audit_time
except ImportError:
    from sqlalchemy import Index
    # Create indexes with names matching the specification
    idx_audit_client = Index('idx_audit_client', 'client_id')
    idx_audit_ticker = Index('idx_audit_ticker', 'ticker')
    idx_audit_time = Index('idx_audit_time', 'timestamp')

# Re-export all models and utilities
__all__ = [
    # Base classes
    'Base', 
    'BaseModel',
    
    # Models
    'Stock', 
    'Broker', 
    'Volatility', 
    'APIKey', 
    'AuditLog',
    
    # Indexes
    'idx_volatility_stock',
    'idx_volatility_date',
    'idx_audit_client',
    'idx_audit_ticker',
    'idx_audit_time',
    
    # Utilities
    'generate_uuid',
]