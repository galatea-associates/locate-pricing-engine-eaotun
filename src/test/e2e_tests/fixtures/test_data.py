"""
Provides pytest fixtures for test data used in end-to-end tests of the Borrow Rate & Locate Fee Pricing Engine.
This module defines test data for stocks, brokers, volatility metrics, and calculation scenarios,
as well as functions to set up and clean up test data in different test environments.
"""

import logging
import pytest
from decimal import Decimal
from typing import Dict, List, Optional, Union, Any

import sqlalchemy
from sqlalchemy import create_engine, MetaData, Table, Column, select, insert, delete

from ..config.settings import get_test_settings, TestEnvironment
from ..helpers.api_client import APIClient
from src.backend.core.constants import BorrowStatus, TransactionFeeType

# Configure logger
logger = logging.getLogger(__name__)

# Test data for stocks
TEST_STOCKS = [
    {
        'ticker': 'AAPL', 
        'borrow_status': BorrowStatus.EASY, 
        'lender_api_id': 'SEC001', 
        'min_borrow_rate': Decimal('0.01')
    },
    {
        'ticker': 'GME', 
        'borrow_status': BorrowStatus.HARD, 
        'lender_api_id': 'SEC002', 
        'min_borrow_rate': Decimal('0.15')
    },
    {
        'ticker': 'MSFT', 
        'borrow_status': BorrowStatus.EASY, 
        'lender_api_id': 'SEC003', 
        'min_borrow_rate': Decimal('0.01')
    },
    {
        'ticker': 'TSLA', 
        'borrow_status': BorrowStatus.MEDIUM, 
        'lender_api_id': 'SEC004', 
        'min_borrow_rate': Decimal('0.05')
    },
    {
        'ticker': 'AMC', 
        'borrow_status': BorrowStatus.HARD, 
        'lender_api_id': 'SEC005', 
        'min_borrow_rate': Decimal('0.20')
    }
]

# Test data for brokers
TEST_BROKERS = [
    {
        'client_id': 'broker_standard', 
        'markup_percentage': Decimal('0.05'), 
        'transaction_fee_type': TransactionFeeType.FLAT, 
        'transaction_amount': Decimal('10.00'),
        'active': True
    },
    {
        'client_id': 'broker_premium', 
        'markup_percentage': Decimal('0.03'), 
        'transaction_fee_type': TransactionFeeType.PERCENTAGE, 
        'transaction_amount': Decimal('0.01'),
        'active': True
    },
    {
        'client_id': 'broker_inactive', 
        'markup_percentage': Decimal('0.07'), 
        'transaction_fee_type': TransactionFeeType.FLAT, 
        'transaction_amount': Decimal('15.00'),
        'active': False
    }
]

# Test data for volatility metrics
TEST_VOLATILITY = [
    {
        'stock_id': 'AAPL', 
        'vol_index': Decimal('15.5'), 
        'event_risk_factor': 1
    },
    {
        'stock_id': 'GME', 
        'vol_index': Decimal('45.0'), 
        'event_risk_factor': 8
    },
    {
        'stock_id': 'MSFT', 
        'vol_index': Decimal('12.0'), 
        'event_risk_factor': 0
    },
    {
        'stock_id': 'TSLA', 
        'vol_index': Decimal('30.0'), 
        'event_risk_factor': 5
    },
    {
        'stock_id': 'AMC', 
        'vol_index': Decimal('50.0'), 
        'event_risk_factor': 7
    }
]

# Test calculation scenarios
TEST_CALCULATION_SCENARIOS = [
    {
        'name': 'normal_market',
        'ticker': 'AAPL',
        'position_value': Decimal('100000'),
        'loan_days': 30,
        'client_id': 'broker_standard'
    },
    {
        'name': 'high_volatility',
        'ticker': 'GME',
        'position_value': Decimal('50000'),
        'loan_days': 15,
        'client_id': 'broker_premium'
    },
    {
        'name': 'corporate_event',
        'ticker': 'TSLA',
        'position_value': Decimal('75000'),
        'loan_days': 7,
        'client_id': 'broker_standard'
    },
    {
        'name': 'hard_to_borrow',
        'ticker': 'AMC',
        'position_value': Decimal('25000'),
        'loan_days': 30,
        'client_id': 'broker_premium'
    },
    {
        'name': 'long_term_loan',
        'ticker': 'MSFT',
        'position_value': Decimal('200000'),
        'loan_days': 90,
        'client_id': 'broker_standard'
    }
]


