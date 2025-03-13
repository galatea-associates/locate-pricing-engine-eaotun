"""
Configuration settings for performance tests of the Borrow Rate & Locate Fee Pricing Engine.

This module defines test parameters, performance thresholds, and environment-specific
settings used across all performance tests to ensure consistent test execution and
validation against SLAs.
"""

import os
import logging
import functools
from typing import Dict, Any

import pydantic  # pydantic 2.4.0+

from src.backend.config.environment import Environment, from_string, DEVELOPMENT, STAGING, PRODUCTION


# Configure logging
logger = logging.getLogger(__name__)

# Global singleton instance
_test_settings_instance = None


class PerformanceThresholds(pydantic.BaseModel):
    """
    Class that defines performance thresholds for different test environments.
    
    These thresholds align with the SLAs defined in the system specification
    and are used to validate test results against performance requirements.
    """
    response_time: int  # Max response time in milliseconds (p95)
    throughput: int  # Min throughput in requests per second
    error_rate: float  # Max error rate as a percentage
    
    def __init__(self, environment: Environment, **data):
        """
        Initializes the PerformanceThresholds with environment-specific values.
        
        Args:
            environment: The Environment enum value representing the current environment
        """
        # Define threshold values based on environment (stricter in production)
        if environment == Environment.PRODUCTION:
            # Production has the strictest requirements
            response_time = 100  # p95 < 100ms as per SLA
            throughput = 1000  # Must handle 1000+ requests/second as per spec
            error_rate = 0.1  # 0.1% error rate maximum for production
        elif environment == Environment.STAGING:
            # Staging is slightly more lenient than production
            response_time = 150  # Allow 50% more latency in staging
            throughput = 800  # 80% of production throughput requirement
            error_rate = 0.5  # 0.5% error rate allowed in staging
        else:  # DEVELOPMENT or any other environment
            # Development is most lenient
            response_time = 200  # Double the response time allowed in dev
            throughput = 500  # 50% of production throughput requirement
            error_rate = 1.0  # 1% error rate allowed in development
        
        # Initialize the Pydantic model with calculated values
        super().__init__(
            response_time=response_time,
            throughput=throughput,
            error_rate=error_rate,
            **data
        )


class TestSettings:
    """
    Main settings class that provides access to all performance test configuration.
    
    This class loads settings from environment variables with sensible defaults
    and provides methods to access configuration values based on the current
    test environment.
    """
    
    def __init__(self):
        """
        Initializes the TestSettings object with values from environment variables.
        
        Settings are loaded from environment variables with defaults provided
        for cases where environment variables are not defined.
        """
        # API configuration
        self.api_base_url = os.environ.get("TEST_API_BASE_URL", "http://localhost:8000/api/v1")
        self.test_api_key = os.environ.get("TEST_API_KEY", "test_key_123456")
        
        # Test parameters
        self.load_test_duration = int(os.environ.get("TEST_DURATION_SECONDS", "300"))  # 5 minutes by default
        self.target_rps = int(os.environ.get("TARGET_RPS", "1000"))  # Target requests per second
        self.concurrent_users = int(os.environ.get("CONCURRENT_USERS", "100"))  # Simulated users
        
        # Environment determination
        env_str = os.environ.get("TEST_ENVIRONMENT", "development")
        self.environment = Environment.from_string(env_str)
        
        # Performance thresholds based on environment
        self.performance_thresholds = PerformanceThresholds(self.environment)
        
        # Test data scale (small, medium, large)
        self.test_data_scale = os.environ.get("TEST_DATA_SCALE", "medium")
        
        logger.info(f"Initialized TestSettings for environment: {self.environment.value}")
        logger.info(f"Performance thresholds: response_time={self.performance_thresholds.response_time}ms, "
                   f"throughput={self.performance_thresholds.throughput}rps, "
                   f"error_rate={self.performance_thresholds.error_rate}%")
    
    def get_api_url(self, endpoint: str) -> str:
        """
        Returns the full API URL for a specific endpoint.
        
        Args:
            endpoint: The API endpoint path
            
        Returns:
            Full API URL
        """
        # Ensure endpoint starts with a slash for proper URL joining
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
            
        return f"{self.api_base_url}{endpoint}"
    
    def get_response_time_threshold(self) -> int:
        """
        Returns the response time threshold based on the current environment.
        
        Returns:
            Response time threshold in milliseconds
        """
        return self.performance_thresholds.response_time
    
    def get_throughput_threshold(self) -> int:
        """
        Returns the throughput threshold based on the current environment.
        
        Returns:
            Throughput threshold in requests per second
        """
        return self.performance_thresholds.throughput
    
    def get_error_rate_threshold(self) -> float:
        """
        Returns the error rate threshold based on the current environment.
        
        Returns:
            Error rate threshold as a percentage
        """
        return self.performance_thresholds.error_rate
    
    def is_development(self) -> bool:
        """
        Checks if the current environment is development.
        
        Returns:
            True if environment is development
        """
        return self.environment == Environment.DEVELOPMENT
    
    def is_staging(self) -> bool:
        """
        Checks if the current environment is staging.
        
        Returns:
            True if environment is staging
        """
        return self.environment == Environment.STAGING
    
    def is_production(self) -> bool:
        """
        Checks if the current environment is production.
        
        Returns:
            True if environment is production
        """
        return self.environment == Environment.PRODUCTION
    
    def get_test_data_size(self) -> Dict[str, Any]:
        """
        Returns the appropriate test data size based on scale setting.
        
        This provides configuration for the amount of test data to generate
        based on the test_data_scale setting.
        
        Returns:
            Dictionary with test data size parameters
        """
        if self.test_data_scale == "small":
            return {
                "num_stocks": 100,
                "num_brokers": 10,
                "transactions_per_test": 1000
            }
        elif self.test_data_scale == "large":
            return {
                "num_stocks": 5000,
                "num_brokers": 100,
                "transactions_per_test": 50000
            }
        else:  # medium or any unrecognized value
            return {
                "num_stocks": 1000,
                "num_brokers": 50,
                "transactions_per_test": 10000
            }


@functools.lru_cache(maxsize=1)
def get_test_settings() -> TestSettings:
    """
    Returns the singleton TestSettings instance, creating it if necessary.
    
    This function implements the singleton pattern to ensure that
    test settings are consistent across all test modules.
    
    Returns:
        Singleton TestSettings instance
    """
    global _test_settings_instance
    if _test_settings_instance is None:
        _test_settings_instance = TestSettings()
    return _test_settings_instance