"""
Integration tests for fallback mechanisms in the Borrow Rate & Locate Fee Pricing Engine.
This module verifies that the system correctly handles external API failures by implementing 
appropriate fallback strategies, ensuring business continuity during service disruptions.
"""

import pytest
import logging
import time
from decimal import Decimal

from .helpers.api_client import APIClient, create_api_client
from .helpers.mock_server import (
    SecLendMockServer, 
    MarketApiMockServer, 
    EventApiMockServer,
    MockServerContext
)
from .helpers.assertions import Assertions
from .config.settings import get_test_settings
from src.backend.core.constants import DEFAULT_MINIMUM_BORROW_RATE

# Configure module logger
logger = logging.getLogger(__name__)

# Test constants
TEST_TICKER = "AAPL"
TEST_POSITION_VALUE = 100000
TEST_LOAN_DAYS = 30
TEST_CLIENT_ID = "test_client"


def setup_module():
    """Setup function that runs once before all tests in the module"""
    logger.info("Starting fallback mechanism integration tests")
    # Ensure mock servers are configured in test settings
    settings = get_test_settings()
    assert settings.use_mock_servers, "Mock servers must be enabled for fallback mechanism tests"
    # Create API client for tests
    create_api_client()


def teardown_module():
    """Teardown function that runs once after all tests in the module"""
    logger.info("Completed fallback mechanism integration tests")
    # Clean up any resources created during tests


