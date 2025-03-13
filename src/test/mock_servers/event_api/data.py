from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import random

# Default error response when API failures are simulated
DEFAULT_ERROR_RESPONSE = {
    "error": "Unable to retrieve event data",
    "code": "EXTERNAL_API_ERROR",
    "status": 500
}

# Tickers that should trigger error responses for testing error handling
ERROR_TICKERS = ["ERROR", "APIERROR", "FAIL", "EXCEPTION"]

# Tickers that should trigger timeout simulation for testing timeout handling
TIMEOUT_TICKERS = ["TIMEOUT", "SLOW", "DELAY", "HANG"]

# Possible event types that can be returned by the API
EVENT_TYPES = [
    "earnings", 
    "dividend", 
    "stock_split", 
    "merger", 
    "acquisition", 
    "product_launch", 
    "regulatory_decision", 
    "investor_day", 
    "conference"
]

# Predefined events for common stock tickers
STOCK_EVENTS = {
    "AAPL": [
        {"type": "earnings", "date": "2023-11-02", "risk_factor": 7},
        {"type": "product_launch", "date": "2023-12-15", "risk_factor": 6}
    ],
    "MSFT": [
        {"type": "earnings", "date": "2023-10-25", "risk_factor": 6},
        {"type": "conference", "date": "2023-11-15", "risk_factor": 3}
    ],
    "AMZN": [
        {"type": "earnings", "date": "2023-10-27", "risk_factor": 8},
        {"type": "product_launch", "date": "2023-11-20", "risk_factor": 5}
    ],
    "TSLA": [
        {"type": "earnings", "date": "2023-10-19", "risk_factor": 9},
        {"type": "product_launch", "date": "2023-12-01", "risk_factor": 8}
    ],
    "GME": [
        {"type": "earnings", "date": "2023-12-08", "risk_factor": 10},
        {"type": "investor_day", "date": "2023-11-10", "risk_factor": 7}
    ],
    "AMC": [
        {"type": "earnings", "date": "2023-11-09", "risk_factor": 9},
        {"type": "investor_day", "date": "2023-10-30", "risk_factor": 6}
    ]
}

# Default risk factors for each event type if not explicitly specified
DEFAULT_RISK_FACTORS = {
    "earnings": 7,
    "dividend": 4,
    "stock_split": 6,
    "merger": 9,
    "acquisition": 8,
    "product_launch": 5,
    "regulatory_decision": 8,
    "investor_day": 4,
    "conference": 2
}


def get_events_response(ticker: str) -> Dict[str, Any]:
    """
    Returns the events response for a specific ticker.
    
    Args:
        ticker: Stock symbol to get events for
        
    Returns:
        Dictionary containing ticker and list of events
    """
    ticker = ticker.upper()
    
    # Get events for the ticker if they exist, otherwise generate some
    if ticker in STOCK_EVENTS:
        events = STOCK_EVENTS[ticker]
    else:
        # Generate 1-3 random events for tickers not in our predefined list
        events = generate_future_events(ticker, random.randint(1, 3))
    
    # Create the response with current timestamp
    response = {
        "ticker": ticker,
        "events": events,
        "timestamp": datetime.now().isoformat()
    }
    
    return response


def get_event_risk_factor_response(ticker: str) -> Dict[str, Any]:
    """
    Returns the event risk factor for a specific ticker.
    
    Args:
        ticker: Stock symbol to get risk factor for
        
    Returns:
        Dictionary containing ticker and calculated risk factor
    """
    ticker = ticker.upper()
    
    # Get all events for this ticker
    events_response = get_events_response(ticker)
    events = events_response.get("events", [])
    
    # Calculate the maximum risk factor from all events
    risk_factor = calculate_event_risk_factor(events)
    
    # Create the response
    response = {
        "ticker": ticker,
        "risk_factor": risk_factor,
        "timestamp": datetime.now().isoformat()
    }
    
    return response


def get_events_by_date_range(ticker: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Returns events for a ticker within a specified date range.
    
    Args:
        ticker: Stock symbol to get events for
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD)
        
    Returns:
        Dictionary containing ticker and filtered list of events
    """
    ticker = ticker.upper()
    
    # Parse date strings to datetime objects
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)
    
    # Get all events for this ticker
    events_response = get_events_response(ticker)
    all_events = events_response.get("events", [])
    
    # Filter events to include only those within the date range
    filtered_events = []
    for event in all_events:
        event_date = datetime.fromisoformat(event["date"])
        if start_dt <= event_date <= end_dt:
            filtered_events.append(event)
    
    # Create the response
    response = {
        "ticker": ticker,
        "events": filtered_events,
        "start_date": start_date,
        "end_date": end_date,
        "timestamp": datetime.now().isoformat()
    }
    
    return response


def is_error_ticker(ticker: str) -> bool:
    """
    Determines if a ticker should return an error response.
    
    Args:
        ticker: Stock symbol to check
        
    Returns:
        True if the ticker should return an error, False otherwise
    """
    return ticker.upper() in ERROR_TICKERS


def is_timeout_ticker(ticker: str) -> bool:
    """
    Determines if a ticker should simulate a timeout.
    
    Args:
        ticker: Stock symbol to check
        
    Returns:
        True if the ticker should simulate a timeout, False otherwise
    """
    return ticker.upper() in TIMEOUT_TICKERS


def get_error_response_for_ticker(ticker: str) -> Dict[str, Any]:
    """
    Returns an appropriate error response for test tickers.
    
    Args:
        ticker: Stock symbol to get error response for
        
    Returns:
        Error response dictionary
    """
    ticker = ticker.upper()
    
    # Generate custom error responses for specific tickers if needed
    if ticker == "APIERROR":
        return {
            "error": "API key invalid",
            "code": "UNAUTHORIZED",
            "status": 401
        }
    elif ticker == "FAIL":
        return {
            "error": "Resource not found",
            "code": "NOT_FOUND",
            "status": 404
        }
    elif ticker == "EXCEPTION":
        return {
            "error": "Internal server error",
            "code": "SERVER_ERROR",
            "status": 500
        }
    
    # Default error response
    return DEFAULT_ERROR_RESPONSE


def generate_future_events(ticker: str, num_events: int = 2) -> List[Dict[str, Any]]:
    """
    Generates random future events for a ticker.
    
    Args:
        ticker: Stock symbol to generate events for
        num_events: Number of events to generate (default: 2)
        
    Returns:
        List of generated event objects
    """
    events = []
    today = datetime.now()
    
    for _ in range(num_events):
        # Pick a random event type
        event_type = random.choice(EVENT_TYPES)
        
        # Generate a random future date within the next 90 days
        days_in_future = random.randint(1, 90)
        event_date = (today + timedelta(days=days_in_future)).strftime("%Y-%m-%d")
        
        # Get risk factor for this event type or generate random one
        risk_factor = DEFAULT_RISK_FACTORS.get(event_type, random.randint(1, 10))
        
        # Create the event
        event = {
            "type": event_type,
            "date": event_date,
            "risk_factor": risk_factor
        }
        
        events.append(event)
    
    return events


def calculate_event_risk_factor(events: List[Dict[str, Any]]) -> int:
    """
    Calculates the overall event risk factor based on upcoming events.
    
    Args:
        events: List of event objects
        
    Returns:
        Calculated risk factor (0-10)
    """
    if not events:
        return 0
    
    # Find the maximum risk factor from all events
    max_risk = max(event.get("risk_factor", 0) for event in events)
    
    # Ensure the risk factor is between 0 and 10
    return min(max_risk, 10)