"""
Implements CRUD (Create, Read, Update, Delete) operations for volatility data in the Borrow Rate & Locate Fee Pricing Engine.
This module extends the generic CRUDBase class to provide volatility-specific database operations, including querying by stock ID
and timestamp, retrieving historical volatility data, and managing event risk factors.
"""

from sqlalchemy import select, and_, desc, func  # sqlalchemy v2.0.0+
from sqlalchemy.orm import Session  # sqlalchemy v2.0.0+
from typing import List, Optional, Dict, Any, Union, Tuple

from datetime import datetime

from .base import CRUDBase
from ..models.volatility import Volatility
from ...schemas.volatility import VolatilityCreate, VolatilityUpdate
from ..utils import get_or_404, execute_with_retry, QueryBuilder
from ...core.exceptions import TickerNotFoundException
from ...utils.logging import setup_logger

# Set up logger
logger = setup_logger('db.crud.volatility')


class CRUDVolatility(CRUDBase[Volatility, VolatilityCreate, VolatilityUpdate]):
    """
    CRUD operations for Volatility model
    """
    
    def __init__(self):
        """
        Initialize the CRUD operations for Volatility model
        """
        super().__init__(Volatility)
    
    def get_by_stock_and_timestamp(
        self, db: Session, stock_id: str, timestamp: datetime
    ) -> Optional[Volatility]:
        """
        Get a volatility record by stock_id and timestamp
        
        Args:
            db: Database session
            stock_id: Stock ticker symbol
            timestamp: Timestamp of the volatility record
            
        Returns:
            Volatility instance if found, None otherwise
        """
        query = select(Volatility).where(
            and_(
                Volatility.stock_id == stock_id,
                Volatility.timestamp == timestamp
            )
        )
        result = execute_with_retry(lambda: db.execute(query).scalars().first())
        return result
    
    def get_by_stock_and_timestamp_or_404(
        self, db: Session, stock_id: str, timestamp: datetime
    ) -> Volatility:
        """
        Get a volatility record by stock_id and timestamp or raise TickerNotFoundException
        
        Args:
            db: Database session
            stock_id: Stock ticker symbol
            timestamp: Timestamp of the volatility record
            
        Returns:
            Volatility instance if found
            
        Raises:
            TickerNotFoundException: If volatility record is not found
        """
        result = self.get_by_stock_and_timestamp(db=db, stock_id=stock_id, timestamp=timestamp)
        if result is None:
            raise TickerNotFoundException(stock_id)
        return result
    
    def get_latest_by_stock(
        self, db: Session, stock_id: str
    ) -> Optional[Volatility]:
        """
        Get the latest volatility record for a stock
        
        Args:
            db: Database session
            stock_id: Stock ticker symbol
            
        Returns:
            Latest Volatility instance if found, None otherwise
        """
        query = select(Volatility).where(
            Volatility.stock_id == stock_id
        ).order_by(desc(Volatility.timestamp)).limit(1)
        
        result = execute_with_retry(lambda: db.execute(query).scalars().first())
        return result
    
    def get_latest_by_stock_or_404(
        self, db: Session, stock_id: str
    ) -> Volatility:
        """
        Get the latest volatility record for a stock or raise TickerNotFoundException
        
        Args:
            db: Database session
            stock_id: Stock ticker symbol
            
        Returns:
            Latest Volatility instance if found
            
        Raises:
            TickerNotFoundException: If no volatility records are found for the stock
        """
        result = self.get_latest_by_stock(db=db, stock_id=stock_id)
        if result is None:
            raise TickerNotFoundException(stock_id)
        return result
    
    def get_historical_by_stock(
        self, 
        db: Session, 
        stock_id: str, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Volatility]:
        """
        Get historical volatility records for a stock within a date range
        
        Args:
            db: Database session
            stock_id: Stock ticker symbol
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            limit: Optional maximum number of records to return
            
        Returns:
            List of Volatility instances within the date range
        """
        query_builder = QueryBuilder(db, Volatility)
        query_builder.filter_by(stock_id=stock_id)
        
        if start_date or end_date:
            query_builder.date_range(Volatility.timestamp, start_date, end_date)
        
        query_builder.order_by(desc(Volatility.timestamp))
        
        if limit:
            query_builder.limit(limit)
        
        return query_builder.execute()
    
    def create_volatility(
        self, db: Session, obj_in: Union[VolatilityCreate, Dict[str, Any]]
    ) -> Volatility:
        """
        Create a new volatility record
        
        Args:
            db: Database session
            obj_in: Volatility data for creation
            
        Returns:
            Created Volatility instance
        """
        return self.create(db=db, obj_in=obj_in)
    
    def update_volatility(
        self, 
        db: Session, 
        db_obj: Volatility, 
        obj_in: Union[VolatilityUpdate, Dict[str, Any]]
    ) -> Volatility:
        """
        Update an existing volatility record
        
        Args:
            db: Database session
            db_obj: Existing Volatility instance
            obj_in: Updated volatility data
            
        Returns:
            Updated Volatility instance
        """
        return self.update(db=db, db_obj=db_obj, obj_in=obj_in)
    
    def remove_by_stock_and_timestamp(
        self, db: Session, stock_id: str, timestamp: datetime
    ) -> Optional[Volatility]:
        """
        Remove a volatility record by stock_id and timestamp
        
        Args:
            db: Database session
            stock_id: Stock ticker symbol
            timestamp: Timestamp of the volatility record
            
        Returns:
            Removed Volatility instance if found, None otherwise
        """
        obj = self.get_by_stock_and_timestamp(db=db, stock_id=stock_id, timestamp=timestamp)
        if obj is None:
            return None
        
        db.delete(obj)
        db.commit()
        
        return obj
    
    def get_average_volatility(
        self, 
        db: Session, 
        stock_id: str, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> Optional[float]:
        """
        Get the average volatility index for a stock over a time period
        
        Args:
            db: Database session
            stock_id: Stock ticker symbol
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            Average volatility index or None if no data
        """
        query = select(func.avg(Volatility.vol_index)).where(
            Volatility.stock_id == stock_id
        )
        
        if start_date:
            query = query.where(Volatility.timestamp >= start_date)
        
        if end_date:
            query = query.where(Volatility.timestamp <= end_date)
        
        result = execute_with_retry(lambda: db.execute(query).scalar())
        return result
    
    def get_max_event_risk(
        self, 
        db: Session, 
        stock_id: str, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> Optional[int]:
        """
        Get the maximum event risk factor for a stock over a time period
        
        Args:
            db: Database session
            stock_id: Stock ticker symbol
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            Maximum event risk factor or None if no data
        """
        query = select(func.max(Volatility.event_risk_factor)).where(
            Volatility.stock_id == stock_id
        )
        
        if start_date:
            query = query.where(Volatility.timestamp >= start_date)
        
        if end_date:
            query = query.where(Volatility.timestamp <= end_date)
        
        result = execute_with_retry(lambda: db.execute(query).scalar())
        return result
    
    def bulk_create_volatility(
        self, db: Session, objs_in: List[Union[VolatilityCreate, Dict[str, Any]]]
    ) -> List[Volatility]:
        """
        Create multiple volatility records in a single transaction
        
        Args:
            db: Database session
            objs_in: List of volatility data for creation
            
        Returns:
            List of created Volatility instances
        """
        db_objs = []
        
        for obj_in in objs_in:
            if not isinstance(obj_in, dict):
                obj_in_data = obj_in.dict() if hasattr(obj_in, 'dict') else dict(obj_in)
            else:
                obj_in_data = obj_in
            
            db_obj = Volatility(**obj_in_data)
            db_objs.append(db_obj)
        
        db.add_all(db_objs)
        db.commit()
        
        for db_obj in db_objs:
            db.refresh(db_obj)
        
        return db_objs
    
    def exists_for_stock(self, db: Session, stock_id: str) -> bool:
        """
        Check if volatility data exists for a stock
        
        Args:
            db: Database session
            stock_id: Stock ticker symbol
            
        Returns:
            True if volatility data exists, False otherwise
        """
        query = select(Volatility).where(Volatility.stock_id == stock_id).limit(1)
        result = execute_with_retry(lambda: db.execute(query).first())
        return result is not None


# Create a singleton instance for application-wide use
volatility = CRUDVolatility()