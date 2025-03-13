"""
Central configuration management for the Borrow Rate & Locate Fee Pricing Engine.

This module provides a singleton Settings class that loads configuration from environment 
variables, validates them, and makes them available throughout the application. It serves
as the single source of truth for all application settings including database connections,
external API configurations, caching parameters, and security settings.
"""

import os
import functools
from typing import Any, Dict, Optional

import pydantic  # pydantic 2.4.0+

from .environment import Environment, EnvironmentVariables
from ..core.constants import (
    BorrowStatus, TransactionFeeType, ExternalAPIs,
    DEFAULT_MINIMUM_BORROW_RATE, DEFAULT_VOLATILITY_FACTOR, DEFAULT_EVENT_RISK_FACTOR,
    DEFAULT_MARKUP_PERCENTAGE, DEFAULT_TRANSACTION_FEE_FLAT, DEFAULT_TRANSACTION_FEE_PERCENTAGE,
    DAYS_IN_YEAR,
    CACHE_TTL_BORROW_RATE, CACHE_TTL_VOLATILITY, CACHE_TTL_EVENT_RISK,
    CACHE_TTL_BROKER_CONFIG, CACHE_TTL_CALCULATION
)

# Global instance to be used by the singleton pattern
_settings_instance = None


@functools.lru_cache(maxsize=1)
def get_settings() -> 'Settings':
    """
    Returns the singleton Settings instance, creating it if necessary.
    
    Returns:
        Settings: Singleton Settings instance
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


def reload_settings() -> 'Settings':
    """
    Forces a reload of the settings from environment variables.
    
    This is useful for testing or when environment variables have changed
    while the application is running.
    
    Returns:
        Settings: Reloaded Settings instance
    """
    # Clear the cache to force recreation of the settings instance
    get_settings.cache_clear()
    return get_settings()


class CalculationSettings(pydantic.BaseModel):
    """
    Pydantic model for calculation-specific settings.
    
    Contains all the parameters used in the borrow rate and fee calculations,
    with reasonable defaults that can be overridden.
    """
    # Default rates and factors
    default_minimum_borrow_rate: float = float(DEFAULT_MINIMUM_BORROW_RATE)
    default_volatility_factor: float = float(DEFAULT_VOLATILITY_FACTOR)
    default_event_risk_factor: float = float(DEFAULT_EVENT_RISK_FACTOR)
    
    # Default broker configuration values
    default_markup_percentage: float = float(DEFAULT_MARKUP_PERCENTAGE)
    default_transaction_fee_flat: float = float(DEFAULT_TRANSACTION_FEE_FLAT)
    default_transaction_fee_percentage: float = float(DEFAULT_TRANSACTION_FEE_PERCENTAGE)
    
    # Calendar constants
    days_in_year: int = int(DAYS_IN_YEAR)


class CacheTTLSettings(pydantic.BaseModel):
    """
    Pydantic model for cache TTL settings.
    
    Defines the time-to-live values for different types of cached data,
    with reasonable defaults that can be overridden.
    """
    # Cache TTLs in seconds
    borrow_rate: int = CACHE_TTL_BORROW_RATE
    volatility: int = CACHE_TTL_VOLATILITY
    event_risk: int = CACHE_TTL_EVENT_RISK
    broker_config: int = CACHE_TTL_BROKER_CONFIG
    calculation: int = CACHE_TTL_CALCULATION


class Settings:
    """
    Main settings class that provides access to all application configuration.
    
    Acts as a central repository for all configuration settings, loaded from
    environment variables and providing defaults where appropriate. This class
    is implemented as a singleton to ensure consistent configuration across
    the application.
    """
    
    def __init__(self):
        """
        Initializes the Settings object with values from environment variables.
        
        Loads configuration from environment variables using the EnvironmentVariables
        class, and sets up additional domain-specific settings with reasonable defaults.
        """
        # Load environment variables
        env = EnvironmentVariables()
        
        # Application settings
        self.app_name = env.app_name
        self.api_version = env.api_version
        self.environment = env.environment
        
        # Database connections
        self.database_url = env.database_url
        self.redis_url = env.redis_url
        
        # External API configurations
        self.seclend_api = env.seclend_api
        self.market_volatility_api = env.market_volatility_api
        self.event_calendar_api = env.event_calendar_api
        
        # Performance settings
        self.default_cache_ttl = env.default_cache_ttl
        self.default_rate_limit = env.default_rate_limit
        
        # Security settings
        self.api_keys = env.api_keys
        
        # Logging configuration
        self.logging = env.logging
        
        # Domain-specific settings
        self.calculation = CalculationSettings().dict()
        
        # Initialize cache TTL settings
        self.cache_ttls = CacheTTLSettings().dict()
    
    def is_development(self) -> bool:
        """
        Checks if the current environment is development.
        
        Returns:
            bool: True if environment is development
        """
        return self.environment is Environment.DEVELOPMENT
    
    def is_staging(self) -> bool:
        """
        Checks if the current environment is staging.
        
        Returns:
            bool: True if environment is staging
        """
        return self.environment is Environment.STAGING
    
    def is_production(self) -> bool:
        """
        Checks if the current environment is production.
        
        Returns:
            bool: True if environment is production
        """
        return self.environment is Environment.PRODUCTION
    
    def get_external_api_config(self, api_name: str) -> Dict[str, Any]:
        """
        Gets configuration for a specific external API.
        
        Args:
            api_name: Name of the external API (use ExternalAPIs constants)
            
        Returns:
            dict: API configuration dictionary
            
        Raises:
            ValueError: If an invalid API name is provided
        """
        if api_name == ExternalAPIs.SECLEND:
            return self.seclend_api
        elif api_name == ExternalAPIs.MARKET_VOLATILITY:
            return self.market_volatility_api
        elif api_name == ExternalAPIs.EVENT_CALENDAR:
            return self.event_calendar_api
        else:
            raise ValueError(f"Invalid API name: {api_name}")
    
    def get_cache_ttl(self, cache_type: str) -> int:
        """
        Gets the TTL for a specific cache type.
        
        Args:
            cache_type: Type of cache (e.g., 'borrow_rate', 'volatility')
            
        Returns:
            int: TTL in seconds for the specified cache type
        """
        return self.cache_ttls.get(cache_type, self.default_cache_ttl)
    
    def get_calculation_setting(self, setting_name: str) -> Any:
        """
        Gets a specific calculation setting.
        
        Args:
            setting_name: Name of the calculation setting
            
        Returns:
            Any: Value of the specified calculation setting
            
        Raises:
            KeyError: If the setting is not found
        """
        return self.calculation[setting_name]
    
    def get_api_key_config(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Gets configuration for a specific API key.
        
        Args:
            api_key: The API key to look up
            
        Returns:
            dict: API key configuration or None if not found
        """
        return self.api_keys.get(api_key)
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Gets the logging configuration.
        
        Returns:
            dict: Logging configuration dictionary
        """
        return self.logging