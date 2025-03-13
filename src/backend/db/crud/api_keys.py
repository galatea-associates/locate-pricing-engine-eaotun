"""
Implements CRUD operations for API keys in the Borrow Rate & Locate Fee Pricing Engine.

This module extends the base CRUD class to provide specialized database operations for API key management,
including creation with secure hashing, validation, retrieval, updates, and deactivation.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from .base import CRUDBase
from ...db.models.api_key import APIKey
from ...schemas.api_key import ApiKeyCreate, ApiKeyUpdate
from ...core.exceptions import ClientNotFoundException, AuthenticationException
from ...core.security import generate_api_key, hash_password, verify_password
from ...utils.logging import setup_logger

# Set up logger
logger = setup_logger('db.crud.api_keys')

# Length of generated API keys
API_KEY_LENGTH = 48


class CRUDAPIKey(CRUDBase[APIKey, ApiKeyCreate, ApiKeyUpdate]):
    """CRUD operations for API keys"""
    
    def __init__(self):
        """Initialize the API key CRUD operations"""
        super().__init__(APIKey)
    
    def create_api_key(self, db: Session, obj_in: ApiKeyCreate) -> Tuple[APIKey, str]:
        """
        Create a new API key with secure hashing
        
        Args:
            db: Database session
            obj_in: API key creation data
            
        Returns:
            Tuple[APIKey, str]: Created API key model and plaintext key
        """
        # Generate a new secure API key
        plaintext_key = generate_api_key(API_KEY_LENGTH)
        
        # Hash the API key for secure storage
        hashed_key = hash_password(plaintext_key)
        
        # Calculate expiration date if provided
        expires_at = None
        if obj_in.expiry_days:
            expires_at = datetime.now() + timedelta(days=obj_in.expiry_days)
        
        # Create API key data
        api_key_data = {
            "key_id": generate_api_key(16),  # Shorter ID for the key
            "client_id": obj_in.client_id,
            "rate_limit": obj_in.rate_limit,
            "expires_at": expires_at,
            "active": True,
            "hashed_key": hashed_key
        }
        
        # Create the API key in the database
        db_obj = super().create(db, api_key_data)
        
        logger.info(f"Created new API key for client {obj_in.client_id}")
        
        # Return both the created model and the plaintext key
        return db_obj, plaintext_key
    
    def get_by_key(self, db: Session, api_key: str) -> Optional[APIKey]:
        """
        Get API key by the plaintext key
        
        Args:
            db: Database session
            api_key: Plaintext API key
            
        Returns:
            Optional[APIKey]: API key if found and valid, None otherwise
        """
        # Get all API keys
        stmt = select(APIKey)
        results = db.execute(stmt).scalars().all()
        
        # Check each key to find a match
        for db_key in results:
            if verify_password(api_key, db_key.hashed_key):
                # Found matching key, check if it's valid
                if db_key.is_valid():
                    logger.debug(f"Found valid API key: {db_key.key_id}")
                    return db_key
                else:
                    logger.warning(f"Found API key {db_key.key_id} but it's not valid (expired or inactive)")
                    return None
        
        logger.warning("API key verification failed: key not found")
        return None
    
    def verify_key(self, db: Session, api_key: str) -> bool:
        """
        Verify if a plaintext API key is valid
        
        Args:
            db: Database session
            api_key: Plaintext API key
            
        Returns:
            bool: True if the key is valid, False otherwise
        """
        return self.get_by_key(db, api_key) is not None
    
    def get_by_client_id(self, db: Session, client_id: str, active_only: bool = True) -> List[APIKey]:
        """
        Get all API keys for a specific client
        
        Args:
            db: Database session
            client_id: Client identifier
            active_only: If True, only return active keys
            
        Returns:
            List[APIKey]: List of API keys for the client
        """
        # Create query for API keys with client_id filter
        stmt = select(APIKey).where(APIKey.client_id == client_id)
        
        # Add active filter if requested
        if active_only:
            stmt = stmt.where(APIKey.active == True)
        
        # Execute query and return results
        results = db.execute(stmt).scalars().all()
        return list(results)
    
    def deactivate(self, db: Session, key_id: str) -> Optional[APIKey]:
        """
        Deactivate an API key
        
        Args:
            db: Database session
            key_id: API key identifier
            
        Returns:
            Optional[APIKey]: Updated API key if found, None otherwise
        """
        # Get the API key
        db_obj = self.get(db, key_id, id_field="key_id")
        if not db_obj:
            logger.warning(f"Cannot deactivate API key: key_id {key_id} not found")
            return None
        
        # Create update object with active=False
        update_data = {"active": False}
        updated_key = self.update(db, db_obj, update_data)
        
        logger.info(f"Deactivated API key {key_id}")
        return updated_key
    
    def extend_expiration(self, db: Session, key_id: str, days: int) -> Optional[APIKey]:
        """
        Extend the expiration date of an API key
        
        Args:
            db: Database session
            key_id: API key identifier
            days: Number of days to extend the expiration
            
        Returns:
            Optional[APIKey]: Updated API key if found, None otherwise
        """
        # Get the API key
        db_obj = self.get(db, key_id, id_field="key_id")
        if not db_obj:
            logger.warning(f"Cannot extend API key expiration: key_id {key_id} not found")
            return None
        
        # Extend the expiration
        db_obj.extend_expiration(days)
        
        # Update the database
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        logger.info(f"Extended expiration of API key {key_id} by {days} days")
        return db_obj
    
    def update_rate_limit(self, db: Session, key_id: str, rate_limit: int) -> Optional[APIKey]:
        """
        Update the rate limit for an API key
        
        Args:
            db: Database session
            key_id: API key identifier
            rate_limit: New rate limit (requests per minute)
            
        Returns:
            Optional[APIKey]: Updated API key if found, None otherwise
        """
        # Get the API key
        db_obj = self.get(db, key_id, id_field="key_id")
        if not db_obj:
            logger.warning(f"Cannot update rate limit: key_id {key_id} not found")
            return None
        
        # Create update object with the new rate_limit
        update_data = {"rate_limit": rate_limit}
        updated_key = self.update(db, db_obj, update_data)
        
        logger.info(f"Updated rate limit for API key {key_id} to {rate_limit}")
        return updated_key
    
    def get_expired_keys(self, db: Session) -> List[APIKey]:
        """
        Get all expired API keys
        
        Args:
            db: Database session
            
        Returns:
            List[APIKey]: List of expired API keys
        """
        current_time = datetime.now()
        
        # Create query for expired and active API keys
        stmt = select(APIKey).where(
            APIKey.expires_at < current_time,
            APIKey.active == True
        )
        
        # Execute query and return results
        results = db.execute(stmt).scalars().all()
        return list(results)
    
    def cleanup_expired_keys(self, db: Session) -> int:
        """
        Deactivate all expired API keys
        
        Args:
            db: Database session
            
        Returns:
            int: Number of deactivated keys
        """
        # Get all expired keys
        expired_keys = self.get_expired_keys(db)
        
        # Deactivate each key
        deactivated_count = 0
        for key in expired_keys:
            self.deactivate(db, key.key_id)
            deactivated_count += 1
        
        if deactivated_count > 0:
            logger.info(f"Cleaned up {deactivated_count} expired API keys")
        
        return deactivated_count


# Create a singleton instance
api_key_crud = CRUDAPIKey()