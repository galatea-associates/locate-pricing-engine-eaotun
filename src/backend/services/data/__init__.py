"""
Initialization module for the data services package in the Borrow Rate & Locate Fee Pricing Engine.
This module exports service classes and instances that provide high-level data access and business logic for stocks, brokers, volatility metrics, and audit logging. It serves as the main entry point for other components to access data-related functionality.
"""

# Internal imports
from .stocks import StockService  # Import stock data service for managing stock information and borrow rates
from .stocks import stock_service  # Import singleton instance of StockService
from .brokers import BrokerService  # Import broker data service for managing broker configurations
from .brokers import broker_service  # Import singleton instance of BrokerService
from .volatility import VolatilityService  # Import volatility data service for managing volatility metrics
from .volatility import volatility_service  # Import singleton instance of VolatilityService
from .audit import create_calculation_audit  # Import function to create audit logs for calculations
from .audit import get_audit_record  # Import function to retrieve audit records
from .audit import filter_audit_records  # Import function to filter audit records
from .audit import get_client_audit_records  # Import function to get audit records for a client
from .audit import get_ticker_audit_records  # Import function to get audit records for a ticker
from .audit import get_fallback_audit_records  # Import function to get audit records for fallback events
from .audit import get_audit_records_by_date_range  # Import function to get audit records by date range
from .utils import DataServiceBase  # Import base class for data services
from .utils import validate_ticker  # Import function to validate ticker symbols
from .utils import validate_client_id  # Import function to validate client IDs
from .utils import cache_result  # Import decorator for caching function results
from .utils import get_cache_key  # Import function to generate cache keys
from .utils import DEFAULT_CACHE_TTL  # Import default cache TTL constant

# Global instances
volatility_service = VolatilityService()

# Exported items
__all__ = [
    "StockService",
    "stock_service",
    "BrokerService",
    "broker_service",
    "VolatilityService",
    "volatility_service",
    "create_calculation_audit",
    "get_audit_record",
    "filter_audit_records",
    "get_client_audit_records",
    "get_ticker_audit_records",
    "get_fallback_audit_records",
    "get_audit_records_by_date_range",
    "DataServiceBase",
    "validate_ticker",
    "validate_client_id",
    "cache_result",
    "get_cache_key",
    "DEFAULT_CACHE_TTL",
]