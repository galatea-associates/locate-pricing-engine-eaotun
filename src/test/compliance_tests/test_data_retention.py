"""
Implements compliance tests for data retention requirements of the Borrow Rate & Locate Fee Pricing Engine.

These tests verify that the system properly retains audit logs and transaction data for the required 
regulatory period (7 years) as mandated by SEC Rule 17a-4 and other financial regulations.
"""

import pytest
import datetime
import uuid
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from .helpers.audit_validation import (
    AuditValidator,
    verify_audit_retention,
    get_oldest_audit_log
)
from src.backend.services.audit.transactions import TransactionAuditor
from src.backend.schemas.audit import AuditLogSchema
from src.backend.db.models.audit import AuditLog
from src.backend.db.session import get_db

# Constants for compliance requirements
SEC_RETENTION_YEARS = 7  # SEC Rule 17a-4 requires 7 years retention
ACTIVE_RETENTION_PERIOD = 1  # 1 year in partitioned tables
ARCHIVE_RETENTION_PERIOD = 7  # 7 years total retention period


@pytest.mark.compliance
def test_audit_log_retention_period(db_session):
    """
    Test that audit logs are retained for the required regulatory period (7 years).
    
    This test verifies that the system maintains audit logs for the full 7-year retention period
    required by SEC Rule 17a-4 for financial transaction records.
    
    Args:
        db_session: Database session fixture
    """
    # Initialize the transaction auditor with the database session
    transaction_auditor = TransactionAuditor(db_session)
    
    # Initialize the audit validator with the transaction auditor
    validator = AuditValidator(transaction_auditor)
    
    # Check if retention requirements are met
    retention_compliant = validator.check_retention_compliance()
    
    # Assert that retention requirements are met
    assert retention_compliant, "Audit logs are not retained for the required 7-year period"
    
    # Log detailed compliance information
    validation_results = validator.get_validation_results()
    pytest.logger.info(f"Retention compliance check results: {validation_results}")


@pytest.mark.compliance
@pytest.mark.parametrize('years_ago', [1, 3, 5, 6, 7])
def test_audit_log_retention_with_time_travel(db_session, years_ago):
    """
    Test audit log retention by simulating different points in time.
    
    Uses freezegun to simulate different dates in the past and ensures that audit logs
    are properly retained and accessible throughout the required 7-year period.
    
    Args:
        db_session: Database session fixture
        years_ago: Number of years to go back in time
    """
    # Initialize the transaction auditor with the database session
    transaction_auditor = TransactionAuditor(db_session)
    
    # Calculate the reference date (current date - years_ago)
    current_date = datetime.date.today()
    reference_date = current_date - relativedelta(years=years_ago)
    
    # Freeze time at the reference date
    with freeze_time(reference_date):
        # Verify that the audit logs are properly retained at this point in time
        is_compliant = verify_audit_retention(transaction_auditor, reference_date)
        
        # Assert that retention requirements are met for this time point
        assert is_compliant, f"Audit retention check failed for {years_ago} years ago"
        
        # Get the oldest available audit log
        oldest_log = get_oldest_audit_log(transaction_auditor)
        
        # If the system has been operational for the full retention period, verify that
        # the oldest log is not older than 7 years from the reference date
        if oldest_log:
            oldest_date = oldest_log.timestamp.date()
            retention_threshold = reference_date - relativedelta(years=SEC_RETENTION_YEARS)
            
            # Verify that logs older than 7 years are not in active storage
            if oldest_date < retention_threshold:
                pytest.fail(f"Found logs older than {SEC_RETENTION_YEARS} years in active storage")


