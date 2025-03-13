"""
Caching strategies for the Borrow Rate & Locate Fee Pricing Engine.

This module defines abstract and concrete cache strategy classes that provide
different approaches to caching, including single-level, tiered (multi-level),
and null caching. It supports the system's multi-level caching architecture
with appropriate fallback mechanisms when primary caches are unavailable.
"""

import abc
from typing import Any, Optional

from .utils import get_ttl_for_data_type
from ...core.constants import (
    CACHE_TTL_BORROW_RATE,
    CACHE_TTL_VOLATILITY,
    CACHE_TTL_EVENT_RISK,
    CACHE_TTL_BROKER_CONFIG,
    CACHE_TTL_CALCULATION
)
from ...core.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


def get_ttl_for_key_type(key: str) -> int:
    """
    Determines the appropriate TTL based on the key prefix.
    
    Args:
        key: Cache key
        
    Returns:
        TTL in seconds for the specified key type
    """
    # Split the key to get the prefix (before first colon)
    prefix = key.split(':', 1)[0] if ':' in key else key
    
    # Map prefix to corresponding TTL
    if prefix == 'borrow_rate':
        return CACHE_TTL_BORROW_RATE
    elif prefix == 'volatility':
        return CACHE_TTL_VOLATILITY
    elif prefix == 'event_risk':
        return CACHE_TTL_EVENT_RISK
    elif prefix == 'broker_config':
        return CACHE_TTL_BROKER_CONFIG
    else:
        # Default to calculation TTL
        return CACHE_TTL_CALCULATION


class CacheStrategy(abc.ABC):
    """
    Abstract base class defining the interface for all cache strategies.
    """
    
    @abc.abstractmethod
    def get(self, key: str, value_type: Optional[str] = None) -> Optional[Any]:
        """
        Retrieve a value from cache by key.
        
        Args:
            key: Cache key
            value_type: Optional type hint for conversion
            
        Returns:
            The cached value or None if not found
        """
        pass
    
    @abc.abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Store a value in cache with the specified key and TTL.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (optional)
            
        Returns:
            True if the value was successfully cached
        """
        pass
    
    @abc.abstractmethod
    def delete(self, key: str) -> bool:
        """
        Remove a value from cache by key.
        
        Args:
            key: Cache key
            
        Returns:
            True if the key was found and deleted
        """
        pass
    
    @abc.abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if the key exists
        """
        pass
    
    @abc.abstractmethod
    def flush(self) -> bool:
        """
        Clear all values from cache.
        
        Returns:
            True if the cache was successfully cleared
        """
        pass


class SingleCacheStrategy(CacheStrategy):
    """
    Cache strategy that uses a single cache implementation.
    """
    
    def __init__(self, cache: Any):
        """
        Initialize with a single cache implementation.
        
        Args:
            cache: The cache implementation to use
        """
        self._cache = cache
        logger.info("Initialized SingleCacheStrategy")
    
    def get(self, key: str, value_type: Optional[str] = None) -> Optional[Any]:
        """
        Retrieve a value from the cache by key.
        
        Args:
            key: Cache key
            value_type: Optional type hint for conversion
            
        Returns:
            The cached value or None if not found
        """
        return self._cache.get(key, value_type)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Store a value in the cache with the specified key and TTL.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (optional)
            
        Returns:
            True if the value was successfully cached
        """
        # If TTL is not specified, determine based on key type
        if ttl is None:
            ttl = get_ttl_for_key_type(key)
        
        return self._cache.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """
        Remove a value from the cache by key.
        
        Args:
            key: Cache key
            
        Returns:
            True if the key was found and deleted
        """
        return self._cache.delete(key)
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if the key exists
        """
        return self._cache.exists(key)
    
    def flush(self) -> bool:
        """
        Clear all values from the cache.
        
        Returns:
            True if the cache was successfully cleared
        """
        return self._cache.flush()


