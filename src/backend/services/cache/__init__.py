"""
Entry point for the cache service module that provides a unified interface for caching operations in the Borrow Rate & Locate Fee Pricing Engine.

This module exports cache implementations, strategies, and utility functions to enable efficient caching
of frequently accessed data such as borrow rates, volatility metrics, and broker configurations.
"""

from typing import Any, Optional

# Import utility functions
from .utils import (
    generate_cache_key,
    get_borrow_rate_key,
    get_volatility_key,
    get_event_risk_key,
    get_broker_config_key,
    get_ttl_for_data_type
)

# Import cache implementations
from .redis import RedisCache
from .local import LocalCache

# Import cache strategies
from .strategies import (
    CacheStrategy,
    SingleCacheStrategy,
    TieredCacheStrategy,
    NullCacheStrategy,
    get_ttl_for_key_type
)

# Import application settings and logging
from ...config.settings import get_settings
from ...core.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Singleton instances
_redis_cache = None
_local_cache = None
_cache_strategy = None

def get_redis_cache() -> RedisCache:
    """
    Returns a singleton instance of the Redis cache.
    
    Returns:
        RedisCache: Singleton Redis cache instance
    """
    global _redis_cache
    
    if _redis_cache is None:
        # Get Redis configuration from settings
        settings = get_settings()
        redis_url = settings.redis_url
        
        # Parse Redis URL
        # Format typically: redis://[:password@]host[:port][/db-number]
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(redis_url)
            
            # Extract host and port
            host = parsed.hostname or "localhost"
            port = parsed.port or 6379
            
            # Extract password
            password = parsed.password
            
            # Extract database number
            path = parsed.path
            db = int(path[1:]) if path and path[1:].isdigit() else 0
            
            # Create Redis cache instance
            _redis_cache = RedisCache(
                host=host,
                port=port,
                password=password,
                db=db
            )
            
            logger.info(f"Initialized Redis cache connection to {host}:{port} (db: {db})")
        except Exception as e:
            logger.warning(f"Failed to parse Redis URL, using default settings: {str(e)}")
            _redis_cache = RedisCache(
                host="localhost",
                port=6379,
                password=None,
                db=0
            )
    
    return _redis_cache

def get_local_cache() -> LocalCache:
    """
    Returns a singleton instance of the local in-memory cache.
    
    Returns:
        LocalCache: Singleton local cache instance
    """
    global _local_cache
    
    if _local_cache is None:
        _local_cache = LocalCache()
    
    return _local_cache

def get_cache_strategy() -> CacheStrategy:
    """
    Returns the configured cache strategy based on application settings.
    
    Returns:
        CacheStrategy: Configured cache strategy instance
    """
    global _cache_strategy
    
    if _cache_strategy is None:
        # Get settings to determine cache configuration
        settings = get_settings()
        
        # Get cache instances
        redis_cache = get_redis_cache()
        local_cache = get_local_cache()
        
        # Check if Redis is connected
        redis_connected = redis_cache.is_connected()
        
        if redis_connected:
            # Use tiered strategy with Redis as primary and local as secondary
            logger.info("Using TieredCacheStrategy with Redis and local cache")
            _cache_strategy = TieredCacheStrategy(
                primary_cache=redis_cache,
                secondary_cache=local_cache
            )
        else:
            # Redis not available, use local cache only
            logger.warning("Redis not available, using SingleCacheStrategy with local cache")
            _cache_strategy = SingleCacheStrategy(cache=local_cache)
    
    return _cache_strategy

def reset_cache_strategy() -> None:
    """
    Resets the cache strategy to force recreation on next access.
    
    Returns:
        None: No return value
    """
    global _cache_strategy
    _cache_strategy = None
    logger.info("Cache strategy reset, will be recreated on next access")

# Export all required components
__all__ = [
    # Cache implementations
    'RedisCache',
    'LocalCache',
    
    # Cache strategies
    'CacheStrategy',
    'SingleCacheStrategy',
    'TieredCacheStrategy',
    'NullCacheStrategy',
    
    # Singleton accessors
    'get_redis_cache',
    'get_local_cache',
    'get_cache_strategy',
    'reset_cache_strategy',
    
    # Utility functions
    'generate_cache_key',
    'get_borrow_rate_key',
    'get_volatility_key',
    'get_event_risk_key',
    'get_broker_config_key',
    'get_ttl_for_data_type',
    'get_ttl_for_key_type'
]