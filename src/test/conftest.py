"""
Provides pytest fixtures and configuration for testing the Borrow Rate & Locate Fee Pricing Engine.
This file defines shared fixtures that can be used across different test types (unit, integration, e2e)
and configures the test environment, database connections, and mock servers.
"""
import pytest  # package_version: 7.4.0+ - Testing framework for fixture definitions
import os  # package_version: standard library - Access environment variables and file path operations
import logging  # package_version: standard library - Logging functionality for test operations
import typing  # package_version: standard library - Type annotations for better code documentation
import subprocess  # package_version: standard library - Start and manage mock server processes
import time  # package_version: standard library - Time-related functions for waiting operations
import requests  # package_version: 2.31.0+ - HTTP client for API interactions during test setup
import sqlalchemy  # package_version: 2.0.0+ - ORM library for database test setup
from fastapi.testclient import TestClient  # package_version: 0.103.0+ - Test client for FastAPI applications

from src.test.e2e_tests.fixtures.environment import TestEnvironmentManager  # src_path: src/test/e2e_tests/fixtures/environment.py - Import environment manager for test setup and teardown
from src.test.integration_tests.fixtures.api_responses import SECLEND_API_RESPONSES  # src_path: src/test/integration_tests/fixtures/api_responses.py - Import mock responses for SecLend API
from src.test.integration_tests.fixtures.api_responses import MARKET_API_RESPONSES  # src_path: src/test/integration_tests/fixtures/api_responses.py - Import mock responses for Market Volatility API
from src.test.integration_tests.fixtures.api_responses import EVENT_API_RESPONSES  # src_path: src/test/integration_tests/fixtures/api_responses.py - Import mock responses for Event Calendar API
from src.test.integration_tests.fixtures.stocks import TEST_STOCKS  # src_path: src/test/integration_tests/fixtures/stocks.py - Import test stock data
from src.test.integration_tests.fixtures.brokers import TEST_BROKERS  # src_path: src/test/integration_tests/fixtures/brokers.py - Import test broker data
from src.test.integration_tests.fixtures.volatility import TEST_VOLATILITY_DATA  # src_path: src/test/integration_tests/fixtures/volatility.py - Import test volatility data
from src.test.mock_servers.seclend_api.app import app as seclend_app  # src_path: src/test/mock_servers/seclend_api/app.py - Import SecLend API mock server application
from src.test.mock_servers.market_api.app import app as market_app  # src_path: src/test/mock_servers/market_api/app.py - Import Market Volatility API mock server application
from src.test.mock_servers.event_api.app import app as event_app  # src_path: src/test/mock_servers/event_api/app.py - Import Event Calendar API mock server application
from src.backend.config.settings import get_settings  # src_path: src/backend/config/settings.py - Import function to get application settings
from src.backend.db.init_db import init_db  # src_path: src/backend/db/init_db.py - Import function to initialize test database
from src.backend.db.init_db import seed_db  # src_path: src/backend/db/init_db.py - Import function to seed test database with initial data
from src.backend.db.session import get_db  # src_path: src/backend/db/session.py - Import context manager for database sessions

# Initialize logger
logger = logging.getLogger(__name__)

# Define mock server ports
MOCK_SERVER_PORTS = {
    'seclend_api': 8001,
    'market_api': 8002,
    'event_api': 8003
}

def pytest_configure(config):
    """
    Pytest hook that runs before test collection to configure the test environment
    """
    # Set up logging configuration for tests
    logger.info("Configuring pytest environment...")

    # Register custom markers for different test types
    config.addinivalue_line("markers", "unit: mark test as a unit test.")
    config.addinivalue_line("markers", "integration: mark test as an integration test.")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test.")

    # Configure test environment variables if needed
    logger.info("Pytest environment configured.")

def pytest_sessionstart(session):
    """
    Pytest hook that runs at the start of the test session
    """
    # Log test session start
    logger.info("Starting test session...")

    # Initialize test database if needed
    settings = get_settings()
    if settings.environment.value == "test":
        logger.info("Initializing test database...")
        init_db()
        seed_db()
        logger.info("Test database initialized.")

    # Perform any global setup required for all tests
    logger.info("Test session setup complete.")

def pytest_sessionfinish(session, exitstatus):
    """
    Pytest hook that runs at the end of the test session
    """
    # Log test session end with exit status
    logger.info(f"Finishing test session with exit status: {exitstatus}")

    # Clean up any global resources
    logger.info("Test session finished.")

