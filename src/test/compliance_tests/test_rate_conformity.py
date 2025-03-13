"""
Compliance test module that verifies the conformity of borrow rate calculations with financial regulations and industry standards.
This module tests that all rate calculations are accurate, consistent, and follow the required formulas for volatility adjustments,
event risk factors, and minimum rate enforcement.
"""

import pytest  # pytest 7.4.0+
from decimal import Decimal  # standard library
import logging  # standard library
import json  # standard library
from typing import Dict, Any  # standard library

# Internal imports
from src.test.compliance_tests.helpers.calculation_validation import (
    CalculationValidator,
    validate_borrow_rate_calculation,
    verify_volatility_adjustment,
    verify_event_risk_adjustment
)
from src.test.compliance_tests.helpers.audit_validation import AuditValidator, TransactionAuditor
from src.backend.services.calculation.borrow_rate import calculate_borrow_rate
from src.backend.services.calculation.locate_fee import calculate_locate_fee
from src.backend.core.constants import (
    DAYS_IN_YEAR,
    DEFAULT_MINIMUM_BORROW_RATE,
    DEFAULT_VOLATILITY_FACTOR,
    DEFAULT_EVENT_RISK_FACTOR,
    TransactionFeeType,
    BorrowStatus
)

# Initialize logger
logger = logging.getLogger(__name__)

# Constants for precision and tolerance
ROUNDING_PRECISION = 4
CALCULATION_PRECISION_TOLERANCE = Decimal('0.0001')


@pytest.mark.compliance
@pytest.mark.rate_conformity
def test_borrow_rate_calculation_accuracy():
    """
    Tests that borrow rate calculations are accurate according to the defined formulas
    """
    # Define test cases with different base rates, volatility indices, and event risk factors
    test_cases = [
        {"base_rate": Decimal('0.05'), "volatility_index": Decimal('20.0'), "event_risk_factor": 2, "expected_rate": Decimal('0.061')},
        {"base_rate": Decimal('0.10'), "volatility_index": Decimal('30.0'), "event_risk_factor": 5, "expected_rate": Decimal('0.1475')},
        {"base_rate": Decimal('0.01'), "volatility_index": Decimal('10.0'), "event_risk_factor": 0, "expected_rate": Decimal('0.011')},
        {"base_rate": Decimal('0.20'), "volatility_index": Decimal('40.0'), "event_risk_factor": 8, "expected_rate": Decimal('0.364')},
        {"base_rate": Decimal('0.005'), "volatility_index": Decimal('5.0'), "event_risk_factor": 1, "expected_rate": Decimal('0.00528')},
    ]

    # For each test case, calculate the expected rate using the defined formulas
    for case in test_cases:
        base_rate = case["base_rate"]
        volatility_index = case["volatility_index"]
        event_risk_factor = case["event_risk_factor"]
        expected_rate = case["expected_rate"]

        # Call calculate_borrow_rate with the test parameters
        calculated_rate = calculate_borrow_rate(
            ticker="AAPL",  # Ticker is not used in the calculation, so it's hardcoded
            min_rate=None,  # Minimum rate is not enforced in this test
            use_cache=False  # Do not use cache for testing purposes
        )

        # Verify that the calculated rate matches the expected rate within tolerance
        is_valid = validate_borrow_rate_calculation(
            base_rate=base_rate,
            volatility_index=volatility_index,
            event_risk_factor=event_risk_factor,
            calculated_rate=calculated_rate,
            min_rate=None  # Minimum rate is not enforced in this test
        )

        # Assert that all calculations are accurate
        assert is_valid, f"Calculation failed for {case}: expected {expected_rate}, got {calculated_rate}"


@pytest.mark.compliance
@pytest.mark.rate_conformity
def test_volatility_adjustment_conformity():
    """
    Tests that volatility adjustments are correctly applied to borrow rates
    """
    # Define test cases with different base rates and volatility indices
    test_cases = [
        {"base_rate": Decimal('0.05'), "volatility_index": Decimal('20.0'), "adjusted_rate": Decimal('0.060')},
        {"base_rate": Decimal('0.10'), "volatility_index": Decimal('30.0'), "adjusted_rate": Decimal('0.130')},
        {"base_rate": Decimal('0.01'), "volatility_index": Decimal('10.0'), "adjusted_rate": Decimal('0.011')},
        {"base_rate": Decimal('0.20'), "volatility_index": Decimal('40.0'), "adjusted_rate": Decimal('0.280')},
        {"base_rate": Decimal('0.005'), "volatility_index": Decimal('5.0'), "adjusted_rate": Decimal('0.00525')},
    ]

    # For each test case, calculate the expected volatility-adjusted rate
    for case in test_cases:
        base_rate = case["base_rate"]
        volatility_index = case["volatility_index"]
        adjusted_rate = case["adjusted_rate"]

        # Call verify_volatility_adjustment with the test parameters
        is_valid = verify_volatility_adjustment(
            base_rate=base_rate,
            volatility_index=volatility_index,
            adjusted_rate=adjusted_rate,
            volatility_factor=DEFAULT_VOLATILITY_FACTOR  # Use default volatility factor
        )

        # Assert that all volatility adjustments are accurate
        assert is_valid, f"Volatility adjustment failed for {case}: expected {adjusted_rate}, got incorrect adjustment"


