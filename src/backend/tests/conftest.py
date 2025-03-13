"""
Central pytest configuration file for the Borrow Rate & Locate Fee Pricing Engine test suite.

This file defines fixtures and setup/teardown functions that are shared across all test modules,
including database setup, mock external APIs, and test data fixtures.
"""

import os
import pytest
import tempfile
import sqlalchemy
from sqlalchemy import create_engine
import requests_mock
import redis
import fakeredis

from . import TEST_PACKAGE_VERSION
from .fixtures.stocks import stock_data, easy_to_borrow_stock, hard_to_borrow_stock
from .fixtures.brokers import broker_data, standard_broker, premium_broker
from .fixtures.volatility import volatility_data
from .fixtures.api_responses import (
    mock_seclend_response,
    mock_market_volatility_response,
    mock_event_calendar_response
)
from ..config.settings import get_settings
from ..db.init_db import init_db
from ..db.session import get_db, get_engine
from ..db.models.base import Base

# Global variable to store test database URL
TEST_DB_URL = None

def pytest_configure(config):
    """
    Configure pytest environment before test collection.
    
    Args:
        config: pytest.Config - Configuration object
    
    Returns:
        None: Configures pytest environment as a side effect
    """
    # Set up any environment variables needed for testing
    os.environ.setdefault("ENVIRONMENT", "test")
    
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Register custom markers
    config.addinivalue_line("markers", "slow: mark test as slow")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "api: mark test as API test")
    config.addinivalue_line("markers", "calculation: mark test as calculation test")
    config.addinivalue_line("markers", "db: mark test as database test")


def pytest_addoption(parser):
    """
    Add command-line options to pytest.
    
    Args:
        parser: pytest.Parser - Command-line argument parser
    
    Returns:
        None: Adds command-line options as a side effect
    """
    parser.addoption(
        "--test-db-url",
        action="store",
        default=None,
        help="Database URL for tests (defaults to in-memory SQLite)",
    )
    parser.addoption(
        "--mock-apis",
        action="store_true",
        default=True,
        help="Mock external APIs for testing",
    )
    parser.addoption(
        "--test-env",
        action="store",
        default="test",
        help="Test environment (test, development, etc.)",
    )


def setup_test_db():
    """
    Set up a test database with required schema.
    
    Returns:
        str: Database URL for the test database
    """
    global TEST_DB_URL
    
    # If TEST_DB_URL is already set, return it
    if TEST_DB_URL:
        return TEST_DB_URL
    
    # Create a temporary SQLite database
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_file.close()
    TEST_DB_URL = f"sqlite:///{db_file.name}"
    
    # Create database schema
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    
    return TEST_DB_URL


@pytest.fixture(scope="session")
def test_engine():
    """
    Pytest fixture providing a SQLAlchemy engine for tests.
    
    Returns:
        Engine: SQLAlchemy engine for tests
    """
    # Set up test database
    db_url = setup_test_db()
    
    # Create engine
    engine = create_engine(db_url)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Yield engine to tests
    yield engine
    
    # Clean up after tests
    engine.dispose()


@pytest.fixture
def test_db(test_engine):
    """
    Pytest fixture providing a test database session.
    
    Args:
        test_engine: SQLAlchemy engine from test_engine fixture
    
    Returns:
        Session: SQLAlchemy session for testing
    """
    # Create a fresh session for each test
    from sqlalchemy.orm import Session
    session = Session(test_engine)
    
    # Create tables if they don't exist
    Base.metadata.create_all(test_engine)
    
    # Start a nested transaction
    connection = test_engine.connect()
    transaction = connection.begin()
    
    # Yield session for the test
    yield session
    
    # Rollback the transaction after the test
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_client():
    """
    Pytest fixture providing a test client for API testing.
    
    Returns:
        TestClient: FastAPI test client
    """
    # This import needs to be here to avoid circular imports
    from fastapi.testclient import TestClient
    
    # Import the app - adjust this import based on your actual app location
    from ..api.app import app
    
    # Create and return a test client
    client = TestClient(app)
    return client


@pytest.fixture
def mock_external_apis():
    """
    Pytest fixture providing mocked external API responses.
    
    Returns:
        requests_mock.Mocker: Mock object for configuring API responses
    """
    with requests_mock.Mocker() as m:
        # Get settings for API URLs
        settings = get_settings()
        seclend_base_url = settings.seclend_api.get('base_url', 'https://api.seclend.com')
        volatility_base_url = settings.market_volatility_api.get('base_url', 'https://api.marketvolatility.com')
        events_base_url = settings.event_calendar_api.get('base_url', 'https://api.eventcalendar.com')
        
        # Mock SecLend API for common stocks
        for ticker in ['AAPL', 'MSFT', 'TSLA', 'GME', 'AMC']:
            m.get(
                f"{seclend_base_url}/borrow/{ticker}",
                json=mock_seclend_response(ticker)
            )
        
        # Mock Market Volatility API
        m.get(
            f"{volatility_base_url}/market/volatility/index",
            json=mock_market_volatility_response()
        )
        
        # Mock stock-specific volatility endpoints
        for ticker in ['AAPL', 'MSFT', 'TSLA', 'GME', 'AMC']:
            m.get(
                f"{volatility_base_url}/market/volatility/stock/{ticker}",
                json={"ticker": ticker, "volatility": 20.0, "timestamp": "2023-01-01T00:00:00Z"}
            )
        
        # Mock Event Calendar API
        for ticker in ['AAPL', 'MSFT', 'TSLA', 'GME', 'AMC']:
            m.get(
                f"{events_base_url}/events/{ticker}",
                json=mock_event_calendar_response(ticker)
            )
        
        yield m


@pytest.fixture
def mock_redis():
    """
    Pytest fixture providing a fake Redis implementation for testing.
    
    Returns:
        fakeredis.FakeRedis: Fake Redis instance
    """
    fake_redis = fakeredis.FakeRedis()
    
    # Apply monkeypatch to use fake_redis instead of real Redis
    monkeypatch = pytest.MonkeyPatch()
    
    # Mock Redis client constructor
    def mock_redis_client(*args, **kwargs):
        return fake_redis
    
    monkeypatch.setattr(redis, "Redis", mock_redis_client)
    
    yield fake_redis
    
    # Clean up
    monkeypatch.undo()


@pytest.fixture
def test_settings():
    """
    Pytest fixture providing test-specific application settings.
    
    Returns:
        Settings: Application settings configured for testing
    """
    # Create a monkeypatch object
    monkeypatch = pytest.MonkeyPatch()
    
    # Set environment variables for testing
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL or "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Force reload of settings
    from ..config.settings import reload_settings
    settings = reload_settings()
    
    yield settings
    
    # Clean up
    monkeypatch.undo()