"""
Core authentication module for the Borrow Rate & Locate Fee Pricing Engine.

This module provides functions for authenticating API requests, validating API keys,
managing rate limits, and handling authentication-related operations. It serves
as the central component of the application's authentication framework.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

from fastapi import Request  # fastapi 0.103.0

from .security import (
    verify_api_key,
    get_client_for_api_key,
    create_access_token,
    decode_access_token
)
from .exceptions import AuthenticationException, RateLimitExceededException
from .constants import ErrorCodes
from ..utils.logging import setup_logger
from ..services.cache.redis import RedisCache
from ..db.crud.api_keys import api_keys

# Set up module logger
logger = setup_logger('core.auth')

# Initialize Redis cache for rate limiting
redis_cache = RedisCache()


def get_api_key_from_header(request: Request) -> Optional[str]:
    """
    Extracts the API key from the request headers.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        Optional[str]: The API key if found in headers, None otherwise
    """
    api_key = request.headers.get("X-API-Key")
    if api_key:
        logger.debug("API key found in request headers")
        return api_key
    
    logger.warning("No API key found in request headers")
    return None


def authenticate_request(api_key: str, client_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Authenticates a request using the provided API key and checks rate limits.
    
    Args:
        api_key: The API key to validate
        client_id: Optional client ID if already known
        
    Returns:
        Dict[str, Any]: Authentication result with client_id and rate limit information
        
    Raises:
        AuthenticationException: If the API key is invalid
        RateLimitExceededException: If the client has exceeded their rate limit
    """
    # Verify the API key
    if not verify_api_key(api_key):
        logger.warning("Authentication failed: Invalid API key")
        raise AuthenticationException("Invalid API key", ErrorCodes.UNAUTHORIZED)
    
    # Get the client ID associated with the API key if not provided
    if not client_id:
        client_id = get_client_for_api_key(api_key)
        if not client_id:
            logger.error("Authentication anomaly: Valid API key but no client_id")
            raise AuthenticationException("Invalid API key", ErrorCodes.UNAUTHORIZED)
    
    # Check rate limits for the client
    rate_limit_info = check_rate_limit(client_id)
    
    # If remaining requests is 0, rate limit has been exceeded
    if rate_limit_info.get("remaining", 0) <= 0:
        retry_after = rate_limit_info.get("reset", 60)
        logger.warning(f"Rate limit exceeded for client {client_id}")
        raise RateLimitExceededException(client_id, retry_after)
    
    # Update rate limit counter
    current_window = int(time.time() / 60)  # Current minute window
    updated_count = update_rate_limit_counter(client_id, current_window)
    
    # Update remaining requests in rate limit info
    rate_limit_info["remaining"] = max(0, rate_limit_info["limit"] - updated_count)
    
    logger.info(f"Authentication successful for client: {client_id}")
    
    return {
        "client_id": client_id,
        "rate_limit": rate_limit_info
    }


def check_rate_limit(client_id: str) -> Dict[str, Any]:
    """
    Checks if a client has exceeded their API rate limit.
    
    Args:
        client_id: The client's unique identifier
        
    Returns:
        Dict[str, Any]: Rate limit information including limit, remaining, and reset time
        
    Raises:
        RateLimitExceededException: If the client has exceeded their rate limit
    """
    # Get the rate limit for the client
    rate_limit = get_rate_limit_for_client(client_id)
    
    # Calculate the current time window (minute-based)
    current_window = int(time.time() / 60)
    
    # Create Redis key for the client's rate limit counter
    rate_limit_key = f"rate_limit:{client_id}:{current_window}"
    
    # Get the current counter value from Redis
    counter = redis_cache.get(rate_limit_key)
    if counter is None:
        # Initialize to 0 if counter doesn't exist
        counter = 0
    
    # Check if the counter exceeds the rate limit
    if counter >= rate_limit:
        # Calculate time until the rate limit resets (in seconds)
        reset_time = 60 - (int(time.time()) % 60)
        
        logger.warning(f"Rate limit exceeded for client {client_id}: {counter}/{rate_limit}")
        
        # Return rate limit information
        return {
            "limit": rate_limit,
            "remaining": 0,
            "reset": reset_time
        }
    
    # Calculate remaining requests
    remaining = rate_limit - counter
    
    # Calculate time until the rate limit resets (in seconds)
    reset_time = 60 - (int(time.time()) % 60)
    
    logger.debug(f"Rate limit check for client {client_id}: {counter}/{rate_limit}")
    
    # Return rate limit information
    return {
        "limit": rate_limit,
        "remaining": remaining,
        "reset": reset_time
    }


