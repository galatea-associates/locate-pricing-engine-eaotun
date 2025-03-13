"""
Configuration settings module for integration tests of the Borrow Rate & Locate Fee Pricing Engine.
Provides environment-specific configuration, test settings management, and utilities for loading
environment variables.
"""

import os
import enum
import json
import logging
from functools import lru_cache
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Default configuration values
DEFAULT_TEST_ENV_FILE = '.env.test.integration'
DEFAULT_TEST_TIMEOUT = 30
DEFAULT_API_VERSION = 'v1'
DEFAULT_MOCK_SECLEND_PORT = 8081
DEFAULT_MOCK_MARKET_PORT = 8082
DEFAULT_MOCK_EVENT_PORT = 8083

# Configure module logger
logger = logging.getLogger(__name__)


@enum.Enum
class TestEnvironment(str, enum.Enum):
    """Enumeration of test environments for configuration."""
    LOCAL = 'local'
    DEVELOPMENT = 'development'
    STAGING = 'staging'
    PRODUCTION = 'production'

    @classmethod
    def from_string(cls, env_str: str) -> 'TestEnvironment':
        """Creates a TestEnvironment enum from a string value.
        
        Args:
            env_str: String representation of environment name
            
        Returns:
            TestEnvironment enum value
        """
        try:
            return cls(env_str.lower())
        except (ValueError, AttributeError):
            logger.warning(f"Invalid environment string '{env_str}', defaulting to LOCAL")
            return cls.LOCAL


class MockServerConfig:
    """Configuration for mock external API servers."""
    
    def __init__(self):
        """Initializes the MockServerConfig with values from environment variables."""
        self.host = os.getenv('TEST_MOCK_HOST', 'localhost')
        self.seclend_port = int(os.getenv('TEST_MOCK_SECLEND_PORT', DEFAULT_MOCK_SECLEND_PORT))
        self.market_port = int(os.getenv('TEST_MOCK_MARKET_PORT', DEFAULT_MOCK_MARKET_PORT))
        self.event_port = int(os.getenv('TEST_MOCK_EVENT_PORT', DEFAULT_MOCK_EVENT_PORT))
    
    def get_url(self, server_type: str) -> str:
        """Gets the full URL for a specific mock server.
        
        Args:
            server_type: Type of mock server ('seclend', 'market', or 'event')
            
        Returns:
            Full URL for the specified mock server
            
        Raises:
            ValueError: If server_type is not recognized
        """
        if server_type == 'seclend':
            return f"http://{self.host}:{self.seclend_port}"
        elif server_type == 'market':
            return f"http://{self.host}:{self.market_port}"
        elif server_type == 'event':
            return f"http://{self.host}:{self.event_port}"
        else:
            raise ValueError(f"Invalid server type: {server_type}. Must be 'seclend', 'market', or 'event'")


class TestDataConfig:
    """Configuration for test data used in integration tests."""
    
    def __init__(self):
        """Initializes the TestDataConfig with default test data."""
        # Default test stock data
        self.stocks = [
            {"ticker": "AAPL", "borrow_status": "EASY", "min_borrow_rate": 0.05},
            {"ticker": "GME", "borrow_status": "HARD", "min_borrow_rate": 0.50},
            {"ticker": "TSLA", "borrow_status": "MEDIUM", "min_borrow_rate": 0.20}
        ]
        
        # Default test broker data
        self.brokers = [
            {"client_id": "test_broker_1", "markup_percentage": 0.05, "transaction_fee_type": "FLAT", "transaction_amount": 10.00},
            {"client_id": "test_broker_2", "markup_percentage": 0.10, "transaction_fee_type": "PERCENTAGE", "transaction_amount": 0.01}
        ]
        
        # Default test volatility data
        self.volatility = [
            {"stock_id": "AAPL", "vol_index": 15.5, "event_risk_factor": 0},
            {"stock_id": "GME", "vol_index": 75.3, "event_risk_factor": 8},
            {"stock_id": "TSLA", "vol_index": 45.2, "event_risk_factor": 5}
        ]
        
        # Default test calculation scenarios
        self.test_cases = [
            {"ticker": "AAPL", "position_value": 100000, "loan_days": 30, "client_id": "test_broker_1"},
            {"ticker": "GME", "position_value": 50000, "loan_days": 7, "client_id": "test_broker_2"},
            {"ticker": "TSLA", "position_value": 75000, "loan_days": 15, "client_id": "test_broker_1"}
        ]
    
    def load_from_file(self, file_path: str) -> bool:
        """Loads test data from a JSON file.
        
        Args:
            file_path: Path to the JSON file containing test data
            
        Returns:
            True if data was loaded successfully, False otherwise
        """
        if not os.path.exists(file_path):
            logger.error(f"Test data file not found: {file_path}")
            return False
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if 'stocks' in data:
                self.stocks = data['stocks']
            if 'brokers' in data:
                self.brokers = data['brokers']
            if 'volatility' in data:
                self.volatility = data['volatility']
            if 'test_cases' in data:
                self.test_cases = data['test_cases']
                
            logger.info(f"Successfully loaded test data from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading test data from {file_path}: {str(e)}")
            return False


