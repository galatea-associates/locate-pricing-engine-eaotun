## Introduction

This runbook provides comprehensive guidance for operating and maintaining the API Gateway service of the Borrow Rate & Locate Fee Pricing Engine. The API Gateway serves as the entry point for all client requests, handling authentication, rate limiting, request validation, and routing to appropriate backend services.

The API Gateway is a critical component of the system, as it controls access to all calculation functionality and ensures proper security, validation, and traffic management. This runbook covers monitoring, troubleshooting, and maintenance procedures to ensure the API Gateway operates reliably and securely.

### Purpose and Scope

This runbook is intended for operations engineers, SREs, and on-call personnel responsible for maintaining the Borrow Rate & Locate Fee Pricing Engine. It provides:

- Detailed information about the API Gateway architecture and components
- Monitoring procedures and key metrics to watch
- Troubleshooting steps for common issues
- Maintenance procedures for routine operations
- Recovery procedures for incident response

This document should be used in conjunction with the general troubleshooting guide and incident response procedures.

### Service Overview

The API Gateway is implemented as a FastAPI application running in Kubernetes. It provides the following key functions:

1. **Authentication**: Validates API keys and enforces access controls
2. **Rate Limiting**: Prevents abuse by limiting request rates per client
3. **Request Validation**: Ensures all requests contain valid parameters
4. **Request Routing**: Directs requests to appropriate backend services
5. **Response Formatting**: Standardizes API responses
6. **Error Handling**: Provides consistent error responses
7. **Logging and Monitoring**: Records all API activity for audit and troubleshooting

The API Gateway exposes the following primary endpoints:

- `/health`: System health check
- `/api/v1/calculate-locate`: Calculate locate fees
- `/api/v1/rates/{ticker}`: Get current borrow rates
- `/metrics`: Prometheus metrics endpoint

The service is designed to be horizontally scalable and highly available, with a minimum of 3 replicas deployed across multiple availability zones.

### Architecture

The API Gateway is deployed as a Kubernetes service with the following components:

**Deployment Configuration:**
- Image: `${ECR_REPO}/borrow-rate-engine-api:${VERSION}`
- Replicas: 3 (minimum)
- CPU Request: 500m, Limit: 2000m
- Memory Request: 1Gi, Limit: 4Gi
- Health Probes: Liveness, Readiness, and Startup probes on `/health`
- Update Strategy: RollingUpdate with maxSurge=1, maxUnavailable=0

**Service Configuration:**
- Type: ClusterIP
- Port: 80 (forwards to container port 8000)

**Dependencies:**
- Calculation Service: For fee calculations
- Data Service: For rate information
- Database: For authentication and configuration
- Redis: For rate limiting and caching

**Key Configuration Parameters:**
- `ENVIRONMENT`: Environment name (dev/staging/prod)
- `LOG_LEVEL`: Logging verbosity (INFO/DEBUG/WARNING/ERROR)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `JWT_SECRET_KEY`: Secret for JWT token generation
- `RATE_LIMIT_PER_MINUTE`: Default rate limit per client
- `CALCULATION_SERVICE_URL`: URL for Calculation Service
- `DATA_SERVICE_URL`: URL for Data Service
- `ENABLE_AUTHENTICATION`: Flag to enable/disable authentication
- `ENABLE_RATE_LIMITING`: Flag to enable/disable rate limiting
- `CORS_ORIGINS`: Allowed origins for CORS

### Monitoring

Effective monitoring of the API Gateway is essential for detecting issues early and ensuring optimal performance. This section covers key metrics to monitor and how to use the monitoring dashboards.

#### Key Metrics

The following metrics should be monitored for the API Gateway:

**Request Metrics:**
- **Request Rate**: Number of requests per second
  - Alert threshold: >800 requests/second (warning), >1000 requests/second (critical)
- **Response Time**: Time taken to process requests in milliseconds
  - Alert threshold: >100ms p95 (warning), >250ms p95 (critical)
