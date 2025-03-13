"""
Redis Cache Service for the Borrow Rate & Locate Fee Pricing Engine.

This module implements a Redis-based caching service that provides a high-performance
distributed caching layer for storing frequently accessed data such as borrow rates,
volatility metrics, and broker configurations with appropriate TTLs. It serves as the
L2 cache in the multi-level caching strategy and includes connection management,
error handling, and fallback mechanisms.
"""

import redis  # redis 4.5.0+
import time
from typing import Any, Dict, Optional
import backoff  # backoff 2.2.0+

from .utils import (
    serialize_cache_value,
    deserialize_cache_value,
    wrap_cache_value,
    unwrap_cache_value,
    is_cache_stale,
    log_cache_operation,
    get_ttl_for_data_type
)
from ...config.settings import get_settings
from ...core.logging import get_logger
from ...core.constants import (
    CACHE_TTL_BORROW_RATE,
    CACHE_TTL_VOLATILITY,
    CACHE_TTL_EVENT_RISK,
    CACHE_TTL_BROKER_CONFIG,
    CACHE_TTL_CALCULATION
)

# Initialize logger
logger = get_logger(__name__)


class RedisCache:
    """Redis-based cache implementation for storing and retrieving cached data."""
    
    def __init__(
        self,
        host: str,
        port: int,
        password: Optional[str] = None,
        db: Optional[int] = 0,
        prefix: Optional[str] = None,
        socket_timeout: Optional[int] = 5,
        socket_connect_timeout: Optional[int] = 2,
        max_connection_retries: Optional[int] = 3
    ):
        """
        Initialize the Redis cache with connection parameters.
        
        Args:
            host: Redis server hostname or IP
            port: Redis server port
            password: Redis server password, if required
            db: Redis database number
            prefix: Key prefix for all cache entries
            socket_timeout: Socket operation timeout in seconds
            socket_connect_timeout: Socket connection timeout in seconds
            max_connection_retries: Maximum number of connection retry attempts
        """
        # Initialize Redis client with connection parameters
        self._client = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            decode_responses=True
        )
        
        # Set default key prefix if not provided
        self._prefix = prefix or "borrow_rate_engine:"
        
        # Initialize connection state
        self._connected = False
        self._connection_retry_count = 0
        self._max_connection_retries = max_connection_retries
        
        # Try to establish connection
        try:
            self.connect()
            logger.info(f"Redis cache initialized - Connected to {host}:{port} (db: {db})")
        except redis.RedisError as e:
            logger.warning(f"Failed to initialize Redis cache connection: {e}")
    
    def connect(self) -> bool:
        """
        Establish connection to Redis server.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Test connection with ping
            self._client.ping()
            self._connected = True
            self._connection_retry_count = 0
            logger.info("Connected to Redis server")
            return True
        except redis.RedisError as e:
            self._connected = False
            logger.error(f"Failed to connect to Redis server: {e}")
            return False
    
    def is_connected(self) -> bool:
        """
        Check if Redis client is connected to server.
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            self._client.ping()
            self._connected = True
            return True
        except redis.RedisError:
            self._connected = False
            return False
    
    def _get_full_key(self, key: str) -> str:
        """
        Generate a full Redis key with prefix.
        
        Args:
            key: Base key without prefix
            
        Returns:
            str: Full key with prefix
        """
        return f"{self._prefix}{key}"
    
    @backoff.on_exception(backoff.expo, redis.RedisError, max_tries=3)
    def get(self, key: str, value_type: Optional[str] = None) -> Optional[Any]:
        """
        Retrieve a value from Redis by key.
        
        Args:
            key: Cache key without prefix
            value_type: Optional type hint for deserialization
            
        Returns:
            Optional[Any]: The cached value or None if not found or expired
        """
        # Check connection status
        if not self._connected and not self.is_connected():
            log_cache_operation("get", key, False, "Redis not connected")
            return None
        
        full_key = self._get_full_key(key)
        
        try:
            # Get value from Redis
            serialized_value = self._client.get(full_key)
            
            # Return None if key not found
            if serialized_value is None:
                log_cache_operation("get", key, False, "Cache miss")
                return None
            
            # Deserialize the value
            wrapped_value = deserialize_cache_value(serialized_value)
            
            # Ensure we got a valid value
            if wrapped_value is None:
                log_cache_operation("get", key, False, "Deserialization failed")
                return None
            
            # Unwrap the value to get the actual data
            value = unwrap_cache_value(wrapped_value)
            
            log_cache_operation("get", key, True, "Cache hit")
            return value
            
        except redis.RedisError as e:
            log_cache_operation("get", key, False, f"Redis error: {str(e)}")
            # Let backoff handle retry or raise exception
            raise
    
    @backoff.on_exception(backoff.expo, redis.RedisError, max_tries=3)
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Store a value in Redis with the specified key and TTL.
        
        Args:
            key: Cache key without prefix
            value: Value to cache
            ttl: Time-to-live in seconds, if None will use appropriate default
            
        Returns:
            bool: True if the value was successfully cached, False otherwise
        """
        # Check connection status
        if not self._connected and not self.is_connected():
            log_cache_operation("set", key, False, "Redis not connected")
            return False
        
        # Determine TTL based on key pattern if not specified
        if ttl is None:
            # Extract data type from the key
            if key.startswith("borrow_rate:"):
                ttl = CACHE_TTL_BORROW_RATE
            elif key.startswith("volatility:"):
                ttl = CACHE_TTL_VOLATILITY
            elif key.startswith("event_risk:"):
                ttl = CACHE_TTL_EVENT_RISK
            elif key.startswith("broker_config:"):
                ttl = CACHE_TTL_BROKER_CONFIG
            elif key.startswith("calculation:"):
                ttl = CACHE_TTL_CALCULATION
            else:
                # Use default calculation TTL for unknown types
                ttl = CACHE_TTL_CALCULATION
        
        full_key = self._get_full_key(key)
        
        try:
            # Wrap the value with metadata
            wrapped_value = wrap_cache_value(value)
            
            # Serialize the wrapped value
            serialized_value = serialize_cache_value(wrapped_value)
            
            # Store in Redis with TTL
            self._client.setex(full_key, ttl, serialized_value)
            
            log_cache_operation("set", key, True, f"TTL: {ttl}s")
            return True
            
        except redis.RedisError as e:
            log_cache_operation("set", key, False, f"Redis error: {str(e)}")
            # Let backoff handle retry or raise exception
            raise
    
    @backoff.on_exception(backoff.expo, redis.RedisError, max_tries=3)
    def delete(self, key: str) -> bool:
        """
        Remove a value from Redis by key.
        
        Args:
            key: Cache key without prefix
            
        Returns:
            bool: True if the key was found and deleted, False otherwise
        """
        # Check connection status
        if not self._connected and not self.is_connected():
            log_cache_operation("delete", key, False, "Redis not connected")
            return False
        
        full_key = self._get_full_key(key)
        
        try:
            # Delete key and check if any keys were deleted
            result = self._client.delete(full_key)
            
            if result > 0:
                log_cache_operation("delete", key, True, "Key deleted")
                return True
            else:
                log_cache_operation("delete", key, False, "Key not found")
                return False
                
        except redis.RedisError as e:
            log_cache_operation("delete", key, False, f"Redis error: {str(e)}")
            # Let backoff handle retry or raise exception
            raise
    
    @backoff.on_exception(backoff.expo, redis.RedisError, max_tries=3)
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        
        Args:
            key: Cache key without prefix
            
        Returns:
            bool: True if the key exists, False otherwise
        """
        # Check connection status
        if not self._connected and not self.is_connected():
            return False
        
        full_key = self._get_full_key(key)
        
        try:
            # Check if key exists
            return bool(self._client.exists(full_key))
            
        except redis.RedisError as e:
            logger.warning(f"Error checking key existence: {e}")
            # Let backoff handle retry or raise exception
            raise
    
    @backoff.on_exception(backoff.expo, redis.RedisError, max_tries=3)
    def flush(self) -> bool:
        """
        Clear all values from Redis with the configured prefix.
        
        Returns:
            bool: True if the cache was successfully cleared, False otherwise
        """
        # Check connection status
        if not self._connected and not self.is_connected():
            logger.warning("Cannot flush cache: Redis not connected")
            return False
        
        try:
            # Find all keys with our prefix
            pattern = f"{self._prefix}*"
            keys = self._client.keys(pattern)
            
            if not keys:
                logger.info("No keys to flush")
                return True
            
            # Delete all matching keys
            self._client.delete(*keys)
            
            logger.info(f"Flushed {len(keys)} keys from Redis cache")
            return True
            
        except redis.RedisError as e:
            logger.error(f"Error flushing cache: {e}")
            # Let backoff handle retry or raise exception
            raise
    
    @backoff.on_exception(backoff.expo, redis.RedisError, max_tries=3)
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Redis cache.
        
        Returns:
            Dict[str, Any]: Dictionary with cache statistics
        """
        # Check connection status
        if not self._connected and not self.is_connected():
            logger.warning("Cannot get cache stats: Redis not connected")
            return {
                "connected": False,
                "keys_count": 0,
                "memory_used": 0,
                "categories": {}
            }
        
        try:
            # Get general Redis info
            info = self._client.info()
            
            # Get all keys with our prefix
            pattern = f"{self._prefix}*"
            all_keys = self._client.keys(pattern)
            
            # Count keys by category
            categories = {
                "borrow_rate": 0,
                "volatility": 0,
                "event_risk": 0,
                "broker_config": 0,
                "calculation": 0,
                "other": 0
            }
            
            # Categorize keys
            for key in all_keys:
                key_without_prefix = key.replace(self._prefix, "", 1)
                
                if key_without_prefix.startswith("borrow_rate:"):
                    categories["borrow_rate"] += 1
                elif key_without_prefix.startswith("volatility:"):
                    categories["volatility"] += 1
                elif key_without_prefix.startswith("event_risk:"):
                    categories["event_risk"] += 1
                elif key_without_prefix.startswith("broker_config:"):
                    categories["broker_config"] += 1
                elif key_without_prefix.startswith("calculation:"):
                    categories["calculation"] += 1
                else:
                    categories["other"] += 1
            
            # Build stats dictionary
            stats = {
                "connected": True,
                "keys_count": len(all_keys),
                "memory_used": info.get("used_memory_human", "unknown"),
                "uptime": info.get("uptime_in_seconds", 0),
                "categories": categories
            }
            
            return stats
            
        except redis.RedisError as e:
            logger.error(f"Error getting cache stats: {e}")
            # Let backoff handle retry or raise exception
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the Redis connection.
        
        Returns:
            Dict[str, Any]: Health check results with status and details
        """
        health_status = {
            "connected": False,
            "response_time_ms": None,
            "server_info": {}
        }
        
        try:
            # Measure response time
            start_time = time.time()
            pong = self._client.ping()
            end_time = time.time()
            
            # Calculate response time
            response_time_ms = round((end_time - start_time) * 1000, 2)
            
            # Get basic Redis info
            info = self._client.info()
            server_info = {
                "redis_version": info.get("redis_version", "unknown"),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown")
            }
            
            # Update health status
            health_status.update({
                "connected": pong,
                "response_time_ms": response_time_ms,
                "server_info": server_info
            })
            
            self._connected = True
            
        except redis.RedisError as e:
            self._connected = False
            logger.warning(f"Redis health check failed: {e}")
            health_status["error"] = str(e)
        
        return health_status
    
    def reconnect(self) -> bool:
        """
        Attempt to reconnect to Redis server.
        
        Returns:
            bool: True if reconnection successful, False otherwise
        """
        # Increment retry counter
        self._connection_retry_count += 1
        
        # Check if max retries reached
        if self._connection_retry_count > self._max_connection_retries:
            logger.error(f"Max reconnection attempts reached ({self._max_connection_retries})")
            return False
        
        logger.info(f"Attempting to reconnect to Redis (attempt {self._connection_retry_count}/{self._max_connection_retries})")
        
        # Implement exponential backoff
        backoff_seconds = 2 ** (self._connection_retry_count - 1)
        time.sleep(min(backoff_seconds, 30))  # Cap at 30 seconds
        
        # Attempt connection
        result = self.connect()
        
        if result:
            # Reset retry counter on success
            self._connection_retry_count = 0
            return True
        
        return False