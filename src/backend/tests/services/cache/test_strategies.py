import pytest
from unittest.mock import Mock, patch
import fakeredis

from src.backend.services.cache.strategies import (
    CacheStrategy,
    SingleCacheStrategy,
    TieredCacheStrategy,
    NullCacheStrategy,
    get_ttl_for_key_type
)
from src.backend.services.cache.local import LocalCache
from src.backend.services.cache.redis import RedisCache
from src.backend.core.constants import (
    CACHE_TTL_BORROW_RATE,
    CACHE_TTL_VOLATILITY,
    CACHE_TTL_EVENT_RISK,
    CACHE_TTL_BROKER_CONFIG,
    CACHE_TTL_CALCULATION
)


def test_get_ttl_for_key_type():
    """Tests the get_ttl_for_key_type function with various key prefixes"""
    # Test with borrow_rate prefix returns CACHE_TTL_BORROW_RATE
    assert get_ttl_for_key_type("borrow_rate:AAPL") == CACHE_TTL_BORROW_RATE
    
    # Test with volatility prefix returns CACHE_TTL_VOLATILITY
    assert get_ttl_for_key_type("volatility:AAPL") == CACHE_TTL_VOLATILITY
    
    # Test with event_risk prefix returns CACHE_TTL_EVENT_RISK
    assert get_ttl_for_key_type("event_risk:AAPL") == CACHE_TTL_EVENT_RISK
    
    # Test with broker_config prefix returns CACHE_TTL_BROKER_CONFIG
    assert get_ttl_for_key_type("broker_config:client123") == CACHE_TTL_BROKER_CONFIG
    
    # Test with calculation prefix returns CACHE_TTL_CALCULATION
    assert get_ttl_for_key_type("calculation:AAPL:client123:100000:30") == CACHE_TTL_CALCULATION
    
    # Test with unknown prefix returns CACHE_TTL_CALCULATION as default
    assert get_ttl_for_key_type("unknown:something") == CACHE_TTL_CALCULATION


def test_single_cache_strategy_initialization():
    """Tests the initialization of SingleCacheStrategy"""
    # Create mock cache object
    mock_cache = Mock()
    
    # Initialize SingleCacheStrategy with mock cache
    strategy = SingleCacheStrategy(mock_cache)
    
    # Verify _cache attribute is set correctly
    assert strategy._cache == mock_cache


def test_single_cache_strategy_get():
    """Tests the get method of SingleCacheStrategy"""
    # Create mock cache object with get method
    mock_cache = Mock()
    mock_cache.get.return_value = "test_value"
    
    # Initialize SingleCacheStrategy with mock cache
    strategy = SingleCacheStrategy(mock_cache)
    
    # Call get method with test key
    result = strategy.get("test_key")
    
    # Verify mock cache get method was called with correct parameters
    mock_cache.get.assert_called_once_with("test_key", None)
    
    # Verify strategy returns the value from the underlying cache
    assert result == "test_value"


def test_single_cache_strategy_set():
    """Tests the set method of SingleCacheStrategy"""
    # Create mock cache object with set method
    mock_cache = Mock()
    mock_cache.set.return_value = True
    
    # Initialize SingleCacheStrategy with mock cache
    strategy = SingleCacheStrategy(mock_cache)
    
    # Call set method with test key, value, and TTL
    result = strategy.set("test_key", "test_value", 60)
    
    # Verify mock cache set method was called with correct parameters
    mock_cache.set.assert_called_once_with("test_key", "test_value", 60)
    
    # Verify strategy returns the result from the underlying cache
    assert result is True
    
    # Test with TTL=None to verify TTL is determined from key type
    mock_cache.reset_mock()
    with patch('src.backend.services.cache.strategies.get_ttl_for_key_type') as mock_get_ttl:
        mock_get_ttl.return_value = 300
        result = strategy.set("borrow_rate:AAPL", "test_value")
        
        mock_get_ttl.assert_called_once_with("borrow_rate:AAPL")
        mock_cache.set.assert_called_once_with("borrow_rate:AAPL", "test_value", 300)


