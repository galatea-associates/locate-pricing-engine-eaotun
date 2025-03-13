This runbook provides comprehensive guidance for operating and maintaining the Data Service of the Borrow Rate & Locate Fee Pricing Engine. The Data Service is responsible for managing all data access, including external API integration, database operations, and caching of frequently accessed data.

The Data Service is a critical component of the system, as it provides the foundation for accurate fee calculations by ensuring reliable access to stock metadata, borrow rates, volatility metrics, and broker configurations. This runbook covers monitoring, troubleshooting, and maintenance procedures to ensure the Data Service operates reliably and efficiently.

## Introduction

### Purpose and Scope

This runbook is intended for operations engineers, SREs, and on-call personnel responsible for maintaining the Borrow Rate & Locate Fee Pricing Engine. It provides:

- Detailed information about the Data Service architecture and components
- Monitoring procedures and key metrics to watch
- Troubleshooting steps for common issues
- Maintenance procedures for routine operations
- Recovery procedures for incident response

This document should be used in conjunction with the general troubleshooting guide and incident response procedures.

### Service Overview

The Data Service is implemented as a FastAPI application running in Kubernetes. It provides the following key functions:

1. **Stock Data Management**: Retrieves and manages stock metadata and borrow rates
2. **Broker Configuration**: Manages broker-specific fee structures and settings
3. **Volatility Data**: Handles volatility metrics and event risk factors
4. **External API Integration**: Connects to SecLend API, Market Data API, and Event Calendar API
5. **Caching**: Implements caching strategies for frequently accessed data
6. **Fallback Mechanisms**: Provides fallback strategies when external sources are unavailable
7. **Audit Logging**: Records all data operations for compliance and troubleshooting

The Data Service exposes the following primary endpoints:

- `/health`: System health check
- `/api/v1/stocks/{ticker}`: Get stock metadata
- `/api/v1/stocks/{ticker}/borrow-rate`: Get current borrow rate
- `/api/v1/brokers/{client_id}`: Get broker configuration
- `/api/v1/volatility/{ticker}`: Get volatility metrics
- `/metrics`: Prometheus metrics endpoint

The service is designed to be horizontally scalable and highly available, with a minimum of 3 replicas deployed across multiple availability zones.

### Architecture

The Data Service is deployed as a Kubernetes service with the following components:

**Deployment Configuration:**
- Image: `${ECR_REPO}/borrow-rate-engine-data:${VERSION}`
- Replicas: 3 (minimum)
- CPU Request: 500m, Limit: 2000m
- Memory Request: 1Gi, Limit: 4Gi
- Health Probes: Liveness, Readiness, and Startup probes on `/health`
- Update Strategy: RollingUpdate with maxSurge=1, maxUnavailable=0

**Service Configuration:**
- Type: ClusterIP
- Port: 80 (forwards to container port 8000)

**Dependencies:**
- PostgreSQL Database: For stock, broker, and volatility data
- Redis: For caching frequently accessed data
- SecLend API: For real-time borrow rates
- Market Data API: For volatility metrics
- Event Calendar API: For event risk factors

