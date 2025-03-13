# Borrow Rate & Locate Fee Pricing Engine

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.103.0+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15.0+-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-red.svg)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://www.docker.com/)

A high-performance REST API for calculating securities borrowing costs in real-time.

## Overview

The Borrow Rate & Locate Fee Pricing Engine is a specialized financial system designed to dynamically calculate short-selling costs for brokerages and financial institutions. It provides real-time pricing of securities borrowing transactions through a high-performance REST API.

## Features

- Real-time borrow rate calculation based on market conditions
- Client-specific fee calculation with markup and transaction fees
- Multi-level caching for optimal performance
- Fallback mechanisms for external API failures
- Comprehensive error handling and validation
- Detailed audit logging for compliance

## System Architecture

The system employs a microservices architecture with the following components:

### API Gateway
Entry point for all client requests, handling authentication, rate limiting, and request routing.

### Calculation Service
Core business logic for borrow rate and fee calculations.

### Data Service
Manages all data access, including external API integration and internal database operations.

### Cache Service
Multi-level caching to optimize performance and reduce external API calls.

### Audit Service
Records all calculations for compliance and troubleshooting.

## Technology Stack

### Backend
- Python 3.11+
- FastAPI 0.103.0+
- Pydantic 2.4.0+
- SQLAlchemy 2.0.0+
- Pandas 2.1.0+
- Redis 4.5.0+

### Database
- PostgreSQL 15.0+
- TimescaleDB 2.11+ (extension)
- Redis 7.0+ (caching)

### External Services
- SecLend API (real-time borrow rates)
- Market Data API (volatility metrics)
- Event Calendar API (corporate actions)

### DevOps
- Docker
- Kubernetes
- GitHub Actions
- Terraform

## Getting Started

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 15.0+
- Redis 7.0+

### Installation

Clone the repository:
```bash
git clone https://github.com/organization/borrow-rate-pricing-engine.git
cd borrow-rate-pricing-engine
```

Set up environment variables:
```bash
cp src/backend/.env.example src/backend/.env
# Edit .env file with your configuration
```

Using Docker:
```bash
docker-compose up -d
```

Using Poetry (local development):
```bash
cd src/backend
poetry install
poetry run python -m backend.scripts.run_migrations
poetry run python -m backend.scripts.seed_data
poetry run uvicorn backend.main:app --reload
```

### Configuration
The application is configured using environment variables. See `.env.example` for available options.

## API Documentation

Once the application is running, API documentation is available at:

### Swagger UI
http://localhost:8000/docs

### ReDoc
http://localhost:8000/redoc

### Key Endpoints
- `GET /api/v1/health`: Health check endpoint
- `GET /api/v1/rates/{ticker}`: Get current borrow rate for a ticker
- `POST /api/v1/calculate-locate`: Calculate locate fee
- `GET /api/v1/calculate-locate`: Calculate locate fee (query parameters)

### Example Request
```bash
curl -X POST http://localhost:8000/api/v1/calculate-locate \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "position_value": 100000,
    "loan_days": 30,
    "client_id": "client123"
  }'
```

### Example Response
```json
{
  "status": "success",
  "total_fee": 428.77,
  "breakdown": {
    "borrow_cost": 395.34,
    "markup": 23.72,
    "transaction_fees": 9.71
  },
  "borrow_rate_used": 0.05
}
```

## Development

### Project Structure
```
src/backend/
├── api/                 # API endpoints and dependencies
│   └── v1/              # API version 1
│       └── endpoints/   # API endpoint implementations
├── core/                # Core functionality and constants
├── db/                  # Database models and operations
│   ├── crud/            # CRUD operations
│   ├── migrations/      # Alembic migrations
│   └── models/          # SQLAlchemy models
├── middleware/          # FastAPI middleware
├── schemas/             # Pydantic models for requests/responses
├── services/            # Business logic services
│   ├── calculation/     # Calculation services
│   ├── cache/           # Caching services
│   ├── data/            # Data access services
│   ├── external/        # External API clients
│   └── audit/           # Audit logging services
├── utils/               # Utility functions
├── scripts/             # Maintenance and utility scripts
├── tests/               # Unit and integration tests
├── config/              # Configuration management
└── infrastructure/      # Infrastructure as code
```

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=backend

# Run specific test module
poetry run pytest tests/services/calculation/test_borrow_rate.py
```

### Code Quality
```bash
# Format code
poetry run black backend tests
poetry run isort backend tests

# Lint code
poetry run flake8 backend tests

# Type checking
poetry run mypy backend
```

### Generating API Keys
```bash
poetry run python -m backend.scripts.generate_api_key --client-id client123
```

## Deployment

The application can be deployed using Docker and Kubernetes.

### Docker
```bash
# Build Docker image
docker build -t borrow-rate-pricing-engine:latest .

# Run Docker container
docker run -p 8000:8000 --env-file .env borrow-rate-pricing-engine:latest
```

### Kubernetes
Kubernetes manifests are available in the `infrastructure/kubernetes/` directory.

```bash
# Apply Kubernetes manifests
kubectl apply -k infrastructure/kubernetes/overlays/prod
```

## Monitoring and Observability

The application includes comprehensive monitoring and observability features:

### Logging
Structured JSON logs are output to stdout and can be collected by logging systems like Loki or CloudWatch.

### Metrics
Prometheus metrics are exposed at `/metrics` endpoint for scraping.

### Tracing
OpenTelemetry tracing is integrated for distributed tracing of requests.

### Health Checks
Health check endpoint at `/api/v1/health` provides system status.

## License

This project is licensed under the terms of the license included in the repository.