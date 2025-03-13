"""
Module for generating synthetic market data for testing the Borrow Rate & Locate Fee Pricing Engine.

This module provides functions to create realistic test market data including stock prices,
volumes, and daily changes based on configurable parameters and market scenarios to support
comprehensive testing of the pricing engine.
"""

import random
import datetime
import os
import json
import csv
from decimal import Decimal
from typing import Dict, List, Any, Optional, Union, Tuple

import pandas as pd  # pandas 2.0.0+

from .config import (
    MARKET_DATA_GENERATION_CONFIG,
    get_output_directory,
    get_scenario_config
)

# Default number of days for market data generation
DEFAULT_MARKET_DATA_DAYS = 30

# Price trend factors for different market scenarios
PRICE_TREND_FACTORS = {
    'normal_market': {'mean': 0.0, 'std_dev': 1.0},
    'high_volatility': {'mean': 0.0, 'std_dev': 2.5},
    'corporate_events': {'mean': 0.5, 'std_dev': 1.5},
    'hard_to_borrow': {'mean': -0.5, 'std_dev': 1.2},
    'market_disruption': {'mean': -1.0, 'std_dev': 3.0}
}

# Volume factors for different market scenarios
VOLUME_FACTORS = {
    'normal_market': {'base_multiplier': 1.0, 'volatility': 0.2},
    'high_volatility': {'base_multiplier': 1.5, 'volatility': 0.5},
    'corporate_events': {'base_multiplier': 1.3, 'volatility': 0.4},
    'hard_to_borrow': {'base_multiplier': 0.8, 'volatility': 0.3},
    'market_disruption': {'base_multiplier': 2.0, 'volatility': 0.7}
}


