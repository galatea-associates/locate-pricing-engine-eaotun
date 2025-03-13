"""
Implements logging middleware for the Borrow Rate & Locate Fee Pricing Engine API.

This middleware captures and logs all incoming requests and outgoing responses with timing
information, correlation IDs, and contextual data. It ensures comprehensive request
tracing and provides an audit trail for API interactions.
"""

from fastapi import Request, Response  # FastAPI 0.103.0+
from typing import Callable, Dict, Any, List, Optional
import time
import uuid

from ..core.logging import (
    get_correlation_id,
    set_correlation_id,
    log_api_request,
    log_api_response,
    get_api_logger
)
from ..config.settings import get_settings

# Get API logger instance
logger = get_api_logger()


def extract_client_id(request: Request) -> Optional[str]:
    """
    Extract client ID from request state or headers.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client ID if available, None otherwise
    """
    # Check if client_id is in request state (from auth middleware)
    if hasattr(request.state, "client_id"):
        return request.state.client_id
    
    # Check for X-Client-ID header
    if "X-Client-ID" in request.headers:
        return request.headers.get("X-Client-ID")
    
    # No client ID found
    return None


def extract_request_params(request: Request) -> Dict[str, Any]:
    """
    Extract parameters from request query, path, and body.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Combined parameters from all sources
    """
    params = {}
    
    # Add query parameters if available
    if request.query_params:
        params.update(dict(request.query_params))
    
    # Add path parameters if available
    if request.path_params:
        params.update(dict(request.path_params))
    
    # Try to add JSON body parameters if available
    try:
        body = request.json()
        if isinstance(body, dict):
            params.update(body)
    except:
        # Ignore errors when trying to parse body
        pass
    
    return params


def is_path_exempt(path: str, exempt_paths: List[str]) -> bool:
    """
    Check if a path should be exempt from logging.
    
    Args:
        path: Request path
        exempt_paths: List of path prefixes to exempt
        
    Returns:
        True if path is exempt, False otherwise
    """
    for exempt_path in exempt_paths:
        if path.startswith(exempt_path):
            return True
    return False


class LoggingMiddleware:
    """
    Middleware for logging API requests and responses with timing and correlation IDs.
    
    This middleware:
    1. Logs all incoming requests with their parameters and headers
    2. Measures request processing time
    3. Logs responses with status codes and timing information
    4. Maintains correlation IDs for request tracing
    5. Adds correlation ID headers to responses
    """
    
    def __init__(self, exempt_paths: List[str] = None):
        """
        Initialize the logging middleware with exempt paths.
        
        Args:
            exempt_paths: List of path prefixes to exempt from logging
        """
        self.exempt_paths = exempt_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        logger.info(f"Initialized logging middleware with exempt paths: {self.exempt_paths}")
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request through the logging middleware.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware or route handler
            
        Returns:
            Response from the next middleware or route handler
        """
        # Always add correlation ID to request
        correlation_id = self.add_correlation_id(request)
        
        # Check if path should be exempt from logging
        if is_path_exempt(request.url.path, self.exempt_paths):
            response = await call_next(request)
            # Add correlation ID to response headers even for exempt paths
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        
        # Extract client ID
        client_id = extract_client_id(request)
        
        # Extract request parameters (query params, path params, body)
        params = extract_request_params(request)
        
        # Log the incoming request
        log_api_request(
            logger,
            request.method,
            request.url.path,
            params,
            client_id or "unknown",
            correlation_id
        )
        
        # Record start time for request processing
        start_time = time.time()
        
        # Process the request with the next middleware or route handler
        response = await call_next(request)
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Log the response
        log_api_response(
            logger,
            request.method,
            request.url.path,
            response.status_code,
            duration,
            correlation_id
        )
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
    
    def add_correlation_id(self, request: Request) -> str:
        """
        Add correlation ID to request state and set in context.
        
        Args:
            request: FastAPI request object
            
        Returns:
            The correlation ID
        """
        # Check for X-Correlation-ID header in request
        if "X-Correlation-ID" in request.headers:
            correlation_id = request.headers.get("X-Correlation-ID")
        else:
            # Generate new correlation ID or get from context
            correlation_id = get_correlation_id() or str(uuid.uuid4())
        
        # Set correlation ID in context
        set_correlation_id(correlation_id)
        
        # Add correlation ID to request state
        request.state.correlation_id = correlation_id
        
        return correlation_id