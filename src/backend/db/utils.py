"""
Database utility module providing common database operations and helper functions for the
Borrow Rate & Locate Fee Pricing Engine.

This module implements retry logic for database operations, transaction management utilities,
and helper functions for common database tasks.
"""

import sqlalchemy  # sqlalchemy 2.0.0+
from sqlalchemy.orm import Session
import contextlib
import typing
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar
import asyncio

from ..utils.logging import setup_logger
from ..utils.retry import retry, retry_async

# Set up logger for database operations
logger = setup_logger('db.utils')

# Default retry parameters
DEFAULT_RETRY_COUNT = 3
DEFAULT_BACKOFF_FACTOR = 2.0
# Database exceptions that should trigger a retry
DATABASE_EXCEPTIONS = (sqlalchemy.exc.OperationalError, sqlalchemy.exc.DatabaseError)

# Type variable for SQLAlchemy model classes
T = TypeVar('T')

def execute_with_retry(func: Callable, max_retries: int = DEFAULT_RETRY_COUNT, 
                      backoff_factor: float = DEFAULT_BACKOFF_FACTOR) -> Any:
    """
    Execute a database operation with retry logic for transient failures.
    
    Args:
        func: The function to execute
        max_retries: Maximum number of retry attempts
        backoff_factor: Factor to multiply wait time by for each attempt
        
    Returns:
        Any: Result of the database operation
    """
    # Apply retry decorator with specified parameters
    retryable_func = retry(
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        exceptions_to_retry=DATABASE_EXCEPTIONS
    )(func)
    
    try:
        return retryable_func()
    except DATABASE_EXCEPTIONS as e:
        logger.error(f"Database operation failed after {max_retries} retries: {str(e)}")
        raise

def execute_async_with_retry(func: Callable, max_retries: int = DEFAULT_RETRY_COUNT,
                            backoff_factor: float = DEFAULT_BACKOFF_FACTOR) -> Any:
    """
    Execute an async database operation with retry logic for transient failures.
    
    Args:
        func: The async function to execute
        max_retries: Maximum number of retry attempts
        backoff_factor: Factor to multiply wait time by for each attempt
        
    Returns:
        Any: Result of the async database operation
    """
    # Apply async retry decorator with specified parameters
    retryable_func = retry_async(
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        exceptions_to_retry=DATABASE_EXCEPTIONS
    )(func)
    
    async def execute():
        try:
            return await retryable_func()
        except DATABASE_EXCEPTIONS as e:
            logger.error(f"Async database operation failed after {max_retries} retries: {str(e)}")
            raise
    
    return execute()

@contextlib.contextmanager
def transaction(session: sqlalchemy.orm.Session) -> typing.Generator:
    """
    Context manager for database transaction management.
    
    Args:
        session: SQLAlchemy session
        
    Returns:
        contextlib.AbstractContextManager: Transaction context manager
    
    Example:
        with transaction(session) as tx:
            session.add(my_object)
    """
    try:
        # Begin transaction
        session.begin()
        # Yield control back to the caller
        yield session
        # If no exceptions, commit the transaction
        session.commit()
    except Exception as e:
        # If an exception occurs, rollback the transaction
        session.rollback()
        logger.error(f"Transaction failed and was rolled back: {str(e)}")
        # Re-raise the exception
        raise