def generate_market_data(
    stocks: List[Dict[str, Any]],
    scenario: str = 'normal_market',
    days: int = None,
    output_format: str = None,
    output_file: str = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generates synthetic market data for a list of stocks based on scenario configuration.
    
    Args:
        stocks: List of stock dictionaries with at least a 'ticker' key
        scenario: Market scenario to use for data generation
        days: Number of days of history to generate (defaults to config value)
        output_format: Format to save the data (json, csv, sql, or None for no save)
        output_file: Name of the output file (without extension)
    
    Returns:
        Dictionary mapping stock tickers to their market data history
    """
    # Get generation configuration
    generation_config = MARKET_DATA_GENERATION_CONFIG
    
    # Get scenario configuration
    scenario_config = get_scenario_config(scenario)
    
    # Default to config days if not specified
    if days is None:
        days = generation_config.get('days_of_history', DEFAULT_MARKET_DATA_DAYS)
    
    # Generate market data for each stock
    market_data = {}
    for stock in stocks:
        ticker = stock['ticker']
        stock_data = generate_stock_market_data(stock, scenario, scenario_config, generation_config, days)
        market_data[ticker] = stock_data
    
    # Save to file if format specified
    if output_format:
        save_market_data_to_file(market_data, output_format, output_file)
    
    return market_data


def generate_stock_market_data(
    stock: Dict[str, Any],
    scenario: str,
    scenario_config: Dict[str, Any],
    generation_config: Dict[str, Any],
    days: int
) -> List[Dict[str, Any]]:
    """
    Generates market data history for a specific stock.
    
    Args:
        stock: Stock dictionary with at least a 'ticker' key
        scenario: Name of the market scenario
        scenario_config: Configuration for the market scenario
        generation_config: General market data generation configuration
        days: Number of days of history to generate
    
    Returns:
        List of market data records for the stock
    """
    ticker = stock['ticker']
    
    # Get price trend factors for this scenario
    trend_factors = PRICE_TREND_FACTORS.get(scenario, PRICE_TREND_FACTORS['normal_market'])
    
    # Get volume factors for this scenario
    volume_factors = VOLUME_FACTORS.get(scenario, VOLUME_FACTORS['normal_market'])
    
    # Generate initial price within the configured range
    min_price = generation_config.get('min_price', 5.0)
    max_price = generation_config.get('max_price', 500.0)
    current_price = Decimal(str(random.uniform(min_price, max_price))).quantize(Decimal('0.01'))
    
    # Generate market data for each day
    market_data = []
    end_date = datetime.datetime.now().date()
    
    for day in range(days, 0, -1):
        # Calculate date
        data_date = end_date - datetime.timedelta(days=day)
        
        # Generate price change
        price_change = generate_price_change(trend_factors, generation_config)
        
        # Apply price change
        price_change_amount = current_price * price_change / Decimal('100')
        new_price = current_price + price_change_amount
        
        # Ensure price doesn't go below a minimum threshold
        if new_price < Decimal('0.1'):
            new_price = Decimal('0.1')
        
        # Round to 2 decimal places
        new_price = new_price.quantize(Decimal('0.01'))
        
        # Generate volume
        volume = generate_trading_volume(volume_factors, generation_config)
        
        # Create market data record
        record = {
            'ticker': ticker,
            'date': data_date.isoformat(),
            'price': float(new_price),
            'change': float(price_change),
            'volume': volume
        }
        
        market_data.append(record)
        
        # Update current price for next day
        current_price = new_price
    
    return market_data


def generate_price_change(
    trend_factors: Dict[str, float],
    generation_config: Dict[str, Any]
) -> Decimal:
    """
    Generates a random daily price change percentage based on scenario factors.
    
    Args:
        trend_factors: Dictionary with 'mean' and 'std_dev' keys
        generation_config: General market data generation configuration
    
    Returns:
        Daily price change percentage as a Decimal
    """
    mean = trend_factors.get('mean', 0.0)
    std_dev = trend_factors.get('std_dev', 1.0)
    
    min_change = generation_config.get('min_daily_change_percentage', -5.0)
    max_change = generation_config.get('max_daily_change_percentage', 5.0)
    
    # Generate random normal value
    random_normal = random.normalvariate(mean, std_dev)
    
    # Scale to fit within min and max change
    scaled_change = min_change + (max_change - min_change) * (
        (random_normal + 3) / 6  # Normalize to ~0-1 range assuming normal dist with 3 std devs
    )
    
    # Convert to Decimal and round to 2 decimal places
    return Decimal(str(scaled_change)).quantize(Decimal('0.01'))


def generate_trading_volume(
    volume_factors: Dict[str, float],
    generation_config: Dict[str, Any]
) -> int:
    """
    Generates a random trading volume based on scenario factors.
    
    Args:
        volume_factors: Dictionary with 'base_multiplier' and 'volatility' keys
        generation_config: General market data generation configuration
    
    Returns:
        Trading volume as an integer
    """
    base_multiplier = volume_factors.get('base_multiplier', 1.0)
    volatility = volume_factors.get('volatility', 0.2)
    
    min_volume = generation_config.get('min_volume', 10000)
    max_volume = generation_config.get('max_volume', 10000000)
    
    # Generate base volume
    base_volume = random.uniform(min_volume, max_volume)
    
    # Apply base multiplier
    base_volume *= base_multiplier
    
    # Apply random volatility factor
    volatility_factor = random.uniform(1 - volatility, 1 + volatility)
    volume = base_volume * volatility_factor
    
    # Round to integer
    return round(volume)


def save_market_data_to_file(
    market_data: Dict[str, List[Dict[str, Any]]],
    output_format: str,
    output_file: str
) -> str:
    """
    Saves generated market data to a file in the specified format.
    
    Args:
        market_data: Dictionary mapping stock tickers to their market data history
        output_format: Output format (json, csv, sql)
        output_file: Base name for the output file (without extension)
    
    Returns:
        Path to the saved file
    """
    # Get output directory
    output_dir = get_output_directory()
    
    # Ensure output filename has appropriate extension
    if not output_file.endswith(f'.{output_format}'):
        output_file = f"{output_file}.{output_format}"
    
    # Construct full output path
    output_path = os.path.join(output_dir, output_file)
    
    # Save in the appropriate format
    if output_format.lower() == 'json':
        with open(output_path, 'w') as f:
            json.dump(market_data, f, indent=2)
    elif output_format.lower() == 'csv':
        # Flatten the hierarchical data for CSV
        flattened_data = flatten_market_data(market_data)
        
        # Convert to DataFrame and save
        df = pd.DataFrame(flattened_data)
        df.to_csv(output_path, index=False)
    elif output_format.lower() == 'sql':
        # Generate SQL INSERT statements
        sql_statements = generate_sql_insert_statements(market_data)
        
        with open(output_path, 'w') as f:
            f.write(sql_statements)
    else:
        raise ValueError(f"Unsupported output format: {output_format}. "
                         f"Supported formats are: json, csv, sql")
    
    return output_path


def generate_sql_insert_statements(market_data: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    Generates SQL INSERT statements for the market_data table.
    
    Args:
        market_data: Dictionary mapping stock tickers to their market data history
    
    Returns:
        SQL INSERT statements as a string
    """
    sql = ""
    
    for ticker, data_points in market_data.items():
        for record in data_points:
            sql += (
                f"INSERT INTO market_data (ticker, data_date, price, price_change, volume) "
                f"VALUES ('{ticker}', '{record['date']}', {record['price']}, "
                f"{record['change']}, {record['volume']});\n"
            )
    
    return sql


def flatten_market_data(market_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Flattens the nested market data structure for CSV export.
    
    Args:
        market_data: Dictionary mapping stock tickers to their market data history
    
    Returns:
        List of flattened market data records
    """
    flattened = []
    
    for ticker, data_points in market_data.items():
        for record in data_points:
            flattened.append({
                'ticker': ticker,
                'date': record['date'],
                'price': record['price'],
                'change': record['change'],
                'volume': record['volume']
            })
    
    return flattened


class MarketDataGenerator:
    """
    Class for generating synthetic market data with various configurations.
    
    This class provides a more object-oriented interface for generating market data
    with persistent configuration and state.
    """
    
    def __init__(self, config: Dict[str, Any] = None, scenario: str = 'normal_market'):
        """
        Initializes the MarketDataGenerator with the provided configuration.
        
        Args:
            config: Market data generation configuration (defaults to MARKET_DATA_GENERATION_CONFIG)
            scenario: Market scenario name
        """
        self.config = config or MARKET_DATA_GENERATION_CONFIG
        self.scenario = scenario
        self.scenario_config = get_scenario_config(scenario)
        self.current_date = datetime.datetime.now()
    
    def generate_for_stocks(self, stocks: List[Dict[str, Any]], days: int = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generates market data for a list of stocks.
        
        Args:
            stocks: List of stock dictionaries with at least a 'ticker' key
            days: Number of days of history to generate (defaults to config value)
        
        Returns:
            Dictionary mapping stock tickers to their market data history
        """
        if days is None:
            days = self.config.get('days_of_history', DEFAULT_MARKET_DATA_DAYS)
        
        market_data = {}
        for stock in stocks:
            ticker = stock['ticker']
            stock_data = self.generate_for_stock(stock, days)
            market_data[ticker] = stock_data
        
        return market_data
    
    def generate_for_stock(self, stock: Dict[str, Any], days: int = None) -> List[Dict[str, Any]]:
        """
        Generates market data history for a single stock.
        
        Args:
            stock: Stock dictionary with at least a 'ticker' key
            days: Number of days of history to generate (defaults to config value)
        
        Returns:
            List of market data records for the stock
        """
        if days is None:
            days = self.config.get('days_of_history', DEFAULT_MARKET_DATA_DAYS)
        
        return generate_stock_market_data(stock, self.scenario, self.scenario_config, self.config, days)
    
    def save_to_file(self, market_data: Dict[str, List[Dict[str, Any]]], 
                     output_format: str, output_file: str) -> str:
        """
        Saves generated market data to a file.
        
        Args:
            market_data: Dictionary mapping stock tickers to their market data history
            output_format: Output format (json, csv, sql)
            output_file: Base name for the output file (without extension)
        
        Returns:
            Path to the saved file
        """
        return save_market_data_to_file(market_data, output_format, output_file)