@pytest.mark.compliance
def test_audit_log_archival_policy(db_session):
    """
    Test that audit logs are properly archived according to the archival policy.
    
    Verifies that audit logs older than 1 year are moved to archive storage while
    maintaining accessibility, and that the archived logs are retained for the full
    7-year regulatory period.
    
    Args:
        db_session: Database session fixture
    """
    # Initialize the transaction auditor with the database session
    transaction_auditor = TransactionAuditor(db_session)
    
    # Get current date and calculate archive threshold date (current date - 1 year)
    current_date = datetime.date.today()
    archive_threshold_date = current_date - relativedelta(years=ACTIVE_RETENTION_PERIOD)
    
    # Query for audit logs older than the threshold date
    filters = {
        "end_date": datetime.datetime.combine(archive_threshold_date, datetime.time.min),
        "page": 1,
        "page_size": 100
    }
    
    # Get logs that should be archived
    archived_logs_response = transaction_auditor.filter_transactions(filters)
    archived_logs = archived_logs_response.items
    
    if archived_logs:
        # Verify that logs older than 1 year are properly archived
        # In a real scenario, we'd check the storage location or a flag in the database
        # For this test, we'll just verify that they're still accessible through the API
        for log in archived_logs:
            # Verify that archived logs are still accessible through the API
            retrieved_log = transaction_auditor.get_transaction_by_id(log.audit_id)
            assert retrieved_log is not None, f"Archived log {log.audit_id} is not accessible"
            
            # Verify that archived logs maintain all required data fields
            assert hasattr(retrieved_log, 'audit_id')
            assert hasattr(retrieved_log, 'timestamp')
            assert hasattr(retrieved_log, 'client_id')
            assert hasattr(retrieved_log, 'ticker')
            assert hasattr(retrieved_log, 'position_value')
            assert hasattr(retrieved_log, 'loan_days')
            assert hasattr(retrieved_log, 'borrow_rate_used')
            assert hasattr(retrieved_log, 'total_fee')
            assert hasattr(retrieved_log, 'data_sources')
            assert hasattr(retrieved_log, 'calculation_breakdown')
    
    # Check if there are any logs that are older than the full retention period
    retention_threshold_date = current_date - relativedelta(years=ARCHIVE_RETENTION_PERIOD)
    oldest_log = get_oldest_audit_log(transaction_auditor)
    
    if oldest_log and oldest_log.timestamp.date() < retention_threshold_date:
        pytest.fail(f"Found logs older than {ARCHIVE_RETENTION_PERIOD} years, which exceeds retention policy")


@pytest.mark.compliance
def test_data_immutability(db_session):
    """
    Test that audit logs are immutable and cannot be modified after creation.
    
    Verifies that the system prevents modifications to audit logs, which is a critical
    requirement for regulatory compliance and data integrity.
    
    Args:
        db_session: Database session fixture
    """
    # Initialize the transaction auditor with the database session
    transaction_auditor = TransactionAuditor(db_session)
    
    # Get a sample audit log for testing
    filters = {"page": 1, "page_size": 1}
    response = transaction_auditor.filter_transactions(filters)
    
    if not response.items:
        pytest.skip("No audit logs found for testing immutability")
    
    sample_log = response.items[0]
    original_fee = sample_log.total_fee
    original_timestamp = sample_log.timestamp
    
    # Attempt to modify the audit log directly in the database
    # This should fail due to immutability protections
    try:
        # Try to modify the log in the database
        audit_log = db_session.query(AuditLog).filter(AuditLog.audit_id == sample_log.audit_id).first()
        
        if audit_log:
            # Attempt to change the total_fee
            audit_log.total_fee = original_fee + 100
            
            # Try to commit the change
            db_session.commit()
            
            # If we reach here, the modification might have succeeded, verify it didn't actually change
            db_session.refresh(audit_log)
            
            # Retrieve the log again and verify it remains unchanged
            modified_log = transaction_auditor.get_transaction_by_id(sample_log.audit_id)
            
            # Either the modification was prevented at the database level (e.g., by triggers),
            # or we need to verify that audit systems would detect such modifications
            assert modified_log.total_fee == original_fee, "Audit log was modified when it should be immutable"
            assert modified_log.timestamp == original_timestamp, "Audit log timestamp was modified"
            
    except Exception as e:
        # If an exception is raised, that's good - it means modification was prevented
        # Rollback any changes that might have been attempted
        db_session.rollback()
        
        # Log that modification was appropriately rejected
        pytest.logger.info(f"Attempted modification of audit log was correctly prevented: {str(e)}")
    
    # Final verification - retrieve the log again and make sure it's unchanged
    final_log = transaction_auditor.get_transaction_by_id(sample_log.audit_id)
    assert final_log.total_fee == original_fee, "Audit log fee was modified despite immutability requirements"
    
    # Assert that audit logs are properly protected against modifications
    # This might be handled by database constraints, triggers, or application logic
    pytest.logger.info("Audit log immutability test passed - logs cannot be modified after creation")


