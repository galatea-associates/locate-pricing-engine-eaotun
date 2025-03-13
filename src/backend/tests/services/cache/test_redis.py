"""
Unit tests for the Redis cache implementation in the Borrow Rate & Locate Fee Pricing Engine.

This module tests the RedisCache class functionality including connection management,
cache operations (get, set, delete, exists, flush), error handling, and reconnection logic.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
import fakeredis
import redis  # redis 4.5.0+

from ../../../services/cache/redis import RedisCache
from ../../../services/cache/utils import (
    serialize_cache_value,
    deserialize_cache_value,
    wrap_cache_value,
    unwrap_cache_value,
    get_ttl_for_data_type
)
from ../../../core/constants import (
    CACHE_TTL_BORROW_RATE,
    CACHE_TTL_VOLATILITY,
    CACHE_TTL_EVENT_RISK,
    CACHE_TTL_BROKER_CONFIG,
    CACHE_TTL_CALCULATION
)


def test_redis_cache_initialization():
    """Tests the initialization of RedisCache with various parameters"""
    # Test initialization with default parameters
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        
        redis_cache = RedisCache(host='localhost', port=6379)
        
        # Verify Redis client was initialized with correct parameters
        mock_redis.assert_called_once_with(
            host='localhost',
            port=6379,
            password=None,
            db=0,
            socket_timeout=5,
            socket_connect_timeout=2,
            decode_responses=True
        )
        
        # Verify default prefix
        assert redis_cache._prefix == "borrow_rate_engine:"
        
        # Verify connection attempt was made
        assert redis_cache._connected is True
        
    # Test initialization with custom parameters
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        
        redis_cache = RedisCache(
            host='redis.example.com',
            port=6380,
            password='secret',
            db=1,
            prefix='custom:',
            socket_timeout=10,
            socket_connect_timeout=5,
            max_connection_retries=5
        )
        
        # Verify Redis client was initialized with correct parameters
        mock_redis.assert_called_once_with(
            host='redis.example.com',
            port=6380,
            password='secret',
            db=1,
            socket_timeout=10,
            socket_connect_timeout=5,
            decode_responses=True
        )
        
        # Verify custom prefix
        assert redis_cache._prefix == "custom:"
        
        # Verify max retries
        assert redis_cache._max_connection_retries == 5


def test_redis_cache_connect():
    """Tests the connect method of RedisCache"""
    # Test successful connection
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        
        redis_cache = RedisCache(host='localhost', port=6379)
        
        # Reset connection status for testing
        redis_cache._connected = False
        redis_cache._connection_retry_count = 2
        
        # Test connect method
        result = redis_cache.connect()
        
        # Verify connect returns True on success
        assert result is True
        
        # Verify _connected flag is set to True
        assert redis_cache._connected is True
        
        # Verify retry count is reset
        assert redis_cache._connection_retry_count == 0
        
    # Test failed connection
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.side_effect = redis.RedisError("Connection refused")
        
        redis_cache = RedisCache(host='localhost', port=6379)
        
        # Reset connection for testing
        redis_cache._connected = True
        
        # Test connect method
        result = redis_cache.connect()
        
        # Verify connect returns False on failure
        assert result is False
        
        # Verify _connected flag is set to False
        assert redis_cache._connected is False


def test_redis_cache_is_connected():
    """Tests the is_connected method of RedisCache"""
    # Test successful ping
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        
        redis_cache = RedisCache(host='localhost', port=6379)
        
        # Reset connection status for testing
        redis_cache._connected = False
        
        # Test is_connected method
        result = redis_cache.is_connected()
        
        # Verify is_connected returns True on successful ping
        assert result is True
        
        # Verify _connected flag is updated
        assert redis_cache._connected is True
        
    # Test failed ping
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.side_effect = redis.RedisError("Connection refused")
        
        redis_cache = RedisCache(host='localhost', port=6379)
        
        # Set connection status for testing
        redis_cache._connected = True
        
        # Test is_connected method
        result = redis_cache.is_connected()
        
        # Verify is_connected returns False on failed ping
        assert result is False
        
        # Verify _connected flag is updated
        assert redis_cache._connected is False


def test_redis_cache_get_full_key():
    """Tests the _get_full_key method of RedisCache"""
    # Test with default prefix
    redis_cache = RedisCache(host='localhost', port=6379)
    
    # Patch ping method to prevent actual connection attempt
    with patch.object(redis_cache, 'connect'):
        # Test key generation with default prefix
        full_key = redis_cache._get_full_key("test_key")
        assert full_key == "borrow_rate_engine:test_key"
        
    # Test with custom prefix
    redis_cache = RedisCache(host='localhost', port=6379, prefix="custom:")
    
    # Patch ping method to prevent actual connection attempt
    with patch.object(redis_cache, 'connect'):
        # Test key generation with custom prefix
        full_key = redis_cache._get_full_key("test_key")
        assert full_key == "custom:test_key"


def test_redis_cache_get():
    """Tests the get method of RedisCache"""
    # Create Redis cache instance with fakeredis
    server = fakeredis.FakeServer()
    fake_redis = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    
    with patch('redis.Redis', return_value=fake_redis):
        redis_cache = RedisCache(host='localhost', port=6379)
        
        # Set a test value
        test_key = "test_key"
        test_value = "test_value"
        full_key = redis_cache._get_full_key(test_key)
        
        # Serialize and store test value
        wrapped_value = wrap_cache_value(test_value)
        serialized_value = serialize_cache_value(wrapped_value)
        fake_redis.set(full_key, serialized_value)
        
        # Test get method
        result = redis_cache.get(test_key)
        
        # Verify correct value is returned
        assert result == test_value
        
        # Test with non-existent key
        non_existent_result = redis_cache.get("non_existent_key")
        assert non_existent_result is None
        
    # Test with disconnected Redis
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = False
        
        redis_cache = RedisCache(host='localhost', port=6379)
        redis_cache._connected = False
        
        # Test get with disconnected Redis
        result = redis_cache.get("test_key")
        
        # Verify None is returned when disconnected
        assert result is None
        
    # Test with Redis error
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        mock_instance.get.side_effect = redis.RedisError("Redis error")
        
        # Patch backoff to avoid actual retries in testing
        with patch('backoff.on_exception', lambda *args, **kwargs: lambda func: func):
            redis_cache = RedisCache(host='localhost', port=6379)
            
            # Test get with Redis error
            with pytest.raises(redis.RedisError):
                redis_cache.get("test_key")


def test_redis_cache_set():
    """Tests the set method of RedisCache"""
    # Create Redis cache instance with fakeredis
    server = fakeredis.FakeServer()
    fake_redis = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    
    with patch('redis.Redis', return_value=fake_redis):
        redis_cache = RedisCache(host='localhost', port=6379)
        
        # Test setting a string value
        test_key = "test_string_key"
        test_value = "test_string_value"
        ttl = 60
        
        # Set the value
        result = redis_cache.set(test_key, test_value, ttl)
        
        # Verify set was successful
        assert result is True
        
        # Verify key exists in Redis
        full_key = redis_cache._get_full_key(test_key)
        assert fake_redis.exists(full_key) == 1
        
        # Verify TTL was set
        assert fake_redis.ttl(full_key) <= ttl and fake_redis.ttl(full_key) > 0
        
        # Verify value can be retrieved
        retrieved_value = redis_cache.get(test_key)
        assert retrieved_value == test_value
        
        # Test setting a numeric value
        test_key = "test_numeric_key"
        test_value = 12345
        
        # Set the value
        result = redis_cache.set(test_key, test_value, ttl)
        
        # Verify set was successful
        assert result is True
        
        # Verify value can be retrieved
        retrieved_value = redis_cache.get(test_key)
        assert retrieved_value == test_value
        
        # Test setting a dictionary value
        test_key = "test_dict_key"
        test_value = {"name": "John", "age": 30}
        
        # Set the value
        result = redis_cache.set(test_key, test_value, ttl)
        
        # Verify set was successful
        assert result is True
        
        # Verify value can be retrieved
        retrieved_value = redis_cache.get(test_key)
        assert retrieved_value == test_value
        
        # Test setting without explicit TTL (using key pattern)
        test_key = "borrow_rate:AAPL"
        test_value = 0.05
        
        # Set the value without TTL
        result = redis_cache.set(test_key, test_value)
        
        # Verify set was successful
        assert result is True
        
        # Verify TTL was set based on key pattern
        full_key = redis_cache._get_full_key(test_key)
        assert fake_redis.ttl(full_key) <= CACHE_TTL_BORROW_RATE and fake_redis.ttl(full_key) > 0
        
    # Test with disconnected Redis
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = False
        
        redis_cache = RedisCache(host='localhost', port=6379)
        redis_cache._connected = False
        
        # Test set with disconnected Redis
        result = redis_cache.set("test_key", "test_value")
        
        # Verify False is returned when disconnected
        assert result is False
        
    # Test with Redis error
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        mock_instance.setex.side_effect = redis.RedisError("Redis error")
        
        # Patch backoff to avoid actual retries in testing
        with patch('backoff.on_exception', lambda *args, **kwargs: lambda func: func):
            redis_cache = RedisCache(host='localhost', port=6379)
            
            # Test set with Redis error
            with pytest.raises(redis.RedisError):
                redis_cache.set("test_key", "test_value")


def test_redis_cache_delete():
    """Tests the delete method of RedisCache"""
    # Create Redis cache instance with fakeredis
    server = fakeredis.FakeServer()
    fake_redis = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    
    with patch('redis.Redis', return_value=fake_redis):
        redis_cache = RedisCache(host='localhost', port=6379)
        
        # Set a test value
        test_key = "test_key"
        test_value = "test_value"
        
        # Set the value
        redis_cache.set(test_key, test_value)
        
        # Verify key exists
        full_key = redis_cache._get_full_key(test_key)
        assert fake_redis.exists(full_key) == 1
        
        # Test delete method
        result = redis_cache.delete(test_key)
        
        # Verify delete was successful
        assert result is True
        
        # Verify key no longer exists
        assert fake_redis.exists(full_key) == 0
        
        # Test delete with non-existent key
        result = redis_cache.delete("non_existent_key")
        
        # Verify delete returns False for non-existent key
        assert result is False
        
    # Test with disconnected Redis
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = False
        
        redis_cache = RedisCache(host='localhost', port=6379)
        redis_cache._connected = False
        
        # Test delete with disconnected Redis
        result = redis_cache.delete("test_key")
        
        # Verify False is returned when disconnected
        assert result is False
        
    # Test with Redis error
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        mock_instance.delete.side_effect = redis.RedisError("Redis error")
        
        # Patch backoff to avoid actual retries in testing
        with patch('backoff.on_exception', lambda *args, **kwargs: lambda func: func):
            redis_cache = RedisCache(host='localhost', port=6379)
            
            # Test delete with Redis error
            with pytest.raises(redis.RedisError):
                redis_cache.delete("test_key")


def test_redis_cache_exists():
    """Tests the exists method of RedisCache"""
    # Create Redis cache instance with fakeredis
    server = fakeredis.FakeServer()
    fake_redis = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    
    with patch('redis.Redis', return_value=fake_redis):
        redis_cache = RedisCache(host='localhost', port=6379)
        
        # Set a test value
        test_key = "test_key"
        test_value = "test_value"
        
        # Set the value
        redis_cache.set(test_key, test_value)
        
        # Test exists method with existing key
        result = redis_cache.exists(test_key)
        
        # Verify exists returns True for existing key
        assert result is True
        
        # Test exists with non-existent key
        result = redis_cache.exists("non_existent_key")
        
        # Verify exists returns False for non-existent key
        assert result is False
        
    # Test with disconnected Redis
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = False
        
        redis_cache = RedisCache(host='localhost', port=6379)
        redis_cache._connected = False
        
        # Test exists with disconnected Redis
        result = redis_cache.exists("test_key")
        
        # Verify False is returned when disconnected
        assert result is False
        
    # Test with Redis error
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        mock_instance.exists.side_effect = redis.RedisError("Redis error")
        
        # Patch backoff to avoid actual retries in testing
        with patch('backoff.on_exception', lambda *args, **kwargs: lambda func: func):
            redis_cache = RedisCache(host='localhost', port=6379)
            
            # Test exists with Redis error
            with pytest.raises(redis.RedisError):
                redis_cache.exists("test_key")


def test_redis_cache_flush():
    """Tests the flush method of RedisCache"""
    # Create Redis cache instance with fakeredis
    server = fakeredis.FakeServer()
    fake_redis = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    
    with patch('redis.Redis', return_value=fake_redis):
        redis_cache = RedisCache(host='localhost', port=6379, prefix="test_prefix:")
        
        # Set multiple test values with different prefixes
        redis_cache.set("key1", "value1")
        redis_cache.set("key2", "value2")
        
        # Set a key with a different prefix directly
        other_key = "other_prefix:key3"
        wrapped_value = wrap_cache_value("value3")
        serialized_value = serialize_cache_value(wrapped_value)
        fake_redis.set(other_key, serialized_value)
        
        # Test flush method
        result = redis_cache.flush()
        
        # Verify flush was successful
        assert result is True
        
        # Verify keys with test_prefix are removed
        assert redis_cache.exists("key1") is False
        assert redis_cache.exists("key2") is False
        
        # Verify key with different prefix still exists
        assert fake_redis.exists("other_prefix:key3") == 1
        
    # Test with disconnected Redis
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = False
        
        redis_cache = RedisCache(host='localhost', port=6379)
        redis_cache._connected = False
        
        # Test flush with disconnected Redis
        result = redis_cache.flush()
        
        # Verify False is returned when disconnected
        assert result is False
        
    # Test with Redis error
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        mock_instance.keys.return_value = ["key1", "key2"]
        mock_instance.delete.side_effect = redis.RedisError("Redis error")
        
        # Patch backoff to avoid actual retries in testing
        with patch('backoff.on_exception', lambda *args, **kwargs: lambda func: func):
            redis_cache = RedisCache(host='localhost', port=6379)
            
            # Test flush with Redis error
            with pytest.raises(redis.RedisError):
                redis_cache.flush()


def test_redis_cache_get_stats():
    """Tests the get_stats method of RedisCache"""
    # Create Redis cache instance with fakeredis
    server = fakeredis.FakeServer()
    fake_redis = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    
    with patch('redis.Redis', return_value=fake_redis), \
         patch.object(fake_redis, 'info', return_value={
             "used_memory_human": "1M",
             "uptime_in_seconds": 3600,
             "connected_clients": 1
         }):
        redis_cache = RedisCache(host='localhost', port=6379)
        
        # Set test values with different prefixes
        redis_cache.set("borrow_rate:AAPL", 0.05)
        redis_cache.set("volatility:AAPL", 25.5)
        redis_cache.set("event_risk:AAPL", 5)
        redis_cache.set("broker_config:client123", {"markup": 0.1})
        redis_cache.set("calculation:AAPL:client123:100000:30", 150.0)
        redis_cache.set("other:some_key", "some_value")
        
        # Test get_stats method
        stats = redis_cache.get_stats()
        
        # Verify stats structure
        assert "connected" in stats
        assert "keys_count" in stats
        assert "memory_used" in stats
        assert "categories" in stats
        
        # Verify connection status
        assert stats["connected"] is True
        
        # Verify key count
        assert stats["keys_count"] == 6
        
        # Verify memory usage
        assert stats["memory_used"] == "1M"
        
        # Verify categories
        categories = stats["categories"]
        assert categories["borrow_rate"] == 1
        assert categories["volatility"] == 1
        assert categories["event_risk"] == 1
        assert categories["broker_config"] == 1
        assert categories["calculation"] == 1
        assert categories["other"] == 1
        
    # Test with disconnected Redis
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = False
        
        redis_cache = RedisCache(host='localhost', port=6379)
        redis_cache._connected = False
        
        # Test get_stats with disconnected Redis
        stats = redis_cache.get_stats()
        
        # Verify empty stats are returned when disconnected
        assert stats["connected"] is False
        assert stats["keys_count"] == 0
        assert stats["memory_used"] == 0
        
    # Test with Redis error
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        mock_instance.info.side_effect = redis.RedisError("Redis error")
        
        # Patch backoff to avoid actual retries in testing
        with patch('backoff.on_exception', lambda *args, **kwargs: lambda func: func):
            redis_cache = RedisCache(host='localhost', port=6379)
            
            # Test get_stats with Redis error
            with pytest.raises(redis.RedisError):
                redis_cache.get_stats()


def test_redis_cache_health_check():
    """Tests the health_check method of RedisCache"""
    # Test successful health check
    with patch('redis.Redis') as mock_redis, \
         patch('time.time', side_effect=[100.0, 100.1]):  # Mock time.time() to return consistent values for response time calculation
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        mock_instance.info.return_value = {
            "redis_version": "6.2.6",
            "uptime_in_seconds": 3600,
            "connected_clients": 10,
            "used_memory_human": "1M"
        }
        
        redis_cache = RedisCache(host='localhost', port=6379)
        
        # Test health_check method
        health = redis_cache.health_check()
        
        # Verify health check structure
        assert "connected" in health
        assert "response_time_ms" in health
        assert "server_info" in health
        
        # Verify connection status
        assert health["connected"] is True
        
        # Verify response time (100ms based on our mock time values)
        assert health["response_time_ms"] == 100.0
        
        # Verify server info
        server_info = health["server_info"]
        assert server_info["redis_version"] == "6.2.6"
        assert server_info["uptime_in_seconds"] == 3600
        assert server_info["connected_clients"] == 10
        assert server_info["used_memory_human"] == "1M"
        
    # Test failed health check
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.side_effect = redis.RedisError("Connection refused")
        
        redis_cache = RedisCache(host='localhost', port=6379)
        
        # Test health_check method with error
        health = redis_cache.health_check()
        
        # Verify connection status
        assert health["connected"] is False
        
        # Verify error is included
        assert "error" in health
        assert "Connection refused" in health["error"]


def test_redis_cache_reconnect():
    """Tests the reconnect method of RedisCache"""
    # Test successful reconnection
    with patch('redis.Redis') as mock_redis, \
         patch('time.sleep') as mock_sleep:  # Mock sleep to avoid actual delays
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.return_value = True
        
        redis_cache = RedisCache(host='localhost', port=6379)
        
        # Set up reconnection test
        redis_cache._connected = False
        redis_cache._connection_retry_count = 2
        
        # Test reconnect method
        result = redis_cache.reconnect()
        
        # Verify reconnect returns True on success
        assert result is True
        
        # Verify _connected flag is updated
        assert redis_cache._connected is True
        
        # Verify retry count is reset
        assert redis_cache._connection_retry_count == 0
        
        # Verify sleep was called with exponential backoff
        mock_sleep.assert_called_once_with(2)  # 2^(retry_count-1) = 2^1 = 2
        
    # Test failed reconnection with max retries
    with patch('redis.Redis') as mock_redis, \
         patch('time.sleep') as mock_sleep:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        mock_instance.ping.side_effect = redis.RedisError("Connection refused")
        
        redis_cache = RedisCache(
            host='localhost',
            port=6379,
            max_connection_retries=3
        )
        
        # Set up reconnection test at max retries
        redis_cache._connected = False
        redis_cache._connection_retry_count = 3
        
        # Test reconnect method
        result = redis_cache.reconnect()
        
        # Verify reconnect returns False at max retries
        assert result is False
        
        # Verify _connected flag remains False
        assert redis_cache._connected is False
        
        # Verify retry count is incremented
        assert redis_cache._connection_retry_count == 4


def test_redis_cache_error_handling():
    """Tests error handling in RedisCache methods"""
    # Test different Redis errors with get method
    for error_type in [redis.ConnectionError, redis.TimeoutError, redis.RedisError]:
        with patch('redis.Redis') as mock_redis:
            mock_instance = MagicMock()
            mock_redis.return_value = mock_instance
            mock_instance.ping.return_value = True
            mock_instance.get.side_effect = error_type("Redis error")
            
            # Patch backoff to avoid actual retries in testing
            with patch('backoff.on_exception', lambda *args, **kwargs: lambda func: func):
                redis_cache = RedisCache(host='localhost', port=6379)
                
                # Test get with Redis error
                with pytest.raises(error_type):
                    redis_cache.get("test_key")
    
    # Test different Redis errors with set method
    for error_type in [redis.ConnectionError, redis.TimeoutError, redis.RedisError]:
        with patch('redis.Redis') as mock_redis:
            mock_instance = MagicMock()
            mock_redis.return_value = mock_instance
            mock_instance.ping.return_value = True
            mock_instance.setex.side_effect = error_type("Redis error")
            
            # Patch backoff to avoid actual retries in testing
            with patch('backoff.on_exception', lambda *args, **kwargs: lambda func: func):
                redis_cache = RedisCache(host='localhost', port=6379)
                
                # Test set with Redis error
                with pytest.raises(error_type):
                    redis_cache.set("test_key", "test_value")
    
    # Test different Redis errors with delete method
    for error_type in [redis.ConnectionError, redis.TimeoutError, redis.RedisError]:
        with patch('redis.Redis') as mock_redis:
            mock_instance = MagicMock()
            mock_redis.return_value = mock_instance
            mock_instance.ping.return_value = True
            mock_instance.delete.side_effect = error_type("Redis error")
            
            # Patch backoff to avoid actual retries in testing
            with patch('backoff.on_exception', lambda *args, **kwargs: lambda func: func):
                redis_cache = RedisCache(host='localhost', port=6379)
                
                # Test delete with Redis error
                with pytest.raises(error_type):
                    redis_cache.delete("test_key")
    
    # Test automatic reconnection attempt
    with patch('redis.Redis') as mock_redis, \
         patch('time.sleep') as mock_sleep:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        
        # First ping succeeds, then get fails with ConnectionError, then second ping succeeds
        mock_instance.ping.side_effect = [True, True]
        mock_instance.get.side_effect = redis.ConnectionError("Connection lost")
        
        # Patch backoff to avoid actual retries and call the function directly
        with patch('backoff.on_exception', lambda *args, **kwargs: lambda func: func):
            redis_cache = RedisCache(host='localhost', port=6379)
            
            # Test reconnection after connection error
            with pytest.raises(redis.ConnectionError):
                redis_cache.get("test_key")


@pytest.mark.integration
def test_redis_cache_with_fakeredis():
    """Integration test using fakeredis to test full functionality"""
    # Create Redis cache instance with fakeredis
    server = fakeredis.FakeServer()
    fake_redis = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    
    with patch('redis.Redis', return_value=fake_redis), \
         patch.object(fake_redis, 'info', return_value={
             "redis_version": "6.2.6",
             "uptime_in_seconds": 3600,
             "connected_clients": 1,
             "used_memory_human": "1M"
         }):
        redis_cache = RedisCache(host='localhost', port=6379)
        
        # Test connection
        assert redis_cache.is_connected() is True
        
        # Test setting and getting string value
        redis_cache.set("string_key", "string_value", 60)
        assert redis_cache.get("string_key") == "string_value"
        
        # Test setting and getting numeric value
        redis_cache.set("numeric_key", 12345, 60)
        assert redis_cache.get("numeric_key") == 12345
        
        # Test setting and getting dictionary value
        dict_value = {"name": "John", "age": 30}
        redis_cache.set("dict_key", dict_value, 60)
        assert redis_cache.get("dict_key") == dict_value
        
        # Test exists method
        assert redis_cache.exists("string_key") is True
        assert redis_cache.exists("non_existent_key") is False
        
        # Test delete method
        assert redis_cache.delete("string_key") is True
        assert redis_cache.exists("string_key") is False
        
        # Test automatic TTL selection based on key pattern
        redis_cache.set("borrow_rate:AAPL", 0.05)
        redis_cache.set("volatility:AAPL", 25.5)
        redis_cache.set("event_risk:AAPL", 5)
        redis_cache.set("broker_config:client123", {"markup": 0.1})
        redis_cache.set("calculation:AAPL:client123:100000:30", 150.0)
        
        # Verify all keys exist
        assert redis_cache.exists("borrow_rate:AAPL") is True
        assert redis_cache.exists("volatility:AAPL") is True
        assert redis_cache.exists("event_risk:AAPL") is True
        assert redis_cache.exists("broker_config:client123") is True
        assert redis_cache.exists("calculation:AAPL:client123:100000:30") is True
        
        # Test get_stats
        stats = redis_cache.get_stats()
        assert stats["connected"] is True
        assert stats["keys_count"] == 5
        
        # Verify categories
        categories = stats["categories"]
        assert categories["borrow_rate"] == 1
        assert categories["volatility"] == 1
        assert categories["event_risk"] == 1
        assert categories["broker_config"] == 1
        assert categories["calculation"] == 1
        
        # Test health check
        health = redis_cache.health_check()
        assert health["connected"] is True
        
        # Test flush
        assert redis_cache.flush() is True
        
        # Verify all keys are removed
        assert redis_cache.exists("borrow_rate:AAPL") is False
        assert redis_cache.exists("volatility:AAPL") is False
        assert redis_cache.exists("event_risk:AAPL") is False
        assert redis_cache.exists("broker_config:client123") is False
        assert redis_cache.exists("calculation:AAPL:client123:100000:30") is False