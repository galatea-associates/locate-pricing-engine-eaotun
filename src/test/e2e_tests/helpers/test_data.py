"""
Helper module for managing test data in end-to-end tests of the Borrow Rate & Locate Fee Pricing Engine.
Provides utilities for generating, manipulating, and validating test data for various test scenarios,
as well as calculating expected results for test assertions.
"""

import logging
from decimal import Decimal
from copy import deepcopy
from typing import Dict, List, Optional, Union, Any

import pytest

from ..config.settings import get_test_settings, TestEnvironment
from ..helpers.api_client import APIClient
from src.backend.core.constants import (
    BorrowStatus, 
    TransactionFeeType, 
    DAYS_IN_YEAR, 
    DEFAULT_VOLATILITY_FACTOR, 
    DEFAULT_EVENT_RISK_FACTOR
)

# Configure logger
logger = logging.getLogger(__name__)

# Test data constants
TEST_STOCKS = [
    {'ticker': 'AAPL', 'borrow_status': BorrowStatus.EASY, 'lender_api_id': 'SEC001', 'min_borrow_rate': Decimal('0.01')},
    {'ticker': 'GME', 'borrow_status': BorrowStatus.HARD, 'lender_api_id': 'SEC002', 'min_borrow_rate': Decimal('0.15')},
    {'ticker': 'MSFT', 'borrow_status': BorrowStatus.EASY, 'lender_api_id': 'SEC003', 'min_borrow_rate': Decimal('0.01')},
    {'ticker': 'TSLA', 'borrow_status': BorrowStatus.MEDIUM, 'lender_api_id': 'SEC004', 'min_borrow_rate': Decimal('0.05')},
    {'ticker': 'AMC', 'borrow_status': BorrowStatus.HARD, 'lender_api_id': 'SEC005', 'min_borrow_rate': Decimal('0.20')}
]

TEST_BROKERS = [
    {'client_id': 'broker_standard', 'markup_percentage': Decimal('0.05'), 'transaction_fee_type': TransactionFeeType.FLAT, 'transaction_amount': Decimal('10.00'), 'active': True},
    {'client_id': 'broker_premium', 'markup_percentage': Decimal('0.03'), 'transaction_fee_type': TransactionFeeType.PERCENTAGE, 'transaction_amount': Decimal('0.01'), 'active': True},
    {'client_id': 'broker_inactive', 'markup_percentage': Decimal('0.07'), 'transaction_fee_type': TransactionFeeType.FLAT, 'transaction_amount': Decimal('15.00'), 'active': False}
]

TEST_VOLATILITY = [
    {'stock_id': 'AAPL', 'vol_index': Decimal('15.5'), 'event_risk_factor': 1},
    {'stock_id': 'GME', 'vol_index': Decimal('45.0'), 'event_risk_factor': 8},
    {'stock_id': 'MSFT', 'vol_index': Decimal('12.0'), 'event_risk_factor': 0},
    {'stock_id': 'TSLA', 'vol_index': Decimal('30.0'), 'event_risk_factor': 5},
    {'stock_id': 'AMC', 'vol_index': Decimal('50.0'), 'event_risk_factor': 7}
]

TEST_CALCULATION_SCENARIOS = [
    {'name': 'normal_market', 'ticker': 'AAPL', 'position_value': Decimal('100000'), 'loan_days': 30, 'client_id': 'broker_standard'},
    {'name': 'high_volatility', 'ticker': 'GME', 'position_value': Decimal('50000'), 'loan_days': 15, 'client_id': 'broker_premium'},
    {'name': 'corporate_event', 'ticker': 'TSLA', 'position_value': Decimal('75000'), 'loan_days': 7, 'client_id': 'broker_standard'},
    {'name': 'hard_to_borrow', 'ticker': 'AMC', 'position_value': Decimal('25000'), 'loan_days': 30, 'client_id': 'broker_premium'},
    {'name': 'long_term_loan', 'ticker': 'MSFT', 'position_value': Decimal('200000'), 'loan_days': 90, 'client_id': 'broker_standard'}
]

DEFAULT_TOLERANCE = Decimal('0.0001')


def get_test_scenario(scenario_name: str) -> dict:
    """
    Retrieves a specific test scenario by name
    
    Args:
        scenario_name: Name of the scenario to retrieve
        
    Returns:
        Test scenario data dictionary
        
    Raises:
        ValueError: If scenario not found
    """
    for scenario in TEST_CALCULATION_SCENARIOS:
        if scenario['name'] == scenario_name:
            return scenario
    
    raise ValueError(f"Test scenario '{scenario_name}' not found")


