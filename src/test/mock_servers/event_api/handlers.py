from fastapi import APIRouter, HTTPException, Request, Response, status, Depends
import asyncio
from typing import Dict, List, Any, Optional
import logging

# Import internal functions from data module
from .data import (
    get_events_response,
    get_event_risk_factor_response,
    get_events_by_date_range,
    is_error_ticker,
    is_timeout_ticker,
    get_error_response_for_ticker,
    DEFAULT_ERROR_RESPONSE
)

# Setup router and logger
router = APIRouter(prefix="/api", tags=["events"])
logger = logging.getLogger("event_api")

# Global state for test configuration
high_risk_mode = False
custom_responses = {}


@router.get("/events/{ticker}", status_code=status.HTTP_200_OK)
async def get_events(
    ticker: str, 
    request: Request,
    response: Response
) -> Dict[str, Any]:
    """
    Endpoint handler for retrieving events for a specific ticker.
    
    Args:
        ticker: Stock symbol to get events for
        request: FastAPI request object
        response: FastAPI response object
        
    Returns:
        Events response with ticker and list of events
    """
    logger.info(f"Request for events: ticker={ticker}")
    
    # Check for custom response
    if ticker in custom_responses:
        logger.info(f"Returning custom response for ticker: {ticker}")
        return custom_responses[ticker]
    
    # Simulate timeout if needed
    if is_timeout_ticker(ticker):
        logger.info(f"Simulating timeout for ticker: {ticker}")
        await asyncio.sleep(30)  # 30 second timeout
        return get_events_response(ticker)
    
    # Simulate error if needed
    if is_error_ticker(ticker):
        error_response = get_error_response_for_ticker(ticker)
        logger.info(f"Simulating error for ticker: {ticker}, error: {error_response}")
        raise HTTPException(
            status_code=error_response.get("status", 500),
            detail=error_response
        )
    
    # Get the normal response
    events_response = get_events_response(ticker)
    
    # If high risk mode is enabled, increase risk factors
    if high_risk_mode:
        for event in events_response.get("events", []):
            # Increase risk factor, but cap at 10
            event["risk_factor"] = min(event["risk_factor"] + 2, 10)
        logger.info(f"High risk mode: increased risk factors for {ticker}")
    
    return events_response


@router.get("/events/{ticker}/date-range", status_code=status.HTTP_200_OK)
async def get_events_by_date(
    ticker: str,
    start_date: str,
    end_date: str,
    request: Request,
    response: Response
) -> Dict[str, Any]:
    """
    Endpoint handler for retrieving events for a ticker within a date range.
    
    Args:
        ticker: Stock symbol to get events for
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD)
        request: FastAPI request object
        response: FastAPI response object
        
    Returns:
        Events response filtered by date range
    """
    logger.info(f"Request for events by date range: ticker={ticker}, start_date={start_date}, end_date={end_date}")
    
    # Check for custom response
    if ticker in custom_responses and "date_range" in custom_responses[ticker]:
        logger.info(f"Returning custom date range response for ticker: {ticker}")
        return custom_responses[ticker]["date_range"]
    
    # Simulate timeout if needed
    if is_timeout_ticker(ticker):
        logger.info(f"Simulating timeout for ticker: {ticker}")
        await asyncio.sleep(30)  # 30 second timeout
        return get_events_by_date_range(ticker, start_date, end_date)
    
    # Simulate error if needed
    if is_error_ticker(ticker):
        error_response = get_error_response_for_ticker(ticker)
        logger.info(f"Simulating error for ticker: {ticker}, error: {error_response}")
        raise HTTPException(
            status_code=error_response.get("status", 500),
            detail=error_response
        )
    
    # Get the normal response
    events_response = get_events_by_date_range(ticker, start_date, end_date)
    
    # If high risk mode is enabled, increase risk factors
    if high_risk_mode:
        for event in events_response.get("events", []):
            # Increase risk factor, but cap at 10
            event["risk_factor"] = min(event["risk_factor"] + 2, 10)
        logger.info(f"High risk mode: increased risk factors for {ticker}")
    
    return events_response


