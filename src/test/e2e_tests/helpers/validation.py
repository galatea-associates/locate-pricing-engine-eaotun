"""
Helper module for validating API responses and calculation results in end-to-end tests
of the Borrow Rate & Locate Fee Pricing Engine. Provides utilities for comparing actual
API responses against expected values with appropriate tolerance for financial calculations.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Union, Any, Tuple
from copy import deepcopy

from .api_client import APIClient
from ..config.settings import get_test_settings, TestEnvironment
from .test_data import (
    get_test_scenario, get_stock_data, get_volatility_data,
    calculate_expected_borrow_rate, calculate_expected_fee,
    is_decimal_equal, compare_calculation_results
)
from src.backend.schemas.response import CalculateLocateResponse, BorrowRateResponse

# Configure logger
logger = logging.getLogger(__name__)

# Default tolerance for decimal comparisons
DEFAULT_TOLERANCE = Decimal('0.0001')


def format_decimal_diff(actual: Decimal, expected: Decimal) -> str:
    """
    Formats the difference between two decimal values for error messages

    Args:
        actual: Actual decimal value
        expected: Expected decimal value

    Returns:
        Formatted string showing the difference
    """
    abs_diff = abs(actual - expected)
    if expected != Decimal('0'):
        pct_diff = (abs_diff / abs(expected)) * Decimal('100')
        return f"actual={actual}, expected={expected}, diff={abs_diff}, pct_diff={pct_diff}%"
    else:
        return f"actual={actual}, expected={expected}, diff={abs_diff}"


def format_validation_error(field_name: str, actual: Any, expected: Any, context: Optional[str] = None) -> str:
    """
    Formats a validation error message with detailed information

    Args:
        field_name: Name of the field being validated
        actual: Actual value
        expected: Expected value
        context: Optional additional context for the error

    Returns:
        Formatted error message
    """
    error_msg = f"Validation error for field '{field_name}'"
    if context:
        error_msg += f" ({context})"
    error_msg += ": "

    if isinstance(actual, Decimal) and isinstance(expected, Decimal):
        error_msg += format_decimal_diff(actual, expected)
    else:
        error_msg += f"actual={actual}, expected={expected}"
    
    return error_msg


class ResponseValidator:
    """
    Validates API responses against expected values for end-to-end tests
    """

    def __init__(self, api_client: APIClient, tolerance: Optional[Decimal] = None):
        """
        Initializes the ResponseValidator with API client and tolerance

        Args:
            api_client: Client for making API requests
            tolerance: Tolerance for decimal comparisons (default: DEFAULT_TOLERANCE)
        """
        self._api_client = api_client
        self._tolerance = tolerance or DEFAULT_TOLERANCE
        logger.info(f"Initialized ResponseValidator with tolerance {self._tolerance}")

    def assert_calculation(self, scenario: Union[str, dict], expected_result: Optional[dict] = None) -> Tuple[dict, dict]:
        """
        Validates a fee calculation against expected result

        Args:
            scenario: Test scenario name or dictionary
            expected_result: Optional expected result dictionary

        Returns:
            Tuple of actual and expected results

        Raises:
            AssertionError: If calculation does not match expected result
        """
        # Get scenario data if string provided
        if isinstance(scenario, str):
            scenario = get_test_scenario(scenario)
        
        # Calculate expected result if not provided
        if expected_result is None:
            expected_result = calculate_expected_fee(scenario)
        
        # Extract parameters from scenario
        ticker = scenario['ticker']
        position_value = scenario['position_value']
        loan_days = scenario['loan_days']
        client_id = scenario['client_id']
        
        # Call API to get actual result
        actual_result = self._api_client.calculate_locate_fee(
            ticker=ticker,
            position_value=position_value,
            loan_days=loan_days,
            client_id=client_id
        )
        
        # Check if we got a CalculateLocateResponse or an error dict
        if isinstance(actual_result, dict) and actual_result.get('status') == 'error':
            # If expecting an error response, check that we got an error
            if expected_result.get('status') == 'error':
                return actual_result, expected_result
            
            # Unexpected error
            error_msg = f"API returned an error: {actual_result.get('message', 'Unknown error')}"
            raise AssertionError(error_msg)
        
        # Verify response status
        self.assert_response_status(actual_result, 'success')
        
        # Compare results
        differences = compare_calculation_results(actual_result, expected_result, self._tolerance)
        
        # Raise assertion error if differences exist
        if differences:
            error_msg = f"Calculation for scenario does not match expected result:\n"
            for field, diff in differences.items():
                if field == 'breakdown':
                    for bd_field, bd_diff in diff.items():
                        error_msg += format_validation_error(
                            f"breakdown.{bd_field}", 
                            bd_diff['actual'], 
                            bd_diff['expected']
                        ) + "\n"
                else:
                    error_msg += format_validation_error(
                        field, 
                        diff['actual'], 
                        diff['expected']
                    ) + "\n"
            
            raise AssertionError(error_msg)
        
        return actual_result, expected_result

    def assert_borrow_rate(self, ticker: str, expected_rate: Optional[Decimal] = None) -> Tuple[Decimal, Decimal]:
        """
        Validates a borrow rate against expected value

        Args:
            ticker: Stock ticker symbol
            expected_rate: Optional expected borrow rate

        Returns:
            Tuple of actual and expected rates

        Raises:
            AssertionError: If borrow rate does not match expected rate
        """
        # Call API to get actual rate
        response = self._api_client.get_borrow_rate(ticker)
        
        # Check if we got a BorrowRateResponse or an error dict
        if isinstance(response, dict) and response.get('status') == 'error':
            error_msg = f"API returned an error when fetching borrow rate for {ticker}: {response.get('message', 'Unknown error')}"
            raise AssertionError(error_msg)
        
        # Verify response status
        self.assert_response_status(response, 'success')
        
        # Get actual rate
        actual_rate = response.current_rate
        
        # Calculate expected rate if not provided
        if expected_rate is None:
            stock_data = get_stock_data(ticker)
            volatility_data = get_volatility_data(ticker)
            expected_rate = calculate_expected_borrow_rate(stock_data, volatility_data)
        
        # Compare rates
        if not is_decimal_equal(actual_rate, expected_rate, self._tolerance):
            error_msg = format_validation_error(
                'borrow_rate', 
                actual_rate, 
                expected_rate, 
                f"ticker={ticker}"
            )
            raise AssertionError(error_msg)
        
        return actual_rate, expected_rate

    def assert_response_status(self, response: dict, expected_status: str) -> bool:
        """
        Validates that a response has the expected status

        Args:
            response: Response dictionary
            expected_status: Expected status value

        Returns:
            True if validation passes

        Raises:
            AssertionError: If status does not match expected status
        """
        if 'status' not in response:
            raise AssertionError(f"Response does not contain 'status' field: {response}")
        
        actual_status = response['status']
        if actual_status != expected_status:
            error_msg = f"Invalid response status: actual='{actual_status}', expected='{expected_status}'"
            raise AssertionError(error_msg)
        
        return True

    def assert_decimal_field(self, response: dict, field_name: str, expected_value: Decimal, 
                             context: Optional[str] = None) -> bool:
        """
        Validates that a decimal field matches expected value within tolerance

        Args:
            response: Response dictionary
            field_name: Name of the field to validate
            expected_value: Expected decimal value
            context: Optional additional context for error message

        Returns:
            True if validation passes

        Raises:
            AssertionError: If field value does not match expected value
        """
        if field_name not in response:
            raise AssertionError(f"Response does not contain field '{field_name}': {response}")
        
        actual_value = response[field_name]
        if not is_decimal_equal(actual_value, expected_value, self._tolerance):
            error_msg = format_validation_error(field_name, actual_value, expected_value, context)
            raise AssertionError(error_msg)
        
        return True

    def assert_breakdown(self, actual_breakdown: dict, expected_breakdown: dict) -> bool:
        """
        Validates that a fee breakdown matches expected values

        Args:
            actual_breakdown: Actual breakdown dictionary
            expected_breakdown: Expected breakdown dictionary

        Returns:
            True if validation passes

        Raises:
            AssertionError: If breakdown fields do not match expected values
        """
        if actual_breakdown is None or expected_breakdown is None:
            if actual_breakdown is None and expected_breakdown is None:
                return True
            
            error_msg = f"Breakdown mismatch: actual={'None' if actual_breakdown is None else 'present'}, expected={'None' if expected_breakdown is None else 'present'}"
            raise AssertionError(error_msg)
        
        # Check that keys match
        actual_keys = set(actual_breakdown.keys())
        expected_keys = set(expected_breakdown.keys())
        
        if actual_keys != expected_keys:
            missing_keys = expected_keys - actual_keys
            extra_keys = actual_keys - expected_keys
            error_msg = f"Breakdown keys do not match.\n"
            if missing_keys:
                error_msg += f"Missing keys: {missing_keys}\n"
            if extra_keys:
                error_msg += f"Extra keys: {extra_keys}\n"
            raise AssertionError(error_msg)
        
        # Check values for each key
        for key in expected_keys:
            expected_value = expected_breakdown[key]
            actual_value = actual_breakdown[key]
            
            if not is_decimal_equal(actual_value, expected_value, self._tolerance):
                error_msg = format_validation_error(
                    f"breakdown.{key}", 
                    actual_value, 
                    expected_value
                )
                raise AssertionError(error_msg)
        
        return True


def create_response_validator(api_client: Optional[APIClient] = None, 
                             tolerance: Optional[Decimal] = None) -> ResponseValidator:
    """
    Factory function to create a ResponseValidator instance

    Args:
        api_client: Optional API client instance
        tolerance: Optional tolerance for decimal comparisons

    Returns:
        Configured validator instance
    """
    if api_client is None:
        api_client = APIClient()
    
    return ResponseValidator(api_client, tolerance)