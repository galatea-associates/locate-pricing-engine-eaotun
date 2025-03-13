"""
Provides test fixtures for broker data used in integration tests for the Borrow Rate & Locate Fee Pricing Engine.

These fixtures include sample brokers with various markup percentages, transaction fee types, and configurations 
to test different fee calculation scenarios.
"""

import pytest
from decimal import Decimal  # version: standard library
import datetime  # version: standard library
from typing import Dict, List, Any  # version: standard library

from ...backend.core.constants import TransactionFeeType

# Current timestamp for consistent datetime values across fixtures
CURRENT_TIMESTAMP = datetime.datetime.now().isoformat()

# Sample broker data for testing
TEST_BROKERS = [
    {
        "client_id": "standard_broker",
        "markup_percentage": Decimal("5.0"),
        "transaction_fee_type": TransactionFeeType.FLAT,
        "transaction_amount": Decimal("25.0"),
        "active": True,
        "last_updated": datetime.datetime.now()
    },
    {
        "client_id": "premium_broker",
        "markup_percentage": Decimal("3.5"),
        "transaction_fee_type": TransactionFeeType.PERCENTAGE,
        "transaction_amount": Decimal("0.5"),
        "active": True,
        "last_updated": datetime.datetime.now()
    },
    {
        "client_id": "high_markup_broker",
        "markup_percentage": Decimal("10.0"),
        "transaction_fee_type": TransactionFeeType.FLAT,
        "transaction_amount": Decimal("30.0"),
        "active": True,
        "last_updated": datetime.datetime.now()
    },
    {
        "client_id": "inactive_broker",
        "markup_percentage": Decimal("5.0"),
        "transaction_fee_type": TransactionFeeType.FLAT,
        "transaction_amount": Decimal("25.0"),
        "active": False,
        "last_updated": datetime.datetime.now()
    },
    {
        "client_id": "zero_fee_broker",
        "markup_percentage": Decimal("2.0"),
        "transaction_fee_type": TransactionFeeType.FLAT,
        "transaction_amount": Decimal("0.0"),
        "active": True,
        "last_updated": datetime.datetime.now()
    }
]

# Individual broker configurations for direct reference
STANDARD_BROKER = {
    "client_id": "standard_broker",
    "markup_percentage": Decimal("5.0"),
    "transaction_fee_type": TransactionFeeType.FLAT,
    "transaction_amount": Decimal("25.0"),
    "active": True,
    "last_updated": datetime.datetime.now()
}

PREMIUM_BROKER = {
    "client_id": "premium_broker",
    "markup_percentage": Decimal("3.5"),
    "transaction_fee_type": TransactionFeeType.PERCENTAGE,
    "transaction_amount": Decimal("0.5"),
    "active": True,
    "last_updated": datetime.datetime.now()
}

HIGH_MARKUP_BROKER = {
    "client_id": "high_markup_broker",
    "markup_percentage": Decimal("10.0"),
    "transaction_fee_type": TransactionFeeType.FLAT,
    "transaction_amount": Decimal("30.0"),
    "active": True,
    "last_updated": datetime.datetime.now()
}


@pytest.fixture
def broker_data() -> List[Dict[str, Any]]:
    """
    Pytest fixture that provides a list of sample broker data for integration testing.
    
    Returns:
        List[Dict[str, Any]]: List of dictionaries containing broker data
    """
    # Return a copy to prevent test side effects
    return TEST_BROKERS.copy()


@pytest.fixture
def standard_broker() -> Dict[str, Any]:
    """
    Pytest fixture that provides a sample standard broker with flat fee for API testing.
    
    Returns:
        Dict[str, Any]: Dictionary with broker data for a standard broker
    """
    return STANDARD_BROKER


@pytest.fixture
def premium_broker() -> Dict[str, Any]:
    """
    Pytest fixture that provides a sample premium broker with percentage fee for API testing.
    
    Returns:
        Dict[str, Any]: Dictionary with broker data for a premium broker
    """
    return PREMIUM_BROKER


@pytest.fixture
def high_markup_broker() -> Dict[str, Any]:
    """
    Pytest fixture that provides a sample broker with high markup for API testing.
    
    Returns:
        Dict[str, Any]: Dictionary with broker data for a high markup broker
    """
    return HIGH_MARKUP_BROKER


@pytest.fixture
def inactive_broker() -> Dict[str, Any]:
    """
    Pytest fixture that provides a sample inactive broker for API testing.
    
    Returns:
        Dict[str, Any]: Dictionary with broker data for an inactive broker
    """
    # Find the inactive broker in the test data
    for broker in TEST_BROKERS:
        if broker["client_id"] == "inactive_broker":
            return broker


@pytest.fixture
def invalid_client_id() -> str:
    """
    Pytest fixture that provides an invalid client ID for testing error handling.
    
    Returns:
        str: Invalid client ID
    """
    return "nonexistent_client"


def get_broker_by_client_id(client_id: str) -> Dict[str, Any]:
    """
    Helper function to retrieve broker data by client ID.
    
    Args:
        client_id (str): The client ID to search for
        
    Returns:
        Dict[str, Any]: Broker data dictionary or None if not found
    """
    for broker in TEST_BROKERS:
        if broker["client_id"] == client_id:
            return broker
    return None


def generate_broker_with_custom_markup(
    client_id: str,
    markup_percentage: Decimal,
    transaction_fee_type: TransactionFeeType,
    transaction_amount: Decimal
) -> Dict[str, Any]:
    """
    Generate a broker fixture with a custom markup percentage for specific test scenarios.
    
    Args:
        client_id (str): Unique client identifier
        markup_percentage (Decimal): The markup percentage to apply
        transaction_fee_type (TransactionFeeType): Type of transaction fee
        transaction_amount (Decimal): Amount for the transaction fee
        
    Returns:
        Dict[str, Any]: Custom broker dictionary with specified parameters
    """
    return {
        "client_id": client_id,
        "markup_percentage": markup_percentage,
        "transaction_fee_type": transaction_fee_type,
        "transaction_amount": transaction_amount,
        "active": True,
        "last_updated": datetime.datetime.now()
    }