- **Error Rate**: Percentage of requests resulting in errors (4xx/5xx)
  - Alert threshold: >1% (warning), >5% (critical)

**Authentication Metrics:**
- **Authentication Success Rate**: Percentage of successful authentications
  - Alert threshold: <99% (warning), <95% (critical)
- **Invalid API Key Rate**: Rate of invalid API key attempts
  - Alert threshold: >1% of total requests (warning), >5% (critical)
- **JWT Token Generation Rate**: Rate of new JWT tokens issued
  - Alert threshold: Sudden increase >50% (warning)

**Rate Limiting Metrics:**
- **Rate Limit Exceeded**: Number of requests exceeding rate limits
  - Alert threshold: >1% of total requests (warning), >5% (critical)
- **Rate Limit Utilization**: Percentage of rate limit used per client
  - Alert threshold: >80% consistently (warning)

**Backend Service Metrics:**
- **Backend Service Latency**: Response time from backend services
  - Alert threshold: >200ms p95 (warning), >500ms p95 (critical)
- **Backend Service Errors**: Rate of errors from backend services
  - Alert threshold: >1% (warning), >5% (critical)

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
sum(rate(http_requests_total{namespace="borrow-rate-engine", app="api-gateway"}[5m]))

# Response time (p95)
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{namespace="borrow-rate-engine", app="api-gateway"}[5m])) by (le))

# Error rate
sum(rate(http_requests_total{namespace="borrow-rate-engine", app="api-gateway", status_code=~"[45].*"}[5m])) / sum(rate(http_requests_total{namespace="borrow-rate-engine", app="api-gateway"}[5m]))

# Authentication success rate
sum(rate(authentication_attempts_total{namespace="borrow-rate-engine", app="api-gateway", status="success"}[5m])) / sum(rate(authentication_attempts_total{namespace="borrow-rate-engine", app="api-gateway"}[5m]))

# Invalid API key rate
sum(rate(authentication_attempts_total{namespace="borrow-rate-engine", app="api-gateway", status="invalid_key"}[5m])) / sum(rate(http_requests_total{namespace="borrow-rate-engine", app="api-gateway"}[5m]))

# Rate limit exceeded
sum(rate(rate_limit_exceeded_total{namespace="borrow-rate-engine", app="api-gateway"}[5m])) / sum(rate(http_requests_total{namespace="borrow-rate-engine", app="api-gateway"}[5m]))

# Backend service latency (p95)
histogram_quantile(0.95, sum(rate(backend_request_duration_seconds_bucket{namespace="borrow-rate-engine", app="api-gateway"}[5m])) by (le, service))

# Backend service errors
sum(rate(backend_requests_total{namespace="borrow-rate-engine", app="api-gateway", status="error"}[5m])) / sum(rate(backend_requests_total{namespace="borrow-rate-engine", app="api-gateway"}[5m]))

# CPU usage
sum(rate(container_cpu_usage_seconds_total{namespace="borrow-rate-engine", pod=~"api-gateway-.*"}[5m])) / sum(kube_pod_container_resource_limits_cpu_cores{namespace="borrow-rate-engine", pod=~"api-gateway-.*"})

# Memory usage
sum(container_memory_usage_bytes{namespace="borrow-rate-engine", pod=~"api-gateway-.*"}) / sum(kube_pod_container_resource_limits_memory_bytes{namespace="borrow-rate-engine", pod=~"api-gateway-.*"})
```

#### Monitoring Dashboards

The following Grafana dashboards are available for monitoring the API Gateway:

1. **API Gateway Overview Dashboard**
   - URL: https://grafana.example.com/d/api-gateway-overview
   - Purpose: High-level overview of API Gateway health and performance
   - Key panels: Request rate, error rate, latency, authentication status

2. **API Gateway Detailed Dashboard**
   - URL: https://grafana.example.com/d/api-gateway-detailed
   - Purpose: Detailed metrics for in-depth analysis
   - Key panels: Endpoint-specific metrics, rate limiting, backend service performance

3. **API Gateway Resource Dashboard**
   - URL: https://grafana.example.com/d/api-gateway-resources
   - Purpose: Resource utilization and scaling metrics
   - Key panels: CPU/memory usage, pod status, scaling events

4. **API Gateway Logs Dashboard**
   - URL: https://grafana.example.com/d/api-gateway-logs
   - Purpose: Log visualization and analysis
   - Key panels: Error logs, authentication failures, rate limit events

These dashboards can be filtered by time range, environment, and specific instances to narrow down the analysis.

```
# Dashboard URLs with useful parameters

