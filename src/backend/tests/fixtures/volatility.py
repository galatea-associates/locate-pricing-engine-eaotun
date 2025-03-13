"""
Provides test fixtures for volatility and event risk data used in unit and integration tests
for the Borrow Rate & Locate Fee Pricing Engine. These fixtures include sample volatility metrics
and event risk factors for different stocks to test various calculation scenarios.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from ...schemas.volatility import VolatilitySchema, VolatilityCreate
from ...services.calculation.volatility import NORMAL_VOLATILITY_THRESHOLD, HIGH_VOLATILITY_THRESHOLD

# Sample volatility data for testing
VOLATILITY_FIXTURES = [
    {
        'stock_id': 'AAPL',
        'vol_index': Decimal('18.5'),
        'event_risk_factor': 2,
        'timestamp': datetime.now()
    },
    {
        'stock_id': 'GME',
        'vol_index': Decimal('45.0'),
        'event_risk_factor': 8,
        'timestamp': datetime.now()
    },
    {
        'stock_id': 'MSFT',
        'vol_index': Decimal('15.2'),
        'event_risk_factor': 1,
        'timestamp': datetime.now()
    },
    {
        'stock_id': 'TSLA',
        'vol_index': Decimal('32.7'),
        'event_risk_factor': 6,
        'timestamp': datetime.now()
    },
    {
        'stock_id': 'AMC',
        'vol_index': Decimal('50.3'),
        'event_risk_factor': 9,
        'timestamp': datetime.now()
    }
]


@pytest.fixture
def volatility_data():
    """
    Pytest fixture that provides a list of sample volatility data for testing.
    
    Returns:
        List of dictionaries containing volatility data
    """
    # Return a copy to prevent tests from modifying the original data
    return VOLATILITY_FIXTURES.copy()


@pytest.fixture
def low_volatility_data():
    """
    Pytest fixture that provides a sample low volatility data point.
    
    Returns:
        Dictionary with volatility data having low volatility index
    """
    # Find first item with vol_index below normal threshold
    for item in VOLATILITY_FIXTURES:
        if item['vol_index'] < NORMAL_VOLATILITY_THRESHOLD:
            return item.copy()
    
    # If no matching item found, return default low volatility data
    return {
        'stock_id': 'LOW_VOL',
        'vol_index': Decimal('10.0'),
        'event_risk_factor': 1,
        'timestamp': datetime.now()
    }


@pytest.fixture
def high_volatility_data():
    """
    Pytest fixture that provides a sample high volatility data point.
    
    Returns:
        Dictionary with volatility data having high volatility index
    """
    # Find first item with vol_index above high threshold
    for item in VOLATILITY_FIXTURES:
        if item['vol_index'] >= HIGH_VOLATILITY_THRESHOLD:
            return item.copy()
    
    # If no matching item found, return default high volatility data
    return {
        'stock_id': 'HIGH_VOL',
        'vol_index': Decimal('35.0'),
        'event_risk_factor': 5,
        'timestamp': datetime.now()
    }


@pytest.fixture
def medium_volatility_data():
    """
    Pytest fixture that provides a sample medium volatility data point.
    
    Returns:
        Dictionary with volatility data having medium volatility index
    """
    # Find first item with vol_index between normal and high threshold
    for item in VOLATILITY_FIXTURES:
        if NORMAL_VOLATILITY_THRESHOLD <= item['vol_index'] < HIGH_VOLATILITY_THRESHOLD:
            return item.copy()
    
    # If no matching item found, return default medium volatility data
    return {
        'stock_id': 'MED_VOL',
        'vol_index': Decimal('25.0'),
        'event_risk_factor': 3,
        'timestamp': datetime.now()
    }


@pytest.fixture
def low_event_risk_data():
    """
    Pytest fixture that provides a sample low event risk data point.
    
    Returns:
        Dictionary with volatility data having low event risk factor
    """
    # Find first item with event_risk_factor <= 3
    for item in VOLATILITY_FIXTURES:
        if item['event_risk_factor'] <= 3:
            return item.copy()
    
    # If no matching item found, return default low event risk data
    return {
        'stock_id': 'LOW_RISK',
        'vol_index': Decimal('15.0'),
        'event_risk_factor': 1,
        'timestamp': datetime.now()
    }


@pytest.fixture
def high_event_risk_data():
    """
    Pytest fixture that provides a sample high event risk data point.
    
    Returns:
        Dictionary with volatility data having high event risk factor
    """
    # Find first item with event_risk_factor >= 7
    for item in VOLATILITY_FIXTURES:
        if item['event_risk_factor'] >= 7:
            return item.copy()
    
    # If no matching item found, return default high event risk data
    return {
        'stock_id': 'HIGH_RISK',
        'vol_index': Decimal('30.0'),
        'event_risk_factor': 8,
        'timestamp': datetime.now()
    }


@pytest.fixture
def volatility_for_stock(ticker):
    """
    Pytest fixture that provides volatility data for a specific stock.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Dictionary with volatility data for the specified ticker
    """
    # Find item with matching stock_id
    for item in VOLATILITY_FIXTURES:
        if item['stock_id'] == ticker:
            return item.copy()
    
    # Return None if not found
    return None


@pytest.fixture
def volatility_schemas():
    """
    Pytest fixture that provides a list of VolatilitySchema objects for testing.
    
    Returns:
        List of VolatilitySchema objects
    """
    return [VolatilitySchema(**item) for item in VOLATILITY_FIXTURES]


@pytest.fixture
def volatility_create_objects():
    """
    Pytest fixture that provides a list of VolatilityCreate objects for testing.
    
    Returns:
        List of VolatilityCreate objects
    """
    # Create a list of VolatilityCreate objects (without timestamp)
    create_objects = []
    for item in VOLATILITY_FIXTURES:
        data = {k: v for k, v in item.items() if k != 'timestamp'}
        create_objects.append(VolatilityCreate(**data))
    
    return create_objects


@pytest.fixture
def extreme_volatility_data():
    """
    Pytest fixture that provides a sample extreme volatility data point.
    
    Returns:
        Dictionary with volatility data having extreme volatility index
    """
    # Find the item with the highest volatility index
    return max(VOLATILITY_FIXTURES, key=lambda x: x['vol_index']).copy()