"""
Helper module providing assertion utilities for integration tests of the Borrow Rate & Locate Fee Pricing Engine.
Contains functions and classes for validating API responses, comparing calculation results, and verifying 
error conditions with appropriate context and precision for financial calculations.
"""

import pytest  # version: 7.4.0+
import requests  # version: 2.28.0+
import json  # standard library
from decimal import Decimal  # standard library
from typing import Dict, List, Any, Optional, Union, Type  # standard library

from src.backend.schemas.response import (
    CalculateLocateResponse, 
    BorrowRateResponse, 
    HealthResponse
)
from src.backend.schemas.error import ErrorResponse, ValidationError
from src.backend.core.constants import ErrorCodes
from .api_client import parse_response

# Default precision for decimal comparisons in financial calculations
DEFAULT_PRECISION = 4

# Configure module logger
logger = logging.getLogger(__name__)


def assert_status_code(response: requests.Response, expected_status_code: int) -> None:
    """
    Asserts that the HTTP response has the expected status code
    
    Args:
        response: The HTTP response from requests
        expected_status_code: The expected HTTP status code
    
    Raises:
        AssertionError: If the status code doesn't match the expected value
    """
    assert response.status_code == expected_status_code, \
        f"Expected status code {expected_status_code}, got {response.status_code}. Response: {response.text}"


def assert_json_response(response: requests.Response) -> Dict[str, Any]:
    """
    Asserts that the response contains valid JSON and returns the parsed data
    
    Args:
        response: The HTTP response from requests
        
    Returns:
        Parsed JSON response data
        
    Raises:
        AssertionError: If the response is not valid JSON
    """
    try:
        return response.json()
    except json.JSONDecodeError as e:
        pytest.fail(f"Response is not valid JSON: {e}. Response content: {response.text[:200]}")


def assert_decimal_equality(
    actual: Union[Decimal, float, int], 
    expected: Union[Decimal, float, int], 
    precision: Optional[int] = None
) -> None:
    """
    Asserts that two decimal values are equal within the specified precision
    
    Args:
        actual: The actual value from the response
        expected: The expected value for comparison
        precision: Number of decimal places for comparison (uses DEFAULT_PRECISION if None)
        
    Raises:
        AssertionError: If the values are not equal within the specified precision
    """
    # Use default precision if not specified
    precision = precision if precision is not None else DEFAULT_PRECISION
    
    # Convert to Decimal if not already
    if not isinstance(actual, Decimal):
        actual = Decimal(str(actual))
    if not isinstance(expected, Decimal):
        expected = Decimal(str(expected))
    
    # Round to specified precision for comparison
    actual_rounded = round(actual, precision)
    expected_rounded = round(expected, precision)
    
    assert actual_rounded == expected_rounded, \
        f"Values differ: expected {expected_rounded} but got {actual_rounded}. " \
        f"Difference: {abs(actual_rounded - expected_rounded)}"


