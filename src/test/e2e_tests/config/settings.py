"""
Configuration settings module for end-to-end tests of the Borrow Rate & Locate Fee Pricing Engine.

This module provides environment-specific configurations, test settings management,
and utilities for loading environment variables for testing purposes.
"""

import os
import enum
import logging
from enum import Enum
from functools import lru_cache
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv  # python-dotenv: version 1.0.0

# Default configuration values
DEFAULT_TEST_ENV_FILE = '.env.test'
DEFAULT_TEST_TIMEOUT = 30
DEFAULT_API_VERSION = 'v1'

# Configure logger
logger = logging.getLogger(__name__)


def load_test_env(env_file: str) -> bool:
    """
    Loads environment variables from a .env file for test configuration.
    
    Args:
        env_file: Path to the environment file to load
        
    Returns:
        bool: True if environment file was loaded successfully, False otherwise
    """
    if not os.path.exists(env_file):
        logger.warning(f"Environment file {env_file} not found")
        return False
    
    try:
        load_dotenv(env_file)
        logger.info(f"Loaded environment variables from {env_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to load environment variables from {env_file}: {str(e)}")
        return False


class TestEnvironment(Enum):
    """
    Enumeration of test environments for configuration.
    """
    LOCAL = 'local'
    DEVELOPMENT = 'development'
    STAGING = 'staging'
    PRODUCTION = 'production'
    
    @staticmethod
    def get_env(env_str: str) -> 'TestEnvironment':
        """
        Gets the environment enum value from a string.
        
        Args:
            env_str: String representation of the environment
            
        Returns:
            TestEnvironment: Environment enum value
        """
        env_str = env_str.lower() if env_str else ''
        for env in TestEnvironment:
            if env.value == env_str:
                return env
        
        logger.warning(f"Unknown environment '{env_str}', defaulting to LOCAL")
        return TestEnvironment.LOCAL


class MockServerConfig:
    """
    Configuration for mock external API servers.
    """
    def __init__(self):
        """
        Initializes the MockServerConfig with values from environment variables.
        """
        self.seclend_api_url = os.getenv('TEST_MOCK_SECLEND_API_URL', 'http://localhost:8001')
        self.market_api_url = os.getenv('TEST_MOCK_MARKET_API_URL', 'http://localhost:8002')
        self.event_api_url = os.getenv('TEST_MOCK_EVENT_API_URL', 'http://localhost:8003')


class TestDataConfig:
    """
    Configuration for test data used in end-to-end tests.
    """
    def __init__(self):
        """
        Initializes the TestDataConfig with default test data.
        """
        # Default test stock data
        self.stocks = [
            {"ticker": "AAPL", "borrow_status": "EASY", "min_borrow_rate": 0.02},
            {"ticker": "GME", "borrow_status": "HARD", "min_borrow_rate": 0.10},
            {"ticker": "TSLA", "borrow_status": "MEDIUM", "min_borrow_rate": 0.05},
            {"ticker": "AMZN", "borrow_status": "EASY", "min_borrow_rate": 0.01},
            {"ticker": "MSFT", "borrow_status": "EASY", "min_borrow_rate": 0.015}
        ]
        
        # Default test broker data
        self.brokers = [
            {"client_id": "broker1", "markup_percentage": 0.05, "transaction_fee_type": "FLAT", "transaction_amount": 10.0},
            {"client_id": "broker2", "markup_percentage": 0.08, "transaction_fee_type": "PERCENTAGE", "transaction_amount": 0.01},
            {"client_id": "broker3", "markup_percentage": 0.03, "transaction_fee_type": "FLAT", "transaction_amount": 5.0}
        ]
        
        # Default test volatility data
        self.volatility = [
            {"ticker": "AAPL", "vol_index": 15.0, "event_risk_factor": 1},
            {"ticker": "GME", "vol_index": 35.0, "event_risk_factor": 8},
            {"ticker": "TSLA", "vol_index": 25.0, "event_risk_factor": 3},
            {"ticker": "AMZN", "vol_index": 18.0, "event_risk_factor": 2},
            {"ticker": "MSFT", "vol_index": 12.0, "event_risk_factor": 1}
        ]
        
        # Default test calculation scenarios
        self.test_cases = [
            {
                "name": "Standard ETB Calculation",
                "ticker": "AAPL",
                "position_value": 100000,
                "loan_days": 30,
                "client_id": "broker1",
                "expected_outcome": {"status": "success"}
            },
            {
                "name": "Hard-to-Borrow Calculation",
                "ticker": "GME",
                "position_value": 50000,
                "loan_days": 7,
                "client_id": "broker2",
                "expected_outcome": {"status": "success"}
            },
            {
                "name": "High Volatility Calculation",
                "ticker": "TSLA",
                "position_value": 75000,
                "loan_days": 14,
                "client_id": "broker3",
                "expected_outcome": {"status": "success"}
            },
            {
                "name": "Invalid Ticker Test",
                "ticker": "INVALID",
                "position_value": 10000,
                "loan_days": 30,
                "client_id": "broker1",
                "expected_outcome": {"status": "error"}
            },
            {
                "name": "Invalid Client Test",
                "ticker": "AAPL",
                "position_value": 10000,
                "loan_days": 30,
                "client_id": "invalid_client",
                "expected_outcome": {"status": "error"}
            }
        ]


