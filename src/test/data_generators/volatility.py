"""
Module for generating synthetic volatility data for testing the Borrow Rate & Locate Fee Pricing Engine.

This module provides functions to create realistic test volatility metrics with configurable
parameters based on different market scenarios to support comprehensive testing of
volatility-adjusted borrow rate calculations.
"""

import random
import datetime
import os
import json
import csv
import pandas as pd
from decimal import Decimal
from typing import List, Dict, Any, Optional, Union

from .config import (
    VOLATILITY_GENERATION_CONFIG,
    get_output_directory,
    get_scenario_config
)
from ...backend.services.calculation.volatility import get_volatility_tier

# Default number of volatility records to generate per stock
DEFAULT_VOLATILITY_COUNT = 30

# Volatility tiers as defined in the system
VOLATILITY_TIERS = ['LOW', 'NORMAL', 'HIGH', 'EXTREME']


def generate_volatility_data(
    stocks: List[Dict[str, Any]],
    scenario: str = 'normal_market',
    output_format: Optional[str] = None,
    output_file: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generates synthetic volatility data for a list of stocks based on scenario configuration.
    
    Args:
        stocks: List of stock dictionaries, each containing at least a 'ticker' key
        scenario: Name of the scenario to use (e.g., 'normal_market', 'high_volatility')
        output_format: Optional format to save the data (json, csv, sql)
        output_file: Optional filename to save the data
        
    Returns:
        List of generated volatility data records
    """
    # Get volatility generation configuration
    generation_config = VOLATILITY_GENERATION_CONFIG.copy()
    
    # Get scenario-specific configuration
    scenario_config = get_scenario_config(scenario)
    
    # List to store all generated volatility data
    all_volatility_data = []
    
    # Generate volatility data for each stock
    for stock in stocks:
        volatility_records = generate_stock_volatility(stock, scenario_config, generation_config)
        all_volatility_data.extend(volatility_records)
    
    # Save to file if output format is specified
    if output_format and output_file:
        save_volatility_to_file(all_volatility_data, output_format, output_file)
    
    return all_volatility_data


def generate_stock_volatility(
    stock: Dict[str, Any],
    scenario_config: Dict[str, Any],
    generation_config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Generates volatility history for a specific stock.
    
    Args:
        stock: Stock dictionary containing at least a 'ticker' key
        scenario_config: Scenario-specific configuration
        generation_config: General volatility generation configuration
        
    Returns:
        List of volatility records for the stock
    """
    ticker = stock['ticker']
    days_of_history = generation_config.get('days_of_history', DEFAULT_VOLATILITY_COUNT)
    
    # Get scenario-specific volatility range
    volatility_range = scenario_config.get('volatility_range', [
        generation_config['min_vol_index'],
        generation_config['max_vol_index']
    ])
    
    # Get probability of a stock having an event
    event_probability = scenario_config.get('event_probability', 
                                          generation_config['default_event_probability'])
    
    # List to store volatility records for this stock
    volatility_records = []
    
    # Generate volatility data for each day
    for day_offset in range(days_of_history):
        # Calculate the date
        date = datetime.datetime.now() - datetime.timedelta(days=day_offset)
        
        # Generate volatility index
        vol_index = generate_volatility_index(volatility_range)
        
        # Determine if this stock has an event on this day
        has_event = random.random() < event_probability
        
        # Generate event risk factor if applicable
        event_risk_factor = generate_event_risk_factor(generation_config) if has_event else 0
        
        # Create volatility record
        volatility_record = {
            'stock_id': ticker,
            'vol_index': float(vol_index),
            'event_risk_factor': event_risk_factor,
            'timestamp': date.isoformat()
        }
        
        volatility_records.append(volatility_record)
    
    return volatility_records


def generate_volatility_index(volatility_range: List[float]) -> Decimal:
    """
    Generates a random volatility index within the specified range.
    
    Args:
        volatility_range: List containing [min, max] volatility values
        
    Returns:
        Generated volatility index
    """
    min_vol, max_vol = volatility_range
    # Generate a random value within the range
    random_vol = random.uniform(min_vol, max_vol)
    # Convert to string first, then to Decimal, and round to 2 decimal places
    return Decimal(str(random_vol)).quantize(Decimal('0.01'))


def generate_event_risk_factor(generation_config: Dict[str, Any]) -> int:
    """
    Generates a random event risk factor for a stock.
    
    Args:
        generation_config: Volatility generation configuration
        
    Returns:
        Generated event risk factor (1-10)
    """
    min_risk = generation_config.get('min_event_risk_factor', 1)
    max_risk = generation_config.get('max_event_risk_factor', 10)
    return random.randint(min_risk, max_risk)


def save_volatility_to_file(
    volatility_data: List[Dict[str, Any]],
    output_format: str,
    output_file: str
) -> str:
    """
    Saves generated volatility data to a file in the specified format.
    
    Args:
        volatility_data: List of volatility data records
        output_format: Format to save the data (json, csv, sql)
        output_file: Filename to save the data
        
    Returns:
        Path to the saved file
    """
    output_dir = get_output_directory()
    file_path = os.path.join(output_dir, output_file)
    
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    if output_format.lower() == 'json':
        with open(file_path, 'w') as f:
            json.dump(volatility_data, f, indent=2)
            
    elif output_format.lower() == 'csv':
        # Convert to DataFrame for easy CSV export
        df = pd.DataFrame(volatility_data)
        df.to_csv(file_path, index=False)
            
    elif output_format.lower() == 'sql':
        sql_statements = generate_sql_insert_statements(volatility_data)
        with open(file_path, 'w') as f:
            f.write(sql_statements)
    
    return file_path


def generate_sql_insert_statements(volatility_data: List[Dict[str, Any]]) -> str:
    """
    Generates SQL INSERT statements for the volatility table.
    
    Args:
        volatility_data: List of volatility data records
        
    Returns:
        SQL INSERT statements for the volatility data
    """
    sql = ""
    
    for record in volatility_data:
        # Format the values according to their types
        stock_id = f"'{record['stock_id']}'"
        vol_index = record['vol_index']
        event_risk_factor = record['event_risk_factor']
        timestamp = f"'{record['timestamp']}'"
        
        # Create INSERT statement
        sql += (f"INSERT INTO Volatility (stock_id, vol_index, event_risk_factor, timestamp) "
                f"VALUES ({stock_id}, {vol_index}, {event_risk_factor}, {timestamp});\n")
    
    return sql


class VolatilityGenerator:
    """
    Class for generating synthetic volatility data with various configurations.
    """
    
    def __init__(self, config: Dict[str, Any], scenario_config: Dict[str, Any]):
        """
        Initializes the VolatilityGenerator with the provided configuration.
        
        Args:
            config: General volatility generation configuration
            scenario_config: Scenario-specific configuration
        """
        self.config = config
        self.scenario_config = scenario_config
    
    def generate_for_stocks(self, stocks: List[Dict[str, Any]], days: int = None) -> List[Dict[str, Any]]:
        """
        Generates volatility data for a list of stocks.
        
        Args:
            stocks: List of stock dictionaries, each containing at least a 'ticker' key
            days: Optional number of days of history to generate, overrides config
            
        Returns:
            List of generated volatility data records
        """
        if days is not None:
            self.config['days_of_history'] = days
            
        all_volatility_data = []
        
        for stock in stocks:
            volatility_records = self.generate_for_stock(stock, days)
            all_volatility_data.extend(volatility_records)
            
        return all_volatility_data
    
    def generate_for_stock(self, stock: Dict[str, Any], days: int = None) -> List[Dict[str, Any]]:
        """
        Generates volatility history for a single stock.
        
        Args:
            stock: Stock dictionary containing at least a 'ticker' key
            days: Optional number of days of history to generate, overrides config
            
        Returns:
            List of volatility records for the stock
        """
        config_copy = self.config.copy()
        if days is not None:
            config_copy['days_of_history'] = days
            
        return generate_stock_volatility(stock, self.scenario_config, config_copy)
    
    def save_to_file(self, volatility_data: List[Dict[str, Any]], output_format: str, output_file: str) -> str:
        """
        Saves generated volatility data to a file.
        
        Args:
            volatility_data: List of volatility data records
            output_format: Format to save the data (json, csv, sql)
            output_file: Filename to save the data
            
        Returns:
            Path to the saved file
        """
        return save_volatility_to_file(volatility_data, output_format, output_file)