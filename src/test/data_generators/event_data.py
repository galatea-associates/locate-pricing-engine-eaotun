"""
Module for generating synthetic corporate event data for testing the Borrow Rate & Locate Fee Pricing Engine.

This module provides functions to create realistic test event data with configurable parameters
based on different market scenarios to support comprehensive testing of event risk-adjusted
borrow rate calculations.
"""

import random
import datetime
import os
import json
import csv
import pandas as pd
from typing import Dict, List, Optional, Any

from config import (
    EVENT_DATA_GENERATION_CONFIG,
    get_output_directory,
    get_scenario_config,
)

# Default number of days to generate events for
DEFAULT_EVENT_DAYS = 30

# Risk factor ranges for different event types (scale 1-10)
EVENT_RISK_FACTORS = {
    'earnings': {'min': 5, 'max': 10},
    'dividend': {'min': 3, 'max': 7},
    'stock_split': {'min': 4, 'max': 8},
    'merger': {'min': 6, 'max': 10},
    'acquisition': {'min': 6, 'max': 10},
    'regulatory_announcement': {'min': 4, 'max': 9}
}

# Probability modifiers for different scenarios
EVENT_PROBABILITY_MODIFIERS = {
    'normal_market': 1.0,
    'high_volatility': 1.2,
    'corporate_events': 2.5,
    'hard_to_borrow': 1.3,
    'market_disruption': 1.8
}