class Assertions:
    """
    Class providing assertion utilities for API response validation in integration tests
    """
    
    def __init__(self, precision: Optional[int] = None):
        """
        Initializes the Assertions helper with optional precision setting
        
        Args:
            precision: Number of decimal places for financial value comparisons
        """
        self._precision = precision if precision is not None else DEFAULT_PRECISION
    
    def assert_successful_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Asserts that the response indicates a successful operation
        
        Args:
            response: The HTTP response from requests
            
        Returns:
            Parsed JSON response data
            
        Raises:
            AssertionError: If the response is not successful
        """
        assert_status_code(response, 200)
        data = assert_json_response(response)
        assert data.get('status') == 'success', \
            f"Expected status 'success', got '{data.get('status')}'. Response: {data}"
        return data
    
    def assert_error_response(
        self, 
        response: requests.Response, 
        expected_status_code: int,
        expected_error_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Asserts that the response indicates an error with the expected error code
        
        Args:
            response: The HTTP response from requests
            expected_status_code: The expected HTTP status code
            expected_error_code: The expected error code (if specified)
            
        Returns:
            Parsed JSON error response data
            
        Raises:
            AssertionError: If the response doesn't match the expected error
        """
        assert_status_code(response, expected_status_code)
        data = assert_json_response(response)
        assert data.get('status') == 'error', \
            f"Expected status 'error', got '{data.get('status')}'. Response: {data}"
        
        if expected_error_code:
            assert data.get('error_code') == expected_error_code, \
                f"Expected error code '{expected_error_code}', got '{data.get('error_code')}'. Response: {data}"
        
        return data
    
    def assert_validation_error(
        self, 
        response: requests.Response,
        field_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Asserts that the response indicates a validation error
        
        Args:
            response: The HTTP response from requests
            field_name: The field name that should have a validation error (if specified)
            
        Returns:
            Parsed JSON validation error response data
            
        Raises:
            AssertionError: If the response doesn't match a validation error
        """
        assert_status_code(response, 400)
        data = assert_json_response(response)
        assert data.get('status') == 'error', \
            f"Expected status 'error', got '{data.get('status')}'. Response: {data}"
        assert data.get('error_code') == ErrorCodes.INVALID_PARAMETER.value, \
            f"Expected error code '{ErrorCodes.INVALID_PARAMETER.value}', got '{data.get('error_code')}'. Response: {data}"
        
        # Check for validation_errors field
        validation_errors = data.get('validation_errors')
        assert validation_errors is not None, \
            f"Expected 'validation_errors' field in response. Response: {data}"
        assert isinstance(validation_errors, list), \
            f"Expected 'validation_errors' to be a list. Response: {data}"
        
        # If a specific field name is provided, check that it's in the validation errors
        if field_name:
            field_found = any(error.get('field') == field_name for error in validation_errors)
            assert field_found, \
                f"Expected validation error for field '{field_name}' not found. Validation errors: {validation_errors}"
        
        return data
    
    def assert_calculation_result(
        self,
        response: requests.Response,
        expected_total_fee: Optional[Union[Decimal, float, int]] = None,
        expected_borrow_rate: Optional[Union[Decimal, float, int]] = None,
        expected_breakdown: Optional[Dict[str, Union[Decimal, float, int]]] = None
    ) -> CalculateLocateResponse:
        """
        Asserts that the locate fee calculation response contains expected values
        
        Args:
            response: The HTTP response from requests
            expected_total_fee: Expected total fee amount
            expected_borrow_rate: Expected borrow rate used in calculation
            expected_breakdown: Expected fee breakdown components
            
        Returns:
            Parsed calculation response
            
        Raises:
            AssertionError: If the response doesn't match the expected values
        """
        assert_status_code(response, 200)
        result = parse_response(response, CalculateLocateResponse)
        
        # Verify it's a successful response
        assert result.status == 'success', \
            f"Expected status 'success', got '{result.status}'. Response: {response.text}"
        
        # Check total fee if provided
        if expected_total_fee is not None:
            assert_decimal_equality(result.total_fee, expected_total_fee, self._precision)
        
        # Check borrow rate if provided
        if expected_borrow_rate is not None:
            assert_decimal_equality(result.borrow_rate_used, expected_borrow_rate, self._precision)
        
        # Check breakdown components if provided
        if expected_breakdown:
            for key, value in expected_breakdown.items():
                assert hasattr(result.breakdown, key), \
                    f"Expected breakdown component '{key}' not found in response. Breakdown: {result.breakdown}"
                actual_value = getattr(result.breakdown, key)
                assert_decimal_equality(actual_value, value, self._precision)
        
        return result
    
    def assert_rate_response(
        self,
        response: requests.Response,
        expected_ticker: str,
        expected_rate: Optional[Union[Decimal, float, int]] = None,
        expected_borrow_status: Optional[str] = None
    ) -> BorrowRateResponse:
        """
        Asserts that the borrow rate response contains expected values
        
        Args:
            response: The HTTP response from requests
            expected_ticker: Expected ticker symbol
            expected_rate: Expected borrow rate
            expected_borrow_status: Expected borrow status (EASY, MEDIUM, HARD)
            
        Returns:
            Parsed borrow rate response
            
        Raises:
            AssertionError: If the response doesn't match the expected values
        """
        assert_status_code(response, 200)
        result = parse_response(response, BorrowRateResponse)
        
        # Verify it's a successful response
        assert result.status == 'success', \
            f"Expected status 'success', got '{result.status}'. Response: {response.text}"
        
        # Check ticker
        assert result.ticker == expected_ticker, \
            f"Expected ticker '{expected_ticker}', got '{result.ticker}'"
        
        # Check rate if provided
        if expected_rate is not None:
            assert_decimal_equality(result.current_rate, expected_rate, self._precision)
        
        # Check borrow status if provided
        if expected_borrow_status is not None:
            assert result.borrow_status == expected_borrow_status, \
                f"Expected borrow status '{expected_borrow_status}', got '{result.borrow_status}'"
        
        return result
    
    def assert_health_check(self, response: requests.Response) -> HealthResponse:
        """
        Asserts that the health check response indicates a healthy system
        
        Args:
            response: The HTTP response from requests
            
        Returns:
            Parsed health check response
            
        Raises:
            AssertionError: If the response doesn't indicate a healthy system
        """
        assert_status_code(response, 200)
        result = parse_response(response, HealthResponse)
        
        # Verify it's a healthy response
        assert result.status == 'healthy', \
            f"Expected status 'healthy', got '{result.status}'. Response: {response.text}"
        
        # Check that components field exists and is a dictionary
        assert result.components is not None, \
            "Expected 'components' field in health check response"
        assert isinstance(result.components, dict), \
            f"Expected 'components' to be a dictionary, got {type(result.components)}"
        
        return result
    
    def assert_external_api_unavailable(self, response: requests.Response) -> Dict[str, Any]:
        """
        Asserts that the response indicates an external API unavailable error
        
        Args:
            response: The HTTP response from requests
            
        Returns:
            Parsed error response data
            
        Raises:
            AssertionError: If the response doesn't match the expected error
        """
        return self.assert_error_response(
            response=response,
            expected_status_code=503,
            expected_error_code=ErrorCodes.EXTERNAL_API_UNAVAILABLE.value
        )
    
    def assert_ticker_not_found(self, response: requests.Response, ticker: Optional[str] = None) -> Dict[str, Any]:
        """
        Asserts that the response indicates a ticker not found error
        
        Args:
            response: The HTTP response from requests
            ticker: The ticker symbol that should be mentioned in the error
            
        Returns:
            Parsed error response data
            
        Raises:
            AssertionError: If the response doesn't match the expected error
        """
        data = self.assert_error_response(
            response=response,
            expected_status_code=404,
            expected_error_code=ErrorCodes.TICKER_NOT_FOUND.value
        )
        
        # If a ticker is provided, check that it's mentioned in the error message
        if ticker:
            error_msg = data.get('error', '').lower()
            assert ticker.lower() in error_msg, \
                f"Expected ticker '{ticker}' to be mentioned in error message: '{error_msg}'"
        
        return data
    
    def assert_client_not_found(self, response: requests.Response, client_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Asserts that the response indicates a client not found error
        
        Args:
            response: The HTTP response from requests
            client_id: The client ID that should be mentioned in the error
            
        Returns:
            Parsed error response data
            
        Raises:
            AssertionError: If the response doesn't match the expected error
        """
        data = self.assert_error_response(
            response=response,
            expected_status_code=404,
            expected_error_code=ErrorCodes.CLIENT_NOT_FOUND.value
        )
        
        # If a client_id is provided, check that it's mentioned in the error message
        if client_id:
            error_msg = data.get('error', '').lower()
            assert client_id.lower() in error_msg, \
                f"Expected client ID '{client_id}' to be mentioned in error message: '{error_msg}'"
        
        return data