"""
Alembic environment configuration script for the Borrow Rate & Locate Fee Pricing Engine.

This script connects SQLAlchemy models with database migrations, setting up the migration
environment, providing access to the application's models, and configuring how migrations
are run against the database.
"""

import logging
from alembic import context
from sqlalchemy import engine_from_config, pool, create_engine

# Internal imports
from ...config.settings import get_settings
from ..base import Base
from ...utils.logging import setup_logger

# Set up logger for migration operations
logger = setup_logger('alembic.env')

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use
config = context.config

# Add model's MetaData object for 'autogenerate' support
# This allows Alembic to detect changes in the models automatically
target_metadata = Base.metadata

def get_database_url():
    """
    Retrieves the database URL from application settings.
    
    Returns:
        str: Database connection URL
    """
    settings = get_settings()
    db_url = settings.database_url
    
    # Mask credentials when logging for security
    masked_url = db_url.replace('://', '://***:***@') if '://' in db_url else db_url
    logger.info(f"Using database connection: {masked_url}")
    
    return db_url

def run_migrations_offline():
    """
    Run migrations in 'offline' mode.
    
    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()
    
    logger.info("Offline migrations completed successfully")

def run_migrations_online():
    """
    Run migrations in 'online' mode.
    
    In this scenario we need to create an Engine and associate a connection
    with the context.
    """
    url = get_database_url()
    
    # Create an engine with the application database URL
    engine = create_engine(url)

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Enable comparing column types during migration generation
            compare_type=True,
            # Enable comparing server defaults during migration generation
            compare_server_default=True,
            # Include schemas in the migration
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()
    
    logger.info("Online migrations completed successfully")

# Determine which migration function to execute based on the context mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()