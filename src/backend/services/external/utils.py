"""
Utility functions for external API interactions in the Borrow Rate & Locate Fee Pricing Engine.

This module provides common helper functions for API URL construction, response parsing,
error handling, and data transformation that are shared across different external API clients.
"""

import urllib.parse
import json
import typing
from typing import Dict, List, Optional, Any, Union
import datetime

from ...utils.logging import setup_logger
from ...core.exceptions import ExternalAPIException
from ...core.constants import ExternalAPIs
from ...config.settings import get_settings

# Set up logger for external API utilities
logger = setup_logger('external_api_utils')


def build_api_url(base_url: str, endpoint: str, query_params: Optional[Dict[str, Any]] = None) -> str:
    """
    Constructs a complete API URL from base URL and endpoint path.
    
    Args:
        base_url: Base URL of the API service
        endpoint: API endpoint path
        query_params: Optional query parameters to include in the URL
        
    Returns:
        Complete API URL with query parameters
    """
    # Ensure base_url doesn't end with a slash
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    
    # Ensure endpoint starts with a slash
    if not endpoint.startswith('/'):
        endpoint = f'/{endpoint}'
    
    # Combine base URL and endpoint
    url = f"{base_url}{endpoint}"
    
    # Add query parameters if provided
    if query_params:
        query_string = urllib.parse.urlencode(query_params)
        url = f"{url}?{query_string}"
    
    logger.debug(f"Built API URL: {url}")
    return url


def get_api_key_header(service_name: str) -> Dict[str, str]:
    """
    Creates authentication header with API key for external service.
    
    Args:
        service_name: Name of the external service (use ExternalAPIs constants)
        
    Returns:
        Header dictionary with API key
    """
    settings = get_settings()
    api_config = settings.get_external_api_config(service_name)
    api_key = api_config.get('api_key')
    
    if not api_key:
        logger.warning(f"No API key configured for service: {service_name}")
        return {}
    
    # Determine the appropriate header format based on service_name
    if service_name == ExternalAPIs.SECLEND:
        return {"X-API-Key": api_key}
    elif service_name == ExternalAPIs.MARKET_VOLATILITY:
        return {"Authorization": f"Bearer {api_key}"}
    elif service_name == ExternalAPIs.EVENT_CALENDAR:
        return {"X-API-Key": api_key}
    else:
        logger.warning(f"Unknown service: {service_name}, using default X-API-Key header format")
        return {"X-API-Key": api_key}


def parse_json_response(response_text: str, service_name: str) -> Dict[str, Any]:
    """
    Safely parses JSON response with error handling.
    
    Args:
        response_text: JSON response string to parse
        service_name: Name of the service for error context
        
    Returns:
        Parsed JSON data
        
    Raises:
        ExternalAPIException: If JSON parsing fails
    """
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response from {service_name}: {e}")
        logger.debug(f"Raw response: {response_text[:500]}...")
        raise ExternalAPIException(
            service=service_name,
            detail=f"Invalid JSON response: {str(e)}"
        )


def format_ticker(ticker: str, service_name: str) -> str:
    """
    Formats ticker symbol according to external API requirements.
    
    Args:
        ticker: Raw ticker symbol
        service_name: Name of the service to format for
        
    Returns:
        Formatted ticker symbol
    """
    # Convert ticker to uppercase as a baseline
    formatted_ticker = ticker.strip().upper()
    
    # Apply service-specific formatting rules if needed
    if service_name == ExternalAPIs.SECLEND:
        # No additional formatting needed for SecLend API
        pass
    elif service_name == ExternalAPIs.MARKET_VOLATILITY:
        # No additional formatting needed for Market Volatility API
        pass
    elif service_name == ExternalAPIs.EVENT_CALENDAR:
        # No additional formatting needed for Event Calendar API
        pass
    
    logger.debug(f"Formatted ticker '{ticker}' to '{formatted_ticker}' for service {service_name}")
    return formatted_ticker


def format_date(date: Union[str, datetime.date, datetime.datetime], 
                service_name: str, 
                format_str: Optional[str] = None) -> str:
    """
    Formats date for external API requests.
    
    Args:
        date: Date to format (string, date, or datetime)
        service_name: Name of the service to format for
        format_str: Optional custom format string to use
        
    Returns:
        Formatted date string
    """
    # If date is already a string and no specific format is requested, return as is
    if isinstance(date, str) and format_str is None:
        return date
    
    # If date is a datetime object, convert to string
    if isinstance(date, (datetime.date, datetime.datetime)):
        # Use service-specific default format if not specified
        if format_str is None:
            if service_name == ExternalAPIs.SECLEND:
                format_str = "%Y-%m-%d"  # ISO format for SecLend API
            elif service_name == ExternalAPIs.MARKET_VOLATILITY:
                format_str = "%Y-%m-%d"  # ISO format for Market Volatility API
            elif service_name == ExternalAPIs.EVENT_CALENDAR:
                format_str = "%Y-%m-%d"  # ISO format for Event Calendar API
            else:
                format_str = "%Y-%m-%d"  # Default ISO format
        
        # Format the date
        if isinstance(date, datetime.datetime):
            formatted_date = date.strftime(format_str)
        else:
            formatted_date = date.strftime(format_str)
        
        logger.debug(f"Formatted date to '{formatted_date}' for service {service_name}")
        return formatted_date
    
    # If we get here, something unexpected happened
    logger.warning(f"Unexpected date format: {date}, type: {type(date)}")
    return str(date)


