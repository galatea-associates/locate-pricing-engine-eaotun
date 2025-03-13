"""
Stock model definition for the Borrow Rate & Locate Fee Pricing Engine.

This module defines the SQLAlchemy ORM model for stock data, which represents
securities tracked in the system. The Stock model includes essential information
about ticker symbols, borrow status, and minimum borrow rates used in calculations.
"""

from sqlalchemy import Column, String, Enum, Numeric, DateTime, func, Index  # sqlalchemy v2.0.0+
from sqlalchemy.orm import relationship  # sqlalchemy v2.0.0+

from .base import Base, BaseModel
from ...core.constants import BorrowStatus


# Define indexes for efficient querying
idx_stocks_ticker = Index('idx_stocks_ticker', 'ticker')
idx_stocks_lender_id = Index('idx_stocks_lender_id', 'lender_api_id')


class Stock(Base, BaseModel):
    """
    SQLAlchemy ORM model representing a stock in the database.
    
    This model stores essential stock information needed for borrow rate calculations,
    including the ticker symbol, borrow status category, minimum borrow rate, and
    external API identifiers.
    """
    # Override the table name from BaseModel's default
    __tablename__ = 'stocks'
    
    # Override the id column from BaseModel - we'll use ticker as our primary key
    id = None
    
    # Stock-specific columns
    ticker = Column(String(10), primary_key=True, index=True)
    borrow_status = Column(Enum(BorrowStatus), nullable=False, default=BorrowStatus.EASY)
    lender_api_id = Column(String(50), nullable=True, unique=True, index=True)
    min_borrow_rate = Column(Numeric(5, 2), nullable=False, default=0.0)
    last_updated = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    volatility_data = relationship('Volatility', back_populates='stock', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        """
        Default constructor for the Stock model.
        
        Args:
            **kwargs: Any model attributes to set.
        """
        super().__init__(**kwargs)
    
    def __repr__(self):
        """
        String representation of the Stock instance.
        
        Returns:
            str: String representation with ticker and borrow_status.
        """
        return f"Stock(ticker='{self.ticker}', borrow_status={self.borrow_status})"