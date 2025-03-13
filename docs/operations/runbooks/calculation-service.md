## Introduction

This runbook provides comprehensive guidance for operating and maintaining the Calculation Service of the Borrow Rate & Locate Fee Pricing Engine. The Calculation Service is a critical component that implements the core business logic for borrow rate and fee calculations.

The Calculation Service is responsible for executing the financial formulas that determine borrow rates, apply volatility and event risk adjustments, calculate client-specific fees, and handle fallback scenarios when external data sources are unavailable. This runbook covers monitoring, troubleshooting, and maintenance procedures to ensure the Calculation Service operates reliably and accurately.

### Purpose and Scope

This runbook is intended for operations engineers, SREs, and on-call personnel responsible for maintaining the Borrow Rate & Locate Fee Pricing Engine. It provides:

- Detailed information about the Calculation Service architecture and components
- Monitoring procedures and key metrics to watch
- Troubleshooting steps for common issues
- Maintenance procedures for routine operations
- Recovery procedures for incident response

This document should be used in conjunction with the general troubleshooting guide and incident response procedures.

### Service Overview

The Calculation Service is implemented as a FastAPI application running in Kubernetes. It provides the following key functions:

1. **Borrow Rate Calculation**: Calculates base borrow rates with volatility and event risk adjustments
2. **Fee Calculation**: Applies broker-specific markups and transaction fees to base rates
3. **Fallback Handling**: Implements fallback strategies when external data sources are unavailable
4. **Caching Integration**: Uses caching for performance optimization
5. **Audit Logging**: Records all calculations for compliance and troubleshooting

The Calculation Service exposes the following primary endpoints:

- `/health`: System health check
- `/health/detailed`: Detailed health check with dependency status
- `/internal/calculate`: Internal endpoint for fee calculations
- `/internal/borrow-rate/{ticker}`: Internal endpoint for borrow rate calculations
- `/internal/metrics`: Prometheus metrics endpoint

The service is designed to be horizontally scalable and highly available, with a minimum of 3 replicas deployed across multiple availability zones.

### Architecture

The Calculation Service is deployed as a Kubernetes service with the following components:

**Deployment Configuration:**
- Image: `${ECR_REPO}/calculation-service:${VERSION}`
- Replicas: 3 (minimum)
- CPU Request: 1000m, Limit: 3000m
- Memory Request: 2Gi, Limit: 6Gi
- Health Probes: Liveness, Readiness, and Startup probes on `/health`
- Update Strategy: RollingUpdate with maxSurge=1, maxUnavailable=0

**Service Configuration:**
- Type: ClusterIP
- Port: 80 (forwards to container port 8000)

**Dependencies:**
- Data Service: For stock, broker, and volatility data
- Cache Service: For caching calculation results
- Audit Service: For logging calculation details

**Key Configuration Parameters:**
- `ENVIRONMENT`: Environment name (dev/staging/prod)
- `LOG_LEVEL`: Logging verbosity (INFO/DEBUG/WARNING/ERROR)
- `DATA_SERVICE_URL`: URL for Data Service
- `CACHE_SERVICE_URL`: URL for Cache Service
- `AUDIT_SERVICE_URL`: URL for Audit Service
- `ENABLE_CACHING`: Flag to enable/disable calculation caching
- `CACHE_TTL_SECONDS`: Cache time-to-live in seconds
- `ENABLE_FALLBACK`: Flag to enable/disable fallback mechanisms
- `DEFAULT_MINIMUM_BORROW_RATE`: Fallback minimum rate
- `DEFAULT_VOLATILITY_FACTOR`: Default volatility adjustment factor
- `DEFAULT_EVENT_RISK_FACTOR`: Default event risk adjustment factor
- `DEFAULT_MARKUP_PERCENTAGE`: Default markup percentage
- `DEFAULT_TRANSACTION_FEE_FLAT`: Default flat transaction fee
- `DEFAULT_TRANSACTION_FEE_PERCENTAGE`: Default percentage transaction fee

### Core Calculation Components

The Calculation Service consists of the following key components:

1. **Borrow Rate Calculator**: Calculates borrow rates with adjustments
   - Retrieves base rates from Data Service
   - Applies volatility adjustments
   - Applies event risk adjustments
   - Enforces minimum rate thresholds
   - Implements fallback mechanisms