**Key Configuration Parameters:**
- `ENVIRONMENT`: Environment name (dev/staging/prod)
- `LOG_LEVEL`: Logging verbosity (INFO/DEBUG/WARNING/ERROR)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECLEND_API_URL`: URL for SecLend API
- `SECLEND_API_KEY`: API key for SecLend API
- `MARKET_API_URL`: URL for Market Data API
- `MARKET_API_KEY`: API key for Market Data API
- `EVENT_API_URL`: URL for Event Calendar API
- `EVENT_API_KEY`: API key for Event Calendar API
- `CACHE_TTL_BORROW_RATE`: TTL for borrow rate cache (seconds)
- `CACHE_TTL_VOLATILITY`: TTL for volatility data cache (seconds)
- `CACHE_TTL_BROKER_CONFIG`: TTL for broker configuration cache (seconds)
- `ENABLE_FALLBACK`: Flag to enable/disable fallback mechanisms

## Monitoring

Effective monitoring of the Data Service is essential for detecting issues early and ensuring optimal performance. This section covers key metrics to monitor and how to use the monitoring dashboards.

### Key Metrics

The following metrics should be monitored for the Data Service:

**Request Metrics:**
- **Request Rate**: Number of requests per second
  - Alert threshold: >500 requests/second (warning), >800 requests/second (critical)
- **Response Time**: Time taken to process requests in milliseconds
  - Alert threshold: >100ms p95 (warning), >250ms p95 (critical)
- **Error Rate**: Percentage of requests resulting in errors (4xx/5xx)
  - Alert threshold: >1% (warning), >5% (critical)

**External API Metrics:**
- **External API Success Rate**: Percentage of successful external API calls
  - Alert threshold: <99% (warning), <95% (critical)
- **External API Latency**: Response time from external APIs
  - Alert threshold: >300ms p95 (warning), >500ms p95 (critical)
- **Fallback Usage Rate**: Percentage of requests using fallback mechanisms
  - Alert threshold: >1% (warning), >5% (critical)

**Cache Metrics:**
- **Cache Hit Rate**: Percentage of cache hits vs. total cache lookups
  - Alert threshold: <90% (warning), <80% (critical)
- **Cache Latency**: Time taken for cache operations
  - Alert threshold: >10ms p95 (warning), >50ms p95 (critical)
- **Cache Size**: Memory usage of cached data
  - Alert threshold: >70% of allocated memory (warning), >85% (critical)

**Database Metrics:**
- **Query Latency**: Time taken for database queries
  - Alert threshold: >50ms p95 (warning), >100ms p95 (critical)
- **Connection Pool Usage**: Percentage of database connections in use
  - Alert threshold: >70% (warning), >85% (critical)
- **Database Errors**: Rate of database operation errors
  - Alert threshold: >0.1% (warning), >1% (critical)

**Resource Metrics:**
- **CPU Usage**: Percentage of CPU limit used
  - Alert threshold: >70% (warning), >85% (critical)
- **Memory Usage**: Percentage of memory limit used
  - Alert threshold: >70% (warning), >85% (critical)
- **Pod Restarts**: Number of pod restarts
  - Alert threshold: >0 in 15 minutes (warning), >2 in 15 minutes (critical)

```
# Prometheus queries for key metrics

# Request rate
sum(rate(http_requests_total{namespace="borrow-rate-engine", app="data-service"}[5m]))

# Response time (p95)
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{namespace="borrow-rate-engine", app="data-service"}[5m])) by (le))

# Error rate
sum(rate(http_requests_total{namespace="borrow-rate-engine", app="data-service", status_code=~"[45].*"}[5m])) / sum(rate(http_requests_total{namespace="borrow-rate-engine", app="data-service"}[5m]))

# External API success rate
sum(rate(external_api_requests_total{namespace="borrow-rate-engine", app="data-service", status="success"}[5m])) / sum(rate(external_api_requests_total{namespace="borrow-rate-engine", app="data-service"}[5m]))

# External API latency (p95)
histogram_quantile(0.95, sum(rate(external_api_request_duration_seconds_bucket{namespace="borrow-rate-engine", app="data-service"}[5m])) by (le, api))

# Fallback usage rate
sum(rate(fallback_usage_total{namespace="borrow-rate-engine", app="data-service"}[5m])) / sum(rate(external_api_requests_total{namespace="borrow-rate-engine", app="data-service"}[5m]))

# Cache hit rate
sum(rate(cache_hits_total{namespace="borrow-rate-engine", app="data-service"}[5m])) / sum(rate(cache_requests_total{namespace="borrow-rate-engine", app="data-service"}[5m]))

# Cache latency (p95)
histogram_quantile(0.95, sum(rate(cache_operation_duration_seconds_bucket{namespace="borrow-rate-engine", app="data-service"}[5m])) by (le, operation))

