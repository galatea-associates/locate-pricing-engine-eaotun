"""
Provides pytest fixtures for setting up and managing test environments for 
performance testing of the Borrow Rate & Locate Fee Pricing Engine. This module 
creates isolated test environments with appropriate configuration for different 
performance test scenarios.
"""

import os
import logging
import contextlib
from typing import Dict, Any

import pytest

from src.backend.config.environment import Environment
from src.test.performance_tests.config.settings import get_test_settings
from src.test.performance_tests.helpers.metrics_collector import get_metrics_collector

# Configure logger
logger = logging.getLogger(__name__)

def setup_test_environment(env_type: Environment, config: Dict = None) -> Dict:
    """
    Sets up the test environment with appropriate configuration.
    
    Args:
        env_type: The environment type to set up
        config: Additional configuration overrides
        
    Returns:
        Environment configuration dictionary
    """
    logger.info(f"Setting up {env_type.value} test environment")
    
    # Get test settings
    settings = get_test_settings()
    
    # Create environment configuration dictionary
    env_config = {
        "env_type": env_type,
        "config": config or {},
        "settings": settings,
    }
    
    # Set up API endpoints based on environment type
    if env_type == Environment.DEVELOPMENT:
        env_config["api_base_url"] = os.environ.get("DEV_API_BASE_URL", "http://localhost:8000/api/v1")
    elif env_type == Environment.STAGING:
        env_config["api_base_url"] = os.environ.get("STAGING_API_BASE_URL", "https://staging-api.example.com/api/v1")
    elif env_type == Environment.PRODUCTION:
        env_config["api_base_url"] = os.environ.get("PROD_API_BASE_URL", "https://api.example.com/api/v1")
    
    # Configure metrics collection based on environment type
    metrics_config = {}
    if env_type == Environment.DEVELOPMENT:
        metrics_config = {
            "collection_interval": 1.0,  # 1 second intervals
            "api": {"enabled": True},
            "calculation": {"enabled": True},
            "resource": {"enabled": True}
        }
    elif env_type == Environment.STAGING:
        metrics_config = {
            "collection_interval": 0.5,  # 0.5 second intervals
            "api": {"enabled": True},
            "calculation": {"enabled": True},
            "resource": {"enabled": True}
        }
    elif env_type == Environment.PRODUCTION:
        metrics_config = {
            "collection_interval": 0.1,  # 0.1 second intervals
            "api": {"enabled": True},
            "calculation": {"enabled": True},
            "resource": {"enabled": True}
        }
    
    env_config["metrics_collector"] = get_metrics_collector(metrics_config)
    
    # Set up appropriate logging level for the environment
    if env_type == Environment.DEVELOPMENT:
        logging.getLogger().setLevel(logging.DEBUG)
    elif env_type == Environment.STAGING:
        logging.getLogger().setLevel(logging.INFO)
    elif env_type == Environment.PRODUCTION:
        logging.getLogger().setLevel(logging.WARNING)
    
    return env_config

def teardown_test_environment(env_config: Dict) -> None:
    """
    Cleans up the test environment after test execution.
    
    Args:
        env_config: Environment configuration to tear down
    """
    env_type = env_config.get("env_type")
    logger.info(f"Tearing down {env_type.value if env_type else 'unknown'} test environment")
    
    # Clean up any resources created during testing
    metrics_collector = env_config.get("metrics_collector")
    if metrics_collector:
        # Stop metrics collection if active
        if metrics_collector.is_collecting:
            metrics_collector.stop_collection()
        # Reset metrics collector
        metrics_collector.reset()
    
    # Reset any modified settings or configurations
    # Close any open connections or resources

class TestEnvironment:
    """
    Context manager class for test environment setup and teardown.
    """
    
    def __init__(self, env_type: Environment, config: Dict = None):
        """
        Initializes the TestEnvironment with specified environment type and configuration.
        
        Args:
            env_type: The environment type to set up
            config: Additional configuration overrides
        """
        self.env_type = env_type
        self.config = config or {}
        self.env_config = None
    
    def __enter__(self) -> 'TestEnvironment':
        """
        Sets up the test environment when entering the context.
        
        Returns:
            Self reference for context manager
        """
        self.env_config = setup_test_environment(self.env_type, self.config)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Tears down the test environment when exiting the context.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        teardown_test_environment(self.env_config)
        if exc_type:
            logger.error(f"Exception occurred during test: {exc_val}")
    
    def get_config(self) -> Dict:
        """
        Returns the current environment configuration.
        
        Returns:
            Current environment configuration
        """
        if not self.env_config:
            raise RuntimeError("Test environment not yet set up. Use within a context manager.")
        return self.env_config

@pytest.fixture
def development_environment():
    """
    Pytest fixture that provides a development test environment.
    
    Yields:
        TestEnvironment: Test environment context manager
    """
    with TestEnvironment(Environment.DEVELOPMENT) as env:
        yield env

@pytest.fixture
def staging_environment():
    """
    Pytest fixture that provides a staging test environment.
    
    Yields:
        TestEnvironment: Test environment context manager
    """
    with TestEnvironment(Environment.STAGING) as env:
        yield env

@pytest.fixture
def production_like_environment():
    """
    Pytest fixture that provides a production-like test environment.
    
    Yields:
        TestEnvironment: Test environment context manager
    """
    with TestEnvironment(Environment.PRODUCTION) as env:
        yield env

@pytest.fixture
def load_test_environment():
    """
    Pytest fixture that provides an environment configured for load testing.
    
    Yields:
        TestEnvironment: Test environment context manager
    """
    config = {
        "test_type": "load",
        "target_rps": 1000,  # Target requests per second
        "duration_seconds": 300,  # 5 minutes
        "concurrent_users": 100,
        "metrics_output_dir": "./metrics/load_test"
    }
    
    with TestEnvironment(Environment.PRODUCTION, config) as env:
        yield env

@pytest.fixture
def stress_test_environment():
    """
    Pytest fixture that provides an environment configured for stress testing.
    
    Yields:
        TestEnvironment: Test environment context manager
    """
    config = {
        "test_type": "stress",
        "target_rps": 2000,  # Target requests per second
        "duration_seconds": 600,  # 10 minutes
        "concurrent_users": 200,
        "metrics_output_dir": "./metrics/stress_test"
    }
    
    with TestEnvironment(Environment.PRODUCTION, config) as env:
        yield env

@pytest.fixture
def endurance_test_environment():
    """
    Pytest fixture that provides an environment configured for endurance testing.
    
    Yields:
        TestEnvironment: Test environment context manager
    """
    config = {
        "test_type": "endurance",
        "target_rps": 800,  # Target requests per second (slightly lower for sustained testing)
        "duration_seconds": 86400,  # 24 hours
        "concurrent_users": 80,
        "metrics_output_dir": "./metrics/endurance_test"
    }
    
    with TestEnvironment(Environment.PRODUCTION, config) as env:
        yield env