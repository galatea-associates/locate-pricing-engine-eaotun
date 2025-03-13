"""
Service module for broker data operations in the Borrow Rate & Locate Fee Pricing Engine.

Provides high-level business logic for retrieving, caching, and managing broker
configurations used in fee calculations. Implements caching strategies and error
handling for broker data access.
"""

from typing import List, Optional, Dict, Any

import sqlalchemy.exc  # sqlalchemy 2.0.0+

from .utils import (
    DataServiceBase,
    validate_client_id,
    cache_result,
    DEFAULT_CACHE_TTL
)
from ...db.crud.brokers import broker_crud
from ..cache.redis import redis_cache
from ...schemas.broker import BrokerSchema, BrokerCreate, BrokerUpdate
from ...core.exceptions import ClientNotFoundException, ValidationException

# Cache time-to-live for broker configurations (30 minutes)
BROKER_CACHE_TTL = 1800

# Cache key prefix for broker data
BROKER_CACHE_KEY_PREFIX = 'broker'


class BrokerService(DataServiceBase):
    """
    Service for managing broker data and configurations.
    """

    def __init__(self):
        """Initialize the broker service."""
        super().__init__()

    @cache_result(BROKER_CACHE_TTL)
    def get_broker(self, client_id: str) -> Dict[str, Any]:
        """
        Get a broker by client ID with caching.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dict[str, Any]: Broker data as a dictionary
        """
        # Validate client ID
        validate_client_id(client_id)
        
        try:
            # Get database session
            with self._get_db_session() as db:
                # Get broker from database
                broker = broker_crud.get_by_client_id_or_404(db, client_id)
                
                # Convert to dictionary and return
                return broker.to_dict()
        except ClientNotFoundException:
            # Handle broker not found
            self._handle_broker_not_found(client_id)
        except sqlalchemy.exc.SQLAlchemyError as e:
            # Handle database error
            self._handle_db_error(e, f"get_broker for {client_id}")

    def get_active_brokers(self, skip: Optional[int] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all active brokers.
        
        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            
        Returns:
            List[Dict[str, Any]]: List of active broker data dictionaries
        """
        try:
            # Get database session
            with self._get_db_session() as db:
                # Get active brokers from database
                brokers = broker_crud.get_active_brokers(db, skip=skip, limit=limit)
                
                # Convert to list of dictionaries and return
                return [broker.to_dict() for broker in brokers]
        except sqlalchemy.exc.SQLAlchemyError as e:
            # Handle database error
            self._log_operation(
                "get_active_brokers",
                f"Error getting active brokers: {str(e)}",
                "ERROR"
            )
            return []  # Return empty list on error

    def create_broker(self, broker_data: BrokerCreate) -> Dict[str, Any]:
        """
        Create a new broker.
        
        Args:
            broker_data: Broker data for creation
            
        Returns:
            Dict[str, Any]: Created broker data as a dictionary
        """
        try:
            # Get database session
            with self._get_db_session() as db:
                # Create broker in database
                broker = broker_crud.create_broker(db, broker_data)
                
                # Log successful creation
                self._log_operation(
                    "create_broker",
                    f"Created broker with client_id: {broker.client_id}"
                )
                
                # Invalidate any existing cache for this broker
                self.invalidate_broker_cache(broker.client_id)
                
                # Convert to dictionary and return
                return broker.to_dict()
        except sqlalchemy.exc.SQLAlchemyError as e:
            # Handle database error
            self._handle_db_error(e, "create_broker")

    def update_broker(self, client_id: str, broker_data: BrokerUpdate) -> Dict[str, Any]:
        """
        Update an existing broker.
        
        Args:
            client_id: Client identifier
            broker_data: Updated broker data
            
        Returns:
            Dict[str, Any]: Updated broker data as a dictionary
        """
        # Validate client ID
        validate_client_id(client_id)
        
        try:
            # Get database session
            with self._get_db_session() as db:
                # Update broker in database
                broker = broker_crud.update_broker(db, client_id, broker_data)
                
                # Invalidate cache for this broker
                self.invalidate_broker_cache(client_id)
                
                # Log successful update
                self._log_operation(
                    "update_broker",
                    f"Updated broker with client_id: {client_id}"
                )
                
                # Convert to dictionary and return
                return broker.to_dict()
        except ClientNotFoundException:
            # Handle broker not found
            self._handle_broker_not_found(client_id)
        except sqlalchemy.exc.SQLAlchemyError as e:
            # Handle database error
            self._handle_db_error(e, f"update_broker for {client_id}")

    def deactivate_broker(self, client_id: str) -> Dict[str, Any]:
        """
        Deactivate a broker.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dict[str, Any]: Deactivated broker data as a dictionary
        """
        # Validate client ID
        validate_client_id(client_id)
        
        try:
            # Get database session
            with self._get_db_session() as db:
                # Deactivate broker in database
                broker = broker_crud.deactivate_broker(db, client_id)
                
                # Invalidate cache for this broker
                self.invalidate_broker_cache(client_id)
                
                # Log successful deactivation
                self._log_operation(
                    "deactivate_broker",
                    f"Deactivated broker with client_id: {client_id}"
                )
                
                # Convert to dictionary and return
                return broker.to_dict()
        except ClientNotFoundException:
            # Handle broker not found
            self._handle_broker_not_found(client_id)
        except sqlalchemy.exc.SQLAlchemyError as e:
            # Handle database error
            self._handle_db_error(e, f"deactivate_broker for {client_id}")

    def activate_broker(self, client_id: str) -> Dict[str, Any]:
        """
        Activate a broker.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dict[str, Any]: Activated broker data as a dictionary
        """
        # Validate client ID
        validate_client_id(client_id)
        
        try:
            # Get database session
            with self._get_db_session() as db:
                # Activate broker in database
                broker = broker_crud.activate_broker(db, client_id)
                
                # Invalidate cache for this broker
                self.invalidate_broker_cache(client_id)
                
                # Log successful activation
                self._log_operation(
                    "activate_broker",
                    f"Activated broker with client_id: {client_id}"
                )
                
                # Convert to dictionary and return
                return broker.to_dict()
        except ClientNotFoundException:
            # Handle broker not found
            self._handle_broker_not_found(client_id)
        except sqlalchemy.exc.SQLAlchemyError as e:
            # Handle database error
            self._handle_db_error(e, f"activate_broker for {client_id}")

    def delete_broker(self, client_id: str) -> Dict[str, Any]:
        """
        Delete a broker.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dict[str, Any]: Deleted broker data as a dictionary
        """
        # Validate client ID
        validate_client_id(client_id)
        
        try:
            # Get database session
            with self._get_db_session() as db:
                # Get broker before deletion for return value
                broker = broker_crud.get_by_client_id_or_404(db, client_id)
                broker_dict = broker.to_dict()
                
                # Delete broker from database
                broker_crud.delete_broker(db, client_id)
                
                # Invalidate cache for this broker
                self.invalidate_broker_cache(client_id)
                
                # Log successful deletion
                self._log_operation(
                    "delete_broker",
                    f"Deleted broker with client_id: {client_id}"
                )
                
                return broker_dict
        except ClientNotFoundException:
            # Handle broker not found
            self._handle_broker_not_found(client_id)
        except sqlalchemy.exc.SQLAlchemyError as e:
            # Handle database error
            self._handle_db_error(e, f"delete_broker for {client_id}")

    def broker_exists(self, client_id: str) -> bool:
        """
        Check if a broker exists by client ID.
        
        Args:
            client_id: Client identifier
            
        Returns:
            bool: True if broker exists, False otherwise
        """
        # Validate client ID
        validate_client_id(client_id)
        
        try:
            # Get database session
            with self._get_db_session() as db:
                # Check if broker exists
                return broker_crud.exists_by_client_id(db, client_id)
        except sqlalchemy.exc.SQLAlchemyError as e:
            # Handle database error and return False
            self._log_operation(
                "broker_exists",
                f"Error checking if broker exists: {str(e)}",
                "ERROR"
            )
            # Return False if there's an error
            return False

    def invalidate_broker_cache(self, client_id: str) -> bool:
        """
        Invalidate cache for a specific broker.
        
        Args:
            client_id: Client identifier
            
        Returns:
            bool: True if cache was invalidated, False otherwise
        """
        try:
            # Generate cache key
            cache_key = self._generate_broker_cache_key(client_id)
            
            # Delete from cache
            deleted = redis_cache.delete(cache_key)
            
            if deleted:
                self._log_operation(
                    "invalidate_broker_cache",
                    f"Invalidated cache for broker: {client_id}"
                )
            
            return deleted
        except Exception as e:
            # Log error and return False
            self._log_operation(
                "invalidate_broker_cache",
                f"Error invalidating cache for broker: {client_id}, error: {str(e)}",
                "ERROR"
            )
            return False

    def _generate_broker_cache_key(self, client_id: str) -> str:
        """
        Generate a cache key for a broker.
        
        Args:
            client_id: Client identifier
            
        Returns:
            str: Cache key string
        """
        return f"{BROKER_CACHE_KEY_PREFIX}:{client_id}"

    def _handle_broker_not_found(self, client_id: str) -> None:
        """
        Handle broker not found errors.
        
        Args:
            client_id: Client identifier
            
        Raises:
            ClientNotFoundException: Always raised with client_id
        """
        self._log_operation(
            "broker_not_found",
            f"Broker not found for client_id: {client_id}",
            "ERROR"
        )
        raise ClientNotFoundException(client_id)


# Create singleton instance
broker_service = BrokerService()