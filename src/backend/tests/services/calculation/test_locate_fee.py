"""
Unit tests for the locate fee calculation functionality in the Borrow Rate & Locate Fee Pricing Engine.

This file contains comprehensive test cases to verify the accuracy of fee calculations,
including base borrow cost, markup, transaction fees, and the total fee calculation
with various broker configurations.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

# Import the functions to test
from src.backend.services.calculation.locate_fee import (
    calculate_locate_fee,
    get_default_broker_config,
    calculate_fee_breakdown
)

# Import the calculation components
from src.backend.services.calculation.borrow_rate import calculate_borrow_rate
from src.backend.services.calculation.formulas import (
    calculate_borrow_cost,
    calculate_markup_amount,
    calculate_fee
)

# Import constants and types
from src.backend.core.constants import (
    TransactionFeeType,
    DEFAULT_MARKUP_PERCENTAGE,
    DEFAULT_TRANSACTION_FEE_FLAT
)

# Import exception classes
from src.backend.core.exceptions import CalculationException

# Import test fixtures
from src.backend.tests.fixtures.brokers import (
    standard_broker,
    premium_broker,
    flat_fee_broker,
    percentage_fee_broker
)
from src.backend.tests.fixtures.stocks import (
    easy_to_borrow_stock,
    hard_to_borrow_stock
)


def test_calculate_locate_fee_with_flat_fee(flat_fee_broker, easy_to_borrow_stock):
    """Tests the locate fee calculation with a flat transaction fee."""
    # Setup test parameters
    position_value = Decimal('100000')  # $100,000
    loan_days = 30
    borrow_rate = Decimal('0.05')  # 5% annual rate
    
    # Extract broker configuration
    markup_percentage = flat_fee_broker["markup_percentage"]
    fee_type = flat_fee_broker["transaction_fee_type"]
    fee_amount = flat_fee_broker["transaction_amount"]
    
    # Mock calculate_borrow_rate to return our test rate
    with patch('src.backend.services.calculation.borrow_rate.calculate_borrow_rate', return_value=borrow_rate):
        # Call the function under test
        result = calculate_locate_fee(
            easy_to_borrow_stock["ticker"],
            position_value,
            loan_days,
            markup_percentage,
            fee_type,
            fee_amount
        )
        
        # Calculate expected values
        expected_base_cost = calculate_borrow_cost(position_value, borrow_rate, loan_days)
        expected_markup = calculate_markup_amount(expected_base_cost, markup_percentage)
        expected_fee = calculate_fee(position_value, fee_type, fee_amount)
        expected_total = expected_base_cost + expected_markup + expected_fee
        
        # Assert that the result contains the expected total fee
        assert 'total_fee' in result
        assert result['total_fee'] == float(expected_total)
        
        # Assert that the breakdown contains the expected components
        assert 'breakdown' in result
        assert 'borrow_cost' in result['breakdown']
        assert 'markup' in result['breakdown']
        assert 'transaction_fees' in result['breakdown']
        
        # Assert that each component matches the expected value
        assert result['breakdown']['borrow_cost'] == float(expected_base_cost)
        assert result['breakdown']['markup'] == float(expected_markup)
        assert result['breakdown']['transaction_fees'] == float(expected_fee)


def test_calculate_locate_fee_with_percentage_fee(percentage_fee_broker, easy_to_borrow_stock):
    """Tests the locate fee calculation with a percentage transaction fee."""
    # Setup test parameters
    position_value = Decimal('100000')  # $100,000
    loan_days = 30
    borrow_rate = Decimal('0.05')  # 5% annual rate
    
    # Extract broker configuration
    markup_percentage = percentage_fee_broker["markup_percentage"]
    fee_type = percentage_fee_broker["transaction_fee_type"]
    fee_amount = percentage_fee_broker["transaction_amount"]
    
    # Mock calculate_borrow_rate to return our test rate
    with patch('src.backend.services.calculation.borrow_rate.calculate_borrow_rate', return_value=borrow_rate):
        # Call the function under test
        result = calculate_locate_fee(
            easy_to_borrow_stock["ticker"],
            position_value,
            loan_days,
            markup_percentage,
            fee_type,
            fee_amount
        )
        
        # Calculate expected values
        expected_base_cost = calculate_borrow_cost(position_value, borrow_rate, loan_days)
        expected_markup = calculate_markup_amount(expected_base_cost, markup_percentage)
        expected_fee = calculate_fee(position_value, fee_type, fee_amount)
        expected_total = expected_base_cost + expected_markup + expected_fee
        
        # Assert that the result contains the expected total fee
        assert 'total_fee' in result
        assert result['total_fee'] == float(expected_total)
        
        # Assert that the breakdown contains the expected components
        assert 'breakdown' in result
        assert 'borrow_cost' in result['breakdown']
        assert 'markup' in result['breakdown']
        assert 'transaction_fees' in result['breakdown']
        
        # Assert that each component matches the expected value
        assert result['breakdown']['borrow_cost'] == float(expected_base_cost)
        assert result['breakdown']['markup'] == float(expected_markup)
        assert result['breakdown']['transaction_fees'] == float(expected_fee)


def test_calculate_locate_fee_with_high_borrow_rate(standard_broker, hard_to_borrow_stock):
    """Tests the locate fee calculation with a high borrow rate (hard-to-borrow stock)."""
    # Setup test parameters
    position_value = Decimal('100000')  # $100,000
    loan_days = 30
    borrow_rate = Decimal('0.25')  # 25% annual rate
    
    # Extract broker configuration
    markup_percentage = standard_broker["markup_percentage"]
    fee_type = standard_broker["transaction_fee_type"]
    fee_amount = standard_broker["transaction_amount"]
    
    # Mock calculate_borrow_rate to return our test rate
    with patch('src.backend.services.calculation.borrow_rate.calculate_borrow_rate', return_value=borrow_rate):
        # Call the function under test
        result = calculate_locate_fee(
            hard_to_borrow_stock["ticker"],
            position_value,
            loan_days,
            markup_percentage,
            fee_type,
            fee_amount
        )
        
        # Calculate expected values
        expected_base_cost = calculate_borrow_cost(position_value, borrow_rate, loan_days)
        expected_markup = calculate_markup_amount(expected_base_cost, markup_percentage)
        expected_fee = calculate_fee(position_value, fee_type, fee_amount)
        expected_total = expected_base_cost + expected_markup + expected_fee
        
        # Assert that the result contains the expected total fee
        assert 'total_fee' in result
        assert result['total_fee'] == float(expected_total)
        
        # Assert that the breakdown contains the expected components
        assert 'breakdown' in result
        assert 'borrow_cost' in result['breakdown']
        assert 'markup' in result['breakdown']
        assert 'transaction_fees' in result['breakdown']
        
        # Assert that each component matches the expected value
        assert result['breakdown']['borrow_cost'] == float(expected_base_cost)
        assert result['breakdown']['markup'] == float(expected_markup)
        assert result['breakdown']['transaction_fees'] == float(expected_fee)


def test_calculate_locate_fee_with_different_loan_days(standard_broker, easy_to_borrow_stock):
    """Tests the locate fee calculation with different loan durations."""
    # Setup test parameters
    position_value = Decimal('100000')  # $100,000
    loan_days_values = [1, 7, 30, 60, 90]
    borrow_rate = Decimal('0.05')  # 5% annual rate
    
    # Extract broker configuration
    markup_percentage = standard_broker["markup_percentage"]
    fee_type = standard_broker["transaction_fee_type"]
    fee_amount = standard_broker["transaction_amount"]
    
    # Mock calculate_borrow_rate to return our test rate
    with patch('src.backend.services.calculation.borrow_rate.calculate_borrow_rate', return_value=borrow_rate):
        for loan_days in loan_days_values:
            # Call the function under test
            result = calculate_locate_fee(
                easy_to_borrow_stock["ticker"],
                position_value,
                loan_days,
                markup_percentage,
                fee_type,
                fee_amount
            )
            
            # Calculate expected values
            expected_base_cost = calculate_borrow_cost(position_value, borrow_rate, loan_days)
            expected_markup = calculate_markup_amount(expected_base_cost, markup_percentage)
            expected_fee = calculate_fee(position_value, fee_type, fee_amount)
            expected_total = expected_base_cost + expected_markup + expected_fee
            
            # Assert that the result contains the expected total fee
            assert 'total_fee' in result
            assert result['total_fee'] == float(expected_total)
            
            # Assert that the breakdown contains the expected components
            assert 'breakdown' in result
            assert 'borrow_cost' in result['breakdown']
            assert 'markup' in result['breakdown']
            assert 'transaction_fees' in result['breakdown']
            
            # Assert that each component matches the expected value
            assert result['breakdown']['borrow_cost'] == float(expected_base_cost)
            assert result['breakdown']['markup'] == float(expected_markup)
            assert result['breakdown']['transaction_fees'] == float(expected_fee)


def test_calculate_locate_fee_with_different_position_values(standard_broker, easy_to_borrow_stock):
    """Tests the locate fee calculation with different position values."""
    # Setup test parameters
    position_values = [Decimal('10000'), Decimal('50000'), Decimal('100000'), Decimal('500000'), Decimal('1000000')]
    loan_days = 30
    borrow_rate = Decimal('0.05')  # 5% annual rate
    
    # Extract broker configuration
    markup_percentage = standard_broker["markup_percentage"]
    fee_type = standard_broker["transaction_fee_type"]
    fee_amount = standard_broker["transaction_amount"]
    
    # Mock calculate_borrow_rate to return our test rate
    with patch('src.backend.services.calculation.borrow_rate.calculate_borrow_rate', return_value=borrow_rate):
        for position_value in position_values:
            # Call the function under test
            result = calculate_locate_fee(
                easy_to_borrow_stock["ticker"],
                position_value,
                loan_days,
                markup_percentage,
                fee_type,
                fee_amount
            )
            
            # Calculate expected values
            expected_base_cost = calculate_borrow_cost(position_value, borrow_rate, loan_days)
            expected_markup = calculate_markup_amount(expected_base_cost, markup_percentage)
            expected_fee = calculate_fee(position_value, fee_type, fee_amount)
            expected_total = expected_base_cost + expected_markup + expected_fee
            
            # Assert that the result contains the expected total fee
            assert 'total_fee' in result
            assert result['total_fee'] == float(expected_total)
            
            # Assert that the breakdown contains the expected components
            assert 'breakdown' in result
            assert 'borrow_cost' in result['breakdown']
            assert 'markup' in result['breakdown']
            assert 'transaction_fees' in result['breakdown']
            
            # Assert that each component matches the expected value
            assert result['breakdown']['borrow_cost'] == float(expected_base_cost)
            assert result['breakdown']['markup'] == float(expected_markup)
            assert result['breakdown']['transaction_fees'] == float(expected_fee)


def test_calculate_locate_fee_with_zero_position_value(standard_broker, easy_to_borrow_stock):
    """Tests the locate fee calculation with a zero position value."""
    # Setup test parameters
    position_value = Decimal('0')
    loan_days = 30
    borrow_rate = Decimal('0.05')  # 5% annual rate
    
    # Extract broker configuration
    markup_percentage = standard_broker["markup_percentage"]
    fee_type = standard_broker["transaction_fee_type"]
    fee_amount = standard_broker["transaction_amount"]
    
    # Mock calculate_borrow_rate to return our test rate
    with patch('src.backend.services.calculation.borrow_rate.calculate_borrow_rate', return_value=borrow_rate):
        # Call the function under test
        result = calculate_locate_fee(
            easy_to_borrow_stock["ticker"],
            position_value,
            loan_days,
            markup_percentage,
            fee_type,
            fee_amount
        )
        
        # Calculate expected values
        expected_base_cost = calculate_borrow_cost(position_value, borrow_rate, loan_days)
        expected_markup = calculate_markup_amount(expected_base_cost, markup_percentage)
        expected_fee = calculate_fee(position_value, fee_type, fee_amount)
        expected_total = expected_base_cost + expected_markup + expected_fee
        
        # Assert that the result contains the expected total fee
        assert 'total_fee' in result
        assert result['total_fee'] == float(expected_total)
        
        # Assert that the breakdown contains the expected components
        assert 'breakdown' in result
        assert 'borrow_cost' in result['breakdown']
        assert 'markup' in result['breakdown']
        assert 'transaction_fees' in result['breakdown']
        
        # Assert that each component matches the expected value
        assert result['breakdown']['borrow_cost'] == float(expected_base_cost)
        assert result['breakdown']['markup'] == float(expected_markup)
        assert result['breakdown']['transaction_fees'] == float(expected_fee)


def test_calculate_locate_fee_with_zero_loan_days(standard_broker, easy_to_borrow_stock):
    """Tests the locate fee calculation with zero loan days."""
    # Setup test parameters
    position_value = Decimal('100000')  # $100,000
    loan_days = 0
    borrow_rate = Decimal('0.05')  # 5% annual rate
    
    # Extract broker configuration
    markup_percentage = standard_broker["markup_percentage"]
    fee_type = standard_broker["transaction_fee_type"]
    fee_amount = standard_broker["transaction_amount"]
    
    # Mock calculate_borrow_rate to return our test rate
    with patch('src.backend.services.calculation.borrow_rate.calculate_borrow_rate', return_value=borrow_rate):
        # Call the function under test
        result = calculate_locate_fee(
            easy_to_borrow_stock["ticker"],
            position_value,
            loan_days,
            markup_percentage,
            fee_type,
            fee_amount
        )
        
        # Calculate expected values
        expected_base_cost = calculate_borrow_cost(position_value, borrow_rate, loan_days)
        expected_markup = calculate_markup_amount(expected_base_cost, markup_percentage)
        expected_fee = calculate_fee(position_value, fee_type, fee_amount)
        expected_total = expected_base_cost + expected_markup + expected_fee
        
        # Assert that the result contains the expected total fee
        assert 'total_fee' in result
        assert result['total_fee'] == float(expected_total)
        
        # Assert that the breakdown contains the expected components
        assert 'breakdown' in result
        assert 'borrow_cost' in result['breakdown']
        assert 'markup' in result['breakdown']
        assert 'transaction_fees' in result['breakdown']
        
        # Assert that each component matches the expected value
        assert result['breakdown']['borrow_cost'] == float(expected_base_cost)
        assert result['breakdown']['markup'] == float(expected_markup)
        assert result['breakdown']['transaction_fees'] == float(expected_fee)


def test_calculate_locate_fee_with_zero_borrow_rate(standard_broker, easy_to_borrow_stock):
    """Tests the locate fee calculation with a zero borrow rate."""
    # Setup test parameters
    position_value = Decimal('100000')  # $100,000
    loan_days = 30
    borrow_rate = Decimal('0.0')  # 0% annual rate
    
    # Extract broker configuration
    markup_percentage = standard_broker["markup_percentage"]
    fee_type = standard_broker["transaction_fee_type"]
    fee_amount = standard_broker["transaction_amount"]
    
    # Mock calculate_borrow_rate to return our test rate
    with patch('src.backend.services.calculation.borrow_rate.calculate_borrow_rate', return_value=borrow_rate):
        # Call the function under test
        result = calculate_locate_fee(
            easy_to_borrow_stock["ticker"],
            position_value,
            loan_days,
            markup_percentage,
            fee_type,
            fee_amount
        )
        
        # Calculate expected values
        expected_base_cost = calculate_borrow_cost(position_value, borrow_rate, loan_days)
        expected_markup = calculate_markup_amount(expected_base_cost, markup_percentage)
        expected_fee = calculate_fee(position_value, fee_type, fee_amount)
        expected_total = expected_base_cost + expected_markup + expected_fee
        
        # Assert that the result contains the expected total fee
        assert 'total_fee' in result
        assert result['total_fee'] == float(expected_total)
        
        # Assert that the breakdown contains the expected components
        assert 'breakdown' in result
        assert 'borrow_cost' in result['breakdown']
        assert 'markup' in result['breakdown']
        assert 'transaction_fees' in result['breakdown']
        
        # Assert that each component matches the expected value
        assert result['breakdown']['borrow_cost'] == float(expected_base_cost)
        assert result['breakdown']['markup'] == float(expected_markup)
        assert result['breakdown']['transaction_fees'] == float(expected_fee)


def test_calculate_locate_fee_with_default_broker_config(easy_to_borrow_stock):
    """Tests the locate fee calculation with default broker configuration."""
    # Setup test parameters
    position_value = Decimal('100000')  # $100,000
    loan_days = 30
    borrow_rate = Decimal('0.05')  # 5% annual rate
    
    # Mock calculate_borrow_rate to return our test rate
    with patch('src.backend.services.calculation.borrow_rate.calculate_borrow_rate', return_value=borrow_rate):
        # Mock get_default_broker_config to return the expected defaults
        default_config = {
            "markup_percentage": DEFAULT_MARKUP_PERCENTAGE,
            "fee_type": TransactionFeeType.FLAT,
            "fee_amount": DEFAULT_TRANSACTION_FEE_FLAT
        }
        with patch('src.backend.services.calculation.locate_fee.get_default_broker_config', return_value=default_config):
            # Call the function under test with minimal parameters (using defaults)
            result = calculate_locate_fee(
                easy_to_borrow_stock["ticker"],
                position_value,
                loan_days,
                markup_percentage=default_config["markup_percentage"],
                fee_type=default_config["fee_type"],
                fee_amount=default_config["fee_amount"]
            )
            
            # Calculate expected values
            expected_base_cost = calculate_borrow_cost(position_value, borrow_rate, loan_days)
            expected_markup = calculate_markup_amount(expected_base_cost, default_config["markup_percentage"])
            expected_fee = calculate_fee(position_value, default_config["fee_type"], default_config["fee_amount"])
            expected_total = expected_base_cost + expected_markup + expected_fee
            
            # Assert that the result contains the expected total fee
            assert 'total_fee' in result
            assert result['total_fee'] == float(expected_total)
            
            # Assert that the breakdown contains the expected components
            assert 'breakdown' in result
            assert 'borrow_cost' in result['breakdown']
            assert 'markup' in result['breakdown']
            assert 'transaction_fees' in result['breakdown']
            
            # Assert that each component matches the expected value
            assert result['breakdown']['borrow_cost'] == float(expected_base_cost)
            assert result['breakdown']['markup'] == float(expected_markup)
            assert result['breakdown']['transaction_fees'] == float(expected_fee)


def test_get_default_broker_config():
    """Tests the get_default_broker_config function returns the expected default values."""
    # Call the function under test
    default_config = get_default_broker_config()
    
    # Assert that the config contains the expected keys
    assert "markup_percentage" in default_config
    assert "fee_type" in default_config
    assert "fee_amount" in default_config
    
    # Assert that the values match the expected defaults
    assert default_config["markup_percentage"] == DEFAULT_MARKUP_PERCENTAGE
    assert default_config["fee_type"] == TransactionFeeType.FLAT
    assert default_config["fee_amount"] == DEFAULT_TRANSACTION_FEE_FLAT


def test_calculate_fee_breakdown(standard_broker, easy_to_borrow_stock):
    """Tests the calculate_fee_breakdown function provides a detailed breakdown."""
    # Setup test parameters
    ticker = easy_to_borrow_stock["ticker"]
    position_value = Decimal('100000')  # $100,000
    loan_days = 30
    borrow_rate = Decimal('0.05')  # 5% annual rate
    
    # Extract broker configuration
    markup_percentage = standard_broker["markup_percentage"]
    fee_type = standard_broker["transaction_fee_type"]
    fee_amount = standard_broker["transaction_amount"]
    
    # Call the function under test
    breakdown = calculate_fee_breakdown(
        ticker,
        position_value,
        loan_days,
        borrow_rate,
        markup_percentage,
        fee_type,
        fee_amount
    )
    
    # Calculate expected values
    expected_base_cost = calculate_borrow_cost(position_value, borrow_rate, loan_days)
    expected_markup = calculate_markup_amount(expected_base_cost, markup_percentage)
    expected_fee = calculate_fee(position_value, fee_type, fee_amount)
    expected_total = expected_base_cost + expected_markup + expected_fee
    
    # Assert that the breakdown contains all expected keys
    assert 'inputs' in breakdown
    assert 'calculations' in breakdown
    assert 'totals' in breakdown
    
    # Check inputs
    assert breakdown['inputs']['ticker'] == ticker
    assert breakdown['inputs']['position_value'] == float(position_value)
    assert breakdown['inputs']['loan_days'] == loan_days
    assert breakdown['inputs']['borrow_rate_annual'] == float(borrow_rate)
    
    # Check totals
    assert breakdown['totals']['base_borrow_cost'] == float(expected_base_cost)
    assert breakdown['totals']['markup'] == float(expected_markup)
    assert breakdown['totals']['transaction_fee'] == float(expected_fee)
    assert breakdown['totals']['total_fee'] == float(expected_total)


def test_calculate_locate_fee_with_cache(standard_broker, easy_to_borrow_stock):
    """Tests the locate fee calculation with caching enabled."""
    # Setup test parameters
    position_value = Decimal('100000')  # $100,000
    loan_days = 30
    borrow_rate = Decimal('0.05')  # 5% annual rate
    
    # Extract broker configuration
    markup_percentage = standard_broker["markup_percentage"]
    fee_type = standard_broker["transaction_fee_type"]
    fee_amount = standard_broker["transaction_amount"]
    
    # Create mock for get_cached_locate_fee
    mock_get_cache = MagicMock(side_effect=[None, {'cached': True}])
    # Create mock for cache_locate_fee
    mock_cache = MagicMock(return_value=True)
    
    # Mock the functions
    with patch('src.backend.services.calculation.borrow_rate.calculate_borrow_rate', return_value=borrow_rate):
        with patch('src.backend.services.calculation.locate_fee.get_cached_locate_fee', mock_get_cache):
            with patch('src.backend.services.calculation.locate_fee.cache_locate_fee', mock_cache):
                # First call should calculate and cache
                result1 = calculate_locate_fee(
                    easy_to_borrow_stock["ticker"],
                    position_value,
                    loan_days,
                    markup_percentage,
                    fee_type,
                    fee_amount,
                    use_cache=True
                )
                
                # Second call should use cached result
                result2 = calculate_locate_fee(
                    easy_to_borrow_stock["ticker"],
                    position_value,
                    loan_days,
                    markup_percentage,
                    fee_type,
                    fee_amount,
                    use_cache=True
                )
                
    # Assert get_cached_locate_fee was called with correct parameters
    mock_get_cache.assert_called_with(
        easy_to_borrow_stock["ticker"],
        position_value,
        loan_days,
        markup_percentage,
        fee_type,
        fee_amount
    )
    
    # Assert cache_locate_fee was called with correct parameters
    mock_cache.assert_called_once()
    
    # Assert that second result is the cached result
    assert result2 == {'cached': True}


def test_calculate_locate_fee_without_cache(standard_broker, easy_to_borrow_stock):
    """Tests the locate fee calculation with caching disabled."""
    # Setup test parameters
    position_value = Decimal('100000')  # $100,000
    loan_days = 30
    borrow_rate = Decimal('0.05')  # 5% annual rate
    
    # Extract broker configuration
    markup_percentage = standard_broker["markup_percentage"]
    fee_type = standard_broker["transaction_fee_type"]
    fee_amount = standard_broker["transaction_amount"]
    
    # Create mocks
    mock_get_cache = MagicMock()
    mock_cache = MagicMock()
    
    # Mock the functions
    with patch('src.backend.services.calculation.borrow_rate.calculate_borrow_rate', return_value=borrow_rate):
        with patch('src.backend.services.calculation.locate_fee.get_cached_locate_fee', mock_get_cache):
            with patch('src.backend.services.calculation.locate_fee.cache_locate_fee', mock_cache):
                # Call with use_cache=False
                result = calculate_locate_fee(
                    easy_to_borrow_stock["ticker"],
                    position_value,
                    loan_days,
                    markup_percentage,
                    fee_type,
                    fee_amount,
                    use_cache=False
                )
                
    # Assert that cache functions were not called
    mock_get_cache.assert_not_called()
    mock_cache.assert_not_called()


def test_calculate_locate_fee_error_handling(standard_broker, easy_to_borrow_stock):
    """Tests error handling in the locate fee calculation."""
    # Setup test parameters
    position_value = Decimal('100000')  # $100,000
    loan_days = 30
    
    # Extract broker configuration
    markup_percentage = standard_broker["markup_percentage"]
    fee_type = standard_broker["transaction_fee_type"]
    fee_amount = standard_broker["transaction_amount"]
    
    # Mock calculate_borrow_rate to raise an exception
    with patch('src.backend.services.calculation.borrow_rate.calculate_borrow_rate', 
              side_effect=CalculationException("Mock error", {})):
        # Check that the exception is propagated
        with pytest.raises(CalculationException):
            calculate_locate_fee(
                easy_to_borrow_stock["ticker"],
                position_value,
                loan_days,
                markup_percentage,
                fee_type,
                fee_amount
            )