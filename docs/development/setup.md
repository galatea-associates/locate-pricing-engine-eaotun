# Development Environment Setup Guide

## Introduction

This document provides comprehensive instructions for setting up the development environment for the Borrow Rate & Locate Fee Pricing Engine. The engine is a specialized financial system designed to dynamically calculate short-selling costs for brokerages and financial institutions, providing accurate, real-time pricing of securities borrowing transactions.

This development environment ensures consistent environments across development and production, facilitating reliable testing and seamless deployment of financial calculations.

## Prerequisites

Before setting up the development environment, ensure you have the following prerequisites installed on your system.

### Required Software

- Docker (24.0+)
- Docker Compose (1.29.2+)
- Python (3.11+)
- Git
- Make (optional, for convenience scripts)

### Recommended Tools

- Visual Studio Code with Python extensions
- Postman or similar API testing tool
- Redis Desktop Manager or similar Redis GUI

## Getting Started

Follow these steps to set up your development environment for the Borrow Rate & Locate Fee Pricing Engine.

### Clone the Repository

```bash
git clone <repository-url>
cd borrow-rate-engine
```

### Environment Configuration

1. Copy the example environment file to create your local configuration
2. Update environment variables as needed for your local setup

```bash
cp src/backend/.env.example src/backend/.env
```

### Docker Environment Setup

1. Build and start all services using Docker Compose
2. Verify all services are running correctly

```bash
cd src/backend
docker-compose up -d
docker-compose ps
```

## Environment Components

The development environment consists of several components that work together to provide a complete system for development and testing.

### API Service

FastAPI-based REST API service for calculating borrow rates and locate fees.

- Runs on port 8000
- Swagger UI available at http://localhost:8000/docs
- ReDoc available at http://localhost:8000/redoc
- Health check endpoint at http://localhost:8000/health

### Database

PostgreSQL database for storing stock metadata, broker configurations, and audit logs.

- Runs on port 5432
- Default credentials: postgres/postgres
- Default database name: borrow_rate_engine
- Data persisted in Docker volume: postgres_data

### Cache

Redis cache for storing frequently accessed data like borrow rates and volatility metrics.

- Runs on port 6379
- No authentication in development mode
- Data persisted in Docker volume: redis_data
- Configured with appendonly for persistence

### Mock External APIs

Mock servers for simulating external API dependencies.

- SecLend API mock on port 8001
- Market Volatility API mock on port 8002
- Event Calendar API mock on port 8003
- All mocks have /health endpoints for status checking

## Development Workflow

This section covers common development tasks and workflows.

### Running Database Migrations

Apply database schema changes using Alembic migrations:

```bash
docker-compose exec api python -m scripts.run_migrations
```

### Seeding Test Data

Populate the database with test data for development:

```bash
docker-compose exec api python -m scripts.seed_data
```

### Running Tests

Execute the test suite to verify functionality:

```bash
docker-compose exec api pytest
```

### Viewing Logs

Access logs from the various services:

```bash
docker-compose logs -f api
docker-compose logs -f db
docker-compose logs -f redis
```

### Rebuilding Services

Rebuild services after code changes:

```bash
docker-compose up -d --build api
```

## Local Development

For faster iteration, you might prefer to develop outside of Docker. This section provides guidance for local development.

### Virtual Environment Setup

Create and activate a Python virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r src/backend/requirements.txt
```

### Running the API Locally

Run the API service directly on your host machine:

```bash
cd src/backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

When running locally, update the following environment variables in your `.env` file to point to the Docker services:
- DATABASE_URL
- REDIS_URL
- External API URLs (SECLEND_API_BASE_URL, MARKET_VOLATILITY_API_BASE_URL, EVENT_CALENDAR_API_BASE_URL)

## Troubleshooting

This section addresses common issues that may arise during development and provides solutions.

### Database Connection Issues

**Problem**: API service cannot connect to the database.

**Solution**: Ensure the database container is running and healthy. Check the DATABASE_URL environment variable.

### Redis Connection Issues

**Problem**: API service cannot connect to Redis.

**Solution**: Ensure the Redis container is running and healthy. Check the REDIS_URL environment variable.

### Mock API Issues

**Problem**: External API calls failing in development.

**Solution**: Verify mock API containers are running. Check the corresponding API_BASE_URL environment variables.

### Port Conflicts

**Problem**: Services fail to start due to port conflicts.

**Solution**: Check if other applications are using the required ports. Modify the port mappings in docker-compose.yml if needed.

## Next Steps

For more information, refer to the following resources:

- [API Documentation](../api/openapi.yaml)
- [Architecture Overview](../architecture/overview.md)
- [Coding Standards](./coding-standards.md)
- [Testing Guide](./testing-guide.md)

## Examples

### Example API Request

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/calculate-locate' \
  -H 'accept: application/json' \
  -H 'X-API-Key: example_standard_api_key_replace_with_secure_value' \
  -H 'Content-Type: application/json' \
  -d '{
  "ticker": "AAPL",
  "position_value": 100000,
  "loan_days": 30,
  "client_id": "standard_client"
}'
```

### Example API Response

```json
{
  "status": "success",
  "total_fee": 428.77,
  "breakdown": {
    "borrow_cost": 383.56,
    "markup": 19.18,
    "transaction_fees": 26.03
  },
  "borrow_rate_used": 0.047
}
```

## Appendix

### Environment Variables

| Variable | Default Value | Description |
|----------|---------------|-------------|
| APP_NAME | Borrow Rate & Locate Fee Pricing Engine | Application name for logging and identification |
| API_VERSION | v1 | API version for URL paths |
| ENVIRONMENT | development | Environment name (development, staging, production) |
| DATABASE_URL | postgresql://postgres:postgres@db:5432/borrow_rate_engine | PostgreSQL connection string |
| REDIS_URL | redis://redis:6379/0 | Redis connection string |
| SECLEND_API_BASE_URL | http://seclend-api:8001/api | Base URL for SecLend API (mock in development) |
| MARKET_VOLATILITY_API_BASE_URL | http://market-api:8002/api | Base URL for Market Volatility API (mock in development) |
| EVENT_CALENDAR_API_BASE_URL | http://event-api:8003/api | Base URL for Event Calendar API (mock in development) |

### Docker Services

| Service | Description | Port | Dependencies |
|---------|-------------|------|-------------|
| api | Main API service for the Borrow Rate & Locate Fee Pricing Engine | 8000 | db, redis, seclend-api, market-api, event-api |
| db | PostgreSQL database for storing application data | 5432 | - |
| redis | Redis cache for storing frequently accessed data | 6379 | - |
| seclend-api | Mock SecLend API for development and testing | 8001 | - |
| market-api | Mock Market Volatility API for development and testing | 8002 | - |
| event-api | Mock Event Calendar API for development and testing | 8003 | - |