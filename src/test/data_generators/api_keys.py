"""
Module for generating synthetic API keys for testing the Borrow Rate & Locate Fee Pricing Engine.

This module provides functions to create realistic test API keys with various configurations
including key IDs, client associations, rate limits, and expiration dates. These synthetic
API keys can be used for testing authentication, authorization, and rate limiting features.
"""

import random
import string
import datetime
import os
import json
import csv
import pandas as pd  # pandas 2.0.0+
import secrets
import hashlib
from config import API_KEY_GENERATION_CONFIG, get_output_directory

# Default number of API keys to generate
DEFAULT_API_KEY_COUNT = 20

# Character set for generating key IDs
CHARACTERS = string.ascii_letters + string.digits + '_-'

def generate_api_key(length):
    """
    Generates a random API key string with the specified length.
    
    Args:
        length (int): Length of the API key to generate
        
    Returns:
        str: A randomly generated API key string
    """
    # Use secrets.token_urlsafe for a cryptographically strong random string
    # This generates a Base64-encoded string, which we truncate or pad as needed
    raw_key = secrets.token_urlsafe(length)
    
    # Adjust the length if needed
    if len(raw_key) > length:
        return raw_key[:length]
    elif len(raw_key) < length:
        # Pad with random characters if needed
        additional_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=length-len(raw_key)))
        return raw_key + additional_chars
    
    return raw_key

def generate_key_id(existing_ids):
    """
    Generates a unique key ID for an API key.
    
    Args:
        existing_ids (set): Set of existing key IDs to avoid duplicates
        
    Returns:
        str: A unique key ID string
    """
    # Generate a random ID
    key_id = ''.join(random.choices(CHARACTERS, k=16))
    
    # Ensure uniqueness
    if key_id in existing_ids:
        return generate_key_id(existing_ids)  # Recursively generate a new ID
    
    existing_ids.add(key_id)
    return key_id

def hash_api_key(api_key):
    """
    Creates a hash of the API key for storage.
    
    Args:
        api_key (str): The plaintext API key
        
    Returns:
        str: Hashed version of the API key
    """
    # Use SHA-256 for hashing
    hasher = hashlib.sha256()
    hasher.update(api_key.encode('utf-8'))
    return hasher.hexdigest()

def generate_api_keys(brokers, count=DEFAULT_API_KEY_COUNT, output_format=None, output_file=None):
    """
    Generates a list of synthetic API keys based on configuration parameters.
    
    Args:
        brokers (list): List of broker dictionaries with client_id field
        count (int, optional): Number of API keys to generate. Defaults to DEFAULT_API_KEY_COUNT.
        output_format (str, optional): Format to save the data (json, csv, sql). Defaults to None.
        output_file (str, optional): Filename to save the data. Defaults to None.
        
    Returns:
        list: List of generated API key dictionaries
    """
    # Get API key generation configuration
    config = API_KEY_GENERATION_CONFIG
    key_length = config.get('key_length', 32)
    expiry_days = config.get('expiry_days', 90)
    rate_limit_standard = config.get('rate_limit_standard', 60)
    rate_limit_premium = config.get('rate_limit_premium', 300)
    premium_percentage = config.get('premium_client_percentage', 0.2)
    
    # Initialize list for API keys and set for tracking key IDs
    api_keys = []
    existing_ids = set()
    
    # Ensure every broker has at least one API key
    remaining_keys = count - len(brokers)
    if remaining_keys < 0:
        # If we have more brokers than keys, select a random subset of brokers
        selected_brokers = random.sample(brokers, count)
        brokers_to_use = selected_brokers
        remaining_keys = 0
    else:
        brokers_to_use = brokers.copy()
    
    # Generate one key for each broker
    for broker in brokers_to_use:
        client_id = broker['client_id']
        
        # Generate an API key
        key_id = generate_key_id(existing_ids)
        api_key = generate_api_key(key_length)
        hashed_key = hash_api_key(api_key)
        
        # Determine if this is a premium client for rate limit
        is_premium = random.random() < premium_percentage
        rate_limit = rate_limit_premium if is_premium else rate_limit_standard
        
        # Calculate expiration date
        created_at = datetime.datetime.now()
        expires_at = created_at + datetime.timedelta(days=expiry_days)
        
        # Create API key entry
        api_keys.append({
            'key_id': key_id,
            'api_key': api_key,  # Plaintext key (for testing only)
            'hashed_key': hashed_key,  # Stored version
            'client_id': client_id,
            'rate_limit': rate_limit,
            'created_at': created_at.isoformat(),
            'expires_at': expires_at.isoformat(),
            'active': True
        })
    
    # Distribute remaining API keys randomly among brokers
    if remaining_keys > 0 and brokers:
        for _ in range(remaining_keys):
            # Select a random broker
            broker = random.choice(brokers)
            client_id = broker['client_id']
            
            # Generate an API key
            key_id = generate_key_id(existing_ids)
            api_key = generate_api_key(key_length)
            hashed_key = hash_api_key(api_key)
            
            # Determine if this is a premium client for rate limit
            is_premium = random.random() < premium_percentage
            rate_limit = rate_limit_premium if is_premium else rate_limit_standard
            
            # Calculate expiration date
            created_at = datetime.datetime.now()
            expires_at = created_at + datetime.timedelta(days=expiry_days)
            
            # Create API key entry
            api_keys.append({
                'key_id': key_id,
                'api_key': api_key,  # Plaintext key (for testing only)
                'hashed_key': hashed_key,  # Stored version
                'client_id': client_id,
                'rate_limit': rate_limit,
                'created_at': created_at.isoformat(),
                'expires_at': expires_at.isoformat(),
                'active': True
            })
    
    # Save to file if output format is specified
    if output_format and output_file:
        save_api_keys_to_file(api_keys, output_format, output_file)
    
    return api_keys