# Last hour with 5s refresh
https://grafana.example.com/d/api-gateway-overview?from=now-1h&to=now&refresh=5s

# Filter to specific endpoint
https://grafana.example.com/d/api-gateway-detailed?var-endpoint=calculate-locate

# Filter to specific pod
https://grafana.example.com/d/api-gateway-resources?var-pod=api-gateway-abc123

# Filter to error logs only
https://grafana.example.com/d/api-gateway-logs?var-level=ERROR
```

#### Log Analysis

The API Gateway generates structured logs that can be analyzed using Loki. Key log patterns to monitor include:

1. **Authentication Errors**
   - Pattern: `level=ERROR msg="Authentication error"`
   - Importance: Critical for identifying API key issues
   - Action: Investigate immediately for potential security issues

2. **Rate Limiting Events**
   - Pattern: `level=WARNING msg="Rate limit exceeded"`
   - Importance: Medium for identifying potential abuse or misconfiguration
   - Action: Check client usage patterns and adjust limits if needed

3. **Backend Service Errors**
   - Pattern: `level=ERROR msg="Backend service error"`
   - Importance: High for identifying dependency issues
   - Action: Check backend service status and connectivity

4. **Request Validation Errors**
   - Pattern: `level=WARNING msg="Validation error"`
   - Importance: Medium for identifying client integration issues
   - Action: Review common validation failures and improve documentation

5. **Slow Requests**
   - Pattern: `level=WARNING msg="Slow request"`
   - Importance: Medium for identifying performance issues
   - Action: Investigate backend service performance or API Gateway bottlenecks

Use the following LogQL queries to analyze logs:

```
# LogQL queries for API Gateway logs

# All errors
{namespace="borrow-rate-engine", app="api-gateway"} |= "level=ERROR"

# Authentication errors
{namespace="borrow-rate-engine", app="api-gateway"} |= "Authentication error"

# Rate limiting events
{namespace="borrow-rate-engine", app="api-gateway"} |= "Rate limit exceeded"

# Backend service errors
{namespace="borrow-rate-engine", app="api-gateway"} |= "Backend service error"

# Validation errors
{namespace="borrow-rate-engine", app="api-gateway"} |= "Validation error"

# Slow requests
{namespace="borrow-rate-engine", app="api-gateway"} |= "Slow request"

# Errors for specific endpoint
{namespace="borrow-rate-engine", app="api-gateway"} |= "endpoint=\"/api/v1/calculate-locate\"" |= "level=ERROR"

# Errors for specific client
{namespace="borrow-rate-engine", app="api-gateway"} |= "client_id=\"client123\"" |= "level=ERROR"
```

#### Health Checks

The API Gateway provides health check endpoints that can be used to verify its status:

1. **Basic Health Check**
   - Endpoint: `/health`
   - Method: GET
   - Expected Response: `{"status":"healthy","version":"1.0.0"}`
   - Purpose: Quick verification of API Gateway availability

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

These health checks are used by monitoring systems and load balancers to determine if the API Gateway is functioning correctly.

```
# Check basic health
curl -v http://api-gateway:8000/health

# Check detailed health
curl -v http://api-gateway:8000/health/detailed

# Check health directly on pod
kubectl exec -n borrow-rate-engine deploy/api-gateway -- curl -s http://localhost:8000/health

