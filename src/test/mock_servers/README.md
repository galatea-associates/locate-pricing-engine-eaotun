# Mock Servers for Borrow Rate & Locate Fee Pricing Engine

This directory contains mock server implementations that simulate the external APIs required by the Borrow Rate & Locate Fee Pricing Engine. These mock servers allow for testing the system without requiring actual connectivity to external services, enabling reliable and reproducible test scenarios.

## Overview

The mock servers provide simulated responses for the following external APIs:

1. **SecLend API** - Provides borrow rates for securities
2. **Market Volatility API** - Provides market volatility metrics
3. **Event Calendar API** - Provides event risk data for securities

Each mock server is implemented as a FastAPI application that mimics the behavior and response format of the corresponding real API. The mock servers can be configured to simulate various scenarios including normal operation, high volatility conditions, API failures, and timeouts.

## Architecture

Each mock server follows a similar architecture:

- **app.py** - Main application file that initializes the FastAPI app and server
- **handlers.py** - Implements the API endpoints and request handling logic
- **data.py** - Provides predefined test data and response templates

The mock servers are designed to be run as Docker containers using the provided docker-compose.yml file, which sets up all three services with appropriate network configuration.

## Features

The mock servers provide the following features:

- **Realistic API responses** - Responses match the format and structure of the real APIs
- **Configurable scenarios** - Support for normal market conditions, high volatility, and error scenarios
- **Failure simulation** - Ability to simulate API failures and timeouts for testing fallback mechanisms
- **Admin endpoints** - Special endpoints for controlling mock server behavior during tests
- **Health checks** - Endpoints for monitoring server health in containerized environments

## Setup and Installation

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Installation

1. Clone the repository
2. Navigate to the `src/test/mock_servers` directory
3. Install dependencies (for local development):
   ```
   pip install -r requirements.txt
   ```

## Running the Mock Servers

### Using Docker Compose (Recommended)

```bash
# Start all mock servers
docker-compose up

# Start a specific mock server
docker-compose up seclend-api

# Start in detached mode
docker-compose up -d

# Stop all mock servers
docker-compose down
```

### Running Locally (Development)

```bash
# Start SecLend API mock server
cd src/test/mock_servers
uvicorn seclend_api.app:app --host 0.0.0.0 --port 8001 --reload

# Start Market Volatility API mock server
uvicorn market_api.app:app --host 0.0.0.0 --port 8002 --reload

# Start Event Calendar API mock server
uvicorn event_api.app:app --host 0.0.0.0 --port 8003 --reload
```

## Configuration

The mock servers can be configured using environment variables:

| Variable | Description | Default | Example |
|----------|-------------|---------|--------|
| `MOCK_API_PORT` | Port number for the mock server | Varies by service | `8001` |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG` |
| `FAILURE_RATE` | Percentage of requests that should fail | `0` | `20` |
| `DELAY_RATE` | Percentage of requests that should be delayed | `0` | `10` |

These variables can be set in the docker-compose.yml file or passed directly when running the servers locally.

## API Endpoints

### SecLend API (Port 8001)

- `GET /api/v1/borrows/{ticker}` - Get borrow rate for a specific ticker
- `GET /api/v1/borrows?tickers=AAPL,MSFT,GOOGL` - Get borrow rates for multiple tickers
- `POST /api/v1/admin/volatility-mode` - Toggle high volatility mode
- `POST /api/v1/admin/custom-response/{ticker}` - Set custom response for a ticker
- `POST /api/v1/admin/clear-custom-responses` - Clear all custom responses
- `GET /api/v1/health` - Health check endpoint

### Market Volatility API (Port 8002)

- `GET /api/v1/market/volatility/{ticker}` - Get volatility metrics for a specific ticker
- `GET /api/v1/market/vix` - Get overall market volatility index
- `POST /api/v1/admin/high-volatility` - Toggle high volatility mode
- `POST /api/v1/admin/custom-response/{ticker}` - Set custom response for a ticker
- `GET /api/v1/health` - Health check endpoint

### Event Calendar API (Port 8003)

- `GET /api/v1/calendar/events` - Get upcoming events for all securities
- `GET /api/v1/calendar/events/{ticker}` - Get upcoming events for a specific ticker
- `POST /api/v1/admin/high-risk` - Toggle high event risk mode
- `POST /api/v1/admin/custom-event/{ticker}` - Add custom event for a ticker
- `GET /api/v1/health` - Health check endpoint

## Testing Scenarios

The mock servers support various testing scenarios:

### Normal Market Conditions

Default behavior with standard borrow rates and volatility metrics.

### High Volatility Market

Activate using the admin endpoints to simulate elevated borrow rates and volatility.

### API Failures

Use special ticker symbols to trigger errors:
- `ERROR_TIMEOUT` - Simulates request timeout
- `ERROR_500` - Returns 500 Internal Server Error
- `ERROR_403` - Returns 403 Forbidden
- `ERROR_404` - Returns 404 Not Found

### Custom Responses

Use the admin endpoints to configure custom responses for specific tickers during test execution.

## Integration with Tests

The mock servers are designed to be used with the integration and end-to-end tests in the `src/test/integration_tests` and `src/test/e2e_tests` directories.

### Example Integration

```python
# In your test setup
import requests

# Configure mock server behavior
requests.post("http://localhost:8001/api/v1/admin/volatility-mode", json={"enabled": True})

# Run your test against the mock API
response = requests.get("http://localhost:8001/api/v1/borrows/AAPL")
assert response.status_code == 200
assert response.json()["rate"] > 0.05  # High volatility rate
```

## Extending the Mock Servers

To add new functionality to the mock servers:

1. Add new data in the appropriate `data.py` file
2. Implement new endpoints in the corresponding `handlers.py` file
3. Update this documentation with the new endpoints

For adding a completely new mock server:

1. Create a new directory with the API name
2. Implement `app.py`, `handlers.py`, and `data.py` following the existing pattern
3. Add the new service to the `docker-compose.yml` file
4. Update this documentation

## Troubleshooting

### Common Issues

**Port conflicts**

If you encounter port conflicts, modify the port mappings in the docker-compose.yml file or use different ports when running locally.

**Container startup failures**

Check the logs using `docker-compose logs` to identify the issue. Common problems include missing dependencies or configuration errors.

**Mock server not responding**

Verify that the server is running using the health check endpoint (e.g., `GET http://localhost:8001/api/v1/health`).

## Contributing

When contributing to the mock servers:

1. Follow the existing code structure and patterns
2. Add appropriate tests for new functionality
3. Update documentation, including this README
4. Ensure all mock servers remain compatible with the main application