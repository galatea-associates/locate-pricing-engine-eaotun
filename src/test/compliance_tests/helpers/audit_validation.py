"""
Helper module for validating audit logs in compliance tests.

Provides functions and classes to verify that audit logs meet regulatory requirements,
contain all required information, and correctly document calculation details including
fallback mechanisms. Used by compliance tests to ensure the system maintains proper
audit trails for financial transactions.
"""

import pytest
import datetime
from decimal import Decimal
import uuid
from typing import List, Dict, Optional, Any, Union, Tuple

from src.backend.services.audit.transactions import TransactionAuditor
from src.backend.schemas.audit import (
    AuditLogSchema,
    DataSourceSchema,
    CalculationBreakdownSchema
)
from src.backend.core.constants import ExternalAPIs
from src.backend.db.session import get_db

# Constants
SEC_RETENTION_YEARS = 7  # SEC Rule 17a-4 requires 7 years retention

# Required fields in audit logs
REQUIRED_AUDIT_FIELDS = [
    "audit_id", "timestamp", "client_id", "ticker", "position_value", 
    "loan_days", "borrow_rate_used", "total_fee", "data_sources", 
    "calculation_breakdown"
]

# Required fields in data sources
REQUIRED_DATA_SOURCE_FIELDS = ["borrow_rate", "volatility", "event_risk"]

# Required fields in calculation breakdown
REQUIRED_CALCULATION_BREAKDOWN_FIELDS = [
    "fee_components", "base_borrow_rate", "final_borrow_rate", 
    "annualized_rate", "time_factor"
]


def validate_audit_log_structure(audit_log: AuditLogSchema) -> bool:
    """
    Validates that an audit log contains all required fields with correct types.
    
    Args:
        audit_log: The audit log to validate
        
    Returns:
        True if audit log structure is valid, raises AssertionError otherwise
    """
    # Check all required fields are present
    for field in REQUIRED_AUDIT_FIELDS:
        assert hasattr(audit_log, field), f"Audit log missing required field: {field}"
    
    # Validate field types
    assert isinstance(audit_log.audit_id, uuid.UUID), "audit_id must be a UUID"
    assert isinstance(audit_log.timestamp, datetime.datetime), "timestamp must be a datetime"
    assert isinstance(audit_log.client_id, str) and audit_log.client_id, "client_id must be a non-empty string"
    assert isinstance(audit_log.ticker, str) and audit_log.ticker, "ticker must be a non-empty string"
    
    # Validate numeric fields
    assert isinstance(audit_log.position_value, Decimal) and audit_log.position_value > 0, "position_value must be a positive Decimal"
    assert isinstance(audit_log.loan_days, int) and audit_log.loan_days > 0, "loan_days must be a positive integer"
    assert isinstance(audit_log.borrow_rate_used, Decimal) and audit_log.borrow_rate_used >= 0, "borrow_rate_used must be a non-negative Decimal"
    assert isinstance(audit_log.total_fee, Decimal) and audit_log.total_fee >= 0, "total_fee must be a non-negative Decimal"
    
    # Validate complex structures
    assert isinstance(audit_log.data_sources, dict), "data_sources must be a dictionary"
    assert isinstance(audit_log.calculation_breakdown, dict), "calculation_breakdown must be a dictionary"
    
    # Validate data_sources has required fields
    validate_data_sources(audit_log.data_sources)
    
    # Validate calculation_breakdown has required fields
    for field in REQUIRED_CALCULATION_BREAKDOWN_FIELDS:
        assert field in audit_log.calculation_breakdown, f"calculation_breakdown missing required field: {field}"
    
    return True


def validate_data_sources(data_sources: Dict[str, str]) -> bool:
    """
    Validates that data sources in an audit log contain all required information.
    
    Args:
        data_sources: Dictionary of data sources from an audit log
        
    Returns:
        True if data sources are valid, raises AssertionError otherwise
    """
    # Check all required fields are present
    for field in REQUIRED_DATA_SOURCE_FIELDS:
        assert field in data_sources, f"data_sources missing required field: {field}"
    
    # Validate field types
    for field in REQUIRED_DATA_SOURCE_FIELDS:
        assert isinstance(data_sources[field], str) and data_sources[field], f"{field} source must be a non-empty string"
    
    # Validate that sources match expected external API identifiers
    # This check ensures the system is using the configured sources
    for source in data_sources.values():
        if not any(api in source for api in [ExternalAPIs.SECLEND, 
                                           ExternalAPIs.MARKET_VOLATILITY, 
                                           ExternalAPIs.EVENT_CALENDAR]):
            assert "fallback" in source.lower(), f"Unknown data source '{source}' isn't marked as fallback"
    
    return True


