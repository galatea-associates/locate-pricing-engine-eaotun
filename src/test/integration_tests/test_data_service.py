"""
Integration tests for the data service component of the Borrow Rate & Locate Fee Pricing Engine.
Tests the functionality of stock, broker, and volatility data services, including their interactions with external APIs, caching behavior, and fallback mechanisms.
"""
import pytest  # package_version: 7.4.0+
from decimal import Decimal  # package_version: standard library
from datetime import datetime  # package_version: standard library
import time  # package_version: standard library
from typing import List, Dict  # package_version: standard library

from ..config.settings import get_test_settings  # path: src/test/integration_tests/config/settings.py
from .fixtures.stocks import stock_data, easy_to_borrow_stock, hard_to_borrow_stock, invalid_ticker  # path: src/test/integration_tests/fixtures/stocks.py
from .fixtures.brokers import broker_data, standard_broker, invalid_client_id  # path: src/test/integration_tests/fixtures/brokers.py
from .fixtures.volatility import volatility_data, low_volatility_data, high_volatility_data, market_volatility_data, event_risk_data  # path: src/test/integration_tests/fixtures/volatility.py
from .fixtures.api_responses import SECLEND_API_RESPONSES, MARKET_API_RESPONSES, EVENT_API_RESPONSES  # path: src/test/integration_tests/fixtures/api_responses.py
from .helpers.api_client import APIClient, create_api_client  # path: src/test/integration_tests/helpers/api_client.py
from .helpers.mock_server import SecLendMockServer, MarketApiMockServer, EventApiMockServer, MockServerContext  # path: src/test/integration_tests/helpers/mock_server.py
from src.backend.services.data import stock_service, broker_service, volatility_service  # path: src/backend/services/data/__init__.py
from src.backend.core.exceptions import TickerNotFoundException, ExternalAPIException  # path: src/backend/core/exceptions.py

TEST_TIMEOUT = 30


@pytest.fixture
def setup_mock_servers() -> MockServerContext:
    """Pytest fixture that sets up mock servers for external APIs"""
    seclend_server = SecLendMockServer()
    market_server = MarketApiMockServer()
    event_server = EventApiMockServer()

    # Configure default responses for each mock server
    seclend_server.configure_borrow_rate(ticker="AAPL", rate=0.05)
    market_server.configure_volatility(ticker="AAPL", volatility_index=15.5)
    event_server.configure_event_risk(ticker="AAPL", risk_factor=1)

    return MockServerContext([seclend_server, market_server, event_server])


@pytest.fixture
def api_client() -> APIClient:
    """Pytest fixture that provides an API client for testing"""
    client = create_api_client()
    client.wait_for_api_ready()
    return client


def test_stock_service_get_stock(stock_data: List[Dict],):
    """Test that stock_service.get_stock correctly retrieves stock data"""
    test_stock = stock_data[0]
    ticker = test_stock['ticker']
    stock = stock_service.get_stock(ticker)
    assert stock['ticker'] == ticker

    stock = stock_service.get_stock("INVALID_TICKER")
    assert stock is None


def test_stock_service_exists(easy_to_borrow_stock: Dict, invalid_ticker: str):
    """Test that stock_service.exists correctly checks if a stock exists"""
    assert stock_service.exists(easy_to_borrow_stock['ticker']) is True
    assert stock_service.exists(invalid_ticker) is False


def test_stock_service_get_current_borrow_rate(easy_to_borrow_stock: Dict, setup_mock_servers: MockServerContext):
    """Test that stock_service.get_current_borrow_rate correctly retrieves borrow rates"""
    with setup_mock_servers:
        ticker = easy_to_borrow_stock['ticker']
        borrow_rate_response = stock_service.get_current_borrow_rate(ticker)
        assert borrow_rate_response.current_rate == 0.05
        assert borrow_rate_response.volatility_index == 18.5
        assert borrow_rate_response.event_risk_factor == 2


def test_stock_service_borrow_rate_caching(easy_to_borrow_stock: Dict, setup_mock_servers: MockServerContext):
    """Test that stock_service caches borrow rates correctly"""
    with setup_mock_servers:
        ticker = easy_to_borrow_stock['ticker']
        borrow_rate_response = stock_service.get_current_borrow_rate(ticker, use_cache=True)
        assert borrow_rate_response.current_rate == 0.05

        # Change the mock API configuration to return a different rate
        for server in setup_mock_servers.servers:
            if isinstance(server, SecLendMockServer):
                server.configure_borrow_rate(ticker=ticker, rate=0.10)

        # Call stock_service.get_current_borrow_rate again with use_cache=True
        borrow_rate_response_cached = stock_service.get_current_borrow_rate(ticker, use_cache=True)
        assert borrow_rate_response_cached.current_rate == 0.05

        # Call stock_service.get_current_borrow_rate with use_cache=False
        borrow_rate_response_no_cache = stock_service.get_current_borrow_rate(ticker, use_cache=False)
        assert borrow_rate_response_no_cache.current_rate == 0.05