class TestFallbackMechanisms:
    """Test class for verifying fallback mechanisms when external APIs are unavailable"""
    
    @classmethod
    def setup_class(cls):
        """Setup method that runs once before all tests in the class"""
        # Create an instance of Assertions for response validation
        cls.assertions = Assertions()
        
        # Create an API client for making requests to the pricing engine
        cls.api_client = create_api_client()
        
        # Initialize mock servers for external APIs
        cls.seclend_mock = SecLendMockServer()
        cls.market_mock = MarketApiMockServer()
        cls.event_mock = EventApiMockServer()
    
    @classmethod
    def teardown_class(cls):
        """Teardown method that runs once after all tests in the class"""
        # Stop all mock servers
        for server in [cls.seclend_mock, cls.market_mock, cls.event_mock]:
            if hasattr(server, 'stop'):
                server.stop()
        
        # Clean up any resources created during tests
    
    @pytest.mark.integration
    def test_seclend_api_fallback(self):
        """Tests that the system falls back to minimum borrow rate when SecLend API is unavailable"""
        # Create mock servers for all external APIs
        with MockServerContext([self.seclend_mock, self.market_mock, self.event_mock]):
            # Configure SecLend API mock server to timeout
            self.seclend_mock.configure_timeout(TEST_TICKER)
            
            # Make a request to get borrow rate for a ticker
            response = self.api_client.get(f"/rates/{TEST_TICKER}")
            
            # Verify that the response contains the fallback minimum borrow rate
            rate_response = self.assertions.assert_rate_response(
                response,
                expected_ticker=TEST_TICKER,
                expected_rate=DEFAULT_MINIMUM_BORROW_RATE
            )
            
            # Verify that the response indicates the rate is a fallback value
            assert hasattr(rate_response, 'data_sources'), "Response missing data_sources attribute"
            assert rate_response.data_sources.get('base_rate') == 'fallback', \
                f"Expected base_rate source to be 'fallback', got {rate_response.data_sources.get('base_rate')}"
            
            logger.info("Successfully tested SecLend API fallback")
    
    @pytest.mark.integration
    def test_market_api_fallback(self):
        """Tests that the system falls back to default volatility when Market API is unavailable"""
        # Create mock servers for all external APIs
        with MockServerContext([self.seclend_mock, self.market_mock, self.event_mock]):
            # Configure Market API mock server to timeout
            self.market_mock.configure_timeout(TEST_TICKER)
            
            # Make a request to calculate locate fee
            payload = {
                "ticker": TEST_TICKER,
                "position_value": TEST_POSITION_VALUE,
                "loan_days": TEST_LOAN_DAYS,
                "client_id": TEST_CLIENT_ID
            }
            response = self.api_client.post("/calculate-locate", json_data=payload)
            
            # Verify that the calculation completes successfully
            calc_response = self.assertions.assert_calculation_result(response)
            
            # Verify that the volatility adjustment uses the default value
            assert hasattr(calc_response, 'data_sources'), "Response missing data_sources attribute"
            assert calc_response.data_sources.get('volatility') == 'fallback', \
                f"Expected volatility source to be 'fallback', got {calc_response.data_sources.get('volatility')}"
            
            logger.info("Successfully tested Market API fallback")
    
    @pytest.mark.integration
    def test_event_api_fallback(self):
        """Tests that the system falls back to zero event risk when Event API is unavailable"""
        # Create mock servers for all external APIs
        with MockServerContext([self.seclend_mock, self.market_mock, self.event_mock]):
            # Configure Event API mock server to timeout
            self.event_mock.configure_timeout(TEST_TICKER)
            
            # Make a request to calculate locate fee
            payload = {
                "ticker": TEST_TICKER,
                "position_value": TEST_POSITION_VALUE,
                "loan_days": TEST_LOAN_DAYS,
                "client_id": TEST_CLIENT_ID
            }
            response = self.api_client.post("/calculate-locate", json_data=payload)
            
            # Verify that the calculation completes successfully
            calc_response = self.assertions.assert_calculation_result(response)
            
            # Verify that the event risk adjustment is zero
            assert hasattr(calc_response, 'data_sources'), "Response missing data_sources attribute"
            assert calc_response.data_sources.get('event_risk') == 'fallback', \
                f"Expected event_risk source to be 'fallback', got {calc_response.data_sources.get('event_risk')}"
            
            logger.info("Successfully tested Event API fallback")
    
    @pytest.mark.integration
    def test_multiple_api_failures(self):
        """Tests that the system handles multiple API failures gracefully"""
        # Create mock servers for all external APIs
        with MockServerContext([self.seclend_mock, self.market_mock, self.event_mock]):
            # Configure all external API mock servers to timeout
            self.seclend_mock.configure_timeout(TEST_TICKER)
            self.market_mock.configure_timeout(TEST_TICKER)
            self.event_mock.configure_timeout(TEST_TICKER)
            
            # Make a request to calculate locate fee
            payload = {
                "ticker": TEST_TICKER,
                "position_value": TEST_POSITION_VALUE,
                "loan_days": TEST_LOAN_DAYS,
                "client_id": TEST_CLIENT_ID
            }
            response = self.api_client.post("/calculate-locate", json_data=payload)
            
            # Verify that the calculation completes successfully
            calc_response = self.assertions.assert_calculation_result(response)
            
            # Verify that all fallback values are used correctly
            assert hasattr(calc_response, 'data_sources'), "Response missing data_sources attribute"
            assert calc_response.data_sources.get('base_rate') == 'fallback', \
                f"Expected base_rate source to be 'fallback', got {calc_response.data_sources.get('base_rate')}"
            assert calc_response.data_sources.get('volatility') == 'fallback', \
                f"Expected volatility source to be 'fallback', got {calc_response.data_sources.get('volatility')}"
            assert calc_response.data_sources.get('event_risk') == 'fallback', \
                f"Expected event_risk source to be 'fallback', got {calc_response.data_sources.get('event_risk')}"
            
            logger.info("Successfully tested multiple API failures")
    
    @pytest.mark.integration
    def test_circuit_breaker_pattern(self):
        """Tests that the circuit breaker pattern prevents repeated API calls after failures"""
        # Create mock servers for all external APIs
        with MockServerContext([self.seclend_mock, self.market_mock, self.event_mock]):
            # Configure SecLend API mock server to timeout
            self.seclend_mock.configure_timeout(TEST_TICKER)
            
            # Clear request history
            self.seclend_mock.clear_request_history()
            
            # Make multiple requests to get borrow rate to trigger circuit breaker
            for _ in range(5):
                response = self.api_client.get(f"/rates/{TEST_TICKER}")
                self.assertions.assert_rate_response(
                    response,
                    expected_ticker=TEST_TICKER,
                    expected_rate=DEFAULT_MINIMUM_BORROW_RATE
                )
            
            # Get request history to see how many requests were made
            initial_request_count = len(self.seclend_mock.get_request_history())
            logger.info(f"Initial API calls: {initial_request_count}")
            
            # Make more requests - these should use the circuit breaker and not hit the API
            for _ in range(5):
                response = self.api_client.get(f"/rates/{TEST_TICKER}")
                self.assertions.assert_rate_response(
                    response,
                    expected_ticker=TEST_TICKER,
                    expected_rate=DEFAULT_MINIMUM_BORROW_RATE
                )
            
            # Get updated request history
            final_request_count = len(self.seclend_mock.get_request_history())
            logger.info(f"Final API calls: {final_request_count}")
            
            # Verify that subsequent requests use fallback immediately without API calls
            # The circuit breaker should prevent additional API calls after a certain number of failures
            assert final_request_count <= initial_request_count + 1, \
                f"Expected circuit breaker to prevent additional API calls after {initial_request_count} failures, " \
                f"but got {final_request_count} total calls"
            
            logger.info("Successfully tested circuit breaker pattern")
    
    @pytest.mark.integration
    def test_recovery_after_api_restored(self):
        """Tests that the system recovers and uses the API again after it becomes available"""
        # Create mock servers for all external APIs
        with MockServerContext([self.seclend_mock, self.market_mock, self.event_mock]):
            # Configure SecLend API mock server to timeout
            self.seclend_mock.configure_timeout(TEST_TICKER)
            
            # Make requests to trigger fallback mechanism
            for _ in range(5):
                response = self.api_client.get(f"/rates/{TEST_TICKER}")
                self.assertions.assert_rate_response(
                    response,
                    expected_ticker=TEST_TICKER,
                    expected_rate=DEFAULT_MINIMUM_BORROW_RATE
                )
            
            # Clear request history
            self.seclend_mock.clear_request_history()
            
            # Reconfigure SecLend API mock server to work normally
            expected_rate = Decimal('0.15')
            self.seclend_mock.configure_borrow_rate(TEST_TICKER, rate=expected_rate, status="EASY")
            
            # Wait for circuit breaker timeout period
            # This depends on the implementation, but we'll wait for a reasonable time
            time.sleep(6)
            
            # Make another request - it should use the API again
            response = self.api_client.get(f"/rates/{TEST_TICKER}")
            
            # Get request history to see if the API was called
            requests_after_recovery = len(self.seclend_mock.get_request_history())
            logger.info(f"Requests after recovery: {requests_after_recovery}")
            
            # Verify that the API was called again
            assert requests_after_recovery > 0, "Expected API to be called after recovery"
            
            # Verify that the response contains the proper rate, not the fallback
            self.assertions.assert_rate_response(
                response,
                expected_ticker=TEST_TICKER,
                expected_rate=expected_rate
            )
            
            logger.info("Successfully tested recovery after API restored")