def save_api_keys_to_file(api_keys, output_format, output_file):
    """
    Saves generated API key data to a file in the specified format.
    
    Args:
        api_keys (list): List of API key dictionaries
        output_format (str): Format to save the data (json, csv, sql)
        output_file (str): Filename to save the data
        
    Returns:
        str: Path to the saved file
    """
    # Ensure the output directory exists
    output_dir = get_output_directory()
    output_path = os.path.join(output_dir, output_file)
    
    # Save in the specified format
    if output_format.lower() == 'json':
        with open(output_path, 'w') as f:
            json.dump(api_keys, f, indent=2)
    
    elif output_format.lower() == 'csv':
        # Convert to DataFrame for easy CSV export
        df = pd.DataFrame(api_keys)
        df.to_csv(output_path, index=False)
    
    elif output_format.lower() == 'sql':
        # Generate SQL INSERT statements
        sql_statements = generate_sql_insert_statements(api_keys)
        with open(output_path, 'w') as f:
            f.write(sql_statements)
    
    else:
        raise ValueError(f"Unsupported output format: {output_format}. Supported formats: json, csv, sql")
    
    return output_path

def generate_sql_insert_statements(api_keys):
    """
    Generates SQL INSERT statements for the api_keys table.
    
    Args:
        api_keys (list): List of API key dictionaries
        
    Returns:
        str: SQL INSERT statements for the API keys
    """
    sql = "-- API keys SQL insert statements\n\n"
    
    for key in api_keys:
        # Format each value according to its type
        values = []
        for k, v in key.items():
            if isinstance(v, str):
                values.append(f"'{v}'")
            elif isinstance(v, bool):
                values.append('TRUE' if v else 'FALSE')
            elif v is None:
                values.append('NULL')
            else:
                values.append(str(v))
        
        # Create the INSERT statement
        columns = ', '.join(key.keys())
        values_str = ', '.join(values)
        sql += f"INSERT INTO api_keys ({columns}) VALUES ({values_str});\n"
    
    return sql

class APIKeyGenerator:
    """
    Class for generating synthetic API key data with various configurations.
    """
    
    def __init__(self, config=None):
        """
        Initializes the APIKeyGenerator with the provided configuration.
        
        Args:
            config (dict, optional): Configuration overrides. Defaults to None.
        """
        # Use provided config or default from module
        self.config = config or API_KEY_GENERATION_CONFIG
        
        # Set to track generated key IDs
        self.generated_key_ids = set()
    
    def generate_batch(self, brokers, count=DEFAULT_API_KEY_COUNT):
        """
        Generates a batch of synthetic API keys for the provided brokers.
        
        Args:
            brokers (list): List of broker dictionaries with client_id field
            count (int, optional): Number of API keys to generate. Defaults to DEFAULT_API_KEY_COUNT.
            
        Returns:
            list: List of generated API key dictionaries
        """
        api_keys = []
        
        # Ensure every broker has at least one API key
        remaining_keys = count - len(brokers)
        if remaining_keys < 0:
            # If we have more brokers than keys, select a random subset of brokers
            selected_brokers = random.sample(brokers, count)
            brokers_to_use = selected_brokers
            remaining_keys = 0
        else:
            brokers_to_use = brokers.copy()
        
        # Generate one key for each broker
        for broker in brokers_to_use:
            api_keys.append(self.generate_api_key(broker))
        
        # Distribute remaining API keys randomly among brokers
        if remaining_keys > 0 and brokers:
            for _ in range(remaining_keys):
                # Select a random broker
                broker = random.choice(brokers)
                api_keys.append(self.generate_api_key(broker))
        
        return api_keys
    
    def generate_api_key(self, broker):
        """
        Generates a single synthetic API key for a broker.
        
        Args:
            broker (dict): Broker dictionary with client_id field
            
        Returns:
            dict: Dictionary representing an API key
        """
        client_id = broker['client_id']
        key_length = self.config.get('key_length', 32)
        expiry_days = self.config.get('expiry_days', 90)
        rate_limit_standard = self.config.get('rate_limit_standard', 60)
        rate_limit_premium = self.config.get('rate_limit_premium', 300)
        premium_percentage = self.config.get('premium_client_percentage', 0.2)
        
        # Generate key ID and API key
        key_id = generate_key_id(self.generated_key_ids)
        api_key = generate_api_key(key_length)
        hashed_key = hash_api_key(api_key)
        
        # Determine if this is a premium client for rate limit
        is_premium = random.random() < premium_percentage
        rate_limit = rate_limit_premium if is_premium else rate_limit_standard
        
        # Calculate expiration date
        created_at = datetime.datetime.now()
        expires_at = created_at + datetime.timedelta(days=expiry_days)
        
        # Create API key entry
        return {
            'key_id': key_id,
            'api_key': api_key,  # Plaintext key (for testing only)
            'hashed_key': hashed_key,  # Stored version
            'client_id': client_id,
            'rate_limit': rate_limit,
            'created_at': created_at.isoformat(),
            'expires_at': expires_at.isoformat(),
            'active': True
        }
    
    def save_to_file(self, api_keys, output_format, output_file):
        """
        Saves generated API keys to a file.
        
        Args:
            api_keys (list): List of API key dictionaries
            output_format (str): Format to save the data (json, csv, sql)
            output_file (str): Filename to save the data
            
        Returns:
            str: Path to the saved file
        """
        return save_api_keys_to_file(api_keys, output_format, output_file)