def test_single_cache_strategy_delete():
    """Tests the delete method of SingleCacheStrategy"""
    # Create mock cache object with delete method
    mock_cache = Mock()
    mock_cache.delete.return_value = True
    
    # Initialize SingleCacheStrategy with mock cache
    strategy = SingleCacheStrategy(mock_cache)
    
    # Call delete method with test key
    result = strategy.delete("test_key")
    
    # Verify mock cache delete method was called with correct parameters
    mock_cache.delete.assert_called_once_with("test_key")
    
    # Verify strategy returns the result from the underlying cache
    assert result is True


def test_single_cache_strategy_exists():
    """Tests the exists method of SingleCacheStrategy"""
    # Create mock cache object with exists method
    mock_cache = Mock()
    mock_cache.exists.return_value = True
    
    # Initialize SingleCacheStrategy with mock cache
    strategy = SingleCacheStrategy(mock_cache)
    
    # Call exists method with test key
    result = strategy.exists("test_key")
    
    # Verify mock cache exists method was called with correct parameters
    mock_cache.exists.assert_called_once_with("test_key")
    
    # Verify strategy returns the result from the underlying cache
    assert result is True


def test_single_cache_strategy_flush():
    """Tests the flush method of SingleCacheStrategy"""
    # Create mock cache object with flush method
    mock_cache = Mock()
    mock_cache.flush.return_value = True
    
    # Initialize SingleCacheStrategy with mock cache
    strategy = SingleCacheStrategy(mock_cache)
    
    # Call flush method
    result = strategy.flush()
    
    # Verify mock cache flush method was called
    mock_cache.flush.assert_called_once()
    
    # Verify strategy returns the result from the underlying cache
    assert result is True


def test_tiered_cache_strategy_initialization():
    """Tests the initialization of TieredCacheStrategy"""
    # Create mock primary and secondary cache objects
    mock_primary = Mock()
    mock_secondary = Mock()
    
    # Initialize TieredCacheStrategy with mock caches
    strategy = TieredCacheStrategy(mock_primary, mock_secondary)
    
    # Verify _primary_cache attribute is set correctly
    assert strategy._primary_cache == mock_primary
    # Verify _secondary_cache attribute is set correctly
    assert strategy._secondary_cache == mock_secondary


def test_tiered_cache_strategy_get_primary_hit():
    """Tests the get method of TieredCacheStrategy when primary cache has the value"""
    # Create mock primary cache that returns a value
    mock_primary = Mock()
    mock_primary.get.return_value = "primary_value"
    # Create mock secondary cache
    mock_secondary = Mock()
    
    # Initialize TieredCacheStrategy with mock caches
    strategy = TieredCacheStrategy(mock_primary, mock_secondary)
    
    # Call get method with test key
    result = strategy.get("test_key")
    
    # Verify primary cache get method was called with correct parameters
    mock_primary.get.assert_called_once_with("test_key", None)
    
    # Verify secondary cache get method was not called
    mock_secondary.get.assert_not_called()
    
    # Verify strategy returns the value from the primary cache
    assert result == "primary_value"


def test_tiered_cache_strategy_get_primary_miss_secondary_hit():
    """Tests the get method of TieredCacheStrategy when primary cache misses but secondary cache has the value"""
    # Create mock primary cache that returns None
    mock_primary = Mock()
    mock_primary.get.return_value = None
    # Create mock secondary cache that returns a value
    mock_secondary = Mock()
    mock_secondary.get.return_value = "secondary_value"
    
    # Initialize TieredCacheStrategy with mock caches
    strategy = TieredCacheStrategy(mock_primary, mock_secondary)
    
    # Call get method with test key
    with patch('src.backend.services.cache.strategies.get_ttl_for_key_type') as mock_get_ttl:
        mock_get_ttl.return_value = 300
        result = strategy.get("test_key")
        
        # Verify primary cache get method was called with correct parameters
        mock_primary.get.assert_called_once_with("test_key", None)
        
        # Verify secondary cache get method was called with correct parameters
        mock_secondary.get.assert_called_once_with("test_key", None)
        
        # Verify primary cache set method was called to update primary cache
        mock_primary.set.assert_called_once_with("test_key", "secondary_value", 300)
        
        # Verify strategy returns the value from the secondary cache
        assert result == "secondary_value"


