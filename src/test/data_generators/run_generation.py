#!/usr/bin/env python3
"""
Main script for orchestrating the generation of synthetic test data for the
Borrow Rate & Locate Fee Pricing Engine.

This script coordinates the generation of all data types (stocks, brokers, volatility,
market data, events, API keys) with consistent parameters and relationships between
entities to create comprehensive test datasets for various market scenarios.
"""

import argparse
import os
import sys
import json
import logging
from datetime import datetime

# Internal imports
from .config import (
    TEST_SCENARIOS,
    get_output_directory,
    get_scenario_config,
    load_config_from_file
)
from .stocks import generate_stocks
from .brokers import generate_brokers
from .volatility import generate_volatility_data
from .market_data import generate_market_data
from .event_data import generate_events
from .api_keys import generate_api_keys

# Default values
DEFAULT_STOCK_COUNT = 1000
DEFAULT_BROKER_COUNT = 20
DEFAULT_OUTPUT_FORMAT = 'json'
DEFAULT_SCENARIO = 'normal_market'

# Set up module logger
LOGGER = logging.getLogger(__name__)


def setup_logging(verbosity: int) -> None:
    """
    Configures the logging system for the data generation process.
    
    Args:
        verbosity: An integer indicating the verbosity level (0=WARNING, 1=INFO, 2+=DEBUG)
    """
    # Set log level based on verbosity
    if verbosity == 0:
        log_level = logging.WARNING
    elif verbosity == 1:
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG
    
    # Configure the root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    LOGGER.info(f"Logging configured with level: {logging.getLevelName(log_level)}")


