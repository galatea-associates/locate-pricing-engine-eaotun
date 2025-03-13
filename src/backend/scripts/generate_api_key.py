#!/usr/bin/env python
"""
Command-line script for generating API keys for brokers in the Borrow Rate & Locate Fee Pricing Engine.

This script allows administrators to create new API keys for existing brokers,
specifying parameters such as rate limits and expiration periods. It handles
validation, secure key generation, and database storage.
"""

import argparse
import sys
import logging
from typing import Optional

from ..db.crud.api_keys import api_key_crud
from ..db.crud.brokers import broker_crud
from ..db.session import get_db, init_db
from ..schemas.api_key import ApiKeyCreate
from ..core.exceptions import ClientNotFoundException
from ..utils.logging import setup_logger
from ..core.constants import API_KEY_EXPIRY_DAYS

# Set up logger
logger = setup_logger('scripts.generate_api_key', logging.INFO)

def parse_arguments():
    """
    Parse command-line arguments for API key generation.
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Generate a new API key for a broker in the Borrow Rate & Locate Fee Pricing Engine."
    )
    
    parser.add_argument(
        "client_id",
        type=str,
        help="Client ID of the broker to generate an API key for"
    )
    
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=60,
        help="Rate limit in requests per minute (default: 60)"
    )
    
    parser.add_argument(
        "--expiry-days",
        type=int,
        default=API_KEY_EXPIRY_DAYS,
        help=f"Number of days until the key expires (default: {API_KEY_EXPIRY_DAYS})"
    )
    
    return parser.parse_args()

def generate_api_key(client_id: str, rate_limit: int, expiry_days: Optional[int]):
    """
    Generate a new API key for a broker.
    
    Args:
        client_id: Client ID of the broker
        rate_limit: Rate limit in requests per minute
        expiry_days: Number of days until the key expires
        
    Returns:
        tuple: Tuple containing API key model and plaintext key
        
    Raises:
        ClientNotFoundException: If the client_id doesn't exist
    """
    # Get a database session
    with get_db() as db:
        # Verify the broker exists
        if not broker_crud.exists_by_client_id(db, client_id):
            raise ClientNotFoundException(client_id)
        
        # Create API key creation data
        api_key_data = ApiKeyCreate(
            client_id=client_id,
            rate_limit=rate_limit,
            expiry_days=expiry_days
        )
        
        # Generate and store the API key
        db_obj, plaintext_key = api_key_crud.create_api_key(db, api_key_data)
        
        return db_obj, plaintext_key

def main():
    """
    Main function to execute the script.
    
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    try:
        # Parse command-line arguments
        args = parse_arguments()
        
        # Initialize database connection
        init_db()
        
        # Generate the API key
        db_obj, plaintext_key = generate_api_key(
            client_id=args.client_id,
            rate_limit=args.rate_limit,
            expiry_days=args.expiry_days
        )
        
        # Print success message and key information
        print(f"Successfully generated API key for client '{args.client_id}':")
        print(f"API Key: {plaintext_key}")
        print(f"Key ID: {db_obj.key_id}")
        print(f"Rate Limit: {db_obj.rate_limit} requests/minute")
        
        if db_obj.expires_at:
            print(f"Expires At: {db_obj.expires_at.isoformat()}")
        else:
            print("Expires At: Never (no expiration set)")
        
        # Add a warning about key security
        print("\nIMPORTANT: Store this API key securely. It cannot be retrieved later.")
        
        return 0
    
    except ClientNotFoundException as e:
        logger.error(f"Error: {str(e)}")
        print(f"Error: Client with ID '{e.params.get('client_id')}' not found.")
        return 1
    
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())