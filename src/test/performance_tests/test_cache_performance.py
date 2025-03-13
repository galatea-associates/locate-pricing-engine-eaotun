"""
Performance tests for the cache service of the Borrow Rate & Locate Fee Pricing Engine.

This module contains comprehensive tests to measure and validate the performance
characteristics of the caching layer, including response times, throughput, and hit
rates under various load conditions.
"""

import pytest
import time
import random
import fakeredis  # fakeredis 2.10.0+
import statistics
from typing import Dict, List, Any, Optional

from src.test.performance_tests.config.settings import get_test_settings
from src.test.performance_tests import (
    metrics_collection,
    get_metrics_collector,
    check_performance_thresholds,
    analyze_performance_results
)
from src.backend.services.cache.redis import RedisCache
from src.backend.services.cache.strategies import SingleCacheStrategy, TieredCacheStrategy
from src.test.performance_tests.fixtures.test_data import (
    normal_market_scenario,
    high_volatility_scenario
)

# Test constants
CACHE_TEST_ITERATIONS = 1000
CACHE_KEY_PREFIX = "test:cache:performance:"
CACHE_VALUE_SIZES = [100, 1000, 10000]  # Small, medium, large values in bytes

# Configure logging
import logging
logger = logging.getLogger(__name__)


def generate_test_data(size: int) -> str:
    """
    Generates test data of specified size for cache performance testing.
    
    Args:
        size: Size of data to generate in bytes
        
    Returns:
        Random string of specified size
    """
    return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=size))


def generate_cache_keys(count: int, prefix: str) -> List[str]:
    """
    Generates a list of cache keys for testing.
    
    Args:
        count: Number of cache keys to generate
        prefix: Prefix for cache keys
        
    Returns:
        List of cache keys
    """
    return [f"{prefix}{i}" for i in range(count)]