def get_stock_data(ticker: str) -> dict:
    """
    Retrieves stock data for a specific ticker
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Stock data dictionary
        
    Raises:
        ValueError: If stock not found
    """
    for stock in TEST_STOCKS:
        if stock['ticker'] == ticker:
            return stock
    
    raise ValueError(f"Stock data for ticker '{ticker}' not found")


def get_broker_data(client_id: str) -> dict:
    """
    Retrieves broker data for a specific client ID
    
    Args:
        client_id: Client identifier
        
    Returns:
        Broker data dictionary
        
    Raises:
        ValueError: If broker not found
    """
    for broker in TEST_BROKERS:
        if broker['client_id'] == client_id:
            return broker
    
    raise ValueError(f"Broker data for client ID '{client_id}' not found")


def get_volatility_data(ticker: str) -> dict:
    """
    Retrieves volatility data for a specific stock
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Volatility data dictionary
        
    Raises:
        ValueError: If volatility data not found
    """
    for vol_data in TEST_VOLATILITY:
        if vol_data['stock_id'] == ticker:
            return vol_data
    
    raise ValueError(f"Volatility data for ticker '{ticker}' not found")


def calculate_expected_borrow_rate(stock_data: dict, volatility_data: dict) -> Decimal:
    """
    Calculates the expected borrow rate for a test scenario
    
    Args:
        stock_data: Stock data dictionary
        volatility_data: Volatility data dictionary
        
    Returns:
        Expected borrow rate
    """
    # Get base rate from stock data
    base_rate = stock_data['min_borrow_rate']
    
    # Get volatility and event risk factors
    vol_index = volatility_data['vol_index']
    event_risk_factor = volatility_data['event_risk_factor']
    
    # Apply volatility adjustment
    volatility_adjustment = vol_index * DEFAULT_VOLATILITY_FACTOR
    
    # Apply event risk adjustment
    event_risk_adjustment = Decimal(event_risk_factor) / Decimal('10') * DEFAULT_EVENT_RISK_FACTOR
    
    # Calculate final borrow rate
    borrow_rate = base_rate * (Decimal('1') + volatility_adjustment) + event_risk_adjustment
    
    logger.debug(f"Calculated borrow rate: {borrow_rate} "
                f"(base: {base_rate}, vol_adj: {volatility_adjustment}, "
                f"event_adj: {event_risk_adjustment})")
    
    return borrow_rate


def calculate_expected_fee(scenario: dict) -> dict:
    """
    Calculates the expected fee for a test scenario
    
    Args:
        scenario: Test scenario dictionary
        
    Returns:
        Expected fee calculation result
    """
    # Get stock, broker, and volatility data
    stock_data = get_stock_data(scenario['ticker'])
    broker_data = get_broker_data(scenario['client_id'])
    volatility_data = get_volatility_data(scenario['ticker'])
    
    # Calculate expected borrow rate
    borrow_rate = calculate_expected_borrow_rate(stock_data, volatility_data)
    
    # Extract scenario parameters
    position_value = scenario['position_value']
    loan_days = scenario['loan_days']
    
    # Calculate base borrow cost
    base_borrow_cost = position_value * borrow_rate * (Decimal(loan_days) / DAYS_IN_YEAR)
    
    # Calculate markup
    markup = base_borrow_cost * broker_data['markup_percentage']
    
    # Calculate transaction fees
    if broker_data['transaction_fee_type'] == TransactionFeeType.FLAT:
        transaction_fees = broker_data['transaction_amount']
    else:  # PERCENTAGE
        transaction_fees = position_value * broker_data['transaction_amount']
    
    # Calculate total fee
    total_fee = base_borrow_cost + markup + transaction_fees
    
    # Prepare result dictionary
    result = {
        'status': 'success',
        'total_fee': total_fee,
        'breakdown': {
            'borrow_cost': base_borrow_cost,
            'markup': markup,
            'transaction_fees': transaction_fees
        },
        'borrow_rate_used': borrow_rate
    }
    
    logger.debug(f"Calculated expected fee: {result}")
    
    return result


