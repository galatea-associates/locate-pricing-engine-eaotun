# Borrow Rate & Locate Fee Pricing Engine: Operations Monitoring Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Monitoring Infrastructure Overview](#monitoring-infrastructure-overview)
3. [Accessing Monitoring Tools](#accessing-monitoring-tools)
4. [Using Dashboards](#using-dashboards)
5. [Common Monitoring Tasks](#common-monitoring-tasks)
6. [Alert Management](#alert-management)
7. [Troubleshooting with Monitoring Tools](#troubleshooting-with-monitoring-tools)
8. [Monitoring System Maintenance](#monitoring-system-maintenance)
9. [Best Practices](#best-practices)
10. [Reference](#reference)

## Introduction

This operations guide provides comprehensive instructions for monitoring the Borrow Rate & Locate Fee Pricing Engine. Effective monitoring is critical to ensure our financial system meets its SLA requirements of 99.95% availability and <100ms response time, while maintaining calculation accuracy.

### Purpose

This guide will help you:
- Understand the monitoring infrastructure and tools
- Interpret metrics and dashboard information
- Respond to alerts effectively
- Troubleshoot issues using monitoring data
- Maintain and extend the monitoring system

### Target Audience

This guide is intended for:
- Operations engineers responsible for system health
- On-call personnel responding to alerts
- Technical support staff troubleshooting client issues
- SRE team members maintaining monitoring infrastructure

### Critical Monitoring Focus Areas

For the Borrow Rate & Locate Fee Pricing Engine, focus monitoring on:

1. **Calculation Accuracy**: Ensure 100% accuracy of fee calculations
2. **API Performance**: Maintain <100ms response time (p95)
3. **External API Health**: Monitor SecLend API, Market Data API, and Event Calendar API
4. **Cache Efficiency**: Track cache hit rates (target >90%)
5. **Business Metrics**: Monitor average fees, client usage, and error rates

## Monitoring Infrastructure Overview

The Borrow Rate Engine uses a comprehensive monitoring stack based on industry-standard open-source tools. For detailed information on the architecture, refer to [Monitoring Architecture](../architecture/monitoring.md).

### Monitoring Stack Components

![Monitoring Infrastructure](../architecture/images/monitoring-stack.png)

| Component | Version | Purpose | URL |
|-----------|---------|---------|-----|
| Prometheus | 2.45.0+ | Time-series metrics collection and storage | http://prometheus.example.com |
| Grafana | 9.5.0+ | Visualization and dashboarding | http://grafana.example.com |
| Loki | 2.8.0+ | Log aggregation and querying | http://loki.example.com |
| Tempo | 2.1.0+ | Distributed tracing | http://tempo.example.com |
| Alertmanager | 0.25.0+ | Alert routing and notification | http://alertmanager.example.com |

### Data Flow

- **Metrics Flow**: Services expose metrics endpoints → Prometheus scrapes metrics → Grafana visualizes metrics
- **Logs Flow**: Services write logs → Fluent Bit collects logs → Loki indexes logs → Grafana displays logs
- **Traces Flow**: Services generate traces → OpenTelemetry collects traces → Tempo stores traces → Grafana shows traces
- **Alerts Flow**: Prometheus evaluates rules → Alertmanager groups and routes alerts → Notifications sent to appropriate channels

## Accessing Monitoring Tools

### Grafana

Grafana is the primary interface for viewing dashboards, logs, and traces.

- **URL**: http://grafana.example.com
- **Authentication**: Use your corporate SSO credentials
- **Default View**: Home dashboard with system overview

### Prometheus

Direct access to Prometheus is typically needed only for advanced query testing.

- **URL**: http://prometheus.example.com
- **Authentication**: Use your corporate SSO credentials
- **Key Features**: Graph interface, Alert rules, Status page

### Loki and Tempo

These are primarily accessed through Grafana, but direct access is available:

- **Loki URL**: http://loki.example.com
- **Tempo URL**: http://tempo.example.com

### Mobile Access

For on-call personnel:
- Install the Grafana mobile app
- Configure alerts in PagerDuty mobile app
- Set up Slack notifications for #alerts channels

## Using Dashboards

### Dashboard Navigation

Grafana organizes dashboards into folders:

1. **Executive**: High-level system health and business metrics
2. **Operational**: Real-time monitoring for operations
3. **Technical**: Detailed metrics for engineering
4. **Service-Specific**: Dedicated dashboards for each service
5. **Business**: Financial and client usage metrics

### Executive Dashboard

The Executive Dashboard provides a high-level overview suitable for management:

- **URL**: http://grafana.example.com/d/executive-dashboard
- **Key Panels**:
  - System Health Status: Overall health with component status
  - 7-Day Availability Trend: Availability percentage over time
  - Daily Calculation Volume: Number of calculations performed
  - Average Fee Amount: Average fee calculated by the system
  - SLA Compliance: Performance against defined SLAs

**When to use**: For status updates, management reporting, and general system health overview.

### Operational Dashboard

The Operational Dashboard is for day-to-day monitoring:

- **URL**: http://grafana.example.com/d/operational-dashboard
- **Key Panels**:
  - Requests per Second: Current traffic levels with trends
  - Response Time Distribution: Latency percentiles across endpoints
  - Error Rates by Endpoint: Error percentages by API endpoint
  - CPU/Memory by Service: Resource utilization across services
  - External API Status: Health of external dependencies

**When to use**: For daily operations, monitoring current performance, and identifying emerging issues.

### Technical Dashboard

The Technical Dashboard provides detailed metrics for troubleshooting:

- **URL**: http://grafana.example.com/d/technical-dashboard
- **Key Panels**:
  - Service Performance: Detailed latency and throughput metrics
  - Database Metrics: Query performance, connection pools, transactions
  - Cache Performance: Hit rates, memory usage, eviction rates
  - API Gateway Metrics: Request volumes, authentication rates

**When to use**: For technical troubleshooting, performance optimization, and root cause analysis.

### Service-Specific Dashboards

Each core service has a dedicated dashboard:

- [API Gateway Dashboard](http://grafana.example.com/d/api-gateway-dashboard)
- [Calculation Service Dashboard](http://grafana.example.com/d/calculation-service-dashboard)
- [Data Service Dashboard](http://grafana.example.com/d/data-service-dashboard)
- [Cache Service Dashboard](http://grafana.example.com/d/cache-service-dashboard)

**When to use**: When troubleshooting issues with a specific service or component.

### Business Metrics Dashboard

The Business Metrics Dashboard focuses on financial metrics:

- **URL**: http://grafana.example.com/d/business-metrics-dashboard
- **Key Panels**:
  - Average Borrow Rate by Ticker: Trends in borrow rates
  - Fee Distribution: Histogram of fee amounts
  - Client Usage Patterns: Request volumes by client
  - Fallback Usage: Tracking of fallback mechanism activation

**When to use**: For business analysis, client usage patterns, and revenue impact assessment.

## Common Monitoring Tasks

### Checking System Health

To verify overall system health:

1. Open the [Operational Dashboard](http://grafana.example.com/d/operational-dashboard)
2. Check the System Health Status panel for component status
3. Review Response Time and Error Rate panels for anomalies
4. Examine External API Status for dependency issues

Alternatively, you can use the `check_service_health` function:

```python
# Check health of a specific service
health_info = check_service_health("calculation-service")
print(f"Status: {health_info['status']}")
print(f"CPU Usage: {health_info['resource_usage']['cpu']}%")
print(f"Memory Usage: {health_info['resource_usage']['memory']}%")
```

### Investigating Performance Issues

When investigating performance issues:

1. Check the Response Time Distribution panel on the Operational Dashboard
2. Identify which services are experiencing higher latency
3. Look for correlation with increased traffic or resource utilization
4. Analyze database query performance and cache hit rates
5. Check external API latency for dependency bottlenecks

For detailed analysis:

```python
# Query response time metrics for the calculation service over the last hour
metrics = query_metrics(
    metric_name="http_request_duration_seconds",
    service_name="calculation-service", 
    time_range="1h"
)

# Analyze the 95th percentile response time
p95_latency = metrics.quantile(0.95)
print(f"95th percentile latency: {p95_latency * 1000}ms")
```

### Monitoring Error Rates

To track error rates across the system:

1. Check the Error Rates by Endpoint panel on the Operational Dashboard
2. Review the Error Rate by Service panel on the Technical Dashboard
3. Look for patterns in error types or affected clients
4. Correlate with recent deployments or configuration changes
5. Analyze logs for the affected services

For error log analysis:

```python
# Search for calculation errors in the last 30 minutes
error_logs = analyze_logs(
    service_name="calculation-service",
    search_pattern="error",
    time_range="30m"
)

# Group errors by type
error_types = {}
for log in error_logs:
    error_type = log.get("error_code", "UNKNOWN")
    error_types[error_type] = error_types.get(error_type, 0) + 1

print("Error distribution:")
for error_type, count in error_types.items():
    print(f"{error_type}: {count}")
```

### Tracking Business Metrics

To monitor business and financial metrics:

1. Open the [Business Metrics Dashboard](http://grafana.example.com/d/business-metrics-dashboard)
2. Review Average Borrow Rate trends for key securities
3. Analyze Fee Distribution to identify fee patterns
4. Monitor Client Usage Patterns for client activity
5. Check Fallback Usage to ensure external API reliability

For client activity analysis:

```python
# Get calculation volumes by client for the past day
metrics = query_metrics(
    metric_name="calculation_total",
    service_name="calculation-service",
    time_range="24h"
)

# Analyze by client_id label
client_volumes = metrics.group_by("client_id").sum()
print("Client calculation volumes:")
for client, volume in client_volumes.items():
    print(f"{client}: {volume} calculations")
```

### Examining Cache Performance

Cache efficiency is critical for system performance:

1. Check the Cache Hit/Miss Ratio panel on the Technical Dashboard
2. Review Cache Performance by Key Pattern for specific cache issues
3. Monitor Cache Eviction Rate for cache pressure
4. Analyze Cache Memory Usage for resource constraints

For cache analysis:

```python
# Get cache hit rates by key pattern
hit_rates = query_metrics(
    metric_name="cache_hit_ratio",
    service_name="cache-service",
    time_range="1h"
)

# Identify patterns with low hit rates
for pattern, rate in hit_rates.items():
    if rate < 0.9:  # Less than 90% hit rate
        print(f"Low cache hit rate for pattern {pattern}: {rate * 100:.1f}%")
```

## Alert Management

### Understanding Alert Severity

Alerts are classified by severity level:

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| P1 (Critical) | Service unavailable, severe business impact | 15 minutes | API Gateway down, >1% error rate, external API unavailable |
| P2 (High) | Degraded service, significant business impact | 30 minutes | Slow response times, high resource usage, cache issues |
| P3 (Medium) | Minor impact, potential future issue | 2 hours | Elevated errors, resource warnings, cache hit rate below threshold |
| P4 (Low) | Informational, non-urgent issue | Next business day | Unusual patterns, minor anomalies, warning-level events |

### Responding to Alerts

Follow this general process when responding to alerts:

1. **Acknowledge the alert** in PagerDuty or Slack
2. **Assess severity and impact** using dashboards
3. **Investigate root cause** using metrics, logs, and traces
4. **Implement mitigation** based on runbooks
5. **Document the incident** for post-mortem analysis
6. **Update status** for stakeholders

Example of handling an alert:

```python
# Handle a monitoring alert for high error rates
alert_info = handle_monitoring_alert(
    alert_name="HighErrorRate",
    severity="P2",
    affected_service="calculation-service"
)

# Access relevant metrics and logs
error_rate = alert_info["metrics"]["error_rate"]
related_logs = alert_info["logs"]
associated_traces = alert_info["traces"]

# Follow the recommended actions
print(f"Recommended actions:")
for step in alert_info["remediation_steps"]:
    print(f"- {step}")
```

### Alert Silencing and Maintenance

During planned maintenance or known issues:

1. In Alertmanager UI, select the alert(s) to silence
2. Click "Silence" and specify duration and reason
3. Add your contact information
4. For extended maintenance, update silences before expiry

### Modifying Alert Rules

Alert rules are defined in Prometheus configuration. To modify them:

1. Edit the appropriate rules file in the [Prometheus rules directory](../../infrastructure/monitoring/rules/)
2. Follow the change management process for configuration changes
3. Test the new rules in the Prometheus UI before applying
4. Monitor for false positives or missed alerts after changes

## Troubleshooting with Monitoring Tools

### Using Metrics for Troubleshooting

Prometheus metrics are powerful for identifying issues:

1. Start with the service-specific dashboard for the affected component
2. Look for correlations between metrics (e.g., high latency and high CPU)
3. Check for changes around the time the issue started
4. Compare with historical patterns to identify anomalies
5. Drill down into specific metrics for detailed analysis

Example troubleshooting workflow:

```python
# Troubleshoot high latency in the calculation service
troubleshooting_steps = troubleshoot_service(
    service_name="calculation-service",
    issue_type="high_latency"
)

# Follow the diagnostic steps
for step in troubleshooting_steps["steps"]:
    print(f"Step {step['step_number']}: {step['description']}")
    print(f"Command: {step['command']}")
    
    # Execute diagnostic commands as needed
    if step['step_number'] == 1:
        latency_metrics = query_metrics(
            metric_name=step['metric_name'],
            service_name="calculation-service",
            time_range=step['time_range']
        )
        print(f"Current p95 latency: {latency_metrics.quantile(0.95) * 1000}ms")
```

### Using Logs for Troubleshooting

Loki provides powerful log searching and analysis:

1. In Grafana, navigate to the Explore view
2. Select Loki as the data source
3. Enter a LogQL query to filter logs (examples below)
4. Look for error patterns, exceptions, or unusual behavior
5. Correlate log entries with metrics anomalies

Common LogQL queries:

```
# All logs from the calculation service
{namespace="borrow-rate-engine", service="calculation-service"}

# Error logs from any service
{namespace="borrow-rate-engine"} |= "ERROR"

# Logs related to a specific client
{namespace="borrow-rate-engine"} | json | client_id="xyz789"

# Logs for calculations with high fees
{namespace="borrow-rate-engine", service="calculation-service"} | json | total_fee > 5000
```

### Using Traces for Troubleshooting

Distributed tracing helps with complex, cross-service issues:

1. In Grafana, navigate to the Explore view
2. Select Tempo as the data source
3. Search for traces by:
   - Trace ID (from logs or metrics)
   - Service name and operation
   - Duration threshold (for slow requests)
4. Analyze the full request flow across services
5. Identify slow operations or error sources

Finding slow traces:

1. In Grafana, go to Explore
2. Select Tempo
3. Query: `duration > 100ms and service.name="calculation-service"`
4. Sort by duration to find the slowest requests

### Correlating Metrics, Logs, and Traces

For complex issues, correlate all three observability signals:

1. Identify the issue timeframe using metrics dashboards
2. Find relevant logs during that period
3. Use trace IDs from logs to examine request flows
4. Look for common patterns or root causes

Example correlation workflow:

1. Notice elevated error rates in metrics
2. Search logs for error messages during that period
3. Extract trace IDs from error logs
4. Analyze traces to find where errors originate
5. Check metrics for those specific components

### Common Troubleshooting Scenarios

#### Scenario 1: High API Response Time

1. Check the Operational Dashboard for response time metrics
2. Verify if the issue affects all endpoints or specific ones
3. Check resource utilization (CPU, memory) for API services
4. Examine database query performance and connection pool
5. Check external API latency if the endpoint uses them
6. Look for logs showing slow operations
7. Check traces for slow requests to pinpoint bottlenecks

#### Scenario 2: Increased Error Rate

1. Check the Technical Dashboard for error rate by service
2. Look at the Logs Dashboard for error patterns
3. Analyze which endpoints or operations are failing
4. Check external API status if those are involved
5. Look for recent deployments or configuration changes
6. Examine resource constraints or rate limiting issues
7. Review traces for failed requests to identify the failure point

#### Scenario 3: Cache Performance Issues

1. Check Cache Service Dashboard for hit/miss ratio
2. Look for changes in cache eviction rate
3. Verify memory usage and resource constraints
4. Check for increased load or data volume
5. Look for changes in access patterns
6. Review cache TTL settings appropriately
7. Examine Redis metrics for potential issues

## Monitoring System Maintenance

### Prometheus Maintenance

Prometheus requires periodic maintenance:

1. **Storage Management**:
   - Prometheus uses local storage with 30-day retention
   - Monitor disk usage on the Prometheus server
   - Consider compaction if storage efficiency decreases

2. **Configuration Updates**:
   - Changes to `prometheus-config.yaml` require a reload
   - Use `curl -X POST http://prometheus:9090/-/reload` to reload without restart
   - Validate configuration before applying with `promtool check config`

3. **Target Management**:
   - Review `/targets` in Prometheus UI periodically
   - Check for any targets showing as down
   - Verify scrape intervals are appropriate

### Grafana Maintenance

1. **Dashboard Organization**:
   - Keep dashboards organized in appropriate folders
   - Use tags for easier searching
   - Archive unused dashboards rather than deleting

2. **User Management**:
   - Review user access periodically
   - Use groups for permission management
   - Audit dashboard changes through version history

3. **Plugin Updates**:
   - Keep Grafana plugins updated
   - Test plugin updates in non-production environment first
   - Schedule updates during maintenance windows

### Alert Manager Maintenance

1. **Silences Review**:
   - Periodically review active silences
   - Remove expired or unnecessary silences
   - Document long-term silences with expiration dates

2. **Notification Channel Testing**:
   - Test PagerDuty, Slack, and email notifications quarterly
   - Verify on-call rotation is correctly configured
   - Ensure contact information is up to date

### Adding New Metrics

To add new metrics to the monitoring system:

1. Work with development to instrument the application code
2. Ensure metrics follow naming conventions
3. Update Prometheus configuration to capture new metrics
4. Create or update dashboards to visualize the metrics
5. Consider adding alerts for critical thresholds

### Creating Custom Dashboards

You can create custom dashboards for specific monitoring needs:

```python
# Create a custom dashboard for monitoring a specific client
dashboard_url = create_custom_dashboard(
    dashboard_name="Client XYZ Monitoring",
    metrics_to_display=[
        "calculation_total{client_id='xyz123'}",
        "calculation_fee_amount{client_id='xyz123'}",
        "http_request_duration_seconds{client_id='xyz123'}"
    ],
    dashboard_layout={
        "rows": 3,
        "cols": 2
    }
)

print(f"Dashboard created: {dashboard_url}")
```

Follow these best practices for custom dashboards:

1. Use clear, descriptive titles for the dashboard and panels
2. Include a dashboard description with purpose and audience
3. Organize panels in a logical flow (overview to detail)
4. Use consistent units and scales across related panels
5. Add template variables for flexible filtering
6. Include appropriate time ranges and refresh rates

## Best Practices

### Effective Monitoring

1. **Focus on the Critical Few**: Monitor what matters most - accuracy, availability, and performance
2. **Establish Baselines**: Understand normal patterns to identify anomalies
3. **Correlate Signals**: Use metrics, logs, and traces together for complete visibility
4. **Alert Meaningfully**: Configure actionable alerts with clear remediation steps
5. **Document Everything**: Maintain runbooks and troubleshooting guides

### Dashboard Organization

1. **Hierarchy of Detail**: Start with high-level dashboards, drill down as needed
2. **Consistent Layout**: Use similar layouts across dashboards for familiarity
3. **Context with Annotations**: Add deployment markers and event annotations
4. **Template Variables**: Use variables for flexible filtering
5. **Performance Considerations**: Optimize complex queries to maintain dashboard performance

### Query Optimization

1. **Limit Time Range**: Query only the time range needed
2. **Reduce Cardinality**: Filter metrics appropriately to reduce processing
3. **Use Rate Function**: Use `rate()` instead of `increase()` for longer intervals
4. **Avoid Regex Where Possible**: Use exact matches for better performance
5. **Test Complex Queries**: Validate complex queries in Prometheus UI first

### Alert Tuning

1. **Reduce False Positives**: Ensure alert thresholds account for normal variation
2. **Use Appropriate Durations**: Set "for" clauses to avoid alerting on spikes
3. **Tiered Severity**: Use different thresholds for warning vs. critical alerts
4. **Business Hours Awareness**: Consider time-based routing for non-critical alerts
5. **Regular Review**: Periodically review alert frequency and effectiveness

## Reference

### PromQL Query Examples

```promql
# Calculate request rate per second for API Gateway
sum(rate(http_requests_total{service="api-gateway"}[5m])) by (path)

# Get 95th percentile response time
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service="calculation-service"}[5m])) by (le))

# Calculate error rate percentage
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100

# Average borrow rate by ticker
avg(borrow_rate) by (ticker)

# Cache hit rate percentage
sum(rate(cache_hits_total[5m])) / (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m]))) * 100
```

### LogQL Query Examples

```logql
# All error logs across services
{namespace="borrow-rate-engine"} |= "ERROR"

# Extract JSON fields and filter
{namespace="borrow-rate-engine"} | json | client_id="xyz123"

# Parse JSON and filter on numeric values
{namespace="borrow-rate-engine"} | json | total_fee > 1000

# Extract specific fields and format output
{namespace="borrow-rate-engine"} | json | line_format "{{.timestamp}} {{.level}} {{.message}}"

# Calculate error frequency
sum(count_over_time({namespace="borrow-rate-engine", level="ERROR"}[5m])) by (service)
```

### Common Metrics Reference

#### API Gateway Metrics

- `http_requests_total`: Total HTTP requests processed
- `http_request_duration_seconds`: Request duration in seconds
- `authentication_attempts_total`: Authentication attempts (success/failure)
- `rate_limit_exceeded_total`: Rate limit exceeded events

#### Calculation Service Metrics

- `calculation_total`: Total calculations performed
- `calculation_duration_seconds`: Calculation duration in seconds
- `calculation_fee_amount`: Fee amount distribution
- `calculation_errors_total`: Calculation errors by type

#### Data Service Metrics

- `external_api_requests_total`: External API requests by status
- `external_api_request_duration_seconds`: External API request duration
- `database_query_duration_seconds`: Database query duration

#### Cache Service Metrics

- `cache_hits_total`: Cache hits by key pattern
- `cache_misses_total`: Cache misses by key pattern
- `cache_size_bytes`: Cache size in bytes
- `cache_evictions_total`: Cache evictions by reason

### Useful Grafana Features

- **Dashboard Variables**: Use template variables (top of dashboard) to filter by service, instance, etc.
- **Time Range Control**: Adjust the time range (top-right) to focus on specific periods
- **Panel Actions**: Click on panel title for export, view, edit options
- **Explore View**: Click on any panel and select "Explore" to dive deeper
- **Dashboard Playlists**: Create playlists for operations displays
- **Annotations**: Add annotations to mark deployments or incidents

### Relevant Runbooks

- [API Gateway Troubleshooting Runbook](../runbooks/api-gateway.md)
- [Calculation Service Troubleshooting Runbook](../runbooks/calculation-service.md)
- [External API Failures Runbook](../runbooks/external-api-failures.md)
- [Database Performance Runbook](../runbooks/database-performance.md)
- [Cache Service Runbook](../runbooks/cache-service.md)
- [Incident Response Playbook](../runbooks/incident-response.md)

### Contact Information

| Team | Responsibility | Contact |
|------|----------------|---------|
| Operations | System health, alerts | ops@example.com |
| Engineering | Core services, performance | engineering@example.com |
| Database | Database performance, scaling | dba@example.com |
| Security | Security monitoring | security@example.com |

Emergency Support: +1-555-123-4567