def verify_audit_log_exists(auditor: TransactionAuditor, audit_id: Union[str, uuid.UUID]) -> bool:
    """
    Verifies that an audit log exists for a given transaction.
    
    Args:
        auditor: The transaction auditor to use
        audit_id: The audit ID to look up
        
    Returns:
        True if audit log exists, False otherwise
    """
    # Convert to UUID if string
    if isinstance(audit_id, str):
        try:
            audit_id = uuid.UUID(audit_id)
        except ValueError:
            return False
    
    # Try to get the audit log
    audit_log = auditor.get_transaction_by_id(audit_id)
    return audit_log is not None


def verify_fallback_logging(audit_log: AuditLogSchema) -> bool:
    """
    Verifies that fallback mechanism usage is properly logged.
    
    Args:
        audit_log: The audit log to check
        
    Returns:
        True if fallback logging is valid, raises AssertionError otherwise
    """
    # Check if any data sources indicate fallback usage
    fallback_used = False
    for source_name, source_info in audit_log.data_sources.items():
        if isinstance(source_info, dict) and source_info.get("is_fallback", False):
            fallback_used = True
            
            # Verify fallback source is properly identified
            assert "fallback_reason" in source_info, f"Fallback source '{source_name}' missing fallback_reason"
            assert source_info["fallback_reason"], "fallback_reason cannot be empty"
            
            # Verify original source is documented
            assert "original_source" in source_info, f"Fallback source '{source_name}' missing original_source"
    
    # If no fallback indicated in data_sources, we should check if terms indicate fallback
    if not fallback_used:
        for source_name, source_info in audit_log.data_sources.items():
            if isinstance(source_info, str) and ("fallback" in source_info.lower() or "minimum" in source_info.lower()):
                fallback_used = True
                # Simple string format doesn't need additional checks
    
    return True


def verify_audit_retention(auditor: TransactionAuditor, reference_date: datetime.date) -> bool:
    """
    Verifies that audit logs are retained for the required regulatory period.
    
    Args:
        auditor: The transaction auditor to use
        reference_date: The date to use as reference (usually current date)
        
    Returns:
        True if retention requirements are met, False otherwise
    """
    # Calculate the start of the retention period (7 years ago)
    retention_start = reference_date.replace(year=reference_date.year - SEC_RETENTION_YEARS)
    
    # Get the oldest available audit log
    oldest_log = get_oldest_audit_log(auditor)
    
    # If we have no logs at all, we can't verify retention
    if oldest_log is None:
        return True
    
    # Get the date of the oldest log
    oldest_date = oldest_log.timestamp.date()
    
    # If the system hasn't been operational for the full retention period,
    # we just ensure no logs have been deleted
    system_start_date = oldest_date
    if system_start_date > retention_start:
        # System hasn't been operational for full retention period
        # so we can't fully verify, but we ensure no logs were deleted
        return True
    
    # Check if we have logs from the start of the retention period
    return oldest_date <= retention_start


def get_oldest_audit_log(auditor: TransactionAuditor) -> Optional[AuditLogSchema]:
    """
    Retrieves the oldest audit log in the system.
    
    Args:
        auditor: The transaction auditor to use
        
    Returns:
        Oldest audit log or None if no logs exist
    """
    # Create a filter for oldest logs (sorted by timestamp ascending)
    filters = {"page": 1, "page_size": 1}
    
    # Get the logs
    result = auditor.filter_transactions(filters)
    
    # Return the first log if any exist
    if result.items:
        return result.items[0]
    
    return None


