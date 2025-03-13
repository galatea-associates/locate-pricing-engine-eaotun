"""
Initialization module for the test data generators package that provides a unified interface for generating synthetic test data for the Borrow Rate & Locate Fee Pricing Engine. This module exposes key functions and classes from the package's submodules to simplify imports for consumers.
"""

# Version of the data generators package
__version__ = "1.0.0"

# List of available data generator types
AVAILABLE_GENERATORS = ['stocks', 'brokers', 'volatility', 'market_data', 'event_data', 'api_keys']

# Internal imports
from .config import (
    TEST_SCENARIOS,
    get_output_directory,
    get_scenario_config,
    load_config_from_file
)

from .stocks import generate_stocks, StockGenerator
from .brokers import generate_brokers, BrokerGenerator
from .volatility import generate_volatility_data, VolatilityGenerator
from .market_data import generate_market_data, MarketDataGenerator
from .event_data import generate_event_data, EventDataGenerator, EVENT_TYPES
from .api_keys import generate_api_keys


def generate_test_data(
    scenario='normal_market', 
    stock_count=100, 
    broker_count=10, 
    output_format=None, 
    output_directory=None
):
    """
    Convenience function to generate all types of test data with a single call
    
    Args:
        scenario (str): Market scenario to use for configuration
        stock_count (int): Number of stocks to generate
        broker_count (int): Number of brokers to generate
        output_format (str, optional): Format to save data (json, csv, sql)
        output_directory (str, optional): Directory to save output files
        
    Returns:
        dict: Dictionary containing all generated test data
    """
    # Get scenario configuration
    scenario_config = get_scenario_config(scenario)
    
    # Generate stocks
    stocks = generate_stocks(
        count=stock_count,
        scenario=scenario,
        output_format=output_format,
        output_file="stocks" if output_format else None
    )
    
    # Generate brokers
    brokers = generate_brokers(
        count=broker_count,
        output_format=output_format,
        output_directory=output_directory
    )
    
    # Generate volatility data
    volatility_data = generate_volatility_data(
        stocks=stocks,
        scenario=scenario,
        output_format=output_format,
        output_file="volatility" if output_format else None
    )
    
    # Generate market data
    market_data = generate_market_data(
        stocks=stocks,
        scenario=scenario,
        output_format=output_format,
        output_file="market_data" if output_format else None
    )
    
    # Generate event data
    event_data = generate_event_data(
        stocks=stocks,
        scenario=scenario,
        output_format=output_format,
        output_file="events" if output_format else None
    )
    
    # Generate API keys
    api_keys = generate_api_keys(
        brokers=brokers,
        output_format=output_format, 
        output_file="api_keys" if output_format else None
    )
    
    # Return all generated data
    return {
        'stocks': stocks,
        'brokers': brokers,
        'volatility_data': volatility_data,
        'market_data': market_data,
        'event_data': event_data,
        'api_keys': api_keys
    }