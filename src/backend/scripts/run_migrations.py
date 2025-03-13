#!/usr/bin/env python
"""
Database migration script for the Borrow Rate & Locate Fee Pricing Engine.

This script provides a command-line interface to run Alembic database migrations
with proper error handling and logging. It supports both online and offline migration
modes and can be used in different deployment environments.

Usage:
    python run_migrations.py [options]

Options:
    --offline         Run migrations in offline mode without database connection
    --revision TEXT   Target revision (use 'head' for latest, '-1' for previous)
    --sql             Output SQL for migration instead of executing
    --message TEXT    Message for new migration (required with --autogenerate)
    --autogenerate    Automatically generate migration based on model changes
"""

import argparse
import sys
import logging
from alembic.config import Config
from alembic import command

# Internal imports
from ..db.migrations.env import run_migrations_online, run_migrations_offline
from ..config.settings import get_settings
from ..utils.logging import setup_logger, log_exceptions
from ..core.exceptions import ExternalAPIException

# Set up logger for migration operations
logger = setup_logger('scripts.run_migrations', logging.INFO)

def parse_args():
    """
    Parse command-line arguments for migration options.
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Run database migrations for the Borrow Rate & Locate Fee Pricing Engine"
    )
    
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run migrations in offline mode (without database connection)"
    )
    
    parser.add_argument(
        "--revision",
        type=str,
        help="Target revision (use 'head' for latest, or specific revision ID)"
    )
    
    parser.add_argument(
        "--sql",
        action="store_true",
        help="Output SQL for migration instead of executing"
    )
    
    parser.add_argument(
        "--message",
        type=str,
        help="Message for new migration (required with --autogenerate)"
    )
    
    parser.add_argument(
        "--autogenerate",
        action="store_true",
        help="Automatically generate migration based on model changes"
    )
    
    return parser.parse_args()

@log_exceptions(logger)
def setup_alembic_config():
    """
    Set up Alembic configuration with proper settings.
    
    Returns:
        alembic.config.Config: Configured Alembic config object
    """
    # Create Alembic config from alembic.ini file
    config = Config("alembic.ini")
    
    # Get database URL from application settings
    settings = get_settings()
    db_url = settings.database_url
    
    # Mask password for logging
    masked_url = db_url.replace('://', '://***:***@') if '://' in db_url else db_url
    logger.info(f"Using database URL: {masked_url}")
    
    # Set the SQLAlchemy URL in the Alembic config
    config.set_main_option("sqlalchemy.url", db_url)
    
    return config

@log_exceptions(logger)
def run_migrations(args):
    """
    Run database migrations based on command-line arguments.
    
    Args:
        args (argparse.Namespace): Parsed command-line arguments
        
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    logger.info("Starting database migration process")
    
    # Set up Alembic configuration
    config = setup_alembic_config()
    
    try:
        # Handle SQL output mode
        if args.sql:
            if not args.revision:
                logger.error("--revision is required with --sql")
                return 1
            
            logger.info(f"Generating SQL for migration to revision {args.revision}")
            command.upgrade(config, args.revision, sql=True)
            return 0
        
        # Handle migration autogeneration
        if args.autogenerate:
            if not args.message:
                logger.error("--message is required with --autogenerate")
                return 1
            
            logger.info(f"Generating migration with message: {args.message}")
            command.revision(config, message=args.message, autogenerate=True)
            return 0
        
        # Handle offline mode
        if args.offline:
            logger.info("Running migrations in offline mode")
            run_migrations_offline()
            return 0
        
        # Handle revision-specific migrations
        if args.revision:
            logger.info(f"Migrating to revision {args.revision}")
            command.upgrade(config, args.revision)
        else:
            # Default: run online migrations to head
            logger.info("Running online migrations to latest revision (head)")
            run_migrations_online()
        
        logger.info("Database migration completed successfully")
        return 0
    except Exception as e:
        logger.error(f"Migration error: {str(e)}", exc_info=True)
        return 1

def main():
    """
    Main entry point for the migration script.
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        args = parse_args()
        return run_migrations(args)
    except ExternalAPIException as e:
        # Handle database connection errors explicitly
        logger.error(f"Database connection error: {str(e)}")
        return 1
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error during migration: {str(e)}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())