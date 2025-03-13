# Compliance Test Suite

## Overview

The Compliance Test Suite is a comprehensive testing framework designed to ensure that the Borrow Rate & Locate Fee Pricing Engine meets all regulatory and financial industry requirements. This test suite is critical for verifying that:

- All financial calculations are accurate and precise
- Complete audit trails are maintained for all operations
- Data retention policies comply with regulatory standards
- API behavior and documentation meet industry requirements
- Fee calculations conform to established rate standards

The suite provides automated verification of these compliance requirements, ensuring that the system can pass regulatory audits and meet financial industry standards. Regular execution of these tests helps maintain continuous compliance and reduces regulatory risk.

## Test Categories

The compliance test suite is organized into five main categories:

### 1. Audit Trail Tests (`audit_trail`)
Verifies that comprehensive audit logs are created for all calculations, containing required information such as:
- Client identifier
- Security details (ticker)
- Transaction values (position value, loan days)
- Calculation results (borrow rate, total fee)
- Data sources used in calculations
- Timestamps and system identifiers

These tests ensure compliance with audit requirements for financial systems and support regulatory investigations if needed.

### 2. Calculation Accuracy Tests (`calculation_accuracy`)
Validates the mathematical accuracy of all financial calculations, including:
- Decimal precision handling for monetary values
- Correct formula application for fee calculations
- Proper handling of edge cases (very large/small values)
- Volatility and event risk adjustments
- Consistent rounding behavior for financial amounts

These tests are critical for ensuring that all financial calculations meet industry standards for accuracy and precision.

### 3. Data Retention Tests (`data_retention`)
Confirms that all required data is properly retained according to regulatory timeframes:
- Transaction records maintained for the required 7-year period
- Calculation details preserved with full fidelity
- Historical rate information stored appropriately
- Data immutability for regulatory compliance
- Proper handling of data access and retrieval

These tests verify compliance with SEC Rule 17a-4 and other data retention requirements.

### 4. Rate Conformity Tests (`rate_conformity`)
Ensures that borrow rates and fee calculations conform to industry standards:
- Base rate calculations align with market standards
- Markup and fee structures are applied consistently
- Rate adjustments for volatility follow documented formulas
- Minimum and maximum rate constraints are enforced
- Rate changes are properly tracked and documented

These tests help prevent pricing anomalies and ensure fair, consistent fee application.

### 5. API Documentation Tests (`api_documentation`)
Verifies that API documentation and behavior are in sync:
- All endpoints are properly documented
- Request/response formats match documentation
- Error responses include required compliance information
- Rate limiting is properly documented and implemented
- Versioning strategy is clearly documented

These tests help ensure that integration partners have accurate information for compliance purposes.

## Regulatory Requirements

The compliance tests address several key regulatory requirements:

### SEC Rule 17a-4
This rule requires broker-dealers to preserve records of financial transactions for specified periods (generally 7 years). Our tests verify:
- Complete transaction records are maintained
- Records are stored in a non-rewriteable, non-erasable format
- Records can be accurately reproduced for regulatory review
- All required transaction details are captured

### Financial Calculation Standards
Industry standards for financial calculations require:
- Appropriate decimal precision (typically 4+ decimal places for rates)
- Consistent rounding behavior (half-up rounding for monetary values)
- Accurate application of financial formulas
- Proper handling of compounding and time-based prorations
- Reproducible calculation results

### Audit Trail Requirements
Financial systems must maintain comprehensive audit trails that:
- Record all system activities that affect financial calculations
- Capture the identity of users/systems initiating transactions
- Include timestamps and sequential identifiers
- Document all data sources used in calculations
- Provide sufficient detail for regulatory reviews

## Test Structure

Compliance tests are organized using the following structure:

```
src/test/compliance_tests/
├── conftest.py                        # Shared fixtures and configuration
├── helpers/
│   ├── __init__.py
│   ├── audit_validation.py            # Audit trail validation utilities
│   ├── calculation_validation.py      # Calculation accuracy validation
│   └── retention_validation.py        # Data retention validation
├── test_api_documentation.py          # API documentation tests
├── test_audit_trail.py                # Audit trail tests
├── test_calculation_accuracy.py       # Calculation accuracy tests
├── test_data_retention.py             # Data retention tests
└── test_rate_conformity.py            # Rate conformity tests
```

Each test module uses pytest markers to categorize tests:
- `@pytest.mark.compliance` - Applied to all compliance tests
- `@pytest.mark.audit_trail` - Audit trail specific tests
- `@pytest.mark.calculation_accuracy` - Calculation accuracy tests
- `@pytest.mark.data_retention` - Data retention tests
- `@pytest.mark.rate_conformity` - Rate conformity tests
- `@pytest.mark.api_documentation` - API documentation tests

## Running Compliance Tests

Compliance tests can be run using the pytest framework. To run the entire compliance test suite:

```bash
pytest src/test/compliance_tests/ -v
```

To run a specific category of compliance tests:

```bash
pytest src/test/compliance_tests/test_audit_trail.py -v
pytest src/test/compliance_tests/ -m calculation_accuracy -v
pytest src/test/compliance_tests/ -m "compliance and not data_retention" -v
```

### Environment Configuration

Compliance tests require specific environment configuration:
1. Set up a test database with appropriate test data
2. Configure the TEST_ENVIRONMENT variable (typically "test" or "compliance")
3. Ensure proper credentials are available for all test services

For full compliance testing, configure the following environment variables:
- `COMPLIANCE_TEST_DB_URL`: Database connection string for compliance testing
- `RETENTION_STORAGE_PATH`: Path to data retention storage
- `AUDIT_LOG_PATH`: Path to audit log storage
- `API_VERSION_TESTED`: API version being tested for documentation verification