# Check Kubernetes probe status
kubectl describe pod -n borrow-rate-engine api-gateway-abc123 | grep -A 10 "Liveness"
```

### Common Issues

This section covers common issues that may occur with the API Gateway and provides troubleshooting steps for each issue.

#### Authentication Failures

Authentication failures occur when clients cannot successfully authenticate with the API Gateway.

**Symptoms:**
- 401 Unauthorized responses
- Error logs mentioning "Authentication error"
- Increased authentication failure rate in monitoring
- Client reports of API access issues

**Possible Causes:**
1. **Invalid API Keys**
   - Expired API keys
   - Incorrectly formatted keys
   - Revoked keys

2. **Authentication Service Issues**
   - Database connectivity problems
   - Authentication service errors
   - Configuration issues

3. **JWT Token Issues**
   - Expired tokens
   - Invalid token signatures
   - Token validation errors

4. **Client Integration Problems**
   - Missing API key header
   - Incorrect authentication method
   - Misconfigured client

**Troubleshooting Steps:**

1. **Check Authentication Logs**
   - Review logs for specific authentication error messages
   - Identify patterns in failures (specific clients, times, etc.)
   - Check for recent changes to authentication configuration

2. **Verify API Key Status**
   - Check if the API key exists in the database
   - Verify the key's expiration date
   - Confirm the key's status (active/inactive)

3. **Test Authentication Directly**
   - Test authentication with a known good API key
   - Verify the authentication endpoint is working
   - Check the authentication service's health

4. **Check Database Connectivity**
   - Verify the API Gateway can connect to the database
   - Check database service health
   - Review database connection pool metrics

**Resolution Steps:**

1. **For Invalid API Keys:**
   - Generate new API keys for affected clients
   - Update key expiration dates if needed
   - Provide correct integration instructions to clients

2. **For Authentication Service Issues:**
   - Restore database connectivity
   - Restart authentication service if needed
   - Fix configuration issues

3. **For JWT Token Issues:**
   - Update JWT secret if compromised
   - Adjust token expiration settings if needed
   - Fix token validation logic

4. **For Client Integration Problems:**
   - Provide clear documentation on authentication requirements
   - Assist clients with integration troubleshooting
   - Consider implementing client libraries

**Verification:**
- Test authentication with affected clients
- Monitor authentication success rate
- Verify error logs no longer show authentication issues

```
# Commands for authentication troubleshooting

# Check authentication error logs
kubectl logs -n borrow-rate-engine -l app=api-gateway --tail=100 | grep "Authentication error"

# Check API key in database
kubectl exec -n borrow-rate-engine deploy/api-gateway -- python -c "from db.crud.api_keys import get_api_key; from db.session import SessionLocal; db = SessionLocal(); print(get_api_key(db, 'API_KEY_HERE'))"

# Test authentication with curl
curl -v -H "X-API-Key: API_KEY_HERE" https://api.example.com/api/v1/rates/AAPL

# Check database connectivity
kubectl exec -n borrow-rate-engine deploy/api-gateway -- python -c "import psycopg2; conn = psycopg2.connect('$DATABASE_URL'); print('Connection successful'); conn.close()"

# Check JWT configuration
kubectl get configmap -n borrow-rate-engine api-gateway-config -o yaml | grep JWT

# Generate new API key for testing
kubectl exec -n borrow-rate-engine deploy/api-gateway -- python -c "from scripts.generate_api_key import generate_key; print(generate_key('test_client', 60))"

