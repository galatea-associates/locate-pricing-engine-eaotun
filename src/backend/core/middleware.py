"""
Central middleware configuration module for the Borrow Rate & Locate Fee Pricing Engine.

This module provides a unified interface for setting up all middleware components in the correct order,
ensuring proper request processing flow through authentication, logging, rate limiting, error handling,
and distributed tracing layers.
"""

from fastapi import FastAPI  # fastapi 0.103.0
from fastapi.middleware.cors import CORSMiddleware  # fastapi 0.103.0
from fastapi.middleware.gzip import GZipMiddleware  # fastapi 0.103.0
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware  # fastapi 0.103.0
from fastapi.middleware.trustedhost import TrustedHostMiddleware  # fastapi 0.103.0

from ..middleware.authentication import AuthenticationMiddleware
from ..middleware.logging import LoggingMiddleware
from ..middleware.error_handling import ErrorHandlingMiddleware
from ..middleware.rate_limiting import RateLimitingMiddleware
from ..middleware.tracing import TracingMiddleware

from ..config.settings import get_settings
from ..utils.logging import setup_logger

# Set up logger
logger = setup_logger('core.middleware')


def setup_middleware(app: FastAPI) -> FastAPI:
    """
    Configure and add all middleware to the FastAPI application in the correct order.
    
    Args:
        app: The FastAPI application to configure
        
    Returns:
        FastAPI: The FastAPI application with middleware configured
    """
    # Get application settings
    settings = get_settings()
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=getattr(settings, 'cors_origins', ["*"]),
        allow_credentials=getattr(settings, 'cors_allow_credentials', True),
        allow_methods=getattr(settings, 'cors_allow_methods', ["*"]),
        allow_headers=getattr(settings, 'cors_allow_headers', ["*"]),
    )
    logger.info("CORS middleware added")
    
    # Add GZip middleware for response compression if enabled
    if getattr(settings, 'enable_gzip', False):
        app.add_middleware(GZipMiddleware, minimum_size=1000)
        logger.info("GZip middleware added for response compression")
    
    # Add HTTPS redirect middleware if in production
    if settings.is_production():
        app.add_middleware(HTTPSRedirectMiddleware)
        logger.info("HTTPS redirect middleware added (production environment)")
    
    # Add trusted host middleware if enabled
    allowed_hosts = getattr(settings, 'allowed_hosts', None)
    if allowed_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts
        )
        logger.info(f"Trusted host middleware added with allowed hosts: {allowed_hosts}")
    
    # Get exempt paths
    exempt_paths = get_exempt_paths()
    
    # Add custom middleware in specific order
    
    # Add tracing middleware (first, to capture entire request flow)
    app.add_middleware(TracingMiddleware, exempt_paths=exempt_paths)
    logger.info("Tracing middleware added")
    
    # Add error handling middleware (next, to catch errors from other middleware)
    app.add_middleware(ErrorHandlingMiddleware)
    logger.info("Error handling middleware added")
    
    # Add authentication middleware
    app.add_middleware(AuthenticationMiddleware, exempt_paths=exempt_paths)
    logger.info("Authentication middleware added")
    
    # Add rate limiting middleware
    app.add_middleware(RateLimitingMiddleware, exempt_paths=exempt_paths)
    logger.info("Rate limiting middleware added")
    
    # Add logging middleware
    app.add_middleware(LoggingMiddleware, exempt_paths=exempt_paths)
    logger.info("Logging middleware added")
    
    # Instrument the app with OpenTelemetry if tracing is enabled
    if getattr(settings, 'tracing_enabled', True):
        tracing_middleware = TracingMiddleware()
        tracing_middleware.instrument_app(app)
        logger.info("App instrumented with OpenTelemetry")
    
    logger.info("All middleware components configured successfully")
    return app


def get_exempt_paths() -> list:
    """
    Get the list of paths exempt from authentication and rate limiting.
    
    Returns:
        list: List of path prefixes that are exempt from middleware processing
    """
    # Default exempt paths
    default_exempt_paths = [
        '/health',
        '/docs',
        '/redoc',
        '/openapi.json',
        '/metrics',
    ]
    
    # Get settings
    settings = get_settings()
    
    # Get custom exempt paths from settings
    custom_exempt_paths = getattr(settings, 'exempt_paths', [])
    
    # Combine default and custom exempt paths
    exempt_paths = default_exempt_paths.copy()
    if custom_exempt_paths:
        exempt_paths.extend(custom_exempt_paths)
        logger.debug(f"Added custom exempt paths: {custom_exempt_paths}")
    
    return exempt_paths