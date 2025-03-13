"""
Initialization module for the configuration package of the Borrow Rate & Locate Fee Pricing Engine.

This module serves as the entry point for accessing configuration settings, environment 
variables, and logging configuration throughout the application. It exposes a clean 
interface to the configuration components while hiding implementation details.

Key components exposed by this module:
- Environment: Enumeration of possible deployment environments
- Settings: Central repository for all application settings
- get_settings: Provides singleton access to the Settings instance
- configure_logging: Initializes and configures the logging system
- get_logger: Provides configured logger instances for application components
- ExternalAPIConfig: Configuration for external API connections
"""

# Import environment variable handling functionality
from .environment import Environment, EnvironmentVariables

# Import application settings functionality
from .settings import Settings, get_settings, ExternalAPIConfig

# Import logging configuration functionality
from .logging_config import configure_logging, get_logger

# Define what is exported when using `from config import *`
__all__ = [
    "Environment",
    "Settings", 
    "get_settings", 
    "configure_logging", 
    "get_logger",
    "ExternalAPIConfig"
]