def test_tiered_cache_strategy_get_both_miss():
    """Tests the get method of TieredCacheStrategy when both caches miss"""
    # Create mock primary cache that returns None
    mock_primary = Mock()
    mock_primary.get.return_value = None
    # Create mock secondary cache that returns None
    mock_secondary = Mock()
    mock_secondary.get.return_value = None
    
    # Initialize TieredCacheStrategy with mock caches
    strategy = TieredCacheStrategy(mock_primary, mock_secondary)
    
    # Call get method with test key
    result = strategy.get("test_key")
    
    # Verify primary cache get method was called with correct parameters
    mock_primary.get.assert_called_once_with("test_key", None)
    
    # Verify secondary cache get method was called with correct parameters
    mock_secondary.get.assert_called_once_with("test_key", None)
    
    # Verify primary cache set method was not called
    mock_primary.set.assert_not_called()
    
    # Verify strategy returns None
    assert result is None


def test_tiered_cache_strategy_set():
    """Tests the set method of TieredCacheStrategy"""
    # Create mock primary and secondary caches with set methods
    mock_primary = Mock()
    mock_primary.set.return_value = True
    mock_secondary = Mock()
    mock_secondary.set.return_value = True
    
    # Initialize TieredCacheStrategy with mock caches
    strategy = TieredCacheStrategy(mock_primary, mock_secondary)
    
    # Call set method with test key, value, and TTL
    result = strategy.set("test_key", "test_value", 60)
    
    # Verify primary cache set method was called with correct parameters
    mock_primary.set.assert_called_once_with("test_key", "test_value", 60)
    # Verify secondary cache set method was called with correct parameters
    mock_secondary.set.assert_called_once_with("test_key", "test_value", 60)
    
    # Verify strategy returns True
    assert result is True
    
    # Test with TTL=None to verify TTL is determined from key type
    mock_primary.reset_mock()
    mock_secondary.reset_mock()
    with patch('src.backend.services.cache.strategies.get_ttl_for_key_type') as mock_get_ttl:
        mock_get_ttl.return_value = 300
        result = strategy.set("borrow_rate:AAPL", "test_value")
        
        mock_get_ttl.assert_called_once_with("borrow_rate:AAPL")
        mock_primary.set.assert_called_once_with("borrow_rate:AAPL", "test_value", 300)
        mock_secondary.set.assert_called_once_with("borrow_rate:AAPL", "test_value", 300)
    
    # Test when primary cache set fails but secondary succeeds
    mock_primary.reset_mock()
    mock_secondary.reset_mock()
    mock_primary.set.side_effect = Exception("Primary cache failure")
    mock_secondary.set.return_value = True
    
    result = strategy.set("test_key", "test_value", 60)
    assert result is True
    
    # Test when secondary cache set fails but primary succeeds
    mock_primary.reset_mock()
    mock_secondary.reset_mock()
    mock_primary.set.side_effect = None
    mock_primary.set.return_value = True
    mock_secondary.set.side_effect = Exception("Secondary cache failure")
    
    result = strategy.set("test_key", "test_value", 60)
    assert result is True
    
    # Test when both caches fail
    mock_primary.reset_mock()
    mock_secondary.reset_mock()
    mock_primary.set.side_effect = Exception("Primary cache failure")
    mock_secondary.set.side_effect = Exception("Secondary cache failure")
    
    result = strategy.set("test_key", "test_value", 60)
    assert result is False


