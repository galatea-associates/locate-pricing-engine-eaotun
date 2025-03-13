"""
Provides functionality for generating synthetic broker data for testing the
Borrow Rate & Locate Fee Pricing Engine.

This module includes utilities for creating realistic broker configurations with
appropriate markup percentages, transaction fee types, and fee amounts based
on configurable parameters.
"""

import random
import datetime
import json
import csv
import os
from typing import List, Dict, Union, Optional, Any
from decimal import Decimal

from .config import BROKER_GENERATION_CONFIG, get_output_directory
from ...backend.core.constants import TransactionFeeType

# Default number of brokers to generate
DEFAULT_BROKER_COUNT = 10


class BrokerGenerator:
    """
    Class for generating synthetic broker data with configurable parameters.
    
    This class provides methods to create realistic broker configurations with
    appropriate markup percentages, transaction fee types, and fee amounts.
    """
    
    def __init__(self, custom_config: Optional[Dict[str, Any]] = None):
        """
        Initializes the broker generator with default or custom configuration.
        
        Args:
            custom_config: Custom configuration to override defaults.
                Defaults to None.
        """
        # Start with default configuration
        self.config: Dict[str, Any] = BROKER_GENERATION_CONFIG.copy()
        
        # Update with custom configuration if provided
        if custom_config:
            self.config.update(custom_config)
        
        # Initialize random number generator
        self.random_generator: random.Random = random.Random()
    
    def generate_broker(self, index: int) -> Dict[str, Any]:
        """
        Generates a single broker configuration.
        
        Args:
            index: Index number for generating a unique client ID.
            
        Returns:
            Generated broker configuration.
        """
        client_id = self.generate_client_id(index)
        markup_percentage = self.generate_markup_percentage()
        fee_type = self.determine_fee_type()
        transaction_amount = self.generate_transaction_amount(fee_type)
        
        # Generate broker configuration
        broker = {
            "client_id": client_id,
            "markup_percentage": markup_percentage,
            "transaction_fee_type": fee_type.value,
            "transaction_amount": transaction_amount,
            "active": True,
            "last_updated": datetime.datetime.now().isoformat()
        }
        
        return broker
    
    def generate_brokers(self, count: int) -> List[Dict[str, Any]]:
        """
        Generates multiple broker configurations.
        
        Args:
            count: Number of broker configurations to generate.
            
        Returns:
            List of generated broker configurations.
            
        Raises:
            ValueError: If count is not a positive integer.
        """
        if not isinstance(count, int) or count <= 0:
            raise ValueError("Count must be a positive integer")
        
        brokers = []
        for i in range(count):
            broker = self.generate_broker(i + 1)
            brokers.append(broker)
        
        return brokers
    
    def generate_client_id(self, index: int) -> str:
        """
        Generates a unique client ID for a broker.
        
        Args:
            index: Index number for making the ID unique.
            
        Returns:
            Generated client ID.
        """
        # Create client ID using prefix and zero-padded index
        prefix = self.config['client_id_prefix']
        padded_index = str(index).zfill(4)
        client_id = f"{prefix}_{padded_index}"
        
        return client_id
    
    def generate_markup_percentage(self) -> float:
        """
        Generates a random markup percentage within the configured range.
        
        Returns:
            Generated markup percentage.
        """
        min_markup = self.config['min_markup_percentage']
        max_markup = self.config['max_markup_percentage']
        
        markup = self.random_generator.uniform(min_markup, max_markup)
        # Round to 2 decimal places for precision
        markup = round(markup, 2)
        
        return markup
    
    def determine_fee_type(self) -> TransactionFeeType:
        """
        Determines the transaction fee type based on the configured distribution.
        
        Returns:
            Selected transaction fee type.
        """
        # Generate random value between 0 and 1
        random_value = self.random_generator.random()
        
        # Get fee type distribution
        flat_probability = self.config['fee_type_distribution']['FLAT']
        
        # Determine fee type based on probability
        if random_value < flat_probability:
            return TransactionFeeType.FLAT
        else:
            return TransactionFeeType.PERCENTAGE
    
    def generate_transaction_amount(self, fee_type: TransactionFeeType) -> float:
        """
        Generates an appropriate transaction amount based on the fee type.
        
        Args:
            fee_type: Type of transaction fee.
            
        Returns:
            Generated transaction amount.
        """
        if fee_type == TransactionFeeType.FLAT:
            min_amount = self.config['min_transaction_fee_flat']
            max_amount = self.config['max_transaction_fee_flat']
        else:  # PERCENTAGE
            min_amount = self.config['min_transaction_fee_percentage']
            max_amount = self.config['max_transaction_fee_percentage']
        
        amount = self.random_generator.uniform(min_amount, max_amount)
        # Round to 2 decimal places for precision
        amount = round(amount, 2)
        
        return amount


