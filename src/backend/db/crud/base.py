"""
Base CRUD module for the Borrow Rate & Locate Fee Pricing Engine.

This module provides a generic base class for CRUD (Create, Read, Update, Delete) 
operations that can be extended by model-specific CRUD modules. It ensures consistent 
data access patterns across the application and implements best practices for 
database operations including retry logic, error handling, and type safety.
"""

from typing import Generic, TypeVar, Type, Optional, Any, Dict, List, Union
from sqlalchemy import select, update, delete  # sqlalchemy v2.0.0+
from sqlalchemy.orm import Session  # sqlalchemy v2.0.0+

from ..models.base import BaseModel
from ..utils import get_or_404, execute_with_retry
from ...core.exceptions import BaseAPIException

# Define type variables for generic typing
ModelType = TypeVar('ModelType', bound=BaseModel)
CreateSchemaType = TypeVar('CreateSchemaType')
UpdateSchemaType = TypeVar('UpdateSchemaType')


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic base class for CRUD operations on database models.
    
    This class provides standard implementations for common database operations
    like create, read, update, and delete. It uses SQLAlchemy for database
    interactions and implements retry logic for handling transient failures.
    
    Attributes:
        model (Type[ModelType]): The SQLAlchemy model class this CRUD handles
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Initialize the CRUD base class with a model.
        
        Args:
            model: The SQLAlchemy model class this CRUD will operate on
        """
        self.model = model
    
    def get(self, db: Session, id: Any, id_field: str = "id") -> Optional[ModelType]:
        """
        Get a single record by ID or another field.
        
        Args:
            db: Database session
            id: Value to search for
            id_field: Field name to search by (defaults to "id")
            
        Returns:
            Model instance if found, None otherwise
        """
        query = select(self.model).where(getattr(self.model, id_field) == id)
        result = execute_with_retry(lambda: db.execute(query).scalars().first())
        return result
    
    def get_or_404(
        self,
        db: Session,
        id: Any,
        id_field: str = "id",
        exception_class: Type[BaseAPIException] = BaseAPIException,
        error_message: str = "Record not found"
    ) -> ModelType:
        """
        Get a record by ID or raise a not found exception.
        
        Args:
            db: Database session
            id: Value to search for
            id_field: Field name to search by (defaults to "id")
            exception_class: Exception class to raise if not found
            error_message: Error message if record not found
            
        Returns:
            Model instance if found
            
        Raises:
            exception_class: If record is not found
        """
        result = self.get(db=db, id=id, id_field=id_field)
        return get_or_404(result, exception_class, error_message)
    
    def get_multi(
        self,
        db: Session,
        skip: Optional[int] = 0,
        limit: Optional[int] = 100
    ) -> List[ModelType]:
        """
        Get multiple records with optional pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of model instances
        """
        query = select(self.model)
        
        if skip is not None:
            query = query.offset(skip)
        
        if limit is not None:
            query = query.limit(limit)
        
        results = execute_with_retry(lambda: db.execute(query).scalars().all())
        return list(results)
    
    def create(self, db: Session, obj_in: Union[CreateSchemaType, Dict[str, Any]]) -> ModelType:
        """
        Create a new record.
        
        Args:
            db: Database session
            obj_in: Input data, either as a Pydantic schema or dictionary
            
        Returns:
            Created model instance
        """
        # Convert input to dictionary if it's not already
        if not isinstance(obj_in, dict):
            obj_in_data = obj_in.dict() if hasattr(obj_in, 'dict') else dict(obj_in)
        else:
            obj_in_data = obj_in
        
        # Create model instance
        db_obj = self.model(**obj_in_data)
        
        # Add to database and commit
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        return db_obj
    
    def update(
        self,
        db: Session,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Update an existing record.
        
        Args:
            db: Database session
            db_obj: Existing model instance to update
            obj_in: Update data, either as a Pydantic schema or dictionary
            
        Returns:
            Updated model instance
        """
        # Convert input to dictionary if it's not already
        if not isinstance(obj_in, dict):
            obj_in_data = obj_in.dict(exclude_unset=True) if hasattr(obj_in, 'dict') else dict(obj_in)
        else:
            obj_in_data = obj_in
        
        # Get current data as dictionary
        db_obj_data = db_obj.to_dict()
        
        # Update the dictionary with new values
        for field in db_obj_data:
            if field in obj_in_data:
                setattr(db_obj, field, obj_in_data[field])
        
        # Add to database and commit
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        return db_obj
    
    def remove(self, db: Session, id: Any, id_field: str = "id") -> Optional[ModelType]:
        """
        Remove a record by ID or another field.
        
        Args:
            db: Database session
            id: Value to search for
            id_field: Field name to search by (defaults to "id")
            
        Returns:
            Removed model instance or None if not found
        """
        obj = self.get(db=db, id=id, id_field=id_field)
        if obj is None:
            return None
        
        db.delete(obj)
        db.commit()
        
        return obj
    
    def exists(self, db: Session, id: Any, id_field: str = "id") -> bool:
        """
        Check if a record exists by ID or another field.
        
        Args:
            db: Database session
            id: Value to search for
            id_field: Field name to search by (defaults to "id")
            
        Returns:
            True if record exists, False otherwise
        """
        query = select(self.model).where(getattr(self.model, id_field) == id)
        result = execute_with_retry(lambda: db.execute(query).first())
        return result is not None
    
    def count(self, db: Session) -> int:
        """
        Count the number of records.
        
        Args:
            db: Database session
            
        Returns:
            Number of records
        """
        query = select(self.model.id)  # Use id column for better performance
        result = execute_with_retry(lambda: db.execute(query).all())
        return len(result)