def start_mock_servers():
    """
    Starts the mock servers for external APIs
    """
    # Start SecLend API mock server on port 8001
    seclend_port = MOCK_SERVER_PORTS['seclend_api']
    seclend_process = subprocess.Popen(
        ["uvicorn", "src.test.mock_servers.seclend_api.app:app", "--host", "0.0.0.0", "--port", str(seclend_port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    logger.info(f"Started SecLend API mock server on port {seclend_port}, PID: {seclend_process.pid}")

    # Start Market Volatility API mock server on port 8002
    market_port = MOCK_SERVER_PORTS['market_api']
    market_process = subprocess.Popen(
        ["uvicorn", "src.test.mock_servers.market_api.app:app", "--host", "0.0.0.0", "--port", str(market_port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    logger.info(f"Started Market Volatility API mock server on port {market_port}, PID: {market_process.pid}")

    # Start Event Calendar API mock server on port 8003
    event_port = MOCK_SERVER_PORTS['event_api']
    event_process = subprocess.Popen(
        ["uvicorn", "src.test.mock_servers.event_api.app:app", "--host", "0.0.0.0", "--port", str(event_port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    logger.info(f"Started Event Calendar API mock server on port {event_port}, PID: {event_process.pid}")

    # Wait for servers to be ready by checking health endpoints
    seclend_ready = wait_for_server(f"http://localhost:{seclend_port}/health", timeout=10, interval=1)
    market_ready = wait_for_server(f"http://localhost:{market_port}/health", timeout=10, interval=1)
    event_ready = wait_for_server(f"http://localhost:{event_port}/health", timeout=10, interval=1)

    if not all([seclend_ready, market_ready, event_ready]):
        logger.error("One or more mock servers failed to start.")
        # Terminate the processes if they are running
        if seclend_process.poll() is None:
            seclend_process.terminate()
        if market_process.poll() is None:
            market_process.terminate()
        if event_process.poll() is None:
            event_process.terminate()
        raise Exception("One or more mock servers failed to start.")

    # Return dictionary with server processes and port information
    return {
        'seclend_process': seclend_process,
        'market_process': market_process,
        'event_process': event_process,
        'seclend_port': seclend_port,
        'market_port': market_port,
        'event_port': event_port
    }

def stop_mock_servers(mock_servers):
    """
    Stops the running mock servers
    """
    # Terminate each mock server process
    seclend_process = mock_servers.get('seclend_process')
    market_process = mock_servers.get('market_process')
    event_process = mock_servers.get('event_process')

    if seclend_process:
        seclend_process.terminate()
        seclend_process.wait()
        logger.info(f"SecLend API mock server (PID: {seclend_process.pid}) stopped.")

    if market_process:
        market_process.terminate()
        market_process.wait()
        logger.info(f"Market Volatility API mock server (PID: {market_process.pid}) stopped.")

    if event_process:
        event_process.terminate()
        event_process.wait()
        logger.info(f"Event Calendar API mock server (PID: {event_process.pid}) stopped.")

def setup_test_database():
    """
    Sets up a test database with required schema and test data
    """
    # Initialize database schema using init_db()
    init_db()

    # Seed database with test data using seed_db()
    seed_db()

    # Log successful database setup
    logger.info("Test database setup completed.")

def wait_for_server(url, timeout=10, interval=1):
    """
    Waits for a server to be ready by checking its health endpoint
    """
    # Calculate end time based on timeout
    end_time = time.time() + timeout

    # Loop until server responds or timeout occurs
    while time.time() < end_time:
        try:
            # Try to connect to health endpoint
            response = requests.get(url)
            if response.status_code == 200:
                # If successful, return True
                logger.info(f"Server at {url} is ready.")
                return True
        except requests.exceptions.RequestException:
            # If connection fails, wait for interval and retry
            logger.debug(f"Server at {url} not ready yet, waiting {interval} seconds...")
            time.sleep(interval)

    # If timeout occurs, return False
    logger.warning(f"Server at {url} did not become ready within {timeout} seconds.")
    return False

@pytest.fixture(scope="session")
def db_session():
    """
    Pytest fixture that provides a database session for tests
    """
    # Initialize database
    setup_test_database()

    # Get database session
    with get_db() as session:
        yield session

@pytest.fixture(scope="session")
def mock_servers():
    """
    Pytest fixture that provides running mock servers for external APIs
    """
    # Start mock servers
    servers = start_mock_servers()
    yield servers

    # Stop mock servers after tests
    stop_mock_servers(servers)

@pytest.fixture
def seclend_api_client(mock_servers):
    """
    Pytest fixture that provides a test client for the SecLend API mock server
    """
    # Get SecLend API port
    seclend_port = mock_servers['seclend_port']

    # Create test client
    return TestClient(seclend_app, base_url=f"http://localhost:{seclend_port}")

@pytest.fixture
def market_api_client(mock_servers):
    """
    Pytest fixture that provides a test client for the Market Volatility API mock server
    """
    # Get Market Volatility API port
    market_port = mock_servers['market_port']

    # Create test client
    return TestClient(market_app, base_url=f"http://localhost:{market_port}")

@pytest.fixture
def event_api_client(mock_servers):
    """
    Pytest fixture that provides a test client for the Event Calendar API mock server
    """
    # Get Event Calendar API port
    event_port = mock_servers['event_port']

    # Create test client
    return TestClient(event_app, base_url=f"http://localhost:{event_port}")

@pytest.fixture(scope="session")
def test_environment():
    """
    Pytest fixture that provides a configured test environment
    """
    # Create a TestEnvironmentManager instance
    manager = TestEnvironmentManager()

    # Set up the test environment
    config = manager.setup()
    yield config

    # Tear down the test environment
    manager.teardown()

@pytest.fixture
def test_stocks():
    """
    Pytest fixture that provides test stock data
    """
    # Return test stock data
    return TEST_STOCKS

@pytest.fixture
def test_brokers():
    """
    Pytest fixture that provides test broker data
    """
    # Return test broker data
    return TEST_BROKERS

@pytest.fixture
def test_volatility_data():
    """
    Pytest fixture that provides test volatility data
    """
    # Return test volatility data
    return TEST_VOLATILITY_DATA

@pytest.fixture
def api_responses():
    """
    Pytest fixture that provides mock API responses for testing
    """
    # Return mock API responses
    return {
        'seclend': SECLEND_API_RESPONSES,
        'market': MARKET_API_RESPONSES,
        'event': EVENT_API_RESPONSES
    }