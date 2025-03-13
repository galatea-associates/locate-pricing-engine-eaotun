"""
Module for generating synthetic stock data for testing the Borrow Rate & Locate Fee Pricing Engine.

This module provides functions and classes to create realistic test stock data with various
borrow statuses, rates, and characteristics based on configurable parameters and market scenarios.
It supports the creation of data for different test scenarios like normal market conditions,
high volatility markets, and hard-to-borrow situations.
"""

import random
import string
import json
import csv
import os
from datetime import datetime, timedelta
import pandas as pd
from decimal import Decimal

# Internal imports
from .config import STOCK_GENERATION_CONFIG, get_output_directory, get_scenario_config
from ...backend.core.constants import BorrowStatus

# Global constants
STOCK_EXCHANGE_PREFIXES = ['NYSE:', 'NASDAQ:', 'AMEX:']
DEFAULT_STOCK_COUNT = 1000
COMMON_TICKER_PATTERNS = ['[A-Z]{3,4}', '[A-Z]{1,2}[A-Z]{2}', '[A-Z]{2,3}[A-Z]{1}']


def generate_ticker(config):
    """
    Generates a random stock ticker symbol.

    Args:
        config (dict): Configuration dictionary with ticker generation parameters.

    Returns:
        str: A randomly generated ticker symbol.
    """
    min_length = config.get('min_ticker_length', 3)
    max_length = config.get('max_ticker_length', 5)
    length = random.randint(min_length, max_length)
    
    ticker = ''.join(random.choices(string.ascii_uppercase, k=length))
    return ticker


def generate_stocks(count=DEFAULT_STOCK_COUNT, scenario='normal_market', output_format=None, output_file=None):
    """
    Generates a list of synthetic stock data based on configuration parameters and market scenario.

    Args:
        count (int): Number of stocks to generate. Defaults to DEFAULT_STOCK_COUNT.
        scenario (str): Market scenario to use for configuration. Defaults to 'normal_market'.
        output_format (str, optional): Output format ('json', 'csv', 'sql'). Defaults to None.
        output_file (str, optional): Output file name. Defaults to None.

    Returns:
        list: List of generated stock dictionaries.
    """
    config = STOCK_GENERATION_CONFIG
    scenario_config = get_scenario_config(scenario)
    
    # Track generated tickers to ensure uniqueness
    generated_tickers = set()
    stocks = []
    
    for _ in range(count):
        # Generate unique ticker
        ticker = None
        while ticker is None or ticker in generated_tickers:
            ticker = generate_ticker(config)
        generated_tickers.add(ticker)
        
        # Determine borrow status based on scenario configuration
        borrow_status = determine_borrow_status(scenario_config)
        
        # Generate stock attributes
        stock = {
            'ticker': ticker,
            'borrow_status': borrow_status.value,
            'lender_api_id': generate_lender_api_id(ticker),
            'min_borrow_rate': float(generate_min_borrow_rate(borrow_status, config)),
            'last_updated': datetime.now().isoformat()
        }
        
        stocks.append(stock)
    
    # Save to file if output format specified
    if output_format:
        saved_path = save_stocks_to_file(stocks, output_format, output_file)
        print(f"Generated {len(stocks)} stocks and saved to {saved_path}")
    
    return stocks


def determine_borrow_status(scenario_config):
    """
    Determines the borrow status for a stock based on scenario configuration.

    Args:
        scenario_config (dict): Scenario configuration with etb_percentage and htb_percentage.

    Returns:
        BorrowStatus: Determined borrow status (EASY, MEDIUM, or HARD).
    """
    etb_percentage = scenario_config.get('etb_percentage', 0.7)
    htb_percentage = scenario_config.get('htb_percentage', 0.1)
    
    rand_val = random.random()
    if rand_val < etb_percentage:
        return BorrowStatus.EASY
    elif rand_val < (etb_percentage + htb_percentage):
        return BorrowStatus.HARD
    else:
        return BorrowStatus.MEDIUM


def generate_min_borrow_rate(borrow_status, config):
    """
    Generates a minimum borrow rate for a stock based on its borrow status.

    Args:
        borrow_status (BorrowStatus): The borrow status of the stock.
        config (dict): Configuration dictionary with rate ranges.

    Returns:
        Decimal: Minimum borrow rate as a decimal.
    """
    min_rates = config.get('min_borrow_rate', {
        'EASY': 0.01,
        'MEDIUM': 0.05,
        'HARD': 0.15
    })
    
    max_rates = config.get('max_borrow_rate', {
        'EASY': 0.05,
        'MEDIUM': 0.15,
        'HARD': 0.5
    })
    
    min_rate = min_rates.get(borrow_status.value, 0.01)
    max_rate = max_rates.get(borrow_status.value, 0.05)
    
    # Generate a random rate within the range for the given borrow status
    rate = min_rate + random.random() * (max_rate - min_rate)
    
    # Return as a Decimal rounded to 2 decimal places
    return Decimal(str(round(rate, 2)))