def setup_test_data(env_config: Dict) -> Dict:
    """
    Sets up test data in the target environment based on environment configuration.
    
    Args:
        env_config: Environment configuration dictionary
        
    Returns:
        Dictionary containing references to created test data
    """
    # Initialize API client
    api_client = APIClient(settings=env_config.get('settings'))
    
    # Determine environment type
    env_type = env_config.get('environment', TestEnvironment.LOCAL)
    
    test_data_refs = {
        'stocks': [],
        'brokers': [],
        'volatility': []
    }
    
    logger.info(f"Setting up test data in {env_type.value} environment")
    
    try:
        if env_type == TestEnvironment.LOCAL:
            # For local environment, use direct database access
            db_url = env_config.get('db_url', 'postgresql://postgres:postgres@localhost:5432/borrow_rate_test')
            engine = create_engine(db_url)
            metadata = MetaData()
            
            # Define tables
            stocks_table = Table('stocks', metadata, autoload_with=engine)
            brokers_table = Table('brokers', metadata, autoload_with=engine)
            volatility_table = Table('volatility', metadata, autoload_with=engine)
            
            # Create test data
            with engine.connect() as conn:
                # Add stocks
                for stock in TEST_STOCKS:
                    result = conn.execute(insert(stocks_table).values(**stock))
                    test_data_refs['stocks'].append(stock['ticker'])
                
                # Add brokers
                for broker in TEST_BROKERS:
                    result = conn.execute(insert(brokers_table).values(**broker))
                    test_data_refs['brokers'].append(broker['client_id'])
                
                # Add volatility data
                for vol in TEST_VOLATILITY:
                    result = conn.execute(insert(volatility_table).values(**vol))
                    test_data_refs['volatility'].append(vol['stock_id'])
                
                conn.commit()
        else:
            # For remote environments, use API endpoints to create test data
            # Note: This assumes the existence of admin API endpoints for test data setup
            # In a real implementation, you would call those endpoints
            
            logger.warning(f"Test data setup for environment {env_type.value} is not fully implemented")
            
            # Mock implementation - in a real system you would use administrative API endpoints
            # to create test data in the target environment
            for stock in TEST_STOCKS:
                # Example: api_client.create_stock(stock)
                test_data_refs['stocks'].append(stock['ticker'])
            
            for broker in TEST_BROKERS:
                # Example: api_client.create_broker(broker)
                test_data_refs['brokers'].append(broker['client_id'])
            
            for vol in TEST_VOLATILITY:
                # Example: api_client.create_volatility(vol)
                test_data_refs['volatility'].append(vol['stock_id'])
        
        logger.info(f"Successfully set up test data: {len(test_data_refs['stocks'])} stocks, "
                   f"{len(test_data_refs['brokers'])} brokers, {len(test_data_refs['volatility'])} volatility records")
        
        return test_data_refs
        
    except Exception as e:
        logger.error(f"Error setting up test data: {str(e)}")
        # Clean up any partially created data
        cleanup_test_data(env_config, test_data_refs)
        raise


def cleanup_test_data(env_config: Dict, test_data_refs: Dict) -> bool:
    """
    Cleans up test data from the target environment.
    
    Args:
        env_config: Environment configuration dictionary
        test_data_refs: References to test data that was created
        
    Returns:
        True if cleanup was successful, False otherwise
    """
    # Initialize API client
    api_client = APIClient(settings=env_config.get('settings'))
    
    # Determine environment type
    env_type = env_config.get('environment', TestEnvironment.LOCAL)
    
    logger.info(f"Cleaning up test data from {env_type.value} environment")
    
    try:
        if env_type == TestEnvironment.LOCAL:
            # For local environment, use direct database access
            db_url = env_config.get('db_url', 'postgresql://postgres:postgres@localhost:5432/borrow_rate_test')
            engine = create_engine(db_url)
            metadata = MetaData()
            
            # Define tables
            stocks_table = Table('stocks', metadata, autoload_with=engine)
            brokers_table = Table('brokers', metadata, autoload_with=engine)
            volatility_table = Table('volatility', metadata, autoload_with=engine)
            
            # Delete test data
            with engine.connect() as conn:
                # Delete volatility data first (foreign key constraints)
                for stock_id in test_data_refs.get('volatility', []):
                    conn.execute(delete(volatility_table).where(volatility_table.c.stock_id == stock_id))
                
                # Delete brokers
                for client_id in test_data_refs.get('brokers', []):
                    conn.execute(delete(brokers_table).where(brokers_table.c.client_id == client_id))
                
                # Delete stocks
                for ticker in test_data_refs.get('stocks', []):
                    conn.execute(delete(stocks_table).where(stocks_table.c.ticker == ticker))
                
                conn.commit()
        else:
            # For remote environments, use API endpoints to delete test data if available
            logger.warning(f"Test data cleanup for environment {env_type.value} is not fully implemented")
            
            # Mock implementation - in a real system you would use administrative API endpoints
            # to delete test data in the target environment
            for stock_id in test_data_refs.get('volatility', []):
                # Example: api_client.delete_volatility(stock_id)
                pass
            
            for client_id in test_data_refs.get('brokers', []):
                # Example: api_client.delete_broker(client_id)
                pass
            
            for ticker in test_data_refs.get('stocks', []):
                # Example: api_client.delete_stock(ticker)
                pass
        
        logger.info(f"Successfully cleaned up test data")
        return True
        
    except Exception as e:
        logger.error(f"Error cleaning up test data: {str(e)}")
        return False


