# Borrow Rate & Locate Fee Pricing Engine API Design

## Introduction

### Purpose

The API provides programmatic access to the Borrow Rate & Locate Fee Pricing Engine, enabling trading platforms and financial applications to calculate securities borrowing costs for short-selling operations in real-time.

### Design Principles

The API follows REST architectural principles with JSON as the primary data format. It emphasizes predictability, consistency, and comprehensive error handling to support financial operations where accuracy is critical.

### Key Features

- Real-time borrow rate calculation
- Client-specific fee calculation with markup
- Detailed fee breakdown
- Caching for performance optimization
- Comprehensive error handling and validation
- Fallback mechanisms for external API failures

## API Architecture

### Component Overview

The API is built using FastAPI framework and follows a layered architecture:
- API Gateway: Entry point for all requests, handling authentication and routing
- Endpoint Handlers: Process specific API requests
- Service Layer: Implements business logic and calculations
- Data Access Layer: Interacts with databases and external APIs

### Request Flow

1. Client sends request to API Gateway
2. Request is authenticated and validated
3. Request is routed to appropriate endpoint handler
4. Endpoint handler calls service layer for business logic
5. Service layer performs calculations and data operations
6. Response is formatted and returned to client

### Technology Stack

- FastAPI: High-performance API framework
- Pydantic: Data validation and settings management
- PostgreSQL: Primary database
- Redis: Caching layer
- OpenAPI: API documentation

## Authentication and Authorization

### Authentication Method

The API uses API key authentication. Each client is issued a unique API key that must be included in the X-API-Key header of each request.

### API Key Management

- API keys are generated and managed through a secure administrative interface
- Keys are stored as hashed values in the database
- Keys can be revoked or rotated as needed
- Each key is associated with a specific client ID

### Authorization

Authorization is based on the client ID associated with the API key. Different clients may have different access levels and rate limits.

### Rate Limiting

To prevent abuse, the API implements rate limiting based on client tier:
- Standard: 60 requests/minute
- Premium: 300 requests/minute
- Internal: 1000 requests/minute

## API Versioning

### Versioning Approach

The API uses URL path versioning with the format `/api/v{major_version}/`. This approach provides clear visibility of the API version being used.

### Version Lifecycle

- Major versions (v1, v2) are supported for 24 months after a new version is released
- Minor updates within a major version maintain backward compatibility
- Deprecation notices are provided 6 months before an API version is retired

### Version Compatibility

Changes that maintain backward compatibility:
- Adding new endpoints
- Adding optional parameters
- Adding fields to response objects

Changes that break compatibility (require new major version):
- Removing endpoints
- Removing or renaming parameters
- Changing parameter types
- Changing response structure

## Endpoints

### Health Endpoints

- `GET /api/v1/health`: Overall system health status
- `GET /api/v1/health/readiness`: Service readiness check
- `GET /api/v1/health/liveness`: Service liveness check

```http
GET /api/v1/health HTTP/1.1
Host: api.example.com

Response:
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": "connected",
    "cache": "connected",
    "external_apis": "available"
  },
  "timestamp": "2023-10-15T14:30:22Z"
}
```

### Calculate Locate Fee Endpoint

- `POST /api/v1/calculate-locate`: Calculate fee based on request body
- `GET /api/v1/calculate-locate`: Calculate fee based on query parameters

```http
POST /api/v1/calculate-locate HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-API-Key: your-api-key

{
  "ticker": "AAPL",
  "position_value": 100000,
  "loan_days": 30,
  "client_id": "xyz123"
}

Response:
{
  "status": "success",
  "total_fee": 3428.77,
  "breakdown": {
    "borrow_cost": 3195.34,
    "markup": 188.53,
    "transaction_fees": 40.90
  },
  "borrow_rate_used": 0.19
}
```

### Borrow Rate Endpoints

- `GET /api/v1/rates/{ticker}`: Get current borrow rate for a ticker
- `GET /api/v1/rates/ticker/{ticker}`: Alternative path for borrow rate
- `GET /api/v1/rates/{ticker}/calculate`: Calculate custom borrow rate
- `GET /api/v1/rates/status/{status}`: Get rates by borrow status

```http
GET /api/v1/rates/AAPL HTTP/1.1
Host: api.example.com
X-API-Key: your-api-key

Response:
{
  "status": "success",
  "ticker": "AAPL",
  "current_rate": 0.05,
  "borrow_status": "EASY",
  "volatility_index": 18.5,
  "event_risk_factor": 2,
  "last_updated": "2023-10-15T14:30:22Z"
}
```

