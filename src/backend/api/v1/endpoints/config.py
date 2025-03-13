"""
API endpoint module for exposing system configuration information. This module provides endpoints for retrieving public configuration settings such as API version, supported features, rate limits, and other non-sensitive configuration details that clients may need to properly interact with the Borrow Rate & Locate Fee Pricing Engine.
"""

from typing import Dict  # standard library
from fastapi import APIRouter, Depends  # fastapi 0.103.0+
from src.backend.config.settings import get_settings  # Access application configuration settings
from src.backend.schemas.response import ConfigResponse  # Response model for configuration endpoint
from src.backend.api.deps import authenticate_api_key  # Authenticate API requests using API key
from src.backend.core.constants import API_RATE_LIMIT_DEFAULT, API_RATE_LIMIT_PREMIUM  # Default API rate limit constant

# Create and configure API router for config endpoints
router = APIRouter(tags=['Configuration'])


@router.get('/config', response_model=ConfigResponse)
@router.get('/config/', response_model=ConfigResponse)
def get_public_config(client_id: str = Depends(authenticate_api_key)) -> ConfigResponse:
    """
    Endpoint to retrieve public configuration information

    Args:
        client_id (str): The authenticated client ID, obtained from the API key.

    Returns:
        ConfigResponse: Configuration response with public settings
    """
    # Get application settings using get_settings()
    settings = get_settings()

    # Create configuration dictionary with API version
    config = {
        "api_version": {
            "current": settings.api_version,
            "deprecated": []  # Add deprecated versions if any
        },
        "supported_features": {
            "rate_calculation": True,
            "fee_proration": True  # Example feature
        },
        "rate_limits": {
            "standard": API_RATE_LIMIT_DEFAULT,
            "premium": API_RATE_LIMIT_PREMIUM
        },
        "cache_ttls": {
            "borrow_rate": settings.cache_ttls.get("borrow_rate"),
            "volatility": settings.cache_ttls.get("volatility"),
            "event_risk": settings.cache_ttls.get("event_risk"),
            "broker_config": settings.cache_ttls.get("broker_config"),
            "calculation": settings.cache_ttls.get("calculation")
        }
    }

    # Return ConfigResponse with status='success' and config dictionary
    return ConfigResponse(status='success', config=config)


# Export the router for inclusion in the main API
__all__ = ["router"]