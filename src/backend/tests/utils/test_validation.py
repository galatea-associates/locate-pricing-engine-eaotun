"""
Unit tests for the validation utility functions used in the Borrow Rate & Locate Fee Pricing Engine.
This file ensures that all validation functions correctly validate input parameters according to
the defined rules and constraints, and properly handle edge cases.
"""

import pytest
from decimal import Decimal
from pytest import parametrize

from ../../utils/validation import (
    validate_ticker,
    validate_position_value,
    validate_loan_days,
    validate_client_id,
    validate_borrow_rate,
    validate_calculation_parameters,
    raise_validation_error,
    ValidationError,
    MIN_POSITION_VALUE,
    MAX_POSITION_VALUE,
    MIN_LOAN_DAYS,
    MAX_LOAN_DAYS,
    MIN_BORROW_RATE,
    MAX_BORROW_RATE
)
from ../../core/exceptions import ValidationException


@pytest.mark.parametrize('ticker, expected', [
    ('AAPL', True),
    ('aapl', True),  # Should convert to uppercase
    ('A', True),
    ('ABCDE', True),
    ('', False),
    (None, False),
    ('ABC123', False),  # Contains digits
    ('ABCDEF', False),  # Too long
])
def test_validate_ticker(ticker, expected):
    """Tests the validate_ticker function with various inputs"""
    assert validate_ticker(ticker) == expected


@pytest.mark.parametrize('position_value, expected', [
    (Decimal('100'), True),
    (Decimal('0.01'), True),  # Minimum value
    (Decimal('1000000000'), True),  # Maximum value
    ('100', True),  # String that can be converted
    (100, True),  # Integer
    (Decimal('0'), False),  # Too small
    (Decimal('-100'), False),  # Negative
    (Decimal('1000000001'), False),  # Too large
    (None, False),
])
def test_validate_position_value(position_value, expected):
    """Tests the validate_position_value function with various inputs"""
    assert validate_position_value(position_value) == expected


@pytest.mark.parametrize('loan_days, expected', [
    (1, True),  # Minimum value
    (30, True),
    (365, True),  # Maximum value
    ('30', True),  # String that can be converted
    (0, False),  # Too small
    (-1, False),  # Negative
    (366, False),  # Too large
    (None, False),
])
def test_validate_loan_days(loan_days, expected):
    """Tests the validate_loan_days function with various inputs"""
    assert validate_loan_days(loan_days) == expected


@pytest.mark.parametrize('client_id, expected', [
    ('client123', True),
    ('CLIENT_ID', True),
    ('cl-id', True),
    ('c_id', True),
    ('ab', False),  # Too short (minimum is 3 characters)
    ('', False),  # Empty
    (None, False),
    ('invalid@id', False),  # Invalid character
    ('very_long_client_id_that_exceeds_the_maximum_allowed_length_for_testing', False),  # Too long
])
def test_validate_client_id(client_id, expected):
    """Tests the validate_client_id function with various inputs"""
    assert validate_client_id(client_id) == expected


@pytest.mark.parametrize('borrow_rate, expected', [
    (Decimal('0.0001'), True),  # Minimum value
    (Decimal('0.05'), True),
    (Decimal('1.0'), True),  # Maximum value
    ('0.05', True),  # String
    (0.05, True),  # Float
    (Decimal('0'), False),  # Too small
    (Decimal('-0.05'), False),  # Negative
    (Decimal('1.01'), False),  # Too large
    (None, False),
])
def test_validate_borrow_rate(borrow_rate, expected):
    """Tests the validate_borrow_rate function with various inputs"""
    assert validate_borrow_rate(borrow_rate) == expected


def test_validate_calculation_parameters():
    """Tests the validate_calculation_parameters function with various combinations of parameters"""
    # Test with all valid parameters
    errors = validate_calculation_parameters(
        ticker='AAPL',
        position_value=Decimal('100'),
        loan_days=30,
        client_id='client123'
    )
    assert errors == {}  # No errors expected
    
    # Test with invalid ticker
    errors = validate_calculation_parameters(
        ticker='INVALID123',
        position_value=Decimal('100'),
        loan_days=30,
        client_id='client123'
    )
    assert 'ticker' in errors  # Expect error for ticker
    
    # Test with invalid position_value
    errors = validate_calculation_parameters(
        ticker='AAPL',
        position_value=Decimal('-100'),
        loan_days=30,
        client_id='client123'
    )
    assert 'position_value' in errors  # Expect error for position_value
    
    # Test with invalid loan_days
    errors = validate_calculation_parameters(
        ticker='AAPL',
        position_value=Decimal('100'),
        loan_days=0,
        client_id='client123'
    )
    assert 'loan_days' in errors  # Expect error for loan_days
    
    # Test with invalid client_id
    errors = validate_calculation_parameters(
        ticker='AAPL',
        position_value=Decimal('100'),
        loan_days=30,
        client_id='ab'  # Too short
    )
    assert 'client_id' in errors  # Expect error for client_id
    
    # Test with all invalid parameters
    errors = validate_calculation_parameters(
        ticker='INVALID123',
        position_value=Decimal('-100'),
        loan_days=0,
        client_id='ab'
    )
    assert len(errors) == 4  # Expect errors for all parameters


def test_raise_validation_error():
    """Tests that the raise_validation_error function correctly raises a ValidationException"""
    with pytest.raises(ValidationException) as excinfo:
        raise_validation_error('ticker', 'Invalid ticker format')
    
    # Verify the exception contains the correct parameter name and detail message
    assert excinfo.value.params['parameter'] == 'ticker'
    assert excinfo.value.params['detail'] == 'Invalid ticker format'
    assert 'Invalid ticker format' in str(excinfo.value)


def test_validation_error_to_dict():
    """Tests that the ValidationError.to_dict method correctly formats error information"""
    errors = {
        'ticker': 'Invalid ticker format',
        'position_value': 'Invalid position value'
    }
    validation_error = ValidationError(errors)
    
    result = validation_error.to_dict()
    
    assert result['status'] == 'error'
    assert result['errors'] == errors