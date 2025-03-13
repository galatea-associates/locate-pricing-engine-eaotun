# Borrow Rate & Locate Fee Pricing Engine

A specialized financial system designed to dynamically calculate short-selling costs for brokerages and financial institutions.

## Overview

The Borrow Rate & Locate Fee Pricing Engine is a REST API-based system that calculates borrowing costs for short-selling operations. It dynamically determines rates based on security characteristics, market conditions, and client-specific parameters.

This system enables financial institutions to optimize revenue from securities lending while providing transparent, consistent pricing to their clients, potentially increasing securities lending revenue by 5-15% through more accurate fee calculations and reduced manual errors.

## Key Features

- Real-time borrow rate calculation based on market conditions
- Client-specific fee calculation with markup and transaction fees
- REST API for integration with trading platforms
- Caching mechanism for performance optimization
- Comprehensive error handling and validation
- Audit logging of all calculations
- Fallback mechanisms for external API failures

## System Architecture

The system employs a microservices architecture with the following components:

- **API Gateway**: Entry point for all client requests
- **Calculation Service**: Core business logic for fee calculations
- **Data Service**: Data access and external API integration
- **Cache Service**: Performance optimization through multi-level caching
- **Audit Service**: Compliance and transaction logging

External integrations include:
- SecLend API for real-time borrow rates
- Market Volatility API for risk adjustments
- Event Calendar API for corporate action risk factors

## Technology Stack

- **Backend**: Python 3.11+ with FastAPI
- **Data Processing**: Pandas, NumPy
- **Database**: PostgreSQL 15+ with TimescaleDB extension
- **Caching**: Redis 7.0+
- **Containerization**: Docker, Kubernetes
- **Infrastructure**: AWS (EKS, RDS, ElastiCache)
- **Monitoring**: Prometheus, Grafana, Datadog
- **CI/CD**: GitHub Actions

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- AWS CLI (for production deployment)
- Kubernetes CLI (for production deployment)

### Local Development Setup

1. Clone the repository
   ```bash
   git clone [repository-url]
   cd borrow-rate-engine
   ```

2. Create and configure environment variables
   ```bash
   cp src/backend/.env.example src/backend/.env
   # Edit .env file with your configuration
   ```

3. Start the development environment
   ```bash
   docker-compose -f src/backend/docker-compose.yml up -d
   ```

4. Run database migrations
   ```bash
   docker-compose -f src/backend/docker-compose.yml exec app python -m src.backend.scripts.run_migrations
   ```

5. Seed initial data
   ```bash
   docker-compose -f src/backend/docker-compose.yml exec app python -m src.backend.scripts.seed_data
   ```

6. Access the API documentation
   ```
   http://localhost:8000/docs
   ```

## API Documentation

The API is documented using OpenAPI/Swagger and can be accessed at `/docs` when running the service.

### Key Endpoints

- `POST /api/v1/calculate-locate` - Calculate locate fee for a security
- `GET /api/v1/rates/{ticker}` - Get current borrow rate for a ticker
- `GET /api/v1/health` - Service health check

Detailed API documentation is available in the [docs/api](docs/api) directory.

## Testing

The project includes comprehensive test suites:

- **Unit Tests**: Test individual components
  ```bash
  pytest src/backend/tests/
  ```

- **Integration Tests**: Test component interactions
  ```bash
  ./src/test/scripts/run_integration_tests.sh
  ```

- **End-to-End Tests**: Test complete system flows
  ```bash
  ./src/test/scripts/run_e2e_tests.sh
  ```

- **Performance Tests**: Test system under load
  ```bash
  ./src/test/scripts/run_performance_tests.sh
  ```

## Deployment

The system can be deployed to Kubernetes using Helm or Kustomize:

### Using Helm

```bash
# Deploy API Gateway
helm install api-gateway ./infrastructure/helm/api-gateway -f ./infrastructure/helm/api-gateway/values.yaml

# Deploy other services similarly
```

### Using Kustomize

```bash
# Deploy to development environment
kubectl apply -k infrastructure/kubernetes/overlays/dev

# Deploy to production environment
kubectl apply -k infrastructure/kubernetes/overlays/prod
```

Refer to [docs/operations/deployment.md](docs/operations/deployment.md) for detailed deployment instructions.

## Monitoring

The system includes comprehensive monitoring:

- Prometheus for metrics collection
- Grafana for visualization
- Loki for log aggregation
- Tempo for distributed tracing

Pre-configured dashboards are available in the [infrastructure/monitoring](infrastructure/monitoring) directory.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.