def generate_test_data(environment: TestEnvironment, custom_data: Optional[Dict] = None) -> Dict:
    """
    Generates test data for a specific environment
    
    Args:
        environment: Test environment
        custom_data: Optional custom data to merge with default test data
        
    Returns:
        Generated test data dictionary
    """
    # Initialize with default test data
    test_data = {
        'stocks': deepcopy(TEST_STOCKS),
        'brokers': deepcopy(TEST_BROKERS),
        'volatility': deepcopy(TEST_VOLATILITY),
        'scenarios': deepcopy(TEST_CALCULATION_SCENARIOS)
    }
    
    # Merge with custom data if provided
    if custom_data:
        for key, value in custom_data.items():
            if key in test_data:
                if isinstance(value, list):
                    test_data[key].extend(value)
                elif isinstance(value, dict):
                    test_data[key].update(value)
                else:
                    test_data[key] = value
            else:
                test_data[key] = value
    
    # Adjust test data based on environment
    if environment == TestEnvironment.LOCAL:
        # No changes for local environment
        pass
    elif environment == TestEnvironment.DEVELOPMENT:
        # Adjust volatility for development environment
        for vol in test_data['volatility']:
            vol['vol_index'] = vol['vol_index'] * Decimal('0.9')  # Reduce volatility by 10%
    elif environment == TestEnvironment.STAGING:
        # Adjust borrow rates for staging environment
        for stock in test_data['stocks']:
            if stock['borrow_status'] == BorrowStatus.HARD:
                stock['min_borrow_rate'] = stock['min_borrow_rate'] * Decimal('1.1')  # Increase hard-to-borrow rates by 10%
    elif environment == TestEnvironment.PRODUCTION:
        # Use more conservative values for production testing
        for stock in test_data['stocks']:
            stock['min_borrow_rate'] = stock['min_borrow_rate'] * Decimal('0.9')  # Reduce all rates by 10%
        for broker in test_data['brokers']:
            broker['markup_percentage'] = broker['markup_percentage'] * Decimal('0.9')  # Reduce markups by 10%
    
    logger.info(f"Generated test data for {environment.name} environment")
    return test_data


def is_decimal_equal(value1: Union[Decimal, float, int], 
                     value2: Union[Decimal, float, int], 
                     tolerance: Optional[Decimal] = None) -> bool:
    """
    Compares two decimal values within a specified tolerance
    
    Args:
        value1: First value to compare
        value2: Second value to compare
        tolerance: Maximum allowed difference (default: DEFAULT_TOLERANCE)
        
    Returns:
        True if values are equal within tolerance, False otherwise
    """
    if tolerance is None:
        tolerance = DEFAULT_TOLERANCE
    
    # Convert to Decimal if needed
    if not isinstance(value1, Decimal):
        value1 = Decimal(str(value1))
    if not isinstance(value2, Decimal):
        value2 = Decimal(str(value2))
    
    # Calculate absolute difference
    diff = abs(value1 - value2)
    
    return diff <= tolerance


def compare_calculation_results(actual: dict, expected: dict, tolerance: Optional[Decimal] = None) -> dict:
    """
    Compares two calculation results and returns differences
    
    Args:
        actual: Actual calculation result
        expected: Expected calculation result
        tolerance: Maximum allowed difference (default: DEFAULT_TOLERANCE)
        
    Returns:
        Dictionary of differences between actual and expected
    """
    if tolerance is None:
        tolerance = DEFAULT_TOLERANCE
    
    differences = {}
    
    # Check status
    if actual.get('status') != expected.get('status'):
        differences['status'] = {
            'actual': actual.get('status'),
            'expected': expected.get('status')
        }
    
    # Check total_fee
    if not is_decimal_equal(actual.get('total_fee', 0), expected.get('total_fee', 0), tolerance):
        differences['total_fee'] = {
            'actual': actual.get('total_fee'),
            'expected': expected.get('total_fee'),
            'difference': abs(Decimal(str(actual.get('total_fee', 0))) - Decimal(str(expected.get('total_fee', 0))))
        }
    
    # Check borrow_rate_used
    if not is_decimal_equal(actual.get('borrow_rate_used', 0), expected.get('borrow_rate_used', 0), tolerance):
        differences['borrow_rate_used'] = {
            'actual': actual.get('borrow_rate_used'),
            'expected': expected.get('borrow_rate_used'),
            'difference': abs(Decimal(str(actual.get('borrow_rate_used', 0))) - Decimal(str(expected.get('borrow_rate_used', 0))))
        }
    
    # Check breakdown
    actual_breakdown = actual.get('breakdown', {})
    expected_breakdown = expected.get('breakdown', {})
    
    breakdown_diff = {}
    for key in set(list(actual_breakdown.keys()) + list(expected_breakdown.keys())):
        actual_value = actual_breakdown.get(key, 0)
        expected_value = expected_breakdown.get(key, 0)
        
        if not is_decimal_equal(actual_value, expected_value, tolerance):
            breakdown_diff[key] = {
                'actual': actual_value,
                'expected': expected_value,
                'difference': abs(Decimal(str(actual_value)) - Decimal(str(expected_value)))
            }
    
    if breakdown_diff:
        differences['breakdown'] = breakdown_diff
    
    return differences