# Database query latency (p95)
histogram_quantile(0.95, sum(rate(database_query_duration_seconds_bucket{namespace="borrow-rate-engine", app="data-service"}[5m])) by (le, query_type))

# Connection pool usage
sum(database_connections_in_use{namespace="borrow-rate-engine", app="data-service"}) / sum(database_connections_max{namespace="borrow-rate-engine", app="data-service"})

# CPU usage
sum(rate(container_cpu_usage_seconds_total{namespace="borrow-rate-engine", pod=~"data-service-.*"}[5m])) / sum(kube_pod_container_resource_limits_cpu_cores{namespace="borrow-rate-engine", pod=~"data-service-.*"})

# Memory usage
sum(container_memory_usage_bytes{namespace="borrow-rate-engine", pod=~"data-service-.*"}) / sum(kube_pod_container_resource_limits_memory_bytes{namespace="borrow-rate-engine", pod=~"data-service-.*"})
```

### Monitoring Dashboards

The following Grafana dashboards are available for monitoring the Data Service:

1. **Data Service Overview Dashboard**
   - URL: https://grafana.example.com/d/data-service-overview
   - Purpose: High-level overview of Data Service health and performance
   - Key panels: Request rate, error rate, latency, external API status

2. **Data Service Detailed Dashboard**
   - URL: https://grafana.example.com/d/data-service-detailed
   - Purpose: Detailed metrics for in-depth analysis
   - Key panels: Endpoint-specific metrics, external API performance, cache performance

3. **External API Dashboard**
   - URL: https://grafana.example.com/d/external-api-performance
   - Purpose: Detailed metrics for external API integration
   - Key panels: API success rates, latency, error rates, fallback usage

4. **Cache Performance Dashboard**
   - URL: https://grafana.example.com/d/cache-performance
   - Purpose: Detailed metrics for cache performance
   - Key panels: Hit rates, latency, memory usage, eviction rates

5. **Database Performance Dashboard**
   - URL: https://grafana.example.com/d/database-performance
   - Purpose: Detailed metrics for database performance
   - Key panels: Query latency, connection pool usage, error rates

These dashboards can be filtered by time range, environment, and specific instances to narrow down the analysis.

```
# Dashboard URLs with useful parameters

# Last hour with 5s refresh
https://grafana.example.com/d/data-service-overview?from=now-1h&to=now&refresh=5s

# Filter to specific endpoint
https://grafana.example.com/d/data-service-detailed?var-endpoint=stocks_borrow_rate

# Filter to specific external API
https://grafana.example.com/d/external-api-performance?var-api=seclend

# Filter to specific cache type
https://grafana.example.com/d/cache-performance?var-cache_type=borrow_rate

# Filter to specific database operation
https://grafana.example.com/d/database-performance?var-query_type=stock_lookup
```

### Log Analysis

The Data Service generates structured logs that can be analyzed using Loki. Key log patterns to monitor include:

1. **External API Errors**
   - Pattern: `level=ERROR msg="External API error"`
   - Importance: Critical for identifying external API issues
   - Action: Investigate immediately for potential data availability issues

2. **Fallback Activation**
   - Pattern: `level=WARNING msg="Using fallback mechanism"`
   - Importance: High for identifying external API failures
   - Action: Check external API status and connectivity

3. **Database Errors**
   - Pattern: `level=ERROR msg="Database error"`
   - Importance: Critical for identifying data persistence issues
   - Action: Check database status and connectivity

4. **Cache Errors**
   - Pattern: `level=ERROR msg="Cache error"`
   - Importance: Medium for identifying cache issues
   - Action: Check Redis status and connectivity

5. **Data Validation Errors**
   - Pattern: `level=WARNING msg="Data validation error"`
   - Importance: Medium for identifying data quality issues
   - Action: Review data sources and validation rules

Use the following LogQL queries to analyze logs:

```
# LogQL queries for Data Service logs

# All errors
{namespace="borrow-rate-engine", app="data-service"} |= "level=ERROR"

# External API errors
{namespace="borrow-rate-engine", app="data-service"} |= "External API error"

