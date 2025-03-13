from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import logging

# Import router from handlers module
from .handlers import router

# Set up logger
logger = logging.getLogger('market_api')

# Initialize FastAPI application
app = FastAPI(
    title="Market Volatility API Mock",
    description="Mock server for Market Volatility API",
    version="1.0.0"
)

def configure_logging():
    """
    Configures the logging system for the application
    """
    # Get log level from environment variables, default to INFO
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    
    # Configure logging format
    logging.basicConfig(
        level=logging.getLevelName(log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set the log level for the application logger
    logger.setLevel(logging.getLevelName(log_level))
    
    # Log application startup with configured log level
    logger.info(f"Logging configured with level: {log_level}")

def configure_cors():
    """
    Configures CORS middleware for the FastAPI application
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for testing purposes
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
        allow_credentials=True
    )

def configure_routes():
    """
    Configures API routes for the FastAPI application
    """
    # Include the router imported from handlers module
    app.include_router(router)
    
    # Root and health check endpoints are defined outside this function
    # as they are decorated directly with app.get

@app.get("/", tags=["info"])
def root_endpoint():
    """
    Root endpoint handler that returns API information
    
    Returns:
        dict: API information including name and version
    """
    return {
        "name": "Market Volatility API Mock",
        "version": "1.0.0"
    }

@app.get("/health", tags=["health"])
def health_check():
    """
    Health check endpoint handler
    
    Returns:
        dict: Health status response
    """
    return {"status": "healthy"}

@app.on_event("startup")
def startup_event():
    """
    Application startup event handler
    """
    port = os.environ.get("MOCK_API_PORT", "8002")
    logger.info("Market Volatility API Mock server starting up")
    logger.info(f"Server will be available at http://localhost:{port}")
    logger.info("Available endpoints:")
    logger.info(f"  - GET /api/market/volatility - Get market-wide volatility")
    logger.info(f"  - GET /api/market/volatility/{{ticker}} - Get stock-specific volatility")
    logger.info(f"  - GET /api/market/events/{{ticker}} - Get event risk data for a stock")
    logger.info(f"  - GET /api/market/history - Get historical volatility data")
    logger.info(f"  - GET /health - Health check endpoint")

@app.on_event("shutdown")
def shutdown_event():
    """
    Application shutdown event handler
    """
    logger.info("Market Volatility API Mock server shutting down")

def main():
    """
    Main function to run the application when executed directly
    """
    # Configure logging for the application
    configure_logging()
    
    # Configure CORS middleware
    configure_cors()
    
    # Configure API routes
    configure_routes()
    
    # Get port from environment variable MOCK_API_PORT, default to 8002
    port = int(os.environ.get("MOCK_API_PORT", "8002"))
    
    # Run the application with uvicorn on the specified port
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()