"""
API client helper for end-to-end tests of the Borrow Rate & Locate Fee Pricing Engine.
Provides a wrapper around HTTP requests to the API endpoints with proper error handling,
response parsing, and test-specific functionality for E2E test scenarios.
"""

import requests  # version: 2.28.0+
import json  # standard library
import logging  # standard library
import time  # standard library
from decimal import Decimal  # standard library
from typing import Dict, List, Optional, Union, Any  # standard library

from ..config.settings import get_test_settings, TestSettings
from src.backend.schemas.request import CalculateLocateRequest, GetRateRequest
from src.backend.schemas.response import CalculateLocateResponse, BorrowRateResponse, HealthResponse

# Configure logger
logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 1


def parse_response(response: requests.Response, expected_model) -> Union[expected_model, Dict[str, Any]]:
    """
    Parses API response JSON into appropriate Pydantic model

    Args:
        response: HTTP response from the API
        expected_model: Pydantic model class to parse the response into

    Returns:
        Parsed response object or error dictionary
    """
    try:
        if response.status_code == 200:
            # Successful response, parse into expected model
            data = response.json()
            parsed_model = expected_model(**data)
            logger.debug(f"Successfully parsed response into {expected_model.__name__}")
            return parsed_model
        else:
            # Error response, return as dictionary
            error_data = response.json() if response.content else {"status": "error", "message": response.reason}
            logger.warning(f"API error response: {response.status_code} - {error_data}")
            return error_data
    except Exception as e:
        logger.error(f"Error parsing response: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to parse response: {str(e)}",
            "raw_status_code": response.status_code,
            "raw_content": response.text[:1000]  # Limit content length for logging
        }


class APIClient:
    """
    Client for interacting with the Borrow Rate & Locate Fee Pricing Engine API in end-to-end tests
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
        self._settings = settings or get_test_settings()
        self._base_url = self._settings.get_api_url()
        self._api_key = self._settings.api_key
        self._default_headers = {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json"
        }
        self._timeout = timeout or DEFAULT_TIMEOUT
        self._retry_count = retry_count or DEFAULT_RETRY_COUNT
        self._retry_delay = retry_delay or DEFAULT_RETRY_DELAY
        
        logger.info(f"Initialized API client with base URL: {self._base_url}")

    def health_check(self) -> Union[HealthResponse, Dict[str, Any]]:
        """
        Calls the health check endpoint to verify API availability

        Returns:
            Health check response
        """
        response = self.get("/health")
        return parse_response(response, HealthResponse)

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
            ticker: Stock ticker symbol
            position_value: Value of the position
            loan_days: Duration of the loan in days
            client_id: Client identifier

        Returns:
            Fee calculation response
        """
        # Convert position_value to Decimal if needed
        if not isinstance(position_value, Decimal):
            position_value = Decimal(str(position_value))
        
        payload = {
            "ticker": ticker,
            "position_value": position_value,
            "loan_days": loan_days,
            "client_id": client_id
        }
        
        response = self.post("/calculate-locate", json_data=payload)
        return parse_response(response, CalculateLocateResponse)

    def get_borrow_rate(self, ticker: str) -> Union[BorrowRateResponse, Dict[str, Any]]:
        """
        Calls the rates endpoint to get current borrow rate for a ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            Borrow rate response
        """
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
            json_data: JSON data for request body
            headers: Request headers
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts for failed requests

        Returns:
            HTTP response object
        """
        # Combine default headers with any provided headers
        request_headers = {**self._default_headers}
        if headers:
            request_headers.update(headers)
        
        # Build full URL
        url = f"{self._base_url}{endpoint}"
        
        # Set retry count from parameter or default
        retries = retry_count if retry_count is not None else self._retry_count
        request_timeout = timeout if timeout is not None else self._timeout
        
        logger.debug(f"Making {method} request to {url}")
        if params:
            logger.debug(f"Request params: {params}")
        if json_data:
            logger.debug(f"Request data: {json_data}")
        
        # Retry logic
        attempts = 0
        while True:
            attempts += 1
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=request_headers,
                    timeout=request_timeout
                )
                break  # Exit retry loop if request succeeds
            except Exception as e:
                logger.warning(f"Request attempt {attempts} failed: {str(e)}")
                if attempts <= retries:
                    logger.info(f"Retrying in {self._retry_delay} seconds... ({attempts}/{retries})")
                    time.sleep(self._retry_delay)
                else:
                    logger.error(f"Max retries ({retries}) exceeded")
                    raise  # Re-raise the exception if max retries exceeded
        
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response summary: {response.text[:200]}...")  # Log first 200 chars of response
        
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
            headers: Request headers
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts for failed requests

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
            json_data: JSON data for request body
            params: Query parameters
            headers: Request headers
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts for failed requests

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
        if self._settings.mock_external_apis:
            logger.info("Using mock servers for external API dependencies")
            # No action needed as the API itself will use mock servers based on configuration

    def wait_for_api_ready(self, max_attempts: Optional[int] = None, delay: Optional[int] = None) -> bool:
        """
        Waits for the API to be ready by polling the health endpoint

        Args:
            max_attempts: Maximum number of polling attempts
            delay: Delay between polling attempts in seconds

        Returns:
            True if API is ready, False otherwise
        """
        max_attempts = max_attempts or 10
        delay = delay or 2
        
        logger.info(f"Waiting for API to be ready (max {max_attempts} attempts with {delay}s delay)")
        
        attempts = 0
        while attempts < max_attempts:
            attempts += 1
            try:
                health_response = self.health_check()
                if isinstance(health_response, HealthResponse) and health_response.status == "healthy":
                    logger.info(f"API is ready after {attempts} attempts")
                    return True
                else:
                    logger.warning(f"API not ready yet (attempt {attempts}/{max_attempts})")
            except Exception as e:
                logger.warning(f"Error checking API health (attempt {attempts}/{max_attempts}): {str(e)}")
            
            time.sleep(delay)
        
        logger.error(f"API not ready after {max_attempts} attempts")
        return False


def create_api_client(
    settings: Optional[TestSettings] = None,
    timeout: Optional[int] = None
) -> APIClient:
    """
    Factory function to create an APIClient instance with optional settings

    Args:
        settings: Test settings configuration
        timeout: Request timeout in seconds

    Returns:
        Configured API client instance
    """
    return APIClient(settings=settings, timeout=timeout)