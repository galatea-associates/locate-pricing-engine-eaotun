"""
Unit tests for broker CRUD operations in the Borrow Rate & Locate Fee Pricing Engine.

This test module verifies the functionality of broker data creation, retrieval, update, 
and deletion operations, ensuring that broker configurations are correctly managed in the database.
"""

import pytest
from decimal import Decimal

# Import broker CRUD operations
from ...db.crud.brokers import (
    get_by_client_id,
    get_by_client_id_or_404,
    get_active_brokers,
    create_broker,
    update_broker,
    deactivate_broker,
    activate_broker,
    delete_broker,
    exists_by_client_id
)

# Import models and schemas
from ...db.models.broker import Broker
from ...schemas.broker import BrokerCreate, BrokerUpdate
from ...core.constants import TransactionFeeType
from ...core.exceptions import ClientNotFoundException

# Import test fixtures
from ..fixtures.brokers import (
    broker_data,
    standard_broker,
    premium_broker,
    inactive_broker,
    invalid_client_id
)


def test_get_by_client_id(test_db, standard_broker):
    """Test retrieving a broker by client ID."""
    client_id = standard_broker["client_id"]
    broker = get_by_client_id(test_db, client_id)
    
    assert broker is not None
    assert broker.client_id == client_id
    assert broker.markup_percentage == standard_broker["markup_percentage"]
    assert broker.transaction_fee_type == standard_broker["transaction_fee_type"]
    assert broker.transaction_amount == standard_broker["transaction_amount"]
    assert broker.active is True


def test_get_by_client_id_not_found(test_db, invalid_client_id):
    """Test retrieving a non-existent broker by client ID."""
    broker = get_by_client_id(test_db, invalid_client_id)
    assert broker is None


def test_get_by_client_id_or_404(test_db, standard_broker):
    """Test retrieving a broker by client ID or raising 404."""
    client_id = standard_broker["client_id"]
    broker = get_by_client_id_or_404(test_db, client_id)
    
    assert broker is not None
    assert broker.client_id == client_id


def test_get_by_client_id_or_404_not_found(test_db, invalid_client_id):
    """Test that get_by_client_id_or_404 raises ClientNotFoundException for non-existent broker."""
    with pytest.raises(ClientNotFoundException):
        get_by_client_id_or_404(test_db, invalid_client_id)


def test_get_active_brokers(test_db, broker_data):
    """Test retrieving all active brokers."""
    active_brokers = get_active_brokers(test_db)
    
    # Count active brokers in fixture data
    expected_count = sum(1 for broker in broker_data if broker["active"])
    
    assert len(active_brokers) == expected_count
    for broker in active_brokers:
        assert broker.active is True


def test_get_active_brokers_with_pagination(test_db, broker_data):
    """Test retrieving active brokers with pagination."""
    active_brokers = get_active_brokers(test_db, skip=1, limit=2)
    
    assert len(active_brokers) == 2
    for broker in active_brokers:
        assert broker.active is True


def test_create_broker(test_db):
    """Test creating a new broker."""
    # Create test data
    new_broker_data = {
        "client_id": "test_new_broker",
        "markup_percentage": Decimal("6.5"),
        "transaction_fee_type": TransactionFeeType.FLAT,
        "transaction_amount": Decimal("30.0"),
        "active": True
    }
    
    broker_create = BrokerCreate(**new_broker_data)
    broker = create_broker(test_db, broker_create)
    
    assert broker is not None
    assert broker.client_id == new_broker_data["client_id"]
    assert broker.markup_percentage == new_broker_data["markup_percentage"]
    assert broker.transaction_fee_type == new_broker_data["transaction_fee_type"]
    assert broker.transaction_amount == new_broker_data["transaction_amount"]
    assert broker.active is True