2. **Fee Calculator**: Calculates total fees for securities borrowing
   - Calculates base borrow cost
   - Applies broker-specific markups
   - Calculates transaction fees
   - Provides detailed fee breakdowns
   - Handles time-based proration

3. **Formula Engine**: Implements core financial formulas
   - Annualized/daily rate conversions
   - Borrow cost calculations
   - Markup calculations
   - Fee type handling (flat/percentage)
   - Volatility and risk adjustments

4. **Caching Layer**: Optimizes performance through caching
   - Caches borrow rates
   - Caches calculation results
   - Implements appropriate TTLs
   - Handles cache invalidation

5. **Audit Logger**: Records calculation details
   - Logs calculation inputs
   - Records calculation results
   - Captures data sources used
   - Provides audit trail for compliance

These components work together to provide accurate and efficient financial calculations for the pricing engine.

## Monitoring

Effective monitoring of the Calculation Service is essential for detecting issues early and ensuring optimal performance. This section covers key metrics to monitor and how to use the monitoring dashboards.

### Key Metrics

The following metrics should be monitored for the Calculation Service:

**Calculation Metrics:**
- **Calculation Rate**: Number of calculations per second
  - Alert threshold: >700 calculations/second (warning), >900 calculations/second (critical)
- **Calculation Duration**: Time taken to perform calculations in milliseconds
  - Alert threshold: >50ms p95 (warning), >100ms p95 (critical)
- **Calculation Errors**: Percentage of calculations resulting in errors
  - Alert threshold: >0.1% (warning), >1% (critical)

**Borrow Rate Metrics:**
- **Borrow Rate Calculation Duration**: Time to calculate borrow rates in milliseconds
  - Alert threshold: >30ms p95 (warning), >60ms p95 (critical)
- **Volatility Adjustment Impact**: Average percentage impact of volatility adjustments
  - Alert threshold: Sudden change >50% (warning)
- **Event Risk Adjustment Impact**: Average percentage impact of event risk adjustments
  - Alert threshold: Sudden change >50% (warning)
- **Fallback Usage Rate**: Percentage of calculations using fallback mechanisms
  - Alert threshold: >5% (warning), >10% (critical)

**Fee Calculation Metrics:**
- **Fee Calculation Duration**: Time to calculate fees in milliseconds
  - Alert threshold: >20ms p95 (warning), >40ms p95 (critical)
- **Average Fee Amount**: Average fee calculated across all requests
  - Alert threshold: Sudden change >20% (warning)
- **Markup Percentage**: Average markup percentage applied
  - Alert threshold: Deviation from expected range (warning)

**Dependency Metrics:**
- **Data Service Latency**: Response time from Data Service in milliseconds
  - Alert threshold: >50ms p95 (warning), >100ms p95 (critical)
- **Data Service Errors**: Rate of errors from Data Service
  - Alert threshold: >1% (warning), >5% (critical)
- **Cache Hit Rate**: Percentage of cache hits for calculations
  - Alert threshold: <80% (warning), <60% (critical)

**Resource Metrics:**
- **CPU Usage**: Percentage of CPU limit used
  - Alert threshold: >70% (warning), >85% (critical)
- **Memory Usage**: Percentage of memory limit used
  - Alert threshold: >70% (warning), >85% (critical)
- **Pod Restarts**: Number of pod restarts
  - Alert threshold: >0 in 15 minutes (warning), >2 in 15 minutes (critical)