def validate_api_response(response_data: Dict[str, Any], 
                         required_fields: List[str], 
                         service_name: str) -> bool:
    """
    Validates that an API response contains required fields.
    
    Args:
        response_data: Response data to validate
        required_fields: List of field names that must be present
        service_name: Name of the service for error context
        
    Returns:
        True if validation passes
        
    Raises:
        ExternalAPIException: If validation fails
    """
    if not response_data:
        logger.error(f"Empty response data from {service_name}")
        raise ExternalAPIException(
            service=service_name,
            detail="Empty response received"
        )
    
    missing_fields = [field for field in required_fields if field not in response_data]
    
    if missing_fields:
        logger.error(f"Response from {service_name} missing required fields: {missing_fields}")
        raise ExternalAPIException(
            service=service_name,
            detail=f"Response missing required fields: {', '.join(missing_fields)}"
        )
    
    logger.debug(f"Response from {service_name} validated successfully")
    return True


def extract_error_details(error_response: Dict[str, Any], service_name: str) -> str:
    """
    Extracts error details from API error response.
    
    Args:
        error_response: Error response data
        service_name: Name of the service for context
        
    Returns:
        Extracted error message
    """
    # Common field names used by different APIs for error messages
    error_fields = []
    
    # Check service-specific error message fields
    if service_name == ExternalAPIs.SECLEND:
        error_fields = ['error', 'message', 'detail', 'errorMessage']
    elif service_name == ExternalAPIs.MARKET_VOLATILITY:
        error_fields = ['error', 'message', 'errorMessage', 'description']
    elif service_name == ExternalAPIs.EVENT_CALENDAR:
        error_fields = ['error', 'message', 'errorDescription', 'detail']
    else:
        error_fields = ['error', 'message', 'detail', 'errorMessage', 'description']
    
    # Try to extract error message using each field
    for field in error_fields:
        if field in error_response and error_response[field]:
            return str(error_response[field])
    
    # If error message couldn't be extracted, return generic message
    logger.debug(f"Could not extract specific error message from {service_name} response")
    return f"Error from {service_name} API (details not available)"


def create_batch_request_params(items: List[str], param_name: str, service_name: str) -> Dict[str, Any]:
    """
    Creates parameters for batch API requests.
    
    Args:
        items: List of items to include in the batch request
        param_name: Parameter name to use
        service_name: Name of the service for formatting
        
    Returns:
        Parameters formatted for batch request
    """
    if not items:
        logger.warning(f"Empty items list for batch request to {service_name}")
        return {}
    
    # Format items based on service-specific requirements
    if service_name == ExternalAPIs.SECLEND:
        # SecLend API uses comma-separated values for batch requests
        return {param_name: ",".join(items)}
    
    elif service_name == ExternalAPIs.MARKET_VOLATILITY:
        # Market Volatility API uses array parameter format
        return {f"{param_name}[]": items}
    
    elif service_name == ExternalAPIs.EVENT_CALENDAR:
        # Event Calendar API uses comma-separated values
        return {param_name: ",".join(items)}
    
    else:
        # Default to comma-separated values
        logger.warning(f"Unknown service: {service_name}, using default comma-separated format")
        return {param_name: ",".join(items)}


def log_api_request(method: str, url: str, service_name: str, 
                   params: Optional[Dict[str, Any]] = None, 
                   data: Optional[Dict[str, Any]] = None) -> None:
    """
    Logs details of an external API request.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        service_name: Name of the service being called
        params: Optional query parameters
        data: Optional request body data
    """
    log_message = f"API Request: {method} {url} to service {service_name}"
    
    # Add params to log message if provided
    if params:
        log_message += f", params: {params}"
    
    # Add data to log message if provided (with sensitive data redacted)
    if data:
        # Create a copy to avoid modifying the original
        safe_data = data.copy()
        
        # Redact sensitive fields if present
        sensitive_fields = ['api_key', 'apiKey', 'key', 'secret', 'password', 'token']
        for field in sensitive_fields:
            if field in safe_data:
                safe_data[field] = "******"
        
        log_message += f", data: {safe_data}"
    
    logger.info(log_message)


def log_api_response(status_code: int, service_name: str, 
                    response_data: Optional[Dict[str, Any]] = None) -> None:
    """
    Logs details of an external API response.
    
    Args:
        status_code: HTTP status code
        service_name: Name of the service
        response_data: Optional response data
    """
    log_message = f"API Response from {service_name} - Status: {status_code}"
    
    # Add truncated response data to log message if provided
    if response_data:
        # Convert to string and truncate to prevent huge log entries
        response_str = str(response_data)
        truncated_response = (response_str[:500] + '...') if len(response_str) > 500 else response_str
        log_message += f", data: {truncated_response}"
    
    # Log at appropriate level based on status code
    if 200 <= status_code < 300:
        logger.info(log_message)
    elif 400 <= status_code < 500:
        logger.warning(log_message)
    else:
        logger.error(log_message)


def get_service_base_url(service_name: str) -> str:
    """
    Retrieves the base URL for an external service from settings.
    
    Args:
        service_name: Name of the service (use ExternalAPIs constants)
        
    Returns:
        Base URL for the specified service
        
    Raises:
        ExternalAPIException: If the service is not recognized
    """
    settings = get_settings()
    
    try:
        api_config = settings.get_external_api_config(service_name)
        base_url = api_config.get('base_url')
        
        if not base_url:
            logger.error(f"Base URL not configured for service: {service_name}")
            raise ExternalAPIException(
                service=service_name,
                detail="Service URL not configured"
            )
        
        return base_url
    
    except ValueError as e:
        logger.error(f"Unknown service: {service_name}")
        raise ExternalAPIException(
            service=service_name,
            detail=f"Unknown service: {service_name}"
        )