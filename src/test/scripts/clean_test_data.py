#!/usr/bin/env python
"""
Script that cleans up test data from the database after test runs for the
Borrow Rate & Locate Fee Pricing Engine. This script provides a way to reset
the database to a clean state, removing test-specific records while preserving
essential reference data.

Usage:
    python clean_test_data.py [--all] [--stocks] [--brokers] [--volatility] 
                             [--api-keys] [--audit-logs] [--older-than DAYS]
                             [--environment ENVIRONMENT]

Options:
    --all                  Remove all data including defaults
    --stocks               Clean stock-related test data
    --brokers              Clean broker-related test data
    --volatility           Clean volatility test data
    --api-keys             Clean API key test data
    --audit-logs           Clean audit logs
    --older-than DAYS      Only clean audit logs older than DAYS days
    --environment ENV      Target environment (development, staging, production)
"""

import argparse
import logging
import sys
import os
import datetime
from sqlalchemy import delete  # sqlalchemy 2.0.0+

# Import internal modules
from src.backend.utils.logging import setup_logger, log_exceptions
from src.backend.config.settings import get_settings
from src.backend.db.session import get_db
from src.backend.db.models.stock import Stock
from src.backend.db.models.broker import Broker
from src.backend.db.models.volatility import Volatility
from src.backend.db.models.api_key import APIKey
from src.backend.db.models.audit import AuditLog
from src.backend.scripts.seed_data import DEFAULT_STOCKS, DEFAULT_BROKERS

# Set up logger
logger = setup_logger('scripts.clean_test_data', logging.INFO)

# Create lists of default tickers and client IDs for reference
DEFAULT_TICKERS = [stock['ticker'] for stock in DEFAULT_STOCKS]
DEFAULT_CLIENT_IDS = [broker['client_id'] for broker in DEFAULT_BROKERS]