def bulk_insert(session: sqlalchemy.orm.Session, objects: List[Any], 
               batch_size: int = 1000) -> None:
    """
    Efficiently insert multiple records into the database.
    
    Args:
        session: SQLAlchemy session
        objects: List of objects to insert
        batch_size: Number of objects to insert in each batch
        
    Returns:
        None: Inserts records as a side effect
    """
    if not objects:
        logger.debug("No objects to bulk insert")
        return
    
    # Determine the appropriate batch size
    actual_batch_size = min(batch_size, len(objects))
    
    # Calculate number of batches
    num_objects = len(objects)
    num_batches = (num_objects + actual_batch_size - 1) // actual_batch_size
    
    logger.info(f"Bulk inserting {num_objects} objects in {num_batches} batches")
    
    # Process objects in batches
    for i in range(0, num_objects, actual_batch_size):
        batch = objects[i:i + actual_batch_size]
        try:
            # Add all objects in the batch to the session
            session.add_all(batch)
            # Flush the session to insert records efficiently
            session.flush()
            logger.debug(f"Inserted batch {i // actual_batch_size + 1}/{num_batches} ({len(batch)} records)")
        except sqlalchemy.exc.SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error bulk inserting batch {i // actual_batch_size + 1}: {str(e)}")
            raise
    
    logger.info(f"Successfully inserted {num_objects} records in {num_batches} batches")

def get_or_create(session: sqlalchemy.orm.Session, model: Type[T], filters: Dict[str, Any], 
                 defaults: Optional[Dict[str, Any]] = None) -> Tuple[T, bool]:
    """
    Get an existing record or create it if it doesn't exist.
    
    Args:
        session: SQLAlchemy session
        model: The model class
        filters: Dict of filters to apply when searching for the record
        defaults: Dict of default values to use when creating a new record
        
    Returns:
        Tuple[sqlalchemy.orm.DeclarativeBase, bool]: The instance and whether it was created
    """
    instance = session.query(model).filter_by(**filters).first()
    
    if instance:
        return instance, False
    else:
        # Combine filters and defaults to create a new instance
        params = dict(filters)
        if defaults:
            params.update(defaults)
            
        try:
            instance = model(**params)
            session.add(instance)
            session.flush()
            logger.debug(f"Created new {model.__name__} instance with filters: {filters}")
            return instance, True
        except sqlalchemy.exc.SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating {model.__name__} instance: {str(e)}")
            raise

def update_or_create(session: sqlalchemy.orm.Session, model: Type[T], filters: Dict[str, Any], 
                    values: Dict[str, Any]) -> Tuple[T, bool]:
    """
    Update an existing record or create it if it doesn't exist.
    
    Args:
        session: SQLAlchemy session
        model: The model class
        filters: Dict of filters to apply when searching for the record
        values: Dict of values to update or use when creating
        
    Returns:
        Tuple[sqlalchemy.orm.DeclarativeBase, bool]: The instance and whether it was created
    """
    instance = session.query(model).filter_by(**filters).first()
    
    if instance:
        # Update existing instance
        for key, value in values.items():
            setattr(instance, key, value)
        logger.debug(f"Updated {model.__name__} instance with filters: {filters}")
        return instance, False
    else:
        # Combine filters and values to create a new instance
        params = dict(filters)
        params.update(values)
            
        try:
            instance = model(**params)
            session.add(instance)
            session.flush()
            logger.debug(f"Created new {model.__name__} instance with filters: {filters}")
            return instance, True
        except sqlalchemy.exc.SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating {model.__name__} instance: {str(e)}")
            raise

def execute_raw_sql(session: sqlalchemy.orm.Session, sql: str, params: Optional[Dict[str, Any]] = None) -> sqlalchemy.engine.Result:
    """
    Execute a raw SQL query with parameters.
    
    Args:
        session: SQLAlchemy session
        sql: SQL query string
        params: Dict of parameters to bind to the query
        
    Returns:
        sqlalchemy.engine.Result: Query result
    """
    # Mask sensitive data in logs
    log_params = params.copy() if params else {}
    for key in log_params:
        if 'password' in key.lower() or 'secret' in key.lower() or 'key' in key.lower():
            log_params[key] = '******'
    
    logger.debug(f"Executing raw SQL: {sql} with params: {log_params}")
    
    try:
        result = session.execute(sqlalchemy.text(sql), params or {})
        return result
    except sqlalchemy.exc.SQLAlchemyError as e:
        logger.error(f"Error executing raw SQL: {str(e)}")
        raise

class TransactionManager:
    """
    Advanced transaction manager with savepoint support.
    """
    
    def __init__(self, session: sqlalchemy.orm.Session, nested: bool = False):
        """
        Initialize the transaction manager.
        
        Args:
            session: SQLAlchemy session
            nested: Whether to use nested transactions (savepoints)
        """
        self.session = session
        self.nested = nested
        self._transaction = None
    
    def __enter__(self):
        """
        Enter the transaction context.
        
        Returns:
            TransactionManager: Self reference for context manager
        """
        # Begin a nested transaction (savepoint) if nested=True
        if self.nested:
            self._transaction = self.session.begin_nested()
        else:
            self._transaction = self.session.begin()
        
        logger.debug(f"Started {'nested ' if self.nested else ''}transaction")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the transaction context with commit or rollback.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
            
        Returns:
            bool: False to propagate exceptions
        """
        if exc_type is not None:
            # An exception occurred, rollback the transaction
            self._transaction.rollback()
            logger.debug(f"Rolled back {'nested ' if self.nested else ''}transaction due to exception: {str(exc_val)}")
        else:
            # No exception, commit the transaction
            self._transaction.commit()
            logger.debug(f"Committed {'nested ' if self.nested else ''}transaction")
        
        # Return False to propagate any exceptions
        return False