def parse_arguments() -> argparse.Namespace:
    """
    Parses command line arguments for the data generation script.
    
    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Generate synthetic test data for the Borrow Rate & Locate Fee Pricing Engine.'
    )
    
    # Add arguments
    parser.add_argument(
        '--scenario',
        choices=list(TEST_SCENARIOS.keys()),
        default=DEFAULT_SCENARIO,
        help=f'Market scenario to use for data generation (default: {DEFAULT_SCENARIO})'
    )
    
    parser.add_argument(
        '--stock-count',
        type=int,
        default=DEFAULT_STOCK_COUNT,
        help=f'Number of stocks to generate (default: {DEFAULT_STOCK_COUNT})'
    )
    
    parser.add_argument(
        '--broker-count',
        type=int,
        default=DEFAULT_BROKER_COUNT,
        help=f'Number of brokers to generate (default: {DEFAULT_BROKER_COUNT})'
    )
    
    parser.add_argument(
        '--output-format',
        choices=['json', 'csv', 'sql'],
        default=DEFAULT_OUTPUT_FORMAT,
        help=f'Output format for generated data (default: {DEFAULT_OUTPUT_FORMAT})'
    )
    
    parser.add_argument(
        '--output-dir',
        help='Output directory for generated files (default: data/)'
    )
    
    parser.add_argument(
        '--config',
        help='Custom configuration file (JSON or YAML) to override default settings'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Increase verbosity (can be specified multiple times for more verbosity)'
    )
    
    return parser.parse_args()


def load_custom_config(config_file: str) -> dict:
    """
    Loads custom configuration from a file if specified.
    
    Args:
        config_file: Path to the configuration file
        
    Returns:
        Custom configuration dictionary or None if not specified
    """
    if config_file is None:
        return None
    
    try:
        if not os.path.exists(config_file):
            LOGGER.error(f"Configuration file not found: {config_file}")
            return None
        
        config = load_config_from_file(config_file)
        LOGGER.info(f"Loaded custom configuration from {config_file}")
        return config
        
    except Exception as e:
        LOGGER.error(f"Error loading configuration file: {str(e)}")
        return None


def generate_all_data(
    scenario: str,
    stock_count: int,
    broker_count: int,
    output_format: str,
    output_dir: str,
    custom_config: dict = None
) -> dict:
    """
    Orchestrates the generation of all test data types with consistent parameters.
    
    Args:
        scenario: Market scenario to use for data generation
        stock_count: Number of stocks to generate
        broker_count: Number of brokers to generate
        output_format: Output format for generated data
        output_dir: Output directory for generated files
        custom_config: Custom configuration overrides
        
    Returns:
        Dictionary containing paths to all generated data files
    """
    # Get output directory
    output_directory = get_output_directory(output_dir)
    LOGGER.info(f"Using output directory: {output_directory}")
    
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Dictionary to store output file paths
    output_files = {}
    
    # Generate stocks data
    LOGGER.info(f"Generating {stock_count} stocks")
    stock_file = f"stocks_{timestamp}.{output_format}"
    stocks = generate_stocks(
        count=stock_count,
        scenario=scenario,
        output_format=output_format,
        output_file=stock_file
    )
    output_files['stocks'] = os.path.join(output_directory, stock_file)
    LOGGER.info(f"Generated {len(stocks)} stocks")
    
    # Generate brokers data
    LOGGER.info(f"Generating {broker_count} brokers")
    broker_file = f"brokers_{timestamp}.{output_format}"
    brokers = generate_brokers(
        count=broker_count,
        output_format=output_format,
        output_directory=output_directory,
        custom_config=custom_config
    )
    output_files['brokers'] = os.path.join(output_directory, broker_file)
    LOGGER.info(f"Generated {len(brokers)} brokers")
    
    # Generate volatility data for stocks
    LOGGER.info(f"Generating volatility data")
    volatility_file = f"volatility_{timestamp}.{output_format}"
    volatility_data = generate_volatility_data(
        stocks=stocks,
        scenario=scenario,
        output_format=output_format,
        output_file=volatility_file
    )
    output_files['volatility'] = os.path.join(output_directory, volatility_file)
    LOGGER.info(f"Generated volatility data for {len(stocks)} stocks")
    
    # Generate market data for stocks
    LOGGER.info(f"Generating market data")
    market_file = f"market_data_{timestamp}.{output_format}"
    market_data = generate_market_data(
        stocks=stocks,
        scenario=scenario,
        output_format=output_format,
        output_file=market_file
    )
    output_files['market_data'] = os.path.join(output_directory, market_file)
    LOGGER.info(f"Generated market data for {len(stocks)} stocks")
    
    # Generate event data for stocks
    LOGGER.info(f"Generating event data")
    event_file = f"events_{timestamp}.{output_format}"
    events = generate_events(
        stocks=stocks,
        scenario=scenario,
        output_format=output_format,
        output_file=event_file
    )
    output_files['events'] = os.path.join(output_directory, event_file)
    num_stocks_with_events = len(events.keys()) if isinstance(events, dict) else 0
    LOGGER.info(f"Generated events for {num_stocks_with_events} stocks")
    
    # Generate API keys for brokers
    LOGGER.info(f"Generating API keys")
    api_key_file = f"api_keys_{timestamp}.{output_format}"
    api_keys = generate_api_keys(
        brokers=brokers,
        count=broker_count * 2,  # Generate 2 keys per broker on average
        output_format=output_format,
        output_file=api_key_file
    )
    output_files['api_keys'] = os.path.join(output_directory, api_key_file)
    LOGGER.info(f"Generated {len(api_keys)} API keys")
    
    LOGGER.info("Data generation completed successfully")
    return output_files


def save_generation_manifest(output_files: dict, scenario: str, output_dir: str) -> str:
    """
    Saves a manifest file with metadata about the generated data.
    
    Args:
        output_files: Dictionary of output file paths
        scenario: The scenario used for generation
        output_dir: Output directory for the manifest file
        
    Returns:
        Path to the saved manifest file
    """
    # Create manifest data
    manifest = {
        'generation_timestamp': datetime.now().isoformat(),
        'scenario': scenario,
        'files': output_files
    }
    
    # Determine output directory
    output_directory = get_output_directory(output_dir)
    
    # Create manifest filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_file = f"generation_manifest_{timestamp}.json"
    manifest_path = os.path.join(output_directory, manifest_file)
    
    # Write manifest to file
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    LOGGER.info(f"Saved generation manifest to {manifest_path}")
    return manifest_path


def main() -> int:
    """
    Main function that runs the data generation process.
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Set up logging
        setup_logging(args.verbose)
        
        # Load custom configuration if specified
        custom_config = load_custom_config(args.config)
        
        # Generate all data
        output_files = generate_all_data(
            scenario=args.scenario,
            stock_count=args.stock_count,
            broker_count=args.broker_count,
            output_format=args.output_format,
            output_dir=args.output_dir,
            custom_config=custom_config
        )
        
        # Save generation manifest
        save_generation_manifest(output_files, args.scenario, args.output_dir)
        
        LOGGER.info("Data generation completed successfully")
        return 0
        
    except Exception as e:
        LOGGER.exception(f"Error during data generation: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())