### Configuration Endpoint

- `GET /api/v1/config`: Get API configuration settings

```http
GET /api/v1/config HTTP/1.1
Host: api.example.com
X-API-Key: your-api-key

Response:
{
  "status": "success",
  "config": {
    "api_version": "1.0.0",
    "supported_features": [
      "borrow_rates",
      "locate_fees",
      "volatility_adjustment"
    ],
    "rate_limits": {
      "default": 60,
      "premium": 300
    }
  }
}
```

## Request and Response Formats

### Request Format

All requests should use JSON format for request bodies. Query parameters should follow standard URL encoding practices.

```json
// POST /api/v1/calculate-locate
{
  "ticker": "AAPL",
  "position_value": 100000,
  "loan_days": 30,
  "client_id": "xyz123"
}
```

### Response Format

All responses use a consistent JSON format with the following structure:
- Success responses include a 'status' field with value 'success'
- Error responses include 'status' field with value 'error', plus 'error' and 'error_code' fields

```json
// Success Response
{
  "status": "success",
  "total_fee": 3428.77,
  "breakdown": {
    "borrow_cost": 3195.34,
    "markup": 188.53,
    "transaction_fees": 40.90
  },
  "borrow_rate_used": 0.19
}

// Error Response
{
  "status": "error",
  "error": "Ticker not found: INVALID",
  "error_code": "TICKER_NOT_FOUND",
  "details": null
}
```

### HTTP Status Codes

The API uses standard HTTP status codes:
- 200: Successful request
- 400: Bad request (validation error)
- 401: Unauthorized (invalid API key)
- 403: Forbidden (insufficient permissions)
- 404: Not found (ticker or client not found)
- 429: Too many requests (rate limit exceeded)
- 500: Internal server error
- 503: Service unavailable (external API failure)

## Error Handling

### Error Response Structure

All error responses follow a consistent structure:
```json
{
  "status": "error",
  "error": "Human-readable error message",
  "error_code": "MACHINE_READABLE_ERROR_CODE",
  "details": {} // Optional additional information
}
```

### Validation Errors

Validation errors provide additional information about the specific validation failures:
```json
{
  "status": "error",
  "error": "Invalid parameter: position_value",
  "error_code": "INVALID_PARAMETER",
  "validation_errors": [
    {
      "field": "position_value",
      "location": "body",
      "message": "Value must be greater than 0"
    }
  ],
  "valid_params": ["ticker", "position_value>0", "loan_days>0", "client_id"]
}
```

### Common Error Codes

- `INVALID_PARAMETER`: Parameter missing or invalid
- `UNAUTHORIZED`: Missing or invalid API key
- `TICKER_NOT_FOUND`: Requested ticker not available
- `CLIENT_NOT_FOUND`: Client ID not found
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `CALCULATION_ERROR`: Error in fee calculation
- `EXTERNAL_API_UNAVAILABLE`: External data source unavailable

### Error Handling Best Practices

Clients should:
- Check the HTTP status code first
- Examine the error_code field for programmatic handling
- Display the error message to users when appropriate
- Implement exponential backoff for 429 and 503 errors

## Caching Strategy

### Cache Headers

The API uses standard HTTP cache headers to indicate cacheability:
- `Cache-Control`: Directives for caching behavior
- `ETag`: Entity tag for conditional requests
- `Last-Modified`: Timestamp of last data update

### Cacheable Resources

- Borrow rates: Cached for 5 minutes
- Volatility data: Cached for 15 minutes
- Event risk data: Cached for 1 hour
- Configuration data: Cached for 30 minutes

### Cache Control

Clients can control caching behavior with query parameters:
- `use_cache=false`: Bypass cache and fetch fresh data
- `max_age=<seconds>`: Override default cache duration

### Conditional Requests

Clients can use conditional requests to avoid unnecessary data transfer:
- `If-None-Match`: ETag-based conditional request
- `If-Modified-Since`: Time-based conditional request

## Rate Limiting

### Rate Limit Headers

All responses include rate limit headers:
- `X-RateLimit-Limit`: Total requests allowed in the current window
- `X-RateLimit-Remaining`: Requests remaining in the current window
- `X-RateLimit-Reset`: Time in seconds until the limit resets

### Rate Limit Tiers

- Standard: 60 requests/minute
- Premium: 300 requests/minute
- Internal: 1000 requests/minute

### Exceeding Rate Limits