# Restart API Gateway if needed
kubectl rollout restart deployment/api-gateway -n borrow-rate-engine
```

#### Rate Limiting Issues

Rate limiting issues occur when clients experience unexpected throttling or when rate limits are not properly enforced.

**Symptoms:**
- 429 Too Many Requests responses
- Error logs mentioning "Rate limit exceeded"
- Client complaints about throttling
- Inconsistent rate limit enforcement

**Possible Causes:**
1. **Redis Connectivity**
   - Redis service unavailable
   - Connection issues
   - Authentication failures

2. **Rate Limit Configuration**
   - Incorrectly configured limits
   - Missing client-specific limits
   - Inconsistent limit application

3. **Client Behavior**
   - Excessive request volume
   - Improper request batching
   - Distributed clients sharing same key

4. **Implementation Issues**
   - Rate limiting algorithm bugs
   - Incorrect counter resets
   - Time window calculation errors

**Troubleshooting Steps:**

1. **Verify Redis Connectivity**
   - Check Redis service health
   - Test connectivity from API Gateway
   - Verify Redis configuration

2. **Check Rate Limit Configuration**
   - Review global and client-specific rate limits
   - Verify rate limit settings in ConfigMap
   - Check for recent configuration changes

3. **Analyze Client Request Patterns**
   - Review request volume by client
   - Check request distribution over time
   - Identify potential abuse patterns

4. **Examine Rate Limiting Implementation**
   - Review rate limiting algorithm
   - Check counter reset logic
   - Verify time window calculations

**Resolution Steps:**

1. **For Redis Issues:**
   - Restore Redis service
   - Fix connectivity problems
   - Update Redis configuration

2. **For Configuration Issues:**
   - Adjust rate limits as needed
   - Update client-specific configurations
   - Ensure consistent configuration across instances

3. **For Client Behavior:**
   - Provide guidance on request batching
   - Adjust limits for high-volume clients
   - Implement client-specific throttling

4. **For Implementation Issues:**
   - Fix rate limiting algorithm bugs
   - Correct counter reset logic
   - Update time window calculations

**Verification:**
- Test rate limiting with controlled request volume
- Monitor rate limit metrics
- Verify appropriate throttling for excessive requests

```
# Commands for rate limiting troubleshooting

# Check rate limiting logs
kubectl logs -n borrow-rate-engine -l app=api-gateway --tail=100 | grep "Rate limit exceeded"

# Check Redis connectivity
kubectl exec -n borrow-rate-engine deploy/api-gateway -- redis-cli -h redis-master ping

# Check rate limit configuration
kubectl get configmap -n borrow-rate-engine api-gateway-config -o yaml | grep RATE_LIMIT

# Check current rate limit usage for a client
kubectl exec -n borrow-rate-engine deploy/redis-master -- redis-cli get "ratelimit:client123"

# Test rate limiting with curl
for i in {1..100}; do curl -v -H "X-API-Key: API_KEY_HERE" https://api.example.com/api/v1/rates/AAPL; done

# Monitor rate limit metrics in real-time
kubectl exec -n borrow-rate-engine deploy/api-gateway -- curl -s http://localhost:8000/metrics | grep rate_limit

# Update rate limit configuration if needed
kubectl patch configmap -n borrow-rate-engine api-gateway-config --type=merge -p '{"data":{"RATE_LIMIT_PER_MINUTE":"120"}}'
kubectl rollout restart deployment/api-gateway -n borrow-rate-engine
```

#### Backend Service Connectivity

Backend service connectivity issues occur when the API Gateway cannot properly communicate with dependent services like the Calculation Service or Data Service.

**Symptoms:**
- 502 Bad Gateway or 504 Gateway Timeout responses
- Error logs mentioning "Backend service error"
- Increased backend error rate in monitoring
- Slow response times

**Possible Causes:**
1. **Service Availability**
   - Backend service is down
   - Pod failures
   - Deployment issues

2. **Network Connectivity**
   - DNS resolution problems
   - Network policy restrictions
   - Service discovery issues

3. **Timeout Configuration**
   - Insufficient timeout settings
   - Mismatched timeouts between services
   - Long-running backend operations

4. **Load and Capacity**
   - Backend service overloaded
   - Resource constraints
   - Insufficient scaling

**Troubleshooting Steps:**

1. **Check Backend Service Status**
   - Verify backend service pods are running
   - Check backend service health endpoints
   - Review backend service logs

2. **Test Direct Connectivity**
   - Test network connectivity from API Gateway to backend
   - Verify DNS resolution
   - Check network policies

3. **Review Timeout Settings**
   - Check API Gateway timeout configuration
   - Verify backend service timeout settings
   - Identify long-running operations

4. **Analyze Load Patterns**
   - Check backend service resource utilization
   - Review request volume and patterns
   - Verify scaling configuration

**Resolution Steps:**

1. **For Service Availability:**
   - Restart backend service if needed
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

4. **For Load Issues:**
   - Scale backend services
   - Implement request throttling
   - Optimize resource allocation

**Verification:**
- Test API endpoints that depend on backend services
- Monitor backend service error rate
- Verify response times are within acceptable limits

```
# Commands for backend service connectivity troubleshooting

