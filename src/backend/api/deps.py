"""
Dependency injection module for the Borrow Rate & Locate Fee Pricing Engine API.
This module provides FastAPI dependency functions that can be injected into API endpoints to access database sessions, authentication, and various services required for fee calculations and data operations. It centralizes the creation and management of shared resources across API endpoints.
"""

import logging
from typing import Dict, Any

from fastapi import Depends, HTTPException, status, Request  # fastapi 0.103.0+
from sqlalchemy.orm import Session  # sqlalchemy 2.0.0+

from ..db.session import get_db, DatabaseSessionManager  # Import database session context manager
from ..core.auth import authenticate_request, get_api_key_from_header, APIKeyAuthenticator  # Import authentication function
from ..services.data.stocks import StockService  # Import stock data service
from ..services.data.brokers import BrokerService  # Import broker data service
from ..services.calculation.borrow_rate import calculate_borrow_rate  # Import borrow rate calculation function
from ..services.calculation.locate_fee import calculate_locate_fee  # Import locate fee calculation function
from ..services.cache.redis import RedisCache  # Import Redis cache client
from ..core.exceptions import AuthenticationException, RateLimitExceededException  # Import authentication exception class
from ..config.settings import get_settings  # Import function to access application settings

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize global instances
db_session_manager = DatabaseSessionManager()
api_key_authenticator = APIKeyAuthenticator()
stock_service = StockService()
broker_service = BrokerService()
redis_cache = RedisCache()


def get_db_session() -> Session:
    """
    Dependency function that provides a database session

    Returns:
        Session: SQLAlchemy database session
    """
    # Use the db_session_manager to get a database session
    with db_session_manager.get_session() as session:
        # Yield the session to the endpoint
        yield session
        # Session is automatically closed after the endpoint execution


def get_auth_from_request(request: Request) -> Dict[str, Any]:
    """
    Dependency function that authenticates the request and returns client information

    Args:
        request: request

    Returns:
        dict: Authentication result with client_id and rate limit information
    """
    # Extract API key from request headers using get_api_key_from_header
    api_key = get_api_key_from_header(request)

    # If no API key found, raise HTTPException with 401 status code
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    try:
        # Authenticate the request using api_key_authenticator
        auth_result = api_key_authenticator.authenticate_request(request)
        # Return authentication result with client_id
        return auth_result
    except AuthenticationException as auth_exc:
        # If authentication fails, catch AuthenticationException and raise HTTPException
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=auth_exc.message
        )
    except RateLimitExceededException as rate_exc:
        # If rate limit exceeded, catch RateLimitExceededException and raise HTTPException with 429 status code
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=rate_exc.message,
            headers={"Retry-After": str(rate_exc.params.get("retry_after", 60))}
        )


def get_client_id(auth_result: Dict[str, Any]) -> str:
    """
    Dependency function that extracts the client ID from the authenticated request

    Args:
        auth_result: auth_result

    Returns:
        str: Client ID from the authentication result
    """
    # Extract client_id from the auth_result dictionary
    client_id = auth_result.get("client_id")

    # If client_id not found, raise HTTPException with 401 status code
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Client ID not found in authentication result"
        )

    # Return the client_id
    return client_id


def get_stock_service() -> StockService:
    """
    Dependency function that provides the stock service

    Returns:
        StockService: Stock data service instance
    """
    # Return the global stock_service instance
    return stock_service


def get_broker_service() -> BrokerService:
    """
    Dependency function that provides the broker service

    Returns:
        BrokerService: Broker data service instance
    """
    # Return the global broker_service instance
    return broker_service


def get_redis_cache() -> RedisCache:
    """
    Dependency function that provides the Redis cache client

    Returns:
        RedisCache: Redis cache client instance
    """
    # Return the global redis_cache instance
    return redis_cache


def get_settings_dependency():
    """
    Dependency function that provides application settings

    Returns:
        Settings: Application settings object
    """
    # Call get_settings() to retrieve application settings
    settings = get_settings()
    # Return the settings object
    return settings


async def get_broker_config(
    client_id: str,
    broker_service: BrokerService = Depends(get_broker_service)
) -> Dict[str, Any]:
    """
    Dependency function that retrieves broker configuration by client ID

    Args:
        client_id: client_id
        broker_service: broker_service

    Returns:
        dict: Broker configuration with markup and fee settings
    """
    try:
        # Use broker_service to get broker configuration by client_id
        broker_config = broker_service.get_broker(client_id)
        # Return the broker configuration
        return broker_config
    except Exception as e:
        # If broker not found, catch ClientNotFoundException and raise HTTPException with 404 status code
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )