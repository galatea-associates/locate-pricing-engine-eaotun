"""
API client helper for integration tests of the Borrow Rate & Locate Fee Pricing Engine.
Provides a wrapper around HTTP requests to the API endpoints with proper error handling,
response parsing, and test-specific functionality for integration test scenarios.
"""

import requests  # version: 2.28.0+
import json  # standard library
import logging  # standard library
import time  # standard library
from decimal import Decimal  # standard library
from typing import Dict, List, Optional, Union, Any  # standard library

from ..config.settings import get_test_settings, TestSettings
from src.backend.schemas.request import CalculateLocateRequest, GetRateRequest
from src.backend.schemas.response import (
    CalculateLocateResponse, 
    BorrowRateResponse, 
    HealthResponse, 
    ConfigResponse
)

# Configure module logger
logger = logging.getLogger(__name__)

# Default values
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 1


def parse_response(response: requests.Response, expected_model):
    """
    Parses API response JSON into appropriate Pydantic model
    
    Args:
        response: HTTP response object from requests
        expected_model: Pydantic model class to parse the response into
        
    Returns:
        Parsed response object or error dictionary
    """
    try:
        # Check if response status code indicates success
        if response.status_code == 200:
            # Parse JSON response into expected model
            parsed_data = response.json()
            model_instance = expected_model(**parsed_data)
            logger.debug(f"Successfully parsed response into {expected_model.__name__}")
            return model_instance
        else:
            # For error responses, parse into dictionary
            try:
                error_data = response.json() if response.content else {"status": "error", "message": "Unknown error"}
            except json.JSONDecodeError:
                error_data = {"status": "error", "message": f"Invalid response format: {response.text[:100]}"}
            
            logger.warning(f"API error response: {response.status_code} - {error_data}")
            return error_data
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON response: {response.text[:100]}")
        return {"status": "error", "message": "Invalid JSON response"}
    except Exception as e:
        logger.error(f"Error parsing response: {str(e)}")
        return {"status": "error", "message": f"Error parsing response: {str(e)}"}


def create_api_client(settings: Optional[TestSettings] = None, timeout: Optional[int] = None) -> 'APIClient':
    """
    Factory function to create an APIClient instance with optional settings
    
    Args:
        settings: Test settings configuration
        timeout: Request timeout in seconds
        
    Returns:
        Configured API client instance
    """
    return APIClient(settings=settings, timeout=timeout)


