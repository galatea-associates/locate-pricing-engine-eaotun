"""
Implements the data service layer for audit functionality in the Borrow Rate & Locate Fee Pricing Engine.
This module provides methods for retrieving, filtering, and managing audit logs from the database,
supporting regulatory compliance, troubleshooting, and business analytics.
"""

import logging
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from typing import List, Dict, Optional, Union, Any

from sqlalchemy.orm import Session

from .utils import DataServiceBase, validate_ticker, validate_client_id, cache_result
from ...db.crud.audit import audit
from ...schemas.audit import AuditLogSchema, AuditLogFilterSchema, AuditLogResponseSchema

# Configure module logger
logger = logging.getLogger(__name__)

class AuditDataService(DataServiceBase):
    """Service for retrieving and managing audit logs from the database"""
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize the audit data service
        
        Args:
            db: Optional database session. If not provided, one will be created as needed.
        """
        super().__init__()
        self._db = db
    
    def get_audit_log(self, audit_id: Union[str, UUID]) -> Optional[AuditLogSchema]:
        """
        Get a specific audit log by ID
        
        Args:
            audit_id: Unique identifier of the audit log
            
        Returns:
            Optional[AuditLogSchema]: Found audit log or None if not found
        """
        # Convert audit_id to UUID if it's a string
        if isinstance(audit_id, str):
            try:
                audit_id = UUID(audit_id)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {audit_id}")
        
        self._log_operation("get_audit_log", f"Retrieving audit log with ID: {audit_id}")
        
        try:
            with self._get_db_session() as db:
                result = audit.get_audit_log(db, audit_id)
                return result
        except Exception as e:
            self._handle_db_error(e, f"retrieving audit log {audit_id}")
    
    @cache_result(ttl=60)
    def filter_audit_logs(self, filters: AuditLogFilterSchema) -> AuditLogResponseSchema:
        """
        Filter audit logs based on various criteria with pagination
        
        Args:
            filters: Filter criteria for audit logs
            
        Returns:
            AuditLogResponseSchema: Paginated audit logs matching the filters
        """
        self._log_operation("filter_audit_logs", f"Filtering audit logs with criteria: {filters}")
        
        # Validate client_id and ticker if provided
        if filters.client_id:
            validate_client_id(filters.client_id)
        
        if filters.ticker:
            validate_ticker(filters.ticker)
        
        try:
            with self._get_db_session() as db:
                result = audit.filter_audit_logs(db, filters)
                return result
        except Exception as e:
            self._handle_db_error(e, "filtering audit logs")
    
    @cache_result(ttl=60)
    def get_client_audit_logs(self, client_id: str, skip: Optional[int] = None, limit: Optional[int] = None) -> List[AuditLogSchema]:
        """
        Get audit logs for a specific client with pagination
        
        Args:
            client_id: Client identifier
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[AuditLogSchema]: List of audit logs for the client
        """
        # Validate client_id
        validate_client_id(client_id)
        
        self._log_operation("get_client_audit_logs", f"Retrieving audit logs for client: {client_id}")
        
        try:
            with self._get_db_session() as db:
                result = audit.get_audit_logs_by_client(db, client_id, skip, limit)
                return result
        except Exception as e:
            self._handle_db_error(e, f"retrieving audit logs for client {client_id}")
    
    @cache_result(ttl=60)
    def get_ticker_audit_logs(self, ticker: str, skip: Optional[int] = None, limit: Optional[int] = None) -> List[AuditLogSchema]:
        """
        Get audit logs for a specific ticker with pagination
        
        Args:
            ticker: Stock symbol
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[AuditLogSchema]: List of audit logs for the ticker
        """
        # Validate ticker
        validate_ticker(ticker)
        
        self._log_operation("get_ticker_audit_logs", f"Retrieving audit logs for ticker: {ticker}")
        
        try:
            with self._get_db_session() as db:
                result = audit.get_audit_logs_by_ticker(db, ticker, skip, limit)
                return result
        except Exception as e:
            self._handle_db_error(e, f"retrieving audit logs for ticker {ticker}")
    
    @cache_result(ttl=60)
    def get_date_range_audit_logs(self, start_date: datetime, end_date: datetime, skip: Optional[int] = None, limit: Optional[int] = None) -> List[AuditLogSchema]:
        """
        Get audit logs within a specific date range with pagination
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[AuditLogSchema]: List of audit logs within the date range
        """
        # Validate that start_date is before end_date
        if start_date > end_date:
            raise ValueError("start_date must be before end_date")
        
        self._log_operation("get_date_range_audit_logs", f"Retrieving audit logs from {start_date} to {end_date}")
        
        try:
            with self._get_db_session() as db:
                result = audit.get_audit_logs_by_date_range(db, start_date, end_date, skip, limit)
                return result
        except Exception as e:
            self._handle_db_error(e, f"retrieving audit logs for date range {start_date} to {end_date}")
    
    @cache_result(ttl=60)
    def get_fallback_audit_logs(self, skip: Optional[int] = None, limit: Optional[int] = None) -> List[AuditLogSchema]:
        """
        Get audit logs where fallback mechanisms were used with pagination
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[AuditLogSchema]: List of audit logs with fallback usage
        """
        self._log_operation("get_fallback_audit_logs", "Retrieving audit logs with fallback usage")
        
        try:
            with self._get_db_session() as db:
                result = audit.get_audit_logs_with_fallback(db, skip, limit)
                return result
        except Exception as e:
            self._handle_db_error(e, "retrieving audit logs with fallback usage")
    
    @cache_result(ttl=300)
    def count_audit_logs(self) -> int:
        """
        Count the total number of audit logs
        
        Returns:
            int: Total count of audit logs
        """
        self._log_operation("count_audit_logs", "Counting total audit logs")
        
        try:
            with self._get_db_session() as db:
                result = audit.count_audit_logs(db)
                return result
        except Exception as e:
            self._handle_db_error(e, "counting audit logs")
    
    def create_audit_filter(
        self,
        client_id: Optional[str] = None,
        ticker: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_position_value: Optional[Decimal] = None,
        max_position_value: Optional[Decimal] = None,
        min_borrow_rate: Optional[Decimal] = None,
        max_borrow_rate: Optional[Decimal] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None
    ) -> AuditLogFilterSchema:
        """
        Create an audit log filter schema from parameters
        
        Args:
            client_id: Filter by client identifier
            ticker: Filter by stock symbol
            start_date: Filter for records after this date/time
            end_date: Filter for records before this date/time
            min_position_value: Filter for position values greater than or equal to this amount
            max_position_value: Filter for position values less than or equal to this amount
            min_borrow_rate: Filter for borrow rates greater than or equal to this rate
            max_borrow_rate: Filter for borrow rates less than or equal to this rate
            page: Page number for pagination
            page_size: Number of items per page
            
        Returns:
            AuditLogFilterSchema: Filter schema for audit logs
        """
        # Create filter schema
        filter_schema = AuditLogFilterSchema(
            client_id=client_id,
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            min_position_value=min_position_value,
            max_position_value=max_position_value,
            min_borrow_rate=min_borrow_rate,
            max_borrow_rate=max_borrow_rate,
            page=page,
            page_size=page_size
        )
        
        # Validate client_id and ticker if provided
        if client_id:
            validate_client_id(client_id)
        
        if ticker:
            validate_ticker(ticker)
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date must be before end_date")
        
        # Validate position value range
        if min_position_value and max_position_value and min_position_value > max_position_value:
            raise ValueError("min_position_value must be less than max_position_value")
        
        # Validate borrow rate range
        if min_borrow_rate and max_borrow_rate and min_borrow_rate > max_borrow_rate:
            raise ValueError("min_borrow_rate must be less than max_borrow_rate")
        
        return filter_schema