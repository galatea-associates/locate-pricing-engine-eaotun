# Integration Tests for Borrow Rate & Locate Fee Pricing Engine

This directory contains integration tests for the Borrow Rate & Locate Fee Pricing Engine. These tests verify the correct interaction between system components and external dependencies, focusing on data flow, API contracts, and error handling scenarios.

## Test Structure

The integration tests are organized as follows:

- `config/`: Test configuration settings and environment variables
- `fixtures/`: Test data fixtures for stocks, brokers, and API responses
- `helpers/`: Utility classes for API client, mock servers, and assertions
- `test_*.py`: Individual test modules for different system components

## Key Components

The integration test suite includes the following key components:

1. **API Client**: A wrapper around HTTP requests to interact with the API endpoints
2. **Mock Servers**: Configurable HTTP servers that simulate external API responses
3. **Assertion Utilities**: Helper functions to validate API responses and calculation results
4. **Test Fixtures**: Reusable test data for different test scenarios

## Mock Server Architecture

The integration tests use mock servers to simulate external dependencies:

- **SecLendMockServer**: Simulates the SecLend API for borrow rates
- **MarketApiMockServer**: Simulates the Market Volatility API
- **EventApiMockServer**: Simulates the Event Calendar API

These mock servers run in separate threads and can be configured to return specific responses or simulate error conditions.

## Test Configuration

Test settings are managed through the `config/settings.py` module, which provides:

- API base URL and credentials
- Mock server URLs and ports
- Test database and Redis connections
- Environment-specific configuration

Settings can be overridden using environment variables or a `.env.test` file.

## Running the Tests

To run the integration tests:

```bash
# Run all integration tests
pytest src/test/integration_tests

# Run tests for a specific component
pytest src/test/integration_tests/test_api_gateway.py

# Run with detailed output
pytest src/test/integration_tests -v

# Run with specific markers
pytest src/test/integration_tests -m "api or calculation"
```

## Test Environment Setup

The integration tests can run in two modes:

1. **Isolated Mode**: Uses mock servers for all external dependencies
2. **Connected Mode**: Connects to actual external services (requires configuration)

By default, tests run in isolated mode. To use connected mode, set the environment variable `USE_MOCK_SERVERS=false`.

## Docker Environment

A Docker Compose environment is available for running tests with isolated dependencies:

```bash
# Start the test environment
docker-compose -f src/test/docker/docker-compose.test.yml up -d

# Run tests in the Docker environment
docker-compose -f src/test/docker/docker-compose.test.yml exec test-runner pytest src/test/integration_tests

# Stop the test environment
docker-compose -f src/test/docker/docker-compose.test.yml down
```

## Writing New Tests

When writing new integration tests:

1. Use the existing fixtures and helpers to maintain consistency
2. Configure mock servers to simulate the expected external API behavior
3. Use the assertion utilities to validate responses
4. Follow the existing test patterns for similar functionality
5. Add appropriate test markers for categorization

## Test Coverage

The integration tests cover the following areas:

- API Gateway functionality (authentication, validation, error handling)
- Calculation Service accuracy and error handling
- Data Service integration with external APIs
- Cache Service behavior and invalidation
- External API client resilience and fallback mechanisms
- End-to-end calculation flows with various scenarios

## Troubleshooting

Common issues and solutions:

- **Port conflicts**: Change mock server ports in `.env.test` if default ports are in use
- **Database connection errors**: Ensure test database is running and accessible
- **Mock server failures**: Check for port conflicts or increase startup timeout
- **Inconsistent test results**: Reset test database between test runs
- **Slow tests**: Use pytest's `-xvs` flags to see detailed output and identify bottlenecks