When a client exceeds their rate limit:
- Request is rejected with 429 Too Many Requests status
- Response includes Retry-After header indicating when to retry
- Error response includes details about the rate limit

### Best Practices

- Monitor rate limit headers in responses
- Implement exponential backoff when limits are exceeded
- Distribute requests evenly over time
- Consider upgrading to a higher tier for increased limits

## Pagination

### Pagination Parameters

Endpoints that return multiple items support pagination with query parameters:
- `skip`: Number of items to skip (default: 0)
- `limit`: Maximum number of items to return (default: 20, max: 100)

### Pagination Response

Paginated responses include metadata about the result set:
```json
{
  "status": "success",
  "items": [...],
  "pagination": {
    "total": 150,
    "skip": 20,
    "limit": 20,
    "has_more": true
  }
}
```

### Pagination Best Practices

- Use reasonable page sizes to balance performance and latency
- Implement cursor-based pagination for frequently changing data
- Cache paginated results when appropriate
- Include total count only when necessary

## Webhooks

### Webhook Registration

Clients can register webhook URLs to receive notifications about specific events:
- Rate changes exceeding thresholds
- System status changes
- Batch processing completion

### Webhook Payload

Webhook notifications use a consistent JSON format:
```json
{
  "event_type": "rate_change",
  "timestamp": "2023-10-15T14:30:22Z",
  "data": {
    "ticker": "AAPL",
    "previous_rate": 0.05,
    "new_rate": 0.07,
    "change_percentage": 40
  }
}
```

### Webhook Security

- Webhooks are signed with HMAC to verify authenticity
- Clients should validate the signature before processing
- Webhook URLs must use HTTPS
- Failed deliveries are retried with exponential backoff

## Client Integration Guidelines

### Getting Started

1. Register for an API key
2. Review the API documentation
3. Set up authentication
4. Implement error handling
5. Test in the sandbox environment

### Authentication Implementation

Include your API key in the X-API-Key header with every request:
```http
GET /api/v1/rates/AAPL HTTP/1.1
Host: api.example.com
X-API-Key: your-api-key
```

### Error Handling

- Implement comprehensive error handling for all API responses
- Use error codes for programmatic handling
- Implement retry logic with exponential backoff for transient errors
- Log detailed error information for troubleshooting

### Performance Optimization

- Use caching where appropriate
- Batch requests when possible
- Implement connection pooling
- Monitor rate limits and adjust request patterns
- Use conditional requests to reduce bandwidth

## API Clients and SDKs

### Official SDKs

- Python: `pip install borrow-rate-client`
- JavaScript: `npm install borrow-rate-client`
- Java: Available via Maven Central
- C#: Available via NuGet

### Community SDKs

- Ruby: `gem install borrow-rate-client`
- Go: `go get github.com/example/borrow-rate-client`
- PHP: Available via Composer

### Client Generation

Clients can be generated from the OpenAPI specification using tools like:
- OpenAPI Generator
- Swagger Codegen
- NSwag

## API Governance

### Change Management

- All API changes follow a formal change management process
- Breaking changes require a new API version
- Deprecation notices are provided 6 months in advance
- Changes are documented in the API changelog

### SLA and Support

- API availability: 99.95% uptime
- Response time: <100ms (p95)
- Support channels: Email, support portal, developer forum
- Support hours: 24/7 for critical issues, business hours for non-critical

### Monitoring and Metrics

- API usage metrics are available in the developer dashboard
- System status is published on a status page
- Scheduled maintenance is announced in advance
- Performance metrics are published quarterly

## Appendix

### Glossary

- **Borrow Rate**: The annualized percentage fee charged for borrowing securities
- **Locate Fee**: The total fee charged to a client for locating and borrowing securities
- **Easy-to-Borrow (ETB)**: Securities that are readily available for borrowing
- **Hard-to-Borrow (HTB)**: Securities that are difficult to borrow due to limited supply
- **Markup**: Additional percentage added by brokers to the base borrow rate

### API Changelog

**v1.0.0 (2023-10-01)**
- Initial release of the API

**v1.1.0 (2023-11-15)**
- Added custom rate calculation endpoint
- Added support for event risk factors
- Improved error messages for validation failures

### Related Documentation

- [OpenAPI Specification](../api/openapi.yaml)
- [Postman Collection](../api/postman_collection.json)
- Security Implementation: The API implements comprehensive security features including API key authentication, TLS encryption, rate limiting, and input validation
- Monitoring: The system includes extensive monitoring for API performance, availability, and error rates