class TestSettings:
    """Main settings class for integration tests configuration."""
    
    def __init__(self):
        """Initializes the TestSettings object with values from environment variables."""
        # Try to load environment variables from default test env file
        load_test_env(DEFAULT_TEST_ENV_FILE)
        
        # API settings
        self.api_base_url = os.getenv('TEST_API_BASE_URL', 'http://localhost:8000')
        self.api_version = os.getenv('TEST_API_VERSION', DEFAULT_API_VERSION)
        self.test_api_key = os.getenv('TEST_API_KEY', 'test-api-key')
        
        # Environment settings
        env_str = os.getenv('TEST_ENVIRONMENT', 'local')
        self.environment = TestEnvironment.from_string(env_str)
        
        # Test execution settings
        self.test_timeout = int(os.getenv('TEST_TIMEOUT', DEFAULT_TEST_TIMEOUT))
        
        # Mock server settings
        use_mock_str = os.getenv('TEST_USE_MOCK_SERVERS', 'true')
        self.use_mock_servers = use_mock_str.lower() == 'true'
        self.mock_server_config = MockServerConfig()
        
        # Test data configuration
        self.test_data_config = TestDataConfig()
    
    def is_local(self) -> bool:
        """Checks if the current test environment is local.
        
        Returns:
            True if environment is local
        """
        return self.environment == TestEnvironment.LOCAL
    
    def is_development(self) -> bool:
        """Checks if the current test environment is development.
        
        Returns:
            True if environment is development
        """
        return self.environment == TestEnvironment.DEVELOPMENT
    
    def is_staging(self) -> bool:
        """Checks if the current test environment is staging.
        
        Returns:
            True if environment is staging
        """
        return self.environment == TestEnvironment.STAGING
    
    def is_production(self) -> bool:
        """Checks if the current test environment is production.
        
        Returns:
            True if environment is production
        """
        return self.environment == TestEnvironment.PRODUCTION
    
    def get_api_url(self) -> str:
        """Gets the full API URL including version.
        
        Returns:
            Full API URL
        """
        return f"{self.api_base_url}/api/{self.api_version}"
    
    def is_using_mock_servers(self) -> bool:
        """Checks if mock servers should be used for external APIs.
        
        Returns:
            True if mock servers should be used
        """
        return self.use_mock_servers
    
    def get_mock_server_url(self, server_type: str) -> str:
        """Gets the URL for a specific mock server.
        
        Args:
            server_type: Type of mock server ('seclend', 'market', or 'event')
            
        Returns:
            Mock server URL
            
        Raises:
            ValueError: If server_type is not recognized
        """
        return self.mock_server_config.get_url(server_type)
    
    def get_test_data(self, data_type: str) -> List[Dict[str, Any]]:
        """Gets test data configuration.
        
        Args:
            data_type: Type of test data ('stocks', 'brokers', 'volatility', or 'test_cases')
            
        Returns:
            Test data for the specified type
            
        Raises:
            ValueError: If data_type is not recognized
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
            raise ValueError(
                f"Invalid data type: {data_type}. Must be 'stocks', 'brokers', 'volatility', or 'test_cases'"
            )


def load_test_env(env_file: str = DEFAULT_TEST_ENV_FILE) -> bool:
    """Loads environment variables from a .env file for test configuration.
    
    Args:
        env_file: Path to the environment file
        
    Returns:
        True if environment file was loaded successfully, False otherwise
    """
    if not os.path.exists(env_file):
        logger.warning(f"Environment file not found: {env_file}")
        return False
    
    loaded = load_dotenv(env_file)
    if loaded:
        logger.info(f"Loaded environment variables from {env_file}")
    else:
        logger.warning(f"Failed to load environment variables from {env_file}")
    
    return loaded


@lru_cache(maxsize=1)
def get_test_settings() -> TestSettings:
    """Returns the singleton TestSettings instance, creating it if necessary.
    
    Returns:
        Singleton TestSettings instance
    """
    return TestSettings()


def reload_test_settings() -> TestSettings:
    """Forces a reload of the test settings from environment variables.
    
    Returns:
        Reloaded TestSettings instance
    """
    # Clear the cache to force recreation of the TestSettings instance
    get_test_settings.cache_clear()
    return get_test_settings()