from fastapi import APIRouter, HTTPException, Query, Path, Depends, Request, Response, status
import asyncio
from typing import Dict, List, Any, Optional
import logging

from .data import (
    get_market_volatility_response,
    get_high_market_volatility_response,
    get_stock_volatility_response,
    get_high_stock_volatility_response,
    get_event_risk_response,
    get_volatility_history_response,
    is_error_ticker,
    is_timeout_ticker,
    get_error_response_for_ticker,
    DEFAULT_ERROR_RESPONSE
)

# Initialize router with appropriate prefix
router = APIRouter(prefix="/api/market", tags=["market"])

# Setup logger
logger = logging.getLogger("market_api")

# Global state variables
high_volatility_mode = False
custom_responses = {}

@router.get("/volatility", status_code=status.HTTP_200_OK)
async def get_market_volatility(request: Request, response: Response) -> Dict[str, Any]:
    """
    Endpoint handler for retrieving current market volatility index
    
    Args:
        request: The FastAPI request object
        response: The FastAPI response object
        
    Returns:
        Dict[str, Any]: Market volatility response with value and timestamp
    """
    logger.info(f"Received market volatility request from {request.client.host}")
    
    # Check for custom response
    if "market" in custom_responses:
        logger.info("Returning custom market volatility response")
        return custom_responses["market"]
    
    # Check if high volatility mode is enabled
    if high_volatility_mode:
        logger.info("Returning high market volatility response")
        return get_high_market_volatility_response()
    
    logger.info("Returning default market volatility response")
    return get_market_volatility_response()

@router.get("/volatility/{ticker}", status_code=status.HTTP_200_OK)
async def get_stock_volatility(
    ticker: str = Path(..., description="Stock ticker symbol"),
    request: Request = None,
    response: Response = None
) -> Dict[str, Any]:
    """
    Endpoint handler for retrieving volatility metrics for a specific stock
    
    Args:
        ticker: Stock ticker symbol
        request: The FastAPI request object
        response: The FastAPI response object
        
    Returns:
        Dict[str, Any]: Stock volatility response with volatility index and event risk factor
    """
    logger.info(f"Received stock volatility request for {ticker} from {request.client.host if request else 'unknown'}")
    
    # Check for custom response
    if ticker in custom_responses:
        logger.info(f"Returning custom response for {ticker}")
        return custom_responses[ticker]
    
    # Simulate timeout for specific tickers
    if is_timeout_ticker(ticker):
        logger.info(f"Simulating timeout for {ticker}")
        await asyncio.sleep(30)  # Simulate a 30-second timeout
        return get_stock_volatility_response(ticker)
    
    # Simulate error for specific tickers
    if is_error_ticker(ticker):
        error_response = get_error_response_for_ticker(ticker)
        logger.info(f"Simulating error for {ticker}: {error_response}")
        raise HTTPException(
            status_code=error_response.get("status", 500),
            detail=error_response
        )
    
    # Check if high volatility mode is enabled
    if high_volatility_mode:
        logger.info(f"Returning high volatility response for {ticker}")
        return get_high_stock_volatility_response(ticker)
    
    logger.info(f"Returning default volatility response for {ticker}")
    return get_stock_volatility_response(ticker)

@router.get("/events/{ticker}", status_code=status.HTTP_200_OK)
async def get_event_risk(
    ticker: str = Path(..., description="Stock ticker symbol"),
    request: Request = None,
    response: Response = None
) -> Dict[str, Any]:
    """
    Endpoint handler for retrieving event risk data for a specific stock
    
    Args:
        ticker: Stock ticker symbol
        request: The FastAPI request object
        response: The FastAPI response object
        
    Returns:
        Dict[str, Any]: Event risk response with upcoming events and risk factor
    """
    logger.info(f"Received event risk request for {ticker} from {request.client.host if request else 'unknown'}")
    
    # Check for custom response
    if ticker in custom_responses and "events" in custom_responses[ticker]:
        logger.info(f"Returning custom event risk response for {ticker}")
        return custom_responses[ticker]["events"]
    
    # Simulate timeout for specific tickers
    if is_timeout_ticker(ticker):
        logger.info(f"Simulating timeout for {ticker}")
        await asyncio.sleep(30)  # Simulate a 30-second timeout
        return get_event_risk_response(ticker)
    
    # Simulate error for specific tickers
    if is_error_ticker(ticker):
        error_response = get_error_response_for_ticker(ticker)
        logger.info(f"Simulating error for {ticker}: {error_response}")
        raise HTTPException(
            status_code=error_response.get("status", 500),
            detail=error_response
        )
    
    logger.info(f"Returning event risk response for {ticker}")
    return get_event_risk_response(ticker)

