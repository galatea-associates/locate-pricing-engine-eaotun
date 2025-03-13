"""
Database session management for the Borrow Rate & Locate Fee Pricing Engine.

This module manages database session creation and connection pooling
for the application. It provides functions to create database engines, 
session factories, and database sessions with appropriate configuration
based on the application settings.
"""

import logging
import time
import contextlib
from typing import Generator, Optional, Dict, Any

from sqlalchemy import create_engine, Engine, event, exc, text
from sqlalchemy.orm import sessionmaker, Session, scoped_session

from ..config.settings import get_settings
from .models.base import Base
from ..utils.logging import setup_logger, log_exceptions
from ..core.exceptions import ExternalAPIException

# Configure module logger
logger = setup_logger("db.session", logging.INFO)

# Global variables for engine and session factory
engine = None
SessionLocal = None


@log_exceptions(logger)
def get_engine() -> Engine:
    """
    Creates or returns an existing SQLAlchemy engine with appropriate connection pooling.
    
    The engine is configured based on the current environment (development, staging, production)
    with appropriate connection pool settings for optimal performance and reliability.
    
    Returns:
        Engine: SQLAlchemy engine instance
    """
    global engine
    
    # Return existing engine if already created
    if engine is not None:
        return engine
    
    # Get database configuration from settings
    settings = get_settings()
    database_url = settings.database_url
    
    # Determine environment-specific pool settings
    if settings.is_production():
        pool_size = 20
        max_overflow = 30
        pool_timeout = 30
    elif settings.is_staging():
        pool_size = 10
        max_overflow = 20
        pool_timeout = 30
    else:  # Development
        pool_size = 5
        max_overflow = 10
        pool_timeout = 30
    
    # Create engine with connection pooling
    engine = create_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_pre_ping=True,  # Check connection before using it
        pool_recycle=3600,   # Recycle connections after 1 hour
        connect_args={"connect_timeout": 10}  # 10 second connection timeout
    )
    
    # Set up event listeners for connection monitoring
    @event.listens_for(engine, "connect")
    def connect(dbapi_connection, connection_record):
        logger.debug("Database connection established")
    
    @event.listens_for(engine, "checkout")
    def checkout(dbapi_connection, connection_record, connection_proxy):
        logger.debug("Database connection checked out")
    
    @event.listens_for(engine, "checkin")
    def checkin(dbapi_connection, connection_record):
        logger.debug("Database connection checked in")
    
    logger.info(f"Database engine created with pool_size={pool_size}, max_overflow={max_overflow}")
    return engine


@log_exceptions(logger)
def get_session_factory() -> sessionmaker:
    """
    Creates or returns a session factory for creating database sessions.
    
    The session factory is configured with appropriate settings for transaction
    management and object expiration.
    
    Returns:
        sessionmaker: SQLAlchemy session factory
    """
    global SessionLocal
    
    # Return existing session factory if already created
    if SessionLocal is not None:
        return SessionLocal
    
    # Create session factory
    engine = get_engine()
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False  # Don't expire objects when transaction commits
    )
    
    logger.info("Database session factory created")
    return SessionLocal


@contextlib.contextmanager
@log_exceptions(logger)
def get_db() -> Generator[Session, None, None]:
    """
    Context manager that provides a database session and handles cleanup.
    
    Creates a new session, handles transaction commit/rollback, and ensures
    proper session closing regardless of exceptions.
    
    Yields:
        Session: Database session that can be used for database operations
    """
    session_factory = get_session_factory()
    session = session_factory()
    
    try:
        logger.debug("Database session started")
        yield session
        session.commit()
        logger.debug("Database session committed")
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        session.rollback()
        logger.debug("Database session rolled back")
        raise
    finally:
        session.close()
        logger.debug("Database session closed")


@log_exceptions(logger)
def create_scoped_session() -> scoped_session:
    """
    Creates a thread-local scoped session for multi-threaded environments.
    
    Thread-local sessions ensure that each thread gets its own session instance,
    which is important for concurrency in multi-threaded applications.
    
    Returns:
        scoped_session: Thread-local session registry
    """
    session_factory = get_session_factory()
    return scoped_session(session_factory)


@log_exceptions(logger)
def init_db() -> None:
    """
    Initializes the database by creating all tables defined in models.
    
    This function should be called during application startup to ensure
    that all required tables exist in the database.
    
    Returns:
        None: Creates database tables as a side effect
    """
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized with all tables")


@log_exceptions(logger)
def close_engine() -> None:
    """
    Closes the database engine and connection pool.
    
    This function should be called during application shutdown to ensure
    that all database connections are properly released.
    
    Returns:
        None: Closes connections as a side effect
    """
    global engine
    if engine is not None:
        engine.dispose()
        engine = None
        logger.info("Database engine and connection pool closed")


@log_exceptions(logger)
def ping_database() -> bool:
    """
    Checks database connectivity by executing a simple query.
    
    This function can be used for health checks to verify that the
    database is accessible.
    
    Returns:
        bool: True if database is accessible, False otherwise
    """
    try:
        engine = get_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connectivity check successful")
        return True
    except exc.DBAPIError as e:
        logger.error(f"Database connectivity check failed: {str(e)}")
        return False


class DatabaseSessionManager:
    """
    Manages database sessions with automatic cleanup and error handling.
    
    This class provides an object-oriented interface for database session
    management, which can be useful in dependency injection scenarios.
    """
    
    def __init__(self):
        """
        Initializes the session manager.
        
        Gets the database engine and session factory for later use.
        """
        self._engine = get_engine()
        self._session_factory = get_session_factory()
    
    def get_session(self):
        """
        Context manager that provides a database session.
        
        Returns:
            contextlib._GeneratorContextManager: Context manager yielding a session
        """
        return get_db()
    
    def close(self):
        """
        Closes the engine and releases all connections.
        
        This method should be called when the manager is no longer needed.
        
        Returns:
            None: Closes connections as a side effect
        """
        close_engine()
        self._engine = None
        self._session_factory = None