# Fallback activation
{namespace="borrow-rate-engine", app="data-service"} |= "Using fallback mechanism"

# Database errors
{namespace="borrow-rate-engine", app="data-service"} |= "Database error"

# Cache errors
{namespace="borrow-rate-engine", app="data-service"} |= "Cache error"

# Data validation errors
{namespace="borrow-rate-engine", app="data-service"} |= "Data validation error"

# Errors for specific external API
{namespace="borrow-rate-engine", app="data-service"} |= "api=\"seclend\"" |= "level=ERROR"

# Errors for specific ticker
{namespace="borrow-rate-engine", app="data-service"} |= "ticker=\"AAPL\"" |= "level=ERROR"
```

### Health Checks

The Data Service provides health check endpoints that can be used to verify its status:

1. **Basic Health Check**
   - Endpoint: `/health`
   - Method: GET
   - Expected Response: `{"status":"healthy","version":"1.0.0"}`
   - Purpose: Quick verification of Data Service availability

2. **Detailed Health Check**
   - Endpoint: `/health/detailed`
   - Method: GET
   - Expected Response: `{"status":"healthy","version":"1.0.0","dependencies":{...}}`
   - Purpose: Comprehensive health check including dependencies

3. **External API Health Check**
   - Endpoint: `/health/external-apis`
   - Method: GET
   - Expected Response: `{"seclend":"healthy","market":"healthy","event":"healthy"}`
   - Purpose: Check status of external API connections

4. **Database Health Check**
   - Endpoint: `/health/database`
   - Method: GET
   - Expected Response: `{"status":"healthy","connection_pool":"healthy","latency_ms":5}`
   - Purpose: Check database connectivity and performance

5. **Cache Health Check**
   - Endpoint: `/health/cache`
   - Method: GET
   - Expected Response: `{"status":"healthy","hit_rate":0.95,"latency_ms":2}`
   - Purpose: Check cache status and performance

These health checks are used by monitoring systems and load balancers to determine if the Data Service is functioning correctly.

```
# Check basic health
curl -v http://data-service:8000/health

# Check detailed health
curl -v http://data-service:8000/health/detailed

# Check external API health
curl -v http://data-service:8000/health/external-apis

# Check database health
curl -v http://data-service:8000/health/database

# Check cache health
curl -v http://data-service:8000/health/cache

# Check health directly on pod
kubectl exec -n borrow-rate-engine deploy/data-service -- curl -s http://localhost:8000/health

# Check Kubernetes probe status
kubectl describe pod -n borrow-rate-engine data-service-abc123 | grep -A 10 "Liveness"
```

## Common Issues

This section covers common issues that may occur with the Data Service and provides troubleshooting steps for each issue.

### External API Connectivity Issues

External API connectivity issues occur when the Data Service cannot properly communicate with external data providers like SecLend API, Market Data API, or Event Calendar API.

**Symptoms:**
- Increased error rates for external API requests
- Error logs mentioning "External API error"
- Increased fallback mechanism usage
- Client reports of stale or incorrect data

**Possible Causes:**
1. **External API Availability**
   - External API service is down
   - Maintenance windows or outages
   - Rate limiting or throttling

2. **Network Connectivity**
   - Network issues between Data Service and external APIs
   - DNS resolution problems
   - Firewall or security group restrictions

3. **Authentication Issues**
   - Expired API keys
   - Invalid API keys
   - Changed authentication requirements

4. **Request Formatting**
   - Invalid request parameters
   - Changed API contract
   - Versioning issues

**Troubleshooting Steps:**

1. **Check External API Status**
   - Verify external API status pages
   - Test direct API calls from outside the cluster
   - Check for announced maintenance or outages

2. **Verify Network Connectivity**
   - Test network connectivity from Data Service to external APIs
   - Check DNS resolution
   - Verify firewall and security group rules

3. **Check Authentication Configuration**
   - Verify API key configuration
   - Check for API key expiration
   - Test authentication directly

4. **Examine Request Formatting**
   - Review request logs
   - Check for API contract changes
   - Verify request parameters

**Resolution Steps:**

1. **For External API Availability Issues:**
   - Wait for external API to recover
   - Ensure fallback mechanisms are working
   - Contact external API provider if necessary

2. **For Network Connectivity Issues:**
   - Fix DNS resolution problems
   - Update firewall or security group rules
   - Work with network team to resolve connectivity issues

3. **For Authentication Issues:**
   - Update API keys
   - Fix authentication configuration
   - Contact external API provider for new credentials

4. **For Request Formatting Issues:**
   - Update request formatting
   - Adapt to API contract changes
   - Fix parameter validation

**Verification:**
- Test external API connectivity directly
- Monitor external API success rate
- Verify fallback mechanisms are no longer being used
- Check for external API error logs

```
# Commands for external API connectivity troubleshooting