class TestSettings:
    """
    Main settings class for end-to-end tests configuration.
    """
    def __init__(self):
        """
        Initializes the TestSettings object with values from environment variables.
        """
        # Load environment variables from default test env file
        load_test_env(os.getenv('TEST_ENV_FILE', DEFAULT_TEST_ENV_FILE))
        
        # API configuration
        self.api_base_url = os.getenv('TEST_API_BASE_URL', 'http://localhost:8000')
        self.api_version = os.getenv('TEST_API_VERSION', DEFAULT_API_VERSION)
        self.api_key = os.getenv('TEST_API_KEY', 'test-api-key')
        
        # Test environment configuration
        env_str = os.getenv('TEST_ENVIRONMENT', 'local')
        self.environment = TestEnvironment.get_env(env_str)
        
        # Test execution configuration
        self.test_timeout = int(os.getenv('TEST_TIMEOUT', DEFAULT_TEST_TIMEOUT))
        self.mock_external_apis = os.getenv('TEST_MOCK_EXTERNAL_APIS', 'true').lower() == 'true'
        
        # Initialize sub-configurations
        self.mock_server_config = MockServerConfig()
        self.test_data_config = TestDataConfig()
    
    def is_local(self) -> bool:
        """
        Checks if the current test environment is local.
        
        Returns:
            bool: True if environment is local
        """
        return self.environment == TestEnvironment.LOCAL
    
    def is_development(self) -> bool:
        """
        Checks if the current test environment is development.
        
        Returns:
            bool: True if environment is development
        """
        return self.environment == TestEnvironment.DEVELOPMENT
    
    def is_staging(self) -> bool:
        """
        Checks if the current test environment is staging.
        
        Returns:
            bool: True if environment is staging
        """
        return self.environment == TestEnvironment.STAGING
    
    def is_production(self) -> bool:
        """
        Checks if the current test environment is production.
        
        Returns:
            bool: True if environment is production
        """
        return self.environment == TestEnvironment.PRODUCTION
    
    def get_api_url(self) -> str:
        """
        Gets the full API URL including version.
        
        Returns:
            str: Full API URL
        """
        return f"{self.api_base_url}/api/{self.api_version}"
    
    def get_mock_server_url(self, server_name: str) -> str:
        """
        Gets the URL for a specific mock server.
        
        Args:
            server_name: Name of the mock server ('seclend', 'market', or 'event')
            
        Returns:
            str: Mock server URL
            
        Raises:
            ValueError: If server_name is invalid
        """
        if server_name == 'seclend':
            return self.mock_server_config.seclend_api_url
        elif server_name == 'market':
            return self.mock_server_config.market_api_url
        elif server_name == 'event':
            return self.mock_server_config.event_api_url
        else:
            raise ValueError(f"Invalid mock server name: {server_name}")
    
    def get_test_data(self, data_type: str) -> List[Dict[str, Any]]:
        """
        Gets test data configuration.
        
        Args:
            data_type: Type of test data ('stocks', 'brokers', 'volatility', or 'test_cases')
            
        Returns:
            list: Test data for the specified type
            
        Raises:
            ValueError: If data_type is invalid
        """
        if data_type == 'stocks':
            return self.test_data_config.stocks
        elif data_type == 'brokers':
            return self.test_data_config.brokers
        elif data_type == 'volatility':
            return self.test_data_config.volatility
        elif data_type == 'test_cases':
            return self.test_data_config.test_cases
        else:
            raise ValueError(f"Invalid test data type: {data_type}")


@lru_cache(maxsize=1)
def get_test_settings() -> TestSettings:
    """
    Returns the singleton TestSettings instance, creating it if necessary.
    
    Returns:
        TestSettings: Singleton TestSettings instance
    """
    return TestSettings()