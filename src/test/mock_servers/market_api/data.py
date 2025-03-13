from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import random

# Default market volatility values
DEFAULT_MARKET_VOLATILITY = 18.5
HIGH_MARKET_VOLATILITY = 35.0

# Stock-specific volatility values
STOCK_VOLATILITY = {
    'AAPL': 15.2,  # Apple - lower volatility blue chip
    'MSFT': 14.8,  # Microsoft - lower volatility blue chip
    'AMZN': 22.5,  # Amazon - moderate volatility
    'TSLA': 45.3,  # Tesla - higher volatility tech
    'GME': 85.7,   # GameStop - very high volatility meme stock
    'AMC': 78.2,   # AMC - very high volatility meme stock
    'DEFAULT': 20.0  # Default volatility for unknown stocks
}

# Multiplier for high volatility scenarios
HIGH_VOLATILITY_MULTIPLIER = 2.0

# Tickers that should simulate API errors
ERROR_TICKERS = ['ERROR', 'APIERROR', 'FAIL', 'EXCEPTION']

# Tickers that should simulate timeouts
TIMEOUT_TICKERS = ['TIMEOUT', 'SLOW', 'DELAY', 'HANG']

# Default error response
DEFAULT_ERROR_RESPONSE = {
    'error': 'Unable to retrieve volatility data',
    'code': 'EXTERNAL_API_ERROR',
    'status': 500
}

def get_market_volatility_response() -> Dict[str, Any]:
    """
    Returns the default market-wide volatility response.
    
    Returns:
        Dict[str, Any]: Market volatility response with value and timestamp
    """
    return {
        'value': DEFAULT_MARKET_VOLATILITY,
        'timestamp': datetime.now().isoformat(),
        'source': 'Mock Market Volatility API'
    }

def get_high_market_volatility_response() -> Dict[str, Any]:
    """
    Returns a high market-wide volatility response.
    
    Returns:
        Dict[str, Any]: Market volatility response with high value and timestamp
    """
    return {
        'value': HIGH_MARKET_VOLATILITY,
        'timestamp': datetime.now().isoformat(),
        'source': 'Mock Market Volatility API',
        'alert_level': 'HIGH'
    }

def get_stock_volatility_response(ticker: str) -> Dict[str, Any]:
    """
    Returns the volatility response for a specific stock.
    
    Args:
        ticker (str): The stock ticker symbol
        
    Returns:
        Dict[str, Any]: Stock volatility response with volatility index and event risk factor
    """
    ticker = ticker.upper()
    
    # Get volatility for the ticker or use default
    volatility = STOCK_VOLATILITY.get(ticker, STOCK_VOLATILITY['DEFAULT'])
    
    # Determine event risk factor (0-10) based on ticker characteristics
    event_risk = 0
    if ticker in ['GME', 'AMC']:
        event_risk = 8  # High event risk for meme stocks
    elif ticker in ['TSLA']:
        event_risk = 5  # Moderate event risk for volatile tech
    elif ticker in ['AMZN']:
        event_risk = 3  # Some event risk for tech giants
    elif ticker in ['AAPL', 'MSFT']:
        event_risk = 2  # Low event risk for stable blue chips
    
    return {
        'ticker': ticker,
        'volatility_index': volatility,
        'event_risk_factor': event_risk,
        'timestamp': datetime.now().isoformat(),
        'source': 'Mock Market Volatility API'
    }

def get_high_stock_volatility_response(ticker: str) -> Dict[str, Any]:
    """
    Returns a high volatility response for a specific stock.
    
    Args:
        ticker (str): The stock ticker symbol
        
    Returns:
        Dict[str, Any]: Stock volatility response with increased volatility index
    """
    # Get base response
    response = get_stock_volatility_response(ticker)
    
    # Increase volatility and event risk
    response['volatility_index'] = round(response['volatility_index'] * HIGH_VOLATILITY_MULTIPLIER, 1)
    
    if 'event_risk_factor' in response:
        response['event_risk_factor'] = min(10, response['event_risk_factor'] + 2)
    
    response['alert_level'] = 'HIGH'
    
    return response

