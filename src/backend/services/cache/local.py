"""
Implements an in-memory local cache for the Borrow Rate & Locate Fee Pricing Engine.

This module provides a fast, process-local caching mechanism that serves as the L1 cache
in the multi-level caching strategy. It's designed for ultra-high-performance during 
calculation bursts and as a fallback when Redis is unavailable.
"""

import threading
import typing
import time
import sys

from .utils import (
    serialize_cache_value, deserialize_cache_value,
    wrap_cache_value, unwrap_cache_value,
    is_cache_stale, log_cache_operation
)
from ...core.logging import get_logger
from ...core.constants import (
    CACHE_TTL_BORROW_RATE, CACHE_TTL_VOLATILITY, CACHE_TTL_EVENT_RISK,
    CACHE_TTL_BROKER_CONFIG, CACHE_TTL_CALCULATION
)

# Initialize logger for cache operations
logger = get_logger(__name__)

class LocalCache:
    """
    Thread-safe in-memory cache implementation for storing and retrieving cached data.
    
    This implementation provides a fast, process-local caching mechanism that serves as 
    the L1 cache in the multi-level caching strategy. It's designed for ultra-high-performance 
    during calculation bursts and as a fallback when Redis is unavailable.
    """
    
    def __init__(self):
        """Initialize the local cache with an empty dictionary and thread lock."""
        self._cache = {}  # Dictionary to store cache entries
        self._lock = threading.Lock()  # Lock for thread safety
        logger.info("Initialized LocalCache")
    
    def get(self, key: str, value_type: typing.Optional[str] = None) -> typing.Optional[typing.Any]:
        """
        Retrieve a value from the local cache by key.
        
        Args:
            key: The cache key to retrieve
            value_type: Optional type hint for deserialization
            
        Returns:
            The cached value or None if not found or expired
        """
        with self._lock:  # Ensure thread safety during the operation
            # Check if key exists in cache
            if key not in self._cache:
                log_cache_operation("get", key, False, "Key not found")
                return None
            
            # Get wrapped value from cache
            wrapped_value = self._cache[key]
            
            # Determine TTL for this value
            ttl = self._get_ttl_for_key(key, wrapped_value)
            
            # Check if value is stale
            if is_cache_stale(wrapped_value, ttl):
                # Remove stale value
                del self._cache[key]
                log_cache_operation("get", key, False, "Value expired")
                return None
            
            # Extract serialized value from wrapped value
            serialized_value = unwrap_cache_value(wrapped_value)
            
            # Deserialize the value
            value = deserialize_cache_value(serialized_value, value_type)
            
            log_cache_operation("get", key, True)
            return value
    
    def set(self, key: str, value: typing.Any, ttl: typing.Optional[int] = None) -> bool:
        """
        Store a value in the local cache with the specified key and TTL.
        
        Args:
            key: The cache key
            value: The value to store
            ttl: Time-to-live in seconds (optional)
            
        Returns:
            True if the value was successfully cached
        """
        with self._lock:  # Ensure thread safety during the operation
            # Serialize the value
            serialized_value = serialize_cache_value(value)
            
            # Wrap the serialized value with metadata
            wrapped_value = wrap_cache_value(serialized_value)
            
            # If a custom TTL is provided, store it in the wrapped value
            if ttl is not None:
                wrapped_value['custom_ttl'] = ttl
            
            # Store in cache
            self._cache[key] = wrapped_value
            
            log_cache_operation("set", key, True)
            return True
    
    def delete(self, key: str) -> bool:
        """
        Remove a value from the local cache by key.
        
        Args:
            key: The cache key to remove
            
        Returns:
            True if the key was found and deleted, False otherwise
        """
        with self._lock:  # Ensure thread safety during the operation
            if key in self._cache:
                del self._cache[key]
                log_cache_operation("delete", key, True)
                return True
            else:
                log_cache_operation("delete", key, False, "Key not found")
                return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the local cache and is not expired.
        
        Args:
            key: The cache key to check
            
        Returns:
            True if the key exists and is not expired, False otherwise
        """
        with self._lock:  # Ensure thread safety during the operation
            if key not in self._cache:
                return False
            
            # Get wrapped value from cache
            wrapped_value = self._cache[key]
            
            # Determine TTL for this value
            ttl = self._get_ttl_for_key(key, wrapped_value)
            
            # Check if value is stale
            if is_cache_stale(wrapped_value, ttl):
                # Remove stale value
                del self._cache[key]
                return False
            
            return True
    
    def flush(self) -> bool:
        """
        Clear all values from the local cache.
        
        Returns:
            True if the cache was successfully cleared
        """
        with self._lock:  # Ensure thread safety during the operation
            self._cache.clear()
            log_cache_operation("flush", "all", True)
            return True
    
    def get_stats(self) -> dict:
        """
        Get statistics about the local cache.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:  # Ensure thread safety during the operation
            # Count total items
            total_items = len(self._cache)
            
            # Estimate memory usage (rough estimation)
            memory_usage = sys.getsizeof(self._cache)
            
            # Group by key prefix
            categories = {}
            for key in self._cache:
                prefix = key.split(':')[0] if ':' in key else 'unknown'
                categories[prefix] = categories.get(prefix, 0) + 1
            
            return {
                "items": total_items,
                "memory_bytes": memory_usage,
                "categories": categories
            }
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired items from the cache.
        
        Returns:
            Number of items removed
        """
        removed_count = 0
        with self._lock:  # Ensure thread safety during the operation
            # Find all expired keys
            expired_keys = []
            for key, wrapped_value in self._cache.items():
                ttl = self._get_ttl_for_key(key, wrapped_value)
                if is_cache_stale(wrapped_value, ttl):
                    expired_keys.append(key)
            
            # Remove expired keys
            for key in expired_keys:
                del self._cache[key]
                removed_count += 1
            
            if removed_count > 0:
                log_cache_operation("cleanup", "expired", True, f"Removed {removed_count} items")
            
            return removed_count
    
    def _get_ttl_for_key(self, key: str, wrapped_value: typing.Optional[dict] = None) -> int:
        """
        Determine the appropriate TTL for a key based on its prefix or custom TTL.
        
        Args:
            key: The cache key
            wrapped_value: Optional wrapped value for this key
            
        Returns:
            TTL in seconds
        """
        # Check if a custom TTL is stored in the wrapped value
        if wrapped_value is not None and 'custom_ttl' in wrapped_value:
            return wrapped_value['custom_ttl']
        
        # Otherwise determine TTL based on key prefix
        prefix = key.split(':')[0] if ':' in key else ""
        
        if prefix == "borrow_rate":
            return CACHE_TTL_BORROW_RATE
        elif prefix == "volatility":
            return CACHE_TTL_VOLATILITY
        elif prefix == "event_risk":
            return CACHE_TTL_EVENT_RISK
        elif prefix == "broker_config":
            return CACHE_TTL_BROKER_CONFIG
        else:  # Default to calculation TTL
            return CACHE_TTL_CALCULATION