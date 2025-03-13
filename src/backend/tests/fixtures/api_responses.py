"""
Provides mock API response fixtures for testing the external API integrations in 
the Borrow Rate & Locate Fee Pricing Engine.

This module contains functions that return predefined responses mimicking the SecLend API,
Market Volatility API, and Event Calendar API, allowing tests to run without actual
external API calls.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Union
from decimal import Decimal

import pytest

from ...core.constants import BorrowStatus, DEFAULT_MINIMUM_BORROW_RATE

# Stock borrow status mapping for mock responses
STOCK_BORROW_STATUS = {
    "AAPL": BorrowStatus.EASY,
    "MSFT": BorrowStatus.EASY,
    "TSLA": BorrowStatus.MEDIUM,
    "GME": BorrowStatus.HARD,
    "AMC": BorrowStatus.HARD,
}

# Stock borrow rates mapping for mock responses
STOCK_BORROW_RATES = {
    "AAPL": "0.05",  # 5% borrow rate
    "MSFT": "0.03",  # 3% borrow rate
    "TSLA": "0.15",  # 15% borrow rate
    "GME": "0.75",   # 75% borrow rate
    "AMC": "0.65",   # 65% borrow rate
}

# Stock volatility mapping for mock responses
STOCK_VOLATILITY = {
    "AAPL": "15.0",  # Volatility index
    "MSFT": "12.5",
    "TSLA": "35.0",
    "GME": "85.0",
    "AMC": "75.0",
}

# Event risk factors mapping for mock responses
EVENT_RISK_FACTORS = {
    "AAPL": "3",  # Risk factor on scale of 0-10
    "MSFT": "2",
    "TSLA": "5",
    "GME": "8",
    "AMC": "7",
}

# API error response templates
API_ERROR_RESPONSES = {
    "not_found": {"error": "Ticker not found", "code": 404},
    "unauthorized": {"error": "Unauthorized access", "code": 401},
    "rate_limit": {"error": "Rate limit exceeded", "code": 429},
    "server_error": {"error": "Internal server error", "code": 500},
}


@pytest.fixture
def mock_seclend_response(ticker: str) -> Dict[str, Any]:
    """
    Creates a mock response from the SecLend API for a given ticker.
    
    Args:
        ticker: The stock symbol to generate a response for
        
    Returns:
        Dict[str, Any]: Mock SecLend API response with borrow rate and status
    """
    ticker = ticker.upper()
    rate = Decimal(STOCK_BORROW_RATES.get(ticker, str(DEFAULT_MINIMUM_BORROW_RATE)))
    status = STOCK_BORROW_STATUS.get(ticker, BorrowStatus.HARD)
    
    return {
        "ticker": ticker,
        "rate": float(rate),  # Convert to float for JSON serialization
        "status": status.value,
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def mock_seclend_batch_response(tickers: List[str]) -> Dict[str, Any]:
    """
    Creates a mock batch response from the SecLend API for multiple tickers.
    
    Args:
        tickers: List of stock symbols to generate responses for
        
    Returns:
        Dict[str, Any]: Mock SecLend API batch response with borrow rates and statuses
                        for multiple tickers
    """
    results = {}
    timestamp = datetime.now().isoformat()
    
    for ticker in tickers:
        ticker = ticker.upper()
        rate = Decimal(STOCK_BORROW_RATES.get(ticker, str(DEFAULT_MINIMUM_BORROW_RATE)))
        status = STOCK_BORROW_STATUS.get(ticker, BorrowStatus.HARD)
        
        results[ticker] = {
            "rate": float(rate),  # Convert to float for JSON serialization
            "status": status.value,
            "timestamp": timestamp,
        }
    
    return {
        "results": results,
        "count": len(results),
        "timestamp": timestamp,
    }


@pytest.fixture
def mock_stock_volatility_response(ticker: str) -> Dict[str, Any]:
    """
    Creates a mock response from the Market Volatility API for a specific stock.
    
    Args:
        ticker: The stock symbol to generate a volatility response for
        
    Returns:
        Dict[str, Any]: Mock Market Volatility API response with volatility data for the stock
    """
    ticker = ticker.upper()
    volatility = Decimal(STOCK_VOLATILITY.get(ticker, "20.0"))  # Default to 20.0 if not in dictionary
    
    return {
        "ticker": ticker,
        "volatility": float(volatility),  # Convert to float for JSON serialization
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def mock_market_volatility_response() -> Dict[str, Any]:
    """
    Creates a mock response for the market-wide volatility index (VIX).
    
    Returns:
        Dict[str, Any]: Mock Market Volatility API response with current VIX value
    """
    return {
        "value": 20.0,  # Default market volatility
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def mock_high_volatility_response() -> Dict[str, Any]:
    """
    Creates a mock response for high market volatility conditions.
    
    Returns:
        Dict[str, Any]: Mock Market Volatility API response with high VIX value
    """
    return {
        "value": 35.0,  # High market volatility
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def mock_low_volatility_response() -> Dict[str, Any]:
    """
    Creates a mock response for low market volatility conditions.
    
    Returns:
        Dict[str, Any]: Mock Market Volatility API response with low VIX value
    """
    return {
        "value": 12.0,  # Low market volatility
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def mock_event_calendar_response(ticker: str) -> Dict[str, Any]:
    """
    Creates a mock response from the Event Calendar API for a specific ticker.
    
    Args:
        ticker: The stock symbol to generate an event calendar response for
        
    Returns:
        Dict[str, Any]: Mock Event Calendar API response with upcoming events for the stock
    """
    ticker = ticker.upper()
    risk_factor = int(EVENT_RISK_FACTORS.get(ticker, "0"))
    
    # Create a future date for the event (10 days from now)
    event_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    
    event = {
        "event_id": f"evt_{ticker}_001",
        "ticker": ticker,
        "event_type": "earnings" if risk_factor > 3 else "dividend",
        "event_date": event_date,
        "risk_factor": risk_factor,
    }
    
    return {
        "events": [event] if risk_factor > 0 else [],
        "count": 1 if risk_factor > 0 else 0,
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def mock_high_event_risk_response(ticker: str) -> Dict[str, Any]:
    """
    Creates a mock response for a stock with high event risk (e.g., upcoming earnings).
    
    Args:
        ticker: The stock symbol to generate a high-risk event response for
        
    Returns:
        Dict[str, Any]: Mock Event Calendar API response with high-risk events
    """
    ticker = ticker.upper()
    
    # Create a near-future date for the event (3 days from now)
    event_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    
    event = {
        "event_id": f"evt_{ticker}_high_risk",
        "ticker": ticker,
        "event_type": "earnings",
        "event_date": event_date,
        "risk_factor": 8,  # High risk factor
    }
    
    return {
        "events": [event],
        "count": 1,
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def mock_no_event_risk_response(ticker: str) -> Dict[str, Any]:
    """
    Creates a mock response for a stock with no upcoming events.
    
    Args:
        ticker: The stock symbol to generate a no-event response for
        
    Returns:
        Dict[str, Any]: Mock Event Calendar API response with empty events list
    """
    return {
        "events": [],
        "count": 0,
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def mock_api_error_response(error_type: str) -> Dict[str, Any]:
    """
    Creates a mock error response from an external API.
    
    Args:
        error_type: Type of error to generate ('not_found', 'unauthorized', 
                   'rate_limit', or 'server_error')
        
    Returns:
        Dict[str, Any]: Mock API error response with appropriate error message and code
    """
    error = API_ERROR_RESPONSES.get(error_type, API_ERROR_RESPONSES["server_error"])
    return error