def test_tiered_cache_strategy_delete():
    """Tests the delete method of TieredCacheStrategy"""
    # Create mock primary and secondary caches with delete methods
    mock_primary = Mock()
    mock_primary.delete.return_value = True
    mock_secondary = Mock()
    mock_secondary.delete.return_value = True
    
    # Initialize TieredCacheStrategy with mock caches
    strategy = TieredCacheStrategy(mock_primary, mock_secondary)
    
    # Call delete method with test key
    result = strategy.delete("test_key")
    
    # Verify primary cache delete method was called with correct parameters
    mock_primary.delete.assert_called_once_with("test_key")
    # Verify secondary cache delete method was called with correct parameters
    mock_secondary.delete.assert_called_once_with("test_key")
    
    # Verify strategy returns True
    assert result is True
    
    # Test when primary cache delete fails but secondary succeeds
    mock_primary.reset_mock()
    mock_secondary.reset_mock()
    mock_primary.delete.side_effect = Exception("Primary cache failure")
    mock_secondary.delete.return_value = True
    
    result = strategy.delete("test_key")
    assert result is True
    
    # Test when secondary cache delete fails but primary succeeds
    mock_primary.reset_mock()
    mock_secondary.reset_mock()
    mock_primary.delete.side_effect = None
    mock_primary.delete.return_value = True
    mock_secondary.delete.side_effect = Exception("Secondary cache failure")
    
    result = strategy.delete("test_key")
    assert result is True
    
    # Test when both caches fail
    mock_primary.reset_mock()
    mock_secondary.reset_mock()
    mock_primary.delete.side_effect = Exception("Primary cache failure")
    mock_secondary.delete.side_effect = Exception("Secondary cache failure")
    
    result = strategy.delete("test_key")
    assert result is False


def test_tiered_cache_strategy_exists():
    """Tests the exists method of TieredCacheStrategy"""
    # Create mock primary cache that returns True for exists
    mock_primary = Mock()
    mock_primary.exists.return_value = True
    # Create mock secondary cache
    mock_secondary = Mock()
    
    # Initialize TieredCacheStrategy with mock caches
    strategy = TieredCacheStrategy(mock_primary, mock_secondary)
    
    # Call exists method with test key
    result = strategy.exists("test_key")
    
    # Verify primary cache exists method was called with correct parameters
    mock_primary.exists.assert_called_once_with("test_key")
    
    # Verify secondary cache exists method was not called
    mock_secondary.exists.assert_not_called()
    
    # Verify strategy returns True
    assert result is True
    
    # Test when primary cache returns False but secondary returns True
    mock_primary.reset_mock()
    mock_secondary.reset_mock()
    mock_primary.exists.return_value = False
    mock_secondary.exists.return_value = True
    
    result = strategy.exists("test_key")
    
    mock_primary.exists.assert_called_once_with("test_key")
    mock_secondary.exists.assert_called_once_with("test_key")
    assert result is True
    
    # Test when both caches return False
    mock_primary.reset_mock()
    mock_secondary.reset_mock()
    mock_primary.exists.return_value = False
    mock_secondary.exists.return_value = False
    
    result = strategy.exists("test_key")
    
    mock_primary.exists.assert_called_once_with("test_key")
    mock_secondary.exists.assert_called_once_with("test_key")
    assert result is False


def test_tiered_cache_strategy_flush():
    """Tests the flush method of TieredCacheStrategy"""
    # Create mock primary and secondary caches with flush methods
    mock_primary = Mock()
    mock_primary.flush.return_value = True
    mock_secondary = Mock()
    mock_secondary.flush.return_value = True
    
    # Initialize TieredCacheStrategy with mock caches
    strategy = TieredCacheStrategy(mock_primary, mock_secondary)
    
    # Call flush method
    result = strategy.flush()
    
    # Verify primary cache flush method was called
    mock_primary.flush.assert_called_once()
    # Verify secondary cache flush method was called
    mock_secondary.flush.assert_called_once()
    
    # Verify strategy returns True
    assert result is True
    
    # Test when primary cache flush fails but secondary succeeds
    mock_primary.reset_mock()
    mock_secondary.reset_mock()
    mock_primary.flush.side_effect = Exception("Primary cache failure")
    mock_secondary.flush.return_value = True
    
    result = strategy.flush()
    assert result is True
    
    # Test when secondary cache flush fails but primary succeeds
    mock_primary.reset_mock()
    mock_secondary.reset_mock()
    mock_primary.flush.side_effect = None
    mock_primary.flush.return_value = True
    mock_secondary.flush.side_effect = Exception("Secondary cache failure")
    
    result = strategy.flush()
    assert result is True
    
    # Test when both caches fail
    mock_primary.reset_mock()
    mock_secondary.reset_mock()
    mock_primary.flush.side_effect = Exception("Primary cache failure")
    mock_secondary.flush.side_effect = Exception("Secondary cache failure")
    
    result = strategy.flush()
    assert result is False


