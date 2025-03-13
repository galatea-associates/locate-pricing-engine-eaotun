"""
Provides test fixtures for stock data used in unit and integration tests for the 
Borrow Rate & Locate Fee Pricing Engine.

These fixtures include sample stocks with various borrow statuses, minimum rates, 
and other attributes to test different calculation scenarios.
"""

import pytest
from decimal import Decimal  # standard library
from datetime import datetime  # standard library

from ...core.constants import BorrowStatus
from ...schemas.stock import StockSchema, StockCreate

# Sample stock data for testing
STOCK_FIXTURES = [
    {
        "ticker": "AAPL",
        "borrow_status": BorrowStatus.EASY,
        "lender_api_id": "SEC_AAPL_001",
        "min_borrow_rate": Decimal('0.01'),
        "last_updated": datetime.now()
    },
    {
        "ticker": "GME",
        "borrow_status": BorrowStatus.HARD,
        "lender_api_id": "SEC_GME_001",
        "min_borrow_rate": Decimal('0.25'),
        "last_updated": datetime.now()
    },
    {
        "ticker": "MSFT",
        "borrow_status": BorrowStatus.EASY,
        "lender_api_id": "SEC_MSFT_001",
        "min_borrow_rate": Decimal('0.01'),
        "last_updated": datetime.now()
    },
    {
        "ticker": "TSLA",
        "borrow_status": BorrowStatus.MEDIUM,
        "lender_api_id": "SEC_TSLA_001",
        "min_borrow_rate": Decimal('0.05'),
        "last_updated": datetime.now()
    },
    {
        "ticker": "AMC",
        "borrow_status": BorrowStatus.HARD,
        "lender_api_id": "SEC_AMC_001",
        "min_borrow_rate": Decimal('0.30'),
        "last_updated": datetime.now()
    }
]


@pytest.fixture
def stock_data():
    """
    Pytest fixture that provides a list of sample stock data for testing.
    
    Returns:
        list: List of dictionaries containing stock data
    """
    # Return a copy to prevent test side effects
    return STOCK_FIXTURES.copy()


@pytest.fixture
def easy_to_borrow_stock():
    """
    Pytest fixture that provides a sample easy-to-borrow stock.
    
    Returns:
        dict: Dictionary with stock data for an easy-to-borrow stock
    """
    # Find the first stock with EASY borrow status
    for stock in STOCK_FIXTURES:
        if stock["borrow_status"] == BorrowStatus.EASY:
            return stock.copy()
    
    # Fallback if no EASY stocks found (shouldn't happen with our data)
    return STOCK_FIXTURES[0].copy()


@pytest.fixture
def hard_to_borrow_stock():
    """
    Pytest fixture that provides a sample hard-to-borrow stock.
    
    Returns:
        dict: Dictionary with stock data for a hard-to-borrow stock
    """
    # Find the first stock with HARD borrow status
    for stock in STOCK_FIXTURES:
        if stock["borrow_status"] == BorrowStatus.HARD:
            return stock.copy()
    
    # Fallback if no HARD stocks found (shouldn't happen with our data)
    return STOCK_FIXTURES[1].copy()


@pytest.fixture
def medium_to_borrow_stock():
    """
    Pytest fixture that provides a sample medium-to-borrow stock.
    
    Returns:
        dict: Dictionary with stock data for a medium-to-borrow stock
    """
    # Find the first stock with MEDIUM borrow status
    for stock in STOCK_FIXTURES:
        if stock["borrow_status"] == BorrowStatus.MEDIUM:
            return stock.copy()
    
    # Fallback if no MEDIUM stocks found (shouldn't happen with our data)
    return STOCK_FIXTURES[3].copy()


@pytest.fixture
def high_min_rate_stock():
    """
    Pytest fixture that provides a stock with a high minimum borrow rate.
    
    Returns:
        dict: Dictionary with stock data having a high minimum borrow rate
    """
    # Find the stock with the highest min_borrow_rate
    return max(STOCK_FIXTURES, key=lambda s: s["min_borrow_rate"]).copy()


@pytest.fixture
def low_min_rate_stock():
    """
    Pytest fixture that provides a stock with a low minimum borrow rate.
    
    Returns:
        dict: Dictionary with stock data having a low minimum borrow rate
    """
    # Find the stock with the lowest min_borrow_rate
    return min(STOCK_FIXTURES, key=lambda s: s["min_borrow_rate"]).copy()


@pytest.fixture
def invalid_ticker():
    """
    Pytest fixture that provides an invalid ticker for testing error handling.
    
    Returns:
        str: Invalid ticker symbol
    """
    return "INVALID"  # Invalid ticker that doesn't exist in our system


@pytest.fixture
def stock_with_volatility():
    """
    Pytest fixture that provides a stock that has corresponding volatility data.
    
    Returns:
        dict: Dictionary with stock data that has volatility metrics
    """
    # For testing purposes, we'll assume TSLA has volatility data available
    for stock in STOCK_FIXTURES:
        if stock["ticker"] == "TSLA":
            return stock.copy()
    
    # Fallback if TSLA not found (shouldn't happen with our data)
    return STOCK_FIXTURES[3].copy()


@pytest.fixture
def stock_schemas():
    """
    Pytest fixture that provides a list of StockSchema objects for testing.
    
    Returns:
        list: List of StockSchema objects
    """
    return [StockSchema(**stock) for stock in STOCK_FIXTURES]


@pytest.fixture
def stock_create_objects():
    """
    Pytest fixture that provides a list of StockCreate objects for testing.
    
    Returns:
        list: List of StockCreate objects
    """
    create_objects = []
    for stock in STOCK_FIXTURES:
        # StockCreate doesn't have last_updated field
        stock_data = {k: v for k, v in stock.items() if k != "last_updated"}
        create_objects.append(StockCreate(**stock_data))
    
    return create_objects