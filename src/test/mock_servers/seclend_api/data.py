"""
Mock data and helper functions for the SecLend API mock server.

This module provides predefined borrow rate responses for different test scenarios,
including normal market conditions, high volatility, and error cases. It also includes
utility functions to determine when to simulate errors or timeouts based on ticker symbols.
"""

from typing import Dict, Any, List
import random
import datetime

# Default error response when API failures are simulated
DEFAULT_ERROR_RESPONSE: Dict[str, Any] = {
    "error": "Unable to retrieve borrow rate data",
    "code": "EXTERNAL_API_ERROR",
    "status": 500
}

# Tickers that will trigger error responses
ERROR_TICKERS: List[str] = ["ERROR", "APIERROR", "FAIL", "EXCEPTION"]

# Tickers that will trigger timeout simulations
TIMEOUT_TICKERS: List[str] = ["TIMEOUT", "SLOW", "DELAY", "HANG"]

# Predefined stock data with borrow rates and availability status
STOCK_DATA: Dict[str, Dict[str, Any]] = {
    # Easy-to-borrow stocks with low rates
    "AAPL": {"rate": 0.05, "status": "EASY"},
    "MSFT": {"rate": 0.03, "status": "EASY"},
    
    # Medium difficulty stocks with moderate rates
    "AMZN": {"rate": 0.08, "status": "MEDIUM"},
    "TSLA": {"rate": 0.15, "status": "MEDIUM"},
    
    # Hard-to-borrow stocks with high rates
    "GME": {"rate": 0.75, "status": "HARD"},
    "AMC": {"rate": 0.65, "status": "HARD"},
    
    # Default values for unknown tickers
    "DEFAULT": {"rate": 0.1, "status": "MEDIUM"}
}

# Multiplier for high volatility scenarios
HIGH_VOLATILITY_MULTIPLIER: float = 2.5


def get_default_response(ticker: str) -> Dict[str, Any]:
    """
    Returns the default borrow rate response for a given ticker.
    
    Args:
        ticker: The stock ticker symbol
        
    Returns:
        Dict with borrow rate data including rate, status, and timestamp
    """
    # Convert ticker to uppercase for consistency
    ticker = ticker.upper()
    
    # Check if the ticker exists in our predefined data
    if ticker in STOCK_DATA:
        stock_info = STOCK_DATA[ticker].copy()
    else:
        # Use default data for unknown tickers
        stock_info = STOCK_DATA["DEFAULT"].copy()
    
    # Add current timestamp to the response
    timestamp = datetime.datetime.now().isoformat()
    response = {
        "ticker": ticker,
        "rate": stock_info["rate"],
        "status": stock_info["status"],
        "timestamp": timestamp
    }
    
    return response


def get_high_volatility_response(ticker: str) -> Dict[str, Any]:
    """
    Returns a high volatility borrow rate response for a given ticker.
    
    Increases the borrow rate by applying the volatility multiplier and 
    potentially upgrades the borrowing difficulty status.
    
    Args:
        ticker: The stock ticker symbol
        
    Returns:
        Dict with borrow rate data adjusted for high volatility
    """
    # Get the default response first
    response = get_default_response(ticker)
    
    # Apply the high volatility multiplier to the rate
    response["rate"] = min(0.95, response["rate"] * HIGH_VOLATILITY_MULTIPLIER)
    
    # Upgrade the status based on volatility
    if response["status"] == "EASY":
        response["status"] = "MEDIUM"
    elif response["status"] == "MEDIUM":
        response["status"] = "HARD"
    
    # Add volatility flag to the response
    response["high_volatility"] = True
    
    return response


def is_error_ticker(ticker: str) -> bool:
    """
    Determines if a ticker should return an error response.
    
    Args:
        ticker: The stock ticker symbol
        
    Returns:
        True if the ticker should simulate an API error, False otherwise
    """
    return ticker.upper() in ERROR_TICKERS


def is_timeout_ticker(ticker: str) -> bool:
    """
    Determines if a ticker should simulate a timeout.
    
    Args:
        ticker: The stock ticker symbol
        
    Returns:
        True if the ticker should simulate a timeout, False otherwise
    """
    return ticker.upper() in TIMEOUT_TICKERS


def generate_random_rate(status: str) -> float:
    """
    Generates a random borrow rate within a specified range based on status.
    
    Args:
        status: The borrowing difficulty status (EASY, MEDIUM, HARD)
        
    Returns:
        A random borrow rate appropriate for the given status
    """
    if status == "EASY":
        # Easy-to-borrow stocks have low rates
        return round(random.uniform(0.01, 0.05), 4)
    elif status == "MEDIUM":
        # Medium difficulty stocks have moderate rates
        return round(random.uniform(0.06, 0.25), 4)
    elif status == "HARD":
        # Hard-to-borrow stocks have high rates
        return round(random.uniform(0.26, 0.95), 4)
    else:
        # Default to a moderate range
        return round(random.uniform(0.05, 0.15), 4)