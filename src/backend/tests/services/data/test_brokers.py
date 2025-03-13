"""
Unit tests for the broker data service in the Borrow Rate & Locate Fee Pricing Engine.
Tests the functionality for retrieving, creating, updating, and caching broker configurations
used in fee calculations.
"""

import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal

from ...services.data.brokers import BrokerService
from ...db.crud.brokers import broker_crud
from ...services.cache.redis import redis_cache
from ...core.exceptions import ClientNotFoundException, ValidationException
from ...schemas.broker import BrokerCreate, BrokerUpdate, BrokerSchema


@pytest.fixture
def standard_broker():
    """Standard broker data fixture"""
    return {
        "client_id": "test_broker",
        "markup_percentage": Decimal("5.0"),
        "transaction_fee_type": "FLAT",
        "transaction_amount": Decimal("25.0"),
        "active": True,
        "last_updated": "2023-10-15T14:30:22Z"
    }


@pytest.fixture
def inactive_broker():
    """Inactive broker data fixture"""
    return {
        "client_id": "inactive_broker",
        "markup_percentage": Decimal("5.0"),
        "transaction_fee_type": "FLAT",
        "transaction_amount": Decimal("25.0"),
        "active": False,
        "last_updated": "2023-10-15T14:30:22Z"
    }


@pytest.fixture
def invalid_client_id():
    """Invalid client ID fixture"""
    return "nonexistent_client"


@pytest.fixture
def broker_data():
    """List of broker data fixtures"""
    return [
        {
            "client_id": "broker_1",
            "markup_percentage": Decimal("5.0"),
            "transaction_fee_type": "FLAT",
            "transaction_amount": Decimal("25.0"),
            "active": True,
            "last_updated": "2023-10-15T14:30:22Z"
        },
        {
            "client_id": "broker_2",
            "markup_percentage": Decimal("6.0"),
            "transaction_fee_type": "PERCENTAGE",
            "transaction_amount": Decimal("0.5"),
            "active": True,
            "last_updated": "2023-10-15T14:30:22Z"
        },
        {
            "client_id": "broker_3",
            "markup_percentage": Decimal("4.5"),
            "transaction_fee_type": "FLAT",
            "transaction_amount": Decimal("30.0"),
            "active": True,
            "last_updated": "2023-10-15T14:30:22Z"
        }
    ]


def test_broker_service_init():
    """Test that the broker service initializes correctly"""
    service = BrokerService()
    assert isinstance(service, BrokerService)


@patch('src.backend.services.data.brokers.broker_crud')
@patch('src.backend.services.data.brokers.redis_cache')
def test_get_broker_success(mock_redis_cache, mock_broker_crud, standard_broker):
    """Test successful retrieval of a broker by client ID"""
    # Setup mock responses
    mock_broker = MagicMock()
    mock_broker.to_dict.return_value = standard_broker
    mock_broker_crud.get_by_client_id_or_404.return_value = mock_broker
    mock_redis_cache.get.return_value = None  # Cache miss
    
    # Create service and call method
    service = BrokerService()
    result = service.get_broker(standard_broker['client_id'])
    
    # Verify
    mock_broker_crud.get_by_client_id_or_404.assert_called_once()
    mock_redis_cache.get.assert_called_once()
    mock_redis_cache.set.assert_called_once()
    assert result == standard_broker


@patch('src.backend.services.data.brokers.broker_crud')
@patch('src.backend.services.data.brokers.redis_cache')
def test_get_broker_from_cache(mock_redis_cache, mock_broker_crud, standard_broker):
    """Test retrieval of a broker from cache"""
    # Setup mock responses
    mock_redis_cache.get.return_value = standard_broker  # Cache hit
    
    # Create service and call method
    service = BrokerService()
    result = service.get_broker(standard_broker['client_id'])
    
    # Verify
    mock_broker_crud.get_by_client_id_or_404.assert_not_called()
    mock_redis_cache.get.assert_called_once()
    assert result == standard_broker


