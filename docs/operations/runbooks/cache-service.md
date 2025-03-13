# Cache Service Operational Runbook

## Table of Contents
- [1. Overview](#1-overview)
- [2. Architecture](#2-architecture)
- [3. Deployment](#3-deployment)
- [4. Monitoring](#4-monitoring)
- [5. Alerting](#5-alerting)
- [6. Troubleshooting](#6-troubleshooting)
- [7. Common Operations](#7-common-operations)
- [8. Performance Tuning](#8-performance-tuning)
- [9. Disaster Recovery](#9-disaster-recovery)
- [10. References](#10-references)

## 1. Overview

The Cache Service is a critical component of the Borrow Rate & Locate Fee Pricing Engine that provides high-performance caching for frequently accessed data such as borrow rates, volatility metrics, and broker configurations.

**Purpose**: 
- Optimize performance through multi-level caching
- Reduce load on external APIs and databases
- Provide fallback mechanisms when data sources are unavailable

**Key Features**:
- Multi-level caching strategy (L1 local cache, L2 Redis cache)
- Configurable Time-To-Live (TTL) values for different data types
- Cache invalidation mechanisms
- Performance monitoring and statistics
- Health checks and self-healing capabilities

**Service Dependencies**:
- Redis (ElastiCache in AWS environments)
- Kubernetes for deployment and orchestration
- Prometheus/Grafana for monitoring

## 2. Architecture

### 2.1 Multi-Level Caching Strategy

The Cache Service implements a multi-level caching strategy:

1. **L1 Cache (LocalCache)**: In-memory application cache
   - Ultra-high performance (microsecond access times)
   - Process-local (not shared between service instances)
   - First level checked for data
   - Default TTL: 60 seconds

2. **L2 Cache (RedisCache)**: Distributed cache
   - High performance (millisecond access times)
   - Shared across all service instances
   - Checked when L1 cache misses
   - Default TTLs: 5-30 minutes depending on data type

### 2.2 Data Types and TTL Configuration

The service uses different TTL values depending on the data type:

| Data Type | Key Pattern | Default TTL | Description |
|-----------|-------------|-------------|-------------|
| Borrow Rates | `borrow_rate:{ticker}` | 300 seconds (5 min) | Current borrow rates for securities |
| Volatility | `volatility:{ticker}` | 900 seconds (15 min) | Volatility metrics for securities |
| Event Risk | `event_risk:{ticker}` | 3600 seconds (1 hour) | Event risk factors for securities |
| Broker Config | `broker_config:{client_id}` | 1800 seconds (30 min) | Broker configuration data |
| Calculation | `calculation:{ticker}:{client_id}:{position_value}:{loan_days}` | 60 seconds (1 min) | Fee calculation results |
| Min Rate | `min_rate:{ticker}` | 86400 seconds (24 hours) | Fallback minimum rates |

### 2.3 High-Level Component Diagram

```
┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │
│ Calculation Service │      │    Data Service     │
│                     │      │                     │
└─────────┬───────────┘      └────────┬────────────┘
          │                           │
          │                           │
          ▼                           ▼
┌─────────────────────────────────────────────────┐
│                                                 │
│                  Cache Service                  │
│                                                 │
│  ┌─────────────┐           ┌─────────────────┐  │
│  │             │           │                 │  │
│  │  L1 Cache   │──────────►│    L2 Cache     │  │
│  │ (In-Memory) │           │    (Redis)      │  │
│  │             │           │                 │  │
│  └─────────────┘           └─────────────────┘  │
│                                                 │
└─────────────────────────────────────────────────┘
                      │
                      │
                      ▼
          ┌─────────────────────┐
          │                     │
          │   Redis Cluster     │
          │                     │
          └─────────────────────┘
```

## 3. Deployment

### 3.1 Kubernetes Deployment Configuration

The Cache Service is deployed as a Kubernetes deployment with the following key configurations:

- **Replicas**: 3 (default)
- **Resource Requests**:
  - CPU: 500m
  - Memory: 2Gi
- **Resource Limits**:
  - CPU: 2000m
  - Memory: 8Gi
- **Health Checks**:
  - Readiness Probe: HTTP GET `/health` (every 10s)
  - Liveness Probe: HTTP GET `/health` (every 20s)
- **Pod Anti-Affinity**: Configured to distribute instances across nodes and zones

### 3.2 Environment Variables

Key environment variables that control the service behavior:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| REDIS_HOST | Redis server hostname | N/A (required) |
| REDIS_PORT | Redis server port | N/A (required) |
| REDIS_PASSWORD | Redis server password | N/A (required) |
| REDIS_DB | Redis database number | 0 |
| REDIS_MAX_CONNECTIONS | Maximum Redis connections | 100 |
| BORROW_RATE_TTL | TTL for borrow rate cache entries | 300 |
| VOLATILITY_TTL | TTL for volatility data | 900 |
| EVENT_RISK_TTL | TTL for event risk data | 3600 |
| BROKER_CONFIG_TTL | TTL for broker configurations | 1800 |
| CALCULATION_RESULT_TTL | TTL for calculation results | 60 |
| MIN_RATE_TTL | TTL for minimum rates | 86400 |
| ENABLE_LOCAL_CACHE | Enable in-memory L1 cache | true |
| LOCAL_CACHE_MAX_SIZE | Maximum size of local cache | 1000 |
| LOCAL_CACHE_TTL | TTL for local cache entries | 60 |
| ENABLE_PUBSUB | Enable Redis pub/sub for cache invalidation | true |
| PUBSUB_CHANNEL | Redis channel for cache invalidation events | cache_invalidation |
| ENABLE_CACHE_STATS | Enable cache statistics collection | true |
| CACHE_WARMUP_ON_STARTUP | Warm up cache on service startup | false |

### 3.3 Scaling Considerations

- The Cache Service is primarily memory-bound
- Scale horizontally when:
  - Memory usage consistently exceeds 70%
  - High CPU utilization (>80%)
  - Response times exceed 100ms
- Vertical scaling considerations:
  - Increase memory for high cache volume
  - Increase CPU for high throughput environments

## 4. Monitoring

### 4.1 Key Metrics

| Metric | Description | Warning Threshold | Critical Threshold |
|--------|-------------|-------------------|-------------------|
| cache_hit_rate | Percentage of cache hits | <90% | <80% |
| cache_miss_rate | Percentage of cache misses | >10% | >20% |
| redis_response_time | Redis server response time (ms) | >20ms | >50ms |
| redis_connections | Current Redis connections | >80% of max | >90% of max |
| redis_memory_usage | Redis memory usage | >70% | >85% |
| local_cache_size | Number of items in local cache | >90% of max | >95% of max |
| request_rate | Requests per second | N/A (monitoring only) | N/A |
| request_latency | Service response time (ms) | >50ms | >100ms |
| error_rate | Error rate percentage | >1% | >5% |

### 4.2 Prometheus Metrics

The Cache Service exposes the following Prometheus metrics at `/metrics`:

- `cache_service_requests_total{operation="get|set|delete", status="hit|miss|error"}`: Total number of cache operations
- `cache_service_request_duration_seconds{operation="get|set|delete"}`: Histogram of request durations
- `cache_service_size{cache="local|redis", type="borrow_rate|volatility|event_risk|broker_config|calculation|min_rate"}`: Current number of items in cache by type
- `redis_response_time_seconds`: Redis server response time
- `redis_connection_count`: Current number of Redis connections
- `redis_error_total`: Total number of Redis errors
- `service_health_status{component="redis|local_cache"}`: Health status of components (1=healthy, 0=unhealthy)

### 4.3 Grafana Dashboard

A Grafana dashboard for the Cache Service should include:

1. **Cache Performance**
   - Hit/miss rates by cache level and data type
   - Request latencies
   - Error rates

2. **Redis Metrics**
   - Memory usage
   - Connection counts
   - Command statistics
   - Response times

3. **Service Health**
   - Instance count
   - CPU/Memory utilization
   - Health check status

4. **Cache Contents**
   - Items by data type
   - Eviction rates
   - Key expiration rates

### 4.4 Health Checks

The Cache Service exposes a health endpoint at `/health` that provides:

- Overall service status
- Redis connection status
- Redis response time
- Redis server information
- Error messages (if any)

Sample health check response:

```json
{
  "status": "healthy",
  "redis": {
    "connected": true,
    "response_time_ms": 2.45,
    "server_info": {
      "redis_version": "7.0.5",
      "uptime_in_seconds": 1234567,
      "connected_clients": 42,
      "used_memory_human": "1.2G"
    }
  },
  "local_cache": {
    "status": "healthy",
    "items": 587,
    "memory_bytes": 12345678
  }
}
```

## 5. Alerting

### 5.1 Alert Definitions

| Alert | Trigger | Severity | Response Time | Notification Channel |
|-------|---------|----------|---------------|----------------------|
| CacheServiceDown | Instance count < desired replica count | Critical | 5 minutes | PagerDuty, Slack |
| RedisConnectionFailed | Redis connection failures > 3 in 5 minutes | Critical | 5 minutes | PagerDuty, Slack |
| HighCacheMissRate | Cache miss rate > 20% for 15 minutes | Warning | 30 minutes | Slack |
| RedisHighMemoryUsage | Redis memory usage > 85% | Warning | 30 minutes | Slack |
| CacheServiceHighLatency | 95th percentile latency > 100ms for 10 minutes | Warning | 30 minutes | Slack |
| CacheServiceErrorRate | Error rate > 5% for 5 minutes | Critical | 15 minutes | PagerDuty, Slack |

### 5.2 Alert Response Procedures

#### CacheServiceDown
1. Check Kubernetes events and logs: `kubectl -n borrow-rate-engine describe pod cache-service-xxx`
2. Verify resource consumption: `kubectl -n borrow-rate-engine top pod cache-service-xxx`
3. Check for OOM events: `kubectl -n borrow-rate-engine logs cache-service-xxx | grep -i "killed"`
4. Restart if necessary: `kubectl -n borrow-rate-engine rollout restart deployment cache-service`

#### RedisConnectionFailed
1. Verify Redis service is running: `kubectl -n borrow-rate-engine exec -it cache-service-xxx -- redis-cli -h $REDIS_HOST -p $REDIS_PORT ping`
2. Check Redis memory and CPU usage
3. Verify network connectivity between Cache Service and Redis
4. Check Redis logs for errors
5. Failover to a replica if necessary

#### CacheServiceHighLatency
1. Check service CPU/memory usage
2. Verify Redis performance metrics
3. Check network latency between Cache Service and Redis
4. Analyze recent changes that might affect performance
5. Consider scaling the service horizontally if load is high

## 6. Troubleshooting

### 6.1 Common Issues and Resolutions

#### High Cache Miss Rate
- **Symptoms**: Low hit rate, increased latency, higher load on backend services
- **Possible Causes**:
  - TTL values too short
  - Cache invalidation too aggressive
  - Cache size too small
  - New data patterns not covered by cache
- **Resolution**:
  - Check TTL configurations and adjust if necessary
  - Analyze cache miss patterns to identify opportunities for pre-warming
  - Increase cache size if memory permits
  - Review invalidation strategies

#### Redis Connection Failures
- **Symptoms**: Error logs showing connection failures, increased latency
- **Possible Causes**:
  - Redis service down
  - Network issues
  - Authentication failures
  - Connection limits reached
- **Resolution**:
  - Verify Redis health: `redis-cli -h $REDIS_HOST -p $REDIS_PORT ping`
  - Check Redis logs for errors
  - Verify credentials in Kubernetes secrets
  - Check connection count and limits

#### High Redis Memory Usage
- **Symptoms**: Redis approaching memory limit, evictions increasing
- **Possible Causes**:
  - Too many cached items
  - Large values being cached
  - Memory fragmentation
  - Insufficient Redis memory allocation
- **Resolution**:
  - Review memory usage by key pattern: `redis-cli --bigkeys`
  - Consider reducing TTLs for less critical data
  - Increase Redis memory allocation
  - Enable LRU eviction policies

#### Service Latency Issues
- **Symptoms**: Slow response times, timeouts
- **Possible Causes**:
  - Redis performance issues
  - Network latency
  - High CPU usage
  - GC pauses
- **Resolution**:
  - Check Redis response times
  - Review network metrics
  - Analyze CPU usage patterns
  - Tune GC parameters if necessary
  - Consider scaling the service

### 6.2 Diagnostic Commands

#### Redis Diagnostics

1. **Check Redis connection**:
   ```bash
   kubectl -n borrow-rate-engine exec -it cache-service-xxx -- redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping
   ```

2. **Get Redis statistics**:
   ```bash
   kubectl -n borrow-rate-engine exec -it cache-service-xxx -- redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info
   ```

3. **Monitor Redis commands** (use sparingly in production):
   ```bash
   kubectl -n borrow-rate-engine exec -it cache-service-xxx -- redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD monitor
   ```

4. **Check key distribution**:
   ```bash
   kubectl -n borrow-rate-engine exec -it cache-service-xxx -- redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD --bigkeys
   ```

5. **Examine memory usage**:
   ```bash
   kubectl -n borrow-rate-engine exec -it cache-service-xxx -- redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info memory
   ```

#### Cache Service Diagnostics

1. **Check service logs**:
   ```bash
   kubectl -n borrow-rate-engine logs deployment/cache-service
   ```

2. **Filter for error logs**:
   ```bash
   kubectl -n borrow-rate-engine logs deployment/cache-service | grep -i error
   ```

3. **Check service health**:
   ```bash
   kubectl -n borrow-rate-engine exec -it cache-service-xxx -- curl -s localhost:8000/health
   ```

4. **Get service metrics**:
   ```bash
   kubectl -n borrow-rate-engine exec -it cache-service-xxx -- curl -s localhost:8000/metrics
   ```

5. **Check cache statistics via API**:
   ```bash
   kubectl -n borrow-rate-engine exec -it cache-service-xxx -- curl -s localhost:8000/stats
   ```

### 6.3 Health Check API

The Cache Service implements a health check API endpoint at `/health` that can be used to verify the service status.

**Python code example for health check** (from the `RedisCache` class):
```python
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
```

### 6.4 Accessing Cache Statistics

The Cache Service exposes detailed statistics that can be useful for troubleshooting.

**Python code example for get_stats** (from the `RedisCache` class):
```python
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
```

## 7. Common Operations

### 7.1 Cache Invalidation

#### Local Cache

The local in-memory cache automatically invalidates entries based on TTL values. You can also manually trigger cache cleanup:

```python
# Code example to clean up expired entries in the local cache
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
```

#### Redis Cache

To invalidate specific keys in Redis:

```bash
# Delete a specific key
kubectl -n borrow-rate-engine exec -it cache-service-xxx -- redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD DEL "borrow_rate_engine:borrow_rate:AAPL"

# Delete multiple keys matching a pattern
kubectl -n borrow-rate-engine exec -it cache-service-xxx -- redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD --scan --pattern "borrow_rate_engine:volatility:*" | xargs -L 1 redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD DEL
```

### 7.2 Scaling the Service

#### Horizontal Scaling

```bash
# Scale to 5 replicas
kubectl -n borrow-rate-engine scale deployment cache-service --replicas=5
```

#### Vertical Scaling

Vertical scaling requires updating the deployment resource limits:

```bash
# Update memory limit to 12Gi
kubectl -n borrow-rate-engine set resources deployment cache-service --limits=memory=12Gi
```

### 7.3 Restarting the Service

```bash
# Restart the service with zero downtime (rolling update)
kubectl -n borrow-rate-engine rollout restart deployment cache-service

# Monitor the rollout status
kubectl -n borrow-rate-engine rollout status deployment cache-service
```

### 7.4 Updating Service Configuration

```bash
# Update a ConfigMap value
kubectl -n borrow-rate-engine patch configmap cache-service-config -p '{"data":{"BORROW_RATE_TTL":"600"}}'

# Restart the service to apply the change
kubectl -n borrow-rate-engine rollout restart deployment cache-service
```

### 7.5 Manual Redis Connection

```bash
# Start Redis CLI
kubectl -n borrow-rate-engine exec -it cache-service-xxx -- redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD

# Useful Redis commands
# Get all keys matching a pattern
KEYS borrow_rate_engine:borrow_rate:*

# Get TTL for a key
TTL borrow_rate_engine:borrow_rate:AAPL

# Get memory usage of a key
MEMORY USAGE borrow_rate_engine:borrow_rate:AAPL

# Get database stats
INFO
```

## 8. Performance Tuning

### 8.1 Cache TTL Optimization

TTL values should be optimized based on data volatility and access patterns:

| Data Type | Considerations | Recommended Range |
|-----------|----------------|-------------------|
| Borrow Rates | Market data that changes frequently | 1-10 minutes |
| Volatility | Changes more slowly than rates | 5-30 minutes |
| Event Risk | Typically changes on a daily basis | 30-120 minutes |
| Broker Config | Administrative changes are infrequent | 15-60 minutes |
| Calculation | Frequently accessed, computation-heavy | 30-120 seconds |

Review cache miss patterns to identify opportunities for TTL adjustments:

```bash
# Review cache miss logs
kubectl -n borrow-rate-engine logs deployment/cache-service | grep -i "cache miss"
```

### 8.2 Redis Memory Optimization

1. **Monitor memory usage**:
   ```bash
   kubectl -n borrow-rate-engine exec -it cache-service-xxx -- redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD info memory
   ```

2. **Identify memory-intensive keys**:
   ```bash
   kubectl -n borrow-rate-engine exec -it cache-service-xxx -- redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD --bigkeys
   ```

3. **Configure maxmemory policy**:
   - Recommended: `volatile-lru` - Evict least recently used keys with an expire time
   - Alternative: `allkeys-lru` - Evict any key using LRU algorithm when memory limit is reached

4. **Adjust key expiration**:
   - Set appropriate TTLs for different data types
   - Consider shorter TTLs for large values

### 8.3 Cache Warmup Strategies

The Cache Service supports cache warmup on startup through the `CACHE_WARMUP_ON_STARTUP` configuration flag.

To implement custom cache warmup:

1. **Identify high-value data** to pre-populate
2. **Create a warmup script** that loads common keys
3. **Execute during off-peak hours** or after service restart

Example warmup for frequently traded securities:

```python
# Pseudo-code for cache warmup
def warm_up_cache():
    # List of frequently traded securities
    frequent_tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "META"]
    
    # Pre-fetch borrow rates
    for ticker in frequent_tickers:
        fetch_and_cache_borrow_rate(ticker)
        
    # Pre-fetch volatility data
    for ticker in frequent_tickers:
        fetch_and_cache_volatility(ticker)
```

### 8.4 Connection Pooling

Redis connection pooling is configured through the `REDIS_MAX_CONNECTIONS` environment variable.

Recommendations:
- Set max connections based on the number of service replicas
- Formula: `connections_per_instance = REDIS_MAX_CONNECTIONS / number_of_replicas`
- Default value (100) is suitable for most deployments
- For high-throughput environments, consider increasing to 200-300

### 8.5 Serialization Optimization

The Cache Service uses JSON serialization for cache values. For performance-critical applications, consider:

1. **Using more efficient serialization** formats like MessagePack or Protocol Buffers
2. **Compressing large values** before caching
3. **Precomputing and caching** frequently calculated values

## 9. Disaster Recovery

### 9.1 Redis Failure Scenarios

#### Complete Redis Failure

If Redis becomes completely unavailable:

1. The service will automatically fall back to using the local in-memory cache
2. Cache hit rates will decrease as each instance has its own local cache
3. Backend service load will increase due to more cache misses
4. Performance will degrade but the system will remain operational

**Resolution**:
- Identify and fix the Redis issue (connection, network, memory, etc.)
- The service will automatically reconnect to Redis when available

#### Redis Data Loss

In case of complete Redis data loss:

1. The cache will be empty and need to be rebuilt
2. Performance will temporarily degrade
3. The cache will be progressively populated as requests are processed

**Resolution**:
- Monitor system performance during cache rebuild
- Consider implementing cache warmup for critical data

### 9.2 Cache Service Failure Scenarios

#### Pod Crashes

If a Cache Service pod crashes:

1. Kubernetes will automatically restart the pod
2. Local cache for that instance will be lost and need to be rebuilt
3. The Redis cache will remain intact and available to other instances

**Resolution**:
- Check logs to identify the root cause of the crash
- Monitor pod restarts using `kubectl -n borrow-rate-engine get pods`

#### Full Service Outage

In case all Cache Service instances become unavailable:

1. Other services will experience increased latency
2. External API calls and database queries will increase
3. The system will remain operational but with degraded performance

**Recovery Steps**:
1. Verify Kubernetes node health
2. Check for resource constraints (CPU/memory)
3. Restart the deployment if necessary:
   ```bash
   kubectl -n borrow-rate-engine rollout restart deployment cache-service
   ```
4. Verify services are coming back online:
   ```bash
   kubectl -n borrow-rate-engine get pods -l component=cache-service
   kubectl -n borrow-rate-engine exec -it cache-service-xxx -- curl -s localhost:8000/health
   ```

### 9.3 Backup and Restore

Redis data should be considered ephemeral and can be rebuilt from source systems. However, for critical deployments:

1. **Redis RDB Snapshots**:
   - Configure Redis to save snapshots periodically
   - Store snapshots in a persistent location

2. **Redis AOF (Append-Only File)**:
   - Enable AOF for more granular data persistence
   - Balance between durability and performance

3. **Manual Backup**:
   ```bash
   kubectl -n borrow-rate-engine exec -it cache-service-xxx -- redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD SAVE
   ```

### 9.4 Recovery Procedures

#### Redis Reconnection

The Cache Service includes automatic reconnection logic:

```python
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
```

This reconnection logic uses exponential backoff to avoid overwhelming the Redis server during recovery.

## 10. References

### 10.1 Internal Documentation

- [Cache Service README](../../README.md)
- [System Architecture Document](../../../docs/architecture.md)
- [Kubernetes Deployment Guide](../../../docs/deployment.md)

### 10.2 Source Code

- [redis.py](../../../src/backend/services/cache/redis.py) - Redis cache implementation
- [local.py](../../../src/backend/services/cache/local.py) - Local cache implementation
- [utils.py](../../../src/backend/services/cache/utils.py) - Cache utility functions

### 10.3 Configuration

- [cache-service-deployment.yaml](../../../infrastructure/kubernetes/base/cache-service-deployment.yaml) - Kubernetes deployment configuration
- [configmap.yaml](../../../infrastructure/kubernetes/base/configmap.yaml) - ConfigMap for service configuration

### 10.4 External Documentation

- [Redis Documentation](https://redis.io/documentation) - Redis 7.0+
- [Kubernetes Documentation](https://kubernetes.io/docs/) - Kubernetes 1.28+
- [Grafana](https://grafana.com/docs/) - Monitoring dashboards 9.0+