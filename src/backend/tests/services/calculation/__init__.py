"""
Initialization module for the calculation service test package.

This module makes the test package importable and provides common test utilities,
fixtures, and configurations specific to testing the calculation service components.
It facilitates testing of borrow rate calculations, locate fee calculations, 
volatility adjustments, and event risk factors.
"""

from decimal import Decimal
import pytest  # pytest 7.4.0+
from ....__init__ import setup_test_environment

# Constants specific to calculation tests
CALCULATION_TEST_PACKAGE = 'calculation'
DECIMAL_PRECISION = 10
TEST_TOLERANCE = Decimal('0.00001')

def setup_calculation_test_fixtures():
    """
    Sets up common test fixtures and configurations specific to calculation service tests.
    
    This function initializes the test environment with the appropriate settings for
    testing financial calculation components, ensuring consistent decimal precision
    and test tolerances across all calculation tests.
    
    Returns:
        None
    """
    # Initialize base test environment
    setup_test_environment()
    
    # Configure decimal precision for financial calculations
    # This ensures consistent behavior across all calculation tests
    getcontext().prec = DECIMAL_PRECISION
    
    # Set up any calculation-specific test utilities or fixtures
    # This could include mock data or common test configurations
    
    # Note: This can be extended with additional setup as needed

def assert_decimal_equal(actual, expected, tolerance=TEST_TOLERANCE):
    """
    Helper function to assert that two Decimal values are equal within a specified tolerance.
    
    Financial calculations often require comparison with a tolerance due to floating point
    precision issues. This function ensures consistent comparison across all calculation tests.
    
    Args:
        actual (Decimal): The actual value from the test
        expected (Decimal): The expected value for comparison
        tolerance (Decimal): Maximum allowed difference between values (default: TEST_TOLERANCE)
        
    Returns:
        bool: True if the values are equal within tolerance
        
    Raises:
        AssertionError: If the values differ by more than the tolerance
    """
    # Calculate the absolute difference
    difference = abs(actual - expected)
    
    # Assert that the difference is within tolerance
    assert difference <= tolerance, f"Values differ by {difference}, which exceeds tolerance of {tolerance}"
    
    return True

# Missing import for getcontext
from decimal import getcontext

# Export public interfaces
__all__ = [
    'setup_calculation_test_fixtures',
    'assert_decimal_equal',
    'CALCULATION_TEST_PACKAGE',
    'DECIMAL_PRECISION',
    'TEST_TOLERANCE'
]