def test_null_cache_strategy_initialization():
    """Tests the initialization of NullCacheStrategy"""
    # Initialize NullCacheStrategy
    strategy = NullCacheStrategy()
    
    # Verify initialization completes without errors
    assert isinstance(strategy, NullCacheStrategy)


def test_null_cache_strategy_get():
    """Tests the get method of NullCacheStrategy"""
    # Initialize NullCacheStrategy
    strategy = NullCacheStrategy()
    
    # Call get method with test key
    result = strategy.get("test_key")
    
    # Verify method returns None
    assert result is None


def test_null_cache_strategy_set():
    """Tests the set method of NullCacheStrategy"""
    # Initialize NullCacheStrategy
    strategy = NullCacheStrategy()
    
    # Call set method with test key, value, and TTL
    result = strategy.set("test_key", "test_value", 60)
    
    # Verify method returns True (pretending to succeed)
    assert result is True


def test_null_cache_strategy_delete():
    """Tests the delete method of NullCacheStrategy"""
    # Initialize NullCacheStrategy
    strategy = NullCacheStrategy()
    
    # Call delete method with test key
    result = strategy.delete("test_key")
    
    # Verify method returns True (pretending to succeed)
    assert result is True


def test_null_cache_strategy_exists():
    """Tests the exists method of NullCacheStrategy"""
    # Initialize NullCacheStrategy
    strategy = NullCacheStrategy()
    
    # Call exists method with test key
    result = strategy.exists("test_key")
    
    # Verify method returns False (pretending key doesn't exist)
    assert result is False


def test_null_cache_strategy_flush():
    """Tests the flush method of NullCacheStrategy"""
    # Initialize NullCacheStrategy
    strategy = NullCacheStrategy()
    
    # Call flush method
    result = strategy.flush()
    
    # Verify method returns True (pretending to succeed)
    assert result is True


@pytest.mark.integration
def test_single_cache_strategy_with_local_cache():
    """Integration test for SingleCacheStrategy with LocalCache"""
    # Initialize LocalCache
    local_cache = LocalCache()
    
    # Initialize SingleCacheStrategy with LocalCache
    strategy = SingleCacheStrategy(local_cache)
    
    # Test full lifecycle of cache operations
    # Set value and verify it can be retrieved
    strategy.set("test_key", "test_value")
    assert strategy.get("test_key") == "test_value"
    
    # Check existence of key
    assert strategy.exists("test_key") is True
    
    # Delete value and verify it's removed
    strategy.delete("test_key")
    assert strategy.get("test_key") is None
    assert strategy.exists("test_key") is False
    
    # Flush cache and verify all values are removed
    strategy.set("another_key", "another_value")
    strategy.flush()
    assert strategy.get("another_key") is None


@pytest.mark.integration
def test_single_cache_strategy_with_redis_cache():
    """Integration test for SingleCacheStrategy with RedisCache"""
    # Initialize fakeredis server
    fake_redis = fakeredis.FakeRedis()
    
    # Initialize RedisCache with fakeredis
    class TestRedisCache:
        def __init__(self, redis_client):
            self.client = redis_client
        
        def get(self, key, value_type=None):
            value = self.client.get(key)
            return value.decode() if value else None
        
        def set(self, key, value, ttl=None):
            if ttl:
                return self.client.setex(key, ttl, value)
            else:
                return self.client.set(key, value)
        
        def delete(self, key):
            return bool(self.client.delete(key))
        
        def exists(self, key):
            return bool(self.client.exists(key))
        
        def flush(self):
            return self.client.flushall()
    
    redis_cache = TestRedisCache(fake_redis)
    
    # Initialize SingleCacheStrategy with RedisCache
    strategy = SingleCacheStrategy(redis_cache)
    
    # Test full lifecycle of cache operations
    # Set value and verify it can be retrieved
    strategy.set("test_key", "test_value")
    assert strategy.get("test_key") == "test_value"
    
    # Check existence of key
    assert strategy.exists("test_key") is True
    
    # Delete value and verify it's removed
    strategy.delete("test_key")
    assert strategy.get("test_key") is None
    assert strategy.exists("test_key") is False
    
    # Flush cache and verify all values are removed
    strategy.set("another_key", "another_value")
    strategy.flush()
    assert strategy.get("another_key") is None


