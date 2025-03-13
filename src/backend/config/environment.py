"""
Environment Management Module for Borrow Rate & Locate Fee Pricing Engine.

This module provides functionality to load environment variables from various sources,
validate their types, and provide a structured interface for accessing environment-specific
configuration across different deployment environments.
"""

import os
import enum
from typing import Dict, Any, Optional, ClassVar, Dict
from dotenv import load_dotenv  # python-dotenv 1.0.0+
from pydantic import BaseModel, Field, validator  # pydantic 2.4.0+

# Constants
ENV_FILE_PATH = '.env'
DEFAULT_APP_NAME = 'Borrow Rate & Locate Fee Pricing Engine'

def get_environment_variables() -> Dict[str, Any]:
    """
    Load environment variables from .env file and OS environment.
    
    Returns:
        Dict[str, Any]: Dictionary of environment variables
    """
    # Load environment variables from .env file
    load_dotenv(ENV_FILE_PATH)
    
    # Return dictionary of all environment variables
    return dict(os.environ)


def get_env_or_default(key: str, default: Any) -> Any:
    """
    Get an environment variable value or return a default if not found.
    
    Args:
        key: The environment variable key
        default: The default value to return if key is not found
        
    Returns:
        Any: Environment variable value or default
    """
    env_vars = get_environment_variables()
    return env_vars.get(key, default)


class Environment(enum.Enum):
    """Enumeration of possible deployment environments."""
    
    DEVELOPMENT = "development"
    STAGING = "staging" 
    PRODUCTION = "production"
    
    def is_development(self) -> bool:
        """
        Check if the environment is development.
        
        Returns:
            bool: True if environment is development
        """
        return self is Environment.DEVELOPMENT
    
    def is_staging(self) -> bool:
        """
        Check if the environment is staging.
        
        Returns:
            bool: True if environment is staging
        """
        return self is Environment.STAGING
    
    def is_production(self) -> bool:
        """
        Check if the environment is production.
        
        Returns:
            bool: True if environment is production
        """
        return self is Environment.PRODUCTION
    
    @classmethod
    def from_string(cls, env_str: str) -> 'Environment':
        """
        Create an Environment enum from a string value.
        
        Args:
            env_str: String representation of the environment
            
        Returns:
            Environment: Environment enum value
        """
        try:
            return cls[env_str.upper()]
        except (KeyError, AttributeError):
            # Default to development environment if invalid or not provided
            return Environment.DEVELOPMENT


class EnvironmentVariables(BaseModel):
    """Pydantic model for environment variables with validation."""
    
    # Application settings
    app_name: str
    api_version: str
    environment: Environment
    
    # Database settings
    database_url: str
    redis_url: str
    
    # External API configurations
    seclend_api: Dict[str, Any]
    market_volatility_api: Dict[str, Any]
    event_calendar_api: Dict[str, Any]
    
    # Performance settings
    default_cache_ttl: int
    default_rate_limit: int
    
    # Security settings
    api_keys: Dict[str, Dict[str, Any]]
    
    # Logging settings
    logging: Dict[str, Any]
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True
    
    def __init__(self, **data):
        """
        Initialize the EnvironmentVariables with values from environment.
        
        All data is loaded from environment variables, with some variables 
        having default values if not provided.
        """
        # Load environment variables
        env_vars = get_environment_variables()
        
        # Initialize with application settings
        data["app_name"] = env_vars.get("APP_NAME", DEFAULT_APP_NAME)
        data["api_version"] = env_vars.get("API_VERSION", "v1")
        data["environment"] = Environment.from_string(env_vars.get("ENVIRONMENT", "development"))
        
        # Database settings - these are required
        data["database_url"] = env_vars.get("DATABASE_URL")
        data["redis_url"] = env_vars.get("REDIS_URL")
        
        # Configure external APIs
        data["seclend_api"] = self.load_external_api_config(env_vars, "SECLEND")
        data["market_volatility_api"] = self.load_external_api_config(env_vars, "MARKET_VOLATILITY")
        data["event_calendar_api"] = self.load_external_api_config(env_vars, "EVENT_CALENDAR")
        
        # Performance settings
        data["default_cache_ttl"] = int(env_vars.get("DEFAULT_CACHE_TTL", "300"))  # Default 5 minutes
        data["default_rate_limit"] = int(env_vars.get("DEFAULT_RATE_LIMIT", "60"))  # Default 60 requests/minute
        
        # Load API keys from environment
        data["api_keys"] = self.load_api_keys(env_vars)
        
        # Configure logging
        data["logging"] = {
            "level": env_vars.get("LOG_LEVEL", "INFO"),
            "format": env_vars.get("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            "file": env_vars.get("LOG_FILE", None),
            "sentry_dsn": env_vars.get("SENTRY_DSN", None)
        }
        
        super().__init__(**data)
    
    @staticmethod
    def load_api_keys(env_vars: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """
        Load API keys from environment variables.
        
        Args:
            env_vars: Dictionary of environment variables
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of API keys with their configurations
        """
        api_keys = {}
        
        # Look for environment variables with API_KEY_ prefix
        for key, value in env_vars.items():
            if key.startswith("API_KEY_"):
                # Parse client_id from the key name
                client_id = key.replace("API_KEY_", "").lower()
                
                # Get rate limit for this API key if specified
                rate_limit_key = f"RATE_LIMIT_{client_id.upper()}"
                rate_limit = int(env_vars.get(rate_limit_key, env_vars.get("DEFAULT_RATE_LIMIT", "60")))
                
                # Add API key to dictionary
                api_keys[value] = {
                    "client_id": client_id,
                    "rate_limit": rate_limit
                }
        
        return api_keys
    
    @staticmethod
    def load_external_api_config(env_vars: Dict[str, str], api_name: str) -> Dict[str, Any]:
        """
        Load configuration for an external API from environment variables.
        
        Args:
            env_vars: Dictionary of environment variables
            api_name: Name of the API (used as prefix for env vars)
            
        Returns:
            Dict[str, Any]: API configuration dictionary
        """
        prefix = f"{api_name}_API_"
        
        # Required settings
        base_url = env_vars.get(f"{prefix}URL")
        api_key = env_vars.get(f"{prefix}KEY")
        
        # Optional settings with defaults
        timeout = int(env_vars.get(f"{prefix}TIMEOUT", "30"))  # Default 30 seconds
        max_retries = int(env_vars.get(f"{prefix}MAX_RETRIES", "3"))  # Default 3 retries
        
        return {
            "base_url": base_url,
            "api_key": api_key,
            "timeout_seconds": timeout,
            "max_retries": max_retries
        }


# For direct imports
__all__ = ['Environment', 'EnvironmentVariables', 'get_environment_variables', 'get_env_or_default']