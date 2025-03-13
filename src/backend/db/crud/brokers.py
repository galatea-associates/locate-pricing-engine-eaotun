"""
Implements CRUD (Create, Read, Update, Delete) operations for broker data in the Borrow Rate & Locate Fee Pricing Engine.

This module extends the generic CRUDBase class to provide broker-specific database operations, including querying by client ID, filtering active brokers, and handling broker-specific validation logic.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from .base import CRUDBase
from ..models.broker import Broker
from ...schemas.broker import BrokerCreate, BrokerUpdate
from ..utils import get_or_404, execute_with_retry
from ...core.exceptions import ClientNotFoundException
from ...utils.logging import setup_logger

# Set up module logger
logger = setup_logger('db.crud.brokers')

class CRUDBroker(CRUDBase[Broker, BrokerCreate, BrokerUpdate]):
    """CRUD operations for broker data"""
    
    def __init__(self):
        """Initialize the broker CRUD operations"""
        super().__init__(Broker)
    
    def get_by_client_id(self, db: Session, client_id: str) -> Optional[Broker]:
        """
        Get a broker by client ID
        
        Args:
            db: Database session
            client_id: Client ID to search for
            
        Returns:
            Broker instance if found, None otherwise
        """
        query = select(self.model).where(self.model.client_id == client_id)
        result = execute_with_retry(lambda: db.execute(query).scalars().first())
        return result
    
    def get_by_client_id_or_404(self, db: Session, client_id: str) -> Broker:
        """
        Get a broker by client ID or raise a not found exception
        
        Args:
            db: Database session
            client_id: Client ID to search for
            
        Returns:
            Broker instance if found
            
        Raises:
            ClientNotFoundException: If broker is not found
        """
        broker = self.get_by_client_id(db, client_id)
        if broker is None:
            raise ClientNotFoundException(client_id)
        return broker
    
    def get_active_brokers(
        self, db: Session, skip: Optional[int] = None, limit: Optional[int] = None
    ) -> List[Broker]:
        """
        Get all active brokers
        
        Args:
            db: Database session
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of active broker instances
        """
        query = select(self.model).where(self.model.active == True)
        
        if skip is not None:
            query = query.offset(skip)
        
        if limit is not None:
            query = query.limit(limit)
        
        results = execute_with_retry(lambda: db.execute(query).scalars().all())
        return list(results)
    
    def create_broker(self, db: Session, broker_in: BrokerCreate) -> Broker:
        """
        Create a new broker
        
        Args:
            db: Database session
            broker_in: Broker data for creation
            
        Returns:
            Created broker instance
        """
        # Check if broker with the same client_id already exists
        if self.exists_by_client_id(db, broker_in.client_id):
            logger.warning(f"Broker with client_id '{broker_in.client_id}' already exists")
            return self.get_by_client_id(db, broker_in.client_id)
        
        # Create new broker
        return super().create(db, broker_in)
    
    def update_broker(self, db: Session, client_id: str, broker_in: BrokerUpdate) -> Broker:
        """
        Update an existing broker
        
        Args:
            db: Database session
            client_id: Client ID of broker to update
            broker_in: Updated broker data
            
        Returns:
            Updated broker instance
        """
        broker = self.get_by_client_id_or_404(db, client_id)
        return super().update(db, broker, broker_in)
    
    def deactivate_broker(self, db: Session, client_id: str) -> Broker:
        """
        Deactivate a broker by setting active to False
        
        Args:
            db: Database session
            client_id: Client ID of broker to deactivate
            
        Returns:
            Deactivated broker instance
        """
        broker = self.get_by_client_id_or_404(db, client_id)
        broker.active = False
        db.add(broker)
        db.commit()
        return broker
    
    def activate_broker(self, db: Session, client_id: str) -> Broker:
        """
        Activate a broker by setting active to True
        
        Args:
            db: Database session
            client_id: Client ID of broker to activate
            
        Returns:
            Activated broker instance
        """
        broker = self.get_by_client_id_or_404(db, client_id)
        broker.active = True
        db.add(broker)
        db.commit()
        return broker
    
    def delete_broker(self, db: Session, client_id: str) -> Broker:
        """
        Delete a broker from the database
        
        Args:
            db: Database session
            client_id: Client ID of broker to delete
            
        Returns:
            Deleted broker instance
        """
        broker = super().remove(db, client_id, id_field="client_id")
        if broker is None:
            raise ClientNotFoundException(client_id)
        return broker
    
    def exists_by_client_id(self, db: Session, client_id: str) -> bool:
        """
        Check if a broker exists by client ID
        
        Args:
            db: Database session
            client_id: Client ID to check
            
        Returns:
            True if broker exists, False otherwise
        """
        query = select(self.model).where(self.model.client_id == client_id)
        result = execute_with_retry(lambda: db.execute(query).first())
        return result is not None

# Create a singleton instance for application-wide use
broker_crud = CRUDBroker()