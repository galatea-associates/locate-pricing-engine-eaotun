import logging
import uvicorn
import threading
from typing import Dict, List, Any, Optional

# Internal imports
from .app import app
from .handlers import router
from .data import (
    DEFAULT_MARKET_VOLATILITY,
    STOCK_VOLATILITY as DEFAULT_VOLATILITY_VALUES,
    HIGH_MARKET_VOLATILITY,
    HIGH_VOLATILITY_MULTIPLIER,
    ERROR_TICKERS as ERROR_RESPONSE_TICKERS,
    TIMEOUT_TICKERS
)

# Setup logger
logger = logging.getLogger('market_api')

# Default configuration
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8002

# Create HIGH_VOLATILITY_VALUES based on STOCK_VOLATILITY and HIGH_VOLATILITY_MULTIPLIER
HIGH_VOLATILITY_VALUES = {
    ticker: value * HIGH_VOLATILITY_MULTIPLIER 
    for ticker, value in DEFAULT_VOLATILITY_VALUES.items()
}

def configure_mock_server(high_volatility_mode: bool = False, custom_responses: Dict[str, Dict[str, Any]] = None) -> bool:
    """
    Configures the Market Volatility API mock server with custom settings
    
    Args:
        high_volatility_mode: Whether to enable high volatility mode
        custom_responses: Dictionary of custom responses keyed by ticker or endpoint name
        
    Returns:
        bool: True if configuration was successful
    """
    try:
        # Import handlers module functions
        from .handlers import set_high_volatility_mode, set_custom_response
        
        # Set high volatility mode
        set_high_volatility_mode(high_volatility_mode)
        
        # Configure custom responses if provided
        if custom_responses:
            for key, response in custom_responses.items():
                set_custom_response(key, response)
        
        logger.info(f"Mock server configured: high_volatility_mode={high_volatility_mode}, custom_responses={custom_responses is not None}")
        return True
    except Exception as e:
        logger.error(f"Error configuring mock server: {str(e)}")
        return False

def reset_mock_server() -> bool:
    """
    Resets the Market Volatility API mock server to default configuration
    
    Returns:
        bool: True if reset was successful
    """
    try:
        # Import handlers module functions
        from .handlers import set_high_volatility_mode, clear_custom_responses
        
        # Disable high volatility mode
        set_high_volatility_mode(False)
        
        # Clear all custom responses
        clear_custom_responses()
        
        logger.info("Mock server reset to default configuration")
        return True
    except Exception as e:
        logger.error(f"Error resetting mock server: {str(e)}")
        return False

class MarketApiMockServer:
    """
    Class that manages the Market Volatility API mock server for testing
    """
    
    def __init__(self, host: str = None, port: int = None):
        """
        Initializes a new MarketApiMockServer instance
        
        Args:
            host: Host address to bind the server to
            port: Port number to bind the server to
        """
        self.host = host or DEFAULT_HOST
        self.port = port or DEFAULT_PORT
        self.server_thread = None
        self.is_running = False
        logger.info(f"Initialized MarketApiMockServer at {self.host}:{self.port}")
    
    def start(self) -> bool:
        """
        Starts the Market Volatility API mock server in a separate thread
        
        Returns:
            bool: True if server started successfully
        """
        if self.is_running:
            logger.info("Server is already running")
            return True
        
        try:
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
            
            logger.info(f"Started MarketApiMockServer at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Error starting mock server: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """
        Stops the Market Volatility API mock server
        
        Returns:
            bool: True if server stopped successfully
        """
        if not self.is_running:
            logger.info("Server is not running")
            return False
        
        try:
            # There's no clean way to stop uvicorn programmatically in a thread
            # The daemon=True flag ensures the thread will be terminated when the main program exits
            self.is_running = False
            self.server_thread = None
            logger.info("Stopped MarketApiMockServer")
            return True
        except Exception as e:
            logger.error(f"Error stopping mock server: {str(e)}")
            return False
    
    def configure(self, high_volatility_mode: bool = False, custom_responses: Dict[str, Dict[str, Any]] = None) -> bool:
        """
        Configures the Market Volatility API mock server with custom settings
        
        Args:
            high_volatility_mode: Whether to enable high volatility mode
            custom_responses: Dictionary of custom responses keyed by ticker or endpoint name
            
        Returns:
            bool: True if configuration was successful
        """
        result = configure_mock_server(high_volatility_mode, custom_responses)
        logger.info(f"Configured MarketApiMockServer: high_volatility_mode={high_volatility_mode}")
        return result
    
    def reset(self) -> bool:
        """
        Resets the Market Volatility API mock server to default configuration
        
        Returns:
            bool: True if reset was successful
        """
        result = reset_mock_server()
        logger.info("Reset MarketApiMockServer to default configuration")
        return result
    
    def get_base_url(self) -> str:
        """
        Returns the base URL for the mock server
        
        Returns:
            str: Base URL string
        """
        return f"http://{self.host}:{self.port}"