## Validation Helpers

The compliance test suite includes validation helper modules to simplify testing:

### Audit Validation

The `audit_validation.py` module provides utilities for validating audit trail requirements:

```python
from src.test.compliance_tests.helpers.audit_validation import AuditValidator

auditor = TransactionAuditor()
validator = AuditValidator(auditor)

# Validate a specific transaction
result = validator.validate_transaction(
    client_id="test_client",
    ticker="AAPL",
    position_value=Decimal("100000.00"),
    loan_days=30,
    expected_fee=Decimal("150.00")
)

# Generate a compliance report
report = validator.generate_compliance_report(
    start_date=datetime.now() - timedelta(days=30),
    end_date=datetime.now()
)
```

### Calculation Validation

The `calculation_validation.py` module provides utilities for validating calculation accuracy:

```python
from src.test.compliance_tests.helpers.calculation_validation import CalculationValidator

validator = CalculationValidator()

# Validate a calculation
result = validator.validate_calculation(calculation)

# Validate precision requirements
precision_valid = validator.validate_precision(calculation)

# Get detailed validation results
validation_results = validator.get_validation_results()
```

## Compliance Reporting

The compliance test suite includes reporting features that generate detailed compliance reports suitable for regulatory review:

1. **HTML Reports**: Comprehensive reports with test results, coverage, and compliance status
2. **CSV Exports**: Detailed test results in a format suitable for regulatory submission
3. **Compliance Dashboards**: Real-time visualization of compliance status

To generate compliance reports:

```bash
pytest src/test/compliance_tests/ --compliance-report=report.html
```

Reports include:
- Test coverage by compliance category
- Pass/fail status for all requirements
- Detailed failure information
- Evidence of compliance for successful tests
- Timestamps and execution context

## Extending Compliance Tests

When adding new compliance tests or extending existing ones:

1. **Identify the requirement**: Clearly document which regulatory or industry requirement the test addresses
2. **Add appropriate markers**: Include the correct pytest markers for categorization
3. **Use validation helpers**: Leverage existing validation helpers when possible
4. **Include comprehensive assertions**: Ensure all aspects of compliance are verified
5. **Document compliance evidence**: Include comments explaining how the test demonstrates compliance
6. **Add to CI/CD pipeline**: Ensure new tests are integrated into the continuous compliance workflow

Template for new compliance test:

```python
import pytest
from decimal import Decimal
from src.test.compliance_tests.helpers.calculation_validation import CalculationValidator

@pytest.mark.compliance
@pytest.mark.calculation_accuracy
def test_new_compliance_requirement():
    """
    Test compliance with [specific requirement].
    
    Regulatory reference: [citation or document reference]
    Requirement summary: [brief description]
    """
    # Test setup
    validator = CalculationValidator()
    
    # Test execution
    result = validator.validate_specific_requirement()
    
    # Assertions
    assert result.is_compliant, f"Compliance failure: {result.failure_reason}"
    assert result.evidence_available, "No compliance evidence available"
```

## Test Data

Compliance tests use specialized test data to validate regulatory requirements:

### Standard Test Scenarios
- Basic fee calculations with known values
- Edge cases (very large positions, extreme rates)
- Historical calculations for retention testing
- Audit trail verification scenarios

### Test Data Management
Test data is managed through:
1. Pytest fixtures defined in `conftest.py`
2. Static test data files in `test_data/` directory
3. Programmatically generated test cases

When adding new test data, ensure:
- All test data is clearly documented
- Source and rationale for test values are provided
- Edge cases are adequately represented
- Data meets regulatory test requirements

## Integration with CI/CD

Compliance tests are integrated into the CI/CD pipeline to ensure continuous compliance:

1. **Pull Request Checks**: Basic compliance tests run on every PR
2. **Nightly Compliance Suite**: Complete compliance test suite runs nightly
3. **Pre-Release Gate**: Full compliance verification required before production deployment
4. **Scheduled Compliance Audits**: Regular comprehensive compliance testing with reports

The CI/CD pipeline automatically generates compliance reports and notifies stakeholders of any compliance issues. Compliance failures in critical areas block deployment to production environments.

Example CI configuration for compliance testing:

```yaml
compliance_tests:
  stage: test
  script:
    - pip install -r requirements-test.txt
    - python -m pytest src/test/compliance_tests/ -v --compliance-report=compliance_report.html
  artifacts:
    paths:
      - compliance_report.html
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
    - if: $CI_PIPELINE_SOURCE == "merge_request_event" && $COMPLIANCE_CHECK == "true"
    - if: $CI_COMMIT_BRANCH == "main"
```

## References

1. **SEC Rule 17a-4**: Securities and Exchange Commission rule requiring broker-dealers to preserve records for specified periods of time. [SEC.gov Rule 17a-4](https://www.sec.gov/rules/final/34-44992.htm)

2. **Financial Calculation Standards**: Industry standards for financial calculation accuracy and precision, including IEEE 754 for floating-point arithmetic and industry-specific standards for fee calculations.

3. **Audit Trail Requirements**: Regulatory requirements for maintaining complete and immutable audit trails of financial transactions, including FINRA Rule 4511 and various SEC requirements for broker-dealers.

4. **Compliance Testing Best Practices**: NIST SP 800-53A, Rev. 4 - Assessing Security and Privacy Controls in Federal Information Systems and Organizations.

5. **API Compliance Standards**: FAPI (Financial-grade API) requirements, OAuth security best practices, and industry-specific API documentation standards.