class APIClient:
    """
    Client for interacting with the Borrow Rate & Locate Fee Pricing Engine API in integration tests
    """
    
    def __init__(
        self, 
        settings: Optional[TestSettings] = None, 
        timeout: Optional[int] = None,
        retry_count: Optional[int] = None,
        retry_delay: Optional[int] = None
    ):
        """
        Initializes the API client with test settings
        
        Args:
            settings: Test settings configuration
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts for failed requests
            retry_delay: Delay between retry attempts in seconds
        """
        # Get test settings if not provided
        self._settings = settings if settings is not None else get_test_settings()
        
        # Set base URL and API key
        self._base_url = self._settings.get_api_url()
        self._api_key = self._settings.test_api_key
        
        # Set default headers
        self._default_headers = {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json"
        }
        
        # Set timeout and retry parameters
        self._timeout = timeout if timeout is not None else self._settings.test_timeout
        if self._timeout is None:
            self._timeout = DEFAULT_TIMEOUT
            
        self._retry_count = retry_count if retry_count is not None else DEFAULT_RETRY_COUNT
        self._retry_delay = retry_delay if retry_delay is not None else DEFAULT_RETRY_DELAY
        
        logger.info(f"Initialized API client with base URL: {self._base_url}")
    
    def health_check(self) -> Union[HealthResponse, Dict[str, Any]]:
        """
        Calls the health check endpoint to verify API availability
        
        Returns:
            Health check response or error dictionary
        """
        response = self.get("/health")
        return parse_response(response, HealthResponse)
    
    def get_config(self) -> Union[ConfigResponse, Dict[str, Any]]:
        """
        Calls the config endpoint to retrieve API configuration
        
        Returns:
            Configuration response or error dictionary
        """
        response = self.get("/config")
        return parse_response(response, ConfigResponse)
    
    def calculate_locate_fee(
        self, 
        ticker: str, 
        position_value: Union[Decimal, float, int], 
        loan_days: int, 
        client_id: str
    ) -> Union[CalculateLocateResponse, Dict[str, Any]]:
        """
        Calls the calculate-locate endpoint to get fee calculation
        
        Args:
            ticker: Stock symbol (e.g., "AAPL")
            position_value: Notional value of the short position
            loan_days: Duration of the borrow in days
            client_id: Client identifier for fee structure
            
        Returns:
            Fee calculation response or error dictionary
        """
        # Convert position_value to Decimal if needed
        if not isinstance(position_value, Decimal):
            position_value = Decimal(str(position_value))
        
        # Create request payload
        payload = {
            "ticker": ticker,
            "position_value": float(position_value),  # Convert Decimal to float for JSON serialization
            "loan_days": loan_days,
            "client_id": client_id
        }
        
        response = self.post("/calculate-locate", json_data=payload)
        return parse_response(response, CalculateLocateResponse)
    
    def get_borrow_rate(self, ticker: str) -> Union[BorrowRateResponse, Dict[str, Any]]:
        """
        Calls the rates endpoint to get current borrow rate for a ticker
        
        Args:
            ticker: Stock symbol (e.g., "AAPL")
            
        Returns:
            Borrow rate response or error dictionary
        """
        ticker = ticker.upper()  # Ensure ticker is uppercase
        response = self.get(f"/rates/{ticker}")
        return parse_response(response, BorrowRateResponse)
    
    def request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None, 
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None, 
        timeout: Optional[int] = None,
        retry_count: Optional[int] = None
    ) -> requests.Response:
        """
        Makes a generic HTTP request to the API with proper error handling and retries
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON payload for POST/PUT requests
            headers: Additional HTTP headers
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts
            
        Returns:
            HTTP response object
        """
        # Combine default headers with any provided headers
        request_headers = self._default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        # Build full URL
        url = f"{self._base_url}{endpoint}"
        
        # Set retry count and timeout
        retries = retry_count if retry_count is not None else self._retry_count
        req_timeout = timeout if timeout is not None else self._timeout
        
        logger.debug(f"Making {method} request to {url}")
        if params:
            logger.debug(f"Request params: {params}")
        if json_data:
            logger.debug(f"Request payload: {json_data}")
        
        # Initialize attempts counter
        attempts = 0
        
        # Retry loop
        while True:
            attempts += 1
            
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=request_headers,
                    timeout=req_timeout
                )
                
                # Request succeeded, break out of retry loop
                break
                
            except requests.Timeout:
                logger.warning(f"Request timeout (attempt {attempts}/{retries+1}): {url} - {req_timeout}s timeout exceeded")
                if attempts <= retries:
                    time.sleep(self._retry_delay)
                    continue
                else:
                    logger.error(f"Max retries ({retries}) reached. Request timed out: {url}")
                    raise
                    
            except (requests.RequestException, ConnectionError) as e:
                logger.warning(f"Request error (attempt {attempts}/{retries+1}): {str(e)}")
                if attempts <= retries:
                    time.sleep(self._retry_delay)
                    continue
                else:
                    logger.error(f"Max retries ({retries}) reached. Request failed: {str(e)}")
                    raise
        
        # Log response status and summary
        logger.debug(f"Response status: {response.status_code}")
        if response.status_code >= 400:
            logger.warning(f"Error response content: {response.text[:200]}")
        
        return response
    
    def get(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        retry_count: Optional[int] = None
    ) -> requests.Response:
        """
        Makes a GET request to the API
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            headers: Additional HTTP headers
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts
            
        Returns:
            HTTP response object
        """
        return self.request(
            method="GET",
            endpoint=endpoint,
            params=params,
            headers=headers,
            timeout=timeout,
            retry_count=retry_count
        )
    
    def post(
        self, 
        endpoint: str, 
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        retry_count: Optional[int] = None
    ) -> requests.Response:
        """
        Makes a POST request to the API
        
        Args:
            endpoint: API endpoint path
            json_data: JSON payload
            params: Query parameters
            headers: Additional HTTP headers
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts
            
        Returns:
            HTTP response object
        """
        return self.request(
            method="POST",
            endpoint=endpoint,
            params=params,
            json_data=json_data,
            headers=headers,
            timeout=timeout,
            retry_count=retry_count
        )
    
    def configure_mock_servers(self) -> None:
        """
        Configures the client to use mock servers for external API dependencies
        """
        if self._settings.use_mock_servers:
            logger.info("Using mock servers for external API dependencies")
            # No action needed on client side as the API itself will use mock servers
            # based on configuration
    
    def wait_for_api_ready(self, max_attempts: Optional[int] = None, delay: Optional[int] = None) -> bool:
        """
        Waits for the API to be ready by polling the health endpoint
        
        Args:
            max_attempts: Maximum number of polling attempts
            delay: Delay between attempts in seconds
            
        Returns:
            True if API is ready, False otherwise
        """
        # Set default values if not provided
        attempts_limit = max_attempts if max_attempts is not None else 10
        wait_delay = delay if delay is not None else 2
        
        logger.info(f"Waiting for API to be ready (max {attempts_limit} attempts, {wait_delay}s delay)")
        
        # Initialize attempts counter
        attempts = 0
        
        # Poll until API is ready or max attempts reached
        while attempts < attempts_limit:
            attempts += 1
            
            try:
                response = self.health_check()
                
                # Check if API is healthy
                if isinstance(response, HealthResponse) and response.status == "healthy":
                    logger.info(f"API is ready after {attempts} attempts")
                    return True
                    
                logger.warning(f"API not ready (attempt {attempts}/{attempts_limit}), status: {response.get('status') if isinstance(response, dict) else response.status}")
                
            except Exception as e:
                logger.warning(f"Error checking API health (attempt {attempts}/{attempts_limit}): {str(e)}")
            
            # Wait before next attempt
            time.sleep(wait_delay)
        
        logger.error(f"API not ready after {attempts_limit} attempts")
        return False
    
    def test_authentication(self) -> bool:
        """
        Tests API authentication with the configured API key
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Call health check which requires authentication
            response = self.health_check()
            
            # Check if response indicates successful authentication
            if isinstance(response, HealthResponse):
                logger.info("Authentication successful")
                return True
            elif isinstance(response, dict) and response.get("status") == "error":
                if "unauthorized" in str(response).lower() or "authentication" in str(response).lower():
                    logger.error(f"Authentication failed: {response.get('message', 'Unknown error')}")
                else:
                    logger.warning(f"API returned error, but may not be authentication-related: {response}")
                return False
            
            # Unexpected response
            logger.warning(f"Unexpected response testing authentication: {response}")
            return False
            
        except Exception as e:
            logger.error(f"Error testing authentication: {str(e)}")
            return False