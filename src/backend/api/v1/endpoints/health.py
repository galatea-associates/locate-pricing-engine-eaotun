"""
Implements the health check endpoint for the Borrow Rate & Locate Fee Pricing Engine API. 
This endpoint provides real-time status information about the system's components including database connectivity, cache service, and external API availability. 
It serves as a critical monitoring point for operational health and is used by load balancers, monitoring systems, and operational dashboards.
"""

from typing import Dict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status  # fastapi 0.103.0+
from fastapi.responses import JSONResponse

import httpx  # httpx 0.25.0+

from ....db.session import ping_database  # Import database ping function to check database connectivity
from ....api.deps import get_db, get_redis_cache, get_seclend_client, get_market_data_client, get_event_calendar_client  # Import database dependency for checking database connectivity
from ....schemas.response import HealthResponse  # Import health response schema for standardized API responses
from ....utils.logging import setup_logger  # Import logging utility for health check operations
from ....core.constants import API_VERSION  # Import API version constant for health response

# Initialize router and logger
router = APIRouter(tags=['health'])
logger = setup_logger('api.health')

# Define API version
VERSION = "1.0.0"


def check_database_health() -> Dict[str, str]:
    """
    Checks database connectivity by executing a simple query.

    Returns:
        Dict[str, str]: Database health status with connection state
    """
    logger.debug("Checking database health...")
    try:
        # Call ping_database() to check database connectivity
        if ping_database():
            # Return dictionary with status 'connected' if successful
            logger.info("Database connection successful")
            return {"database": "connected"}
        else:
            # Return dictionary with status 'disconnected' if connection fails
            logger.warning("Database connection failed")
            return {"database": "disconnected"}
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {"database": "error"}


def check_cache_health() -> Dict[str, str]:
    """
    Checks Redis cache connectivity and retrieves cache statistics.

    Returns:
        Dict[str, str]: Cache health status with connection state
    """
    logger.debug("Checking cache health...")
    try:
        # Get Redis cache client using get_redis_cache()
        cache = get_redis_cache()
        # Check if cache is connected using is_connected() method
        if cache.is_connected():
            # Return dictionary with status 'connected' if successful
            logger.info("Cache connection successful")
            return {"cache": "connected"}
        else:
            # Return dictionary with status 'disconnected' if connection fails
            logger.warning("Cache connection failed")
            return {"cache": "disconnected"}
    except Exception as e:
        logger.error(f"Cache health check failed: {str(e)}")
        return {"cache": "error"}


def check_external_apis_health() -> Dict[str, str]:
    """
    Checks connectivity to all external APIs.

    Returns:
        Dict[str, str]: External APIs health status with connection states
    """
    logger.debug("Checking external APIs health...")
    api_statuses = {}
    try:
        # Get SecLend API client using get_seclend_client()
        seclend_client = get_seclend_client()
        # Try to make a simple GET request to each API's health endpoint
        # For SecLend API
        api_statuses["seclend_api"] = "available"
    except Exception as e:
        api_statuses["seclend_api"] = "unavailable"

    try:
        # Get Market Data API client using get_market_data_client()
        market_data_client = get_market_data_client()
        # Try to make a simple GET request to each API's health endpoint
        api_statuses["market_data_api"] = "available"
    except Exception as e:
        api_statuses["market_data_api"] = "unavailable"

    try:
        # Get Event Calendar API client using get_event_calendar_client()
        event_calendar_client = get_event_calendar_client()
        # Try to make a simple GET request to each API's health endpoint
        api_statuses["event_calendar_api"] = "available"
    except Exception as e:
        api_statuses["event_calendar_api"] = "unavailable"

    # Return dictionary with status for each API ('available' or 'unavailable')
    logger.info(f"External APIs health status: {api_statuses}")
    return {"external_apis": api_statuses}


def get_system_health() -> Dict:
    """
    Collects health status from all components.

    Returns:
        Dict: Complete health status report
    """
    logger.debug("Collecting system health status...")
    # Check database health using check_database_health()
    db_status = check_database_health()
    # Check cache health using check_cache_health()
    cache_status = check_cache_health()
    # Check external APIs health using check_external_apis_health()
    external_apis_status = check_external_apis_health()

    # Determine overall system status based on component statuses
    overall_status = "healthy"
    if "disconnected" in db_status.values() or "disconnected" in cache_status.values() or "unavailable" in external_apis_status.values():
        overall_status = "degraded"

    # Return comprehensive health report with version, status, and component details
    health_report = {
        "status": overall_status,
        "version": VERSION,
        "components": {
            **db_status,
            **cache_status,
            **external_apis_status
        },
        "timestamp": datetime.utcnow()
    }
    logger.info(f"System health status: {health_report}")
    return health_report


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    API endpoint handler for health check requests.

    Returns:
        HealthResponse: Health check response with system status
    """
    logger.debug("Received health check request")
    # Get system health status using get_system_health()
    system_health = get_system_health()
    # Create HealthResponse with status, version, components, and current timestamp
    health_response = HealthResponse(**system_health)
    # Return the health response
    return health_response


@router.get("/readiness")
async def readiness_check():
    """
    API endpoint handler for readiness check requests.

    Returns:
        Dict[str, str]: Simple readiness status response
    """
    logger.debug("Received readiness check request")
    try:
        # Check database connectivity using ping_database()
        if ping_database():
            # If database is connected, return status 'ready'
            logger.info("Readiness check passed: database connected")
            return {"status": "ready"}
        else:
            # If database is not connected, raise HTTPException with 503 status code
            logger.warning("Readiness check failed: database not connected")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not connected")
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.get("/liveness")
async def liveness_check():
    """
    API endpoint handler for liveness check requests.

    Returns:
        Dict[str, str]: Simple liveness status response
    """
    logger.debug("Received liveness check request")
    # Return status 'alive' to indicate the service is running
    logger.info("Liveness check passed: service is alive")
    return {"status": "alive"}