def generate_lender_api_id(ticker):
    """
    Generates a unique lender API identifier for a stock.

    Args:
        ticker (str): The stock ticker symbol.

    Returns:
        str: A lender API identifier.
    """
    # Generate a random alphanumeric string
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"LENDER-{ticker}-{random_part}"


def save_stocks_to_file(stocks, output_format, output_file=None):
    """
    Saves generated stock data to a file in the specified format.

    Args:
        stocks (list): List of stock dictionaries to save.
        output_format (str): Format to save in ('json', 'csv', 'sql').
        output_file (str, optional): Output file name. Defaults to None.

    Returns:
        str: Path to the saved file.
    """
    if output_format not in ['json', 'csv', 'sql']:
        raise ValueError(f"Unsupported output format: {output_format}. Supported formats: json, csv, sql")
    
    # Determine output directory and filename
    output_dir = get_output_directory()
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"stocks_{timestamp}.{output_format}"
    
    # Make sure the filename has the correct extension
    if not output_file.endswith(f".{output_format}"):
        output_file = f"{output_file}.{output_format}"
    
    output_path = os.path.join(output_dir, output_file)
    
    # Save in the specified format
    if output_format == 'json':
        with open(output_path, 'w') as f:
            json.dump(stocks, f, indent=2)
    
    elif output_format == 'csv':
        df = pd.DataFrame(stocks)
        df.to_csv(output_path, index=False)
    
    elif output_format == 'sql':
        sql_content = generate_sql_insert_statements(stocks)
        with open(output_path, 'w') as f:
            f.write(sql_content)
    
    return output_path


def generate_sql_insert_statements(stocks):
    """
    Generates SQL INSERT statements for the stocks table.

    Args:
        stocks (list): List of stock dictionaries.

    Returns:
        str: SQL INSERT statements for the stocks.
    """
    sql_statements = []
    
    for stock in stocks:
        # Format values according to their types
        ticker = f"'{stock['ticker']}'"
        borrow_status = f"'{stock['borrow_status']}'"
        lender_api_id = f"'{stock['lender_api_id']}'"
        min_borrow_rate = stock['min_borrow_rate']
        last_updated = f"'{stock['last_updated']}'"
        
        sql = (
            f"INSERT INTO stocks (ticker, borrow_status, lender_api_id, min_borrow_rate, last_updated) "
            f"VALUES ({ticker}, {borrow_status}, {lender_api_id}, {min_borrow_rate}, {last_updated});"
        )
        
        sql_statements.append(sql)
    
    return "\n".join(sql_statements)


class StockGenerator:
    """
    Class for generating synthetic stock data with various configurations.
    
    This class provides methods for generating stocks in batches, with state maintained
    between calls to ensure unique ticker symbols and consistent stock properties.
    """
    
    def __init__(self, config=None, scenario_config=None):
        """
        Initializes the StockGenerator with the provided configuration.
        
        Args:
            config (dict, optional): Stock generation configuration. Defaults to STOCK_GENERATION_CONFIG.
            scenario_config (dict, optional): Scenario configuration. Defaults to 'normal_market' scenario.
        """
        self.config = config or STOCK_GENERATION_CONFIG
        self.scenario_config = scenario_config or get_scenario_config('normal_market')
        self.generated_tickers = set()
    
    def generate_batch(self, count):
        """
        Generates a batch of synthetic stocks.
        
        Args:
            count (int): Number of stocks to generate.
            
        Returns:
            list: List of generated stock dictionaries.
        """
        stocks = []
        for _ in range(count):
            stocks.append(self.generate_stock())
        return stocks
    
    def generate_stock(self):
        """
        Generates a single synthetic stock.
        
        Returns:
            dict: Dictionary representing a stock.
        """
        # Generate unique ticker
        ticker = None
        while ticker is None or ticker in self.generated_tickers:
            ticker = generate_ticker(self.config)
        self.generated_tickers.add(ticker)
        
        # Determine borrow status and generate attributes
        borrow_status = determine_borrow_status(self.scenario_config)
        
        return {
            'ticker': ticker,
            'borrow_status': borrow_status.value,
            'lender_api_id': generate_lender_api_id(ticker),
            'min_borrow_rate': float(generate_min_borrow_rate(borrow_status, self.config)),
            'last_updated': datetime.now().isoformat()
        }
    
    def save_to_file(self, stocks, output_format, output_file=None):
        """
        Saves generated stocks to a file.
        
        Args:
            stocks (list): List of stock dictionaries to save.
            output_format (str): Format to save in ('json', 'csv', 'sql').
            output_file (str, optional): Output file name. Defaults to None.
            
        Returns:
            str: Path to the saved file.
        """
        return save_stocks_to_file(stocks, output_format, output_file)


# For direct invocation
if __name__ == "__main__":
    # Generate 100 stocks with normal market conditions and save as JSON
    generate_stocks(100, "normal_market", "json", "sample_stocks.json")