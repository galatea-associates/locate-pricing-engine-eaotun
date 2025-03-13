"""
Central API router configuration for version 1 of the Borrow Rate & Locate Fee Pricing Engine API.
This module aggregates all endpoint routers from different modules and configures them under a unified API router with proper prefixes, tags, and dependencies. It serves as the main entry point for all API requests in the v1 namespace.
"""

import logging  # Standard library for logging
from fastapi import APIRouter, Depends  # fastapi 0.103.0+ - Import FastAPI's APIRouter and Depends for creating and configuring API routes
from .endpoints import health, rates, calculate, config  # Internal imports - Import endpoint-specific routers
from ..deps import authenticate_api_key  # Internal imports - Import authentication dependency for API endpoints
from ...core.constants import API_VERSION  # Internal imports - Import API version constant for versioning information
from ...utils.logging import setup_logger  # Internal imports - Import function to set up logger for the API module
from ...core.middleware import get_exempt_paths  # Internal imports - Import function to get paths exempt from authentication

# Initialize logger for this module
logger = setup_logger('api.v1')

# Create an APIRouter instance with a prefix for all routes in this router
api_router = APIRouter(prefix='/api/v1')


def configure_routes():
    """
    Configures all endpoint routers with the main API router
    """
    # Get exempt paths using get_exempt_paths() function
    exempt_paths = get_exempt_paths()

    # Include health router without authentication dependency
    api_router.include_router(health.router)

    # Include rates router with authentication dependency
    api_router.include_router(rates.router, dependencies=[Depends(authenticate_api_key)])

    # Include calculate router with authentication dependency
    api_router.include_router(calculate.router, dependencies=[Depends(authenticate_api_key)])

    # Include config router with authentication dependency
    api_router.include_router(config.router, dependencies=[Depends(authenticate_api_key)])

    # Log successful router configuration
    logger.info("API v1 router configured with all endpoints")


# Call configure_routes to set up the routes
configure_routes()

# Export the router for use in the main FastAPI application
__all__ = ["api_router"]