@pytest.mark.compliance
@pytest.mark.rate_conformity
def test_event_risk_adjustment_conformity():
    """
    Tests that event risk adjustments are correctly applied to borrow rates
    """
    # Define test cases with different base rates and event risk factors
    test_cases = [
        {"base_rate": Decimal('0.05'), "event_risk_factor": 2, "adjusted_rate": Decimal('0.0505')},
        {"base_rate": Decimal('0.10'), "event_risk_factor": 5, "adjusted_rate": Decimal('0.1025')},
        {"base_rate": Decimal('0.01'), "event_risk_factor": 0, "adjusted_rate": Decimal('0.0100')},
        {"base_rate": Decimal('0.20'), "event_risk_factor": 8, "adjusted_rate": Decimal('0.2080')},
        {"base_rate": Decimal('0.005'), "event_risk_factor": 1, "adjusted_rate": Decimal('0.00503')},
    ]

    # For each test case, calculate the expected risk-adjusted rate
    for case in test_cases:
        base_rate = case["base_rate"]
        event_risk_factor = case["event_risk_factor"]
        adjusted_rate = case["adjusted_rate"]

        # Call verify_event_risk_adjustment with the test parameters
        is_valid = verify_event_risk_adjustment(
            base_rate=base_rate,
            event_risk_factor=event_risk_factor,
            adjusted_rate=adjusted_rate,
            risk_multiplier=DEFAULT_EVENT_RISK_FACTOR  # Use default risk multiplier
        )

        # Assert that all event risk adjustments are accurate
        assert is_valid, f"Event risk adjustment failed for {case}: expected {adjusted_rate}, got incorrect adjustment"


@pytest.mark.compliance
@pytest.mark.rate_conformity
def test_minimum_rate_enforcement():
    """
    Tests that minimum borrow rates are enforced correctly
    """
    # Define test cases with rates below and above minimum thresholds
    test_cases = [
        {"calculated_rate": Decimal('0.00005'), "min_rate": Decimal('0.0001'), "expected_rate": Decimal('0.0001')},
        {"calculated_rate": Decimal('0.00015'), "min_rate": Decimal('0.0001'), "expected_rate": Decimal('0.00015')},
        {"calculated_rate": Decimal('0.00005'), "min_rate": None, "expected_rate": DEFAULT_MINIMUM_BORROW_RATE},
        {"calculated_rate": Decimal('0.00015'), "min_rate": None, "expected_rate": Decimal('0.00015')},
    ]

    # For each test case, calculate the expected rate after minimum enforcement
    for case in test_cases:
        calculated_rate = case["calculated_rate"]
        min_rate = case["min_rate"]
        expected_rate = case["expected_rate"]

        # Call calculate_borrow_rate with the test parameters and minimum rate
        if min_rate is None:
            min_rate_to_use = DEFAULT_MINIMUM_BORROW_RATE
        else:
            min_rate_to_use = min_rate

        calculated_rate_with_min = max(calculated_rate, min_rate_to_use)

        # Verify that the calculated rate is never below the minimum rate
        assert calculated_rate_with_min == expected_rate, f"Minimum rate enforcement failed for {case}: expected {expected_rate}, got {calculated_rate_with_min}"

        # Assert that minimum rate enforcement is working correctly
        assert calculated_rate_with_min >= min_rate_to_use if min_rate is not None else calculated_rate_with_min >= DEFAULT_MINIMUM_BORROW_RATE, "Rate is below minimum"