def get_test_scenario(scenario_name: str) -> Dict:
    """
    Retrieves a specific test scenario by name.
    
    Args:
        scenario_name: Name of the scenario to retrieve
        
    Returns:
        Test scenario data dictionary
        
    Raises:
        ValueError: If scenario with the given name is not found
    """
    for scenario in TEST_CALCULATION_SCENARIOS:
        if scenario['name'] == scenario_name:
            return scenario
    
    raise ValueError(f"Test scenario '{scenario_name}' not found")


def get_stock_data(ticker: str) -> Dict:
    """
    Retrieves stock data for a specific ticker.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Stock data dictionary
        
    Raises:
        ValueError: If stock with the given ticker is not found
    """
    for stock in TEST_STOCKS:
        if stock['ticker'] == ticker:
            return stock
    
    raise ValueError(f"Test stock with ticker '{ticker}' not found")


def get_broker_data(client_id: str) -> Dict:
    """
    Retrieves broker data for a specific client ID.
    
    Args:
        client_id: Broker client ID
        
    Returns:
        Broker data dictionary
        
    Raises:
        ValueError: If broker with the given client ID is not found
    """
    for broker in TEST_BROKERS:
        if broker['client_id'] == client_id:
            return broker
    
    raise ValueError(f"Test broker with client_id '{client_id}' not found")


def get_volatility_data(ticker: str) -> Dict:
    """
    Retrieves volatility data for a specific stock.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Volatility data dictionary
        
    Raises:
        ValueError: If volatility data for the given ticker is not found
    """
    for vol in TEST_VOLATILITY:
        if vol['stock_id'] == ticker:
            return vol
    
    raise ValueError(f"Test volatility data for ticker '{ticker}' not found")


def calculate_expected_borrow_rate(stock_data: Dict, volatility_data: Dict) -> Decimal:
    """
    Calculates the expected borrow rate for a test scenario.
    
    Args:
        stock_data: Stock data dictionary
        volatility_data: Volatility data dictionary
        
    Returns:
        Expected borrow rate
    """
    # Extract values
    base_rate = stock_data['min_borrow_rate']
    vol_index = volatility_data['vol_index']
    event_risk_factor = volatility_data['event_risk_factor']
    
    # Apply volatility adjustment
    # Formula: base_rate * (1 + (vol_index * 0.01))
    volatility_adjustment = vol_index * Decimal('0.01')
    
    # Apply event risk adjustment
    # Formula: event_risk_factor / 10 * 0.05
    event_risk_adjustment = Decimal(event_risk_factor) / Decimal('10') * Decimal('0.05')
    
    # Calculate final rate
    final_rate = base_rate * (Decimal('1') + volatility_adjustment) + event_risk_adjustment
    
    return final_rate


def calculate_expected_fee(scenario: Dict) -> Dict:
    """
    Calculates the expected fee for a test scenario.
    
    Args:
        scenario: Test scenario dictionary
        
    Returns:
        Expected fee calculation result
    """
    # Get required data
    ticker = scenario['ticker']
    position_value = scenario['position_value']
    loan_days = scenario['loan_days']
    client_id = scenario['client_id']
    
    stock_data = get_stock_data(ticker)
    broker_data = get_broker_data(client_id)
    volatility_data = get_volatility_data(ticker)
    
    # Calculate expected borrow rate
    borrow_rate = calculate_expected_borrow_rate(stock_data, volatility_data)
    
    # Calculate base borrow cost
    # Formula: position_value * borrow_rate * (loan_days / 365)
    base_borrow_cost = position_value * borrow_rate * (Decimal(loan_days) / Decimal('365'))
    
    # Calculate markup
    markup = base_borrow_cost * broker_data['markup_percentage']
    
    # Calculate transaction fees
    if broker_data['transaction_fee_type'] == TransactionFeeType.FLAT:
        transaction_fees = broker_data['transaction_amount']
    else:  # PERCENTAGE
        transaction_fees = position_value * broker_data['transaction_amount']
    
    # Calculate total fee
    total_fee = base_borrow_cost + markup + transaction_fees
    
    # Return the expected calculation result
    return {
        'total_fee': total_fee,
        'breakdown': {
            'borrow_cost': base_borrow_cost,
            'markup': markup,
            'transaction_fees': transaction_fees
        },
        'borrow_rate_used': borrow_rate
    }