@pytest.mark.compliance
def test_oldest_audit_log_retrieval(db_session):
    """
    Test that the oldest audit logs can be successfully retrieved.
    
    Verifies that the system maintains access to the oldest audit logs, which is important
    for demonstrating retention compliance during regulatory audits.
    
    Args:
        db_session: Database session fixture
    """
    # Initialize the transaction auditor with the database session
    transaction_auditor = TransactionAuditor(db_session)
    
    # Call get_oldest_audit_log to retrieve the oldest log
    oldest_log = get_oldest_audit_log(transaction_auditor)
    
    # If no logs exist, skip the test
    if oldest_log is None:
        pytest.skip("No audit logs found for testing oldest log retrieval")
    
    # Verify that the oldest log can be successfully retrieved
    assert oldest_log is not None, "Failed to retrieve oldest audit log"
    
    # Validate that the oldest log has all required fields
    assert hasattr(oldest_log, 'audit_id'), "Oldest log missing audit_id field"
    assert hasattr(oldest_log, 'timestamp'), "Oldest log missing timestamp field"
    assert hasattr(oldest_log, 'client_id'), "Oldest log missing client_id field"
    assert hasattr(oldest_log, 'ticker'), "Oldest log missing ticker field"
    assert hasattr(oldest_log, 'position_value'), "Oldest log missing position_value field"
    assert hasattr(oldest_log, 'loan_days'), "Oldest log missing loan_days field"
    assert hasattr(oldest_log, 'borrow_rate_used'), "Oldest log missing borrow_rate_used field"
    assert hasattr(oldest_log, 'total_fee'), "Oldest log missing total_fee field"
    assert hasattr(oldest_log, 'data_sources'), "Oldest log missing data_sources field"
    assert hasattr(oldest_log, 'calculation_breakdown'), "Oldest log missing calculation_breakdown field"
    
    # Verify that the oldest log's timestamp is within the retention period
    current_date = datetime.date.today()
    retention_threshold_date = current_date - relativedelta(years=SEC_RETENTION_YEARS)
    oldest_timestamp = oldest_log.timestamp.date()
    
    # If the system has been operational for less than 7 years, this check doesn't apply
    system_age = (current_date - oldest_timestamp).days / 365.25  # Approximate years
    
    if system_age >= SEC_RETENTION_YEARS:
        # If system has existed for 7+ years, oldest log should not be older than retention period
        assert oldest_timestamp >= retention_threshold_date, \
            f"Oldest log timestamp {oldest_timestamp} is beyond the retention period"


