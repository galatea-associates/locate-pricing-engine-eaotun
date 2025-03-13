"""
Base client implementation for external API communication in the Borrow Rate & Locate Fee Pricing Engine.

This module provides reusable HTTP client functionality with retry logic, circuit breaker pattern,
and error handling for all external API integrations including SecLend API, Market Volatility API,
and Event Calendar API.
"""

import requests  # requests 2.28.0+
import aiohttp  # aiohttp 3.8.0+
import json
from typing import Dict, Optional, Any, Union

from ...core.exceptions import ExternalAPIException
from ...utils.logging import setup_logger
from ...utils.retry import (
    retry, retry_async, retry_with_fallback, retry_async_with_fallback
)
from ...utils.circuit_breaker import circuit_breaker, async_circuit_breaker
from ...core.constants import ExternalAPIs

# Set up logger
logger = setup_logger('external_client')

# Default timeout in seconds
DEFAULT_TIMEOUT = 10

# Default retry parameters
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 2


@retry_with_fallback(
    fallback_value=None,
    max_retries=DEFAULT_RETRIES,
    backoff_factor=DEFAULT_BACKOFF_FACTOR,
    exceptions_to_retry=(requests.RequestException,)
)
@circuit_breaker(
    service_name=None,  # Will be overridden by the service_name parameter
    failure_threshold=5,
    timeout_seconds=60,
    success_threshold=3,
    fallback_value=None
)
def get(
    url: str,
    service_name: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None,
    fallback_value: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Makes a GET request to an external API with retry and circuit breaker patterns.
    
    Args:
        url: The URL to request
        service_name: The name of the service for circuit breaker and logging
        params: Optional query parameters
        headers: Optional request headers
        timeout: Request timeout in seconds
        fallback_value: Value to return if the request fails and circuit is open
        
    Returns:
        Dict[str, Any]: JSON response from the API or fallback value
        
    Raises:
        ExternalAPIException: If the request fails and no fallback value is provided
    """
    logger.info(f"Making GET request to {url} for service {service_name}")
    
    # Set default values
    timeout = timeout or DEFAULT_TIMEOUT
    params = params or {}
    headers = headers or {}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        
        # Check if response was successful
        if response.status_code >= 200 and response.status_code < 300:
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response from {url}: {str(e)}")
                raise ExternalAPIException(service_name, f"Invalid JSON response: {str(e)}")
        else:
            logger.error(f"Error response from {url}: {response.status_code} - {response.text}")
            raise ExternalAPIException(
                service_name, 
                f"API returned error: HTTP {response.status_code}"
            )
            
    except requests.RequestException as e:
        logger.error(f"Request exception for {url}: {str(e)}")
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error during GET request to {url}: {str(e)}")
        raise ExternalAPIException(service_name, f"Unexpected error: {str(e)}")


@retry_async_with_fallback(
    fallback_value=None, 
    max_retries=DEFAULT_RETRIES, 
    backoff_factor=DEFAULT_BACKOFF_FACTOR,
    exceptions_to_retry=(aiohttp.ClientError,)
)
@async_circuit_breaker(
    service_name=None,  # Will be overridden by the service_name parameter
    failure_threshold=5,
    timeout_seconds=60,
    success_threshold=3,
    fallback_value=None
)
async def async_get(
    url: str,
    service_name: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None,
    fallback_value: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Makes an asynchronous GET request to an external API with retry and circuit breaker patterns.
    
    Args:
        url: The URL to request
        service_name: The name of the service for circuit breaker and logging
        params: Optional query parameters
        headers: Optional request headers
        timeout: Request timeout in seconds
        fallback_value: Value to return if the request fails and circuit is open
        
    Returns:
        Dict[str, Any]: JSON response from the API or fallback value
        
    Raises:
        ExternalAPIException: If the request fails and no fallback value is provided
    """
    logger.info(f"Making async GET request to {url} for service {service_name}")
    
    # Set default values
    timeout = timeout or DEFAULT_TIMEOUT
    params = params or {}
    headers = headers or {}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, 
                params=params, 
                headers=headers, 
                timeout=timeout
            ) as response:
                
                # Check if response was successful
                if response.status >= 200 and response.status < 300:
                    try:
                        return await response.json()
                    except (json.JSONDecodeError, aiohttp.ContentTypeError) as e:
                        logger.error(f"Error parsing JSON response from {url}: {str(e)}")
                        raise ExternalAPIException(service_name, f"Invalid JSON response: {str(e)}")
                else:
                    error_text = await response.text()
                    logger.error(f"Error response from {url}: {response.status} - {error_text}")
                    raise ExternalAPIException(
                        service_name, 
                        f"API returned error: HTTP {response.status}"
                    )
                
    except aiohttp.ClientError as e:
        logger.error(f"Request exception for {url}: {str(e)}")
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error during async GET request to {url}: {str(e)}")
        raise ExternalAPIException(service_name, f"Unexpected error: {str(e)}")