@router.get("/risk-factor/{ticker}", status_code=status.HTTP_200_OK)
async def get_event_risk_factor(
    ticker: str,
    request: Request,
    response: Response
) -> Dict[str, Any]:
    """
    Endpoint handler for retrieving event risk factor for a specific ticker.
    
    Args:
        ticker: Stock symbol to get risk factor for
        request: FastAPI request object
        response: FastAPI response object
        
    Returns:
        Risk factor response with ticker and risk factor value
    """
    logger.info(f"Request for risk factor: ticker={ticker}")
    
    # Check for custom response
    if ticker in custom_responses and "risk_factor" in custom_responses[ticker]:
        logger.info(f"Returning custom risk factor response for ticker: {ticker}")
        return custom_responses[ticker]["risk_factor"]
    
    # Simulate timeout if needed
    if is_timeout_ticker(ticker):
        logger.info(f"Simulating timeout for ticker: {ticker}")
        await asyncio.sleep(30)  # 30 second timeout
        return get_event_risk_factor_response(ticker)
    
    # Simulate error if needed
    if is_error_ticker(ticker):
        error_response = get_error_response_for_ticker(ticker)
        logger.info(f"Simulating error for ticker: {ticker}, error: {error_response}")
        raise HTTPException(
            status_code=error_response.get("status", 500),
            detail=error_response
        )
    
    # Get the normal response
    risk_response = get_event_risk_factor_response(ticker)
    
    # If high risk mode is enabled, increase risk factor
    if high_risk_mode:
        # Increase risk factor, but cap at 10
        risk_response["risk_factor"] = min(risk_response["risk_factor"] + 2, 10)
        logger.info(f"High risk mode: increased risk factor for {ticker}")
    
    return risk_response


@router.post("/admin/high-risk-mode", status_code=status.HTTP_200_OK)
async def set_high_risk_mode(enabled: bool) -> Dict[str, bool]:
    """
    Endpoint handler for toggling high risk mode on/off.
    
    Args:
        enabled: Boolean indicating whether to enable high risk mode
        
    Returns:
        Status response indicating current high risk mode
    """
    global high_risk_mode
    high_risk_mode = enabled
    logger.info(f"High risk mode set to: {high_risk_mode}")
    return {"high_risk_mode": high_risk_mode}


@router.post("/admin/custom-response/{ticker}", status_code=status.HTTP_200_OK)
async def set_custom_response(ticker: str, response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Endpoint handler for setting a custom response for a specific ticker.
    
    Args:
        ticker: Stock symbol to set custom response for
        response_data: Custom response data to return
        
    Returns:
        Confirmation of custom response setup
    """
    global custom_responses
    custom_responses[ticker] = response_data
    logger.info(f"Custom response set for ticker: {ticker}")
    return {"ticker": ticker, "status": "custom response set"}


@router.post("/admin/clear-custom-responses", status_code=status.HTTP_200_OK)
async def clear_custom_responses() -> Dict[str, str]:
    """
    Endpoint handler for clearing all custom responses.
    
    Returns:
        Confirmation of custom responses cleared
    """
    global custom_responses
    custom_responses = {}
    logger.info("Custom responses cleared")
    return {"status": "custom responses cleared"}


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """
    Endpoint handler for health check.
    
    Returns:
        Health status response
    """
    return {"status": "healthy"}


async def validate_api_key(request: Request) -> bool:
    """
    Dependency function to validate API key in request headers.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if API key is valid, raises exception otherwise
    """
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Missing API key", "code": "UNAUTHORIZED"}
        )
    
    # In a real implementation, we would check the API key against a database
    # For the mock server, we'll accept a test key
    if api_key != "test-api-key":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid API key", "code": "UNAUTHORIZED"}
        )
    
    return True