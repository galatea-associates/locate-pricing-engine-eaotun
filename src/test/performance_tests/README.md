# Performance Testing Framework for Borrow Rate & Locate Fee Pricing Engine

This document provides comprehensive guidance on the performance testing framework for the Borrow Rate & Locate Fee Pricing Engine, including how to run tests, interpret results, and configure the test environment to validate that the system meets its performance requirements.

## Table of Contents

- [Performance Testing Framework](#performance-testing-framework)
- [Test Categories](#test-categories)
- [Performance Requirements](#performance-requirements)
- [Test Environment Setup](#test-environment-setup)
- [Running Performance Tests](#running-performance-tests)
- [Test Configuration](#test-configuration)
- [Metrics Collection](#metrics-collection)
- [Results Analysis](#results-analysis)
- [Report Generation](#report-generation)
- [Continuous Integration](#continuous-integration)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [References](#references)

## Performance Testing Framework

The performance testing framework for the Borrow Rate & Locate Fee Pricing Engine is designed to validate that the system meets its critical performance requirements. As a financial system that calculates borrow rates and locate fees for securities lending operations, the engine must deliver accurate calculations with high throughput and low latency.

The framework uses pytest as its foundation and extends it with custom fixtures, metrics collection utilities, and analysis tools specifically designed for performance testing. Key components include:

- **Test Modules**: Organized by performance characteristic being tested
- **Configuration**: Centralized settings for all test parameters
- **Metrics Collection**: Utilities to capture and store performance metrics
- **Analysis Tools**: Statistical analysis and threshold validation
- **Reporting**: Generation of standardized performance reports

The framework enables comprehensive validation of the system's performance characteristics across different load profiles and usage patterns.

## Test Categories

The performance testing framework includes the following test categories:

### API Latency Tests

Located in `test_api_latency.py`, these tests measure and validate API response times under various load conditions. They ensure that the system meets its response time SLAs, particularly the requirement for p95 response times under 100ms.

Key tests include:
- Single request latency measurement
- Concurrent request latency under moderate load
- Latency distribution analysis under heavy load
- Latency measurement for different API endpoints and operations

### Calculation Speed Tests

Located in `test_calculation_speed.py`, these tests focus on the performance of the core calculation engine. They validate that calculations complete within the required timeframe (less than 50ms) across a variety of scenarios.

Key tests include:
- Basic fee calculation performance
- Complex calculation scenarios with volatility adjustments
- Calculation performance with different input parameters
- Batch calculation performance

### Throughput Tests

Located in `test_throughput.py`, these tests validate the system's ability to handle the required request volume. They ensure that the system can sustain processing of at least 1000 requests per second as required.

Key tests include:
- Sustained throughput test (1000 requests/second)
- Stress test (2000+ requests/second)
- Ramp-up test (gradually increasing load)
- Spike test (sudden increase to 3000 requests/second)

### Resource Utilization Tests

Located in `test_resource_utilization.py`, these tests monitor CPU, memory, and network usage during load testing to ensure the system uses resources efficiently.

Key tests include:
- CPU utilization under load
- Memory consumption patterns
- Network I/O monitoring
- Database connection pool utilization

### Resilience Under Load Tests

Located in `test_resilience_under_load.py`, these tests verify system stability under sustained or spike loads, ensuring it maintains performance and doesn't degrade over time.

Key tests include:
- Endurance test (sustained load for 24 hours)
- Recovery after load spike
- Performance under database contention
- Behavior during external API slowdowns

## Performance Requirements

The performance tests validate the following key requirements:

| Metric | Requirement | Test Category |
|--------|-------------|---------------|
| API Response Time | <100ms (p95) | API Latency |
| Calculation Speed | <50ms per calculation | Calculation Speed |
| Throughput | 1000+ requests/second | Throughput |
| Error Rate | <0.1% under load | All Categories |
| System Availability | 99.95% uptime | Resilience |

These requirements are critical for a financial system that must provide accurate, real-time pricing information for securities lending operations. The performance testing framework provides comprehensive validation that these requirements are met.

## Test Environment Setup

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose (for local environment testing)
- Access to a staging or performance testing environment
- API credentials with appropriate permissions

### Installation

1. Clone the repository:
   ```bash
   git clone [repository-url]
   cd [repository-directory]
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   ```

3. Set up environment variables:
   ```bash
   export PERFORMANCE_TEST_API_BASE_URL="http://api-gateway.staging.svc:8000"
   export PERFORMANCE_TEST_API_KEY="your_api_key_here"
   export PERFORMANCE_TEST_CONCURRENT_USERS=100
   export PERFORMANCE_TEST_TARGET_RPS=1000
   export PERFORMANCE_TEST_DURATION=300
   ```

### Environment Options

The performance tests can run against different environments:

1. **Local Environment**: Uses Docker Compose to start all required services locally
   ```bash
   docker-compose -f docker-compose.performance.yml up -d
   ```

2. **Staging Environment**: Tests against a dedicated staging environment
   ```bash
   export PERFORMANCE_TEST_ENV=staging
   ```

3. **Production-Like Environment**: A scaled environment that mimics production
   ```bash
   export PERFORMANCE_TEST_ENV=perf
   ```

## Running Performance Tests

### Basic Test Execution

```bash
# Run all performance tests
python -m pytest src/test/performance_tests/ -v -m performance

# Run specific performance test category
python -m pytest src/test/performance_tests/test_api_latency.py -v

# Run long-running performance tests
python -m pytest src/test/performance_tests/ -v -m "performance and slow"
```

### Test Selection

Tests are organized by performance characteristic and can be selected using pytest markers:

- `performance`: All performance tests
- `api`: API latency tests
- `calculation`: Calculation speed tests
- `throughput`: Throughput tests
- `resources`: Resource utilization tests
- `resilience`: Resilience under load tests
- `slow`: Long-running tests (typically run in scheduled jobs, not CI)

Example:
```bash
# Run only API latency tests
python -m pytest src/test/performance_tests/ -v -m "performance and api"
```

### Parallel Execution

For faster execution, tests can be run in parallel:

```bash
python -m pytest src/test/performance_tests/ -v -m performance -n 4
```

Note: Some tests cannot run in parallel due to resource contention. These tests are marked with `@pytest.mark.no_parallel`.

### Output Options

Various output formats are supported:

```bash
# Generate JUnit XML report
python -m pytest src/test/performance_tests/ -v --junitxml=results.xml

# Generate HTML report
python -m pytest src/test/performance_tests/ -v --html=report.html

# Export metrics to CSV
python -m pytest src/test/performance_tests/ -v --metrics-export=metrics.csv
```

## Test Configuration

The performance tests are configured through the `config/settings.py` file and environment variables. Key configuration options include:

### API Configuration

- `API_BASE_URL`: Base URL for the API gateway
- `API_KEY`: API key for authentication
- `API_TIMEOUT`: Request timeout in seconds

### Load Parameters

- `CONCURRENT_USERS`: Number of concurrent virtual users
- `TARGET_RPS`: Target requests per second
- `TEST_DURATION`: Duration of load tests in seconds
- `RAMP_UP_TIME`: Time to gradually increase load to target

### Performance Thresholds

- `API_LATENCY_P95_THRESHOLD`: p95 latency threshold in milliseconds
- `CALCULATION_TIME_THRESHOLD`: Maximum calculation time in milliseconds
- `ERROR_RATE_THRESHOLD`: Maximum acceptable error rate percentage
- `RESOURCE_UTILIZATION_THRESHOLDS`: CPU, memory, and network thresholds

### Environment-Specific Settings

Different settings can be applied based on the test environment:

```python
# In config/settings.py
if ENVIRONMENT == "local":
    CONCURRENT_USERS = 10
    TARGET_RPS = 100
elif ENVIRONMENT == "staging":
    CONCURRENT_USERS = 50
    TARGET_RPS = 500
elif ENVIRONMENT == "perf":
    CONCURRENT_USERS = 100
    TARGET_RPS = 1000
```

## Metrics Collection

The performance testing framework includes a comprehensive metrics collection system in `helpers/metrics_collector.py`. This system captures various performance metrics during test execution.

### Available Collectors

- `APIMetricsCollector`: Captures API response times, throughput, and error rates
- `CalculationMetricsCollector`: Measures calculation speed and accuracy
- `ResourceMetricsCollector`: Monitors CPU, memory, and network usage
- `DatabaseMetricsCollector`: Tracks database performance and connection pool usage

### Using Metrics Collectors

```python
from src.test.performance_tests.helpers.metrics_collector import get_api_metrics_collector, metrics_collection

# Create a metrics collector
collector = get_api_metrics_collector({
    'include_percentiles': True,
    'record_individual_samples': True
})

# Use the metrics collector in a test
with metrics_collection(collector) as metrics:
    # Run your test operations here
    for _ in range(100):
        response = api_client.calculate_locate_fee(ticker="AAPL", position_value=100000, loan_days=30)

# Analyze the collected metrics
results = check_performance_thresholds(metrics, 'api')
print(f"Test passed: {results['passed']}")
```

### Metrics Storage

Metrics are stored in various formats:

- In-memory during test execution
- CSV export for detailed analysis
- Time-series database (Prometheus) for long-term tracking
- Test result attributes for JUnit reporting

## Results Analysis

The `helpers/analysis.py` module provides tools for analyzing performance test results, including:

### Statistical Analysis

- Percentile calculations (p50, p90, p95, p99)
- Mean, median, and standard deviation
- Outlier detection and removal
- Trend analysis for long-running tests

### Threshold Validation

- Comparison of results against defined thresholds
- Pass/fail determination based on performance requirements
- Degradation detection compared to baseline performance

### Anomaly Detection

- Identification of performance anomalies
- Root cause analysis helpers
- Correlation between metrics

### Example Usage

```python
from src.test.performance_tests.helpers.analysis import analyze_api_latency, detect_anomalies

# Analyze latency metrics
latency_stats = analyze_api_latency(metrics)
print(f"P95 latency: {latency_stats['p95']}ms")

# Detect anomalies
anomalies = detect_anomalies(metrics, baseline_metrics)
if anomalies:
    print(f"Detected {len(anomalies)} anomalies in the current test run")
```

## Report Generation

The `helpers/reporting.py` module provides capabilities for generating detailed performance test reports.

### Report Formats

- HTML reports with interactive charts
- PDF reports for formal documentation
- JSON reports for programmatic consumption
- Slack/Teams notifications for CI integration

### Visualization Options

- Response time distribution charts
- Throughput over time graphs
- Error rate visualizations
- Resource utilization dashboards

### Report Storage

Reports are stored in:

- Local filesystem for development
- Artifact storage in CI/CD
- Historical performance database for trend analysis

### Example Usage

```python
from src.test.performance_tests.helpers.reporting import generate_performance_report

# Generate a report after test execution
report_path = generate_performance_report(
    metrics,
    report_format="html",
    include_charts=True,
    output_dir="./performance-reports"
)
print(f"Report generated at: {report_path}")
```

## Continuous Integration

The performance tests are integrated into the CI/CD pipeline to ensure performance is consistently monitored.

### CI/CD Integration

- Fast performance tests run on every PR
- Full suite runs nightly on the main branch
- Extended tests (endurance, etc.) run weekly
- Results compared against historical baselines

### Performance Regression Detection

The CI pipeline automatically detects performance regressions by:

1. Comparing current results to baseline measurements
2. Flagging significant deviations (>10%)
3. Blocking deployment if critical thresholds are exceeded

### Scheduled Performance Testing

Scheduled performance tests are configured in the CI system:

```yaml
# Excerpt from CI configuration
performance_test_nightly:
  schedule: "0 0 * * *"  # Run daily at midnight
  script:
    - python -m pytest src/test/performance_tests/ -v -m "performance and not slow"

performance_test_weekly:
  schedule: "0 0 * * 0"  # Run weekly on Sunday
  script:
    - python -m pytest src/test/performance_tests/ -v -m "performance and slow"
```

### Notification Mechanisms

Performance test results trigger notifications through:

- Pull request comments with performance metrics
- Slack/Teams messages for scheduled runs
- Email alerts for performance regressions
- Dashboard updates in monitoring system

## Troubleshooting

### Common Issues

#### Environment Problems

- **Issue**: Tests fail to connect to API
  **Solution**: Check API_BASE_URL and network connectivity

- **Issue**: Authentication failures
  **Solution**: Verify API_KEY is correct and has appropriate permissions

- **Issue**: Resource allocation too low
  **Solution**: Increase container resources in Docker Compose

#### Test Failures

- **Issue**: Tests timeout during execution
  **Solution**: Increase timeout in pytest configuration or API_TIMEOUT setting

- **Issue**: Inconsistent performance results
  **Solution**: Check for resource contention or background processes

- **Issue**: High error rates during load tests
  **Solution**: Verify system under test is properly scaled for load

#### Result Interpretation

- **Issue**: False positives in performance regression
  **Solution**: Adjust threshold sensitivity in analysis tools

- **Issue**: Metrics collection overhead affecting results
  **Solution**: Use sampling mode for metrics collection

- **Issue**: Misleading averages due to outliers
  **Solution**: Use median and percentile metrics instead of mean

### Diagnostic Tools

- Check the log files in `logs/performance_tests/`
- Use the debug mode: `pytest -vvs --log-level=DEBUG`
- Run with verbose metrics: `pytest --verbose-metrics`

## Best Practices

### Writing Effective Performance Tests

1. **Isolate the test target**: Ensure tests focus on specific components
2. **Use realistic data**: Test with production-like data volumes and patterns
3. **Control external factors**: Mock external dependencies to ensure consistency
4. **Measure what matters**: Focus on end-user experience metrics
5. **Start simple**: Begin with basic tests before complex scenarios

### Interpreting Results

1. **Look at percentiles**: p95/p99 are more important than averages
2. **Consider variability**: High standard deviation indicates instability
3. **Compare to baselines**: Absolute values matter less than changes
4. **Check multiple metrics**: Correlation between metrics provides insights
5. **Understand the context**: Different environments have different characteristics

### Maintaining the Framework

1. **Keep dependencies updated**: Regularly update testing libraries
2. **Version test data**: Track changes to test data alongside code
3. **Document assumptions**: Note any assumptions about the test environment
4. **Clean up after tests**: Ensure tests don't leave resources or data behind
5. **Review and refactor**: Periodically review test code for improvements

## References

| Component | Path | Description |
|-----------|------|-------------|
| API Latency Tests | `src/test/performance_tests/test_api_latency.py` | Tests that measure and validate API response times under various load conditions |
| Calculation Speed Tests | `src/test/performance_tests/test_calculation_speed.py` | Tests that measure the performance of calculation functions and formulas |
| Throughput Tests | `src/test/performance_tests/test_throughput.py` | Tests that validate the system's ability to handle the required request volume |
| Resource Utilization Tests | `src/test/performance_tests/test_resource_utilization.py` | Tests that monitor CPU, memory, and network usage during load |
| Resilience Tests | `src/test/performance_tests/test_resilience_under_load.py` | Tests that verify system stability under sustained or spike loads |
| Performance Test Settings | `src/test/performance_tests/config/settings.py` | Configuration settings for performance tests including thresholds and parameters |
| Metrics Collector | `src/test/performance_tests/helpers/metrics_collector.py` | Utilities for collecting and analyzing performance metrics during tests |
| Performance Analysis | `src/test/performance_tests/helpers/analysis.py` | Tools for analyzing performance test results and detecting anomalies |
| Report Generation | `src/test/performance_tests/helpers/reporting.py` | Utilities for generating performance test reports and visualizations |