"""
Configuration module for test data generation in the Borrow Rate & Locate Fee Pricing Engine.

This module defines test scenarios, generation parameters, and utility functions for
configuring the data generation process across different data types including stocks,
brokers, volatility metrics, market data, and event data.
"""

import os
import json
from pathlib import Path
import yaml  # pyyaml 6.0+

# Default output directory for generated data files
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'data')

# Default output format and supported formats
DEFAULT_OUTPUT_FORMAT = 'json'
SUPPORTED_OUTPUT_FORMATS = ['json', 'csv', 'sql']

# Test scenarios with their configurations
TEST_SCENARIOS = {
    'normal_market': {
        'description': 'Standard market conditions with typical volatility and borrow rates',
        'volatility_range': [10.0, 25.0],
        'etb_percentage': 0.7,  # Easy-to-borrow percentage
        'htb_percentage': 0.1,  # Hard-to-borrow percentage
        'event_probability': 0.2  # Probability of a stock having an upcoming event
    },
    'high_volatility': {
        'description': 'Market with elevated volatility and higher borrow rates',
        'volatility_range': [25.0, 45.0],
        'etb_percentage': 0.5,
        'htb_percentage': 0.3,
        'event_probability': 0.3
    },
    'corporate_events': {
        'description': 'Market with significant corporate events affecting many stocks',
        'volatility_range': [15.0, 35.0],
        'etb_percentage': 0.6,
        'htb_percentage': 0.2,
        'event_probability': 0.7
    },
    'hard_to_borrow': {
        'description': 'Market with limited stock availability and high borrow rates',
        'volatility_range': [15.0, 30.0],
        'etb_percentage': 0.3,
        'htb_percentage': 0.5,
        'event_probability': 0.3
    },
    'market_disruption': {
        'description': 'Extreme market conditions with very high volatility and borrow rates',
        'volatility_range': [35.0, 60.0],
        'etb_percentage': 0.2,
        'htb_percentage': 0.7,
        'event_probability': 0.5
    }
}

# Configuration for stock data generation
STOCK_GENERATION_CONFIG = {
    'min_ticker_length': 3,
    'max_ticker_length': 5,
    'min_borrow_rate': {
        'EASY': 0.01,    # 1% minimum for easy-to-borrow
        'MEDIUM': 0.05,  # 5% minimum for medium difficulty
        'HARD': 0.15     # 15% minimum for hard-to-borrow
    },
    'max_borrow_rate': {
        'EASY': 0.05,    # 5% maximum for easy-to-borrow
        'MEDIUM': 0.15,  # 15% maximum for medium difficulty
        'HARD': 0.5      # 50% maximum for hard-to-borrow
    }
}

# Configuration for broker data generation
BROKER_GENERATION_CONFIG = {
    'client_id_prefix': 'BRK',
    'min_markup_percentage': 1.0,  # 1% minimum markup
    'max_markup_percentage': 10.0,  # 10% maximum markup
    'min_transaction_fee_flat': 10.0,  # $10 minimum flat fee
    'max_transaction_fee_flat': 50.0,  # $50 maximum flat fee
    'min_transaction_fee_percentage': 0.1,  # 0.1% minimum percentage fee
    'max_transaction_fee_percentage': 1.0,  # 1% maximum percentage fee
    'fee_type_distribution': {
        'FLAT': 0.6,       # 60% of brokers use flat fees
        'PERCENTAGE': 0.4  # 40% of brokers use percentage fees
    }
}

# Configuration for volatility data generation
VOLATILITY_GENERATION_CONFIG = {
    'min_vol_index': 10.0,  # Minimum volatility index
    'max_vol_index': 60.0,  # Maximum volatility index
    'min_event_risk_factor': 1,  # Minimum event risk factor (1-10 scale)
    'max_event_risk_factor': 10,  # Maximum event risk factor
    'default_event_probability': 0.2,  # Default probability of an event
    'days_of_history': 30  # Number of days of historical volatility data to generate
}

# Configuration for market data generation
MARKET_DATA_GENERATION_CONFIG = {
    'min_price': 5.0,  # Minimum stock price
    'max_price': 500.0,  # Maximum stock price
    'min_daily_change_percentage': -5.0,  # Minimum daily price change
    'max_daily_change_percentage': 5.0,  # Maximum daily price change
    'min_volume': 10000,  # Minimum daily volume
    'max_volume': 10000000,  # Maximum daily volume
    'days_of_history': 30  # Number of days of historical market data to generate
}