@pytest.mark.integration
def test_tiered_cache_strategy_with_local_and_redis():
    """Integration test for TieredCacheStrategy with LocalCache and RedisCache"""
    # Initialize LocalCache as primary cache
    local_cache = LocalCache()
    
    # Initialize fakeredis server
    fake_redis = fakeredis.FakeRedis()
    
    # Initialize RedisCache with fakeredis as secondary cache
    class TestRedisCache:
        def __init__(self, redis_client):
            self.client = redis_client
        
        def get(self, key, value_type=None):
            value = self.client.get(key)
            return value.decode() if value else None
        
        def set(self, key, value, ttl=None):
            if ttl:
                return self.client.setex(key, ttl, value)
            else:
                return self.client.set(key, value)
        
        def delete(self, key):
            return bool(self.client.delete(key))
        
        def exists(self, key):
            return bool(self.client.exists(key))
        
        def flush(self):
            return self.client.flushall()
    
    redis_cache = TestRedisCache(fake_redis)
    
    # Initialize TieredCacheStrategy with both caches
    strategy = TieredCacheStrategy(local_cache, redis_cache)
    
    # Test primary cache hit scenario
    local_cache.set("primary_key", "primary_value")
    assert strategy.get("primary_key") == "primary_value"
    
    # Test primary cache miss, secondary cache hit scenario
    redis_cache.set("secondary_key", "secondary_value")
    assert strategy.get("secondary_key") == "secondary_value"
    
    # Test cache update propagation between tiers
    assert local_cache.get("secondary_key") == "secondary_value"
    
    # Test deletion across both caches
    strategy.set("both_key", "both_value")
    strategy.delete("both_key")
    assert local_cache.get("both_key") is None
    assert redis_cache.get("both_key") is None
    
    # Test flush across both caches
    strategy.set("flush_key", "flush_value")
    strategy.flush()
    assert local_cache.get("flush_key") is None
    assert redis_cache.get("flush_key") is None


def test_tiered_cache_strategy_fallback():
    """Tests the fallback behavior of TieredCacheStrategy when primary cache fails"""
    # Create mock primary cache that raises exceptions
    failing_primary = Mock()
    failing_primary.get.side_effect = Exception("Primary cache failure")
    failing_primary.set.side_effect = Exception("Primary cache failure")
    failing_primary.delete.side_effect = Exception("Primary cache failure")
    failing_primary.exists.side_effect = Exception("Primary cache failure")
    failing_primary.flush.side_effect = Exception("Primary cache failure")
    
    # Create mock secondary cache that works correctly
    mock_secondary = Mock()
    mock_secondary.get.return_value = "secondary_value"
    mock_secondary.set.return_value = True
    mock_secondary.delete.return_value = True
    mock_secondary.exists.return_value = True
    mock_secondary.flush.return_value = True
    
    # Initialize TieredCacheStrategy with mock caches
    strategy = TieredCacheStrategy(failing_primary, mock_secondary)
    
    # Test get method falls back to secondary cache
    result = strategy.get("test_key")
    assert result == "secondary_value"
    
    # Test set method falls back to secondary cache
    result = strategy.set("test_key", "test_value")
    assert result is True
    
    # Test delete method falls back to secondary cache
    result = strategy.delete("test_key")
    assert result is True
    
    # Test exists method falls back to secondary cache
    result = strategy.exists("test_key")
    assert result is True
    
    # Test flush method falls back to secondary cache
    result = strategy.flush()
    assert result is True