class TieredCacheStrategy(CacheStrategy):
    """
    Multi-level cache strategy that uses primary and secondary caches with fallback.
    """
    
    def __init__(self, primary_cache: Any, secondary_cache: Any):
        """
        Initialize with primary and secondary cache implementations.
        
        Args:
            primary_cache: Primary (faster) cache implementation
            secondary_cache: Secondary (more durable) cache implementation
        """
        self._primary_cache = primary_cache
        self._secondary_cache = secondary_cache
        logger.info("Initialized TieredCacheStrategy")
    
    def get(self, key: str, value_type: Optional[str] = None) -> Optional[Any]:
        """
        Retrieve a value from the cache hierarchy.
        
        First checks the primary cache, then falls back to the secondary cache.
        If found in secondary but not primary, it will update the primary cache.
        
        Args:
            key: Cache key
            value_type: Optional type hint for conversion
            
        Returns:
            The cached value or None if not found
        """
        # Try to get from primary cache first
        value = self._primary_cache.get(key, value_type)
        if value is not None:
            logger.debug(f"Cache hit in primary cache for key: {key}")
            return value
        
        # If not in primary, try secondary cache
        logger.debug(f"Cache miss in primary cache for key: {key}, trying secondary")
        value = self._secondary_cache.get(key, value_type)
        
        if value is not None:
            # Found in secondary, update primary cache
            logger.debug(f"Cache hit in secondary cache for key: {key}, updating primary")
            ttl = get_ttl_for_key_type(key)
            self._primary_cache.set(key, value, ttl)
            return value
        
        # Not found in either cache
        logger.debug(f"Cache miss for key: {key} in both caches")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Store a value in both primary and secondary caches.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (optional)
            
        Returns:
            True if the value was successfully cached in at least one cache
        """
        # If TTL is not specified, determine based on key type
        if ttl is None:
            ttl = get_ttl_for_key_type(key)
        
        # Try to set in both caches
        primary_success = False
        secondary_success = False
        
        try:
            primary_success = self._primary_cache.set(key, value, ttl)
        except Exception as e:
            logger.warning(f"Failed to set key {key} in primary cache: {str(e)}")
        
        try:
            secondary_success = self._secondary_cache.set(key, value, ttl)
        except Exception as e:
            logger.warning(f"Failed to set key {key} in secondary cache: {str(e)}")
        
        # Return True if at least one cache operation succeeded
        return primary_success or secondary_success
    
    def delete(self, key: str) -> bool:
        """
        Remove a value from both primary and secondary caches.
        
        Args:
            key: Cache key
            
        Returns:
            True if the key was found and deleted from at least one cache
        """
        # Try to delete from both caches
        primary_success = False
        secondary_success = False
        
        try:
            primary_success = self._primary_cache.delete(key)
        except Exception as e:
            logger.warning(f"Failed to delete key {key} from primary cache: {str(e)}")
        
        try:
            secondary_success = self._secondary_cache.delete(key)
        except Exception as e:
            logger.warning(f"Failed to delete key {key} from secondary cache: {str(e)}")
        
        # Return True if at least one delete operation succeeded
        return primary_success or secondary_success
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in either primary or secondary cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if the key exists in at least one cache
        """
        # Check primary cache first
        if self._primary_cache.exists(key):
            return True
        
        # If not in primary, check secondary
        return self._secondary_cache.exists(key)
    
    def flush(self) -> bool:
        """
        Clear all values from both primary and secondary caches.
        
        Returns:
            True if at least one cache was successfully cleared
        """
        # Try to flush both caches
        primary_success = False
        secondary_success = False
        
        try:
            primary_success = self._primary_cache.flush()
        except Exception as e:
            logger.warning(f"Failed to flush primary cache: {str(e)}")
        
        try:
            secondary_success = self._secondary_cache.flush()
        except Exception as e:
            logger.warning(f"Failed to flush secondary cache: {str(e)}")
        
        # Return True if at least one flush operation succeeded
        return primary_success or secondary_success


class NullCacheStrategy(CacheStrategy):
    """
    No-op cache strategy that doesn't actually cache anything.
    
    Useful for testing or when caching needs to be disabled.
    """
    
    def __init__(self):
        """
        Initialize the null cache strategy.
        """
        logger.info("Initialized NullCacheStrategy - caching disabled")
    
    def get(self, key: str, value_type: Optional[str] = None) -> None:
        """
        Always returns None as if cache miss.
        
        Args:
            key: Cache key
            value_type: Optional type hint for conversion
            
        Returns:
            None: Always returns None
        """
        logger.debug(f"NullCache get operation for key: {key} (always misses)")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        No-op implementation that pretends to cache.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (optional)
            
        Returns:
            bool: Always returns True
        """
        logger.debug(f"NullCache set operation for key: {key} (no-op)")
        return True
    
    def delete(self, key: str) -> bool:
        """
        No-op implementation that pretends to delete.
        
        Args:
            key: Cache key
            
        Returns:
            bool: Always returns True
        """
        logger.debug(f"NullCache delete operation for key: {key} (no-op)")
        return True
    
    def exists(self, key: str) -> bool:
        """
        Always returns False as if key doesn't exist.
        
        Args:
            key: Cache key
            
        Returns:
            bool: Always returns False
        """
        return False
    
    def flush(self) -> bool:
        """
        No-op implementation that pretends to flush.
        
        Returns:
            bool: Always returns True
        """
        logger.debug("NullCache flush operation (no-op)")
        return True