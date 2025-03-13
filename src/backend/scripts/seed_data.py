#!/usr/bin/env python
"""
Script for seeding the database with initial data for the Borrow Rate & Locate Fee Pricing Engine.

This script populates the database with stocks, brokers, volatility metrics, and API keys
for development, testing, and initial production setup. It provides both realistic and
synthetic data to enable immediate system functionality.

Usage:
    python seed_data.py [--reset] [--real-data] [--sample-size SAMPLE_SIZE] [--environment ENVIRONMENT]

Options:
    --reset                Reset the database before seeding
    --real-data            Fetch real borrow rates from SecLend API
    --sample-size SIZE     Number of stocks to seed (default: 10)
    --environment ENV      Target environment (development, staging, production)
"""

import argparse
import logging
import random
import datetime
from decimal import Decimal
import hashlib
import uuid
from sqlalchemy import exc

# Import internal modules
from ..utils.logging import setup_logger, log_exceptions
from ..config.settings import get_settings
from ..db.session import get_db
from ..db.init_db import init_db
from ..db.models.stock import Stock
from ..db.models.broker import Broker
from ..db.models.volatility import Volatility
from ..db.models.api_key import APIKey
from ..core.constants import BorrowStatus, TransactionFeeType
from ..services.external.seclend_api import get_borrow_rate

# Set up logger
logger = setup_logger('scripts.seed_data', logging.INFO)

# Default stocks data
DEFAULT_STOCKS = [
    {'ticker': 'AAPL', 'borrow_status': BorrowStatus.EASY, 'min_borrow_rate': Decimal('0.0025')},
    {'ticker': 'MSFT', 'borrow_status': BorrowStatus.EASY, 'min_borrow_rate': Decimal('0.0020')},
    {'ticker': 'GOOGL', 'borrow_status': BorrowStatus.EASY, 'min_borrow_rate': Decimal('0.0030')},
    {'ticker': 'AMZN', 'borrow_status': BorrowStatus.EASY, 'min_borrow_rate': Decimal('0.0035')},
    {'ticker': 'TSLA', 'borrow_status': BorrowStatus.MEDIUM, 'min_borrow_rate': Decimal('0.0150')},
    {'ticker': 'GME', 'borrow_status': BorrowStatus.HARD, 'min_borrow_rate': Decimal('0.5000')},
    {'ticker': 'AMC', 'borrow_status': BorrowStatus.HARD, 'min_borrow_rate': Decimal('0.3500')},
    {'ticker': 'BBBY', 'borrow_status': BorrowStatus.MEDIUM, 'min_borrow_rate': Decimal('0.0800')},
    {'ticker': 'META', 'borrow_status': BorrowStatus.EASY, 'min_borrow_rate': Decimal('0.0040')},
    {'ticker': 'NFLX', 'borrow_status': BorrowStatus.EASY, 'min_borrow_rate': Decimal('0.0045')}
]

# Default brokers data
DEFAULT_BROKERS = [
    {'client_id': 'broker_standard', 'markup_percentage': Decimal('5.0'), 'transaction_fee_type': TransactionFeeType.FLAT, 'transaction_amount': Decimal('25.0')},
    {'client_id': 'broker_premium', 'markup_percentage': Decimal('3.5'), 'transaction_fee_type': TransactionFeeType.PERCENTAGE, 'transaction_amount': Decimal('0.5')},
    {'client_id': 'broker_discount', 'markup_percentage': Decimal('2.0'), 'transaction_fee_type': TransactionFeeType.FLAT, 'transaction_amount': Decimal('15.0')},
    {'client_id': 'broker_institutional', 'markup_percentage': Decimal('1.5'), 'transaction_fee_type': TransactionFeeType.PERCENTAGE, 'transaction_amount': Decimal('0.25')}
]


