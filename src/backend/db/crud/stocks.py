"""
Implements CRUD (Create, Read, Update, Delete) operations for stock data in the Borrow Rate & Locate Fee Pricing Engine.

This module extends the generic CRUDBase class to provide stock-specific database operations,
including querying by ticker symbol, updating borrow rates, and handling stock metadata.
"""

from typing import List, Optional, Dict, Any, Union

from sqlalchemy import select  # sqlalchemy v2.0.0+
from sqlalchemy.orm import Session  # sqlalchemy v2.0.0+

from .base import CRUDBase
from ..models.stock import Stock
from ...schemas.stock import StockCreate, StockUpdate
from ..utils import get_or_404, execute_with_retry, QueryBuilder
from ...core.exceptions import TickerNotFoundException
from ...utils.logging import setup_logger

# Set up logger
logger = setup_logger('db.crud.stocks')

class CRUDStock(CRUDBase[Stock, StockCreate, StockUpdate]):
    """CRUD operations for Stock model"""
    
    def __init__(self):
        """Initialize the CRUD operations for Stock model"""
        super().__init__(Stock)
    
    def get_by_ticker(self, db: Session, ticker: str) -> Optional[Stock]:
        """
        Get a stock by ticker symbol
        
        Args:
            db: Database session
            ticker: Stock ticker symbol
            
        Returns:
            Stock instance if found, None otherwise
        """
        return self.get(db=db, id=ticker, id_field="ticker")
    
    def get_by_ticker_or_404(self, db: Session, ticker: str) -> Stock:
        """
        Get a stock by ticker symbol or raise TickerNotFoundException
        
        Args:
            db: Database session
            ticker: Stock ticker symbol
            
        Returns:
            Stock instance if found
            
        Raises:
            TickerNotFoundException: If stock not found
        """
        stock = self.get_by_ticker(db, ticker)
        return get_or_404(stock, TickerNotFoundException, ticker)
    
    def get_by_lender_api_id(self, db: Session, lender_api_id: str) -> Optional[Stock]:
        """
        Get a stock by lender API ID
        
        Args:
            db: Database session
            lender_api_id: External lender API identifier
            
        Returns:
            Stock instance if found, None otherwise
        """
        query = select(Stock).where(Stock.lender_api_id == lender_api_id)
        result = execute_with_retry(lambda: db.execute(query).scalars().first())
        return result
    
    def get_stocks_by_borrow_status(
        self, 
        db: Session, 
        borrow_status: str, 
        skip: Optional[int] = None, 
        limit: Optional[int] = None
    ) -> List[Stock]:
        """
        Get stocks filtered by borrow status
        
        Args:
            db: Database session
            borrow_status: Status to filter by
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of stocks with the specified borrow status
        """
        query_builder = QueryBuilder(db, Stock)
        query_builder.filter_by(borrow_status=borrow_status)
        
        return query_builder.execute()
    
    def update_min_borrow_rate(
        self, 
        db: Session, 
        ticker: str, 
        min_borrow_rate: float
    ) -> Optional[Stock]:
        """
        Update the minimum borrow rate for a stock
        
        Args:
            db: Database session
            ticker: Stock ticker symbol
            min_borrow_rate: New minimum borrow rate
            
        Returns:
            Updated stock instance if found, None otherwise
        """
        stock = self.get_by_ticker(db, ticker)
        if not stock:
            return None
            
        return self.update(db, stock, {"min_borrow_rate": min_borrow_rate})
    
    def update_borrow_status(
        self, 
        db: Session, 
        ticker: str, 
        borrow_status: str
    ) -> Optional[Stock]:
        """
        Update the borrow status for a stock
        
        Args:
            db: Database session
            ticker: Stock ticker symbol
            borrow_status: New borrow status
            
        Returns:
            Updated stock instance if found, None otherwise
        """
        stock = self.get_by_ticker(db, ticker)
        if not stock:
            return None
            
        return self.update(db, stock, {"borrow_status": borrow_status})
    
    def create_with_ticker(
        self, 
        db: Session, 
        ticker: str, 
        attributes: Optional[Dict[str, Any]] = None
    ) -> Stock:
        """
        Create a new stock with the given ticker and optional attributes
        
        Args:
            db: Database session
            ticker: Stock ticker symbol
            attributes: Additional attributes for the stock
            
        Returns:
            Created stock instance
        """
        if attributes is None:
            attributes = {}
        
        attributes["ticker"] = ticker
        return self.create(db, attributes)
    
    def upsert(
        self, 
        db: Session, 
        ticker: str, 
        attributes: Dict[str, Any]
    ) -> Stock:
        """
        Create a stock if it doesn't exist, or update it if it does
        
        Args:
            db: Database session
            ticker: Stock ticker symbol
            attributes: Attributes to set on the stock
            
        Returns:
            Created or updated stock instance
        """
        stock = self.get_by_ticker(db, ticker)
        
        if stock:
            return self.update(db, stock, attributes)
        else:
            attributes["ticker"] = ticker
            return self.create(db, attributes)
    
    def remove_by_ticker(self, db: Session, ticker: str) -> Optional[Stock]:
        """
        Remove a stock by ticker symbol
        
        Args:
            db: Database session
            ticker: Stock ticker symbol
            
        Returns:
            Removed stock instance if found, None otherwise
        """
        return self.remove(db, ticker, id_field="ticker")
    
    def exists_by_ticker(self, db: Session, ticker: str) -> bool:
        """
        Check if a stock exists by ticker symbol
        
        Args:
            db: Database session
            ticker: Stock ticker symbol
            
        Returns:
            True if stock exists, False otherwise
        """
        query = select(Stock).where(Stock.ticker == ticker)
        result = execute_with_retry(lambda: db.execute(query).first())
        return result is not None

# Create a singleton instance
stock = CRUDStock()