# Check external API error logs
kubectl logs -n borrow-rate-engine -l app=data-service --tail=100 | grep "External API error"

# Check fallback usage logs
kubectl logs -n borrow-rate-engine -l app=data-service --tail=100 | grep "Using fallback mechanism"

# Test SecLend API connectivity directly
kubectl exec -n borrow-rate-engine deploy/data-service -- curl -v -H "X-API-Key: $SECLEND_API_KEY" $SECLEND_API_URL/api/borrows/AAPL

# Test Market Data API connectivity directly
kubectl exec -n borrow-rate-engine deploy/data-service -- curl -v -H "X-API-Key: $MARKET_API_KEY" $MARKET_API_URL/api/market/volatility/AAPL

# Test Event Calendar API connectivity directly
kubectl exec -n borrow-rate-engine deploy/data-service -- curl -v -H "X-API-Key: $EVENT_API_KEY" $EVENT_API_URL/api/calendar/events?ticker=AAPL

# Check DNS resolution
kubectl exec -n borrow-rate-engine deploy/data-service -- nslookup $(echo $SECLEND_API_URL | cut -d'/' -f3)

# Check API key configuration
kubectl get secret -n borrow-rate-engine external-api-keys -o yaml

# Update API key if needed
kubectl patch secret -n borrow-rate-engine external-api-keys --type=merge -p '{"data":{"SECLEND_API_KEY":"'$(echo -n "new-api-key" | base64)'"}}'

# Restart Data Service to apply new API key
kubectl rollout restart deployment/data-service -n borrow-rate-engine
```

### Database Connectivity Issues

Database connectivity issues occur when the Data Service cannot properly communicate with the PostgreSQL database.

**Symptoms:**
- Increased error rates for database operations
- Error logs mentioning "Database error"
- 500 Internal Server Error responses
- Inability to retrieve or update data

**Possible Causes:**
1. **Database Availability**
   - Database service is down
   - Database maintenance or failover
   - Resource constraints

2. **Connection Pool Issues**
   - Connection pool exhaustion
   - Connection leaks
   - Connection timeouts

3. **Authentication Issues**
   - Invalid database credentials
   - Changed authentication requirements
   - Permission issues

4. **Query Issues**
   - Invalid SQL queries
   - Schema changes
   - Deadlocks or locks

**Troubleshooting Steps:**

1. **Check Database Status**
   - Verify database service is running
   - Check database logs for errors
   - Verify database resource usage

2. **Examine Connection Pool**
   - Check connection pool metrics
   - Verify connection pool configuration
   - Look for connection leaks

3. **Verify Authentication**
   - Check database credentials
   - Test direct database connection
   - Verify database user permissions

4. **Review Query Execution**
   - Check for slow queries
   - Verify schema compatibility
   - Look for deadlocks or locks

**Resolution Steps:**

1. **For Database Availability Issues:**
   - Restore database service
   - Wait for maintenance to complete
   - Scale database resources if needed

2. **For Connection Pool Issues:**
   - Adjust connection pool size
   - Fix connection leaks
   - Implement connection timeout handling

3. **For Authentication Issues:**
   - Update database credentials
   - Fix authentication configuration
   - Adjust database user permissions

4. **For Query Issues:**
   - Fix invalid queries
   - Update schema references
   - Resolve deadlocks or locks

**Verification:**
- Test database connectivity directly
- Monitor database operation success rate
- Check for database error logs
- Verify data retrieval and update operations

```
# Commands for database connectivity troubleshooting