def generate_events(
    stocks: List[Dict[str, Any]],
    scenario: str = 'normal_market',
    days: int = None,
    output_format: str = None,
    output_file: str = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generates synthetic event data for a list of stocks based on scenario configuration.
    
    Args:
        stocks: List of stock dictionaries containing ticker symbols
        scenario: Market scenario name to use for configuration
        days: Number of days into the future to generate events for
        output_format: Format to save the output (json, csv, sql)
        output_file: Name of the output file
        
    Returns:
        Dictionary mapping stock tickers to their upcoming events
    """
    # Get event data generation configuration
    generation_config = EVENT_DATA_GENERATION_CONFIG
    
    # Get scenario-specific configuration
    scenario_config = get_scenario_config(scenario)
    
    # Set default days if not provided
    if days is None:
        days = DEFAULT_EVENT_DAYS
    
    # Initialize empty dictionary for events
    events = {}
    
    # Generate events for each stock
    for stock in stocks:
        ticker = stock.get('ticker')
        
        # Check if this stock should have events based on probability
        event_probability = scenario_config.get('event_probability', 0.2)
        event_probability_modifier = EVENT_PROBABILITY_MODIFIERS.get(scenario, 1.0)
        final_probability = min(event_probability * event_probability_modifier, 1.0)
        
        if ticker and random.random() < final_probability:
            stock_events = generate_stock_events(stock, scenario_config, generation_config, days)
            if stock_events:
                events[ticker] = stock_events
    
    # Save to file if output format is specified
    if output_format and output_file:
        save_events_to_file(events, output_format, output_file)
    
    return events


def generate_stock_events(
    stock: Dict[str, Any],
    scenario_config: Dict[str, Any],
    generation_config: Dict[str, Any],
    days: int
) -> List[Dict[str, Any]]:
    """
    Generates upcoming events for a specific stock.
    
    Args:
        stock: Dictionary containing stock information
        scenario_config: Configuration for the current scenario
        generation_config: General event generation configuration
        days: Number of days into the future to generate events for
        
    Returns:
        List of event records for the stock
    """
    ticker = stock.get('ticker')
    
    # Extract event probability from scenario configuration
    event_probability = scenario_config.get('event_probability', 0.2)
    
    # Apply scenario-specific probability modifier
    scenario_name = scenario_config.get('name', 'normal_market')
    probability_modifier = EVENT_PROBABILITY_MODIFIERS.get(scenario_name, 1.0)
    adjusted_probability = min(event_probability * probability_modifier, 1.0)
    
    # Determine number of events (0-3 based on probability)
    num_events = 0
    if random.random() < adjusted_probability:
        num_events = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
    
    # Generate the events
    events = []
    for _ in range(num_events):
        # Select random event type
        event_type = generate_event_type(generation_config)
        
        # Generate random date
        event_date = generate_event_date(generation_config, days)
        
        # Generate risk factor
        risk_factor = generate_risk_factor(event_type)
        
        # Create event record
        event = {
            'ticker': ticker,
            'event_type': event_type,
            'date': event_date.isoformat(),
            'risk_factor': risk_factor
        }
        
        events.append(event)
    
    return events


def generate_event_type(generation_config: Dict[str, Any]) -> str:
    """
    Selects a random event type from the available types.
    
    Args:
        generation_config: Event generation configuration
        
    Returns:
        Selected event type
    """
    event_types = generation_config.get('event_types', [
        'earnings', 'dividend', 'stock_split', 'merger', 'acquisition', 'regulatory_announcement'
    ])
    
    return random.choice(event_types)


def generate_event_date(generation_config: Dict[str, Any], max_days: int) -> datetime.date:
    """
    Generates a random future date for an event.
    
    Args:
        generation_config: Event generation configuration
        max_days: Maximum number of days into the future
        
    Returns:
        Generated future date
    """
    min_days = generation_config.get('min_future_days', 1)
    max_future_days = generation_config.get('max_future_days', 30)
    
    # Ensure max_future_days doesn't exceed max_days
    max_future_days = min(max_future_days, max_days)
    
    # Random number of days into the future
    days_ahead = random.randint(min_days, max_future_days)
    
    # Calculate future date
    future_date = datetime.datetime.now().date() + datetime.timedelta(days=days_ahead)
    
    return future_date


def generate_risk_factor(event_type: str) -> int:
    """
    Generates a risk factor based on event type.
    
    Args:
        event_type: Type of event
        
    Returns:
        Generated risk factor (1-10)
    """
    # Get risk factor range for this event type
    risk_range = EVENT_RISK_FACTORS.get(event_type, {'min': 1, 'max': 5})
    
    # Generate random risk factor within range
    risk_factor = random.randint(risk_range['min'], risk_range['max'])
    
    return risk_factor


def save_events_to_file(
    events: Dict[str, List[Dict[str, Any]]],
    output_format: str,
    output_file: str
) -> str:
    """
    Saves generated event data to a file in the specified format.
    
    Args:
        events: Dictionary of generated event data
        output_format: Format to save the data (json, csv, sql)
        output_file: Name of the output file
        
    Returns:
        Path to the saved file
    """
    # Determine the output directory
    output_dir = get_output_directory()
    
    # Construct the full output file path
    if not output_file.endswith(f".{output_format}"):
        output_file = f"{output_file}.{output_format}"
    
    file_path = os.path.join(output_dir, output_file)
    
    # Write the formatted data to the output file
    if output_format.lower() == 'json':
        with open(file_path, 'w') as f:
            json.dump(events, f, indent=2)
    
    elif output_format.lower() == 'csv':
        # Flatten the nested structure for CSV
        flattened_events = flatten_events(events)
        
        if flattened_events:
            df = pd.DataFrame(flattened_events)
            df.to_csv(file_path, index=False)
        else:
            # Create empty CSV with headers
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['ticker', 'event_type', 'date', 'risk_factor'])
    
    elif output_format.lower() == 'sql':
        # Generate SQL INSERT statements
        sql_statements = generate_sql_insert_statements(events)
        
        with open(file_path, 'w') as f:
            f.write(sql_statements)
    
    return file_path


def generate_sql_insert_statements(events: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    Generates SQL INSERT statements for the events table.
    
    Args:
        events: Dictionary of generated event data
        
    Returns:
        SQL INSERT statements for the events data
    """
    sql = "-- Event data SQL INSERT statements\n\n"
    
    for ticker, ticker_events in events.items():
        for event in ticker_events:
            sql += (
                f"INSERT INTO events (ticker, event_type, date, risk_factor) "
                f"VALUES ('{event['ticker']}', '{event['event_type']}', "
                f"'{event['date']}', {event['risk_factor']});\n"
            )
    
    return sql


def flatten_events(events: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Flattens the nested events structure for CSV export.
    
    Args:
        events: Dictionary of generated event data
        
    Returns:
        Flattened list of event records
    """
    flattened = []
    
    for ticker, ticker_events in events.items():
        for event in ticker_events:
            flattened.append(event)
    
    return flattened


class EventGenerator:
    """
    Class for generating synthetic event data with various configurations.
    """
    
    def __init__(self, config: Dict[str, Any], scenario_config: Dict[str, Any]):
        """
        Initializes the EventGenerator with the provided configuration.
        
        Args:
            config: Event generation configuration
            scenario_config: Scenario-specific configuration
        """
        self.config = config
        self.scenario_config = scenario_config
        self.current_date = datetime.datetime.now().date()
    
    def generate_for_stocks(self, stocks: List[Dict[str, Any]], days: int = DEFAULT_EVENT_DAYS) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generates event data for a list of stocks.
        
        Args:
            stocks: List of stock dictionaries
            days: Number of days into the future to generate events for
            
        Returns:
            Dictionary mapping stock tickers to their events
        """
        events = {}
        
        for stock in stocks:
            ticker = stock.get('ticker')
            if ticker:
                stock_events = self.generate_for_stock(stock, days)
                if stock_events:
                    events[ticker] = stock_events
        
        return events
    
    def generate_for_stock(self, stock: Dict[str, Any], days: int = DEFAULT_EVENT_DAYS) -> List[Dict[str, Any]]:
        """
        Generates events for a single stock.
        
        Args:
            stock: Stock dictionary
            days: Number of days into the future to generate events for
            
        Returns:
            List of event records for the stock
        """
        return generate_stock_events(stock, self.scenario_config, self.config, days)
    
    def save_to_file(self, events: Dict[str, List[Dict[str, Any]]], output_format: str, output_file: str) -> str:
        """
        Saves generated event data to a file.
        
        Args:
            events: Dictionary of generated event data
            output_format: Format to save the data
            output_file: Name of the output file
            
        Returns:
            Path to the saved file
        """
        return save_events_to_file(events, output_format, output_file)