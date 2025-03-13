"""
SecLend API Mock Server

This module initializes the FastAPI application for the SecLend API mock server,
which simulates the external SecLend API for testing purposes. It configures
middleware, includes API routes, and sets up event handlers.
"""

import os
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .handlers import router

# Set up logger for the application
logger = logging.getLogger('seclend_api')

# Create the FastAPI application
app = FastAPI(
    title="SecLend API Mock",
    description="Mock server for SecLend API",
    version="1.0.0"
)

def configure_logging():
    """
    Configures the logging system for the application.
    """
    # Get the log level from environment variable or default to INFO
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    # Configure logging format
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    
    # Set the log level for the application logger
    logger.setLevel(getattr(logging, log_level))
    
    # Log the configured log level
    logger.info(f"Logging configured with level: {log_level}")

def configure_cors():
    """
    Configures CORS middleware for the FastAPI application.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for testing purposes
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],  # Allow all headers
    )

def configure_routes():
    """
    Configures API routes for the FastAPI application.
    """
    # Include the router from handlers
    app.include_router(router)

@app.get("/", tags=["info"])
def root_endpoint():
    """
    Root endpoint handler that returns API information.
    
    Returns:
        dict: API information including name and version
    """
    return {
        "name": "SecLend API Mock",
        "version": "1.0.0"
    }

@app.get("/health", tags=["health"])
def health_check():
    """
    Health check endpoint handler.
    
    Returns:
        dict: Health status response
    """
    return {"status": "healthy"}

@app.on_event("startup")
def startup_event():
    """
    Application startup event handler.
    """
    port = os.environ.get('MOCK_API_PORT', 8001)
    logger.info(f"Starting SecLend API Mock Server on port {port}")
    logger.info("Available test endpoints:")
    logger.info("  - GET /api/borrows/{ticker}: Get borrow rate for a ticker")
    logger.info("  - POST /api/borrows/batch: Get borrow rates for multiple tickers")
    logger.info("  - POST /api/admin/high-volatility-mode: Toggle high volatility mode")
    logger.info("  - POST /api/admin/custom-response/{ticker}: Set custom response for a ticker")
    logger.info("  - POST /api/admin/clear-custom-responses: Clear all custom responses")
    logger.info("  - GET /api/health: Health check for the API")

@app.on_event("shutdown")
def shutdown_event():
    """
    Application shutdown event handler.
    """
    logger.info("Shutting down SecLend API Mock Server")

def main():
    """
    Main function to run the application when executed directly.
    """
    # Configure logging
    configure_logging()
    
    # Configure CORS middleware
    configure_cors()
    
    # Configure routes
    configure_routes()
    
    # Get the port from the environment or default to 8001
    port = int(os.environ.get('MOCK_API_PORT', 8001))
    
    # Run the application
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()