def get_event_risk_response(ticker: str) -> Dict[str, Any]:
    """
    Returns the event risk data for a specific stock.
    
    Args:
        ticker (str): The stock ticker symbol
        
    Returns:
        Dict[str, Any]: Event risk response with upcoming events and risk factor
    """
    ticker = ticker.upper()
    
    # Create mock upcoming events based on ticker
    events = []
    risk_factor = 0
    
    # Different events based on ticker type
    if ticker in ['GME', 'AMC']:
        events.append({
            'type': 'earnings',
            'date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
            'impact': 'high'
        })
        events.append({
            'type': 'social_sentiment',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'impact': 'extreme'
        })
        risk_factor = 8
    elif ticker in ['TSLA']:
        events.append({
            'type': 'earnings',
            'date': (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d'),
            'impact': 'high'
        })
        events.append({
            'type': 'product_announcement',
            'date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'impact': 'medium'
        })
        risk_factor = 5
    elif ticker in ['AMZN', 'AAPL', 'MSFT']:
        events.append({
            'type': 'earnings',
            'date': (datetime.now() + timedelta(days=21)).strftime('%Y-%m-%d'),
            'impact': 'medium'
        })
        risk_factor = 3
    else:
        # Generic event for other tickers
        events.append({
            'type': 'earnings',
            'date': (datetime.now() + timedelta(days=random.randint(7, 60))).strftime('%Y-%m-%d'),
            'impact': 'unknown'
        })
        risk_factor = 2
    
    return {
        'ticker': ticker,
        'events': events,
        'risk_factor': risk_factor,
        'timestamp': datetime.now().isoformat(),
        'source': 'Mock Market Volatility API'
    }

def get_volatility_history_response(ticker: Optional[str] = None, 
                                   start_date: str = None, 
                                   end_date: str = None) -> Dict[str, Any]:
    """
    Returns historical volatility data for market or specific stock.
    
    Args:
        ticker (Optional[str]): The stock ticker symbol, or None for market-wide data
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        Dict[str, Any]: Historical volatility data with timestamps
    """
    # Parse dates or use defaults (last 30 days)
    if not start_date:
        start_dt = datetime.now() - timedelta(days=30)
    else:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    
    if not end_date:
        end_dt = datetime.now()
    else:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Generate historical data points
    data_points = []
    current_dt = start_dt
    
    # Get base volatility
    if ticker:
        ticker = ticker.upper()
        base_volatility = STOCK_VOLATILITY.get(ticker, STOCK_VOLATILITY['DEFAULT'])
    else:
        base_volatility = DEFAULT_MARKET_VOLATILITY
    
    # Generate daily data
    while current_dt <= end_dt:
        # Add some randomness to historical data
        daily_volatility = generate_random_volatility(base_volatility, 0.15)
        
        # Special case for certain dates (market events)
        # Simulate market crash or volatility spike
        if current_dt.month == 3 and current_dt.day == 15:  # Example market event date
            daily_volatility = daily_volatility * 1.8
        
        data_points.append({
            'date': current_dt.strftime('%Y-%m-%d'),
            'value': daily_volatility,
            'market_condition': 'normal' if daily_volatility < base_volatility * 1.3 else 'volatile'
        })
        
        current_dt += timedelta(days=1)
    
    response = {
        'data': data_points,
        'period': {
            'start': start_dt.strftime('%Y-%m-%d'),
            'end': end_dt.strftime('%Y-%m-%d')
        },
        'source': 'Mock Market Volatility API'
    }
    
    if ticker:
        response['ticker'] = ticker
    else:
        response['scope'] = 'market'
    
    return response

def is_error_ticker(ticker: str) -> bool:
    """
    Determines if a ticker should return an error response.
    
    Args:
        ticker (str): The stock ticker symbol
        
    Returns:
        bool: True if ticker should return an error, False otherwise
    """
    return ticker.upper() in ERROR_TICKERS

def is_timeout_ticker(ticker: str) -> bool:
    """
    Determines if a ticker should simulate a timeout.
    
    Args:
        ticker (str): The stock ticker symbol
        
    Returns:
        bool: True if ticker should simulate a timeout, False otherwise
    """
    return ticker.upper() in TIMEOUT_TICKERS

def get_error_response_for_ticker(ticker: str) -> Dict[str, Any]:
    """
    Returns an appropriate error response for test tickers.
    
    Args:
        ticker (str): The stock ticker symbol
        
    Returns:
        Dict[str, Any]: Error response object
    """
    ticker = ticker.upper()
    
    # Create specific error responses based on ticker
    if ticker == 'APIERROR':
        return {
            'error': 'API authorization failed',
            'code': 'AUTH_ERROR',
            'status': 401
        }
    elif ticker == 'FAIL':
        return {
            'error': 'Resource not found',
            'code': 'NOT_FOUND',
            'status': 404
        }
    elif ticker == 'EXCEPTION':
        return {
            'error': 'Internal server error',
            'code': 'SERVER_ERROR',
            'status': 500,
            'details': 'Unhandled exception in volatility calculation'
        }
    
    # Return default error for other error tickers
    return DEFAULT_ERROR_RESPONSE

def generate_random_volatility(base_volatility: float, variation_percent: float) -> float:
    """
    Generates a random volatility value within a specified range.
    
    Args:
        base_volatility (float): The base volatility value
        variation_percent (float): The percentage variation (0.10 = 10%)
        
    Returns:
        float: Random volatility value
    """
    variation = base_volatility * variation_percent
    random_volatility = base_volatility + random.uniform(-variation, variation)
    return round(random_volatility, 1)  # Round to 1 decimal place