class TestDataManager:
    """
    Manages test data lifecycle for end-to-end tests.
    """
    
    def __init__(self, env_config: Dict):
        """
        Initializes the TestDataManager with environment configuration.
        
        Args:
            env_config: Environment configuration dictionary
        """
        self._env_config = env_config
        self._test_data_refs = {}
        self._api_client = APIClient(settings=env_config.get('settings'))
    
    def setup(self) -> Dict:
        """
        Sets up test data for the current test environment.
        
        Returns:
            Dictionary containing references to created test data
        """
        self._test_data_refs = setup_test_data(self._env_config)
        return self._test_data_refs
    
    def cleanup(self) -> bool:
        """
        Cleans up test data from the current test environment.
        
        Returns:
            True if cleanup was successful, False otherwise
        """
        success = cleanup_test_data(self._env_config, self._test_data_refs)
        if success:
            self._test_data_refs = {}
        return success
    
    def get_scenario(self, scenario_name: str) -> Dict:
        """
        Gets a test scenario by name.
        
        Args:
            scenario_name: Name of the scenario to retrieve
            
        Returns:
            Test scenario data
        """
        return get_test_scenario(scenario_name)
    
    def get_expected_result(self, scenario_name: str) -> Dict:
        """
        Calculates expected result for a test scenario.
        
        Args:
            scenario_name: Name of the scenario to calculate
            
        Returns:
            Expected calculation result
        """
        scenario = self.get_scenario(scenario_name)
        return calculate_expected_fee(scenario)


@pytest.fixture
def test_data_manager(request) -> TestDataManager:
    """
    Pytest fixture that provides a TestDataManager instance.
    
    The TestDataManager is initialized with the test environment configuration
    and handles test data setup and cleanup.
    
    Returns:
        TestDataManager instance
    """
    env_config = get_test_settings().__dict__
    manager = TestDataManager(env_config)
    
    # Set up test data before the test
    manager.setup()
    
    # Provide manager to the test
    yield manager
    
    # Clean up test data after the test
    manager.cleanup()


@pytest.fixture
def test_stocks() -> List[Dict]:
    """
    Pytest fixture that provides test stock data.
    
    Returns:
        List of test stock dictionaries
    """
    return TEST_STOCKS


@pytest.fixture
def test_brokers() -> List[Dict]:
    """
    Pytest fixture that provides test broker data.
    
    Returns:
        List of test broker dictionaries
    """
    return TEST_BROKERS


@pytest.fixture
def test_volatility() -> List[Dict]:
    """
    Pytest fixture that provides test volatility data.
    
    Returns:
        List of test volatility dictionaries
    """
    return TEST_VOLATILITY


@pytest.fixture
def test_scenarios() -> List[Dict]:
    """
    Pytest fixture that provides all test calculation scenarios.
    
    Returns:
        List of test calculation scenario dictionaries
    """
    return TEST_CALCULATION_SCENARIOS


@pytest.fixture
def normal_market_scenario() -> Dict:
    """
    Pytest fixture for normal market conditions test scenario.
    
    Returns:
        Normal market test scenario
    """
    return get_test_scenario('normal_market')


@pytest.fixture
def high_volatility_scenario() -> Dict:
    """
    Pytest fixture for high volatility test scenario.
    
    Returns:
        High volatility test scenario
    """
    return get_test_scenario('high_volatility')


@pytest.fixture
def corporate_event_scenario() -> Dict:
    """
    Pytest fixture for corporate event test scenario.
    
    Returns:
        Corporate event test scenario
    """
    return get_test_scenario('corporate_event')


@pytest.fixture
def hard_to_borrow_scenario() -> Dict:
    """
    Pytest fixture for hard-to-borrow securities test scenario.
    
    Returns:
        Hard-to-borrow test scenario
    """
    return get_test_scenario('hard_to_borrow')


@pytest.fixture
def long_term_loan_scenario() -> Dict:
    """
    Pytest fixture for long-term loan test scenario.
    
    Returns:
        Long-term loan test scenario
    """
    return get_test_scenario('long_term_loan')