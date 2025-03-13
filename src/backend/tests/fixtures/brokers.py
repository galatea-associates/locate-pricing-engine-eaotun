"""
Provides test fixtures for broker data used in unit and integration tests for the 
Borrow Rate & Locate Fee Pricing Engine.

These fixtures include sample brokers with different markup percentages, transaction fee types,
and other attributes to test various fee calculation scenarios.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from ...core.constants import TransactionFeeType
from ...schemas.broker import BrokerSchema, BrokerCreate

# Sample broker data for testing different fee calculation scenarios
BROKER_FIXTURES = [
    {
        "client_id": "standard_broker",
        "markup_percentage": Decimal('5.0'),  # 5% markup
        "transaction_fee_type": TransactionFeeType.FLAT,
        "transaction_amount": Decimal('25.0'),  # $25 flat fee
        "active": True,
        "last_updated": datetime.now()
    },
    {
        "client_id": "premium_broker",
        "markup_percentage": Decimal('3.5'),  # 3.5% markup
        "transaction_fee_type": TransactionFeeType.PERCENTAGE,
        "transaction_amount": Decimal('0.5'),  # 0.5% percentage fee
        "active": True,
        "last_updated": datetime.now()
    },
    {
        "client_id": "high_markup_broker",
        "markup_percentage": Decimal('10.0'),  # 10% markup
        "transaction_fee_type": TransactionFeeType.FLAT,
        "transaction_amount": Decimal('50.0'),  # $50 flat fee
        "active": True,
        "last_updated": datetime.now()
    },
    {
        "client_id": "low_markup_broker",
        "markup_percentage": Decimal('1.0'),  # 1% markup
        "transaction_fee_type": TransactionFeeType.PERCENTAGE,
        "transaction_amount": Decimal('0.1'),  # 0.1% percentage fee
        "active": True,
        "last_updated": datetime.now()
    },
    {
        "client_id": "inactive_broker",
        "markup_percentage": Decimal('5.0'),  # 5% markup
        "transaction_fee_type": TransactionFeeType.FLAT,
        "transaction_amount": Decimal('25.0'),  # $25 flat fee
        "active": False,
        "last_updated": datetime.now()
    }
]


@pytest.fixture
def broker_data():
    """
    Pytest fixture that provides a list of sample broker data for testing.
    
    Returns:
        list: List of dictionaries containing broker data
    """
    # Return a copy to prevent test side effects modifying the original data
    return BROKER_FIXTURES.copy()


@pytest.fixture
def standard_broker():
    """
    Pytest fixture that provides a sample standard broker with flat fee.
    
    Returns:
        dict: Dictionary with broker data for a standard broker
    """
    return next(broker for broker in BROKER_FIXTURES if broker["client_id"] == "standard_broker")


@pytest.fixture
def premium_broker():
    """
    Pytest fixture that provides a sample premium broker with percentage fee.
    
    Returns:
        dict: Dictionary with broker data for a premium broker
    """
    return next(broker for broker in BROKER_FIXTURES if broker["client_id"] == "premium_broker")


@pytest.fixture
def high_markup_broker():
    """
    Pytest fixture that provides a broker with high markup percentage.
    
    Returns:
        dict: Dictionary with broker data having a high markup percentage
    """
    return next(broker for broker in BROKER_FIXTURES if broker["client_id"] == "high_markup_broker")


@pytest.fixture
def low_markup_broker():
    """
    Pytest fixture that provides a broker with low markup percentage.
    
    Returns:
        dict: Dictionary with broker data having a low markup percentage
    """
    return next(broker for broker in BROKER_FIXTURES if broker["client_id"] == "low_markup_broker")


@pytest.fixture
def inactive_broker():
    """
    Pytest fixture that provides an inactive broker for testing error handling.
    
    Returns:
        dict: Dictionary with broker data for an inactive broker
    """
    return next(broker for broker in BROKER_FIXTURES if broker["client_id"] == "inactive_broker")


@pytest.fixture
def invalid_client_id():
    """
    Pytest fixture that provides an invalid client ID for testing error handling.
    
    Returns:
        str: Invalid client ID
    """
    return "NONEXISTENT"


@pytest.fixture
def broker_schemas():
    """
    Pytest fixture that provides a list of BrokerSchema objects for testing.
    
    Returns:
        list: List of BrokerSchema objects
    """
    return [BrokerSchema(**broker) for broker in BROKER_FIXTURES]


@pytest.fixture
def broker_create_objects():
    """
    Pytest fixture that provides a list of BrokerCreate objects for testing.
    
    Returns:
        list: List of BrokerCreate objects
    """
    create_objects = []
    
    for broker in BROKER_FIXTURES:
        # Create a copy without 'last_updated' which isn't part of BrokerCreate
        broker_data = {k: v for k, v in broker.items() if k != 'last_updated'}
        create_objects.append(BrokerCreate(**broker_data))
        
    return create_objects


@pytest.fixture
def flat_fee_broker():
    """
    Pytest fixture that provides a broker with flat transaction fee.
    
    Returns:
        dict: Dictionary with broker data using flat transaction fee
    """
    return next(broker for broker in BROKER_FIXTURES 
               if broker["transaction_fee_type"] == TransactionFeeType.FLAT)


@pytest.fixture
def percentage_fee_broker():
    """
    Pytest fixture that provides a broker with percentage transaction fee.
    
    Returns:
        dict: Dictionary with broker data using percentage transaction fee
    """
    return next(broker for broker in BROKER_FIXTURES 
               if broker["transaction_fee_type"] == TransactionFeeType.PERCENTAGE)