def update_rate_limit_counter(client_id: str, window: int) -> int:
    """
    Updates the rate limit counter for a client.
    
    Args:
        client_id: The client's unique identifier
        window: The current time window (minute-based)
        
    Returns:
        int: The updated counter value
    """
    # Create Redis key for the client's rate limit counter
    rate_limit_key = f"rate_limit:{client_id}:{window}"
    
    # Increment the counter in Redis
    counter = redis_cache.get(rate_limit_key)
    if counter is None:
        counter = 1
        redis_cache.set(rate_limit_key, counter, 60)  # Expire after 60 seconds (1 minute)
    else:
        counter += 1
        redis_cache.set(rate_limit_key, counter, 60)
    
    logger.debug(f"Updated rate limit counter for client {client_id}: {counter}")
    
    return counter


def get_rate_limit_for_client(client_id: str) -> int:
    """
    Gets the rate limit configuration for a client.
    
    Args:
        client_id: The client's unique identifier
        
    Returns:
        int: The rate limit for the client
    """
    try:
        # Query the database for client-specific rate limit
        api_key_record = api_keys.get_by_client_id(client_id)
        if api_key_record:
            # Get the rate limit from the first active API key for this client
            rate_limit = api_key_record.rate_limit
            logger.debug(f"Using database rate limit for client {client_id}: {rate_limit}")
            return rate_limit
        
        # If not found in database, check settings
        from ..config.settings import get_settings
        settings = get_settings()
        
        # Check if there's an API key configuration with this client ID
        for key, config in settings.api_keys.items():
            if config.get("client_id") == client_id:
                rate_limit = config.get("rate_limit")
                if rate_limit:
                    logger.debug(f"Using configured rate limit for client {client_id}: {rate_limit}")
                    return rate_limit
        
        # If not found, use default rate limit
        from .constants import API_RATE_LIMIT_DEFAULT, API_RATE_LIMIT_PREMIUM
        
        # Check if client is a premium client
        is_premium = False  # Replace with actual check
        
        if is_premium:
            logger.debug(f"Using premium rate limit for client {client_id}: {API_RATE_LIMIT_PREMIUM}")
            return API_RATE_LIMIT_PREMIUM
        else:
            logger.debug(f"Using default rate limit for client {client_id}: {API_RATE_LIMIT_DEFAULT}")
            return API_RATE_LIMIT_DEFAULT
            
    except Exception as e:
        logger.error(f"Error getting rate limit for client {client_id}: {str(e)}")
        # Fall back to default rate limit
        from .constants import API_RATE_LIMIT_DEFAULT
        return API_RATE_LIMIT_DEFAULT


