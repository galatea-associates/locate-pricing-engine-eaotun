"""
Implements distributed tracing middleware for the Borrow Rate & Locate Fee Pricing Engine using OpenTelemetry.

This middleware adds tracing capabilities to the API, enabling end-to-end visibility of request flows
across services, performance monitoring, and troubleshooting of complex transactions.
"""

import time
from fastapi import FastAPI, Request, Response
from typing import Callable, Dict, Optional, Any
from opentelemetry import trace
from opentelemetry.context import context
from opentelemetry.propagate import extract, inject
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from ..config.settings import get_settings
from ..core.logging import get_correlation_id, set_correlation_id
from ..utils.logging import setup_logger

# Set up logger for tracing middleware
logger = setup_logger('middleware.tracing')

# Create a tracer for the tracing middleware
tracer = trace.get_tracer(__name__)


class TracingMiddleware:
    """Middleware for adding distributed tracing to API requests using OpenTelemetry."""
    
    exempt_paths: list
    enabled: bool
    
    def __init__(self, exempt_paths: Optional[list] = None):
        """
        Initialize the tracing middleware with optional exempt paths.
        
        Args:
            exempt_paths: List of path prefixes to exclude from tracing
        """
        self.exempt_paths = exempt_paths or []
        
        # Check if tracing is enabled in settings
        settings = get_settings()
        self.enabled = getattr(settings, 'tracing_enabled', True)
        
        logger.info(f"Tracing middleware initialized, enabled: {self.enabled}, exempt paths: {self.exempt_paths}")
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request through the tracing middleware.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware or route handler in the chain
            
        Returns:
            Response: The response from the next middleware or route handler
        """
        # If tracing is disabled or path is exempt, skip tracing
        if not self.enabled or self.is_path_exempt(request.url.path):
            return await call_next(request)
        
        # Extract context from request headers
        context_data = self.get_trace_context(request)
        
        # Create a span for the request
        with tracer.start_as_current_span(
            f"{request.method} {request.url.path}",
            context=context_data,
            kind=trace.SpanKind.SERVER,
        ) as span:
            # Add request attributes to span
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.path", request.url.path)
            span.set_attribute("http.query_string", str(request.url.query))
            
            # Add client info to span
            client_host = request.client.host if request.client else "unknown"
            span.set_attribute("http.client_ip", client_host)
            
            # Set correlation ID from trace context for log correlation
            current_context = trace.get_current_span(context.get_current()).get_span_context()
            set_correlation_id(f"trace-{current_context.trace_id:032x}")
            
            # Start timing the request
            start_time = time.time()
            
            # Execute the next handler
            response = await call_next(request)
            
            # Calculate request duration
            duration = time.time() - start_time
            
            # Add response attributes to span
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.duration_ms", duration * 1000)
            
            # Add trace headers to response
            response_headers = {}
            inject(response_headers)
            for key, value in response_headers.items():
                response.headers[key] = value
            
            # Return the response
            return response
    
    def instrument_app(self, app: FastAPI) -> None:
        """
        Instrument the FastAPI application with OpenTelemetry.
        
        Args:
            app: FastAPI application instance
            
        Returns:
            None: Instruments app as a side effect
        """
        if not self.enabled:
            logger.info("Tracing is disabled, skipping instrumentation")
            return
        
        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)
        
        # Instrument HTTPX for outgoing requests
        HTTPXInstrumentor().instrument()
        
        # Instrument Redis client
        RedisInstrumentor().instrument()
        
        # Instrument SQLAlchemy ORM
        SQLAlchemyInstrumentor().instrument()
        
        logger.info("Application instrumented with OpenTelemetry")
    
    def get_trace_context(self, request: Request) -> Dict[str, Any]:
        """
        Extract trace context from request headers.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Dict[str, Any]: Extracted trace context
        """
        # Convert headers to dictionary format
        headers = dict(request.headers.items())
        
        # Extract trace context from headers
        return extract(headers)
    
    def is_path_exempt(self, path: str) -> bool:
        """
        Check if a request path is exempt from tracing.
        
        Args:
            path: Request path
            
        Returns:
            bool: True if the path is exempt, False otherwise
        """
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        return False