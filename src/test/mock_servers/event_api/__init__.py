"""
Event Calendar API Mock Server

This module provides a configurable interface for simulating the real Event Calendar API during testing,
enabling isolated testing of the Borrow Rate & Locate Fee Pricing Engine without requiring actual
external connectivity.
"""

import logging
import uvicorn
import threading
from typing import Dict, List, Any, Optional

# Import internal components
from .app import app
from .handlers import router
from .data import (
    STOCK_EVENTS,
    ERROR_TICKERS as ERROR_RESPONSE_TICKERS,
    TIMEOUT_TICKERS
)

# Configure logger
logger = logging.getLogger('event_api')

# Default configuration
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8003
DEFAULT_EVENTS = STOCK_EVENTS


def configure_mock_server(high_risk_mode: bool, custom_responses: Dict[str, Dict[str, Any]]) -> bool:
    """
    Configures the Event Calendar API mock server with custom settings.
    
    Args:
        high_risk_mode: Flag to enable high risk mode (increases risk factors)
        custom_responses: Dictionary of custom responses for specific tickers
        
    Returns:
        True if configuration was successful
    """
    try:
        # Import the handlers module to access its global variables
        from . import handlers
        
        # Set high risk mode
        handlers.high_risk_mode = high_risk_mode
        
        # Set custom responses
        for ticker, response in custom_responses.items():
            handlers.custom_responses[ticker] = response
        
        logger.info(f"Mock server configured: high_risk_mode={high_risk_mode}, custom_responses for {len(custom_responses)} tickers")
        return True
    except Exception as e:
        logger.error(f"Failed to configure mock server: {str(e)}")
        return False


def reset_mock_server() -> bool:
    """
    Resets the Event Calendar API mock server to default configuration.
    
    Returns:
        True if reset was successful
    """
    try:
        # Import the handlers module to access its global variables
        from . import handlers
        
        # Disable high risk mode
        handlers.high_risk_mode = False
        
        # Clear custom responses
        handlers.custom_responses = {}
        
        logger.info("Mock server reset to default configuration")
        return True
    except Exception as e:
        logger.error(f"Failed to reset mock server: {str(e)}")
        return False


class EventApiMockServer:
    """
    Class that manages the Event Calendar API mock server for testing.
    
    This class provides methods to start, stop, and configure the mock server,
    allowing tests to simulate various API responses and behaviors.
    """
    
    def __init__(self, host: str = None, port: int = None):
        """
        Initializes a new EventApiMockServer instance.
        
        Args:
            host: Host address to bind the server to (default: 0.0.0.0)
            port: Port to run the server on (default: 8003)
        """
        self.host = host or DEFAULT_HOST
        self.port = port or DEFAULT_PORT
        self.server_thread = None
        self.is_running = False
        logger.info(f"EventApiMockServer initialized with host={self.host}, port={self.port}")
    
    def start(self) -> bool:
        """
        Starts the Event Calendar API mock server in a separate thread.
        
        Returns:
            True if server started successfully
        """
        if self.is_running:
            logger.info("Server is already running")
            return True
        
        try:
            # Create and start a new thread for the server
            self.server_thread = threading.Thread(
                target=uvicorn.run,
                kwargs={
                    "app": app,
                    "host": self.host,
                    "port": self.port,
                    "log_level": "error"
                }
            )
            self.server_thread.daemon = True
            self.server_thread.start()
            
            self.is_running = True
            logger.info(f"Event Calendar API mock server started on {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to start mock server: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """
        Stops the Event Calendar API mock server.
        
        Returns:
            True if server stopped successfully
        """
        if not self.is_running:
            logger.info("Server is not running")
            return False
        
        try:
            # Terminate the server thread
            # Note: This is a simplified approach for the mock server
            self.is_running = False
            self.server_thread = None
            
            logger.info("Event Calendar API mock server stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop mock server: {str(e)}")
            return False
    
    def configure(self, high_risk_mode: bool, custom_responses: Dict[str, Dict[str, Any]]) -> bool:
        """
        Configures the Event Calendar API mock server with custom settings.
        
        Args:
            high_risk_mode: Flag to enable high risk mode (increases risk factors)
            custom_responses: Dictionary of custom responses for specific tickers
            
        Returns:
            True if configuration was successful
        """
        result = configure_mock_server(high_risk_mode, custom_responses)
        if result:
            logger.info("Mock server configured successfully")
        return result
    
    def reset(self) -> bool:
        """
        Resets the Event Calendar API mock server to default configuration.
        
        Returns:
            True if reset was successful
        """
        result = reset_mock_server()
        if result:
            logger.info("Mock server reset to default configuration")
        return result
    
    def get_base_url(self) -> str:
        """
        Returns the base URL for the mock server.
        
        Returns:
            Base URL string in the format 'http://{host}:{port}'
        """
        return f"http://{self.host}:{self.port}"