```
# Prometheus queries for key metrics

# Calculation rate
sum(rate(calculations_total{namespace="borrow-rate-engine", app="calculation-service"}[5m]))

# Calculation duration (p95)
histogram_quantile(0.95, sum(rate(calculation_duration_seconds_bucket{namespace="borrow-rate-engine", app="calculation-service"}[5m])) by (le, calculation_type))

# Calculation error rate
sum(rate(calculations_total{namespace="borrow-rate-engine", app="calculation-service", status="error"}[5m])) / sum(rate(calculations_total{namespace="borrow-rate-engine", app="calculation-service"}[5m]))

# Borrow rate calculation duration (p95)
histogram_quantile(0.95, sum(rate(calculation_duration_seconds_bucket{namespace="borrow-rate-engine", app="calculation-service", calculation_type="borrow_rate"}[5m])) by (le))

# Volatility adjustment impact
avg(volatility_adjustment_impact{namespace="borrow-rate-engine", app="calculation-service"})

# Fallback usage rate
sum(rate(fallback_usage_total{namespace="borrow-rate-engine", app="calculation-service"}[5m])) / sum(rate(calculations_total{namespace="borrow-rate-engine", app="calculation-service", calculation_type="borrow_rate"}[5m]))

# Fee calculation duration (p95)
histogram_quantile(0.95, sum(rate(calculation_duration_seconds_bucket{namespace="borrow-rate-engine", app="calculation-service", calculation_type="locate_fee"}[5m])) by (le))

# Average fee amount
avg(fee_amount_total{namespace="borrow-rate-engine", app="calculation-service"}) / count(fee_amount_total{namespace="borrow-rate-engine", app="calculation-service"})

# Data service latency (p95)
histogram_quantile(0.95, sum(rate(dependency_request_duration_seconds_bucket{namespace="borrow-rate-engine", app="calculation-service", dependency="data-service"}[5m])) by (le))

# Data service error rate
sum(rate(dependency_requests_total{namespace="borrow-rate-engine", app="calculation-service", dependency="data-service", status="error"}[5m])) / sum(rate(dependency_requests_total{namespace="borrow-rate-engine", app="calculation-service", dependency="data-service"}[5m]))

# Cache hit rate
sum(rate(cache_hits_total{namespace="borrow-rate-engine", app="calculation-service"}[5m])) / sum(rate(cache_requests_total{namespace="borrow-rate-engine", app="calculation-service"}[5m]))

# CPU usage
sum(rate(container_cpu_usage_seconds_total{namespace="borrow-rate-engine", pod=~"calculation-service-.*"}[5m])) / sum(kube_pod_container_resource_limits_cpu_cores{namespace="borrow-rate-engine", pod=~"calculation-service-.*"})

# Memory usage
sum(container_memory_usage_bytes{namespace="borrow-rate-engine", pod=~"calculation-service-.*"}) / sum(kube_pod_container_resource_limits_memory_bytes{namespace="borrow-rate-engine", pod=~"calculation-service-.*"})
```

### Monitoring Dashboards

The following Grafana dashboards are available for monitoring the Calculation Service:

1. **Calculation Service Overview Dashboard**
   - URL: https://grafana.example.com/d/calculation-service-overview
   - Purpose: High-level overview of Calculation Service health and performance
   - Key panels: Calculation rate, error rate, latency, dependency status

2. **Calculation Service Detailed Dashboard**
   - URL: https://grafana.example.com/d/calculation-service-detailed
   - Purpose: Detailed metrics for in-depth analysis
   - Key panels: Calculation-specific metrics, formula performance, dependency latency

3. **Financial Calculations Dashboard**
   - URL: https://grafana.example.com/d/financial-calculations
   - Purpose: Business metrics related to financial calculations
   - Key panels: Average rates, fee distributions, adjustment impacts

4. **Calculation Service Resource Dashboard**
   - URL: https://grafana.example.com/d/calculation-service-resources
   - Purpose: Resource utilization and scaling metrics
   - Key panels: CPU/memory usage, pod status, scaling events

5. **Calculation Service Logs Dashboard**
   - URL: https://grafana.example.com/d/calculation-service-logs
   - Purpose: Log visualization and analysis
   - Key panels: Error logs, calculation failures, dependency issues

These dashboards can be filtered by time range, environment, and specific instances to narrow down the analysis.

```
# Dashboard URLs with useful parameters

# Last hour with 5s refresh
https://grafana.example.com/d/calculation-service-overview?from=now-1h&to=now&refresh=5s

# Filter to specific calculation type
https://grafana.example.com/d/calculation-service-detailed?var-calculation_type=locate_fee

# Filter to specific ticker
https://grafana.example.com/d/financial-calculations?var-ticker=AAPL

# Filter to specific pod
https://grafana.example.com/d/calculation-service-resources?var-pod=calculation-service-abc123

# Filter to error logs only
https://grafana.example.com/d/calculation-service-logs?var-level=ERROR
```

### Log Analysis

The Calculation Service generates structured logs that can be analyzed using Loki. Key log patterns to monitor include:

1. **Calculation Errors**
   - Pattern: `level=ERROR msg="Calculation error"`
   - Importance: Critical for identifying formula or input issues
   - Action: Investigate immediately for potential financial impact

2. **Dependency Failures**
   - Pattern: `level=ERROR msg="Dependency failure"`
   - Importance: High for identifying integration issues
   - Action: Check dependent service status and connectivity

3. **Fallback Mechanism Usage**
   - Pattern: `level=WARNING msg="Using fallback mechanism"`
   - Importance: Medium for monitoring dependency health
   - Action: Investigate dependency issues if pattern persists

4. **Performance Warnings**
   - Pattern: `level=WARNING msg="Slow calculation"`
   - Importance: Medium for identifying performance degradation
   - Action: Investigate calculation bottlenecks

5. **Formula Parameter Issues**
   - Pattern: `level=WARNING msg="Unusual parameter value"`
   - Importance: Medium for identifying potential data quality issues
   - Action: Verify data inputs and validation

Use the following LogQL queries to analyze logs:

```
# LogQL queries for Calculation Service logs

# All errors
{namespace="borrow-rate-engine", app="calculation-service"} |= "level=ERROR"

# Calculation errors
{namespace="borrow-rate-engine", app="calculation-service"} |= "Calculation error"

# Dependency failures
{namespace="borrow-rate-engine", app="calculation-service"} |= "Dependency failure"

# Fallback mechanism usage
{namespace="borrow-rate-engine", app="calculation-service"} |= "Using fallback mechanism"

# Performance warnings
{namespace="borrow-rate-engine", app="calculation-service"} |= "Slow calculation"

# Errors for specific ticker
{namespace="borrow-rate-engine", app="calculation-service"} |= "ticker=\"AAPL\"" |= "level=ERROR"

# Errors for specific calculation type
{namespace="borrow-rate-engine", app="calculation-service"} |= "calculation_type=\"locate_fee\"" |= "level=ERROR"
```

### Health Checks

The Calculation Service provides health check endpoints that can be used to verify its status:

1. **Basic Health Check**
   - Endpoint: `/health`
   - Method: GET
   - Expected Response: `{"status":"healthy","version":"1.0.0"}`
   - Purpose: Quick verification of Calculation Service availability

2. **Detailed Health Check**
   - Endpoint: `/health/detailed`
   - Method: GET
   - Expected Response: `{"status":"healthy","version":"1.0.0","dependencies":{...}}`
   - Purpose: Comprehensive health check including dependencies

3. **Kubernetes Probes**
   - Liveness Probe: `/health`
   - Readiness Probe: `/health`
   - Startup Probe: `/health`
   - Purpose: Used by Kubernetes to manage pod lifecycle

These health checks are used by monitoring systems and load balancers to determine if the Calculation Service is functioning correctly.

```
# Check basic health
curl -v http://calculation-service:8000/health

# Check detailed health
curl -v http://calculation-service:8000/health/detailed

# Check health directly on pod
kubectl exec -n borrow-rate-engine deploy/calculation-service -- curl -s http://localhost:8000/health

# Check Kubernetes probe status
kubectl describe pod -n borrow-rate-engine calculation-service-abc123 | grep -A 10 "Liveness"
```

## Common Issues

This section covers common issues that may occur with the Calculation Service and provides troubleshooting steps for each issue.

### Calculation Errors

Calculation errors occur when the Calculation Service encounters issues during the execution of financial formulas.

**Symptoms:**
- Error logs mentioning "Calculation error"
- Increased error rate in calculation metrics
- Client reports of incorrect calculation results
- Failed calculations in audit logs

**Possible Causes:**
1. **Invalid Input Data**
   - Missing required parameters
   - Invalid parameter types
   - Out-of-range parameter values
   - Unexpected data formats

2. **Formula Implementation Issues**
   - Logic errors in calculation formulas
   - Precision or rounding issues
   - Edge case handling problems
   - Recent code changes affecting calculations

3. **Configuration Problems**
   - Incorrect default values
   - Missing configuration parameters
   - Incompatible configuration settings
   - Environment-specific configuration issues

4. **Dependency Data Issues**
   - Invalid data from Data Service
   - Missing broker configuration
   - Unexpected volatility or event risk data
   - Data format changes

**Troubleshooting Steps:**