def export_brokers_to_json(brokers: List[Dict[str, Any]], output_directory: str) -> str:
    """
    Exports generated broker data to a JSON file.
    
    Args:
        brokers: List of broker configurations to export.
        output_directory: Directory to save the output file.
        
    Returns:
        Path to the exported JSON file.
    """
    # Ensure output directory exists
    os.makedirs(output_directory, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"brokers_{timestamp}.json"
    filepath = os.path.join(output_directory, filename)
    
    # Convert broker objects to dictionaries if needed
    broker_dicts = []
    for broker in brokers:
        # If broker is already a dict, use it directly
        if isinstance(broker, dict):
            broker_dict = broker
        else:
            # Otherwise, convert to dict if it has attributes
            broker_dict = vars(broker)
        
        broker_dicts.append(broker_dict)
    
    # Write to JSON file
    with open(filepath, 'w') as f:
        json.dump(broker_dicts, f, indent=2)
    
    return filepath


def export_brokers_to_csv(brokers: List[Dict[str, Any]], output_directory: str) -> str:
    """
    Exports generated broker data to a CSV file.
    
    Args:
        brokers: List of broker configurations to export.
        output_directory: Directory to save the output file.
        
    Returns:
        Path to the exported CSV file.
    """
    # Ensure output directory exists
    os.makedirs(output_directory, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"brokers_{timestamp}.csv"
    filepath = os.path.join(output_directory, filename)
    
    # If brokers list is empty, return early
    if not brokers:
        return filepath
    
    # Get field names from first broker
    first_broker = brokers[0]
    if isinstance(first_broker, dict):
        fieldnames = list(first_broker.keys())
    else:
        # Convert to dict if it has attributes
        fieldnames = list(vars(first_broker).keys())
    
    # Write to CSV file
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for broker in brokers:
            # If broker is already a dict, write it directly
            if isinstance(broker, dict):
                writer.writerow(broker)
            else:
                # Otherwise, convert to dict if it has attributes
                writer.writerow(vars(broker))
    
    return filepath


def export_brokers_to_sql(brokers: List[Dict[str, Any]], output_directory: str) -> str:
    """
    Exports generated broker data as SQL insert statements.
    
    Args:
        brokers: List of broker configurations to export.
        output_directory: Directory to save the output file.
        
    Returns:
        Path to the exported SQL file.
    """
    # Ensure output directory exists
    os.makedirs(output_directory, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"brokers_{timestamp}.sql"
    filepath = os.path.join(output_directory, filename)
    
    # Generate SQL statements
    sql_statements = []
    
    # Add table creation statement
    create_table = """
    CREATE TABLE IF NOT EXISTS Brokers (
        client_id VARCHAR(50) PRIMARY KEY,
        markup_percentage DECIMAL(4,2) NOT NULL,
        transaction_fee_type VARCHAR(10) NOT NULL,
        transaction_amount DECIMAL(10,2) NOT NULL,
        active BOOLEAN DEFAULT TRUE,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    sql_statements.append(create_table)
    
    # Generate insert statements for each broker
    for broker in brokers:
        # Convert broker to dict if needed
        if isinstance(broker, dict):
            broker_dict = broker
        else:
            broker_dict = vars(broker)
        
        # Extract broker attributes
        client_id = broker_dict.get('client_id')
        markup_percentage = broker_dict.get('markup_percentage')
        transaction_fee_type = broker_dict.get('transaction_fee_type')
        transaction_amount = broker_dict.get('transaction_amount')
        active = 'TRUE' if broker_dict.get('active', True) else 'FALSE'
        last_updated = broker_dict.get('last_updated')
        
        # Format values for SQL
        insert_stmt = f"""
        INSERT INTO Brokers (client_id, markup_percentage, transaction_fee_type, transaction_amount, active, last_updated)
        VALUES ('{client_id}', {markup_percentage}, '{transaction_fee_type}', {transaction_amount}, {active}, '{last_updated}');
        """
        sql_statements.append(insert_stmt)
    
    # Write SQL statements to file
    with open(filepath, 'w') as f:
        f.write('\n'.join(sql_statements))
    
    return filepath


def generate_brokers(
    count: int = DEFAULT_BROKER_COUNT,
    output_format: Optional[str] = None,
    output_directory: Optional[str] = None,
    custom_config: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Generates a specified number of synthetic broker configurations.
    
    Args:
        count: Number of brokers to generate. Defaults to DEFAULT_BROKER_COUNT.
        output_format: Format for exporting data ('json', 'csv', 'sql').
            Defaults to None (no export).
        output_directory: Directory to save exported data.
            Defaults to None (uses default directory).
        custom_config: Custom configuration overrides.
            Defaults to None.
            
    Returns:
        List of generated broker configurations.
        
    Raises:
        ValueError: If an unsupported output format is specified.
    """
    # Initialize broker generator
    generator = BrokerGenerator(custom_config)
    
    # Generate broker data
    brokers = generator.generate_brokers(count)
    
    # Export data if output format is specified
    if output_format:
        if output_directory is None:
            output_directory = get_output_directory()
            
        if output_format.lower() == 'json':
            export_brokers_to_json(brokers, output_directory)
        elif output_format.lower() == 'csv':
            export_brokers_to_csv(brokers, output_directory)
        elif output_format.lower() == 'sql':
            export_brokers_to_sql(brokers, output_directory)
        else:
            raise ValueError(f"Unsupported output format: {output_format}. "
                             f"Supported formats: json, csv, sql")
    
    return brokers