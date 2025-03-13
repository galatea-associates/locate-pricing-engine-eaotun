import os
import json
import logging
import yaml
from locust import HttpUser, between

# Import the specific scenario classes
from scenarios.borrow_rate_scenario import BorrowRateScenario
from scenarios.calculate_fee_scenario import CalculateFeeScenario
from scenarios.mixed_workload_scenario import MixedWorkloadScenario

# Default config file location, can be overridden via environment variable
CONFIG_FILE = os.getenv('LOAD_TEST_CONFIG', 'config.yaml')

def load_config(config_file):
    """
    Loads test configuration from the specified YAML file
    
    Args:
        config_file (str): Path to the configuration file
        
    Returns:
        dict: Configuration parameters for the load test
    """
    try:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_file}")
        return {}
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML configuration: {e}")
        return {}

def setup_logger():
    """
    Configures logging for the load test
    
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger("locust")
    
    # Set log level based on environment variable or default to INFO
    log_level_name = os.getenv('LOAD_TEST_LOG_LEVEL', 'INFO')
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Configure console handler
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

class LoadTestUser(HttpUser):
    """Base user class for load testing with common functionality"""
    
    config = {}
    logger = None
    
    def __init__(self, environment):
        """Initializes the base user with configuration and logging"""
        super().__init__(environment)
        self.config = load_config(CONFIG_FILE)
        self.logger = setup_logger()
    
    def on_start(self):
        """Setup method called when a simulated user starts"""
        # Set common headers including API key from configuration
        env_config = self.config.get("environments", {}).get("staging", {})
        self.client.headers = env_config.get("headers", {})
        self.client.headers["X-API-Key"] = env_config.get("api_key", "${API_KEY}")
        
        # Initialize any other session state needed
        self.logger.info("LoadTestUser initialized with headers: %s", self.client.headers)
    
    def on_stop(self):
        """Cleanup method called when a simulated user stops"""
        # Perform any necessary cleanup
        self.logger.info("LoadTestUser finished execution")

class BorrowRateUser(LoadTestUser):
    """User class that simulates clients requesting borrow rates"""
    
    tasks = BorrowRateScenario.tasks
    weight = 4  # 40% of the mix, from the config weight of 0.4
    
    def __init__(self, environment):
        """Initializes the borrow rate user"""
        super().__init__(environment)
        # Set user weight based on configuration
        config_weight = self.config.get("scenarios", {}).get("borrow_rate", {}).get("weight", 0.4)
        self.weight = int(config_weight * 10)  # Convert 0.4 to 4, etc.

class CalculateFeeUser(LoadTestUser):
    """User class that simulates clients requesting fee calculations"""
    
    tasks = CalculateFeeScenario.tasks
    weight = 6  # 60% of the mix, from the config weight of 0.6
    
    def __init__(self, environment):
        """Initializes the calculate fee user"""
        super().__init__(environment)
        # Set user weight based on configuration
        config_weight = self.config.get("scenarios", {}).get("calculate_fee", {}).get("weight", 0.6)
        self.weight = int(config_weight * 10)  # Convert 0.6 to 6, etc.

class MixedWorkloadUser(LoadTestUser):
    """User class that simulates clients with mixed request patterns"""
    
    tasks = MixedWorkloadScenario.tasks
    weight = 5  # Default weight
    
    def __init__(self, environment):
        """Initializes the mixed workload user"""
        super().__init__(environment)
        # Set user weight based on configuration
        self.weight = self.config.get("scenarios", {}).get("mixed_workload", {}).get("weight", 5)