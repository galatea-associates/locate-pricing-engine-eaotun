"""
Middleware for rate limiting in the Borrow Rate & Locate Fee Pricing Engine API.

This middleware enforces request rate limits based on client configurations,
using a token bucket algorithm with Redis for distributed counter management.
It ensures fair resource allocation, prevents API abuse, and provides appropriate
feedback to clients when limits are exceeded.
"""

import time
from typing import List, Dict, Optional, Any, Callable

from fastapi import Request, Response, HTTPException, status  # fastapi 0.103.0+

from ..core.auth import RateLimiter
from ..services.cache.redis import RedisCache
from ..core.exceptions import RateLimitExceededException
from ..core.constants import ErrorCodes, API_RATE_LIMIT_DEFAULT, API_RATE_LIMIT_PREMIUM
from ..core.errors import get_error_message, create_error_response
from ..utils.logging import setup_logger
from ..config.settings import get_settings

# Set up logger
logger = setup_logger('middleware.rate_limiting')
# Initialize Redis cache
redis_cache = RedisCache()
# Initialize rate limiter
rate_limiter = RateLimiter(redis_cache)


class RateLimitingMiddleware:
    """Middleware for enforcing API rate limits based on client configuration"""

    def __init__(self, exempt_paths: Optional[List[str]] = None):
        """
        Initialize the rate limiting middleware with optional exempt paths.
        
        Args:
            exempt_paths: List of URL paths that should be exempt from rate limiting
        """
        # Define default exempt paths if none provided
        self.exempt_paths = exempt_paths or ['/health', '/docs', '/openapi.json', '/redoc']
        # Store rate limiter instance
        self._rate_limiter = rate_limiter
        logger.info(f"Rate limiting middleware initialized with exempt paths: {self.exempt_paths}")
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request through the rate limiting middleware.
        
        Args:
            request: The incoming FastAPI request
            call_next: The next middleware or route handler
            
        Returns:
            Response: The response from the next middleware or route handler
        """
        # Check if the request path is exempt from rate limiting
        if self.is_path_exempt(request.url.path):
            logger.debug(f"Skipping rate limiting for exempt path: {request.url.path}")
            return await call_next(request)
        
        # Extract client ID from auth result if available
        client_id = None
        if hasattr(request.state, 'auth_result') and request.state.auth_result:
            client_id = request.state.auth_result.get('client_id')
        
        # Use client IP as fallback identifier if no client_id available
        if not client_id:
            client_id = request.client.host if request.client else "unknown"
            logger.debug(f"No client_id found, using IP address as identifier: {client_id}")
        
        try:
            # Check if the client has exceeded their rate limit
            rate_limit_info = self.check_rate_limit(client_id)
            
            # Process the request
            logger.debug(f"Rate limit check passed for client {client_id}: {rate_limit_info}")
            
            # Increment the counter before processing
            current_window = int(time.time() / 60)
            self._rate_limiter.increment_counter(client_id, current_window)
            
            # Call next middleware or route handler
            response = await call_next(request)
            
            # Add rate limit headers to the response
            response = self.add_rate_limit_headers(response, rate_limit_info)
            
            return response
            
        except RateLimitExceededException as e:
            # Create error response with retry-after information
            logger.warning(f"Rate limit exceeded for client {client_id}")
            error_message = get_error_message(
                ErrorCodes.RATE_LIMIT_EXCEEDED, 
                {"retry_after": e.params.get("retry_after", 60)}
            )
            error_response = create_error_response(
                error_message, 
                ErrorCodes.RATE_LIMIT_EXCEEDED, 
                {"client_id": client_id}
            )
            
            # Create HTTP exception with rate limit headers
            response = Response(
                content=error_response,
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json"
            )
            
            # Add rate limit headers to the response
            retry_after = e.params.get("retry_after", 60)
            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-RateLimit-Limit"] = str(self.get_client_rate_limit(client_id))
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + retry_after)
            
            return response
    
    def is_path_exempt(self, path: str) -> bool:
        """
        Check if a request path is exempt from rate limiting.
        
        Args:
            path: The URL path to check
            
        Returns:
            bool: True if the path is exempt, False otherwise
        """
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        return False
    
    def check_rate_limit(self, client_id: str) -> Dict[str, Any]:
        """
        Check if a client has exceeded their rate limit.
        
        Args:
            client_id: The client's unique identifier
            
        Returns:
            Dict[str, Any]: Rate limit information including limit, remaining, and reset time
            
        Raises:
            RateLimitExceededException: If rate limit is exceeded
        """
        # Get rate limit for the client
        rate_limit = self.get_client_rate_limit(client_id)
        
        # Check if client has exceeded their rate limit
        rate_limit_info = self._rate_limiter.check_rate_limit(client_id, rate_limit)
        
        # If rate limit exceeded, raise exception
        if rate_limit_info.get("exceeded", False):
            retry_after = rate_limit_info.get("reset", 60)
            logger.warning(f"Rate limit exceeded for client {client_id}: {rate_limit_info}")
            raise RateLimitExceededException(client_id, retry_after)
        
        logger.debug(f"Rate limit check for client {client_id}: {rate_limit_info}")
        return rate_limit_info
    
    def add_rate_limit_headers(self, response: Response, rate_limit_info: Dict[str, Any]) -> Response:
        """
        Add rate limit headers to the response.
        
        Args:
            response: The response object
            rate_limit_info: Dictionary with rate limit information
            
        Returns:
            Response: The response with added headers
        """
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info.get("limit", 0))
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info.get("remaining", 0))
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + rate_limit_info.get("reset", 60))
        
        return response
    
    def get_client_rate_limit(self, client_id: str) -> int:
        """
        Get the rate limit configuration for a client.
        
        Args:
            client_id: The client's unique identifier
            
        Returns:
            int: The rate limit for the client
        """
        settings = get_settings()
        
        # Check if client is in premium client list (via configuration)
        premium_clients = []
        try:
            # Look for premium clients in API key configurations
            for key, config in settings.api_keys.items():
                if config.get("client_id") == client_id and config.get("rate_limit", 0) >= API_RATE_LIMIT_PREMIUM:
                    logger.debug(f"Client {client_id} identified as premium client")
                    return API_RATE_LIMIT_PREMIUM
        except Exception as e:
            logger.error(f"Error checking premium client status: {str(e)}")
        
        # Use default rate limit if not a premium client
        logger.debug(f"Using default rate limit for client {client_id}: {API_RATE_LIMIT_DEFAULT}")
        return API_RATE_LIMIT_DEFAULT