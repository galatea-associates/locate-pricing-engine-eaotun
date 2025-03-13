"""
Client implementation for the Event Calendar API integration in the Borrow Rate & Locate Fee Pricing Engine.

This module provides functions to retrieve event risk data for securities, which is used to adjust
borrow rates based on upcoming corporate events like earnings announcements, dividend payments,
or regulatory decisions.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime

# Internal imports
from .client import get, async_get, build_url, validate_response
from ...core.exceptions import ExternalAPIException
from ...core.constants import ExternalAPIs
from ...utils.logging import setup_logger
from ...config.settings import get_settings

# Setup logger
logger = setup_logger('event_api')

# Constants
EVENT_API_SERVICE = ExternalAPIs.EVENT_CALENDAR
DEFAULT_EVENT_RISK_FACTOR = 0
REQUIRED_EVENT_FIELDS = ['event_id', 'ticker', 'event_type', 'event_date', 'risk_factor']

def get_api_config() -> Dict[str, Any]:
    """
    Retrieves the Event Calendar API configuration from settings.

    Returns:
        Dict[str, Any]: API configuration including base URL, endpoints, and credentials
    """
    settings = get_settings()
    api_config = settings.get_external_api_config(EVENT_API_SERVICE)
    return api_config

def get_auth_headers() -> Dict[str, str]:
    """
    Builds authentication headers for the Event Calendar API.

    Returns:
        Dict[str, str]: Headers dictionary with API key
    """
    api_config = get_api_config()
    api_key = api_config.get('api_key')
    
    # Create headers with API key
    headers = {
        'X-API-Key': api_key
    }
    
    return headers

def get_event_risk_factor(ticker: str) -> int:
    """
    Retrieves the event risk factor for a specific ticker.

    Args:
        ticker: Stock symbol

    Returns:
        int: Event risk factor (0-10) indicating the risk level of upcoming events
    """
    logger.info(f"Getting event risk factor for ticker: {ticker}")
    
    # Get API configuration
    api_config = get_api_config()
    base_url = api_config.get('base_url')
    events_endpoint = api_config.get('events_endpoint', 'events')
    
    # Build complete URL
    url = build_url(base_url, events_endpoint)
    
    # Get authentication headers
    headers = get_auth_headers()
    
    # Set up query parameters
    params = {
        'ticker': ticker
    }
    
    # Make API request with fallback to default risk factor if request fails
    response = get(
        url, 
        EVENT_API_SERVICE, 
        params=params, 
        headers=headers,
        fallback_value=DEFAULT_EVENT_RISK_FACTOR
    )
    
    # Validate response
    if not validate_response(response, ['events']):
        logger.warning(f"Invalid response from Event Calendar API for ticker {ticker}, using default risk factor")
        return DEFAULT_EVENT_RISK_FACTOR
    
    # Extract events from response
    events = response.get('events', [])
    
    # If no events found, return default risk factor
    if not events:
        logger.info(f"No events found for ticker {ticker}, using default risk factor")
        return DEFAULT_EVENT_RISK_FACTOR
    
    # Find the highest risk factor among all events
    highest_risk = DEFAULT_EVENT_RISK_FACTOR
    for event in events:
        risk_factor = event.get('risk_factor', DEFAULT_EVENT_RISK_FACTOR)
        try:
            risk_factor = int(risk_factor)
            highest_risk = max(highest_risk, risk_factor)
        except (ValueError, TypeError):
            logger.warning(f"Invalid risk factor format for event {event.get('event_id')}: {risk_factor}")
    
    logger.info(f"Event risk factor for ticker {ticker}: {highest_risk}")
    return highest_risk

async def async_get_event_risk_factor(ticker: str) -> int:
    """
    Asynchronously retrieves the event risk factor for a specific ticker.

    Args:
        ticker: Stock symbol

    Returns:
        int: Event risk factor (0-10) indicating the risk level of upcoming events
    """
    logger.info(f"Async getting event risk factor for ticker: {ticker}")
    
    # Get API configuration
    api_config = get_api_config()
    base_url = api_config.get('base_url')
    events_endpoint = api_config.get('events_endpoint', 'events')
    
    # Build complete URL
    url = build_url(base_url, events_endpoint)
    
    # Get authentication headers
    headers = get_auth_headers()
    
    # Set up query parameters
    params = {
        'ticker': ticker
    }
    
    # Make API request with fallback to default risk factor if request fails
    response = await async_get(
        url, 
        EVENT_API_SERVICE, 
        params=params, 
        headers=headers,
        fallback_value=DEFAULT_EVENT_RISK_FACTOR
    )
    
    # Validate response
    if not validate_response(response, ['events']):
        logger.warning(f"Invalid response from Event Calendar API for ticker {ticker}, using default risk factor")
        return DEFAULT_EVENT_RISK_FACTOR
    
    # Extract events from response
    events = response.get('events', [])
    
    # If no events found, return default risk factor
    if not events:
        logger.info(f"No events found for ticker {ticker}, using default risk factor")
        return DEFAULT_EVENT_RISK_FACTOR
    
    # Find the highest risk factor among all events
    highest_risk = DEFAULT_EVENT_RISK_FACTOR
    for event in events:
        risk_factor = event.get('risk_factor', DEFAULT_EVENT_RISK_FACTOR)
        try:
            risk_factor = int(risk_factor)
            highest_risk = max(highest_risk, risk_factor)
        except (ValueError, TypeError):
            logger.warning(f"Invalid risk factor format for event {event.get('event_id')}: {risk_factor}")
    
    logger.info(f"Event risk factor for ticker {ticker}: {highest_risk}")
    return highest_risk

def get_upcoming_events(ticker: str, days_ahead: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieves a list of upcoming events for a specific ticker.

    Args:
        ticker: Stock symbol
        days_ahead: Optional number of days to look ahead

    Returns:
        List[Dict[str, Any]]: List of upcoming events with their details
    """
    logger.info(f"Getting upcoming events for ticker: {ticker}, days_ahead: {days_ahead}")
    
    # Get API configuration
    api_config = get_api_config()
    base_url = api_config.get('base_url')
    events_endpoint = api_config.get('events_endpoint', 'events')
    
    # Build complete URL
    url = build_url(base_url, events_endpoint)
    
    # Get authentication headers
    headers = get_auth_headers()
    
    # Set up query parameters
    params = {
        'ticker': ticker
    }
    
    # Add days_ahead parameter if provided
    if days_ahead is not None:
        params['days_ahead'] = days_ahead
    
    # Make API request with fallback to empty list if request fails
    response = get(
        url, 
        EVENT_API_SERVICE, 
        params=params, 
        headers=headers,
        fallback_value=[]
    )
    
    # Validate response
    if not validate_response(response, ['events']):
        logger.warning(f"Invalid response from Event Calendar API for ticker {ticker}, returning empty list")
        return []
    
    # Extract events from response
    events = response.get('events', [])
    
    logger.info(f"Retrieved {len(events)} upcoming events for ticker {ticker}")
    return events