# Check backend service error logs
kubectl logs -n borrow-rate-engine -l app=api-gateway --tail=100 | grep "Backend service error"

# Check backend service status
kubectl get pods -n borrow-rate-engine -l app=calculation-service
kubectl get pods -n borrow-rate-engine -l app=data-service

# Test direct connectivity to backend services
kubectl exec -n borrow-rate-engine deploy/api-gateway -- curl -v http://calculation-service:80/health
kubectl exec -n borrow-rate-engine deploy/api-gateway -- curl -v http://data-service:80/health

# Check DNS resolution
kubectl exec -n borrow-rate-engine deploy/api-gateway -- nslookup calculation-service.borrow-rate-engine.svc.cluster.local

# Check network policies
kubectl get networkpolicies -n borrow-rate-engine

# Check timeout configuration
kubectl get configmap -n borrow-rate-engine api-gateway-config -o yaml | grep TIMEOUT

# Check backend service logs
kubectl logs -n borrow-rate-engine -l app=calculation-service --tail=100

# Check backend service resource utilization
kubectl top pods -n borrow-rate-engine -l app=calculation-service

# Restart backend service if needed
kubectl rollout restart deployment/calculation-service -n borrow-rate-engine
```

#### Request Validation Errors

Request validation errors occur when client requests fail validation checks for required parameters, data types, or value ranges.

**Symptoms:**
- 400 Bad Request responses
- Error logs mentioning "Validation error"
- Client reports of API integration issues
- Specific endpoints with high error rates

**Possible Causes:**
1. **Client Integration Issues**
   - Missing required parameters
   - Incorrect parameter types
   - Invalid parameter values

2. **API Schema Changes**
   - Updated validation rules
   - New required parameters
   - Changed parameter formats

3. **Documentation Gaps**
   - Unclear parameter requirements
   - Missing validation rules in documentation
   - Outdated integration examples

4. **Validation Implementation**
   - Overly strict validation
   - Inconsistent validation across endpoints
   - Validation logic bugs

**Troubleshooting Steps:**

1. **Analyze Validation Errors**
   - Review logs for specific validation error messages
   - Identify patterns in failures (specific parameters, clients, etc.)
   - Check for recent API schema changes

2. **Review Client Requests**
   - Examine actual request payloads
   - Compare against API requirements
   - Identify common mistakes

3. **Check Validation Implementation**
   - Review validation rules in code
   - Verify consistency across endpoints
   - Test with valid and invalid inputs

4. **Assess Documentation**
   - Review API documentation for clarity
   - Check for missing validation rules
   - Verify example requests are correct

**Resolution Steps:**

1. **For Client Integration Issues:**
   - Provide clear error messages with correction guidance
   - Assist clients with integration troubleshooting
   - Consider client libraries or SDKs

2. **For API Schema Changes:**
   - Implement versioned APIs for breaking changes
   - Provide migration guides
   - Consider backward compatibility

3. **For Documentation Gaps:**
   - Update API documentation
   - Add clear validation rules
   - Provide more example requests

4. **For Validation Implementation:**
   - Fix validation logic bugs
   - Ensure consistent validation
   - Consider relaxing overly strict validation

**Verification:**
- Test API endpoints with valid and invalid requests
- Monitor validation error rate
- Verify clients can successfully integrate

```
# Commands for validation error troubleshooting

