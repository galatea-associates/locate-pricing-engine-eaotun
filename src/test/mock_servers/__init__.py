"""
Mock Servers Package for Testing

This package provides simulated external API environments for testing the
Borrow Rate & Locate Fee Pricing Engine without actual external dependencies.
"""

import logging
from typing import Dict, List, Any, Optional

# Import SecLend API mock server components
from .seclend_api import (
    SecLendMockServer,
    configure_mock_server as configure_seclend_server,
    reset_mock_server as reset_seclend_server,
    DEFAULT_BORROW_RATES,
    DEFAULT_BORROW_STATUSES
)

# Import Market Volatility API mock server components
from .market_api import (
    MarketApiMockServer,
    configure_mock_server as configure_market_server,
    reset_mock_server as reset_market_server,
    DEFAULT_MARKET_VOLATILITY,
    DEFAULT_STOCK_VOLATILITY
)

# Import Event Calendar API mock server components
from .event_api import (
    EventApiMockServer,
    configure_mock_server as configure_event_server,
    reset_mock_server as reset_event_server,
    DEFAULT_EVENTS
)

# Set up logger
logger = logging.getLogger(__name__)

# Define version
VERSION = "1.0.0"

def reset_all_mock_servers() -> None:
    """
    Resets all mock servers to their default configurations
    
    Returns:
        None: No return value
    """
    reset_seclend_server()
    reset_market_server()
    reset_event_server()
    logger.info("All mock servers reset to default configuration")

def configure_high_volatility_scenario() -> None:
    """
    Configures all mock servers for a high volatility market scenario
    
    Returns:
        None: No return value
    """
    # Configure SecLend API for high volatility
    configure_seclend_server(volatility_mode=True)
    
    # Configure Market API for high volatility
    configure_market_server(high_volatility_mode=True)
    
    # Configure Event API for high risk
    configure_event_server(high_risk_mode=True, custom_responses={})
    
    logger.info("High volatility scenario configured for all mock servers")

def configure_api_failure_scenario(apis: List[str]) -> None:
    """
    Configures mock servers to simulate API failures
    
    Args:
        apis: List of API names to fail ('seclend', 'market', 'event')
    
    Returns:
        None: No return value
    """
    # Create custom error responses
    error_response = {"error": "API unavailable", "code": "SERVICE_UNAVAILABLE", "status": 503}
    
    for api in apis:
        if api.lower() == 'seclend':
            # Configure SecLend API to return errors
            configure_seclend_server(custom_responses={"AAPL": error_response})
            logger.info("SecLend API configured to fail")
        
        elif api.lower() == 'market':
            # Configure Market API to return errors
            configure_market_server(custom_responses={"AAPL": error_response})
            logger.info("Market API configured to fail")
        
        elif api.lower() == 'event':
            # Configure Event API to return errors
            configure_event_server(high_risk_mode=False, custom_responses={"AAPL": error_response})
            logger.info("Event API configured to fail")
    
    logger.info(f"API failure scenario configured for: {', '.join(apis)}")

class MockServerManager:
    """
    Class that manages all mock servers for testing
    """
    
    def __init__(self, config: Dict = None):
        """
        Initializes a new MockServerManager instance
        
        Args:
            config: Configuration dictionary for the mock servers
        """
        # Use empty dict if config is None
        config = config or {}
        
        # Initialize servers with any provided configuration
        seclend_config = config.get('seclend', {})
        market_config = config.get('market', {})
        event_config = config.get('event', {})
        
        self.seclend_server = SecLendMockServer(**seclend_config)
        self.market_server = MarketApiMockServer(**market_config)
        self.event_server = EventApiMockServer(**event_config)
        self.is_running = False
    
    def start_all(self) -> bool:
        """
        Starts all mock servers
        
        Returns:
            bool: True if all servers started successfully
        """
        seclend_started = self.seclend_server.start()
        market_started = self.market_server.start()
        event_started = self.event_server.start()
        
        all_started = seclend_started and market_started and event_started
        self.is_running = all_started
        
        if all_started:
            logger.info("All mock servers started successfully")
        else:
            logger.error("Failed to start all mock servers")
        
        return all_started
    
    def stop_all(self) -> bool:
        """
        Stops all mock servers
        
        Returns:
            bool: True if all servers stopped successfully
        """
        seclend_stopped = self.seclend_server.stop()
        market_stopped = self.market_server.stop()
        event_stopped = self.event_server.stop()
        
        all_stopped = seclend_stopped and market_stopped and event_stopped
        self.is_running = not all_stopped
        
        if all_stopped:
            logger.info("All mock servers stopped successfully")
        else:
            logger.error("Failed to stop all mock servers")
        
        return all_stopped
    
    def reset_all(self) -> bool:
        """
        Resets all mock servers to default configuration
        
        Returns:
            bool: True if all servers reset successfully
        """
        seclend_reset = self.seclend_server.reset()
        market_reset = self.market_server.reset()
        event_reset = self.event_server.reset()
        
        all_reset = seclend_reset and market_reset and event_reset
        
        if all_reset:
            logger.info("All mock servers reset successfully")
        else:
            logger.error("Failed to reset all mock servers")
        
        return all_reset
    
    def configure_scenario(self, scenario_name: str, scenario_config: Dict = None) -> bool:
        """
        Configures all mock servers for a specific test scenario
        
        Args:
            scenario_name: Name of the scenario to configure
            scenario_config: Configuration options for the scenario
            
        Returns:
            bool: True if scenario configuration was successful
        """
        scenario_config = scenario_config or {}
        
        if scenario_name == 'high_volatility':
            # Configure high volatility scenario
            seclend_config = self.seclend_server.configure(volatility_mode=True)
            market_config = self.market_server.configure(high_volatility_mode=True)
            event_config = self.event_server.configure(high_risk_mode=True, custom_responses={})
            
            success = seclend_config and market_config and event_config
            logger.info("High volatility scenario configured")
            
        elif scenario_name == 'api_failure':
            # Configure API failure scenario
            apis_to_fail = scenario_config.get('apis', ['seclend', 'market', 'event'])
            configure_api_failure_scenario(apis_to_fail)
            success = True
            logger.info(f"API failure scenario configured for: {', '.join(apis_to_fail)}")
            
        elif scenario_name == 'normal_market':
            # Reset to default configuration
            success = self.reset_all()
            logger.info("Normal market scenario configured (reset to defaults)")
            
        else:
            # Unknown scenario
            logger.error(f"Unknown scenario: {scenario_name}")
            success = False
        
        return success