# Check database error logs
kubectl logs -n borrow-rate-engine -l app=data-service --tail=100 | grep "Database error"

# Check database connection pool metrics
kubectl exec -n borrow-rate-engine deploy/data-service -- curl -s http://localhost:8000/metrics | grep database_connections

# Test database connectivity directly
kubectl exec -n borrow-rate-engine deploy/data-service -- python -c "import psycopg2; conn = psycopg2.connect('$DATABASE_URL'); print('Connection successful'); conn.close()"

# Check database status
kubectl exec -n borrow-rate-engine deploy/postgresql-0 -- pg_isready

# Check database connection count
kubectl exec -n borrow-rate-engine deploy/postgresql-0 -- psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check for long-running queries
kubectl exec -n borrow-rate-engine deploy/postgresql-0 -- psql -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE state != 'idle' ORDER BY duration DESC LIMIT 10;"

# Check for locks
kubectl exec -n borrow-rate-engine deploy/postgresql-0 -- psql -c "SELECT relation::regclass, mode, pid, granted FROM pg_locks l JOIN pg_stat_activity a ON l.pid = a.pid;"

# Restart Data Service to reset connections
kubectl rollout restart deployment/data-service -n borrow-rate-engine
```

### Cache Connectivity Issues

Cache connectivity issues occur when the Data Service cannot properly communicate with the Redis cache.

**Symptoms:**
- Increased latency for data retrieval
- Error logs mentioning "Cache error"
- Decreased cache hit rate
- Increased load on external APIs and database

**Possible Causes:**
1. **Redis Availability**
   - Redis service is down
   - Redis maintenance or failover
   - Resource constraints

2. **Connection Issues**
   - Network connectivity problems
   - Authentication failures
   - Connection timeouts

3. **Cache Configuration**
   - Invalid cache configuration
   - Incorrect TTL settings
   - Memory limits reached

4. **Data Serialization**
   - Serialization errors
   - Data format changes
   - Incompatible data types

**Troubleshooting Steps:**

1. **Check Redis Status**
   - Verify Redis service is running
   - Check Redis logs for errors
   - Verify Redis resource usage

2. **Test Redis Connectivity**
   - Test direct Redis connection
   - Verify Redis authentication
   - Check network connectivity

3. **Examine Cache Configuration**
   - Verify Redis URL configuration
   - Check TTL settings
   - Review memory usage and limits

4. **Verify Data Serialization**
   - Check for serialization errors
   - Verify data format compatibility
   - Test with simple data types

**Resolution Steps:**

1. **For Redis Availability Issues:**
   - Restore Redis service
   - Wait for maintenance to complete
   - Scale Redis resources if needed

2. **For Connection Issues:**
   - Fix network connectivity
   - Update Redis authentication
   - Implement connection retry logic

3. **For Cache Configuration Issues:**
   - Update Redis URL configuration
   - Adjust TTL settings
   - Increase memory limits if needed

4. **For Data Serialization Issues:**
   - Fix serialization logic
   - Update data format handling
   - Implement error handling for serialization

**Verification:**
- Test Redis connectivity directly
- Monitor cache hit rate
- Check for cache error logs
- Verify cache operations are working

```
# Commands for cache connectivity troubleshooting

# Check cache error logs
kubectl logs -n borrow-rate-engine -l app=data-service --tail=100 | grep "Cache error"

# Check cache metrics
kubectl exec -n borrow-rate-engine deploy/data-service -- curl -s http://localhost:8000/metrics | grep cache

# Test Redis connectivity directly
kubectl exec -n borrow-rate-engine deploy/data-service -- redis-cli -h redis-master ping

