"""
Initializes the fixtures package for the Borrow Rate & Locate Fee Pricing Engine tests.

This module exports all test fixtures from the package's modules, making them available
to test files throughout the application without requiring individual imports from
each fixture module.
"""

# Import fixtures from stocks module
from .stocks import (
    stock_data,
    easy_to_borrow_stock,
    hard_to_borrow_stock,
    medium_to_borrow_stock,
    invalid_ticker,
    stock_with_volatility,
    stock_schemas,
    stock_create_objects
)

# Import fixtures from brokers module
from .brokers import (
    broker_data,
    standard_broker,
    premium_broker,
    high_markup_broker,
    inactive_broker,
    invalid_client_id,
    broker_schemas,
    broker_create_objects
)

# Import fixtures from volatility module
from .volatility import (
    volatility_data,
    low_volatility_data,
    high_volatility_data,
    extreme_volatility_data,
    low_event_risk_data,
    high_event_risk_data,
    market_volatility_data,
    current_market_volatility,
    event_risk_data,
    stock_with_upcoming_earnings,
    volatility_schemas,
    mock_market_volatility_response,
    mock_event_risk_response
)

# Import fixtures from api_responses module
from .api_responses import (
    mock_seclend_response,
    mock_seclend_batch_response,
    mock_stock_volatility_response,
    mock_event_calendar_response,
    mock_api_error_response,
    mock_high_volatility_response,
    mock_low_volatility_response,
    mock_high_event_risk_response,
    mock_no_event_risk_response
)

# All fixtures are exported directly from this module
__all__ = [
    # Stock fixtures
    'stock_data',
    'easy_to_borrow_stock',
    'hard_to_borrow_stock',
    'medium_to_borrow_stock',
    'invalid_ticker',
    'stock_with_volatility',
    'stock_schemas',
    'stock_create_objects',
    
    # Broker fixtures
    'broker_data',
    'standard_broker',
    'premium_broker',
    'high_markup_broker',
    'inactive_broker',
    'invalid_client_id',
    'broker_schemas',
    'broker_create_objects',
    
    # Volatility and event risk fixtures
    'volatility_data',
    'low_volatility_data',
    'high_volatility_data',
    'extreme_volatility_data',
    'low_event_risk_data',
    'high_event_risk_data',
    'market_volatility_data',
    'current_market_volatility',
    'event_risk_data',
    'stock_with_upcoming_earnings',
    'volatility_schemas',
    'mock_market_volatility_response',
    'mock_event_risk_response',
    
    # External API mock response fixtures
    'mock_seclend_response',
    'mock_seclend_batch_response',
    'mock_stock_volatility_response',
    'mock_event_calendar_response',
    'mock_api_error_response',
    'mock_high_volatility_response',
    'mock_low_volatility_response',
    'mock_high_event_risk_response',
    'mock_no_event_risk_response'
]