def parse_args():
    """
    Parse command line arguments for the script
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Clean test data from the database for Borrow Rate & Locate Fee Pricing Engine"
    )
    parser.add_argument(
        "--all", 
        action="store_true", 
        help="Remove all data including defaults"
    )
    parser.add_argument(
        "--stocks", 
        action="store_true", 
        help="Clean stock-related test data"
    )
    parser.add_argument(
        "--brokers", 
        action="store_true", 
        help="Clean broker-related test data"
    )
    parser.add_argument(
        "--volatility", 
        action="store_true", 
        help="Clean volatility test data"
    )
    parser.add_argument(
        "--api-keys", 
        action="store_true", 
        help="Clean API key test data"
    )
    parser.add_argument(
        "--audit-logs", 
        action="store_true", 
        help="Clean audit logs"
    )
    parser.add_argument(
        "--older-than", 
        type=int,
        default=30,
        help="Only clean audit logs older than specified days (default: 30)"
    )
    parser.add_argument(
        "--environment", 
        type=str,
        default="development",
        choices=["development", "staging", "production"],
        help="Target environment (default: development)"
    )
    
    return parser.parse_args()

@log_exceptions(logger)
def clean_stocks(session, remove_all=False):
    """
    Clean stock test data from the database
    
    Args:
        session: SQLAlchemy session
        remove_all: bool
        
    Returns:
        int: Number of stocks removed
    """
    logger.info("Cleaning stocks table...")
    
    if remove_all:
        # Delete all stocks
        result = session.query(Stock).delete()
        logger.info(f"Removed all {result} stocks from database")
    else:
        # Delete only test stocks (those not in DEFAULT_TICKERS)
        result = session.query(Stock).filter(Stock.ticker.notin_(DEFAULT_TICKERS)).delete(synchronize_session='fetch')
        logger.info(f"Removed {result} test stocks from database (preserved default stocks)")
    
    return result

@log_exceptions(logger)
def clean_brokers(session, remove_all=False):
    """
    Clean broker test data from the database
    
    Args:
        session: SQLAlchemy session
        remove_all: bool
        
    Returns:
        int: Number of brokers removed
    """
    logger.info("Cleaning brokers table...")
    
    if remove_all:
        # Delete all brokers
        result = session.query(Broker).delete()
        logger.info(f"Removed all {result} brokers from database")
    else:
        # Delete only test brokers (those not in DEFAULT_CLIENT_IDS)
        result = session.query(Broker).filter(Broker.client_id.notin_(DEFAULT_CLIENT_IDS)).delete(synchronize_session='fetch')
        logger.info(f"Removed {result} test brokers from database (preserved default brokers)")
    
    return result

@log_exceptions(logger)
def clean_volatility(session, remove_all=False):
    """
    Clean volatility test data from the database
    
    Args:
        session: SQLAlchemy session
        remove_all: bool
        
    Returns:
        int: Number of volatility records removed
    """
    logger.info("Cleaning volatility table...")
    
    if remove_all:
        # Delete all volatility records
        result = session.query(Volatility).delete()
        logger.info(f"Removed all {result} volatility records from database")
    else:
        # Delete volatility records for non-default stocks
        result = session.query(Volatility).filter(Volatility.stock_id.notin_(DEFAULT_TICKERS)).delete(synchronize_session='fetch')
        logger.info(f"Removed {result} test volatility records from database (preserved records for default stocks)")
    
    return result

@log_exceptions(logger)
def clean_api_keys(session, remove_all=False):
    """
    Clean API key test data from the database
    
    Args:
        session: SQLAlchemy session
        remove_all: bool
        
    Returns:
        int: Number of API keys removed
    """
    logger.info("Cleaning API keys table...")
    
    if remove_all:
        # Delete all API keys
        result = session.query(APIKey).delete()
        logger.info(f"Removed all {result} API keys from database")
    else:
        # Delete API keys for non-default brokers
        result = session.query(APIKey).filter(APIKey.client_id.notin_(DEFAULT_CLIENT_IDS)).delete(synchronize_session='fetch')
        logger.info(f"Removed {result} test API keys from database (preserved keys for default brokers)")
    
    return result

@log_exceptions(logger)
def clean_audit_logs(session, older_than=30):
    """
    Clean audit log test data from the database
    
    Args:
        session: SQLAlchemy session
        older_than: int
        
    Returns:
        int: Number of audit logs removed
    """
    logger.info(f"Cleaning audit logs older than {older_than} days...")
    
    # Calculate cutoff date
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=older_than)
    
    # Delete audit logs older than cutoff date
    result = session.query(AuditLog).filter(AuditLog.timestamp < cutoff_date).delete(synchronize_session='fetch')
    logger.info(f"Removed {result} audit logs older than {cutoff_date}")
    
    return result

def main():
    """
    Main function to execute the database cleaning process
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    args = parse_args()
    logger.info(f"Starting database cleanup with args: {args}")
    
    try:
        # Verify environment to prevent accidental production cleanup
        if args.environment == "production":
            logger.warning("WARNING: Cleaning test data from PRODUCTION environment!")
            confirmation = input("Are you sure you want to continue? (yes/no): ")
            if confirmation.lower() != "yes":
                logger.info("Cleanup aborted by user")
                return 0
        
        # Get database session
        with get_db() as session:
            # Set up default flag state if no specific flags were provided
            # If no flags are specified, clean everything except defaults
            clean_all = not any([args.stocks, args.brokers, args.volatility, args.api_keys, args.audit_logs])
            
            # Override with --all flag if specified
            remove_all = args.all
            
            # Clean stocks
            if args.stocks or clean_all:
                clean_stocks(session, remove_all)
            
            # Clean brokers
            if args.brokers or clean_all:
                clean_brokers(session, remove_all)
            
            # Clean volatility data
            if args.volatility or clean_all:
                clean_volatility(session, remove_all)
            
            # Clean API keys
            if args.api_keys or clean_all:
                clean_api_keys(session, remove_all)
            
            # Clean audit logs
            if args.audit_logs or clean_all:
                clean_audit_logs(session, args.older_than)
            
            # Commit the session to save all changes
            session.commit()
            
            logger.info("Database cleanup completed successfully!")
        
        return 0  # Success exit code
    except Exception as e:
        logger.error(f"Error cleaning database: {e}")
        return 1  # Error exit code

if __name__ == '__main__':
    sys.exit(main())