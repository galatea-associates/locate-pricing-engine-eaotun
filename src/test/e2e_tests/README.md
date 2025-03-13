# Borrow Rate & Locate Fee Pricing Engine - End-to-End Tests

This directory contains end-to-end tests for the Borrow Rate & Locate Fee Pricing Engine. These tests verify the complete system behavior under realistic conditions, including interactions with external dependencies and handling of various failure scenarios.

## Test Structure

The E2E test suite is organized into the following components:

- **config/**: Configuration settings for different test environments
- **fixtures/**: Test data and environment setup fixtures
- **helpers/**: Utility classes and functions for test execution
- **test_*.py**: Test modules for different aspects of the system

## Key Test Modules

- **test_full_calculation_flow.py**: Tests the complete calculation flow from API request to response
- **test_system_resilience.py**: Tests fallback mechanisms and error handling
- **test_api_versioning.py**: Tests API versioning and backward compatibility
- **test_security_features.py**: Tests authentication, authorization, and rate limiting
- **test_audit_logging.py**: Tests audit trail generation and compliance
- **test_caching_behavior.py**: Tests caching mechanisms and invalidation
- **test_data_refresh.py**: Tests data synchronization with external sources

## Test Scenarios

The test suite covers various market scenarios:

1. **Normal Market Conditions**: Standard borrow rates, average volatility
2. **High Volatility Market**: Elevated VIX, high borrow rates
3. **Corporate Events**: Stocks with upcoming earnings/events
4. **Hard-to-Borrow Securities**: Limited availability stocks
5. **Market Disruption**: Extreme volatility, API failures

## Environment Configuration

Tests can be run against different environments:

- **LOCAL**: Local development environment with mock external APIs
- **DEVELOPMENT**: Development environment with sandbox external APIs
- **STAGING**: Staging environment with sandbox external APIs
- **PRODUCTION**: Production-like environment with real external APIs (restricted usage)

## Setup Instructions

1. Create a `.env.test` file based on `.env.example` with appropriate configuration
2. Install test dependencies: `pip install -r requirements.txt`
3. Start mock servers if testing locally: `../scripts/run_mock_servers.sh`
4. Run the tests: `pytest -xvs` or use the provided script: `../scripts/run_e2e_tests.sh`

## Configuration Options

Key configuration options in `.env.test`:

- `TEST_ENVIRONMENT`: Environment to test against (LOCAL, DEVELOPMENT, STAGING, PRODUCTION)
- `API_BASE_URL`: Base URL of the API to test
- `API_VERSION`: API version to test (default: v1)
- `API_KEY`: Valid API key for authentication
- `TEST_TIMEOUT`: Request timeout in seconds (default: 30)
- `MOCK_EXTERNAL_APIS`: Whether to use mock servers for external APIs (true/false)

## Mock Servers

When testing locally, mock servers simulate external APIs:

- **SecLend API**: Provides borrow rates for securities
- **Market Volatility API**: Provides market volatility metrics
- **Event Calendar API**: Provides corporate event data

Mock servers can be configured to simulate various failure conditions for resilience testing.

## Test Data

Test data is provided through fixtures in `fixtures/test_data.py`. This includes:

- Stock metadata and characteristics
- Broker configurations and fee structures
- Market scenarios with expected calculation results
- Volatility and event risk factors

## Validation

The `ResponseValidator` class in `helpers/validation.py` provides methods to validate API responses and calculation results. It handles:

- Calculation accuracy verification
- Response structure validation
- Error response validation
- Tolerance-based comparison for financial calculations

## Running Specific Tests

To run specific test categories:

- All E2E tests: `pytest -xvs -m e2e`
- Calculation flow tests: `pytest -xvs test_full_calculation_flow.py`
- Resilience tests: `pytest -xvs test_system_resilience.py`
- Security tests: `pytest -xvs test_security_features.py`

## Continuous Integration

E2E tests are integrated into the CI/CD pipeline:

- Run automatically on pull requests to staging/production
- Run nightly against the development environment
- Generate test reports available in the CI artifacts

See `../ci/github_actions/e2e_test_workflow.yml` for CI configuration.

## Troubleshooting

Common issues and solutions:

1. **Connection errors**: Verify API_BASE_URL and network connectivity
2. **Authentication failures**: Check API_KEY validity
3. **Test timeouts**: Increase TEST_TIMEOUT value
4. **Mock server issues**: Ensure mock servers are running with `docker-compose ps`
5. **Data inconsistencies**: Reset test data with `../scripts/clean_test_data.py`