1. **Analyze Error Patterns**
   - Review error logs for specific error messages
   - Identify affected calculation types
   - Check for patterns in input parameters
   - Determine if errors are isolated or widespread

2. **Verify Input Data**
   - Check input parameter values and types
   - Verify data from dependencies
   - Test with known good input values
   - Validate against expected ranges

3. **Review Formula Implementation**
   - Check formula code for logical errors
   - Verify precision and rounding handling
   - Test edge cases manually
   - Review recent code changes

4. **Check Configuration**
   - Verify service configuration
   - Check environment variables
   - Compare against known good configuration
   - Test with default configuration

**Resolution Steps:**

1. **For Invalid Input Data:**
   - Enhance input validation
   - Improve error messages
   - Add data normalization
   - Update client documentation

2. **For Formula Issues:**
   - Fix formula implementation
   - Improve precision handling
   - Add edge case handling
   - Roll back problematic code changes

3. **For Configuration Problems:**
   - Update configuration values
   - Add missing parameters
   - Fix environment-specific settings
   - Implement configuration validation

4. **For Dependency Data Issues:**
   - Work with Data Service team to fix data issues
   - Enhance data validation
   - Implement more robust parsing
   - Add fallback mechanisms

**Verification:**
- Test calculations with previously failing inputs
- Verify calculation results are correct
- Monitor error rate metrics
- Check audit logs for successful calculations

```
# Commands for investigating calculation errors

# Check calculation error logs
kubectl logs -n borrow-rate-engine -l app=calculation-service --tail=100 | grep "Calculation error"

# Check specific calculation with test input
kubectl exec -n borrow-rate-engine deploy/calculation-service -- curl -s -X POST -H "Content-Type: application/json" -d '{"ticker":"AAPL","position_value":100000,"loan_days":30,"client_id":"test123"}' http://localhost:8000/internal/calculate

# Check borrow rate calculation for specific ticker
kubectl exec -n borrow-rate-engine deploy/calculation-service -- curl -s http://localhost:8000/internal/borrow-rate/AAPL

# Check configuration values
kubectl get configmap -n borrow-rate-engine calculation-service-config -o yaml

# Verify data from Data Service
kubectl exec -n borrow-rate-engine deploy/calculation-service -- curl -s http://data-service:80/internal/stocks/AAPL
kubectl exec -n borrow-rate-engine deploy/calculation-service -- curl -s http://data-service:80/internal/brokers/test123

# Test calculation with default values
kubectl exec -n borrow-rate-engine deploy/calculation-service -- python -c "from services.calculation.formulas import calculate_borrow_cost; from decimal import Decimal; print(calculate_borrow_cost(Decimal('100000'), Decimal('0.05'), 30))"

# Restart service if needed
kubectl rollout restart deployment/calculation-service -n borrow-rate-engine
```

### Dependency Failures

Dependency failures occur when the Calculation Service cannot properly communicate with dependent services like the Data Service or Cache Service.

**Symptoms:**
- Error logs mentioning "Dependency failure"
- Increased fallback mechanism usage
- Degraded calculation performance
- Increased error rates

**Possible Causes:**
1. **Service Availability**
   - Dependent service is down
   - Pod failures
   - Deployment issues

2. **Network Connectivity**
   - DNS resolution problems
   - Network policy restrictions
   - Service discovery issues

3. **Timeout Configuration**
   - Insufficient timeout settings
   - Long-running operations in dependencies
   - Network latency

4. **Authentication/Authorization**
   - Invalid credentials
   - Expired tokens
   - Permission issues

**Troubleshooting Steps:**

1. **Check Dependency Status**
   - Verify dependent service pods are running
   - Check dependent service health endpoints
   - Review dependent service logs

2. **Test Direct Connectivity**
   - Test network connectivity from Calculation Service to dependencies
   - Verify DNS resolution
   - Check network policies

3. **Review Timeout Settings**
   - Check request timeout configuration
   - Verify retry settings
   - Identify long-running operations

4. **Examine Authentication**
   - Check authentication configuration
   - Verify credentials
   - Test authentication directly

**Resolution Steps:**

1. **For Service Availability:**
   - Restore dependent services
   - Fix deployment issues
   - Ensure proper health checks

2. **For Network Connectivity:**
   - Fix DNS resolution issues
   - Update network policies
   - Correct service discovery configuration

