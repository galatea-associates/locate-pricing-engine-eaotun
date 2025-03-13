"""
Implements CRUD operations for audit logs in the Borrow Rate & Locate Fee Pricing Engine.

This module provides database access methods for creating, retrieving, and filtering audit records 
that track all fee calculations, data source usage, and system events to ensure regulatory compliance 
and support troubleshooting.
"""

from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union

from .base import CRUDBase
from ..models.audit import AuditLog
from ...schemas.audit import AuditLogSchema, AuditLogFilterSchema, AuditLogResponseSchema


class CRUDAudit(CRUDBase[AuditLog, AuditLogSchema, AuditLogSchema]):
    """CRUD operations for audit logs"""
    
    def __init__(self):
        """Initialize the CRUD operations for AuditLog model"""
        super().__init__(AuditLog)
    
    def create_audit_log(self, db: Session, audit_log: AuditLogSchema) -> AuditLog:
        """
        Create a new audit log entry
        
        Args:
            db: Database session
            audit_log: Audit log data to create
            
        Returns:
            AuditLog: Created audit log record
        """
        audit_log_data = audit_log.dict() if hasattr(audit_log, 'dict') else dict(audit_log)
        db_audit_log = self.create(db, obj_in=audit_log_data)
        return db_audit_log
    
    def get_audit_log(self, db: Session, audit_id: UUID) -> Optional[AuditLog]:
        """
        Get a specific audit log by ID
        
        Args:
            db: Database session
            audit_id: Unique identifier of the audit log
            
        Returns:
            Optional[AuditLog]: Found audit log or None
        """
        return self.get(db, id=audit_id, id_field="audit_id")
    
    def filter_audit_logs(self, db: Session, filters: AuditLogFilterSchema) -> AuditLogResponseSchema:
        """
        Filter audit logs based on various criteria with pagination
        
        Args:
            db: Database session
            filters: Filter criteria
            
        Returns:
            AuditLogResponseSchema: Paginated audit logs matching the filters
        """
        # Build the base query
        query = select(AuditLog)
        
        # Initialize filter conditions list
        conditions = []
        
        # Add filter conditions based on provided filters
        if filters.client_id:
            conditions.append(AuditLog.client_id == filters.client_id)
        
        if filters.ticker:
            conditions.append(AuditLog.ticker == filters.ticker)
        
        if filters.start_date:
            conditions.append(AuditLog.timestamp >= filters.start_date)
        
        if filters.end_date:
            conditions.append(AuditLog.timestamp <= filters.end_date)
        
        if filters.min_position_value:
            conditions.append(AuditLog.position_value >= filters.min_position_value)
        
        if filters.max_position_value:
            conditions.append(AuditLog.position_value <= filters.max_position_value)
        
        if filters.min_borrow_rate:
            conditions.append(AuditLog.borrow_rate_used >= filters.min_borrow_rate)
        
        if filters.max_borrow_rate:
            conditions.append(AuditLog.borrow_rate_used <= filters.max_borrow_rate)
        
        # Apply all conditions to the query if there are any
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = db.execute(count_query).scalar_one()
        
        # Apply pagination
        page = filters.page or 1
        page_size = filters.page_size or 50
        offset = (page - 1) * page_size
        
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        results = db.execute(query).scalars().all()
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size
        
        # Build response
        return AuditLogResponseSchema(
            items=[result.to_schema() for result in results],
            total=total,
            page=page,
            page_size=page_size,
            pages=total_pages
        )
    
    def get_audit_logs_by_client(self, db: Session, client_id: str, skip: Optional[int] = 0, limit: Optional[int] = 100) -> List[AuditLog]:
        """
        Get audit logs for a specific client
        
        Args:
            db: Database session
            client_id: Client identifier
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[AuditLog]: List of audit logs for the client
        """
        query = select(AuditLog).where(AuditLog.client_id == client_id)
        
        if skip is not None:
            query = query.offset(skip)
        
        if limit is not None:
            query = query.limit(limit)
        
        results = db.execute(query).scalars().all()
        return list(results)
    
    def get_audit_logs_by_ticker(self, db: Session, ticker: str, skip: Optional[int] = 0, limit: Optional[int] = 100) -> List[AuditLog]:
        """
        Get audit logs for a specific ticker
        
        Args:
            db: Database session
            ticker: Stock symbol
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[AuditLog]: List of audit logs for the ticker
        """
        query = select(AuditLog).where(AuditLog.ticker == ticker)
        
        if skip is not None:
            query = query.offset(skip)
        
        if limit is not None:
            query = query.limit(limit)
        
        results = db.execute(query).scalars().all()
        return list(results)
    
    def get_audit_logs_by_date_range(self, db: Session, start_date: datetime, end_date: datetime, skip: Optional[int] = 0, limit: Optional[int] = 100) -> List[AuditLog]:
        """
        Get audit logs within a specific date range
        
        Args:
            db: Database session
            start_date: Start of date range
            end_date: End of date range
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[AuditLog]: List of audit logs within the date range
        """
        query = select(AuditLog).where(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date
            )
        )
        
        if skip is not None:
            query = query.offset(skip)
        
        if limit is not None:
            query = query.limit(limit)
        
        results = db.execute(query).scalars().all()
        return list(results)
    
    def get_audit_logs_with_fallback(self, db: Session, skip: Optional[int] = 0, limit: Optional[int] = 100) -> List[AuditLog]:
        """
        Get audit logs where fallback mechanisms were used
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[AuditLog]: List of audit logs with fallback usage
        """
        # For PostgreSQL JSONB data_sources field, find logs where any source has is_fallback=true
        query = select(AuditLog).where(
            AuditLog.data_sources.contains({"is_fallback": True})
        )
        
        if skip is not None:
            query = query.offset(skip)
        
        if limit is not None:
            query = query.limit(limit)
        
        results = db.execute(query).scalars().all()
        
        # As a fallback, filter results again using the model method in case the JSONB query
        # doesn't work as expected with the specific structure of data_sources
        return [result for result in results if result.has_fallback_source()]
    
    def count_audit_logs(self, db: Session) -> int:
        """
        Count the total number of audit logs
        
        Args:
            db: Database session
            
        Returns:
            int: Total count of audit logs
        """
        query = select(func.count()).select_from(AuditLog)
        return db.execute(query).scalar_one()


# Create singleton instance
audit = CRUDAudit()