class TestCachePerformance:
    """Test suite for measuring cache service performance."""
    
    def setup_method(self, method):
        """Set up test environment before each test method."""
        # Create fake Redis server for testing
        self.redis_server = fakeredis.FakeServer()
        self.redis_client = fakeredis.FakeStrictRedis(server=self.redis_server)
        
        # Create RedisCache instance with fakeredis
        self.cache = RedisCache(
            host="localhost",
            port=6379,
            password=None,
            db=0,
            prefix=CACHE_KEY_PREFIX
        )
        
        # Replace the real Redis client with our fake one
        self.cache._client = self.redis_client
        self.cache._connected = True
        
        # Initialize metrics collector
        self.metrics = get_metrics_collector("cache_performance")
        
        # Generate test data of different sizes
        self.test_data = {}
        for size in CACHE_VALUE_SIZES:
            self.test_data[size] = generate_test_data(size)
        
        # Generate cache keys
        self.cache_keys = generate_cache_keys(CACHE_TEST_ITERATIONS, "test_key_")
    
    def teardown_method(self, method):
        """Clean up test environment after each test method."""
        # Flush the cache
        self.cache.flush()
        
        # Reset metrics collector
        self.metrics.reset()
    
    def test_redis_cache_set_performance(self):
        """Test the performance of Redis cache set operations."""
        # Get test settings
        settings = get_test_settings()
        response_time_threshold = settings.get_response_time_threshold()
        
        # Test data to use
        small_data = self.test_data[CACHE_VALUE_SIZES[0]]
        medium_data = self.test_data[CACHE_VALUE_SIZES[1]]
        large_data = self.test_data[CACHE_VALUE_SIZES[2]]
        
        # Start metrics collection
        with metrics_collection(self.metrics):
            # Test set performance with small values
            for i in range(CACHE_TEST_ITERATIONS // 3):
                key = self.cache_keys[i]
                start_time = time.time()
                self.cache.set(key, small_data, 60)
                end_time = time.time()
                self.metrics.record_metric("set_small", (end_time - start_time) * 1000)
            
            # Test set performance with medium values
            for i in range(CACHE_TEST_ITERATIONS // 3, 2 * (CACHE_TEST_ITERATIONS // 3)):
                key = self.cache_keys[i]
                start_time = time.time()
                self.cache.set(key, medium_data, 60)
                end_time = time.time()
                self.metrics.record_metric("set_medium", (end_time - start_time) * 1000)
            
            # Test set performance with large values
            for i in range(2 * (CACHE_TEST_ITERATIONS // 3), CACHE_TEST_ITERATIONS):
                key = self.cache_keys[i]
                start_time = time.time()
                self.cache.set(key, large_data, 60)
                end_time = time.time()
                self.metrics.record_metric("set_large", (end_time - start_time) * 1000)
        
        # Analyze results
        results = analyze_performance_results(self.metrics)
        logger.info(f"Cache set performance results: {results}")
        
        # Check performance thresholds
        assert check_performance_thresholds(
            self.metrics, 
            "set_small", 
            response_time_threshold
        ), f"Small value cache set performance exceeded threshold of {response_time_threshold}ms"
        
        assert check_performance_thresholds(
            self.metrics, 
            "set_medium", 
            response_time_threshold
        ), f"Medium value cache set performance exceeded threshold of {response_time_threshold}ms"
        
        assert check_performance_thresholds(
            self.metrics, 
            "set_large", 
            response_time_threshold * 2  # Allow more time for large values
        ), f"Large value cache set performance exceeded threshold of {response_time_threshold * 2}ms"
    
    def test_redis_cache_get_performance(self):
        """Test the performance of Redis cache get operations."""
        # Get test settings
        settings = get_test_settings()
        response_time_threshold = settings.get_response_time_threshold()
        
        # Test data to use
        small_data = self.test_data[CACHE_VALUE_SIZES[0]]
        medium_data = self.test_data[CACHE_VALUE_SIZES[1]]
        large_data = self.test_data[CACHE_VALUE_SIZES[2]]
        
        # Populate cache with test data
        for i in range(CACHE_TEST_ITERATIONS // 3):
            key = self.cache_keys[i]
            self.cache.set(key, small_data, 60)
        
        for i in range(CACHE_TEST_ITERATIONS // 3, 2 * (CACHE_TEST_ITERATIONS // 3)):
            key = self.cache_keys[i]
            self.cache.set(key, medium_data, 60)
        
        for i in range(2 * (CACHE_TEST_ITERATIONS // 3), CACHE_TEST_ITERATIONS):
            key = self.cache_keys[i]
            self.cache.set(key, large_data, 60)
        
        # Start metrics collection
        with metrics_collection(self.metrics):
            # Test get performance with small values
            for i in range(CACHE_TEST_ITERATIONS // 3):
                key = self.cache_keys[i]
                start_time = time.time()
                self.cache.get(key)
                end_time = time.time()
                self.metrics.record_metric("get_small", (end_time - start_time) * 1000)
            
            # Test get performance with medium values
            for i in range(CACHE_TEST_ITERATIONS // 3, 2 * (CACHE_TEST_ITERATIONS // 3)):
                key = self.cache_keys[i]
                start_time = time.time()
                self.cache.get(key)
                end_time = time.time()
                self.metrics.record_metric("get_medium", (end_time - start_time) * 1000)
            
            # Test get performance with large values
            for i in range(2 * (CACHE_TEST_ITERATIONS // 3), CACHE_TEST_ITERATIONS):
                key = self.cache_keys[i]
                start_time = time.time()
                self.cache.get(key)
                end_time = time.time()
                self.metrics.record_metric("get_large", (end_time - start_time) * 1000)
        
        # Analyze results
        results = analyze_performance_results(self.metrics)
        logger.info(f"Cache get performance results: {results}")
        
        # Check performance thresholds
        assert check_performance_thresholds(
            self.metrics, 
            "get_small", 
            response_time_threshold
        ), f"Small value cache get performance exceeded threshold of {response_time_threshold}ms"
        
        assert check_performance_thresholds(
            self.metrics, 
            "get_medium", 
            response_time_threshold
        ), f"Medium value cache get performance exceeded threshold of {response_time_threshold}ms"
        
        assert check_performance_thresholds(
            self.metrics, 
            "get_large", 
            response_time_threshold * 2  # Allow more time for large values
        ), f"Large value cache get performance exceeded threshold of {response_time_threshold * 2}ms"
    
    def test_redis_cache_miss_performance(self):
        """Test the performance of Redis cache get operations for non-existent keys."""
        # Get test settings
        settings = get_test_settings()
        response_time_threshold = settings.get_response_time_threshold()
        
        # Generate a set of keys that don't exist in the cache
        non_existent_keys = [f"non_existent_key_{i}" for i in range(CACHE_TEST_ITERATIONS)]
        
        # Start metrics collection
        with metrics_collection(self.metrics):
            for key in non_existent_keys:
                start_time = time.time()
                self.cache.get(key)
                end_time = time.time()
                self.metrics.record_metric("cache_miss", (end_time - start_time) * 1000)
        
        # Analyze results
        results = analyze_performance_results(self.metrics)
        logger.info(f"Cache miss performance results: {results}")
        
        # Check performance thresholds
        assert check_performance_thresholds(
            self.metrics, 
            "cache_miss", 
            response_time_threshold
        ), f"Cache miss performance exceeded threshold of {response_time_threshold}ms"
    
    def test_single_cache_strategy_performance(self):
        """Test the performance of SingleCacheStrategy."""
        # Get test settings
        settings = get_test_settings()
        response_time_threshold = settings.get_response_time_threshold()
        
        # Create SingleCacheStrategy with RedisCache
        strategy = SingleCacheStrategy(self.cache)
        
        # Test data to use
        test_data = self.test_data[CACHE_VALUE_SIZES[1]]  # Medium-sized data
        
        # Start metrics collection
        with metrics_collection(self.metrics):
            # Test set performance
            for i in range(CACHE_TEST_ITERATIONS // 2):
                key = self.cache_keys[i]
                start_time = time.time()
                strategy.set(key, test_data, 60)
                end_time = time.time()
                self.metrics.record_metric("strategy_set", (end_time - start_time) * 1000)
            
            # Test get performance
            for i in range(CACHE_TEST_ITERATIONS // 2):
                key = self.cache_keys[i]
                start_time = time.time()
                strategy.get(key)
                end_time = time.time()
                self.metrics.record_metric("strategy_get", (end_time - start_time) * 1000)
        
        # Analyze results
        results = analyze_performance_results(self.metrics)
        logger.info(f"SingleCacheStrategy performance results: {results}")
        
        # Check performance thresholds
        assert check_performance_thresholds(
            self.metrics, 
            "strategy_set", 
            response_time_threshold
        ), f"Strategy set performance exceeded threshold of {response_time_threshold}ms"
        
        assert check_performance_thresholds(
            self.metrics, 
            "strategy_get", 
            response_time_threshold
        ), f"Strategy get performance exceeded threshold of {response_time_threshold}ms"
    
    def test_tiered_cache_strategy_performance(self):
        """Test the performance of TieredCacheStrategy."""
        # Get test settings
        settings = get_test_settings()
        response_time_threshold = settings.get_response_time_threshold()
        
        # Create two Redis cache instances for primary and secondary caches
        primary_cache = self.cache
        
        # Create another Redis instance for secondary cache
        secondary_redis = fakeredis.FakeStrictRedis(server=self.redis_server)
        secondary_cache = RedisCache(
            host="localhost",
            port=6379,
            password=None,
            db=1,
            prefix=CACHE_KEY_PREFIX + "secondary:"
        )
        secondary_cache._client = secondary_redis
        secondary_cache._connected = True
        
        # Create TieredCacheStrategy with both caches
        strategy = TieredCacheStrategy(primary_cache, secondary_cache)
        
        # Test data to use
        test_data = self.test_data[CACHE_VALUE_SIZES[1]]  # Medium-sized data
        
        # Start metrics collection
        with metrics_collection(self.metrics):
            # Test set performance (writes to both caches)
            for i in range(CACHE_TEST_ITERATIONS // 3):
                key = self.cache_keys[i]
                start_time = time.time()
                strategy.set(key, test_data, 60)
                end_time = time.time()
                self.metrics.record_metric("tiered_set", (end_time - start_time) * 1000)
            
            # Test get performance for L1 cache hit
            for i in range(CACHE_TEST_ITERATIONS // 3):
                key = self.cache_keys[i]
                start_time = time.time()
                strategy.get(key)
                end_time = time.time()
                self.metrics.record_metric("tiered_get_l1_hit", (end_time - start_time) * 1000)
            
            # Test get performance for L1 miss but L2 hit
            # First, remove some keys from L1 but keep them in L2
            keys_to_remove = self.cache_keys[CACHE_TEST_ITERATIONS // 3: 2 * (CACHE_TEST_ITERATIONS // 3)]
            for key in keys_to_remove:
                strategy.set(key, test_data, 60)  # Set in both L1 and L2
                primary_cache.delete(key)  # Remove from L1 only
            
            # Now test L2 hits
            for key in keys_to_remove:
                start_time = time.time()
                strategy.get(key)
                end_time = time.time()
                self.metrics.record_metric("tiered_get_l2_hit", (end_time - start_time) * 1000)
        
        # Analyze results
        results = analyze_performance_results(self.metrics)
        logger.info(f"TieredCacheStrategy performance results: {results}")
        
        # Check performance thresholds
        assert check_performance_thresholds(
            self.metrics, 
            "tiered_set", 
            response_time_threshold * 1.5  # Allow more time for writing to both caches
        ), f"Tiered strategy set performance exceeded threshold of {response_time_threshold * 1.5}ms"
        
        assert check_performance_thresholds(
            self.metrics, 
            "tiered_get_l1_hit", 
            response_time_threshold
        ), f"Tiered strategy L1 hit performance exceeded threshold of {response_time_threshold}ms"
        
        assert check_performance_thresholds(
            self.metrics, 
            "tiered_get_l2_hit", 
            response_time_threshold * 1.5  # Allow more time for L2 hits
        ), f"Tiered strategy L2 hit performance exceeded threshold of {response_time_threshold * 1.5}ms"
    
    def test_cache_hit_rate_under_load(self):
        """Test cache hit rate under simulated load conditions."""
        # Get test settings
        settings = get_test_settings()
        
        # Test data
        test_data = self.test_data[CACHE_VALUE_SIZES[1]]  # Medium-sized data
        
        # Populate cache with some keys
        keys_to_cache = self.cache_keys[:int(CACHE_TEST_ITERATIONS * 0.8)]  # 80% of keys
        for key in keys_to_cache:
            self.cache.set(key, test_data, 60)
        
        # Track hits and misses
        hits = 0
        misses = 0
        
        # Start metrics collection
        with metrics_collection(self.metrics):
            # Perform mixed get operations with some hits and some misses
            for i in range(CACHE_TEST_ITERATIONS):
                # 80% of requests should be for cached keys, 20% for non-existent keys
                if i < int(CACHE_TEST_ITERATIONS * 0.8):
                    key = random.choice(keys_to_cache)  # Should be a hit
                else:
                    key = f"non_existent_key_{i}"  # Should be a miss
                
                start_time = time.time()
                result = self.cache.get(key)
                end_time = time.time()
                
                if result is not None:
                    hits += 1
                    self.metrics.record_metric("cache_hit", (end_time - start_time) * 1000)
                else:
                    misses += 1
                    self.metrics.record_metric("cache_miss", (end_time - start_time) * 1000)
        
        # Calculate hit rate
        total_requests = hits + misses
        hit_rate = (hits / total_requests) * 100 if total_requests > 0 else 0
        
        # Log results
        logger.info(f"Cache hit rate: {hit_rate:.2f}% ({hits} hits, {misses} misses)")
        
        # Check hit rate target (should be >90% for known keys)
        hit_rate_for_known_keys = (hits / len(keys_to_cache)) * 100 if len(keys_to_cache) > 0 else 0
        logger.info(f"Cache hit rate for known keys: {hit_rate_for_known_keys:.2f}%")
        
        assert hit_rate_for_known_keys > 90, f"Cache hit rate for known keys was {hit_rate_for_known_keys:.2f}%, should be >90%"
    
    def test_cache_performance_with_market_data(self, normal_market_scenario):
        """Test cache performance with realistic market data."""
        # Get test settings
        settings = get_test_settings()
        response_time_threshold = settings.get_response_time_threshold()
        
        # Extract stock and volatility data from the scenario
        stocks = normal_market_scenario['stocks']
        
        # Start metrics collection
        with metrics_collection(self.metrics):
            # Cache stock data
            for i, stock in enumerate(stocks):
                key = f"borrow_rate:{stock['ticker']}"
                start_time = time.time()
                self.cache.set(key, stock['min_borrow_rate'], 300)  # 5 minute TTL
                end_time = time.time()
                self.metrics.record_metric("cache_stock_set", (end_time - start_time) * 1000)
                
                # Also cache volatility data
                vol_key = f"volatility:{stock['ticker']}"
                # Create mock volatility data
                vol_data = {
                    'ticker': stock['ticker'],
                    'vol_index': random.uniform(10, 40),
                    'timestamp': str(time.time())
                }
                start_time = time.time()
                self.cache.set(vol_key, vol_data, 900)  # 15 minute TTL
                end_time = time.time()
                self.metrics.record_metric("cache_volatility_set", (end_time - start_time) * 1000)
            
            # Get stock data
            for stock in stocks:
                key = f"borrow_rate:{stock['ticker']}"
                start_time = time.time()
                self.cache.get(key)
                end_time = time.time()
                self.metrics.record_metric("cache_stock_get", (end_time - start_time) * 1000)
                
                # Also get volatility data
                vol_key = f"volatility:{stock['ticker']}"
                start_time = time.time()
                self.cache.get(vol_key)
                end_time = time.time()
                self.metrics.record_metric("cache_volatility_get", (end_time - start_time) * 1000)
        
        # Analyze results
        results = analyze_performance_results(self.metrics)
        logger.info(f"Market data cache performance results: {results}")
        
        # Check performance thresholds
        assert check_performance_thresholds(
            self.metrics, 
            "cache_stock_set", 
            response_time_threshold
        ), f"Stock data cache set performance exceeded threshold of {response_time_threshold}ms"
        
        assert check_performance_thresholds(
            self.metrics, 
            "cache_stock_get", 
            response_time_threshold
        ), f"Stock data cache get performance exceeded threshold of {response_time_threshold}ms"
        
        assert check_performance_thresholds(
            self.metrics, 
            "cache_volatility_set", 
            response_time_threshold
        ), f"Volatility data cache set performance exceeded threshold of {response_time_threshold}ms"
        
        assert check_performance_thresholds(
            self.metrics, 
            "cache_volatility_get", 
            response_time_threshold
        ), f"Volatility data cache get performance exceeded threshold of {response_time_threshold}ms"
    
    def test_cache_performance_under_high_volatility(self, high_volatility_scenario):
        """Test cache performance under high volatility market conditions."""
        # Get test settings
        settings = get_test_settings()
        response_time_threshold = settings.get_response_time_threshold()
        
        # Extract stock data from the scenario
        stocks = high_volatility_scenario['stocks']
        
        # Start metrics collection
        with metrics_collection(self.metrics):
            # Simulate rapid cache updates to model volatile market
            for _ in range(10):  # Simulate 10 market updates
                for i, stock in enumerate(stocks):
                    key = f"borrow_rate:{stock['ticker']}"
                    
                    # Update borrow rate with random change to simulate volatility
                    borrow_rate = float(stock['min_borrow_rate']) * (1 + random.uniform(-0.2, 0.2))
                    
                    # Short TTL to simulate frequent updates
                    start_time = time.time()
                    self.cache.set(key, borrow_rate, 60)  # 1 minute TTL for high volatility
                    end_time = time.time()
                    self.metrics.record_metric("high_volatility_set", (end_time - start_time) * 1000)
                    
                    # Immediately get the value to simulate trading activity
                    start_time = time.time()
                    self.cache.get(key)
                    end_time = time.time()
                    self.metrics.record_metric("high_volatility_get", (end_time - start_time) * 1000)
                
                # Small sleep to simulate time between market updates
                time.sleep(0.01)
        
        # Analyze results
        results = analyze_performance_results(self.metrics)
        logger.info(f"High volatility cache performance results: {results}")
        
        # Check performance thresholds
        assert check_performance_thresholds(
            self.metrics, 
            "high_volatility_set", 
            response_time_threshold
        ), f"High volatility cache set performance exceeded threshold of {response_time_threshold}ms"
        
        assert check_performance_thresholds(
            self.metrics, 
            "high_volatility_get", 
            response_time_threshold
        ), f"High volatility cache get performance exceeded threshold of {response_time_threshold}ms"
    
    def test_cache_memory_usage(self):
        """Test memory usage of the cache under various data loads."""
        # Get memory usage stats before adding data
        initial_stats = self.cache.get_stats()
        initial_memory = initial_stats.get('memory_used', '0')
        
        # Convert memory string to bytes (this is an approximation since fakeredis
        # doesn't provide real memory usage stats)
        if isinstance(initial_memory, str) and initial_memory.endswith('B'):
            if initial_memory.endswith('KB'):
                initial_memory_bytes = float(initial_memory[:-2]) * 1024
            elif initial_memory.endswith('MB'):
                initial_memory_bytes = float(initial_memory[:-2]) * 1024 * 1024
            else:
                initial_memory_bytes = float(initial_memory[:-1])
        else:
            initial_memory_bytes = 0
        
        # Record memory usage as we add more data
        memory_samples = []
        data_counts = []
        
        # Use large values to increase memory impact
        large_data = self.test_data[CACHE_VALUE_SIZES[2]]
        
        # Add data in batches
        batch_size = 50
        num_batches = 10
        
        for batch in range(1, num_batches + 1):
            # Add a batch of data
            for i in range(batch_size):
                key = f"memory_test_key_{batch}_{i}"
                self.cache.set(key, large_data, 3600)  # 1 hour TTL
            
            # Record data count
            data_counts.append(batch * batch_size)
            
            # Get memory stats after adding data
            stats = self.cache.get_stats()
            memory = stats.get('memory_used', '0')
            
            # Convert memory string to bytes (approximation)
            if isinstance(memory, str) and memory.endswith('B'):
                if memory.endswith('KB'):
                    memory_bytes = float(memory[:-2]) * 1024
                elif memory.endswith('MB'):
                    memory_bytes = float(memory[:-2]) * 1024 * 1024
                else:
                    memory_bytes = float(memory[:-1])
            else:
                memory_bytes = batch * batch_size * len(large_data)  # Estimation for fakeredis
            
            memory_samples.append(memory_bytes)
        
        # Calculate memory growth rate
        if len(memory_samples) >= 2:
            memory_growth = [(memory_samples[i] - memory_samples[i-1]) / batch_size 
                             for i in range(1, len(memory_samples))]
            avg_growth_per_item = statistics.mean(memory_growth)
            
            logger.info(f"Average memory growth per item: {avg_growth_per_item:.2f} bytes")
            logger.info(f"Memory samples: {memory_samples}")
            
            # Assert that memory usage scales linearly (approximately)
            # This is approximate and may not be accurate with fakeredis
            if avg_growth_per_item > 0:
                variation = [abs(growth - avg_growth_per_item) / avg_growth_per_item 
                            for growth in memory_growth]
                avg_variation = statistics.mean(variation)
                
                logger.info(f"Memory growth variation: {avg_variation:.2f}")
                
                # Verify memory growth is relatively consistent
                assert avg_variation < 0.5, f"Memory growth variation {avg_variation:.2f} exceeds 0.5"
    
    def test_cache_ttl_expiration(self):
        """Test that cache entries expire correctly according to TTL."""
        # Test data
        test_data = self.test_data[CACHE_VALUE_SIZES[0]]  # Small data for this test
        
        # Set up test keys with different TTLs
        ttl_1s_key = "ttl_test_1s"
        ttl_2s_key = "ttl_test_2s"
        ttl_5s_key = "ttl_test_5s"
        
        self.cache.set(ttl_1s_key, test_data, 1)  # 1 second TTL
        self.cache.set(ttl_2s_key, test_data, 2)  # 2 second TTL
        self.cache.set(ttl_5s_key, test_data, 5)  # 5 second TTL
        
        # Verify all keys exist immediately
        assert self.cache.exists(ttl_1s_key), "1s TTL key should exist immediately after setting"
        assert self.cache.exists(ttl_2s_key), "2s TTL key should exist immediately after setting"
        assert self.cache.exists(ttl_5s_key), "5s TTL key should exist immediately after setting"
        
        # Start metrics collection
        with metrics_collection(self.metrics):
            # Wait for 1 second and check 1s TTL key
            time.sleep(1.1)  # Slightly longer to account for timing variations
            
            start_time = time.time()
            ttl_1s_exists = self.cache.exists(ttl_1s_key)
            end_time = time.time()
            self.metrics.record_metric("ttl_check", (end_time - start_time) * 1000)
            
            # Wait for 1 more second and check 2s TTL key
            time.sleep(1.1)
            
            start_time = time.time()
            ttl_2s_exists = self.cache.exists(ttl_2s_key)
            end_time = time.time()
            self.metrics.record_metric("ttl_check", (end_time - start_time) * 1000)
            
            # Wait for 3 more seconds and check 5s TTL key
            time.sleep(3.1)
            
            start_time = time.time()
            ttl_5s_exists = self.cache.exists(ttl_5s_key)
            end_time = time.time()
            self.metrics.record_metric("ttl_check", (end_time - start_time) * 1000)
        
        # Verify TTL expirations
        assert not ttl_1s_exists, "1s TTL key should have expired after 1.1 seconds"
        assert not ttl_2s_exists, "2s TTL key should have expired after 2.2 seconds"
        assert not ttl_5s_exists, "5s TTL key should have expired after 5.3 seconds"
        
        # Check TTL check performance
        results = analyze_performance_results(self.metrics)
        logger.info(f"TTL check performance results: {results}")
        
        # Get test settings
        settings = get_test_settings()
        response_time_threshold = settings.get_response_time_threshold()
        
        # Check performance thresholds
        assert check_performance_thresholds(
            self.metrics, 
            "ttl_check", 
            response_time_threshold
        ), f"TTL check performance exceeded threshold of {response_time_threshold}ms"