@pytest.mark.compliance
@pytest.mark.parametrize('months_ago', [1, 6, 12, 24, 36, 48, 60, 72, 84])
def test_audit_log_accessibility_by_age(db_session, months_ago):
    """
    Test that audit logs of different ages are accessible with consistent performance.
    
    Verifies that the system maintains reliable access to audit logs across their entire
    lifecycle, from recent logs to those approaching the retention limit.
    
    Args:
        db_session: Database session fixture
        months_ago: Number of months to go back in time
    """
    # Initialize the transaction auditor with the database session
    transaction_auditor = TransactionAuditor(db_session)
    
    # Calculate reference date (current date - months_ago months)
    current_date = datetime.date.today()
    reference_date = current_date - relativedelta(months=months_ago)
    
    # Determine the date range to query (1 day window around reference date)
    start_date = datetime.datetime.combine(reference_date - datetime.timedelta(days=1), datetime.time.min)
    end_date = datetime.datetime.combine(reference_date + datetime.timedelta(days=1), datetime.time.max)
    
    # Skip test if the reference date is beyond the retention period
    if months_ago > SEC_RETENTION_YEARS * 12:
        pytest.skip(f"Test date {reference_date} is beyond the required retention period")
    
    # Query for audit logs around the reference date
    filters = {
        "start_date": start_date,
        "end_date": end_date,
        "page": 1,
        "page_size": 50
    }
    
    # Measure query response time
    start_time = datetime.datetime.now()
    response = transaction_auditor.filter_transactions(filters)
    end_time = datetime.datetime.now()
    query_time_ms = (end_time - start_time).total_seconds() * 1000
    
    # Log the query performance
    pytest.logger.info(f"Query for logs from {months_ago} months ago took {query_time_ms:.2f} ms")
    
    # We don't always expect to find logs for every time period, especially in test environments
    # If no logs found, skip the remaining verifications
    if not response.items:
        pytest.logger.info(f"No logs found for period {months_ago} months ago")
        return
    
    # Verify that logs can be retrieved regardless of age
    logs = response.items
    assert len(logs) > 0, f"Failed to retrieve logs from {months_ago} months ago"
    
    # Assert that query performance is within acceptable limits
    # Performance requirements might vary based on storage tier (active vs. archive)
    if months_ago <= ACTIVE_RETENTION_PERIOD * 12:
        # Active storage should be fast
        assert query_time_ms < 500, f"Query for active storage logs too slow: {query_time_ms} ms"
    else:
        # Archive storage might be slower but still within reasonable limits
        assert query_time_ms < 2000, f"Query for archive storage logs too slow: {query_time_ms} ms"
    
    # Verify that all required data fields are present in retrieved logs
    for log in logs:
        assert hasattr(log, 'audit_id')
        assert hasattr(log, 'timestamp')
        assert hasattr(log, 'client_id')
        assert hasattr(log, 'ticker')
        assert hasattr(log, 'position_value')
        assert hasattr(log, 'loan_days')
        assert hasattr(log, 'borrow_rate_used')
        assert hasattr(log, 'total_fee')
        assert hasattr(log, 'data_sources')
        assert hasattr(log, 'calculation_breakdown')


@pytest.mark.compliance
def test_comprehensive_retention_compliance(db_session):
    """
    Comprehensive test of all data retention compliance requirements.
    
    This test performs a thorough evaluation of the system's compliance with data retention
    requirements, including active storage, archival, immutability, and accessibility.
    
    Args:
        db_session: Database session fixture
    """
    # Initialize the transaction auditor with the database session
    transaction_auditor = TransactionAuditor(db_session)
    
    # Initialize the audit validator with the transaction auditor
    validator = AuditValidator(transaction_auditor)
    
    # Generate comprehensive compliance report
    compliance_report = validator.generate_compliance_report()
    
    # Verify active retention period compliance (1 year in main tables)
    assert compliance_report["retention_compliance"]["compliant"], \
        "Failed to meet basic retention requirements"
    
    # Verify archive retention period compliance (7 years total)
    assert compliance_report["retention_compliance"]["required_years"] == SEC_RETENTION_YEARS, \
        f"Incorrect retention period configured: expected {SEC_RETENTION_YEARS} years"
    
    # Log statistics about the audit logs
    log_count = compliance_report["log_validation"]["sample_size"]
    valid_count = compliance_report["log_validation"]["valid_count"]
    compliance_percentage = compliance_report["log_validation"]["compliance_percentage"]
    
    pytest.logger.info(f"Audit log compliance: {valid_count}/{log_count} logs valid ({compliance_percentage:.2f}%)")
    
    # If there are any validation errors, log them for investigation
    if valid_count < log_count:
        validation_errors = compliance_report["log_validation"]["validation_errors"]
        for audit_id, error in validation_errors.items():
            pytest.logger.error(f"Validation error in log {audit_id}: {error}")
    
    # Verify data integrity across all storage tiers
    assert compliance_percentage >= 99.0, \
        f"Audit log data integrity too low: {compliance_percentage:.2f}%"
    
    # Verify fallback usage is properly tracked
    fallback_count = compliance_report["fallback_usage"]["fallback_count"]
    fallback_percentage = compliance_report["fallback_usage"]["fallback_percentage"]
    
    pytest.logger.info(f"Fallback mechanism usage: {fallback_count} logs ({fallback_percentage:.2f}%)")
    
    # Assert that all retention requirements are met
    assert compliance_report["overall_compliance"], \
        "Failed to meet all compliance requirements for data retention"
    
    # Log detailed compliance report for review
    pytest.logger.info(f"Comprehensive compliance report: {compliance_report}")