def parse_args():
    """Parse command line arguments for the script"""
    parser = argparse.ArgumentParser(
        description="Seed database with initial data for Borrow Rate & Locate Fee Pricing Engine"
    )
    parser.add_argument(
        "--reset", 
        action="store_true", 
        help="Reset the database before seeding"
    )
    parser.add_argument(
        "--real-data", 
        action="store_true", 
        help="Fetch real borrow rates from SecLend API"
    )
    parser.add_argument(
        "--sample-size", 
        type=int, 
        default=10, 
        help="Number of stocks to seed (default: 10)"
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
def seed_stocks(session, sample_size, use_real_data):
    """Seed the database with stock data"""
    logger.info(f"Starting to seed stocks table with {sample_size} entries")
    
    created_stocks = []
    
    for i, stock_data in enumerate(DEFAULT_STOCKS):
        if i >= sample_size:
            break
            
        stock = Stock(
            ticker=stock_data['ticker'],
            borrow_status=stock_data['borrow_status'],
            min_borrow_rate=stock_data['min_borrow_rate'],
            lender_api_id=f"SL-{stock_data['ticker']}"  # Default lender API ID
        )
        
        # Try to get real borrow rate data if requested
        if use_real_data:
            try:
                logger.info(f"Fetching real borrow rate for {stock.ticker} from SecLend API")
                rate_data = get_borrow_rate(stock.ticker)
                if rate_data and 'rate' in rate_data:
                    stock.min_borrow_rate = Decimal(str(rate_data['rate']))
                    logger.info(f"Updated {stock.ticker} with real borrow rate: {stock.min_borrow_rate}")
            except Exception as e:
                logger.warning(f"Failed to get real borrow rate for {stock.ticker}: {e}")
        
        session.add(stock)
        created_stocks.append(stock)
    
    logger.info(f"Created {len(created_stocks)} stock entries")
    return created_stocks


@log_exceptions(logger)
def seed_brokers(session):
    """Seed the database with broker data"""
    logger.info("Starting to seed brokers table")
    
    created_brokers = []
    
    for broker_data in DEFAULT_BROKERS:
        broker = Broker(
            client_id=broker_data['client_id'],
            markup_percentage=broker_data['markup_percentage'],
            transaction_fee_type=broker_data['transaction_fee_type'],
            transaction_amount=broker_data['transaction_amount'],
            active=True
        )
        
        session.add(broker)
        created_brokers.append(broker)
    
    logger.info(f"Created {len(created_brokers)} broker entries")
    return created_brokers


@log_exceptions(logger)
def seed_volatility(session, stocks):
    """Seed the database with volatility data for stocks"""
    logger.info("Starting to seed volatility data")
    
    count = 0
    current_time = datetime.datetime.now()
    
    for stock in stocks:
        # Generate realistic vol_index based on borrow status
        # More volatile (higher vol_index) for HARD-to-borrow stocks
        if stock.borrow_status == BorrowStatus.HARD:
            vol_index = Decimal(str(random.uniform(25.0, 40.0)))
            event_risk_factor = random.randint(5, 10)
        elif stock.borrow_status == BorrowStatus.MEDIUM:
            vol_index = Decimal(str(random.uniform(15.0, 25.0)))
            event_risk_factor = random.randint(3, 7)
        else:  # EASY
            vol_index = Decimal(str(random.uniform(5.0, 15.0)))
            event_risk_factor = random.randint(0, 4)
        
        volatility = Volatility(
            stock_id=stock.ticker,
            vol_index=vol_index,
            event_risk_factor=event_risk_factor,
            timestamp=current_time
        )
        
        session.add(volatility)
        count += 1
    
    logger.info(f"Created {count} volatility records")
    return count


@log_exceptions(logger)
def seed_api_keys(session, brokers):
    """Seed the database with API keys for brokers"""
    logger.info("Starting to seed API keys for brokers")
    
    broker_keys = {}
    
    for broker in brokers:
        # Generate a unique API key
        api_key, hashed_key = generate_api_key()
        
        # Determine rate limit based on broker type
        rate_limit = 60  # Default rate limit
        if "premium" in broker.client_id:
            rate_limit = 300
        elif "institutional" in broker.client_id:
            rate_limit = 500
        
        api_key_record = APIKey(
            key_id=api_key[:8],  # Use first 8 chars as ID
            client_id=broker.client_id,
            rate_limit=rate_limit,
            active=True,
            hashed_key=hashed_key
        )
        
        session.add(api_key_record)
        broker_keys[broker.client_id] = api_key
    
    logger.info(f"Created {len(broker_keys)} API keys")
    return broker_keys


def generate_api_key():
    """Generate a unique API key and its hash"""
    # Generate a random UUID
    api_key = str(uuid.uuid4()).replace('-', '')
    
    # Create a hash of the API key for storage
    hashed_key = hashlib.sha256(api_key.encode()).hexdigest()
    
    return api_key, hashed_key


def main():
    """Main function to execute the database seeding process"""
    args = parse_args()
    logger.info(f"Starting database seed with args: reset={args.reset}, real_data={args.real_data}, sample_size={args.sample_size}, environment={args.environment}")
    
    try:
        # Reset database if requested
        if args.reset:
            logger.info("Resetting database...")
            init_db()
        
        # Get database session
        with get_db() as session:
            # Seed stocks
            stocks = seed_stocks(session, args.sample_size, args.real_data)
            
            # Seed brokers
            brokers = seed_brokers(session)
            
            # Seed volatility data
            seed_volatility(session, stocks)
            
            # Seed API keys
            api_keys = seed_api_keys(session, brokers)
            
            # Commit the session to save all changes
            session.commit()
            
            logger.info("Database seeding completed successfully!")
            
            # Print API keys for testing
            if args.environment == "development":
                logger.info("Generated API keys for testing:")
                for client_id, key in api_keys.items():
                    logger.info(f"  {client_id}: {key}")
        
        return 0  # Success exit code
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        return 1  # Error exit code


if __name__ == "__main__":
    exit(main())