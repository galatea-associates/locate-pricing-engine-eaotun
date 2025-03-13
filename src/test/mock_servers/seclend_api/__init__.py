"""
SecLend API Mock Server

This module provides a configurable interface for simulating the real SecLend API
during testing. It enables isolated testing of the Borrow Rate & Locate Fee Pricing
Engine without requiring actual external connectivity.
"""

import logging
import threading
import uvicorn
from typing import Dict, List, Any, Optional

# Import FastAPI application and router
from .app import app
from .handlers import router

# Import mock data configurations
from .data import (
    STOCK_DATA,
    ERROR_TICKERS as ERROR_RESPONSE_TICKERS,
    TIMEOUT_TICKERS
)

# Set up logger
logger = logging.getLogger('seclend_api')

# Default host and port for the mock server
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8001

# Extract DEFAULT_BORROW_RATES from STOCK_DATA
DEFAULT_BORROW_RATES = {
    ticker: data["rate"] for ticker, data in STOCK_DATA.items()
}

# Extract DEFAULT_BORROW_STATUSES from STOCK_DATA
DEFAULT_BORROW_STATUSES = {
    ticker: data["status"] for ticker, data in STOCK_DATA.items()
}

# Calculate HIGH_VOLATILITY_BORROW_RATES using high volatility multiplier (2.5)
HIGH_VOLATILITY_BORROW_RATES = {
    ticker: min(0.95, data["rate"] * 2.5) for ticker, data in STOCK_DATA.items()
}

def configure_mock_server(volatility_mode: bool = False, 
                         custom_responses: Optional[Dict[str, Dict[str, Any]]] = None) -> bool:
    """
    Configures the SecLend API mock server with custom settings.
    
    Args:
        volatility_mode: Whether to enable high volatility mode
        custom_responses: Dictionary mapping tickers to custom response data
        
    Returns:
        True if configuration was successful
    """
    # Import set_volatility_mode from handlers module
    from .handlers import set_high_volatility_mode as set_volatility_mode
    
    # Import set_custom_response from handlers module
    from .handlers import set_custom_response
    
    # We need to handle the async nature of these functions
    import asyncio
    
    # Create an event loop if there isn't one
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Call set_volatility_mode with the provided volatility_mode parameter
    loop.run_until_complete(set_volatility_mode(volatility_mode))
    
    # For each ticker and response in custom_responses:
    # Call set_custom_response with the ticker and response data
    if custom_responses:
        for ticker, response in custom_responses.items():
            loop.run_until_complete(set_custom_response(ticker, response))
    
    # Log the configuration changes
    logger.info(f"Mock server configured: volatility_mode={volatility_mode}, "
               f"custom_responses for {len(custom_responses) if custom_responses else 0} tickers")
    
    # Return True if configuration was successful
    return True

def reset_mock_server() -> bool:
    """
    Resets the SecLend API mock server to default configuration.
    
    Returns:
        True if reset was successful
    """
    # Import set_volatility_mode from handlers module
    from .handlers import set_high_volatility_mode as set_volatility_mode
    
    # Import clear_custom_responses from handlers module
    from .handlers import clear_custom_responses
    
    # We need to handle the async nature of these functions
    import asyncio
    
    # Create an event loop if there isn't one
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Call set_volatility_mode with False to disable volatility mode
    loop.run_until_complete(set_volatility_mode(False))
    
    # Call clear_custom_responses to remove all custom responses
    loop.run_until_complete(clear_custom_responses())
    
    # Log the reset operation
    logger.info("Mock server reset to default configuration")
    
    # Return True if reset was successful
    return True

class SecLendMockServer:
    """
    Class that manages the SecLend API mock server for testing.
    """
    
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        """
        Initializes a new SecLendMockServer instance.
        
        Args:
            host: Host address to bind the server to
            port: Port number to listen on
        """
        self.host = host
        self.port = port
        self.server_thread = None
        self.is_running = False
        
        logger.info(f"Initialized SecLendMockServer on {host}:{port}")
    
    def start(self) -> bool:
        """
        Starts the SecLend API mock server in a separate thread.
        
        Returns:
            True if server started successfully
        """
        if self.is_running:
            logger.info("Server is already running")
            return True
        
        def run_server():
            uvicorn.run(
                app,
                host=self.host,
                port=self.port,
                log_level="info"
            )
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.is_running = True
        
        logger.info(f"Started SecLend API mock server on {self.host}:{self.port}")
        
        return True
    
    def stop(self) -> bool:
        """
        Stops the SecLend API mock server.
        
        Returns:
            True if server stopped successfully
        """
        if not self.is_running:
            logger.info("Server is not running")
            return False
        
        # Since we're using a daemon thread, we don't need to explicitly terminate it
        # Just update our state
        self.is_running = False
        self.server_thread = None
        
        logger.info("Stopped SecLend API mock server")
        
        return True
    
    def configure(self, volatility_mode: bool = False,
                 custom_responses: Optional[Dict[str, Dict[str, Any]]] = None) -> bool:
        """
        Configures the SecLend API mock server with custom settings.
        
        Args:
            volatility_mode: Whether to enable high volatility mode
            custom_responses: Dictionary mapping tickers to custom response data
            
        Returns:
            True if configuration was successful
        """
        result = configure_mock_server(volatility_mode, custom_responses)
        logger.info("Mock server configured through server instance")
        return result
    
    def reset(self) -> bool:
        """
        Resets the SecLend API mock server to default configuration.
        
        Returns:
            True if reset was successful
        """
        result = reset_mock_server()
        logger.info("Mock server reset through server instance")
        return result
    
    def get_base_url(self) -> str:
        """
        Returns the base URL for the mock server.
        
        Returns:
            Base URL string
        """
        return f"http://{self.host}:{self.port}"