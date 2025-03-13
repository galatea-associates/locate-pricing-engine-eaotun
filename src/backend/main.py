"""
Entry point for the Borrow Rate & Locate Fee Pricing Engine API. This module
initializes the FastAPI application, configures middleware, sets up database
connections, registers API routes, and handles application startup and shutdown
events. It serves as the main executable file for running the API service.
"""

import logging  # standard library
import sys  # standard library
import os  # standard library

# Third-party libraries
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status  # fastapi 0.103.0+
import uvicorn  # uvicorn 0.23.0+

# Internal modules
from .api.v1.api import api_router  # Import the configured API router for version 1 endpoints
from .config.settings import get_settings  # Import settings accessor function for application configuration
from .core.middleware import setup_middleware  # Import middleware setup function for configuring all middleware components
from .db.session import init_db, get_db, close_engine, ping_database  # Import database initialization function for creating tables
from .utils.logging import setup_logger  # Import logger setup function for application logging

# Initialize logger for this module
logger = setup_logger('main')

# Create a FastAPI application instance
app = FastAPI(
    title="Borrow Rate & Locate Fee Pricing Engine",
    description="API for calculating securities borrowing costs",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler that initializes database and logs startup
    """
    logger.info("Application starting up...")
    init_db()  # Initialize database schema
    if ping_database():  # Check database connectivity
        logger.info("Database initialized successfully")
    else:
        logger.error("Database initialization failed")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler that closes database connections
    """
    logger.info("Application shutting down...")
    close_engine()  # Close database connections
    logger.info("Database connections closed successfully")

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint to verify API and database availability

    Returns:
        dict: Health status information
    """
    db_status = "OK" if ping_database() else "Unreachable"  # Check database connectivity
    if db_status == "Unreachable":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database Unavailable")
    return {"api_status": "OK", "database_status": db_status}  # Return health status

def configure_app(app: FastAPI) -> FastAPI:
    """
    Configure the FastAPI application with middleware and routes
    """
    settings = get_settings()  # Get application settings
    setup_middleware(app)  # Configure middleware
    app.include_router(api_router)  # Include API router
    return app

def main():
    """
    Main entry point for running the application
    """
    configure_app(app)  # Configure the application
    
    # Get host and port from environment variables or use defaults
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    
    try:
        # Run the application using uvicorn
        uvicorn.run(app, host=host, port=port)
    except KeyboardInterrupt:
        # Handle keyboard interrupts gracefully
        print("Exiting...")

# Export the FastAPI application instance for ASGI servers
__all__ = ["app"]