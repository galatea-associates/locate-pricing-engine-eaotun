"""
Implements the audit logging service for the Borrow Rate & Locate Fee Pricing Engine.

This module provides comprehensive functionality for recording fee calculations,
tracking data sources, logging validation errors, and recording fallback events
to ensure regulatory compliance and support troubleshooting.
"""

import logging
from datetime import datetime
import uuid
from decimal import Decimal
from typing import List, Dict, Optional, Any, Union

from sqlalchemy.orm import Session  # sqlalchemy 2.0.0+

# Import from internal modules
from ...db.crud.audit import audit
from ...schemas.audit import AuditLogSchema, AuditLogFilterSchema, AuditLogResponseSchema
from .utils import (
    format_decimal_for_audit,
    serialize_audit_data,
    deserialize_audit_data,
    create_audit_context,
    has_fallback_source,
    get_data_source_names
)
from ...core.logging import get_audit_logger, log_calculation, log_fallback_usage, log_error

# Set up module logger
logger = logging.getLogger(__name__)


def format_calculation_for_audit(
    position_value: Union[Decimal, float],
    borrow_rate: Union[Decimal, float],
    total_fee: Union[Decimal, float],
    breakdown: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Format calculation data for audit logging with consistent precision.
    
    Args:
        position_value: Position value in USD
        borrow_rate: Applied borrow rate
        total_fee: Total calculated fee
        breakdown: Detailed fee breakdown
        
    Returns:
        Dict[str, Any]: Formatted calculation data with consistent precision
    """
    # Format all decimal values with consistent precision
    formatted_data = {
        "position_value": format_decimal_for_audit(position_value, precision=2),  # Money precision
        "borrow_rate": format_decimal_for_audit(borrow_rate, precision=4),  # Rate precision
        "total_fee": format_decimal_for_audit(total_fee, precision=2),  # Money precision
    }
    
    # Process the breakdown dictionary, formatting decimal values
    formatted_breakdown = {}
    for key, value in breakdown.items():
        if isinstance(value, (Decimal, float)):
            # Format with money precision for fee amounts
            formatted_breakdown[key] = format_decimal_for_audit(value, precision=2)
        elif isinstance(value, dict):
            # Handle nested dictionaries like fee components
            formatted_breakdown[key] = {}
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, (Decimal, float)):
                    formatted_breakdown[key][sub_key] = format_decimal_for_audit(sub_value, precision=2)
                else:
                    formatted_breakdown[key][sub_key] = sub_value
        else:
            formatted_breakdown[key] = value
    
    formatted_data["breakdown"] = formatted_breakdown
    
    return formatted_data


class AuditLogger:
    """Service for logging audit events and storing them in the database."""
    
    def __init__(self, db: Session):
        """
        Initialize the audit logger with a database session.
        
        Args:
            db: Database session for storing audit logs
        """
        self._db = db
        self._logger = get_audit_logger()
        self._logger.info("Audit service initialized")
    
    def log_calculation(
        self,
        ticker: str,
        position_value: Union[Decimal, float],
        loan_days: int,
        client_id: str,
        borrow_rate: Union[Decimal, float],
        total_fee: Union[Decimal, float],
        breakdown: Dict[str, Any],
        data_sources: List[Dict[str, Any]],
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> AuditLogSchema:
        """
        Log a fee calculation with all relevant details.
        
        Args:
            ticker: Stock symbol
            position_value: Position value in USD
            loan_days: Loan duration in days
            client_id: Client identifier
            borrow_rate: Applied borrow rate
            total_fee: Total calculated fee
            breakdown: Detailed fee breakdown
            data_sources: Sources of data used in calculation
            request_id: Identifier for the API request
            user_agent: User agent of the client making the request
            ip_address: IP address of the client
            
        Returns:
            AuditLogSchema: Created audit log record
        """
        # Format calculation data with consistent precision
        formatted_calc = format_calculation_for_audit(
            position_value, borrow_rate, total_fee, breakdown
        )
        
        # Extract data source names
        source_names = get_data_source_names(data_sources)
        
        # Create audit log schema
        audit_log = AuditLogSchema(
            audit_id=uuid.uuid4(),
            timestamp=datetime.utcnow(),
            client_id=client_id,
            ticker=ticker,
            position_value=formatted_calc["position_value"],
            loan_days=loan_days,
            borrow_rate_used=formatted_calc["borrow_rate"],
            total_fee=formatted_calc["total_fee"],
            data_sources=source_names,
            calculation_breakdown=formatted_calc["breakdown"]
        )
        
        # Add request context if provided
        if request_id:
            audit_log.request_id = request_id
        if user_agent:
            audit_log.user_agent = user_agent
        if ip_address:
            audit_log.ip_address = ip_address
        
        # Create audit log record in database
        try:
            db_audit_log = audit.create_audit_log(self._db, audit_log)
        except Exception as e:
            self._logger.error(
                f"Failed to create audit log record: {str(e)}",
                exc_info=True,
                extra={"ticker": ticker, "client_id": client_id}
            )
            # Still return the audit log even if database storage failed
            return audit_log
        
        # Log the calculation event
        log_calculation(
            self._logger,
            ticker=ticker,
            position_value=float(formatted_calc["position_value"]),
            loan_days=loan_days,
            client_id=client_id,
            borrow_rate=float(formatted_calc["borrow_rate"]),
            total_fee=float(formatted_calc["total_fee"]),
            breakdown=formatted_calc["breakdown"],
            data_sources=source_names
        )
        
        # Check if fallback mechanisms were used
        if has_fallback_source(data_sources):
            self._logger.warning(
                f"Fallback mechanisms were used in calculation for {ticker} - Client: {client_id}",
                extra={"ticker": ticker, "client_id": client_id}
            )
        
        return audit_log
    
    def log_fallback_event(
        self,
        service_name: str,
        fallback_type: str,
        context: Dict[str, Any],
        client_id: Optional[str] = None,
        ticker: Optional[str] = None
    ) -> None:
        """
        Log when a fallback mechanism is used due to external API failure.
        
        Args:
            service_name: Name of the service that failed
            fallback_type: Type of fallback mechanism used
            context: Additional context for the fallback
            client_id: Client identifier if available
            ticker: Stock symbol if relevant
        """
        # Create audit context with all available information
        audit_context = create_audit_context(additional_context=context)
        
        # Add client_id and ticker to context if provided
        if client_id:
            audit_context["client_id"] = client_id
        if ticker:
            audit_context["ticker"] = ticker
        
        # Log fallback event
        log_fallback_usage(
            self._logger,
            service_name=service_name,
            fallback_type=fallback_type,
            context=audit_context
        )
        
        # Log additional details at debug level
        self._logger.debug(
            f"Fallback details - Service: {service_name}, Type: {fallback_type}",
            extra=audit_context
        )
    
    def log_validation_error(
        self,
        error_type: str,
        message: str,
        context: Dict[str, Any],
        client_id: Optional[str] = None,
        exception: Optional[Exception] = None
    ) -> None:
        """
        Log validation errors for audit and troubleshooting.
        
        Args:
            error_type: Type of validation error
            message: Error message
            context: Error context data
            client_id: Client identifier if available
            exception: Original exception if available
        """
        # Create audit context with all available information
        audit_context = create_audit_context(additional_context=context)
        
        # Add client_id to context if provided
        if client_id:
            audit_context["client_id"] = client_id
        
        # Add exception details to context if provided
        if exception:
            audit_context["exception_type"] = type(exception).__name__
            audit_context["exception_message"] = str(exception)
        
        # Log the error
        log_error(
            self._logger,
            error=exception or Exception(message),
            message=f"Validation error: {error_type}",
            context=audit_context
        )
        
        # Log additional details at debug level
        self._logger.debug(
            f"Validation error details - Type: {error_type}, Message: {message}",
            extra=audit_context
        )
    
    def get_audit_logs(self, filters: AuditLogFilterSchema) -> AuditLogResponseSchema:
        """
        Get audit logs filtered by various criteria.
        
        Args:
            filters: Filter criteria for audit logs
            
        Returns:
            AuditLogResponseSchema: Filtered and paginated audit logs
        """
        # Validate filter parameters
        if filters.page and filters.page < 1:
            filters.page = 1
        if filters.page_size and filters.page_size < 1:
            filters.page_size = 50
        
        # Get filtered audit logs
        audit_logs = audit.filter_audit_logs(self._db, filters)
        
        return audit_logs
    
    def get_audit_log(self, audit_id: Union[str, uuid.UUID]) -> Optional[AuditLogSchema]:
        """
        Get a specific audit log by ID.
        
        Args:
            audit_id: Unique identifier of the audit log
            
        Returns:
            Optional[AuditLogSchema]: Found audit log or None
        """
        # Convert string to UUID if needed
        if isinstance(audit_id, str):
            audit_id = uuid.UUID(audit_id)
        
        # Get audit log by ID
        audit_log = audit.get_audit_log(self._db, audit_id)
        
        if audit_log:
            return audit_log.to_schema()
        else:
            self._logger.warning(f"Audit log with ID {audit_id} not found")
            return None
    
    def get_client_audit_logs(
        self,
        client_id: str,
        skip: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[AuditLogSchema]:
        """
        Get audit logs for a specific client.
        
        Args:
            client_id: Client identifier
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[AuditLogSchema]: List of audit logs for the client
        """
        # Get audit logs for client
        audit_logs = audit.get_audit_logs_by_client(self._db, client_id, skip, limit)
        
        # Convert to schemas
        return [log.to_schema() for log in audit_logs]
    
    def get_ticker_audit_logs(
        self,
        ticker: str,
        skip: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[AuditLogSchema]:
        """
        Get audit logs for a specific ticker.
        
        Args:
            ticker: Stock symbol
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[AuditLogSchema]: List of audit logs for the ticker
        """
        # Get audit logs for ticker
        audit_logs = audit.get_audit_logs_by_ticker(self._db, ticker, skip, limit)
        
        # Convert to schemas
        return [log.to_schema() for log in audit_logs]
    
    def get_fallback_audit_logs(
        self,
        skip: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[AuditLogSchema]:
        """
        Get audit logs where fallback mechanisms were used.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[AuditLogSchema]: List of audit logs with fallback usage
        """
        # Get audit logs with fallback usage
        audit_logs = audit.get_audit_logs_with_fallback(self._db, skip, limit)
        
        # Convert to schemas
        return [log.to_schema() for log in audit_logs]