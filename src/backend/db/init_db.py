"""
Database initialization module for the Borrow Rate & Locate Fee Pricing Engine.

This module is responsible for creating the database schema, seeding initial reference data,
and providing utilities for database verification and reset operations during development.
It implements the database schema as defined in the technical specifications and ensures
proper initialization of all required tables.
"""

import logging
import sqlalchemy
from sqlalchemy import exc
from sqlalchemy.orm import Session

# Internal imports
from ..config.settings import get_settings
from ..utils.logging import setup_logger, log_exceptions
from .base import Base
from .session import get_engine, get_db
from .models.stock import Stock
from .models.broker import Broker
from ..core.constants import BorrowStatus, TransactionFeeType

# Configure module logger
logger = setup_logger('db.init_db', logging.INFO)


@log_exceptions(logger)
def init_db() -> None:
    """
    Initialize the database by creating all tables defined in models.
    
    This function creates all tables that are mapped to SQLAlchemy models and
    registered with the declarative base. It should be called during application 
    startup to ensure the database schema is properly set up.
    
    Returns:
        None: Creates database tables as a side effect
    """
    logger.info("Initializing database schema...")
    engine = get_engine()
    
    # Create all tables defined in Base.metadata
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized successfully")
    except exc.SQLAlchemyError as e:
        logger.error(f"Failed to initialize database schema: {str(e)}")
        raise


@log_exceptions(logger)
def seed_db() -> None:
    """
    Populate the database with initial reference data.
    
    This function seeds the database with default values for stocks and brokers
    if the respective tables are empty. It ensures that the system has necessary
    reference data for testing and initial operation.
    
    Returns:
        None: Seeds database with initial data as a side effect
    """
    logger.info("Seeding database with initial data...")
    
    with get_db() as db:
        # Seed stocks table if empty
        stock_count = db.query(Stock).count()
        if stock_count == 0:
            logger.info("Seeding stocks table with default values")
            default_stocks = get_default_stocks()
            db.add_all(default_stocks)
            logger.info(f"Added {len(default_stocks)} default stock entries")
        else:
            logger.info(f"Stocks table already contains {stock_count} entries, skipping seed")
        
        # Seed brokers table if empty
        broker_count = db.query(Broker).count()
        if broker_count == 0:
            logger.info("Seeding brokers table with default values")
            default_brokers = get_default_brokers()
            db.add_all(default_brokers)
            logger.info(f"Added {len(default_brokers)} default broker entries")
        else:
            logger.info(f"Brokers table already contains {broker_count} entries, skipping seed")
        
        # Commit the transaction
        db.commit()
    
    logger.info("Database seeding completed")


@log_exceptions(logger)
def verify_db() -> bool:
    """
    Verify that the database schema is correctly set up.
    
    This function checks if all required tables exist in the database and have
    the expected columns. It can be used during application startup to ensure
    database integrity.
    
    Returns:
        bool: True if database schema is valid, False otherwise
    """
    logger.info("Verifying database schema...")
    engine = get_engine()
    inspector = sqlalchemy.inspect(engine)
    
    # Define required tables
    required_tables = ['stocks', 'broker', 'volatility', 'apikey', 'auditlog']
    
    # Check if all required tables exist
    existing_tables = inspector.get_table_names()
    for table in required_tables:
        if table not in existing_tables:
            logger.error(f"Required table '{table}' does not exist in database")
            return False
    
    # Verify key columns in stocks table
    stock_columns = [col['name'] for col in inspector.get_columns('stocks')]
    required_stock_columns = ['ticker', 'borrow_status', 'min_borrow_rate', 'lender_api_id']
    for column in required_stock_columns:
        if column not in stock_columns:
            logger.error(f"Required column '{column}' does not exist in 'stocks' table")
            return False
    
    # Verify key columns in broker table
    broker_columns = [col['name'] for col in inspector.get_columns('broker')]
    required_broker_columns = ['client_id', 'markup_percentage', 'transaction_fee_type', 'transaction_amount']
    for column in required_broker_columns:
        if column not in broker_columns:
            logger.error(f"Required column '{column}' does not exist in 'broker' table")
            return False
    
    logger.info("Database schema verification completed successfully")
    return True