3. **For Timeout Issues:**
   - Adjust timeout settings
   - Implement circuit breakers
   - Optimize long-running operations

4. **For Authentication Issues:**
   - Update credentials
   - Fix authentication configuration
   - Implement proper token refresh

**Verification:**
- Test connectivity to dependencies
- Verify calculation operations that depend on external services
- Monitor fallback usage rate
- Check dependency error rate metrics

```
# Commands for investigating dependency failures

# Check dependency error logs
kubectl logs -n borrow-rate-engine -l app=calculation-service --tail=100 | grep "Dependency failure"

# Check dependent service status
kubectl get pods -n borrow-rate-engine -l app=data-service
kubectl get pods -n borrow-rate-engine -l app=cache-service

# Test direct connectivity to dependencies
kubectl exec -n borrow-rate-engine deploy/calculation-service -- curl -v http://data-service:80/health
kubectl exec -n borrow-rate-engine deploy/calculation-service -- curl -v http://cache-service:80/health

# Check DNS resolution
kubectl exec -n borrow-rate-engine deploy/calculation-service -- nslookup data-service.borrow-rate-engine.svc.cluster.local

# Check network policies
kubectl get networkpolicies -n borrow-rate-engine

# Check timeout configuration
kubectl get configmap -n borrow-rate-engine calculation-service-config -o yaml | grep TIMEOUT

# Check dependent service logs
kubectl logs -n borrow-rate-engine -l app=data-service --tail=100

# Restart service if needed
kubectl rollout restart deployment/calculation-service -n borrow-rate-engine
```

### Performance Issues

Performance issues occur when the Calculation Service experiences high latency or resource constraints affecting calculation speed.

**Symptoms:**
- Increased calculation duration
- Slow response times
- High CPU or memory utilization
- Client reports of slow calculations

**Possible Causes:**
1. **Resource Constraints**
   - Insufficient CPU or memory allocation
   - Pod scheduling issues
   - Node resource contention

2. **Inefficient Calculations**
   - Suboptimal algorithm implementation
   - Excessive logging
   - Memory leaks
   - Blocking operations

3. **Dependency Performance**
   - Slow Data Service responses
   - Cache Service performance issues
   - Database latency

4. **High Traffic Volume**
   - Request spikes
   - Insufficient scaling
   - Uneven load distribution

**Troubleshooting Steps:**

1. **Analyze Resource Usage**
   - Check CPU and memory metrics
   - Review pod resource allocation
   - Examine node resource utilization

2. **Profile Calculation Performance**
   - Identify slow calculation types
   - Measure individual formula performance
   - Check for memory usage patterns
   - Look for excessive logging

3. **Examine Dependency Performance**
   - Measure Data Service response times
   - Check Cache Service performance
   - Verify database query performance

4. **Review Traffic Patterns**
   - Analyze calculation request volume
   - Check for request spikes
   - Verify load balancing

**Resolution Steps:**

1. **For Resource Constraints:**
   - Increase CPU/memory allocation
   - Adjust pod scheduling
   - Scale horizontally

2. **For Inefficient Calculations:**
   - Optimize algorithm implementation
   - Reduce logging verbosity
   - Fix memory leaks
   - Implement asynchronous processing

3. **For Dependency Performance:**
   - Work with dependent service teams
   - Implement caching
   - Add timeouts and circuit breakers

4. **For High Traffic:**
   - Implement auto-scaling
   - Add request throttling
   - Optimize load distribution

**Verification:**
- Monitor calculation duration metrics
- Check resource utilization after changes
- Test calculation performance
- Verify client experience improves

