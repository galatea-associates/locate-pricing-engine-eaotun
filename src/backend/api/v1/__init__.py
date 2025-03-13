"""
Initialization module for the v1 API package of the Borrow Rate & Locate Fee Pricing Engine.
This module serves as the entry point for version 1 of the API, importing and re-exporting the main API router with all configured endpoints. It enables clean imports of the API router in the main application.
"""

import logging  # standard library
from fastapi import APIRouter  # fastapi 0.103.0+
from .api import api_router  # Internal imports
from ...core.constants import API_VERSION  # Internal imports
from ...utils.logging import setup_logger  # Internal imports

# Initialize logger for this module
logger = setup_logger('api.v1')

# Export the configured v1 API router for use in the main FastAPI application
__all__ = ["api_router"]