def test_stock_service_fallback_mechanism(easy_to_borrow_stock: Dict, setup_mock_servers: MockServerContext):
    """Test that stock_service uses fallback mechanisms when external APIs fail"""
    with setup_mock_servers:
        ticker = easy_to_borrow_stock['ticker']

        # Configure mock SecLend API to timeout or return an error
        for server in setup_mock_servers.servers:
            if isinstance(server, SecLendMockServer):
                server.configure_timeout(ticker=ticker, timeout_seconds=1)

        # Call stock_service.get_current_borrow_rate
        borrow_rate_response = stock_service.get_current_borrow_rate(ticker)

        # Assert that it returns a fallback rate based on the stock's min_borrow_rate
        assert borrow_rate_response.current_rate == easy_to_borrow_stock['min_borrow_rate']
        # Assert that the response indicates fallback was used
        assert borrow_rate_response.borrow_status == easy_to_borrow_stock['borrow_status']


def test_broker_service_get_broker(broker_data: List[Dict]):
    """Test that broker_service.get_broker correctly retrieves broker data"""
    test_broker = broker_data[0]
    client_id = test_broker['client_id']
    broker = broker_service.get_broker(client_id)
    assert broker['client_id'] == client_id

    broker = broker_service.get_broker("INVALID_CLIENT_ID")
    assert broker is None


def test_broker_service_exists(standard_broker: Dict, invalid_client_id: str):
    """Test that broker_service.broker_exists correctly checks if a broker exists"""
    assert broker_service.broker_exists(standard_broker['client_id']) is True
    assert broker_service.broker_exists(invalid_client_id) is False


def test_volatility_service_get_volatility(easy_to_borrow_stock: Dict, low_volatility_data: Dict, setup_mock_servers: MockServerContext):
    """Test that volatility_service.get_volatility correctly retrieves volatility data"""
    with setup_mock_servers:
        ticker = easy_to_borrow_stock['ticker']
        for server in setup_mock_servers.servers:
            if isinstance(server, MarketApiMockServer):
                server.configure_volatility(ticker=ticker, volatility_index=low_volatility_data['vol_index'])
        volatility = volatility_service.get_volatility(ticker)
        assert volatility.vol_index == low_volatility_data['vol_index']


def test_volatility_service_get_market_volatility(market_volatility_data: Dict, setup_mock_servers: MockServerContext):
    """Test that volatility_service.get_market_volatility correctly retrieves market volatility"""
    with setup_mock_servers:
        for server in setup_mock_servers.servers:
            if isinstance(server, MarketApiMockServer):
                server.configure_market_volatility(volatility_index=market_volatility_data['value'])
        market_volatility = volatility_service.get_market_volatility()
        assert market_volatility == market_volatility_data['value']


def test_volatility_service_get_event_risk(easy_to_borrow_stock: Dict, event_risk_data: List[Dict], setup_mock_servers: MockServerContext):
    """Test that volatility_service.get_event_risk correctly retrieves event risk data"""
    with setup_mock_servers:
        ticker = easy_to_borrow_stock['ticker']
        for server in setup_mock_servers.servers:
            if isinstance(server, EventApiMockServer):
                server.configure_event_risk(ticker=ticker, risk_factor=1)
        event_risk = volatility_service.get_event_risk(ticker)
        assert event_risk == 1


def test_volatility_service_fallback_mechanism(easy_to_borrow_stock: Dict, setup_mock_servers: MockServerContext):
    """Test that volatility_service uses fallback mechanisms when external APIs fail"""
    with setup_mock_servers:
        ticker = easy_to_borrow_stock['ticker']

        # Configure mock Market API to timeout or return an error
        for server in setup_mock_servers.servers:
            if isinstance(server, MarketApiMockServer):
                server.configure_timeout(ticker=ticker, timeout_seconds=1)

        # Call volatility_service.get_volatility
        volatility = volatility_service.get_volatility(ticker)
        # Assert that it returns a default volatility value
        # Configure mock Event API to timeout or return an error
        for server in setup_mock_servers.servers:
            if isinstance(server, EventApiMockServer):
                server.configure_timeout(ticker=ticker, timeout_seconds=1)

        # Call volatility_service.get_event_risk
        event_risk = volatility_service.get_event_risk(ticker)
        # Assert that it returns a default event risk factor of 0
        assert event_risk == 0


def test_api_integration_get_borrow_rate(api_client: APIClient, easy_to_borrow_stock: Dict, setup_mock_servers: MockServerContext):
    """Test the integration between the API and data service for borrow rate retrieval"""
    with setup_mock_servers:
        ticker = easy_to_borrow_stock['ticker']

        # Configure mock SecLend API to return a specific borrow rate
        for server in setup_mock_servers.servers:
            if isinstance(server, SecLendMockServer):
                server.configure_borrow_rate(ticker=ticker, rate=0.05)
            if isinstance(server, MarketApiMockServer):
                server.configure_volatility(ticker=ticker, volatility_index=18.5)
            if isinstance(server, EventApiMockServer):
                server.configure_event_risk(ticker=ticker, risk_factor=2)

        # Call api_client.get_borrow_rate with the ticker
        borrow_rate_response = api_client.get_borrow_rate(ticker)

        # Assert that the API response contains the expected borrow rate
        assert borrow_rate_response.current_rate == 0.05
        # Assert that the API response contains the expected volatility and event risk data
        assert borrow_rate_response.volatility_index == 18.5
        assert borrow_rate_response.event_risk_factor == 2