"""
Mock SecLend API handlers for testing purposes.

This module provides FastAPI route handlers that simulate the real SecLend API behavior,
allowing tests to run without actual external API dependencies. It supports various
test scenarios including normal responses, errors, timeouts, and high volatility.
"""

import asyncio
import logging
from typing import Dict, List, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request, Response, status

from .data import (
    get_default_response,
    get_high_volatility_response, 
    is_error_ticker,
    is_timeout_ticker,
    DEFAULT_ERROR_RESPONSE
)

# Create router for SecLend API endpoints
router = APIRouter(prefix="/api", tags=["seclend"])

# Set up logging
logger = logging.getLogger("seclend_api")

# Global flag for high volatility mode
high_volatility_mode = False

# Dictionary to store custom responses for specific tickers
custom_responses = {}


async def validate_api_key(request: Request) -> bool:
    """
    Validate the API key provided in the request headers.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        True if the API key is valid
        
    Raises:
        HTTPException: If the API key is missing or invalid
    """
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key"
        )
    
    # For testing purposes, accept a simple test key
    if api_key != "test-api-key":
        logger.warning(f"Invalid API key: {api_key}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return True


@router.get("/borrows/{ticker}", status_code=status.HTTP_200_OK)
async def get_borrow_rate(
    ticker: str,
    request: Request,
    response: Response
) -> Dict[str, Any]:
    """
    Get the borrow rate for a specific ticker.
    
    Args:
        ticker: The stock ticker symbol
        request: The FastAPI request object
        response: The FastAPI response object
        
    Returns:
        Dict containing the borrow rate information
        
    Raises:
        HTTPException: If the ticker is configured to return an error
    """
    # Log the request
    logger.info(f"Received borrow rate request for ticker: {ticker}")
    
    # Check if there's a custom response for this ticker
    if ticker in custom_responses:
        logger.info(f"Returning custom response for ticker: {ticker}")
        return custom_responses[ticker]
    
    # Check if this ticker should simulate a timeout
    if is_timeout_ticker(ticker):
        logger.info(f"Simulating timeout for ticker: {ticker}")
        await asyncio.sleep(30)  # Sleep for 30 seconds to simulate timeout
        return get_default_response(ticker)
    
    # Check if this ticker should return an error
    if is_error_ticker(ticker):
        logger.info(f"Returning error response for ticker: {ticker}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=DEFAULT_ERROR_RESPONSE
        )
    
    # Determine which response to return based on high_volatility_mode
    if high_volatility_mode:
        logger.info(f"Returning high volatility response for ticker: {ticker}")
        return get_high_volatility_response(ticker)
    else:
        logger.info(f"Returning default response for ticker: {ticker}")
        return get_default_response(ticker)


@router.post("/borrows/batch", status_code=status.HTTP_200_OK)
async def get_batch_borrow_rates(
    tickers: List[str],
    request: Request,
    response: Response
) -> Dict[str, Dict[str, Any]]:
    """
    Get borrow rates for multiple tickers in a single request.
    
    Args:
        tickers: List of stock ticker symbols
        request: The FastAPI request object
        response: The FastAPI response object
        
    Returns:
        Dict mapping each ticker to its borrow rate information
    """
    # Log the request
    logger.info(f"Received batch borrow rate request for tickers: {tickers}")
    
    result = {}
    
    for ticker in tickers:
        # Check if there's a custom response for this ticker
        if ticker in custom_responses:
            result[ticker] = custom_responses[ticker]
            continue
        
        # Check if this ticker should return an error
        if is_error_ticker(ticker):
            result[ticker] = DEFAULT_ERROR_RESPONSE
            continue
        
        # Determine which response to return based on high_volatility_mode
        if high_volatility_mode:
            result[ticker] = get_high_volatility_response(ticker)
        else:
            result[ticker] = get_default_response(ticker)
    
    return result


@router.post("/admin/high-volatility-mode", status_code=status.HTTP_200_OK)
async def set_high_volatility_mode(enabled: bool) -> Dict[str, bool]:
    """
    Toggle high volatility mode on or off.
    
    Args:
        enabled: Whether to enable high volatility mode
        
    Returns:
        Dict containing the current status of high volatility mode
    """
    global high_volatility_mode
    high_volatility_mode = enabled
    
    logger.info(f"High volatility mode set to: {high_volatility_mode}")
    
    return {"high_volatility_mode": high_volatility_mode}


@router.post("/admin/custom-response/{ticker}", status_code=status.HTTP_200_OK)
async def set_custom_response(
    ticker: str,
    response_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Set a custom response for a specific ticker.
    
    Args:
        ticker: The stock ticker symbol
        response_data: The custom response data to return for this ticker
        
    Returns:
        Dict confirming the custom response setup
    """
    custom_responses[ticker] = response_data
    
    logger.info(f"Set custom response for ticker: {ticker}")
    
    return {
        "ticker": ticker,
        "status": "custom_response_set"
    }


@router.post("/admin/clear-custom-responses", status_code=status.HTTP_200_OK)
async def clear_custom_responses() -> Dict[str, str]:
    """
    Clear all custom responses.
    
    Returns:
        Dict confirming the custom responses were cleared
    """
    custom_responses.clear()
    
    logger.info("Cleared all custom responses")
    
    return {"status": "custom_responses_cleared"}


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Dict containing the health status
    """
    return {"status": "healthy"}