# Check validation error logs
kubectl logs -n borrow-rate-engine -l app=api-gateway --tail=100 | grep "Validation error"

# Test API endpoint with valid request
curl -v -H "X-API-Key: API_KEY_HERE" -H "Content-Type: application/json" -d '{"ticker":"AAPL","position_value":100000,"loan_days":30,"client_id":"test123"}' https://api.example.com/api/v1/calculate-locate

# Test API endpoint with invalid request (missing required parameter)
curl -v -H "X-API-Key: API_KEY_HERE" -H "Content-Type: application/json" -d '{"ticker":"AAPL","position_value":100000,"client_id":"test123"}' https://api.example.com/api/v1/calculate-locate

# Check validation implementation
kubectl exec -n borrow-rate-engine deploy/api-gateway -- cat /app/api/v1/endpoints/calculate.py | grep -A 20 "CalculateLocateRequest"

# Check API documentation
kubectl exec -n borrow-rate-engine deploy/api-gateway -- curl -s http://localhost:8000/docs
```

#### Performance Issues

Performance issues occur when the API Gateway experiences high latency, timeout errors, or resource constraints affecting response times.

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

2. **Backend Service Performance**
   - Slow backend service responses
   - Database performance issues
   - External API latency

3. **High Traffic Volume**
   - Request spikes
   - Insufficient scaling
   - Inefficient request handling

4. **Code Inefficiencies**
   - Unoptimized request processing
   - Memory leaks
   - Blocking operations

**Troubleshooting Steps:**

1. **Analyze Resource Usage**
   - Check CPU and memory metrics
   - Review pod resource allocation
   - Examine node resource utilization

2. **Profile Request Latency**
   - Identify slow endpoints
   - Measure backend service response times
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

2. **For Backend Service Performance:**
   - Optimize backend services
   - Implement caching
   - Set appropriate timeouts

3. **For High Traffic:**
   - Implement auto-scaling
   - Add rate limiting
   - Optimize request handling

4. **For Code Inefficiencies:**
   - Optimize algorithms
   - Implement asynchronous processing
   - Fix memory leaks

**Verification:**
- Monitor response times under load
- Check resource utilization after changes
- Verify client experience improves

```
# Commands for performance troubleshooting

# Check resource usage
kubectl top pods -n borrow-rate-engine -l app=api-gateway

# Check resource limits and requests
kubectl get pods -n borrow-rate-engine -l app=api-gateway -o jsonpath='{.items[0].spec.containers[0].resources}'

# Profile endpoint latency
kubectl exec -n borrow-rate-engine deploy/api-gateway -- curl -s http://localhost:8000/metrics | grep http_request_duration_seconds

# Check backend service latency
kubectl exec -n borrow-rate-engine deploy/api-gateway -- curl -s http://localhost:8000/metrics | grep backend_request_duration_seconds

# Analyze traffic patterns
kubectl exec -n borrow-rate-engine deploy/api-gateway -- curl -s http://localhost:8000/metrics | grep http_requests_total

# Check for memory leaks
kubectl exec -n borrow-rate-engine deploy/api-gateway -- curl -s http://localhost:8000/metrics | grep process_resident_memory_bytes

# Increase resource limits if needed
kubectl patch deployment/api-gateway -n borrow-rate-engine -p '{"spec":{"template":{"spec":{"containers":[{"name":"api-gateway","resources":{"requests":{"cpu":"1000m","memory":"2Gi"},"limits":{"cpu":"3000m","memory":"6Gi"}}}]}}}}}'

