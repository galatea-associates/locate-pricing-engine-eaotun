import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import the router with all Event Calendar API mock endpoints
from .handlers import router

# Configure logger
logger = logging.getLogger('event_api')

# Create FastAPI application
app = FastAPI(
    title='Event Calendar API Mock',
    description='Mock server for Event Calendar API',
    version='1.0.0'
)

def configure_logging():
    """Configures the logging system for the application"""
    # Get LOG_LEVEL from environment variables or default to INFO
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    # Configure logging format with timestamp, level, and message
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set the log level for the event_api logger
    logger.setLevel(getattr(logging, log_level))
    
    logger.info(f"Logging configured with level: {log_level}")

def configure_cors():
    """Configures CORS middleware for the application"""
    # Add CORSMiddleware to the application
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_methods=["GET", "POST", "PUT", "DELETE"],  # Allow common HTTP methods
        allow_headers=["*"],  # Allow standard headers
        allow_credentials=True,  # Allow credentials to be included in requests
    )
    logger.info("CORS middleware configured")

def configure_routes():
    """Configures API routes for the application"""
    # Include the router imported from handlers.py
    app.include_router(router)
    logger.info("Routes configured")

@app.get('/', status_code=200)
def root_endpoint():
    """Handler for the root endpoint that returns API information"""
    return {
        "name": "Event Calendar API Mock",
        "version": "1.0.0",
        "description": "Mock server for Event Calendar API"
    }

@app.get('/health', status_code=200)
def health_check():
    """Handler for the health check endpoint"""
    return {"status": "healthy"}

# Configure the application when the module is imported
configure_logging()
configure_cors()
configure_routes()

def main():
    """Main function to run the application when executed directly"""
    # Get MOCK_API_PORT from environment variables or default to 8003
    port = int(os.environ.get('MOCK_API_PORT', 8003))
    
    # Run the application with uvicorn on the specified port
    uvicorn.run(
        app,
        host="0.0.0.0",  # Configure host as 0.0.0.0 to allow external connections
        port=port,
        reload=True  # Enable reload for development convenience
    )

if __name__ == "__main__":
    main()