@patch('src.backend.services.data.brokers.broker_crud')
@patch('src.backend.services.data.brokers.redis_cache')
def test_get_broker_not_found(mock_redis_cache, mock_broker_crud, invalid_client_id):
    """Test handling of broker not found error"""
    # Setup mock responses
    mock_broker_crud.get_by_client_id_or_404.side_effect = ClientNotFoundException(invalid_client_id)
    mock_redis_cache.get.return_value = None  # Cache miss
    
    # Create service and test the exception
    service = BrokerService()
    with pytest.raises(ClientNotFoundException):
        service.get_broker(invalid_client_id)
    
    # Verify
    mock_broker_crud.get_by_client_id_or_404.assert_called_once()
    mock_redis_cache.get.assert_called_once()


@patch('src.backend.services.data.brokers.broker_crud')
def test_get_active_brokers(mock_broker_crud, broker_data):
    """Test retrieval of all active brokers"""
    # Setup mock responses
    mock_brokers = []
    for data in broker_data:
        mock_broker = MagicMock()
        mock_broker.to_dict.return_value = data
        mock_brokers.append(mock_broker)
    
    mock_broker_crud.get_active_brokers.return_value = mock_brokers
    
    # Create service and call method
    service = BrokerService()
    result = service.get_active_brokers(skip=0, limit=10)
    
    # Verify
    mock_broker_crud.get_active_brokers.assert_called_once()
    assert len(result) == len(broker_data)
    for i, broker in enumerate(result):
        assert broker == broker_data[i]


@patch('src.backend.services.data.brokers.broker_crud')
@patch('src.backend.services.data.brokers.redis_cache')
def test_create_broker(mock_redis_cache, mock_broker_crud):
    """Test creation of a new broker"""
    # Setup test data
    broker_data = BrokerCreate(
        client_id="test_broker",
        markup_percentage=Decimal("5.0"),
        transaction_fee_type="FLAT",
        transaction_amount=Decimal("25.0"),
        active=True
    )
    
    # Setup mock responses
    mock_broker = MagicMock()
    mock_broker.to_dict.return_value = {
        "client_id": "test_broker",
        "markup_percentage": Decimal("5.0"),
        "transaction_fee_type": "FLAT",
        "transaction_amount": Decimal("25.0"),
        "active": True,
        "last_updated": "2023-10-15T14:30:22Z"
    }
    mock_broker_crud.create_broker.return_value = mock_broker
    mock_redis_cache.delete.return_value = True
    
    # Create service and call method
    service = BrokerService()
    result = service.create_broker(broker_data)
    
    # Verify
    mock_broker_crud.create_broker.assert_called_once()
    mock_redis_cache.delete.assert_called_once()
    assert result["client_id"] == "test_broker"
    assert result["markup_percentage"] == Decimal("5.0")
    assert result["transaction_fee_type"] == "FLAT"
    assert result["transaction_amount"] == Decimal("25.0")
    assert result["active"] is True


@patch('src.backend.services.data.brokers.broker_crud')
@patch('src.backend.services.data.brokers.redis_cache')
def test_update_broker(mock_redis_cache, mock_broker_crud, standard_broker):
    """Test updating an existing broker"""
    # Setup test data
    client_id = standard_broker["client_id"]
    update_data = BrokerUpdate(
        markup_percentage=Decimal("6.0"),
        transaction_amount=Decimal("30.0")
    )
    
    # Setup mock responses
    mock_broker = MagicMock()
    mock_broker.to_dict.return_value = {
        **standard_broker,
        "markup_percentage": Decimal("6.0"),
        "transaction_amount": Decimal("30.0")
    }
    mock_broker_crud.update_broker.return_value = mock_broker
    mock_redis_cache.delete.return_value = True
    
    # Create service and call method
    service = BrokerService()
    result = service.update_broker(client_id, update_data)
    
    # Verify
    mock_broker_crud.update_broker.assert_called_once()
    mock_redis_cache.delete.assert_called_once()
    assert result["markup_percentage"] == Decimal("6.0")
    assert result["transaction_amount"] == Decimal("30.0")