@router.get("/history", status_code=status.HTTP_200_OK)
async def get_volatility_history(
    ticker: Optional[str] = Query(None, description="Stock ticker symbol (optional)"),
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    request: Request = None,
    response: Response = None
) -> Dict[str, Any]:
    """
    Endpoint handler for retrieving historical volatility data
    
    Args:
        ticker: Optional stock ticker symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        request: The FastAPI request object
        response: The FastAPI response object
        
    Returns:
        Dict[str, Any]: Historical volatility data with timestamps
    """
    logger.info(f"Received volatility history request for {ticker or 'market'} "
                f"from {request.client.host if request else 'unknown'}, "
                f"period: {start_date} to {end_date}")
    
    # Check for custom response
    if "history" in custom_responses:
        logger.info("Returning custom history response")
        return custom_responses["history"]
    
    # Check if ticker is provided and should error
    if ticker and is_error_ticker(ticker):
        error_response = get_error_response_for_ticker(ticker)
        logger.info(f"Simulating error for {ticker}: {error_response}")
        raise HTTPException(
            status_code=error_response.get("status", 500),
            detail=error_response
        )
    
    logger.info(f"Returning volatility history for {ticker or 'market'}")
    return get_volatility_history_response(ticker, start_date, end_date)

@router.post("/admin/high-volatility-mode", status_code=status.HTTP_200_OK)
async def set_high_volatility_mode(enabled: bool) -> Dict[str, bool]:
    """
    Endpoint handler for toggling high volatility mode on/off
    
    Args:
        enabled: Boolean flag to enable/disable high volatility mode
        
    Returns:
        Dict[str, bool]: Status response indicating current high volatility mode
    """
    global high_volatility_mode
    high_volatility_mode = enabled
    logger.info(f"High volatility mode set to: {enabled}")
    return {"high_volatility_mode": high_volatility_mode}

@router.post("/admin/custom-response/{key}", status_code=status.HTTP_200_OK)
async def set_custom_response(
    key: str = Path(..., description="Key for custom response (ticker symbol or endpoint name)"),
    response_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Endpoint handler for setting a custom response for a specific ticker or endpoint
    
    Args:
        key: Key for custom response (ticker symbol or endpoint name)
        response_data: The custom response data to return
        
    Returns:
        Dict[str, Any]: Confirmation of custom response setup
    """
    global custom_responses
    custom_responses[key] = response_data
    logger.info(f"Custom response set for key: {key}")
    return {"key": key, "status": "custom response set"}

@router.post("/admin/clear-custom-responses", status_code=status.HTTP_200_OK)
async def clear_custom_responses() -> Dict[str, str]:
    """
    Endpoint handler for clearing all custom responses
    
    Returns:
        Dict[str, str]: Confirmation of custom responses cleared
    """
    global custom_responses
    custom_responses = {}
    logger.info("All custom responses cleared")
    return {"status": "all custom responses cleared"}

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """
    Endpoint handler for health check
    
    Returns:
        Dict[str, str]: Health status response
    """
    return {"status": "healthy"}

async def validate_api_key(request: Request) -> bool:
    """
    Dependency function to validate API key in request headers
    
    Args:
        request: The FastAPI request object
        
    Returns:
        bool: True if API key is valid, raises exception otherwise
    """
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Missing API key", "code": "MISSING_API_KEY"}
        )
    
    # In a real implementation, we would check the API key against a database
    # For testing purposes, we'll accept a test key
    if api_key != "test-market-api-key":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid API key", "code": "INVALID_API_KEY"}
        )
    
    return True