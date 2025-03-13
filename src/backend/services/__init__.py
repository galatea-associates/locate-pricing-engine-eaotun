"""
Initialization module for the services package in the Borrow Rate & Locate Fee Pricing Engine.
This module serves as a central entry point for accessing all service components, including calculation services, data services, external API clients, caching services, and audit logging. It provides a clean, unified interface for other parts of the application to access these services without needing to import from specific submodules.
"""
import logging  # package_version: standard library; For logging module initialization

# Internal imports
from .calculation import *  # Import all calculation service components for borrow rates and locate fees
from .data import *  # Import all data service components for stocks, brokers, and volatility
from .external import *  # Import all external API client components
from .cache import *  # Import all cache service components
from .audit import *  # Import all audit service components
from ..core.logging import get_logger  # Import logging functionality

# Initialize logger
logger = get_logger(__name__)

# Version of the service
__version__ = "1.0.0"

# Exported items
__all__ = [
    # Calculation service exports
    "calculate_borrow_rate",  # Calculate borrow rate with volatility and event risk adjustments
    "calculate_locate_fee",  # Calculate total locate fee including base cost, markup, and transaction fees
    "get_real_time_borrow_rate",  # Get real-time borrow rate from external API
    "get_fallback_borrow_rate",  # Get fallback borrow rate when external API is unavailable
    
    # Data service exports
    "StockService",  # Service for stock data operations
    "stock_service",  # Singleton instance of StockService
    "BrokerService",  # Service for broker data operations
    "broker_service",  # Singleton instance of BrokerService
    "VolatilityService",  # Service for volatility data operations
    "volatility_service",  # Singleton instance of VolatilityService
    
    # External API client exports
    "get_borrow_rate",  # Get borrow rate from SecLend API
    "get_market_volatility",  # Get market volatility index from Market Volatility API
    "get_event_risk_factor",  # Get event risk factor from Event Calendar API
    
    # Cache service exports
    "get_cache_strategy",  # Get configured cache strategy
    "get_redis_cache",  # Get Redis cache instance
    "get_local_cache",  # Get local cache instance
    
    # Audit service exports
    "AuditLogger",  # Service for logging audit events
    "TransactionAuditor", # Service for auditing and analyzing fee calculations
    
    # Additional audit service exports
    "create_calculation_audit",
    "get_audit_record",
    "filter_audit_records",
    "get_client_audit_records",
    "get_ticker_audit_records",
    "get_fallback_audit_records",
    "get_audit_records_by_date_range",
    
    # Data service base class
    "DataServiceBase",
    
    # Validation utilities
    "validate_ticker",
    "validate_client_id",
    
    # Caching utilities
    "cache_result",
    "get_cache_key",
    
    # Default cache TTL
    "DEFAULT_CACHE_TTL",
]