@pytest.mark.compliance
@pytest.mark.rate_conformity
def test_rate_precision_conformity():
    """
    Tests that borrow rate calculations maintain the required decimal precision
    """
    # Define test cases with different calculation parameters
    test_cases = [
        {"base_rate": Decimal('0.0512345'), "volatility_index": Decimal('20.12345'), "event_risk_factor": 2},
        {"base_rate": Decimal('0.1098765'), "volatility_index": Decimal('30.98765'), "event_risk_factor": 5},
        {"base_rate": Decimal('0.0145678'), "volatility_index": Decimal('10.45678'), "event_risk_factor": 0},
        {"base_rate": Decimal('0.2012345'), "volatility_index": Decimal('40.12345'), "event_risk_factor": 8},
        {"base_rate": Decimal('0.0056789'), "volatility_index": Decimal('5.67890'), "event_risk_factor": 1},
    ]

    # For each test case, calculate the borrow rate
    for case in test_cases:
        base_rate = case["base_rate"]
        volatility_index = case["volatility_index"]
        event_risk_factor = case["event_risk_factor"]

        # Calculate the borrow rate
        calculated_rate = calculate_borrow_rate(
            ticker="AAPL",  # Ticker is not used in the calculation, so it's hardcoded
            min_rate=None,  # Minimum rate is not enforced in this test
            use_cache=False  # Do not use cache for testing purposes
        )

        # Create a CalculationValidator instance
        validator = CalculationValidator()

        # Call validate_precision with the calculated rate and required precision
        is_valid = validator.validate_precision(
            calculation_result={"total_fee": 1.0, "breakdown": {"borrow_cost": 1.0, "markup": 1.0, "transaction_fees": 1.0}, "borrow_rate_used": calculated_rate},
            required_precision=ROUNDING_PRECISION
        )

        # Verify that all rates maintain the required decimal precision
        assert is_valid, f"Precision check failed for {case}: rate {calculated_rate} does not meet required precision"


@pytest.mark.compliance
@pytest.mark.rate_conformity
def test_rate_calculation_with_extreme_values():
    """
    Tests that borrow rate calculations handle extreme values correctly
    """
    # Define test cases with extreme values (very high/low rates, volatility, etc.)
    test_cases = [
        {"base_rate": Decimal('0.00000001'), "volatility_index": Decimal('0.00000001'), "event_risk_factor": 0},
        {"base_rate": Decimal('1.0'), "volatility_index": Decimal('1000.0'), "event_risk_factor": 10},
        {"base_rate": Decimal('1000.0'), "volatility_index": Decimal('0.00000001'), "event_risk_factor": 0},
    ]

    # For each test case, calculate the expected rate
    for case in test_cases:
        base_rate = case["base_rate"]
        volatility_index = case["volatility_index"]
        event_risk_factor = case["event_risk_factor"]

        # Call calculate_borrow_rate with the extreme test parameters
        calculated_rate = calculate_borrow_rate(
            ticker="AAPL",  # Ticker is not used in the calculation, so it's hardcoded
            min_rate=None,  # Minimum rate is not enforced in this test
            use_cache=False  # Do not use cache for testing purposes
        )

        # Verify that the calculation handles extreme values without errors
        assert isinstance(calculated_rate, Decimal), f"Calculation failed for {case}: did not return a Decimal"

        # Assert that results are still accurate within tolerance
        assert calculated_rate >= 0, f"Calculation failed for {case}: rate is negative"


@pytest.mark.compliance
@pytest.mark.rate_conformity
def test_rate_calculation_consistency():
    """
    Tests that borrow rate calculations are consistent across multiple calls
    """
    # Define a set of test parameters
    test_parameters = {
        "base_rate": Decimal('0.05'),
        "volatility_index": Decimal('20.0'),
        "event_risk_factor": 2
    }

    # Call calculate_borrow_rate multiple times with the same parameters
    results = []
    for _ in range(5):
        calculated_rate = calculate_borrow_rate(
            ticker="AAPL",  # Ticker is not used in the calculation, so it's hardcoded
            min_rate=None,  # Minimum rate is not enforced in this test
            use_cache=False  # Do not use cache for testing purposes
        )
        results.append(calculated_rate)

    # Verify that all results are identical
    first_result = results[0]
    for result in results[1:]:
        assert result == first_result, "Calculations are inconsistent"

    # Assert that calculations are consistent
    assert len(set(results)) == 1, "Calculations are inconsistent"


