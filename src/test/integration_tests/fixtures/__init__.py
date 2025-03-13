"""
Initializes the fixtures package for integration tests, exposing all test fixtures for
stocks, brokers, volatility data, and API responses to be used across integration tests
for the Borrow Rate & Locate Fee Pricing Engine.
"""

import pytest  # version: 7.4.0+
from decimal import Decimal  # version: standard library
from typing import Dict, Any, Optional  # version: standard library

# Import API response fixtures
from .api_responses import (
    SECLEND_API_RESPONSES,
    MARKET_API_RESPONSES, 
    EVENT_API_RESPONSES,
    CALCULATION_API_RESPONSES,
    ERROR_RESPONSES,
    generate_seclend_response,
    generate_market_volatility_response,
    generate_event_response,
    generate_calculation_response
)

# Import stock data fixtures
from .stocks import (
    stock_data,
    easy_to_borrow_stock,
    hard_to_borrow_stock,
    medium_to_borrow_stock,
    invalid_ticker,
    get_stock_by_ticker,
    generate_stock_with_custom_rate,
    TEST_STOCKS
)

# Import broker data fixtures
from .brokers import (
    broker_data,
    standard_broker,
    premium_broker,
    high_markup_broker,
    inactive_broker,
    invalid_client_id,
    get_broker_by_client_id,
    generate_broker_with_custom_markup,
    TEST_BROKERS
)

# Import volatility data fixtures
from .volatility import (
    volatility_data,
    market_volatility,
    event_risk_data,
    low_volatility_data,
    medium_volatility_data,
    high_volatility_data,
    get_volatility_by_stock_id,
    generate_volatility_with_custom_values,
    TEST_VOLATILITY_DATA,
    MARKET_VOLATILITY_DATA
)

# Create additional fixtures that were specified but not defined in the imported modules

@pytest.fixture
def stock_with_volatility() -> Dict[str, Any]:
    """
    Pytest fixture providing stock data with volatility information.
    
    Returns:
        Dict[str, Any]: Dictionary with stock data that has volatility information
    """
    # Use the TSLA stock which has medium volatility in our test data
    stock = get_stock_by_ticker("TSLA")
    vol_data = get_volatility_by_stock_id("TSLA")
    
    # Combine the data for convenience
    result = stock.copy()
    result["volatility_index"] = vol_data["vol_index"]
    result["event_risk_factor"] = vol_data["event_risk_factor"]
    
    return result

@pytest.fixture
def stock_with_high_volatility() -> Dict[str, Any]:
    """
    Pytest fixture providing stock data with high volatility.
    
    Returns:
        Dict[str, Any]: Dictionary with stock data that has high volatility
    """
    # Use the GME stock which has high volatility in our test data
    stock = get_stock_by_ticker("GME")
    vol_data = get_volatility_by_stock_id("GME")
    
    # Combine the data for convenience
    result = stock.copy()
    result["volatility_index"] = vol_data["vol_index"]
    result["event_risk_factor"] = vol_data["event_risk_factor"]
    
    return result

@pytest.fixture
def stock_with_event_risk() -> Dict[str, Any]:
    """
    Pytest fixture providing stock data with significant event risk.
    
    Returns:
        Dict[str, Any]: Dictionary with stock data that has significant event risk
    """
    # Use the GME stock which has high event risk in our test data
    stock = get_stock_by_ticker("GME")
    vol_data = get_volatility_by_stock_id("GME")
    
    # Ensure the event risk factor is high
    result = stock.copy()
    result["volatility_index"] = vol_data["vol_index"]
    result["event_risk_factor"] = vol_data["event_risk_factor"]
    
    return result

@pytest.fixture
def extreme_volatility_data() -> Dict[str, Any]:
    """
    Pytest fixture providing data for an extremely volatile stock.
    
    Returns:
        Dict[str, Any]: Dictionary with volatility data for an extremely volatile stock
    """
    # Create extreme volatility data based on GME but with even higher volatility
    extreme_data = get_volatility_by_stock_id("GME").copy()
    extreme_data["vol_index"] = Decimal("65.0")  # Extremely high volatility
    return extreme_data

@pytest.fixture
def high_event_risk_data() -> Dict[str, Any]:
    """
    Pytest fixture providing data for a stock with high event risk.
    
    Returns:
        Dict[str, Any]: Dictionary with data for a stock with high event risk
    """
    # Create high event risk data based on GME
    high_risk_data = get_volatility_by_stock_id("GME").copy()
    high_risk_data["event_risk_factor"] = 9  # Very high event risk
    return high_risk_data

# Function aliases for compatibility
def get_volatility_by_ticker(ticker: str) -> Dict[str, Any]:
    """
    Helper function to retrieve volatility data by ticker symbol.
    
    Args:
        ticker (str): The ticker symbol to search for
        
    Returns:
        Dict[str, Any]: Volatility data dictionary or None if not found
    """
    return get_volatility_by_stock_id(ticker)

def generate_custom_volatility_data(
    ticker: str, 
    vol_index: Decimal, 
    event_risk_factor: int
) -> Dict[str, Any]:
    """
    Generate custom volatility data for specific test scenarios.
    
    Args:
        ticker (str): The ticker symbol for the stock
        vol_index (Decimal): The volatility index value
        event_risk_factor (int): The event risk factor value
        
    Returns:
        Dict[str, Any]: Custom volatility data with specified parameters
    """
    return generate_volatility_with_custom_values(ticker, vol_index, event_risk_factor)

# Export all fixtures and helpers for use in tests
__all__ = [
    # API response fixtures
    "SECLEND_API_RESPONSES",
    "MARKET_API_RESPONSES",
    "EVENT_API_RESPONSES",
    "CALCULATION_API_RESPONSES",
    "ERROR_RESPONSES",
    "generate_seclend_response",
    "generate_market_volatility_response",
    "generate_event_response",
    "generate_calculation_response",
    
    # Stock fixtures
    "stock_data",
    "easy_to_borrow_stock",
    "hard_to_borrow_stock",
    "medium_to_borrow_stock",
    "invalid_ticker",
    "stock_with_volatility",
    "stock_with_high_volatility",
    "stock_with_event_risk",
    "get_stock_by_ticker",
    "generate_stock_with_custom_rate",
    "TEST_STOCKS",
    
    # Broker fixtures
    "broker_data",
    "standard_broker",
    "premium_broker",
    "high_markup_broker",
    "inactive_broker",
    "invalid_client_id",
    "get_broker_by_client_id",
    "generate_broker_with_custom_markup",
    "TEST_BROKERS",
    
    # Volatility fixtures
    "volatility_data",
    "market_volatility",
    "event_risk_data",
    "low_volatility_data",
    "medium_volatility_data",
    "high_volatility_data",
    "extreme_volatility_data",
    "high_event_risk_data",
    "get_volatility_by_ticker",
    "generate_custom_volatility_data",
    "TEST_VOLATILITY_DATA",
    "MARKET_VOLATILITY_DATA"
]