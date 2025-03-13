"""
Provides test fixtures for volatility and event risk data used in integration tests for the Borrow Rate & Locate Fee Pricing Engine.
These fixtures include sample volatility metrics for different stocks with varying volatility levels and event risk factors to test
borrow rate adjustments.
"""

import pytest
from decimal import Decimal
import datetime
from typing import Dict, List, Any, Optional

from .stocks import CURRENT_TIMESTAMP, TEST_STOCKS

# Volatility threshold constants
NORMAL_VOLATILITY_THRESHOLD = Decimal('20.0')
HIGH_VOLATILITY_THRESHOLD = Decimal('30.0')

# Test volatility data for different stocks with varying volatility levels
TEST_VOLATILITY_DATA = [
    {
        'stock_id': 'AAPL',
        'vol_index': Decimal('15.5'),
        'event_risk_factor': 1,
        'timestamp': datetime.datetime.now()
    },
    {
        'stock_id': 'TSLA',
        'vol_index': Decimal('25.8'),
        'event_risk_factor': 3,
        'timestamp': datetime.datetime.now()
    },
    {
        'stock_id': 'GME',
        'vol_index': Decimal('45.2'),
        'event_risk_factor': 7,
        'timestamp': datetime.datetime.now()
    },
    {
        'stock_id': 'MSFT',
        'vol_index': Decimal('12.3'),
        'event_risk_factor': 0,
        'timestamp': datetime.datetime.now()
    },
    {
        'stock_id': 'AMC',
        'vol_index': Decimal('38.7'),
        'event_risk_factor': 5,
        'timestamp': datetime.datetime.now()
    }
]

# Individual volatility data fixtures for specific test scenarios
LOW_VOLATILITY_DATA = {
    'stock_id': 'AAPL',
    'vol_index': Decimal('15.5'),
    'event_risk_factor': 1,
    'timestamp': datetime.datetime.now()
}

MEDIUM_VOLATILITY_DATA = {
    'stock_id': 'TSLA',
    'vol_index': Decimal('25.8'),
    'event_risk_factor': 3,
    'timestamp': datetime.datetime.now()
}

HIGH_VOLATILITY_DATA = {
    'stock_id': 'GME',
    'vol_index': Decimal('45.2'),
    'event_risk_factor': 7,
    'timestamp': datetime.datetime.now()
}

# Market-wide volatility data
MARKET_VOLATILITY_DATA = {
    'value': Decimal('22.5'),
    'timestamp': datetime.datetime.now()
}

# Event risk data for stocks with upcoming events
EVENT_RISK_DATA = [
    {
        'ticker': 'AAPL',
        'risk_factor': 1,
        'events': [
            {
                'type': 'earnings',
                'date': datetime.datetime.now() + datetime.timedelta(days=30),
                'risk_factor': 1,
                'description': 'Quarterly earnings announcement'
            }
        ],
        'timestamp': datetime.datetime.now()
    },
    {
        'ticker': 'GME',
        'risk_factor': 7,
        'events': [
            {
                'type': 'earnings',
                'date': datetime.datetime.now() + datetime.timedelta(days=5),
                'risk_factor': 5,
                'description': 'Quarterly earnings announcement'
            },
            {
                'type': 'corporate_action',
                'date': datetime.datetime.now() + datetime.timedelta(days=15),
                'risk_factor': 7,
                'description': 'Board meeting for strategic decisions'
            }
        ],
        'timestamp': datetime.datetime.now()
    }
]


@pytest.fixture
def volatility_data() -> List[Dict[str, Any]]:
    """
    Pytest fixture that provides a list of sample volatility data for integration testing.
    
    Returns:
        List[Dict[str, Any]]: List of dictionaries containing volatility data
    """
    # Return a copy to prevent test side effects
    return TEST_VOLATILITY_DATA.copy()


@pytest.fixture
def low_volatility_data() -> Dict[str, Any]:
    """
    Pytest fixture that provides a sample low volatility data for API testing.
    
    Returns:
        Dict[str, Any]: Dictionary with volatility data for a low volatility stock
    """
    return LOW_VOLATILITY_DATA.copy()


@pytest.fixture
def medium_volatility_data() -> Dict[str, Any]:
    """
    Pytest fixture that provides a sample medium volatility data for API testing.
    
    Returns:
        Dict[str, Any]: Dictionary with volatility data for a medium volatility stock
    """
    return MEDIUM_VOLATILITY_DATA.copy()


@pytest.fixture
def high_volatility_data() -> Dict[str, Any]:
    """
    Pytest fixture that provides a sample high volatility data for API testing.
    
    Returns:
        Dict[str, Any]: Dictionary with volatility data for a high volatility stock
    """
    return HIGH_VOLATILITY_DATA.copy()


@pytest.fixture
def market_volatility_data() -> Dict[str, Any]:
    """
    Pytest fixture that provides sample market-wide volatility data for API testing.
    
    Returns:
        Dict[str, Any]: Dictionary with market volatility data
    """
    return MARKET_VOLATILITY_DATA.copy()


@pytest.fixture
def event_risk_data() -> List[Dict[str, Any]]:
    """
    Pytest fixture that provides sample event risk data for API testing.
    
    Returns:
        List[Dict[str, Any]]: List of dictionaries containing event risk data
    """
    # Return a copy to prevent test side effects
    return EVENT_RISK_DATA.copy()


def get_volatility_by_stock_id(stock_id: str) -> Dict[str, Any]:
    """
    Helper function to retrieve volatility data by stock ID.
    
    Args:
        stock_id (str): The stock ID to search for
        
    Returns:
        Dict[str, Any]: Volatility data dictionary or None if not found
    """
    for vol_data in TEST_VOLATILITY_DATA:
        if vol_data['stock_id'] == stock_id:
            return vol_data.copy()
    return None


def get_event_risk_by_ticker(ticker: str) -> Dict[str, Any]:
    """
    Helper function to retrieve event risk data by ticker.
    
    Args:
        ticker (str): The ticker symbol to search for
        
    Returns:
        Dict[str, Any]: Event risk data dictionary or None if not found
    """
    for event_data in EVENT_RISK_DATA:
        if event_data['ticker'] == ticker:
            return event_data.copy()
    return None


def generate_volatility_with_custom_values(
    stock_id: str, 
    vol_index: Decimal, 
    event_risk_factor: int
) -> Dict[str, Any]:
    """
    Generate volatility data with custom values for specific test scenarios.
    
    Args:
        stock_id (str): The stock ID for the volatility data
        vol_index (Decimal): The volatility index value
        event_risk_factor (int): The event risk factor value
        
    Returns:
        Dict[str, Any]: Custom volatility data dictionary with specified parameters
    """
    return {
        'stock_id': stock_id,
        'vol_index': vol_index,
        'event_risk_factor': event_risk_factor,
        'timestamp': datetime.datetime.now()
    }


def get_volatility_tier(vol_index: Decimal) -> str:
    """
    Helper function to determine volatility tier based on volatility index.
    
    Args:
        vol_index (Decimal): The volatility index value
        
    Returns:
        str: Volatility tier (LOW, NORMAL, HIGH, EXTREME)
    """
    if vol_index < NORMAL_VOLATILITY_THRESHOLD:
        return 'LOW'
    elif vol_index < HIGH_VOLATILITY_THRESHOLD:
        return 'NORMAL'
    elif vol_index < Decimal('40.0'):
        return 'HIGH'
    else:
        return 'EXTREME'