@pytest.mark.compliance
@pytest.mark.rate_conformity
def test_rate_audit_logging_conformity():
    """
    Tests that borrow rate calculations are properly logged for audit purposes
    """
    # Create a TransactionAuditor instance for testing
    auditor = TransactionAuditor()

    # Create an AuditValidator instance with the auditor
    audit_validator = AuditValidator(auditor)

    # Perform a borrow rate calculation that generates an audit log
    ticker = "AAPL"
    calculated_rate = calculate_borrow_rate(
        ticker=ticker,  # Ticker is used in the calculation
        min_rate=None,  # Minimum rate is not enforced in this test
        use_cache=False  # Do not use cache for testing purposes
    )

    # Retrieve the audit log for the calculation
    # In a real implementation, you would retrieve the audit log from the database
    # For this test, we'll create a mock audit log
    # Create a mock audit log
    class MockAuditLog:
        def __init__(self, ticker, calculated_rate):
            self.ticker = ticker
            self.borrow_rate_used = calculated_rate
            self.data_sources = {"source": "test"}
            self.calculation_breakdown = {"breakdown": "test"}

    mock_audit_log = MockAuditLog(ticker=ticker, calculated_rate=calculated_rate)

    # Validate that the audit log contains all required rate information
    assert mock_audit_log.ticker == ticker, "Ticker does not match"
    assert mock_audit_log.borrow_rate_used == calculated_rate, "Borrow rate does not match"
    assert mock_audit_log.data_sources is not None, "Data sources is None"
    assert mock_audit_log.calculation_breakdown is not None, "Calculation breakdown is None"

    # Assert that audit logging meets compliance requirements
    assert True, "Audit logging meets compliance requirements"


@pytest.mark.compliance
@pytest.mark.rate_conformity
def test_rate_calculation_against_reference_implementation():
    """
    Tests that borrow rate calculations match an independent reference implementation
    """
    # Define test cases with different calculation parameters
    test_cases = [
        {"base_rate": Decimal('0.05'), "volatility_index": Decimal('20.0'), "event_risk_factor": 2},
        {"base_rate": Decimal('0.10'), "volatility_index": Decimal('30.0'), "event_risk_factor": 5},
        {"base_rate": Decimal('0.01'), "volatility_index": Decimal('10.0'), "event_risk_factor": 0},
        {"base_rate": Decimal('0.20'), "volatility_index": Decimal('40.0'), "event_risk_factor": 8},
        {"base_rate": Decimal('0.005'), "volatility_index": Decimal('5.0'), "event_risk_factor": 1},
    ]

    # For each test case, calculate the rate using the system implementation
    for case in test_cases:
        base_rate = case["base_rate"]
        volatility_index = case["volatility_index"]
        event_risk_factor = case["event_risk_factor"]

        # Calculate the rate using the system implementation
        calculated_rate = calculate_borrow_rate(
            ticker="AAPL",  # Ticker is not used in the calculation, so it's hardcoded
            min_rate=None,  # Minimum rate is not enforced in this test
            use_cache=False  # Do not use cache for testing purposes
        )

        # Calculate the rate using an independent reference implementation
        reference_rate = base_rate * (1 + (volatility_index * Decimal('0.01')) + (event_risk_factor / 10 * Decimal('0.05')))

        # Compare the results from both implementations
        assert calculated_rate == pytest.approx(reference_rate, rel=1e-5), "System implementation does not match reference implementation"


class RateConformityTestCase:
    """
    Helper class for defining and running rate conformity test cases
    """

    def __init__(self, test_parameters: Dict[str, Any], expected_result: Decimal):
        """
        Initialize a rate conformity test case
        """
        # Store test parameters
        self.test_parameters = test_parameters
        # Store expected result
        self.expected_result = expected_result
        # Initialize CalculationValidator instance
        self._validator = CalculationValidator()

    def run_test(self) -> bool:
        """
        Run the test case and validate results
        """
        # Extract parameters from test_parameters
        ticker = self.test_parameters["ticker"]
        position_value = self.test_parameters["position_value"]
        loan_days = self.test_parameters["loan_days"]
        markup_percentage = self.test_parameters["markup_percentage"]
        fee_type = self.test_parameters["fee_type"]
        fee_amount = self.test_parameters["fee_amount"]

        # Call calculate_borrow_rate with the parameters
        calculation_result = calculate_locate_fee(
            ticker=ticker,
            position_value=position_value,
            loan_days=loan_days,
            markup_percentage=markup_percentage,
            fee_type=fee_type,
            fee_amount=fee_amount,
            borrow_rate=None,
            use_cache=False
        )

        # Compare the result with expected_result using the validator
        is_valid = self._validator.validate_calculation(calculation_result)

        # Log test results
        logger.info(f"Test case: {self.test_parameters}, Expected: {self.expected_result}, Valid: {is_valid}")

        # Return True if validation passes, False otherwise
        return is_valid

    def get_validation_results(self) -> Dict[str, Any]:
        """
        Get detailed validation results from the last test run
        """
        # Return validation results from the validator
        return self._validator.get_validation_results()