@retry_with_fallback(
    fallback_value=None,
    max_retries=DEFAULT_RETRIES,
    backoff_factor=DEFAULT_BACKOFF_FACTOR,
    exceptions_to_retry=(requests.RequestException,)
)
@circuit_breaker(
    service_name=None,  # Will be overridden by the service_name parameter
    failure_threshold=5,
    timeout_seconds=60,
    success_threshold=3,
    fallback_value=None
)
def post(
    url: str,
    service_name: str,
    json_data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None,
    fallback_value: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Makes a POST request to an external API with retry and circuit breaker patterns.
    
    Args:
        url: The URL to request
        service_name: The name of the service for circuit breaker and logging
        json_data: Optional JSON data to send in the request body
        headers: Optional request headers
        timeout: Request timeout in seconds
        fallback_value: Value to return if the request fails and circuit is open
        
    Returns:
        Dict[str, Any]: JSON response from the API or fallback value
        
    Raises:
        ExternalAPIException: If the request fails and no fallback value is provided
    """
    logger.info(f"Making POST request to {url} for service {service_name}")
    
    # Set default values
    timeout = timeout or DEFAULT_TIMEOUT
    json_data = json_data or {}
    headers = headers or {}
    
    try:
        response = requests.post(url, json=json_data, headers=headers, timeout=timeout)
        
        # Check if response was successful
        if response.status_code >= 200 and response.status_code < 300:
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response from {url}: {str(e)}")
                raise ExternalAPIException(service_name, f"Invalid JSON response: {str(e)}")
        else:
            logger.error(f"Error response from {url}: {response.status_code} - {response.text}")
            raise ExternalAPIException(
                service_name, 
                f"API returned error: HTTP {response.status_code}"
            )
            
    except requests.RequestException as e:
        logger.error(f"Request exception for {url}: {str(e)}")
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error during POST request to {url}: {str(e)}")
        raise ExternalAPIException(service_name, f"Unexpected error: {str(e)}")


@retry_async_with_fallback(
    fallback_value=None, 
    max_retries=DEFAULT_RETRIES, 
    backoff_factor=DEFAULT_BACKOFF_FACTOR,
    exceptions_to_retry=(aiohttp.ClientError,)
)
@async_circuit_breaker(
    service_name=None,  # Will be overridden by the service_name parameter
    failure_threshold=5,
    timeout_seconds=60,
    success_threshold=3,
    fallback_value=None
)
async def async_post(
    url: str,
    service_name: str,
    json_data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None,
    fallback_value: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Makes an asynchronous POST request to an external API with retry and circuit breaker patterns.
    
    Args:
        url: The URL to request
        service_name: The name of the service for circuit breaker and logging
        json_data: Optional JSON data to send in the request body
        headers: Optional request headers
        timeout: Request timeout in seconds
        fallback_value: Value to return if the request fails and circuit is open
        
    Returns:
        Dict[str, Any]: JSON response from the API or fallback value
        
    Raises:
        ExternalAPIException: If the request fails and no fallback value is provided
    """
    logger.info(f"Making async POST request to {url} for service {service_name}")
    
    # Set default values
    timeout = timeout or DEFAULT_TIMEOUT
    json_data = json_data or {}
    headers = headers or {}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, 
                json=json_data, 
                headers=headers, 
                timeout=timeout
            ) as response:
                
                # Check if response was successful
                if response.status >= 200 and response.status < 300:
                    try:
                        return await response.json()
                    except (json.JSONDecodeError, aiohttp.ContentTypeError) as e:
                        logger.error(f"Error parsing JSON response from {url}: {str(e)}")
                        raise ExternalAPIException(service_name, f"Invalid JSON response: {str(e)}")
                else:
                    error_text = await response.text()
                    logger.error(f"Error response from {url}: {response.status} - {error_text}")
                    raise ExternalAPIException(
                        service_name, 
                        f"API returned error: HTTP {response.status}"
                    )
                
    except aiohttp.ClientError as e:
        logger.error(f"Request exception for {url}: {str(e)}")
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error during async POST request to {url}: {str(e)}")
        raise ExternalAPIException(service_name, f"Unexpected error: {str(e)}")


def validate_response(response: Dict[str, Any], required_fields: list[str]) -> bool:
    """
    Validates that a response contains all required fields.
    
    Args:
        response: The response to validate
        required_fields: List of field names that must be present
        
    Returns:
        bool: True if response contains all required fields, False otherwise
    """
    if not response:
        logger.error("Response is empty or None")
        return False
    
    for field in required_fields:
        if field not in response:
            logger.error(f"Required field '{field}' missing from response")
            return False
    
    return True


def build_url(base_url: str, endpoint: str) -> str:
    """
    Builds a complete URL from base URL and endpoint.
    
    Args:
        base_url: The base URL
        endpoint: The API endpoint
        
    Returns:
        str: Complete URL
    """
    # Remove trailing slash from base_url if present
    base_url = base_url.rstrip('/')
    
    # Remove leading slash from endpoint if present
    endpoint = endpoint.lstrip('/')
    
    return f"{base_url}/{endpoint}"