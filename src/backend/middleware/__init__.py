"""
Initialization module for the middleware package in the Borrow Rate & Locate Fee Pricing Engine.

This module exports all middleware components for easy access throughout the application,
providing a centralized point for importing middleware classes used in request processing.

Middleware components:
- AuthenticationMiddleware: Handles API key validation and authentication for API requests
- LoggingMiddleware: Logs request/response information with timing and correlation IDs
- ErrorHandlingMiddleware: Converts exceptions to standardized error responses
- RateLimitingMiddleware: Enforces rate limits for API clients
- TracingMiddleware: Adds distributed tracing for request flows using OpenTelemetry
"""

from .authentication import AuthenticationMiddleware
from .logging import LoggingMiddleware
from .error_handling import ErrorHandlingMiddleware
from .rate_limiting import RateLimitingMiddleware
from .tracing import TracingMiddleware

__all__ = [
    'AuthenticationMiddleware',
    'LoggingMiddleware',
    'ErrorHandlingMiddleware',
    'RateLimitingMiddleware',
    'TracingMiddleware',
]