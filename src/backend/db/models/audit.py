"""
Audit Log Model for the Borrow Rate & Locate Fee Pricing Engine.

This module defines the SQLAlchemy model for comprehensive audit logs of all fee
calculations, supporting regulatory compliance (SEC Rule 17a-4), troubleshooting,
and business analytics with a 7-year retention requirement.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base, BaseModel


class AuditLog(Base):
    """
    SQLAlchemy model for storing comprehensive audit logs of all fee calculations.
    
    This model captures detailed information about each fee calculation to support:
    - Regulatory compliance with SEC Rule 17a-4 (7-year retention)
    - Troubleshooting of calculation issues
    - Analysis of pricing patterns and fallback usage
    - Detection of unusual fee patterns
    
    The model uses PostgreSQL-specific types (UUID, JSONB) for efficiency and
    includes indexes on frequently queried fields.
    """
    __tablename__ = 'auditlog'
    
    # Primary identifier
    audit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core calculation identifiers
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    client_id = Column(String(50), nullable=False, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    
    # Calculation inputs
    position_value = Column(Numeric(15, 2), nullable=False)
    loan_days = Column(Integer, nullable=False)
    
    # Calculation outputs
    borrow_rate_used = Column(Numeric(5, 4), nullable=False)
    total_fee = Column(Numeric(15, 2), nullable=False)
    
    # Detailed information
    data_sources = Column(JSONB, nullable=False)
    calculation_breakdown = Column(JSONB, nullable=False)
    
    # Request context for troubleshooting
    request_id = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(50), nullable=True)
    
    # Define composite indexes for common query patterns
    __table_args__ = (
        Index('ix_auditlog_client_timestamp', 'client_id', 'timestamp'),
        Index('ix_auditlog_ticker_timestamp', 'ticker', 'timestamp'),
    )
    
    def __init__(self, **kwargs):
        """
        Default constructor for the AuditLog model.
        
        Args:
            **kwargs: Any model attributes to set.
        """
        super().__init__(**kwargs)
        if 'timestamp' not in kwargs:
            self.timestamp = datetime.utcnow()
    
    def has_fallback_source(self):
        """
        Check if any data sources used fallback mechanisms.
        
        This method helps identify calculations where external data was unavailable
        and fallback values were used instead.
        
        Returns:
            bool: True if fallback mechanisms were used, False otherwise.
        """
        if not self.data_sources:
            return False
            
        for source_name, source_data in self.data_sources.items():
            if source_data.get('is_fallback', False):
                return True
        
        return False
    
    def to_schema(self):
        """
        Convert database model to Pydantic schema.
        
        This method creates a Pydantic schema representation of the audit log
        for use in API responses and data validation.
        
        Returns:
            AuditLogSchema: Pydantic schema representation.
        """
        # This import is here to avoid circular dependencies
        from ...schemas.audit import AuditLogSchema
        
        return AuditLogSchema(
            audit_id=self.audit_id,
            timestamp=self.timestamp,
            client_id=self.client_id,
            ticker=self.ticker,
            position_value=self.position_value,
            loan_days=self.loan_days,
            borrow_rate_used=self.borrow_rate_used,
            total_fee=self.total_fee,
            data_sources=self.data_sources,
            calculation_breakdown=self.calculation_breakdown,
            request_id=self.request_id,
            user_agent=self.user_agent,
            ip_address=self.ip_address
        )