# Check Redis memory usage
kubectl exec -n borrow-rate-engine deploy/redis-master -- redis-cli info memory

# Check Redis key count
kubectl exec -n borrow-rate-engine deploy/redis-master -- redis-cli dbsize

# Check specific cache keys
kubectl exec -n borrow-rate-engine deploy/redis-master -- redis-cli keys "borrow_rate:*"

# Get TTL for a specific key
kubectl exec -n borrow-rate-engine deploy/redis-master -- redis-cli ttl "borrow_rate:AAPL"

# Test cache set operation
kubectl exec -n borrow-rate-engine deploy/redis-master -- redis-cli set test_key test_value ex 60

# Test cache get operation
kubectl exec -n borrow-rate-engine deploy/redis-master -- redis-cli get test_key

# Restart Data Service to reset cache connections
kubectl rollout restart deployment/data-service -n borrow-rate-engine
```

### Data Synchronization Issues

Data synchronization issues occur when the Data Service cannot properly synchronize data between external sources, the database, and the cache.

**Symptoms:**
- Stale or inconsistent data
- Discrepancies between cached and database data
- Unexpected data values
- Client reports of incorrect calculations

**Possible Causes:**
1. **Cache Invalidation**
   - Failed cache invalidation
   - Incorrect TTL settings
   - Race conditions

2. **External Data Refresh**
   - Failed external data refresh
   - Partial data updates
   - Rate limiting during refresh

3. **Database Updates**
   - Failed database updates
   - Transaction issues
   - Concurrent update conflicts

4. **Data Transformation**
   - Incorrect data mapping
   - Format conversion errors
   - Schema mismatches

**Troubleshooting Steps:**

1. **Verify Data Consistency**
   - Compare data across sources
   - Check data timestamps
   - Verify data refresh logs

2. **Examine Cache Invalidation**
   - Check cache invalidation logs
   - Verify TTL settings
   - Test manual cache invalidation

3. **Check External Data Refresh**
   - Review data refresh logs
   - Verify external API responses
   - Check refresh schedules

4. **Inspect Database Updates**
   - Check database update logs
   - Verify transaction success
   - Look for update conflicts

**Resolution Steps:**

1. **For Cache Invalidation Issues:**
   - Manually invalidate affected cache entries
   - Adjust TTL settings
   - Fix cache invalidation logic

2. **For External Data Refresh Issues:**
   - Trigger manual data refresh
   - Fix external API integration
   - Adjust refresh schedules

3. **For Database Update Issues:**
   - Fix transaction handling
   - Implement retry logic
   - Resolve update conflicts

4. **For Data Transformation Issues:**
   - Fix data mapping logic
   - Update format conversion
   - Align schema definitions

**Verification:**
- Compare data across all sources
- Verify data freshness
- Check for data consistency
- Test end-to-end data flow

```
# Commands for data synchronization troubleshooting

# Check data refresh logs
kubectl logs -n borrow-rate-engine -l app=data-service --tail=100 | grep "Data refresh"

# Check cache invalidation logs
kubectl logs -n borrow-rate-engine -l app=data-service --tail=100 | grep "Cache invalidation"

# Compare cached and database data for a ticker
kubectl exec -n borrow-rate-engine deploy/data-service -- python -c "from services.data.stocks import stock_service; from db.session import SessionLocal; db = SessionLocal(); print('DB:', stock_service.get_stock_from_db(db, 'AAPL')); print('Cache:', stock_service.get_stock_from_cache('AAPL'))"

# Check data timestamps
kubectl exec -n borrow-rate-engine deploy/postgresql-0 -- psql -c "SELECT ticker, last_updated FROM stock ORDER BY last_updated DESC LIMIT 10;"

# Manually invalidate cache for a ticker
kubectl exec -n borrow-rate-engine deploy/data-service -- python -c "from services.data.stocks import stock_service; print(stock_service.invalidate_stock_cache('AAPL'))"