class TestDataManager:
    """
    Manages test data lifecycle for end-to-end tests
    """
    
    def __init__(self, environment: TestEnvironment, custom_data: Optional[Dict] = None, 
                 tolerance: Optional[Decimal] = None):
        """
        Initializes the TestDataManager with environment and optional custom data
        
        Args:
            environment: Test environment
            custom_data: Optional custom data to merge with default test data
            tolerance: Tolerance for decimal comparisons (default: DEFAULT_TOLERANCE)
        """
        self._environment = environment
        self._tolerance = tolerance or DEFAULT_TOLERANCE
        self._test_data = generate_test_data(environment, custom_data)
        self._api_client = APIClient()
    
    def get_scenario(self, scenario_name: str) -> dict:
        """
        Gets a test scenario by name
        
        Args:
            scenario_name: Name of the scenario to retrieve
            
        Returns:
            Test scenario data
        """
        scenario = get_test_scenario(scenario_name)
        return deepcopy(scenario)
    
    def get_stock(self, ticker: str) -> dict:
        """
        Gets stock data by ticker
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Stock data
        """
        stock = get_stock_data(ticker)
        return deepcopy(stock)
    
    def get_broker(self, client_id: str) -> dict:
        """
        Gets broker data by client ID
        
        Args:
            client_id: Client identifier
            
        Returns:
            Broker data
        """
        broker = get_broker_data(client_id)
        return deepcopy(broker)
    
    def get_volatility(self, ticker: str) -> dict:
        """
        Gets volatility data by ticker
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Volatility data
        """
        volatility = get_volatility_data(ticker)
        return deepcopy(volatility)
    
    def calculate_expected_result(self, scenario: Union[str, dict]) -> dict:
        """
        Calculates expected result for a test scenario
        
        Args:
            scenario: Test scenario name or dictionary
            
        Returns:
            Expected calculation result
        """
        if isinstance(scenario, str):
            scenario = self.get_scenario(scenario)
        
        return calculate_expected_fee(scenario)
    
    def compare_results(self, actual: dict, expected: dict) -> dict:
        """
        Compares actual and expected calculation results
        
        Args:
            actual: Actual calculation result
            expected: Expected calculation result
            
        Returns:
            Differences between actual and expected results
        """
        return compare_calculation_results(actual, expected, self._tolerance)
    
    def run_calculation_test(self, scenario: Union[str, dict]) -> tuple:
        """
        Runs a calculation test and returns results
        
        Args:
            scenario: Test scenario name or dictionary
            
        Returns:
            Tuple of (actual_result, expected_result, differences)
        """
        if isinstance(scenario, str):
            scenario = self.get_scenario(scenario)
        
        expected_result = self.calculate_expected_result(scenario)
        
        # Call the API to get actual result
        actual_result = self._api_client.calculate_locate_fee(
            ticker=scenario['ticker'],
            position_value=scenario['position_value'],
            loan_days=scenario['loan_days'],
            client_id=scenario['client_id']
        )
        
        # Compare results
        differences = self.compare_results(actual_result, expected_result)
        
        return actual_result, expected_result, differences
    
    def assert_calculation(self, scenario: Union[str, dict]) -> None:
        """
        Asserts that a calculation matches expected result
        
        Args:
            scenario: Test scenario name or dictionary
            
        Raises:
            AssertionError: If calculation does not match expected result
        """
        actual, expected, differences = self.run_calculation_test(scenario)
        
        if differences:
            scenario_name = scenario if isinstance(scenario, str) else scenario.get('name', 'unnamed')
            error_msg = f"Calculation for scenario '{scenario_name}' does not match expected result:\n"
            error_msg += f"Differences: {differences}\n"
            error_msg += f"Actual: {actual}\n"
            error_msg += f"Expected: {expected}"
            raise AssertionError(error_msg)