# Configuration for event data generation
EVENT_DATA_GENERATION_CONFIG = {
    'event_types': [
        'earnings',
        'dividend',
        'stock_split',
        'merger',
        'acquisition',
        'regulatory_announcement'
    ],
    'min_future_days': 1,  # Minimum days in the future for events
    'max_future_days': 30,  # Maximum days in the future for events
    'days_of_future': 30  # Number of days into the future for which to generate events
}

# Configuration for API key generation
API_KEY_GENERATION_CONFIG = {
    'key_length': 32,  # Length of generated API keys
    'expiry_days': 90,  # Number of days until keys expire
    'rate_limit_standard': 60,  # Requests per minute for standard clients
    'rate_limit_premium': 300,  # Requests per minute for premium clients
    'premium_client_percentage': 0.2  # Percentage of clients with premium rate limits
}


def get_output_directory(custom_dir=None):
    """
    Returns the output directory for generated data files.

    Args:
        custom_dir (str, optional): Custom output directory. Defaults to None.

    Returns:
        str: Path to the output directory
    """
    output_dir = os.path.abspath(custom_dir if custom_dir else DEFAULT_OUTPUT_DIR)
    
    # Create the directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    return output_dir


def get_scenario_config(scenario_name):
    """
    Returns the configuration for a specific test scenario.

    Args:
        scenario_name (str): Name of the scenario

    Returns:
        dict: Configuration dictionary for the specified scenario

    Raises:
        ValueError: If the scenario name is not found and no default is available
    """
    if scenario_name in TEST_SCENARIOS:
        return TEST_SCENARIOS[scenario_name]
    elif 'normal_market' in TEST_SCENARIOS:
        # Fall back to normal_market if the specified scenario doesn't exist
        return TEST_SCENARIOS['normal_market']
    else:
        raise ValueError(f"Scenario '{scenario_name}' not found and no default scenario is available")


def load_config_from_file(file_path):
    """
    Loads configuration from a JSON or YAML file.

    Args:
        file_path (str): Path to the configuration file

    Returns:
        dict: Configuration dictionary loaded from the file

    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If the file format is not supported
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    # Determine file type and load accordingly
    if file_path.suffix.lower() == '.json':
        with open(file_path, 'r') as f:
            return json.load(f)
    elif file_path.suffix.lower() in ['.yaml', '.yml']:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}. Supported formats: .json, .yaml, .yml")


def merge_configs(default_config, custom_config):
    """
    Merges a custom configuration with the default configuration.

    Args:
        default_config (dict): Default configuration dictionary
        custom_config (dict): Custom configuration dictionary to merge

    Returns:
        dict: Merged configuration dictionary
    """
    # Create a deep copy of the default config
    merged = default_config.copy()
    
    # Update with custom config values
    for key, value in custom_config.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            # Recursively merge nested dictionaries
            merged[key] = merge_configs(merged[key], value)
        else:
            # Replace or add the value
            merged[key] = value
    
    return merged


def validate_scenario_config(scenario_config):
    """
    Validates that a scenario configuration has all required fields.

    Args:
        scenario_config (dict): Scenario configuration to validate

    Returns:
        bool: True if the configuration is valid, False otherwise
    """
    required_fields = [
        'description',
        'volatility_range',
        'etb_percentage',
        'htb_percentage',
        'event_probability'
    ]
    
    # Check for required fields
    for field in required_fields:
        if field not in scenario_config:
            return False
    
    # Validate percentage fields
    for field in ['etb_percentage', 'htb_percentage', 'event_probability']:
        value = scenario_config[field]
        if not isinstance(value, (int, float)) or value < 0 or value > 1:
            return False
    
    # Validate volatility range
    vol_range = scenario_config['volatility_range']
    if not isinstance(vol_range, (list, tuple)) or len(vol_range) != 2:
        return False
    
    if vol_range[0] > vol_range[1]:
        return False
    
    return True


def get_config_value(config, key, default_value=None):
    """
    Gets a configuration value with fallback to default if not found.

    Args:
        config (dict): Configuration dictionary
        key (str): Key to look up
        default_value: Default value to return if key is not found

    Returns:
        The configuration value or default value
    """
    return config.get(key, default_value)