# Trigger manual data refresh for a ticker
kubectl exec -n borrow-rate-engine deploy/data-service -- python -c "from services.data.stocks import stock_service; print(stock_service.sync_stock_from_external('AAPL'))"

# Check external API response for a ticker
kubectl exec -n borrow-rate-engine deploy/data-service -- python -c "from services.external.seclend_api import get_borrow_rate; print(get_borrow_rate('AAPL'))"

# Check database record for a ticker
kubectl exec -n borrow-rate-engine deploy/postgresql-0 -- psql -c "SELECT * FROM stock WHERE ticker = 'AAPL';"
```

### Performance Issues

Performance issues occur when the Data Service experiences high latency, timeout errors, or resource constraints affecting response times.

**Symptoms:**
- Increased response times
- Timeout errors
- High CPU or memory utilization
- Client reports of slow API responses

**Possible Causes:**
1. **Resource Constraints**
   - Insufficient CPU or memory allocation
   - Pod scheduling issues
   - Node resource contention

2. **External Dependency Performance**
   - Slow external API responses
   - Database performance issues
   - Redis performance issues

3. **High Traffic Volume**
   - Request spikes
   - Insufficient scaling
   - Inefficient request handling

4. **Code Inefficiencies**
   - Unoptimized data processing
   - Memory leaks
   - Blocking operations

**Troubleshooting Steps:**

1. **Analyze Resource Usage**
   - Check CPU and memory metrics
   - Review pod resource allocation
   - Examine node resource utilization

2. **Profile Request Latency**
   - Identify slow endpoints
   - Measure external dependency response times
   - Check database query performance

3. **Examine Traffic Patterns**
   - Analyze request volume and distribution
   - Identify peak traffic periods
   - Check for unusual request patterns

4. **Review Code Performance**
   - Look for inefficient algorithms
   - Check for blocking operations
   - Identify memory usage patterns

**Resolution Steps:**

1. **For Resource Constraints:**
   - Increase CPU/memory allocation
   - Adjust pod scheduling
   - Scale horizontally

2. **For External Dependency Performance:**
   - Optimize external API usage
   - Implement more aggressive caching
   - Tune database queries

3. **For High Traffic:**
   - Implement auto-scaling
   - Optimize request handling
   - Consider rate limiting

4. **For Code Inefficiencies:**
   - Optimize data processing algorithms
   - Implement asynchronous processing
   - Fix memory leaks

**Verification:**
- Monitor response times under load
- Check resource utilization after changes
- Verify client experience improves

```
# Commands for performance troubleshooting

# Check resource usage
kubectl top pods -n borrow-rate-engine -l app=data-service

# Check resource limits and requests
kubectl get pods -n borrow-rate-engine -l app=data-service -o jsonpath='{.items[0].spec.containers[0].resources}'

# Profile endpoint latency
kubectl exec -n borrow-rate-engine deploy/data-service -- curl -s http://localhost:8000/metrics | grep http_request_duration_seconds

# Check external API latency
kubectl exec -n borrow-rate-engine deploy/data-service -- curl -s http://localhost:8000/metrics | grep external_api_request_duration_seconds

# Check database query latency
kubectl exec -n borrow-rate-engine deploy/data-service -- curl -s http://localhost:8000/metrics | grep database_query_duration_seconds

# Analyze traffic patterns
kubectl exec -n borrow-rate-engine deploy/data-service -- curl -s http://localhost:8000/metrics | grep http_requests_total

# Check for memory leaks
kubectl exec -n borrow-rate-engine deploy/data-service -- curl -s http://localhost:8000/metrics | grep process_resident_memory_bytes

# Increase resource limits if needed
kubectl patch deployment/data-service -n borrow-rate-engine -p '{"spec":{"template":{"spec":{"containers":[{"name":"data-service","resources":{"requests":{"cpu":"1000m","memory":"2Gi"},"limits":{"cpu":"3000m","memory":"6Gi"}}}]}}}}}'

# Scale horizontally
kubectl scale deployment/data-service -n borrow-rate-engine --replicas=5