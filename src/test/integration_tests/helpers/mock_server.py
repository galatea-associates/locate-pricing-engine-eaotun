"""
Provides mock server implementations for simulating external APIs during integration testing
of the Borrow Rate & Locate Fee Pricing Engine. This module contains a base MockServer class
and specialized implementations for SecLend API, Market Volatility API, and Event Calendar API
to enable isolated testing without external dependencies.
"""

import requests
import json
import logging
import time
import threading
import subprocess
import contextlib
from typing import Dict, List, Any, Optional, Union
from decimal import Decimal

from ..config.settings import get_test_settings, TestSettings
from .data_generators import DataGenerator

# Configure module logger
logger = logging.getLogger(__name__)

# Default timeout values
DEFAULT_TIMEOUT = 5  # Default timeout in seconds for waiting operations
DEFAULT_STARTUP_WAIT = 2  # Default wait time for server startup in seconds


class MockServer:
    """Base class for mock servers that simulate external APIs"""
    
    def __init__(self, server_type: str, settings: Optional[TestSettings] = None):
        """Initializes a new MockServer instance

        Args:
            server_type: Type of the mock server ('seclend', 'market', or 'event')
            settings: Test settings object (will use default if None)
        """
        self.server_type = server_type
        
        # Get settings using get_test_settings() if not provided
        self._settings = settings if settings is not None else get_test_settings()
        
        # Set base URL for this server type
        self.base_url = self._settings.get_mock_server_url(server_type)
        
        # Initialize dictionaries for storing responses
        self.default_responses = {}
        self.configured_responses = {}
        
        # Initialize request history
        self.request_history = []
        
        # Initialize process reference
        self.process = None
        self.is_running = False
        
        # Configure default responses for this server type
        self.configure_default_responses()
    
    def start(self, wait_for_server: Optional[bool] = True) -> bool:
        """Starts the mock server process

        Args:
            wait_for_server: Whether to wait for the server to be ready

        Returns:
            True if server started successfully
        """
        if self.is_running:
            logger.info(f"Mock {self.server_type} server is already running")
            return True
        
        # Determine command to start server based on server_type
        if self.server_type == 'seclend':
            cmd = ["python", "-m", "src.test.mock_api_server", "--type", "seclend", 
                   "--port", str(self._settings.mock_server_config.seclend_port)]
        elif self.server_type == 'market':
            cmd = ["python", "-m", "src.test.mock_api_server", "--type", "market", 
                   "--port", str(self._settings.mock_server_config.market_port)]
        elif self.server_type == 'event':
            cmd = ["python", "-m", "src.test.mock_api_server", "--type", "event", 
                   "--port", str(self._settings.mock_server_config.event_port)]
        else:
            logger.error(f"Unknown server type: {self.server_type}")
            return False
        
        # Start the server process
        try:
            self.process = subprocess.Popen(cmd)
            self.is_running = True
            
            # Wait for the server to be ready if requested
            if wait_for_server:
                # Wait for server to start
                time.sleep(DEFAULT_STARTUP_WAIT)
                
                # Check if server is healthy
                max_attempts = 5
                for attempt in range(max_attempts):
                    if self.is_healthy():
                        break
                    time.sleep(1)
                else:
                    logger.error(f"Mock {self.server_type} server failed to start after {max_attempts} attempts")
                    self.stop()
                    return False
            
            logger.info(f"Started mock {self.server_type} server at {self.base_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to start mock {self.server_type} server: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """Stops the mock server process

        Returns:
            True if server stopped successfully
        """
        if not self.is_running:
            logger.info(f"Mock {self.server_type} server is not running")
            return True
        
        try:
            # Terminate the process
            self.process.terminate()
            
            # Wait for the process to exit with a timeout
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # If the process didn't exit, kill it forcefully
                logger.warning(f"Mock {self.server_type} server did not terminate gracefully, killing")
                self.process.kill()
                self.process.wait()
            
            self.is_running = False
            logger.info(f"Stopped mock {self.server_type} server")
            return True
        except Exception as e:
            logger.error(f"Failed to stop mock {self.server_type} server: {str(e)}")
            return False
    
    def configure_response(self, endpoint: str, response_data: Dict[str, Any], 
                         status_code: int = 200, delay: Optional[int] = None) -> bool:
        """Configures a custom response for a specific endpoint

        Args:
            endpoint: The endpoint path (without base URL)
            response_data: The response data to return
            status_code: HTTP status code to return
            delay: Optional delay in seconds before responding

        Returns:
            True if configuration was successful
        """
        if not self.is_running:
            logger.error(f"Cannot configure response: Mock {self.server_type} server is not running")
            return False
        
        try:
            # Create configuration with response data, status code, and delay
            config = {
                "response_data": response_data,
                "status_code": status_code,
            }
            
            if delay is not None:
                config["delay"] = delay
            
            # Send configuration to mock server's admin endpoint
            admin_url = f"{self.base_url}/admin/configure"
            payload = {
                "endpoint": endpoint,
                "config": config
            }
            
            response = requests.post(admin_url, json=payload)
            
            if response.status_code == 200:
                # Store configuration in configured_responses
                self.configured_responses[endpoint] = config
                logger.info(f"Configured mock {self.server_type} server response for {endpoint}")
                return True
            else:
                logger.error(f"Failed to configure mock server response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error configuring mock server response: {str(e)}")
            return False
    
    def configure_default_responses(self) -> None:
        """Configures default responses for common endpoints"""
        # Create a DataGenerator instance
        data_generator = DataGenerator(self._settings)
        
        # Configure default responses based on server_type
        if self.server_type == 'seclend':
            # Configure default borrow rate endpoints for common tickers
            for stock in self._settings.get_test_data('stocks'):
                ticker = stock['ticker']
                borrow_status = stock.get('borrow_status', 'EASY')
                min_rate = stock.get('min_borrow_rate', 0.05)
                
                response = data_generator.generate_seclend_response(
                    ticker=ticker,
                    rate=Decimal(str(min_rate)),
                    status=borrow_status
                )
                
                endpoint = f"/api/borrows/{ticker}"
                self.default_responses[endpoint] = {
                    "response_data": response,
                    "status_code": 200,
                }
        
        elif self.server_type == 'market':
            # Configure default volatility endpoints for common tickers
            for volatility in self._settings.get_test_data('volatility'):
                stock_id = volatility['stock_id']
                vol_index = volatility.get('vol_index', 15.0)
                
                response = data_generator.generate_market_volatility_response(
                    ticker=stock_id,
                    volatility_index=Decimal(str(vol_index))
                )
                
                endpoint = f"/api/market/volatility/{stock_id}"
                self.default_responses[endpoint] = {
                    "response_data": response,
                    "status_code": 200,
                }
            
            # Configure default market-wide volatility endpoint
            market_response = data_generator.generate_market_volatility_response(
                volatility_index=Decimal('20.0')
            )
            
            endpoint = "/api/market/vix"
            self.default_responses[endpoint] = {
                "response_data": market_response,
                "status_code": 200,
            }
            
        elif self.server_type == 'event':
            # Configure default event risk endpoints for common tickers
            for volatility in self._settings.get_test_data('volatility'):
                stock_id = volatility['stock_id']
                event_risk = volatility.get('event_risk_factor', 0)
                
                response = data_generator.generate_event_risk_response(
                    ticker=stock_id,
                    risk_factor=event_risk
                )
                
                endpoint = f"/api/calendar/events"
                query_param = f"?ticker={stock_id}"
                self.default_responses[endpoint + query_param] = {
                    "response_data": response,
                    "status_code": 200,
                }
    
    def configure_error_response(self, endpoint: str, error_message: str, 
                               status_code: int = 400) -> bool:
        """Configures an error response for a specific endpoint

        Args:
            endpoint: The endpoint path (without base URL)
            error_message: The error message to include
            status_code: HTTP status code to return (default 400)

        Returns:
            True if configuration was successful
        """
        # Create error response data
        error_data = {
            "status": "error",
            "error": error_message
        }
        
        # Configure the response with error data and status code
        return self.configure_response(endpoint, error_data, status_code)
    
    def configure_timeout_response(self, endpoint: str, 
                                 timeout_seconds: Optional[int] = None) -> bool:
        """Configures a timeout response for a specific endpoint

        Args:
            endpoint: The endpoint path (without base URL)
            timeout_seconds: Seconds to delay (simulating timeout)

        Returns:
            True if configuration was successful
        """
        # Use a large value by default to simulate a timeout
        if timeout_seconds is None:
            timeout_seconds = 30
        
        # Configure empty response with a long delay
        return self.configure_response(endpoint, {}, 200, timeout_seconds)
    
    def get_request_history(self, endpoint: Optional[str] = None) -> List[Dict[str, Any]]:
        """Gets the history of requests made to the mock server

        Args:
            endpoint: Optional endpoint to filter history by

        Returns:
            List of request history items
        """
        if not self.is_running:
            logger.error(f"Cannot get request history: Mock {self.server_type} server is not running")
            return []
        
        try:
            # Send request to mock server's history endpoint
            history_url = f"{self.base_url}/admin/history"
            response = requests.get(history_url)
            
            if response.status_code == 200:
                # Parse response and update request_history
                self.request_history = response.json()
                
                # Filter by endpoint if requested
                if endpoint is not None:
                    return [req for req in self.request_history if req.get('path', '').startswith(endpoint)]
                return self.request_history
            else:
                logger.error(f"Failed to get request history: {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting request history: {str(e)}")
            return []
    
    def clear_request_history(self) -> bool:
        """Clears the request history on the mock server

        Returns:
            True if history was cleared successfully
        """
        if not self.is_running:
            logger.error(f"Cannot clear request history: Mock {self.server_type} server is not running")
            return False
        
        try:
            # Send request to mock server's clear history endpoint
            clear_url = f"{self.base_url}/admin/clear_history"
            response = requests.post(clear_url)
            
            if response.status_code == 200:
                # Clear local request_history
                self.request_history = []
                logger.info(f"Cleared request history for mock {self.server_type} server")
                return True
            else:
                logger.error(f"Failed to clear request history: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error clearing request history: {str(e)}")
            return False
    
    def reset_configuration(self) -> bool:
        """Resets all configured responses to defaults

        Returns:
            True if configuration was reset successfully
        """
        if not self.is_running:
            logger.error(f"Cannot reset configuration: Mock {self.server_type} server is not running")
            return False
        
        try:
            # Send request to mock server's reset endpoint
            reset_url = f"{self.base_url}/admin/reset"
            response = requests.post(reset_url)
            
            if response.status_code == 200:
                # Clear configured_responses
                self.configured_responses = {}
                logger.info(f"Reset configuration for mock {self.server_type} server")
                return True
            else:
                logger.error(f"Failed to reset configuration: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error resetting configuration: {str(e)}")
            return False
    
    def wait_for_requests(self, count: int, endpoint: Optional[str] = None, 
                        timeout: Optional[int] = None) -> bool:
        """Waits until a specific number of requests have been made to the server

        Args:
            count: Number of requests to wait for
            endpoint: Optional endpoint to filter by
            timeout: Maximum seconds to wait (default: DEFAULT_TIMEOUT)

        Returns:
            True if the expected number of requests was reached
        """
        if timeout is None:
            timeout = DEFAULT_TIMEOUT
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Get request history, filtered by endpoint if specified
            history = self.get_request_history(endpoint)
            
            # If we have enough requests, return True
            if len(history) >= count:
                return True
            
            # Sleep briefly to avoid busy waiting
            time.sleep(0.1)
        
        # If we've reached here, we timed out
        logger.warning(f"Timed out waiting for {count} requests to mock {self.server_type} server")
        return False
    
    def is_healthy(self) -> bool:
        """Checks if the mock server is healthy and responding

        Returns:
            True if server is healthy
        """
        if not self.is_running:
            return False
        
        try:
            # Try to reach the health endpoint
            health_url = f"{self.base_url}/health"
            response = requests.get(health_url, timeout=2)
            return response.status_code == 200
        except:
            return False


class SecLendMockServer(MockServer):
    """Mock server for the SecLend API that provides borrow rate data"""
    
    def __init__(self, settings: Optional[TestSettings] = None):
        """Initializes a new SecLendMockServer instance

        Args:
            settings: Test settings to use (will get default if None)
        """
        super().__init__(server_type='seclend', settings=settings)
    
    def configure_borrow_rate(self, ticker: str, rate: Union[Decimal, float], 
                            status: Optional[str] = None) -> bool:
        """Configures a specific borrow rate response for a ticker

        Args:
            ticker: Stock ticker symbol
            rate: Borrow rate value
            status: Borrow status (EASY, MEDIUM, HARD)

        Returns:
            True if configuration was successful
        """
        # Create endpoint path for the ticker
        endpoint = f"/api/borrows/{ticker}"
        
        # Use DataGenerator to create response
        data_generator = DataGenerator(self._settings)
        
        # Ensure rate is a Decimal
        if not isinstance(rate, Decimal):
            rate = Decimal(str(rate))
        
        # Generate response data
        response_data = data_generator.generate_seclend_response(
            ticker=ticker,
            rate=rate,
            status=status
        )
        
        # Configure the response
        return self.configure_response(endpoint, response_data)
    
    def configure_ticker_not_found(self, ticker: str) -> bool:
        """Configures a not found response for a ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if configuration was successful
        """
        # Create endpoint path for the ticker
        endpoint = f"/api/borrows/{ticker}"
        
        # Create error message
        error_message = f"Ticker not found: {ticker}"
        
        # Configure the error response with 404 status code
        return self.configure_error_response(endpoint, error_message, 404)
    
    def configure_timeout(self, ticker: str, timeout_seconds: Optional[int] = None) -> bool:
        """Configures a timeout response for a ticker

        Args:
            ticker: Stock ticker symbol
            timeout_seconds: Seconds to delay (simulating timeout)

        Returns:
            True if configuration was successful
        """
        # Create endpoint path for the ticker
        endpoint = f"/api/borrows/{ticker}"
        
        # Configure the timeout response
        return self.configure_timeout_response(endpoint, timeout_seconds)


class MarketApiMockServer(MockServer):
    """Mock server for the Market Volatility API that provides volatility data"""
    
    def __init__(self, settings: Optional[TestSettings] = None):
        """Initializes a new MarketApiMockServer instance

        Args:
            settings: Test settings to use (will get default if None)
        """
        super().__init__(server_type='market', settings=settings)
    
    def configure_volatility(self, ticker: str, volatility_index: Union[Decimal, float]) -> bool:
        """Configures a specific volatility response for a ticker

        Args:
            ticker: Stock ticker symbol
            volatility_index: Volatility index value

        Returns:
            True if configuration was successful
        """
        # Create endpoint path for the ticker
        endpoint = f"/api/market/volatility/{ticker}"
        
        # Use DataGenerator to create response
        data_generator = DataGenerator(self._settings)
        
        # Ensure volatility_index is a Decimal
        if not isinstance(volatility_index, Decimal):
            volatility_index = Decimal(str(volatility_index))
        
        # Generate response data
        response_data = data_generator.generate_market_volatility_response(
            ticker=ticker,
            volatility_index=volatility_index
        )
        
        # Configure the response
        return self.configure_response(endpoint, response_data)
    
    def configure_market_volatility(self, volatility_index: Union[Decimal, float]) -> bool:
        """Configures the market-wide volatility response

        Args:
            volatility_index: Market-wide volatility index value

        Returns:
            True if configuration was successful
        """
        # Create endpoint path for market volatility
        endpoint = f"/api/market/vix"
        
        # Use DataGenerator to create response
        data_generator = DataGenerator(self._settings)
        
        # Ensure volatility_index is a Decimal
        if not isinstance(volatility_index, Decimal):
            volatility_index = Decimal(str(volatility_index))
        
        # Generate response data
        response_data = data_generator.generate_market_volatility_response(
            volatility_index=volatility_index
        )
        
        # Configure the response
        return self.configure_response(endpoint, response_data)
    
    def configure_timeout(self, ticker: Optional[str] = None, 
                        timeout_seconds: Optional[int] = None) -> bool:
        """Configures a timeout response for volatility data

        Args:
            ticker: Stock ticker symbol (None for market-wide endpoint)
            timeout_seconds: Seconds to delay (simulating timeout)

        Returns:
            True if configuration was successful
        """
        # Create endpoint path based on ticker
        if ticker is None:
            endpoint = f"/api/market/vix"
        else:
            endpoint = f"/api/market/volatility/{ticker}"
        
        # Configure the timeout response
        return self.configure_timeout_response(endpoint, timeout_seconds)


class EventApiMockServer(MockServer):
    """Mock server for the Event Calendar API that provides event risk data"""
    
    def __init__(self, settings: Optional[TestSettings] = None):
        """Initializes a new EventApiMockServer instance

        Args:
            settings: Test settings to use (will get default if None)
        """
        super().__init__(server_type='event', settings=settings)
    
    def configure_event_risk(self, ticker: str, risk_factor: int, 
                           events: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Configures a specific event risk response for a ticker

        Args:
            ticker: Stock ticker symbol
            risk_factor: Event risk factor (0-10)
            events: Optional list of events (generated if None)

        Returns:
            True if configuration was successful
        """
        # Create endpoint path for the ticker
        endpoint = f"/api/calendar/events?ticker={ticker}"
        
        # Use DataGenerator to create response
        data_generator = DataGenerator(self._settings)
        
        # Generate response data
        response_data = data_generator.generate_event_risk_response(
            ticker=ticker,
            risk_factor=risk_factor,
            events=events
        )
        
        # Configure the response
        return self.configure_response(endpoint, response_data)
    
    def configure_no_events(self, ticker: str) -> bool:
        """Configures a response with no upcoming events for a ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if configuration was successful
        """
        # Create endpoint path for the ticker
        endpoint = f"/api/calendar/events?ticker={ticker}"
        
        # Use DataGenerator to create response with empty events list
        data_generator = DataGenerator(self._settings)
        response_data = data_generator.generate_event_risk_response(
            ticker=ticker,
            risk_factor=0,
            events=[]
        )
        
        # Configure the response
        return self.configure_response(endpoint, response_data)
    
    def configure_timeout(self, ticker: str, timeout_seconds: Optional[int] = None) -> bool:
        """Configures a timeout response for event data

        Args:
            ticker: Stock ticker symbol
            timeout_seconds: Seconds to delay (simulating timeout)

        Returns:
            True if configuration was successful
        """
        # Create endpoint path for the ticker
        endpoint = f"/api/calendar/events?ticker={ticker}"
        
        # Configure the timeout response
        return self.configure_timeout_response(endpoint, timeout_seconds)


class MockServerContext:
    """Context manager for using mock servers in tests with automatic cleanup"""
    
    def __init__(self, servers: List[MockServer]):
        """Initializes a new MockServerContext with specified servers

        Args:
            servers: List of MockServer instances to manage
        """
        self.servers = servers
    
    def __enter__(self) -> 'MockServerContext':
        """Starts all mock servers when entering the context

        Returns:
            Self reference for context manager
        """
        for server in self.servers:
            server.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stops all mock servers when exiting the context

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        for server in self.servers:
            server.stop()