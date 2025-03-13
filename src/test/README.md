# Borrow Rate & Locate Fee Pricing Engine - Testing Framework

This directory contains the comprehensive testing framework for the Borrow Rate & Locate Fee Pricing Engine. The framework is designed to ensure the system meets its functional requirements, performance targets, and security standards.

## Test Directory Structure

```
├── ci/                       # CI/CD integration for tests
├── compliance_tests/         # Regulatory compliance tests
├── data_generators/          # Test data generation utilities
├── docker/                   # Docker configurations for test environments
├── e2e_tests/                # End-to-end tests
├── integration_tests/        # Integration tests
├── load_testing/             # Load and performance testing
├── metrics/                  # Test metrics collection and reporting
├── mock_servers/             # Mock implementations of external APIs
├── performance_tests/        # Performance and scalability tests
├── reports/                  # Test reports and results
├── scripts/                  # Test utility scripts
├── security_tests/           # Security and vulnerability tests
├── conftest.py               # Shared pytest configuration
├── pytest.ini                # Pytest settings
├── requirements.txt          # Test dependencies
└── README.md                 # This file
```

## Test Categories

The testing framework includes the following test categories:

### Unit Tests
Located in `src/backend/tests/`, these tests verify individual components in isolation.

### Integration Tests
Located in `integration_tests/`, these tests verify the correct interaction between system components and external dependencies.

### End-to-End Tests
Located in `e2e_tests/`, these tests verify the complete system behavior under realistic conditions.

### Performance Tests
Located in `performance_tests/`, these tests verify the system meets its performance requirements.

### Load Tests
Located in `load_testing/`, these tests verify the system's behavior under various load conditions.

### Security Tests
Located in `security_tests/`, these tests verify the system's security controls and identify vulnerabilities.

### Compliance Tests
Located in `compliance_tests/`, these tests verify the system meets regulatory requirements.

## Mock Servers

The `mock_servers/` directory contains mock implementations of the external APIs required by the system:

- **SecLend API**: Provides borrow rates for securities
- **Market Volatility API**: Provides market volatility metrics
- **Event Calendar API**: Provides event risk data

These mock servers enable reliable and reproducible testing without requiring actual connectivity to external services. See the [Mock Servers README](mock_servers/README.md) for details.

## Test Environments

The testing framework supports multiple test environments:

- **Local**: Development environment with mock external APIs
- **CI**: Continuous integration environment with isolated dependencies
- **Staging**: Pre-production environment with sandbox external APIs
- **Production-like**: Environment that mirrors production for performance testing

Environment configuration is managed through environment variables and `.env` files. See the `.env.example` file for available configuration options.

## Running Tests

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for local environment)
- Required dependencies: `pip install -r requirements.txt`

### Running Unit Tests

```bash
# Run all unit tests
python -m pytest src/backend/tests

# Run specific unit tests
python -m pytest src/backend/tests/services/calculation
```

### Running Integration Tests

```bash
# Run all integration tests
bash scripts/run_integration_tests.sh

# Run specific integration tests
python -m pytest integration_tests/test_api_gateway.py
```

### Running End-to-End Tests

```bash
# Run all E2E tests
bash scripts/run_e2e_tests.sh

# Run specific E2E tests
python -m pytest e2e_tests/test_full_calculation_flow.py
```

### Running Performance Tests

```bash
# Run all performance tests
bash scripts/run_performance_tests.sh

# Run specific performance tests
python -m pytest performance_tests/test_api_latency.py
```

### Running Load Tests

```bash
# Run load tests
cd load_testing
./run_tests.sh -t load -e development
```

### Running Security Tests

```bash
# Run all security tests
bash scripts/run_security_tests.sh

# Run specific security tests
python -m pytest security_tests/test_authentication.py
```

## Test Data

Test data is managed through fixtures and data generators:

- **Fixtures**: Reusable test data defined in `conftest.py` and `*/fixtures/` directories
- **Data Generators**: Utilities in `data_generators/` for creating test data

Test data includes:

- Stock metadata and characteristics
- Broker configurations and fee structures
- Market scenarios with expected calculation results
- Volatility and event risk factors

The data generators support various market scenarios including normal conditions, high volatility, corporate events, hard-to-borrow securities, and market disruptions.

## CI/CD Integration

The testing framework is integrated with the CI/CD pipeline through GitHub Actions workflows in the `ci/github_actions/` directory:

- `integration_test_workflow.yml`: Runs integration tests on pull requests
- `e2e_test_workflow.yml`: Runs E2E tests before deployment
- `performance_test_workflow.yml`: Runs performance tests after deployment
- `security_scan_workflow.yml`: Runs security tests on a schedule
- `compliance_test_workflow.yml`: Runs compliance tests on a schedule
- `nightly_test_workflow.yml`: Runs comprehensive tests nightly

Test results are automatically collected, analyzed, and reported to the team.

## Test Reports

Test reports are generated in the `reports/` directory and include:

- Test execution results and statistics
- Code coverage reports
- Performance metrics and charts
- Security findings and recommendations

The reporting framework supports various formats including HTML, JSON, and CSV.

## Quality Metrics

The testing framework tracks the following quality metrics:

- **Code Coverage**: Target of ≥90% overall, 100% for calculation logic
- **Test Success Rate**: Target of 100% for all test suites
- **API Response Time**: Target of <100ms (p95) under test load
- **Error Rate**: Target of <0.1% during load testing

These metrics are monitored through the CI/CD pipeline and reported to the team.

## Test Scripts

The `scripts/` directory contains utility scripts for test execution and management:

- `run_integration_tests.sh`: Runs integration tests
- `run_e2e_tests.sh`: Runs end-to-end tests
- `run_performance_tests.sh`: Runs performance tests
- `run_security_tests.sh`: Runs security tests
- `run_all_tests.sh`: Runs all test types
- `setup_test_env.sh`: Sets up the test environment
- `run_mock_servers.sh`: Starts mock servers
- `clean_test_data.py`: Cleans up test data
- `generate_test_report.py`: Generates test reports

## Extending the Test Framework

When adding new tests:

1. Follow the existing directory structure and naming conventions
2. Use the shared fixtures and helpers to maintain consistency
3. Add appropriate test markers for categorization
4. Update documentation as needed
5. Ensure tests are isolated and don't interfere with each other

For new test types or categories, create a new directory with a README.md file explaining the purpose and usage of the tests.

## Troubleshooting

Common issues and solutions:

- **Connection errors**: Verify API_BASE_URL and network connectivity
- **Authentication failures**: Check API_KEY validity
- **Test timeouts**: Increase TEST_TIMEOUT value
- **Mock server issues**: Ensure mock servers are running with `docker-compose ps`
- **Data inconsistencies**: Reset test data with `scripts/clean_test_data.py`
- **Port conflicts**: Change mock server ports in `.env.test` if default ports are in use
- **Database connection errors**: Ensure test database is running and accessible

## References

- [Integration Tests README](integration_tests/README.md)
- [End-to-End Tests README](e2e_tests/README.md)
- [Performance Tests README](performance_tests/README.md)
- [Load Testing README](load_testing/README.md)
- [Mock Servers README](mock_servers/README.md)
- [Security Tests README](security_tests/README.md)
- [Main Project README](../README.md)
- [Technical Specifications](../docs/architecture/overview.md)