def create_auth_token(client_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates an authentication token for a client.
    
    Args:
        client_id: The client's unique identifier
        expires_delta: Optional custom expiration time
        
    Returns:
        str: JWT access token
    """
    # Create token data with client_id claim
    token_data = {
        "sub": client_id,
        "client_id": client_id,
        "token_type": "access"
    }
    
    # Create JWT token with appropriate expiration
    token = create_access_token(token_data, expires_delta)
    
    logger.info(f"Created authentication token for client {client_id}")
    
    return token


def validate_auth_token(token: str) -> Dict[str, Any]:
    """
    Validates an authentication token.
    
    Args:
        token: JWT token to validate
        
    Returns:
        Dict[str, Any]: Decoded token payload
        
    Raises:
        AuthenticationException: If the token is invalid
    """
    # Decode and validate the token
    payload = decode_access_token(token)
    
    # Verify the token contains required claims
    if "client_id" not in payload:
        logger.warning("Token validation failed: missing client_id claim")
        raise AuthenticationException("Invalid token format", ErrorCodes.UNAUTHORIZED)
    
    logger.info(f"Validated authentication token for client {payload.get('client_id')}")
    
    return payload


class RateLimiter:
    """
    Implements token bucket algorithm for API rate limiting.
    """
    
    def __init__(self, redis_cache: Optional[RedisCache] = None):
        """
        Initialize the rate limiter with Redis cache.
        
        Args:
            redis_cache: Optional Redis cache instance, uses global instance if not provided
        """
        self._redis_cache = redis_cache or globals()["redis_cache"]
        logger.debug("Rate limiter initialized")
    
    def check_rate_limit(self, client_id: str, limit: int) -> Dict[str, Any]:
        """
        Check if a client has exceeded their rate limit.
        
        Args:
            client_id: The client's unique identifier
            limit: Rate limit (requests per minute)
            
        Returns:
            Dict[str, Any]: Rate limit information
        """
        # Calculate the current time window (minute-based)
        current_window = self.get_window()
        
        # Create Redis key for the client's rate counter
        rate_limit_key = f"rate_limit:{client_id}:{current_window}"
        
        # Get the current counter value from Redis
        counter = self._redis_cache.get(rate_limit_key)
        if counter is None:
            counter = 0
        
        # Check if the counter exceeds the limit
        if counter >= limit:
            # Calculate time until the rate limit resets (in seconds)
            reset_time = 60 - (int(time.time()) % 60)
            
            logger.warning(f"Rate limit exceeded for client {client_id}: {counter}/{limit}")
            
            # Return rate limit information
            return {
                "limit": limit,
                "remaining": 0,
                "reset": reset_time,
                "exceeded": True
            }
        
        # Calculate remaining requests
        remaining = limit - counter
        
        # Calculate time until the rate limit resets (in seconds)
        reset_time = 60 - (int(time.time()) % 60)
        
        logger.debug(f"Rate limit check for client {client_id}: {counter}/{limit}")
        
        # Return rate limit information
        return {
            "limit": limit,
            "remaining": remaining,
            "reset": reset_time,
            "exceeded": False
        }
    
    def increment_counter(self, client_id: str, window: int) -> int:
        """
        Increment the request counter for a client.
        
        Args:
            client_id: The client's unique identifier
            window: The current time window (minute-based)
            
        Returns:
            int: Updated counter value
        """
        # Create Redis key for the client's rate limit counter
        rate_limit_key = f"rate_limit:{client_id}:{window}"
        
        # Increment the counter in Redis
        counter = self._redis_cache.get(rate_limit_key)
        if counter is None:
            counter = 1
            self._redis_cache.set(rate_limit_key, counter, 60)  # Expire after 60 seconds (1 minute)
        else:
            counter += 1
            self._redis_cache.set(rate_limit_key, counter, 60)
        
        logger.debug(f"Incremented rate limit counter for client {client_id}: {counter}")
        
        return counter
    
    def get_window(self) -> int:
        """
        Calculate the current time window for rate limiting.
        
        Returns:
            int: Current minute-based time window
        """
        return int(time.time() / 60)


class APIKeyAuthenticator:
    """
    Handles API key authentication and management.
    """
    
    def __init__(self):
        """
        Initialize the API key authenticator.
        """
        self._rate_limiter = RateLimiter()
        logger.debug("API Key authenticator initialized")
    
    def authenticate(self, api_key: str) -> Dict[str, Any]:
        """
        Authenticate a request using an API key.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Dict[str, Any]: Authentication result with client_id
            
        Raises:
            AuthenticationException: If the API key is invalid
            RateLimitExceededException: If the client has exceeded their rate limit
        """
        # Validate the API key using database
        api_key_record = api_keys.authenticate(api_key)
        if not api_key_record:
            logger.warning("Authentication failed: Invalid API key")
            raise AuthenticationException("Invalid API key", ErrorCodes.UNAUTHORIZED)
        
        # Get the client ID associated with the API key
        client_id = api_key_record.get("client_id")
        if not client_id:
            logger.error("Authentication anomaly: Valid API key record but no client_id")
            raise AuthenticationException("Invalid API key configuration", ErrorCodes.UNAUTHORIZED)
        
        # Get rate limit for the client
        rate_limit = api_key_record.get("rate_limit", get_rate_limit_for_client(client_id))
        
        # Check rate limits for the client
        rate_limit_info = self._rate_limiter.check_rate_limit(client_id, rate_limit)
        
        # If rate limit exceeded, raise exception
        if rate_limit_info.get("exceeded", False):
            retry_after = rate_limit_info.get("reset", 60)
            logger.warning(f"Rate limit exceeded for client {client_id}")
            raise RateLimitExceededException(client_id, retry_after)
        
        # Update rate limit counter
        current_window = self._rate_limiter.get_window()
        updated_count = self._rate_limiter.increment_counter(client_id, current_window)
        
        # Update remaining requests in rate limit info
        rate_limit_info["remaining"] = max(0, rate_limit_info["limit"] - updated_count)
        
        logger.info(f"Authentication successful for client: {client_id}")
        
        return {
            "client_id": client_id,
            "rate_limit": rate_limit_info
        }
    
    def authenticate_request(self, request: Request) -> Dict[str, Any]:
        """
        Authenticate a request object.
        
        Args:
            request: The FastAPI request object
            
        Returns:
            Dict[str, Any]: Authentication result with client_id
            
        Raises:
            AuthenticationException: If the API key is invalid or missing
            RateLimitExceededException: If the client has exceeded their rate limit
        """
        # Extract API key from request headers
        api_key = get_api_key_from_header(request)
        if not api_key:
            logger.warning("Authentication failed: No API key provided")
            raise AuthenticationException("API key required", ErrorCodes.UNAUTHORIZED)
        
        # Authenticate using the API key
        auth_result = self.authenticate(api_key)
        
        logger.info(f"Request authenticated for client: {auth_result.get('client_id')}")
        
        return auth_result
    
    def create_auth_token(self, client_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create an authentication token for a client.
        
        Args:
            client_id: The client's unique identifier
            expires_delta: Optional custom expiration time
            
        Returns:
            str: JWT access token
        """
        return create_auth_token(client_id, expires_delta)