"""
Provides test fixtures for stock data used in integration tests for the Borrow Rate & Locate Fee Pricing Engine.
These fixtures include sample stocks with various borrow statuses, rates, and characteristics to test different
calculation scenarios and API interactions.
"""
import pytest
from decimal import Decimal
import datetime
from typing import Dict, List, Any

from ...backend.core.constants import BorrowStatus

# Current timestamp for consistent datetime values across fixtures
CURRENT_TIMESTAMP = datetime.datetime.now().isoformat()

# Test stock data collection with various borrow statuses and rates
TEST_STOCKS = [
    {
        'ticker': 'AAPL',
        'borrow_status': BorrowStatus.EASY,
        'lender_api_id': 'SEC123',
        'min_borrow_rate': Decimal('0.01'),
        'last_updated': datetime.datetime.now()
    },
    {
        'ticker': 'TSLA',
        'borrow_status': BorrowStatus.MEDIUM,
        'lender_api_id': 'SEC456',
        'min_borrow_rate': Decimal('0.05'),
        'last_updated': datetime.datetime.now()
    },
    {
        'ticker': 'GME',
        'borrow_status': BorrowStatus.HARD,
        'lender_api_id': 'SEC789',
        'min_borrow_rate': Decimal('0.15'),
        'last_updated': datetime.datetime.now()
    },
    {
        'ticker': 'MSFT',
        'borrow_status': BorrowStatus.EASY,
        'lender_api_id': 'SEC234',
        'min_borrow_rate': Decimal('0.01'),
        'last_updated': datetime.datetime.now()
    },
    {
        'ticker': 'AMC',
        'borrow_status': BorrowStatus.HARD,
        'lender_api_id': 'SEC567',
        'min_borrow_rate': Decimal('0.12'),
        'last_updated': datetime.datetime.now()
    }
]

# Pre-defined stock for easy-to-borrow test scenarios
EASY_TO_BORROW_STOCK = {
    'ticker': 'AAPL',
    'borrow_status': BorrowStatus.EASY,
    'lender_api_id': 'SEC123',
    'min_borrow_rate': Decimal('0.01'),
    'last_updated': datetime.datetime.now()
}

# Pre-defined stock for hard-to-borrow test scenarios
HARD_TO_BORROW_STOCK = {
    'ticker': 'GME',
    'borrow_status': BorrowStatus.HARD,
    'lender_api_id': 'SEC789',
    'min_borrow_rate': Decimal('0.15'),
    'last_updated': datetime.datetime.now()
}


@pytest.fixture
def stock_data() -> List[Dict[str, Any]]:
    """
    Pytest fixture that provides a list of sample stock data for integration testing.
    
    Returns:
        List[Dict[str, Any]]: List of dictionaries containing stock data
    """
    # Return a copy to prevent test side effects
    return TEST_STOCKS.copy()


@pytest.fixture
def easy_to_borrow_stock() -> Dict[str, Any]:
    """
    Pytest fixture that provides a sample easy-to-borrow stock for API testing.
    
    Returns:
        Dict[str, Any]: Dictionary with stock data for an easy-to-borrow stock
    """
    return EASY_TO_BORROW_STOCK.copy()


@pytest.fixture
def hard_to_borrow_stock() -> Dict[str, Any]:
    """
    Pytest fixture that provides a sample hard-to-borrow stock for API testing.
    
    Returns:
        Dict[str, Any]: Dictionary with stock data for a hard-to-borrow stock
    """
    return HARD_TO_BORROW_STOCK.copy()


@pytest.fixture
def medium_to_borrow_stock() -> Dict[str, Any]:
    """
    Pytest fixture that provides a sample medium-to-borrow stock for API testing.
    
    Returns:
        Dict[str, Any]: Dictionary with stock data for a medium-to-borrow stock
    """
    for stock in TEST_STOCKS:
        if stock['ticker'] == 'TSLA':
            return stock.copy()
    # This should never happen if TEST_STOCKS is properly defined
    raise ValueError("Medium-to-borrow stock (TSLA) not found in TEST_STOCKS")


@pytest.fixture
def invalid_ticker() -> str:
    """
    Pytest fixture that provides an invalid ticker for testing error handling.
    
    Returns:
        str: Invalid ticker symbol
    """
    return 'INVALID123'


def get_stock_by_ticker(ticker: str) -> Dict[str, Any]:
    """
    Helper function to retrieve stock data by ticker symbol.
    
    Args:
        ticker (str): The ticker symbol to search for
        
    Returns:
        Dict[str, Any]: Stock data dictionary or None if not found
    """
    for stock in TEST_STOCKS:
        if stock['ticker'] == ticker:
            return stock.copy()
    return None


def generate_stock_with_custom_rate(ticker: str, borrow_status: BorrowStatus, min_borrow_rate: Decimal) -> Dict[str, Any]:
    """
    Generate a stock fixture with a custom minimum borrow rate for specific test scenarios.
    
    Args:
        ticker (str): The ticker symbol for the stock
        borrow_status (BorrowStatus): The borrow status enum value
        min_borrow_rate (Decimal): The minimum borrow rate to use
        
    Returns:
        Dict[str, Any]: Custom stock dictionary with specified parameters
    """
    return {
        'ticker': ticker,
        'borrow_status': borrow_status,
        'lender_api_id': f'SEC{hash(ticker) % 1000:03d}',
        'min_borrow_rate': min_borrow_rate,
        'last_updated': datetime.datetime.now()
    }