@log_exceptions(logger)
def reset_db() -> None:
    """
    Reset the database by dropping and recreating all tables (for development/testing).
    
    This function drops all tables and recreates them with fresh data. It should
    only be used in development environments for testing purposes. In production,
    it will log a warning and exit without taking action.
    
    Returns:
        None: Resets database as a side effect
    """
    settings = get_settings()
    
    # Only allow reset in development environment
    if not settings.is_development():
        logger.warning("Database reset is only allowed in development environment. Current environment: "
                      f"{settings.environment}. Reset aborted.")
        return
    
    logger.warning("Resetting database - ALL DATA WILL BE LOST!")
    engine = get_engine()
    
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    logger.info("All tables dropped")
    
    # Recreate tables
    Base.metadata.create_all(bind=engine)
    logger.info("Tables recreated")
    
    # Seed with initial data
    seed_db()
    
    logger.info("Database reset completed")


def get_default_stocks() -> list:
    """
    Generate a list of default stock entries for database seeding.
    
    This function creates a list of Stock objects with predefined tickers, borrow statuses,
    and minimum borrow rates to be used as initial seed data.
    
    Returns:
        list: List of Stock objects with default values
    """
    # Define some common stocks with their borrow status
    default_stock_data = [
        # Easy to borrow stocks
        {"ticker": "AAPL", "borrow_status": BorrowStatus.EASY, "min_borrow_rate": 0.25},
        {"ticker": "MSFT", "borrow_status": BorrowStatus.EASY, "min_borrow_rate": 0.25},
        {"ticker": "GOOGL", "borrow_status": BorrowStatus.EASY, "min_borrow_rate": 0.25},
        {"ticker": "AMZN", "borrow_status": BorrowStatus.EASY, "min_borrow_rate": 0.25},
        {"ticker": "FB", "borrow_status": BorrowStatus.EASY, "min_borrow_rate": 0.25},
        
        # Medium difficulty stocks
        {"ticker": "TSLA", "borrow_status": BorrowStatus.MEDIUM, "min_borrow_rate": 0.50},
        {"ticker": "NFLX", "borrow_status": BorrowStatus.MEDIUM, "min_borrow_rate": 0.50},
        {"ticker": "NVDA", "borrow_status": BorrowStatus.MEDIUM, "min_borrow_rate": 0.75},
        {"ticker": "AMD", "borrow_status": BorrowStatus.MEDIUM, "min_borrow_rate": 0.75},
        
        # Hard to borrow stocks
        {"ticker": "GME", "borrow_status": BorrowStatus.HARD, "min_borrow_rate": 5.00},
        {"ticker": "AMC", "borrow_status": BorrowStatus.HARD, "min_borrow_rate": 5.00},
        {"ticker": "BBBY", "borrow_status": BorrowStatus.HARD, "min_borrow_rate": 7.50},
        {"ticker": "MEME", "borrow_status": BorrowStatus.HARD, "min_borrow_rate": 10.00}
    ]
    
    # Create Stock objects from the default data
    default_stocks = [Stock(**data) for data in default_stock_data]
    
    return default_stocks


def get_default_brokers() -> list:
    """
    Generate a list of default broker entries for database seeding.
    
    This function creates a list of Broker objects with predefined client IDs, markup
    percentages, and transaction fee structures to be used as initial seed data.
    
    Returns:
        list: List of Broker objects with default values
    """
    # Define some example broker configurations
    default_broker_data = [
        # Standard broker with flat fee
        {
            "client_id": "standard_broker",
            "markup_percentage": 5.0,
            "transaction_fee_type": TransactionFeeType.FLAT,
            "transaction_amount": 25.0
        },
        # Premium broker with lower markup but percentage fee
        {
            "client_id": "premium_broker",
            "markup_percentage": 3.0,
            "transaction_fee_type": TransactionFeeType.PERCENTAGE,
            "transaction_amount": 0.5
        },
        # Discount broker with high markup but no fee
        {
            "client_id": "discount_broker",
            "markup_percentage": 7.5,
            "transaction_fee_type": TransactionFeeType.FLAT,
            "transaction_amount": 0.0
        },
        # Institutional broker with low markup and percentage fee
        {
            "client_id": "institutional_broker",
            "markup_percentage": 2.0,
            "transaction_fee_type": TransactionFeeType.PERCENTAGE,
            "transaction_amount": 0.25
        }
    ]
    
    # Create Broker objects from the default data
    default_brokers = [Broker(**data) for data in default_broker_data]
    
    return default_brokers