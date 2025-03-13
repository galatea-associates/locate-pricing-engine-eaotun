"""
Initializes the CRUD (Create, Read, Update, Delete) operations module for the Borrow Rate & Locate Fee Pricing Engine.

This file exports all CRUD classes and their singleton instances to provide a clean API 
for database operations throughout the application.
"""

# Base CRUD class
from .base import CRUDBase

# Stock CRUD operations
from .stocks import CRUDStock, stock

# Broker CRUD operations
from .brokers import CRUDBroker, broker_crud as broker

# Volatility CRUD operations
from .volatility import CRUDVolatility, volatility

# API Key CRUD operations
from .api_keys import CRUDAPIKey, api_key_crud as api_keys

# Audit CRUD operations
from .audit import CRUDAudit, audit

# Export all CRUD classes and instances
__all__ = [
    "CRUDBase",
    "CRUDStock", "stock",
    "CRUDBroker", "broker",
    "CRUDVolatility", "volatility", 
    "CRUDAPIKey", "api_keys",
    "CRUDAudit", "audit"
]