def test_create_broker_duplicate(test_db, standard_broker):
    """Test creating a broker with an existing client ID."""
    # Create data with same client_id but different values
    duplicate_broker_data = {
        "client_id": standard_broker["client_id"],
        "markup_percentage": Decimal("7.5"),  # Different from standard_broker
        "transaction_fee_type": TransactionFeeType.PERCENTAGE,  # Different from standard_broker
        "transaction_amount": Decimal("1.0"),  # Different from standard_broker
        "active": True
    }
    
    broker_create = BrokerCreate(**duplicate_broker_data)
    broker = create_broker(test_db, broker_create)
    
    # Should return the existing broker, not create a new one with the new values
    assert broker.markup_percentage == standard_broker["markup_percentage"]
    assert broker.transaction_fee_type == standard_broker["transaction_fee_type"]
    assert broker.transaction_amount == standard_broker["transaction_amount"]


def test_update_broker(test_db, standard_broker):
    """Test updating an existing broker."""
    client_id = standard_broker["client_id"]
    
    # Create update data
    update_data = {
        "markup_percentage": Decimal("8.0"),
        "transaction_fee_type": TransactionFeeType.PERCENTAGE,
        "transaction_amount": Decimal("1.5")
    }
    
    broker_update = BrokerUpdate(**update_data)
    updated_broker = update_broker(test_db, client_id, broker_update)
    
    assert updated_broker.markup_percentage == update_data["markup_percentage"]
    assert updated_broker.transaction_fee_type == update_data["transaction_fee_type"]
    assert updated_broker.transaction_amount == update_data["transaction_amount"]


def test_update_broker_not_found(test_db, invalid_client_id):
    """Test updating a non-existent broker."""
    update_data = {
        "markup_percentage": Decimal("8.0"),
        "transaction_fee_type": TransactionFeeType.PERCENTAGE,
        "transaction_amount": Decimal("1.5")
    }
    
    broker_update = BrokerUpdate(**update_data)
    
    with pytest.raises(ClientNotFoundException):
        update_broker(test_db, invalid_client_id, broker_update)


def test_deactivate_broker(test_db, standard_broker):
    """Test deactivating an active broker."""
    client_id = standard_broker["client_id"]
    
    deactivated_broker = deactivate_broker(test_db, client_id)
    assert deactivated_broker.active is False
    
    # Verify the broker is deactivated in the database
    broker = get_by_client_id(test_db, client_id)
    assert broker.active is False


def test_deactivate_broker_not_found(test_db, invalid_client_id):
    """Test deactivating a non-existent broker."""
    with pytest.raises(ClientNotFoundException):
        deactivate_broker(test_db, invalid_client_id)


def test_activate_broker(test_db, inactive_broker):
    """Test activating an inactive broker."""
    client_id = inactive_broker["client_id"]
    
    activated_broker = activate_broker(test_db, client_id)
    assert activated_broker.active is True
    
    # Verify the broker is activated in the database
    broker = get_by_client_id(test_db, client_id)
    assert broker.active is True


def test_activate_broker_not_found(test_db, invalid_client_id):
    """Test activating a non-existent broker."""
    with pytest.raises(ClientNotFoundException):
        activate_broker(test_db, invalid_client_id)


def test_delete_broker(test_db, standard_broker):
    """Test deleting a broker."""
    client_id = standard_broker["client_id"]
    
    deleted_broker = delete_broker(test_db, client_id)
    assert deleted_broker is not None
    assert deleted_broker.client_id == client_id
    
    # Verify the broker is deleted
    broker = get_by_client_id(test_db, client_id)
    assert broker is None


def test_delete_broker_not_found(test_db, invalid_client_id):
    """Test deleting a non-existent broker."""
    with pytest.raises(ClientNotFoundException):
        delete_broker(test_db, invalid_client_id)


def test_exists_by_client_id(test_db, standard_broker):
    """Test checking if a broker exists by client ID."""
    client_id = standard_broker["client_id"]
    exists = exists_by_client_id(test_db, client_id)
    assert exists is True


def test_exists_by_client_id_not_found(test_db, invalid_client_id):
    """Test checking if a non-existent broker exists by client ID."""
    exists = exists_by_client_id(test_db, invalid_client_id)
    assert exists is False