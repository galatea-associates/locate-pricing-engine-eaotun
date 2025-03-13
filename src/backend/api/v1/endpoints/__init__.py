"""
Initialization module for the API endpoints package in the Borrow Rate & Locate Fee Pricing Engine.
This module exports the router objects from each endpoint module, making them available for import in the API router configuration. It serves as a central point for organizing and exposing all API endpoint routers.
"""

from fastapi import APIRouter  # fastapi 0.103.0+

from .health import router as health_router  # Import health check endpoints router
from .rates import router as rates_router  # Import borrow rates endpoints router
from .calculate import router as calculate_router  # Import fee calculation endpoints router
from .config import router as config_router  # Import configuration endpoints router

__all__ = [
    "health_router",  # Export health check endpoints router for API configuration
    "rates_router",  # Export borrow rates endpoints router for API configuration
    "calculate_router",  # Export fee calculation endpoints router for API configuration
    "config_router",  # Export configuration endpoints router for API configuration
]