# Scale horizontally
kubectl scale deployment/api-gateway -n borrow-rate-engine --replicas=5
```

### Maintenance Procedures

This section covers routine maintenance procedures for the API Gateway.

#### Deployment and Updates

The API Gateway uses a rolling update strategy to minimize downtime during deployments. Follow these procedures when deploying updates:

**Pre-Deployment Checklist:**
1. Verify the new version has passed all CI/CD tests
2. Ensure all API integration tests are passing
3. Check that the staging environment deployment was successful
4. Ensure sufficient cluster resources are available
5. Schedule deployment during low-traffic periods if possible
6. Notify stakeholders of planned deployment

**Deployment Procedure:**
1. Update the API Gateway image tag in the deployment configuration
2. Apply the updated configuration using kubectl or ArgoCD
3. Monitor the rolling update progress
4. Verify new pods are starting and passing health checks
5. Confirm old pods are terminated gracefully

**Post-Deployment Verification:**
1. Verify the deployment is complete and all pods are running
2. Check application logs for any errors or warnings
3. Test API endpoints with sample requests
4. Verify authentication and rate limiting are working
5. Monitor performance metrics for any degradation

**Rollback Procedure:**
1. If issues are detected, initiate a rollback to the previous version
2. Monitor the rollback progress
3. Verify the previous version is restored and functioning
4. Investigate the issues with the new version

The API Gateway is configured with a RollingUpdate strategy with maxSurge=1 and maxUnavailable=0, ensuring zero downtime during updates.

```
# Commands for deployment and updates

# Check current deployment status
kubectl get deployment/api-gateway -n borrow-rate-engine

# Update image tag
kubectl set image deployment/api-gateway -n borrow-rate-engine api-gateway=${ECR_REPO}/borrow-rate-engine-api:${NEW_VERSION}

# Monitor rolling update progress
kubectl rollout status deployment/api-gateway -n borrow-rate-engine

# Check pods during update
kubectl get pods -n borrow-rate-engine -l app=api-gateway -w

# Verify logs of new pods
kubectl logs -n borrow-rate-engine -l app=api-gateway --tail=50

# Test API endpoints after deployment
curl -v -H "X-API-Key: API_KEY_HERE" https://api.example.com/api/v1/rates/AAPL

# Rollback if needed
kubectl rollout undo deployment/api-gateway -n borrow-rate-engine

# Verify rollback
kubectl rollout status deployment/api-gateway -n borrow-rate-engine
```

#### Scaling

The API Gateway is designed to scale horizontally to handle varying traffic loads. Follow these procedures for scaling:

**Manual Scaling:**
1. Assess the current load and performance metrics
2. Determine the appropriate number of replicas needed
3. Scale the deployment to the desired replica count
4. Monitor performance after scaling
5. Adjust resource limits if needed

**Automatic Scaling:**
The API Gateway is configured with a Horizontal Pod Autoscaler (HPA) with the following settings:
- Minimum replicas: 3
- Maximum replicas: 10
- CPU target utilization: 70%
- Custom metric target: 800 requests/second per pod

To modify the autoscaling configuration:
1. Update the HPA resource with new settings
2. Apply the updated configuration
3. Monitor scaling behavior under load

**Vertical Scaling:**
If the API Gateway requires more resources per pod:
1. Update CPU and memory requests/limits in the deployment
2. Apply the updated configuration
3. Monitor the rolling update as pods are recreated
4. Verify performance with new resource allocation

**Scaling Considerations:**
- Ensure sufficient cluster resources before scaling up
- Consider the impact on dependent services (Database, Redis)
- Monitor authentication and rate limiting behavior when scaling
- Verify load balancing across all instances

```
# Commands for scaling operations

# Manual horizontal scaling
kubectl scale deployment/api-gateway -n borrow-rate-engine --replicas=5

# Check current HPA configuration
kubectl get hpa -n borrow-rate-engine api-gateway-hpa

# Update HPA configuration
kubectl apply -f updated-hpa.yaml

# Monitor autoscaling behavior
kubectl get hpa -n borrow-rate-engine api-gateway-hpa -w

# Update resource limits (vertical scaling)
kubectl patch deployment/api-gateway -n borrow-rate-engine -p '{"spec":{"template":{"spec":{"containers":[{"name":"api-gateway","resources":{"requests":{"cpu":"1000m","memory":"2Gi"},"limits":{"cpu":"3000m","memory":"6Gi"}}}]}}}}}'