"""
Initialization module for the API package of the Borrow Rate & Locate Fee Pricing Engine.
This module serves as the entry point for the API layer, importing and re-exporting key
components from submodules to provide a clean interface for the main application.
"""

import logging  # standard library
from fastapi import APIRouter  # fastapi 0.103.0+

from .v1.api import api_router  # Import the configured API router for v1 of the API
from ..utils.logging import setup_logger  # Import function to set up logger for the API module

# Initialize logger for this module
logger = setup_logger('api')

# Export the configured v1 API router for use in the main FastAPI application
__all__ = ["api_router"]