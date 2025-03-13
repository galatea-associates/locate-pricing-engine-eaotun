"""
Authentication middleware for the Borrow Rate & Locate Fee Pricing Engine API.

This middleware intercepts incoming requests, validates API keys, enforces
authentication requirements, and adds authentication context to the request
state for downstream handlers. It ensures that only authenticated clients can
access protected API endpoints.
"""

from fastapi import Request, Response, HTTPException, status  # fastapi 0.103.0
from typing import Callable, Dict, List, Optional, Any  # standard library

from ..core.auth import get_api_key_from_header, authenticate_request, create_auth_token
from ..core.exceptions import AuthenticationException, RateLimitExceededException
from ..utils.logging import setup_logger
from ..config.settings import get_settings

# Set up logger
logger = setup_logger('middleware.authentication')


class AuthenticationMiddleware:
    """Middleware for authenticating API requests using API keys"""
    
    def __init__(self, exempt_paths: Optional[List[str]] = None):
        """
        Initialize the authentication middleware with optional exempt paths
        
        Args:
            exempt_paths: List of path prefixes that are exempt from authentication
        """
        # Default exempt paths
        default_exempt_paths = ['/health', '/docs', '/openapi.json', '/redoc']
        
        # Use provided exempt paths or default ones
        self.exempt_paths = exempt_paths or default_exempt_paths
        
        logger.info(f"Authentication middleware initialized with exempt paths: {self.exempt_paths}")
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request through the authentication middleware
        
        Args:
            request: The FastAPI request object
            call_next: The next middleware or route handler in the pipeline
            
        Returns:
            Response: The response from the next middleware or route handler
        """
        # Check if the path is exempt from authentication
        if self.is_path_exempt(request.url.path):
            logger.debug(f"Path exempt from authentication: {request.url.path}")
            # If exempt, bypass authentication and call the next handler
            response = await call_next(request)
            return response
        
        # Extract API key from request headers
        api_key = get_api_key_from_header(request)
        
        # If no API key found, return 401 Unauthorized
        if not api_key:
            logger.warning(f"Authentication failed: No API key provided for {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required"
            )
        
        try:
            # Authenticate the request using the API key
            auth_result = authenticate_request(api_key)
            
            # Store authentication result in request state for downstream handlers
            request.state.auth_result = auth_result
            
            # Log successful authentication
            logger.info(f"Request authenticated for client: {auth_result.get('client_id')}")
            
            # Call the next handler in the middleware chain
            response = await call_next(request)
            
            # Add authentication-related headers to the response
            response = self.add_auth_headers(response, auth_result)
            
            return response
            
        except AuthenticationException as e:
            # Handle authentication failures
            logger.warning(f"Authentication failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )
            
        except RateLimitExceededException as e:
            # Handle rate limit exceeded errors
            logger.warning(f"Rate limit exceeded: {str(e)}")
            
            # Create response with appropriate status code
            response = Response(
                content=f"Rate limit exceeded. Try again in {e.params.get('retry_after', 60)} seconds.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS
            )
            
            # Add retry-after header
            response.headers["Retry-After"] = str(e.params.get("retry_after", 60))
            return response
    
    def is_path_exempt(self, path: str) -> bool:
        """
        Check if a request path is exempt from authentication
        
        Args:
            path: The request path to check
            
        Returns:
            bool: True if the path is exempt, False otherwise
        """
        # Check if the path starts with any of the exempt paths
        return any(path.startswith(exempt_path) for exempt_path in self.exempt_paths)
    
    def add_auth_headers(self, response: Response, auth_result: Dict[str, Any]) -> Response:
        """
        Add authentication-related headers to the response
        
        Args:
            response: The response object to modify
            auth_result: Authentication result containing rate limit information
            
        Returns:
            Response: The response with added headers
        """
        # Add rate limit headers if rate limit information is available
        rate_limit_info = auth_result.get("rate_limit")
        if rate_limit_info:
            response.headers["X-RateLimit-Limit"] = str(rate_limit_info.get("limit", 60))
            response.headers["X-RateLimit-Remaining"] = str(rate_limit_info.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(rate_limit_info.get("reset", 60))
        
        return response
    
    def get_client_id(self, request: Request) -> Optional[str]:
        """
        Extract client ID from the request state
        
        Args:
            request: The FastAPI request object
            
        Returns:
            Optional[str]: Client ID if available, None otherwise
        """
        # Check if auth_result exists in request.state
        if hasattr(request.state, "auth_result"):
            # Return the client_id from auth_result
            return request.state.auth_result.get("client_id")
        return None
    
    def create_jwt_token(self, client_id: str) -> str:
        """
        Create a JWT token for the authenticated client
        
        Args:
            client_id: The client identifier
            
        Returns:
            str: JWT token
        """
        # Call create_auth_token function with the client_id
        return create_auth_token(client_id)