```
# Commands for investigating performance issues

# Check resource usage
kubectl top pods -n borrow-rate-engine -l app=calculation-service

# Check resource limits and requests
kubectl get pods -n borrow-rate-engine -l app=calculation-service -o jsonpath='{.items[0].spec.containers[0].resources}'

# Profile calculation duration
kubectl exec -n borrow-rate-engine deploy/calculation-service -- curl -s http://localhost:8000/internal/metrics | grep calculation_duration_seconds

# Check dependency latency
kubectl exec -n borrow-rate-engine deploy/calculation-service -- curl -s http://localhost:8000/internal/metrics | grep dependency_request_duration_seconds

# Analyze traffic patterns
kubectl exec -n borrow-rate-engine deploy/calculation-service -- curl -s http://localhost:8000/internal/metrics | grep calculations_total

# Check for memory leaks
kubectl exec -n borrow-rate-engine deploy/calculation-service -- curl -s http://localhost:8000/internal/metrics | grep process_resident_memory_bytes

# Increase resource limits if needed
kubectl patch deployment/calculation-service -n borrow-rate-engine -p '{"spec":{"template":{"spec":{"containers":[{"name":"calculation-service","resources":{"requests":{"cpu":"2000m","memory":"4Gi"},"limits":{"cpu":"4000m","memory":"8Gi"}}}]}}}}}'

# Scale horizontally
kubectl scale deployment/calculation-service -n borrow-rate-engine --replicas=5
```

### Caching Issues

Caching issues occur when the Calculation Service experiences problems with its caching layer, affecting performance and potentially calculation accuracy.

**Symptoms:**
- Decreased cache hit rate
- Increased calculation duration
- Error logs related to caching
- Inconsistent calculation results

**Possible Causes:**
1. **Cache Connectivity**
   - Redis service unavailable
   - Network connectivity issues
   - Authentication failures

2. **Cache Configuration**
   - Inappropriate TTL settings
   - Ineffective cache key design
   - Insufficient cache size

3. **Cache Invalidation Issues**
   - Stale cached data
   - Missing invalidation triggers
   - Race conditions

4. **Serialization Problems**
   - Data serialization errors
   - Incompatible data formats
   - Large cached objects

**Troubleshooting Steps:**

1. **Check Cache Connectivity**
   - Verify Redis service is running
   - Test connectivity from Calculation Service
   - Check authentication configuration

2. **Analyze Cache Metrics**
   - Review cache hit/miss rates
   - Check key expiration patterns
   - Monitor memory usage

3. **Examine Cache Configuration**
   - Verify TTL settings
   - Check cache key patterns
   - Review invalidation logic

4. **Test Serialization**
   - Verify data can be properly serialized
   - Check for serialization errors in logs
   - Test with different data types

**Resolution Steps:**

1. **For Cache Connectivity:**
   - Restore Redis service
   - Fix network connectivity
   - Update authentication configuration

2. **For Cache Configuration:**
   - Adjust TTL settings based on data volatility
   - Optimize cache key design
   - Implement multi-level caching

3. **For Invalidation Issues:**
   - Implement proper invalidation triggers
   - Add versioning to cache keys
   - Improve invalidation logic

4. **For Serialization Problems:**
   - Fix serialization code
   - Implement data compression
   - Limit object size

**Verification:**
- Monitor cache hit rate improvement
- Verify calculation performance
- Check for consistent results
- Confirm proper invalidation

```
# Commands for investigating caching issues

# Check cache-related logs
kubectl logs -n borrow-rate-engine -l app=calculation-service --tail=100 | grep -i "cache"

# Check Redis connectivity
kubectl exec -n borrow-rate-engine deploy/calculation-service -- redis-cli -h redis-master ping

# Check cache hit rate metrics
kubectl exec -n borrow-rate-engine deploy/calculation-service -- curl -s http://localhost:8000/internal/metrics | grep cache_hit

# Check cache configuration
kubectl get configmap -n borrow-rate-engine calculation-service-config -o yaml | grep CACHE

# Test cache operation directly
kubectl exec -n borrow-rate-engine deploy/calculation-service -- curl -s http://localhost:8000/internal/cache-test

# Flush cache if needed (use with caution)
kubectl exec -n borrow-rate-engine deploy/redis-master -- redis-cli flushdb

# Disable caching temporarily for troubleshooting
kubectl patch configmap -n borrow-rate-engine calculation-service-config --type=merge -p '{"data":{"ENABLE_CACHING":"false"}}'
kubectl rollout restart deployment/calculation-service -n borrow-rate-engine

# Re-enable caching after fixing issues
kubectl patch configmap -n borrow-rate-engine calculation-service-config --type=merge -p '{"data":{"ENABLE_CACHING":"true"}}'
kubectl rollout restart deployment/calculation-service -n borrow-rate-engine
```

### Audit Logging Failures

Audit logging failures occur when the Calculation Service cannot properly record calculation details for compliance and troubleshooting purposes.

