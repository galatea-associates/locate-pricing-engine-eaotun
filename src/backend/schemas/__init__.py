"""
Initialization file for the schemas package that exports all Pydantic models used for data validation,
serialization, and documentation in the Borrow Rate & Locate Fee Pricing Engine.

This file provides a centralized import interface for all schema models, simplifying imports
throughout the application by allowing users to import directly from the schemas package
rather than from individual schema modules.
"""

# Import error response schemas
from .error import ErrorResponse, ValidationError

# Import request schemas
from .request import CalculateLocateRequest, GetRateRequest

# Import response schemas
from .response import (
    BaseResponse,
    CalculateLocateResponse, 
    BorrowRateResponse,
    HealthResponse
)

# Import stock data schemas
from .stock import (
    StockBase,
    StockSchema,
    StockCreate,
    StockUpdate,
    StockInDB,
    RateResponse
)

# Import broker data schemas
from .broker import (
    BrokerBase,
    BrokerSchema,
    BrokerCreate,
    BrokerUpdate,
    BrokerInDB
)

# Import volatility data schemas
from .volatility import (
    VolatilityBase,
    VolatilitySchema,
    VolatilityCreate,
    VolatilityUpdate,
    VolatilityInDB,
    VolatilityResponse,
    MarketVolatilityResponse,
    EventRiskResponse,
    EventSchema
)

# Import API key schemas
from .api_key import (
    ApiKeySchema,
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyUpdate,
    ApiKeyInDB
)

# Import audit log schemas
from .audit import (
    DataSourceSchema,
    CalculationBreakdownSchema,
    AuditLogSchema,
    AuditLogFilterSchema,
    AuditLogResponseSchema
)

# Import calculation schemas
from .calculation import (
    CalculationBase,
    FeeBreakdownSchema,
    CalculationSchema,
    CalculationCreate,
    CalculationInDB,
    BorrowRateCalculationSchema
)

# Export all models
__all__ = [
    # Error schemas
    "ErrorResponse",
    "ValidationError",
    
    # Request schemas
    "CalculateLocateRequest",
    "GetRateRequest",
    
    # Response schemas
    "BaseResponse",
    "CalculateLocateResponse",
    "BorrowRateResponse",
    "HealthResponse",
    
    # Stock schemas
    "StockBase",
    "StockSchema",
    "StockCreate",
    "StockUpdate",
    "StockInDB",
    "RateResponse",
    
    # Broker schemas
    "BrokerBase",
    "BrokerSchema",
    "BrokerCreate",
    "BrokerUpdate",
    "BrokerInDB",
    
    # Volatility schemas
    "VolatilityBase",
    "VolatilitySchema",
    "VolatilityCreate",
    "VolatilityUpdate",
    "VolatilityInDB",
    "VolatilityResponse",
    "MarketVolatilityResponse",
    "EventRiskResponse",
    "EventSchema",
    
    # API key schemas
    "ApiKeySchema",
    "ApiKeyCreate",
    "ApiKeyResponse",
    "ApiKeyUpdate",
    "ApiKeyInDB",
    
    # Audit schemas
    "DataSourceSchema",
    "CalculationBreakdownSchema",
    "AuditLogSchema",
    "AuditLogFilterSchema",
    "AuditLogResponseSchema",
    
    # Calculation schemas
    "CalculationBase",
    "FeeBreakdownSchema",
    "CalculationSchema",
    "CalculationCreate",
    "CalculationInDB",
    "BorrowRateCalculationSchema"
]