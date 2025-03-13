"""
Initializes the database package and provides a centralized import point for all database-related components in the Borrow Rate & Locate Fee Pricing Engine. This module simplifies imports throughout the application by exposing key database functionality from various submodules.
"""

# Re-export database models and base class
from .base import (
    Base,
    Stock,
    Broker,
    Volatility,
    APIKey,
    AuditLog
)

# Re-export session management functionality
from .session import (
    get_db,
    init_db,
    get_engine
)

# Use DatabaseSessionManager as DatabaseSession for compatibility
from .session import DatabaseSessionManager as DatabaseSession

# Re-export utility functions
from .utils import (
    get_or_create,
    execute_with_retry,
    update_or_create,
    bulk_insert
)

# Use TransactionManager as TransactionContext for compatibility
from .utils import TransactionManager as TransactionContext

# Define bulk_insert_or_update to combine bulk_insert and update_or_create functionality
def bulk_insert_or_update(session, objects, key_fields=None, batch_size=1000):
    """
    Efficiently insert or update multiple database records.
    
    Args:
        session: SQLAlchemy session
        objects: List of objects to insert or update
        key_fields: List of fields to use for determining if an object exists
        batch_size: Number of objects to process in each batch
        
    Returns:
        None: Modifies database as a side effect
    """
    if not objects:
        return
        
    # If no key fields provided, just do a bulk insert
    if not key_fields:
        return bulk_insert(session, objects, batch_size)
    
    # Process in batches for better performance
    for i in range(0, len(objects), batch_size):
        batch = objects[i:i+batch_size]
        
        # Handle each object in the batch
        for obj in batch:
            # Extract filter criteria based on key fields
            filters = {field: getattr(obj, field) for field in key_fields if hasattr(obj, field)}
            
            # If we couldn't extract all key fields, skip this object
            if len(filters) != len(key_fields):
                continue
            
            # Get the model class
            model_cls = type(obj)
            
            # Extract values from the object's table columns
            values = {}
            if hasattr(model_cls, '__table__'):
                for column in model_cls.__table__.columns:
                    column_name = column.name
                    if column_name not in key_fields and hasattr(obj, column_name):
                        values[column_name] = getattr(obj, column_name)
            
            # Use update_or_create to either update or create the object
            update_or_create(session, model_cls, filters, values)
        
        # Flush after each batch to apply changes
        session.flush()


# Implement QueryBuilder class
class QueryBuilder:
    """
    Helper class for building complex SQLAlchemy queries.
    """
    
    def __init__(self, session, model=None):
        """
        Initialize the query builder with a session and optional model.
        
        Args:
            session: SQLAlchemy session
            model: Optional SQLAlchemy model to query
        """
        self.session = session
        self.query = session.query(model) if model else None
    
    def filter_by(self, **kwargs):
        """
        Filter query by keyword arguments.
        
        Args:
            **kwargs: Filtering criteria
            
        Returns:
            QueryBuilder: Self reference for method chaining
        """
        if self.query is None:
            raise ValueError("Query not initialized. Provide a model in constructor.")
        
        self.query = self.query.filter_by(**kwargs)
        return self
    
    def filter(self, *args):
        """
        Filter query by SQLAlchemy expression.
        
        Args:
            *args: SQLAlchemy filter expressions
            
        Returns:
            QueryBuilder: Self reference for method chaining
        """
        if self.query is None:
            raise ValueError("Query not initialized. Provide a model in constructor.")
        
        self.query = self.query.filter(*args)
        return self
    
    def order_by(self, *args):
        """
        Order query results.
        
        Args:
            *args: SQLAlchemy order criteria
            
        Returns:
            QueryBuilder: Self reference for method chaining
        """
        if self.query is None:
            raise ValueError("Query not initialized. Provide a model in constructor.")
        
        self.query = self.query.order_by(*args)
        return self
    
    def paginate(self, page=1, per_page=20):
        """
        Paginate query results.
        
        Args:
            page: Page number (1-indexed)
            per_page: Number of items per page
            
        Returns:
            QueryBuilder: Self reference for method chaining
        """
        if self.query is None:
            raise ValueError("Query not initialized. Provide a model in constructor.")
        
        offset = (page - 1) * per_page
        self.query = self.query.offset(offset).limit(per_page)
        return self
    
    def execute(self):
        """
        Execute the query and return all results.
        
        Returns:
            list: Query results
        """
        if self.query is None:
            raise ValueError("Query not initialized. Provide a model in constructor.")
        
        return self.query.all()
    
    def first(self):
        """
        Execute the query and return the first result.
        
        Returns:
            Any: First result or None if no results
        """
        if self.query is None:
            raise ValueError("Query not initialized. Provide a model in constructor.")
        
        return self.query.first()
    
    def one_or_none(self):
        """
        Execute the query and return one result or None.
        
        Returns:
            Any: One result or None if no results
            
        Raises:
            sqlalchemy.orm.exc.MultipleResultsFound: If more than one result found
        """
        if self.query is None:
            raise ValueError("Query not initialized. Provide a model in constructor.")
        
        return self.query.one_or_none()