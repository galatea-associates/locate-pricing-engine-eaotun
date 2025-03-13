# Borrow Rate & Locate Fee Pricing Engine - Load Testing Framework

## Overview

This directory contains the load testing framework for the Borrow Rate & Locate Fee Pricing Engine API. The framework is designed to validate the system's performance characteristics against the requirements specified in the technical specifications:

- Response time: <100ms for 95% of requests
- Throughput: Support for 1000+ requests/second
- Availability: 99.95% uptime
- Error rate: <0.1% error rate under load

The framework uses Locust as the primary load testing tool, with custom scenarios designed to simulate realistic client behavior when interacting with the API.

## Prerequisites

- Python 3.11+
- Locust 2.15.0+
- pandas 2.1.0+
- matplotlib 3.7.0+
- pyyaml 6.0+
- seaborn 0.12.0+

Install all dependencies using:

```bash
pip install -r requirements.txt
```

## Directory Structure

```
├── config.yaml                # Configuration for test environments and scenarios
├── locustfile.py             # Main Locust configuration file
├── run_tests.sh              # Script to execute different types of load tests
├── analyze_results.py        # Script to analyze and visualize test results
├── requirements.txt          # Python dependencies
├── scenarios/                # Test scenario definitions
│   ├── __init__.py
│   ├── borrow_rate_scenario.py     # Scenario for testing borrow rate endpoints
│   ├── calculate_fee_scenario.py    # Scenario for testing fee calculation endpoints
│   └── mixed_workload_scenario.py   # Scenario for testing mixed workload patterns
└── reports/                  # Directory for test results and analysis
    ├── raw/                  # Raw test data
    └── analysis/             # Processed results and visualizations
```

## Configuration

The `config.yaml` file contains all configuration parameters for the load tests, including:

- Environment configurations (development, staging, production)
- Test scenario definitions
- Performance thresholds
- Test data
- Reporting settings

You can modify this file to adjust test parameters, thresholds, and environments.

## Test Scenarios

The framework includes three main test scenarios:

1. **Borrow Rate Scenario**: Tests the `/api/v1/rates/{ticker}` endpoint, which provides current borrow rates for securities.

2. **Calculate Fee Scenario**: Tests the `/api/v1/calculate-locate` endpoint, which calculates locate fees based on ticker, position value, loan days, and client ID.

3. **Mixed Workload Scenario**: Simulates a realistic mix of requests to both endpoints, representing typical client behavior.

Each scenario is defined in a separate file in the `scenarios/` directory and can be customized as needed.

## Test Types

The framework supports four types of performance tests:

1. **Load Test**: Standard load test with a steady number of users to validate normal operating conditions.
   - Default: 100 users, 10 users/second spawn rate, 5 minutes duration

2. **Stress Test**: High-load test to identify the system's breaking point.
   - Default: Up to 2000 users, 50 users/second spawn rate

3. **Endurance Test**: Long-duration test to identify performance degradation over time.
   - Default: 24 hours duration with moderate load

4. **Spike Test**: Sudden increase in load to test the system's ability to handle traffic spikes.
   - Default: Spike to 3000 users for 5 minutes

## Running Tests

Use the `run_tests.sh` script to execute different types of tests:

```bash
# Run a standard load test in the development environment
./run_tests.sh -t load -e development

# Run a stress test in the staging environment
./run_tests.sh -t stress -e staging

# Run an endurance test with custom duration
./run_tests.sh -t endurance -e staging -d 3600

# Run a spike test
./run_tests.sh -t spike -e staging

# Run a custom load test with specific parameters
./run_tests.sh -t load -e production -u 500 -r 20 -d 1800
```

Options:
- `-t, --test-type`: Type of test (load, stress, endurance, spike)
- `-e, --environment`: Target environment (development, staging, production)
- `-u, --users`: Number of users for load test
- `-r, --spawn-rate`: User spawn rate per second
- `-d, --duration`: Test duration in seconds
- `-o, --output-dir`: Custom output directory
- `-a, --analyze`: Analyze results after test completion
- `-c, --compare`: Compare with previous test results
- `-h, --help`: Show help message

## Analyzing Results

After a test completes, use the `analyze_results.py` script to process the results:

```bash
python analyze_results.py --results-dir reports/2023-10-15_14-30-22 --output-dir reports/analysis
```

This will generate:

1. Performance metrics summary
2. Response time distribution charts
3. Throughput over time charts
4. Error rate analysis
5. Resource utilization charts (if resource monitoring was enabled)
6. Comparison with previous test runs (if requested)
7. Comprehensive HTML report

The analysis will also check for any threshold violations based on the performance requirements.

## Interpreting Results

The analysis report will highlight key performance metrics:

- **Response Time**: The p95 response time should be below 100ms for all endpoints.
- **Throughput**: The system should handle at least 1000 requests per second.
- **Error Rate**: The error rate should remain below 0.1% under load.
- **Resource Utilization**: CPU and memory usage should stay within acceptable limits.

Any threshold violations will be clearly marked in the report with appropriate severity levels.

## Continuous Integration

The load testing framework is integrated with the CI/CD pipeline through GitHub Actions workflows:

- `performance_test_workflow.yml`: Runs performance tests on staging after deployment
- `nightly_test_workflow.yml`: Runs extended performance tests nightly

Test results are automatically analyzed and reported to the team via Slack notifications.

## Troubleshooting

### Common Issues

1. **Connection Errors**: Check if the target environment is accessible and API Gateway is running.

2. **Authentication Failures**: Verify that the API keys in the configuration are valid and have appropriate permissions.

3. **Resource Constraints**: If the load generator itself is running out of resources, consider distributing the load across multiple machines.

4. **Inconsistent Results**: Ensure there are no other tests or significant workloads running in the target environment during testing.

### Logs

Locust logs are stored in the reports directory along with the test results. Check these logs for detailed information about any issues encountered during test execution.

## Extending the Framework

### Adding New Scenarios

To add a new test scenario:

1. Create a new file in the `scenarios/` directory
2. Define a new class that inherits from `HttpUser`
3. Implement the required tasks and behaviors
4. Update `locustfile.py` to include the new scenario
5. Add configuration for the new scenario in `config.yaml`

### Customizing Analysis

The analysis script can be extended to include additional metrics or visualizations:

1. Add new analysis functions in `analyze_results.py`
2. Create new chart types in the `ChartGenerator` class
3. Update the report generation to include the new metrics and charts

## Best Practices

1. **Realistic Data**: Use realistic test data that represents actual production patterns.

2. **Isolated Environment**: Run tests in an isolated environment that mirrors production.

3. **Gradual Scaling**: Start with low load and gradually increase to identify performance bottlenecks.

4. **Regular Testing**: Run performance tests regularly to detect performance regressions early.

5. **Comprehensive Analysis**: Don't focus solely on averages; examine percentiles and distributions.

6. **Resource Monitoring**: Always monitor system resources during tests to identify bottlenecks.

## References

- [Locust Documentation](https://docs.locust.io/)
- [Technical Specifications - Performance Requirements](../docs/architecture/performance.md)
- [API Documentation](../docs/api/openapi.yaml)