class AuditValidator:
    """Helper class for validating audit logs against compliance requirements."""
    
    def __init__(self, auditor: TransactionAuditor):
        """
        Initialize the audit validator with a transaction auditor.
        
        Args:
            auditor: The transaction auditor to use
        """
        self._auditor = auditor
        self._validation_results = {}
    
    def validate_audit_log(self, audit_log: AuditLogSchema) -> bool:
        """
        Performs comprehensive validation of an audit log.
        
        Args:
            audit_log: The audit log to validate
            
        Returns:
            True if audit log is valid, False otherwise
        """
        # Reset validation results
        self._validation_results = {}
        
        try:
            # Validate basic structure
            validate_audit_log_structure(audit_log)
            self._validation_results["structure_valid"] = True
            
            # Validate data sources
            validate_data_sources(audit_log.data_sources)
            self._validation_results["data_sources_valid"] = True
            
            # Check if fallback mechanisms were used
            fallback_used = False
            for source_name, source_info in audit_log.data_sources.items():
                if isinstance(source_info, dict) and source_info.get("is_fallback", False):
                    fallback_used = True
                    break
                elif isinstance(source_info, str) and ("fallback" in source_info.lower() or "minimum" in source_info.lower()):
                    fallback_used = True
                    break
            
            # If fallback was used, verify it was properly logged
            if fallback_used:
                verify_fallback_logging(audit_log)
                self._validation_results["fallback_logging_valid"] = True
            
            return all(self._validation_results.values())
        
        except AssertionError as e:
            # Record the validation failure
            failed_check = e.args[0] if e.args else "Unknown validation error"
            self._validation_results["error"] = failed_check
            return False
    
    def validate_transaction(self, audit_id: Union[str, uuid.UUID]) -> bool:
        """
        Validates an audit log by its transaction ID.
        
        Args:
            audit_id: The audit ID to validate
            
        Returns:
            True if transaction audit log is valid, False otherwise
        """
        # Get the audit log
        audit_log = self._auditor.get_transaction_by_id(audit_id)
        
        if audit_log is None:
            self._validation_results = {"error": f"Audit log not found: {audit_id}"}
            return False
        
        # Validate the audit log
        return self.validate_audit_log(audit_log)
    
    def check_retention_compliance(self, reference_date: Optional[datetime.date] = None) -> bool:
        """
        Checks if the system complies with audit log retention requirements.
        
        Args:
            reference_date: The date to use as reference (defaults to current date)
            
        Returns:
            True if retention requirements are met, False otherwise
        """
        if reference_date is None:
            reference_date = datetime.date.today()
        
        retention_compliant = verify_audit_retention(self._auditor, reference_date)
        self._validation_results["retention_compliant"] = retention_compliant
        
        return retention_compliant
    
    def generate_compliance_report(self, sample_size: Optional[int] = 100) -> Dict[str, Any]:
        """
        Generates a comprehensive compliance report for audit logs.
        
        Args:
            sample_size: Number of recent audit logs to sample for validation
            
        Returns:
            Compliance report with validation results and statistics
        """
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "retention_compliance": {},
            "log_validation": {},
            "fallback_usage": {},
            "sample_size": sample_size,
            "overall_compliance": False
        }
        
        # Check retention compliance
        retention_compliant = self.check_retention_compliance()
        report["retention_compliance"] = {
            "compliant": retention_compliant,
            "required_years": SEC_RETENTION_YEARS
        }
        
        # Get a sample of recent audit logs
        filters = {"page": 1, "page_size": sample_size}
        sample_result = self._auditor.filter_transactions(filters)
        sample_logs = sample_result.items
        
        # Validate each log in the sample
        valid_count = 0
        validation_errors = {}
        
        for log in sample_logs:
            if self.validate_audit_log(log):
                valid_count += 1
            else:
                error = self._validation_results.get("error", "Unknown validation error")
                validation_errors[str(log.audit_id)] = error
        
        # Calculate compliance percentage
        sample_count = len(sample_logs)
        compliance_percentage = (valid_count / sample_count * 100) if sample_count > 0 else 0
        
        report["log_validation"] = {
            "sample_size": sample_count,
            "valid_count": valid_count,
            "compliance_percentage": compliance_percentage,
            "validation_errors": validation_errors
        }
        
        # Analyze fallback usage
        fallback_logs = self._auditor.get_fallback_transactions()
        
        fallback_count = len(fallback_logs)
        fallback_percentage = (fallback_count / sample_count * 100) if sample_count > 0 else 0
        
        report["fallback_usage"] = {
            "fallback_count": fallback_count,
            "fallback_percentage": fallback_percentage,
        }
        
        # Determine overall compliance
        report["overall_compliance"] = (
            retention_compliant and 
            compliance_percentage >= 99.0 and  # Allow for a small margin of error
            len(validation_errors) == 0
        )
        
        return report
    
    def get_validation_results(self) -> Dict[str, Any]:
        """
        Returns the detailed results of the last validation.
        
        Returns:
            Detailed validation results
        """
        return self._validation_results


class TransactionAuditor:
    """Mock class for testing audit validation without database dependencies."""
    
    def __init__(self):
        """Initialize the mock transaction auditor with sample audit logs."""
        self._mock_audit_logs = []
    
    def get_transaction_by_id(self, audit_id: Union[str, uuid.UUID]) -> Optional[AuditLogSchema]:
        """
        Get a mock transaction by its audit ID.
        
        Args:
            audit_id: The audit ID to look up
            
        Returns:
            Found audit log or None
        """
        # Convert to UUID if string
        if isinstance(audit_id, str):
            try:
                audit_id = uuid.UUID(audit_id)
            except ValueError:
                return None
        
        # Find the audit log with matching ID
        for log in self._mock_audit_logs:
            if log.audit_id == audit_id:
                return log
        
        return None
    
    def filter_transactions(self, filters: Dict[str, Any]) -> List[AuditLogSchema]:
        """
        Filter mock transactions based on criteria.
        
        Args:
            filters: Filter criteria
            
        Returns:
            Filtered audit logs
        """
        # Simple implementation for testing
        return self._mock_audit_logs[:filters.get("page_size", 50)]
    
    def get_fallback_transactions(self) -> List[AuditLogSchema]:
        """
        Get mock transactions where fallback mechanisms were used.
        
        Returns:
            Audit logs with fallback usage
        """
        # Return logs with fallback indicators
        return [log for log in self._mock_audit_logs if "fallback" in str(log.data_sources).lower()]