@patch('src.backend.services.data.brokers.broker_crud')
@patch('src.backend.services.data.brokers.redis_cache')
def test_deactivate_broker(mock_redis_cache, mock_broker_crud, standard_broker):
    """Test deactivation of a broker"""
    # Setup test data
    client_id = standard_broker["client_id"]
    
    # Setup mock responses
    mock_broker = MagicMock()
    mock_broker.to_dict.return_value = {
        **standard_broker,
        "active": False
    }
    mock_broker_crud.deactivate_broker.return_value = mock_broker
    mock_redis_cache.delete.return_value = True
    
    # Create service and call method
    service = BrokerService()
    result = service.deactivate_broker(client_id)
    
    # Verify
    mock_broker_crud.deactivate_broker.assert_called_once()
    mock_redis_cache.delete.assert_called_once()
    assert result["active"] is False


@patch('src.backend.services.data.brokers.broker_crud')
@patch('src.backend.services.data.brokers.redis_cache')
def test_activate_broker(mock_redis_cache, mock_broker_crud, inactive_broker):
    """Test activation of a broker"""
    # Setup test data
    client_id = inactive_broker["client_id"]
    
    # Setup mock responses
    mock_broker = MagicMock()
    mock_broker.to_dict.return_value = {
        **inactive_broker,
        "active": True
    }
    mock_broker_crud.activate_broker.return_value = mock_broker
    mock_redis_cache.delete.return_value = True
    
    # Create service and call method
    service = BrokerService()
    result = service.activate_broker(client_id)
    
    # Verify
    mock_broker_crud.activate_broker.assert_called_once()
    mock_redis_cache.delete.assert_called_once()
    assert result["active"] is True


@patch('src.backend.services.data.brokers.broker_crud')
@patch('src.backend.services.data.brokers.redis_cache')
def test_delete_broker(mock_redis_cache, mock_broker_crud, standard_broker):
    """Test deletion of a broker"""
    # Setup test data
    client_id = standard_broker["client_id"]
    
    # Setup mock responses
    mock_broker = MagicMock()
    mock_broker.to_dict.return_value = standard_broker
    mock_broker_crud.delete_broker.return_value = mock_broker
    mock_redis_cache.delete.return_value = True
    
    # Create service and call method
    service = BrokerService()
    result = service.delete_broker(client_id)
    
    # Verify
    mock_broker_crud.delete_broker.assert_called_once()
    mock_redis_cache.delete.assert_called_once()
    assert result == standard_broker


@patch('src.backend.services.data.brokers.broker_crud')
def test_broker_exists(mock_broker_crud, standard_broker):
    """Test checking if a broker exists"""
    # Setup test data
    client_id = standard_broker["client_id"]
    
    # Setup mock responses
    mock_broker_crud.exists_by_client_id.return_value = True
    
    # Create service and call method
    service = BrokerService()
    result = service.broker_exists(client_id)
    
    # Verify
    mock_broker_crud.exists_by_client_id.assert_called_once()
    assert result is True


@patch('src.backend.services.data.brokers.broker_crud')
def test_broker_not_exists(mock_broker_crud, invalid_client_id):
    """Test checking if a broker does not exist"""
    # Setup mock responses
    mock_broker_crud.exists_by_client_id.return_value = False
    
    # Create service and call method
    service = BrokerService()
    result = service.broker_exists(invalid_client_id)
    
    # Verify
    mock_broker_crud.exists_by_client_id.assert_called_once()
    assert result is False


@patch('src.backend.services.data.brokers.redis_cache')
def test_invalidate_broker_cache(mock_redis_cache, standard_broker):
    """Test invalidation of broker cache"""
    # Setup test data
    client_id = standard_broker["client_id"]
    
    # Setup mock responses
    mock_redis_cache.delete.return_value = True
    
    # Create service and call method
    service = BrokerService()
    result = service.invalidate_broker_cache(client_id)
    
    # Verify
    mock_redis_cache.delete.assert_called_once()
    assert result is True


def test_validation_error_handling():
    """Test handling of validation errors"""
    # Create service
    service = BrokerService()
    
    # Test with empty client_id
    with pytest.raises(ValidationException):
        service.get_broker("")
    
    # Test with None client_id
    with pytest.raises(ValidationException):
        service.get_broker(None)