async def async_get_upcoming_events(ticker: str, days_ahead: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Asynchronously retrieves a list of upcoming events for a specific ticker.

    Args:
        ticker: Stock symbol
        days_ahead: Optional number of days to look ahead

    Returns:
        List[Dict[str, Any]]: List of upcoming events with their details
    """
    logger.info(f"Async getting upcoming events for ticker: {ticker}, days_ahead: {days_ahead}")
    
    # Get API configuration
    api_config = get_api_config()
    base_url = api_config.get('base_url')
    events_endpoint = api_config.get('events_endpoint', 'events')
    
    # Build complete URL
    url = build_url(base_url, events_endpoint)
    
    # Get authentication headers
    headers = get_auth_headers()
    
    # Set up query parameters
    params = {
        'ticker': ticker
    }
    
    # Add days_ahead parameter if provided
    if days_ahead is not None:
        params['days_ahead'] = days_ahead
    
    # Make API request with fallback to empty list if request fails
    response = await async_get(
        url, 
        EVENT_API_SERVICE, 
        params=params, 
        headers=headers,
        fallback_value=[]
    )
    
    # Validate response
    if not validate_response(response, ['events']):
        logger.warning(f"Invalid response from Event Calendar API for ticker {ticker}, returning empty list")
        return []
    
    # Extract events from response
    events = response.get('events', [])
    
    logger.info(f"Retrieved {len(events)} upcoming events for ticker {ticker}")
    return events

def get_event_types() -> List[str]:
    """
    Retrieves a list of all available event types from the API.

    Returns:
        List[str]: List of event type identifiers
    """
    logger.info("Getting available event types")
    
    # Get API configuration
    api_config = get_api_config()
    base_url = api_config.get('base_url')
    event_types_endpoint = api_config.get('event_types_endpoint', 'event-types')
    
    # Build complete URL
    url = build_url(base_url, event_types_endpoint)
    
    # Get authentication headers
    headers = get_auth_headers()
    
    # Make API request with fallback to empty list if request fails
    response = get(
        url, 
        EVENT_API_SERVICE, 
        headers=headers,
        fallback_value=[]
    )
    
    # Validate response contains event_types field
    if not validate_response(response, ['event_types']):
        logger.warning("Invalid response from Event Calendar API for event types, returning empty list")
        return []
    
    # Extract event types from response
    event_types = response.get('event_types', [])
    
    logger.info(f"Retrieved {len(event_types)} event types")
    return event_types

def get_event_details(event_id: str) -> Dict[str, Any]:
    """
    Retrieves detailed information about a specific event.

    Args:
        event_id: Unique identifier of the event

    Returns:
        Dict[str, Any]: Detailed event information
    """
    logger.info(f"Getting details for event: {event_id}")
    
    # Get API configuration
    api_config = get_api_config()
    base_url = api_config.get('base_url')
    event_details_endpoint = api_config.get('event_details_endpoint', 'event')
    
    # Build complete URL
    url = build_url(base_url, event_details_endpoint)
    
    # Get authentication headers
    headers = get_auth_headers()
    
    # Set up query parameters
    params = {
        'event_id': event_id
    }
    
    # Make API request with fallback to empty dict if request fails
    response = get(
        url, 
        EVENT_API_SERVICE, 
        params=params, 
        headers=headers,
        fallback_value={}
    )
    
    # Validate response contains required fields
    if not validate_response(response, REQUIRED_EVENT_FIELDS):
        logger.warning(f"Invalid response from Event Calendar API for event {event_id}, returning empty dict")
        return {}
    
    logger.info(f"Successfully retrieved details for event {event_id}")
    return response