**Symptoms:**
- Error logs mentioning audit logging failures
- Missing audit records
- Incomplete audit information
- Compliance reporting issues

**Possible Causes:**
1. **Audit Service Availability**
   - Audit Service is down
   - Message queue issues
   - Network connectivity problems

2. **Message Format Issues**
   - Invalid audit message format
   - Missing required fields
   - Serialization errors

3. **Configuration Problems**
   - Incorrect Audit Service URL
   - Authentication issues
   - Misconfigured audit logging

4. **Resource Constraints**
   - Message queue capacity exceeded
   - Disk space limitations
   - Network bandwidth constraints

**Troubleshooting Steps:**

1. **Check Audit Service Status**
   - Verify Audit Service is running
   - Check message queue status
   - Test connectivity to Audit Service

2. **Examine Audit Messages**
   - Review audit message format
   - Check for missing fields
   - Verify serialization

3. **Review Configuration**
   - Check Audit Service URL
   - Verify authentication settings
   - Review audit logging configuration

4. **Analyze Resource Usage**
   - Check message queue capacity
   - Verify disk space
   - Monitor network bandwidth

**Resolution Steps:**

1. **For Audit Service Issues:**
   - Restore Audit Service
   - Fix message queue problems
   - Resolve network connectivity issues

2. **For Message Format Issues:**
   - Fix audit message format
   - Add missing fields
   - Resolve serialization errors

3. **For Configuration Problems:**
   - Update Audit Service URL
   - Fix authentication settings
   - Correct audit logging configuration

4. **For Resource Constraints:**
   - Increase message queue capacity
   - Add disk space
   - Optimize network usage

**Verification:**
- Verify audit records are being created
- Check audit record completeness
- Confirm compliance reporting works
- Monitor audit logging errors

```
# Commands for investigating audit logging failures

# Check audit logging error logs
kubectl logs -n borrow-rate-engine -l app=calculation-service --tail=100 | grep -i "audit"

# Check Audit Service status
kubectl get pods -n borrow-rate-engine -l app=audit-service

# Test connectivity to Audit Service
kubectl exec -n borrow-rate-engine deploy/calculation-service -- curl -v http://audit-service:80/health

# Check audit configuration
kubectl get configmap -n borrow-rate-engine calculation-service-config -o yaml | grep AUDIT

# Check message queue status (if using RabbitMQ)
kubectl exec -n borrow-rate-engine deploy/rabbitmq -- rabbitmqctl list_queues

# Test audit logging directly
kubectl exec -n borrow-rate-engine deploy/calculation-service -- curl -s -X POST -H "Content-Type: application/json" -d '{"event":"test_audit","data":{"test":"data"}}' http://audit-service:80/internal/log

# Check Audit Service logs
kubectl logs -n borrow-rate-engine -l app=audit-service --tail=100

# Restart service if needed
kubectl rollout restart deployment/calculation-service -n borrow-rate-engine
```

## Maintenance Procedures

This section covers routine maintenance procedures for the Calculation Service.

### Deployment and Updates

The Calculation Service uses a rolling update strategy to minimize downtime during deployments. Follow these procedures when deploying updates:

**Pre-Deployment Checklist:**
1. Verify the new version has passed all CI/CD tests
2. Ensure all calculation tests are passing with expected results
3. Check that the staging environment deployment was successful
4. Ensure sufficient cluster resources are available
5. Schedule deployment during low-traffic periods if possible
6. Notify stakeholders of planned deployment

**Deployment Procedure:**
1. Update the Calculation Service image tag in the deployment configuration
2. Apply the updated configuration using kubectl or ArgoCD
3. Monitor the rolling update progress
4. Verify new pods are starting and passing health checks
5. Confirm old pods are terminated gracefully

**Post-Deployment Verification:**
1. Verify the deployment is complete and all pods are running
2. Check application logs for any errors or warnings
3. Test calculation endpoints with sample requests
4. Verify calculation results are correct
5. Monitor performance metrics for any degradation

**Rollback Procedure:**
1. If issues are detected, initiate a rollback to the previous version
2. Monitor the rollback progress
3. Verify the previous version is restored and functioning
4. Investigate the issues with the new version

The Calculation Service is configured with a RollingUpdate strategy with maxSurge=1 and maxUnavailable=0, ensuring zero downtime during updates.