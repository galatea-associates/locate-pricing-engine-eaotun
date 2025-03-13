# src/test/compliance_tests/test_audit_trail.py
import pytest  # pytest 7.4.0+
import datetime  # standard library
import uuid  # standard library
from decimal import Decimal  # standard library
import requests  # requests 2.28.0+

from src.test.compliance_tests.helpers.audit_validation import (
    AuditValidator,
    validate_audit_log_structure,
    verify_audit_log_exists,
    verify_fallback_logging,
    verify_audit_retention,
)
from src.backend.services.audit.transactions import TransactionAuditor
from src.backend.schemas.audit import AuditLogSchema, CalculationBreakdownSchema
from src.test.compliance_tests.helpers.calculation_validation import CalculationValidator
from src.backend.db.session import get_db

SEC_RETENTION_YEARS = 7
REQUIRED_AUDIT_FIELDS = ["audit_id", "timestamp", "client_id", "ticker", "position_value", "loan_days", "borrow_rate_used", "total_fee", "data_sources", "calculation_breakdown"]

@pytest.mark.compliance
def test_audit_log_structure(Session):
    """Test that audit logs contain all required fields with correct types"""
    # Initialize TransactionAuditor with db_session
    auditor = TransactionAuditor(Session)
    # Get a sample of recent audit logs
    recent_logs = auditor.filter_transactions({"page": 1, "page_size": 5})
    # For each audit log, call validate_audit_log_structure
    for audit_log in recent_logs.items:
        # Assert that all required fields are present
        assert all(hasattr(audit_log, field) for field in REQUIRED_AUDIT_FIELDS), "Audit log missing required fields"
        # Assert that audit_id is a valid UUID
        assert isinstance(audit_log.audit_id, uuid.UUID), "audit_id must be a UUID"
        # Assert that timestamp is a datetime object
        assert isinstance(audit_log.timestamp, datetime.datetime), "timestamp must be a datetime object"
        # Assert that data_sources contains required information
        assert isinstance(audit_log.data_sources, dict), "data_sources must be a dictionary"
        # Assert that calculation_breakdown contains required components
        assert isinstance(audit_log.calculation_breakdown, CalculationBreakdownSchema), "calculation_breakdown must be a CalculationBreakdownSchema"

@pytest.mark.compliance
@pytest.mark.integration
def test_audit_log_creation(api_base_url: str, api_key: str, Session):
    """Test that an audit log is created for each fee calculation"""
    # Initialize TransactionAuditor with db_session
    auditor = TransactionAuditor(Session)
    # Make a request to calculate-locate endpoint with test parameters
    headers = {"X-API-Key": api_key}
    params = {
        "ticker": "AAPL",
        "position_value": 100000,
        "loan_days": 30,
        "client_id": "test_client"
    }
    response = requests.get(f"{api_base_url}/api/v1/calculate-locate", params=params, headers=headers)
    assert response.status_code == 200, f"API request failed: {response.status_code} - {response.text}"
    # Extract audit_id from the response
    response_data = response.json()
    audit_id = response_data.get("audit_id")
    assert audit_id is not None, "audit_id not found in response"
    # Call verify_audit_log_exists with the audit_id
    audit_log_exists = verify_audit_log_exists(auditor, audit_id)
    # Assert that the audit log exists
    assert audit_log_exists, f"Audit log not found for audit_id: {audit_id}"
    # Retrieve the audit log using get_transaction_by_id
    audit_log = auditor.get_transaction_by_id(audit_id)
    # Verify that the audit log contains the same parameters as the request
    assert audit_log.ticker == params["ticker"], "ticker does not match"
    assert audit_log.position_value == Decimal(str(params["position_value"])), "position_value does not match"
    assert audit_log.loan_days == params["loan_days"], "loan_days does not match"
    assert audit_log.client_id == params["client_id"], "client_id does not match"

@pytest.mark.compliance
def test_fallback_mechanism_logging(Session):
    """Test that fallback mechanism usage is properly logged"""
    # Initialize TransactionAuditor with db_session
    auditor = TransactionAuditor(Session)
    # Get transactions where fallback mechanisms were used
    fallback_transactions = auditor.get_fallback_transactions()
    # Assert that at least one fallback transaction exists
    assert fallback_transactions, "No fallback transactions found"
    # For each fallback transaction, call verify_fallback_logging
    for transaction in fallback_transactions:
        # Assert that fallback source is properly identified
        assert "fallback" in str(transaction.data_sources).lower(), "Fallback source not identified in data_sources"
        # Assert that fallback reason is documented
        assert verify_fallback_logging(transaction), "Fallback reason not documented"
        # Assert that original source is documented
        assert "original_source" in str(transaction.data_sources).lower(), "Original source not documented"

@pytest.mark.compliance
def test_audit_log_retention(Session):
    """Test that audit logs are retained for the required regulatory period"""
    # Initialize TransactionAuditor with db_session
    auditor = TransactionAuditor(Session)
    # Initialize AuditValidator with the auditor
    validator = AuditValidator(auditor)
    # Call check_retention_compliance to verify retention requirements
    retention_compliant = validator.check_retention_compliance()
    # If system has been operational for less than retention period, verify no logs have been deleted
    assert retention_compliant, "Audit log retention requirements not met"
    # If system has been operational for full retention period, verify logs exist from start of retention period
    if retention_compliant:
        # Verify logs exist from start of retention period
        assert verify_audit_retention(auditor, datetime.date.today()), "Logs do not exist from start of retention period"

@pytest.mark.compliance
def test_calculation_accuracy_in_audit(Session):
    """Test that calculations recorded in audit logs are accurate"""
    # Initialize TransactionAuditor with db_session
    auditor = TransactionAuditor(Session)
    # Get a sample of recent audit logs
    recent_logs = auditor.filter_transactions({"page": 1, "page_size": 5})
    # Initialize CalculationValidator
    calculation_validator = CalculationValidator()
    # For each audit log, extract calculation details
    for audit_log in recent_logs.items:
        # Validate calculation accuracy using CalculationValidator
        is_valid = calculation_validator.validate_calculation(audit_log.calculation_breakdown)
        # Assert that all calculations are accurate within tolerance
        assert is_valid, f"Calculation accuracy validation failed for audit_id: {audit_log.audit_id}"

@pytest.mark.compliance
def test_comprehensive_audit_compliance(Session):
    """Comprehensive test of all audit compliance requirements"""
    # Initialize TransactionAuditor with db_session
    auditor = TransactionAuditor(Session)
    # Initialize AuditValidator with the auditor
    validator = AuditValidator(auditor)
    # Generate comprehensive compliance report
    compliance_report = validator.generate_compliance_report()
    # Assert that structure compliance is 100%
    assert compliance_report["log_validation"]["compliance_percentage"] == 100, "Structure compliance is not 100%"
    # Assert that data source compliance is 100%
    assert compliance_report["log_validation"]["compliance_percentage"] == 100, "Data source compliance is not 100%"
    # Assert that fallback logging compliance is 100%
    assert compliance_report["log_validation"]["compliance_percentage"] == 100, "Fallback logging compliance is not 100%"
    # Assert that retention compliance is met
    assert compliance_report["retention_compliance"]["compliant"], "Retention compliance is not met"
    # Log detailed compliance report for review
    print(f"Detailed Compliance Report: {compliance_report}")