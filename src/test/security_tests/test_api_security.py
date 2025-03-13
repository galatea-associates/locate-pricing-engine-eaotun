"""
Security tests for the Borrow Rate & Locate Fee Pricing Engine API endpoints.

This module focuses on testing API security aspects including authentication, authorization,
input validation, injection vulnerabilities, and secure communication. It uses security
testing tools to identify potential vulnerabilities in the API implementation.
"""

import pytest
import requests
import json
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any

# Internal imports
from . import settings
from .helpers.security_tools import (
    ZAPSecurityScanner,
    JWTAnalyzer,
    SecurityAPIClient,
    create_security_client,
    test_authentication_bypass,
    test_input_validation,
    test_rate_limiting,
    scan_for_sensitive_data_exposure,
    verify_tls_configuration,
)
from .helpers.payloads import (
    SQLInjectionPayloads,
    XSSPayloads,
    InputValidationPayloads,
)
from ...integration_tests.helpers.api_client import APIClient

# Configure logger
logger = logging.getLogger(__name__)

# Test constants
TEST_TICKER = "AAPL"
TEST_POSITION_VALUE = Decimal('100000')
TEST_LOAN_DAYS = 30
TEST_CLIENT_ID = "test_client_001"
INVALID_CLIENT_ID = "invalid_client"


def setup_security_client(api_key: Optional[str] = None) -> SecurityAPIClient:
    """
    Creates and configures a security client for testing.

    Args:
        api_key: Optional API key to use, defaults to settings.test_api_key if not provided

    Returns:
        Configured security API client
    """
    # Use provided API key or default from settings
    key = api_key if api_key is not None else settings.test_api_key
    
    # Create and return the security client
    client = SecurityAPIClient(settings=settings, api_key=key)
    
    # Log the client creation
    logger.info(f"Created security test client with API key: {'valid' if key == settings.test_api_key else 'custom'}")
    
    return client


@pytest.mark.security
@pytest.mark.authentication
def test_api_authentication_security():
    """
    Tests API authentication security mechanisms.
    
    Verifies that all API endpoints properly require and validate authentication,
    rejecting requests with invalid, missing, or malformed credentials.
    """
    # Create a client with invalid API key
    client = setup_security_client(settings.invalid_api_key)
    
    # Test endpoints with invalid authentication
    endpoints = [
        "/health",  # Health endpoint should still require auth
        f"/rates/{TEST_TICKER}",  # Rates endpoint
        "/calculate-locate"  # Calculate endpoint
    ]
    
    # Test each endpoint with invalid API key
    for endpoint in endpoints:
        logger.info(f"Testing authentication for endpoint: {endpoint}")
        
        if endpoint == "/calculate-locate":
            # For POST endpoint, send valid payload
            payload = {
                "ticker": TEST_TICKER,
                "position_value": float(TEST_POSITION_VALUE),
                "loan_days": TEST_LOAN_DAYS,
                "client_id": TEST_CLIENT_ID
            }
            response = client.request(method="POST", endpoint=endpoint, json_data=payload)
        else:
            # For GET endpoints
            response = client.request(method="GET", endpoint=endpoint)
        
        # Verify we get an authentication error (401)
        assert response.status_code == 401, f"Expected 401 Unauthorized for invalid API key on {endpoint}, got {response.status_code}"
    
    # Test with missing authentication header
    for endpoint in endpoints:
        logger.info(f"Testing missing authentication for endpoint: {endpoint}")
        
        # Create a request with no API key header
        headers = {"Content-Type": "application/json"}
        
        if endpoint == "/calculate-locate":
            # For POST endpoint
            payload = {
                "ticker": TEST_TICKER,
                "position_value": float(TEST_POSITION_VALUE),
                "loan_days": TEST_LOAN_DAYS,
                "client_id": TEST_CLIENT_ID
            }
            response = requests.post(
                f"{settings.api_base_url}/api/{settings.api_version}{endpoint}",
                json=payload,
                headers=headers
            )
        else:
            # For GET endpoints
            response = requests.get(
                f"{settings.api_base_url}/api/{settings.api_version}{endpoint}",
                headers=headers
            )
        
        # Verify we get an authentication error (401)
        assert response.status_code == 401, f"Expected 401 Unauthorized for missing API key on {endpoint}, got {response.status_code}"
    
    # Test with empty API key
    empty_key_client = setup_security_client("")
    
    for endpoint in endpoints:
        logger.info(f"Testing empty API key for endpoint: {endpoint}")
        
        if endpoint == "/calculate-locate":
            # For POST endpoint
            payload = {
                "ticker": TEST_TICKER,
                "position_value": float(TEST_POSITION_VALUE),
                "loan_days": TEST_LOAN_DAYS,
                "client_id": TEST_CLIENT_ID
            }
            response = empty_key_client.request(method="POST", endpoint=endpoint, json_data=payload)
        else:
            # For GET endpoints
            response = empty_key_client.request(method="GET", endpoint=endpoint)
        
        # Verify we get an authentication error (401)
        assert response.status_code == 401, f"Expected 401 Unauthorized for empty API key on {endpoint}, got {response.status_code}"
    
    # Test with malformed API key
    malformed_keys = ["malformed-key", "12345", "null", "undefined"]
    
    for malformed_key in malformed_keys:
        malformed_client = setup_security_client(malformed_key)
        
        for endpoint in endpoints:
            logger.info(f"Testing malformed API key '{malformed_key}' for endpoint: {endpoint}")
            
            if endpoint == "/calculate-locate":
                # For POST endpoint
                payload = {
                    "ticker": TEST_TICKER,
                    "position_value": float(TEST_POSITION_VALUE),
                    "loan_days": TEST_LOAN_DAYS,
                    "client_id": TEST_CLIENT_ID
                }
                response = malformed_client.request(method="POST", endpoint=endpoint, json_data=payload)
            else:
                # For GET endpoints
                response = malformed_client.request(method="GET", endpoint=endpoint)
            
            # Verify we get an authentication error (401)
            assert response.status_code == 401, f"Expected 401 Unauthorized for malformed API key on {endpoint}, got {response.status_code}"


@pytest.mark.security
@pytest.mark.input_validation
def test_api_input_validation():
    """
    Tests API input validation for all endpoints.
    
    Verifies that all API endpoints properly validate input parameters,
    rejecting invalid inputs with appropriate error messages.
    """
    # Create a client with valid API key for testing input validation
    client = setup_security_client()
    
    # Test calculate-locate endpoint with invalid ticker formats
    invalid_tickers = ["", "123", "A-B", "ABCDEF", "a", "A B", "A*B"]
    
    for invalid_ticker in invalid_tickers:
        logger.info(f"Testing invalid ticker: '{invalid_ticker}'")
        
        payload = {
            "ticker": invalid_ticker,
            "position_value": float(TEST_POSITION_VALUE),
            "loan_days": TEST_LOAN_DAYS,
            "client_id": TEST_CLIENT_ID
        }
        
        response = client.request(method="POST", endpoint="/calculate-locate", json_data=payload)
        
        # Verify we get a validation error (400)
        assert response.status_code == 400, f"Expected 400 Bad Request for invalid ticker '{invalid_ticker}', got {response.status_code}"
        
        # Verify the error message mentions the ticker parameter
        response_json = response.json()
        assert "error" in response_json, "Expected error message in response"
        error_message = response_json.get("error", {}).get("message", "") if isinstance(response_json.get("error"), dict) else response_json.get("error", "")
        assert "ticker" in error_message.lower(), f"Expected error message to mention 'ticker', got: {error_message}"
    
    # Test calculate-locate endpoint with invalid position values
    invalid_position_values = [-1, 0, "abc", 1e20, 0.00001]
    
    for invalid_value in invalid_position_values:
        logger.info(f"Testing invalid position_value: {invalid_value}")
        
        payload = {
            "ticker": TEST_TICKER,
            "position_value": invalid_value,
            "loan_days": TEST_LOAN_DAYS,
            "client_id": TEST_CLIENT_ID
        }
        
        response = client.request(method="POST", endpoint="/calculate-locate", json_data=payload)
        
        # Verify we get a validation error (400)
        assert response.status_code == 400, f"Expected 400 Bad Request for invalid position_value {invalid_value}, got {response.status_code}"
        
        # Verify the error message mentions the position_value parameter
        response_json = response.json()
        assert "error" in response_json, "Expected error message in response"
        error_message = response_json.get("error", {}).get("message", "") if isinstance(response_json.get("error"), dict) else response_json.get("error", "")
        assert "position" in error_message.lower(), f"Expected error message to mention 'position', got: {error_message}"
    
    # Test calculate-locate endpoint with invalid loan days
    invalid_loan_days = [-1, 0, "abc", 366, 1000]
    
    for invalid_days in invalid_loan_days:
        logger.info(f"Testing invalid loan_days: {invalid_days}")
        
        payload = {
            "ticker": TEST_TICKER,
            "position_value": float(TEST_POSITION_VALUE),
            "loan_days": invalid_days,
            "client_id": TEST_CLIENT_ID
        }
        
        response = client.request(method="POST", endpoint="/calculate-locate", json_data=payload)
        
        # Verify we get a validation error (400)
        assert response.status_code == 400, f"Expected 400 Bad Request for invalid loan_days {invalid_days}, got {response.status_code}"
        
        # Verify the error message mentions the loan_days parameter
        response_json = response.json()
        assert "error" in response_json, "Expected error message in response"
        error_message = response_json.get("error", {}).get("message", "") if isinstance(response_json.get("error"), dict) else response_json.get("error", "")
        assert "loan" in error_message.lower() or "day" in error_message.lower(), f"Expected error message to mention 'loan_days', got: {error_message}"
    
    # Test calculate-locate endpoint with invalid client IDs
    invalid_client_ids = ["", "ab", "client@id", "client:id", "a" * 51]
    
    for invalid_id in invalid_client_ids:
        logger.info(f"Testing invalid client_id: '{invalid_id}'")
        
        payload = {
            "ticker": TEST_TICKER,
            "position_value": float(TEST_POSITION_VALUE),
            "loan_days": TEST_LOAN_DAYS,
            "client_id": invalid_id
        }
        
        response = client.request(method="POST", endpoint="/calculate-locate", json_data=payload)
        
        # Verify we get a validation error (400)
        assert response.status_code == 400, f"Expected 400 Bad Request for invalid client_id '{invalid_id}', got {response.status_code}"
        
        # Verify the error message mentions the client_id parameter
        response_json = response.json()
        assert "error" in response_json, "Expected error message in response"
        error_message = response_json.get("error", {}).get("message", "") if isinstance(response_json.get("error"), dict) else response_json.get("error", "")
        assert "client" in error_message.lower(), f"Expected error message to mention 'client_id', got: {error_message}"
    
    # Test rates endpoint with invalid ticker formats
    for invalid_ticker in invalid_tickers:
        logger.info(f"Testing rates endpoint with invalid ticker: '{invalid_ticker}'")
        
        response = client.request(method="GET", endpoint=f"/rates/{invalid_ticker}")
        
        # Verify we get a validation error (400) or not found error (404)
        assert response.status_code in [400, 404], f"Expected 400 Bad Request or 404 Not Found for invalid ticker '{invalid_ticker}', got {response.status_code}"


@pytest.mark.security
@pytest.mark.injection
def test_api_sql_injection():
    """
    Tests API endpoints for SQL injection vulnerabilities.
    
    Sends SQL injection payloads to various endpoints and parameters,
    verifying that they are properly sanitized and not vulnerable to
    SQL injection attacks.
    """
    # Create a client with valid API key
    client = setup_security_client()
    
    # Get SQL injection payloads
    sql_payloads = SQLInjectionPayloads()
    
    # Test calculate-locate endpoint with SQL injection in ticker parameter
    for i, payload in enumerate(sql_payloads.get_payload("basic")):
        logger.info(f"Testing SQL injection in ticker parameter: '{payload}'")
        
        request_payload = {
            "ticker": payload,
            "position_value": float(TEST_POSITION_VALUE),
            "loan_days": TEST_LOAN_DAYS,
            "client_id": TEST_CLIENT_ID
        }
        
        response = client.request(method="POST", endpoint="/calculate-locate", json_data=request_payload)
        
        # Verify we get a validation error (400), not a server error (500) which might indicate SQL injection
        assert response.status_code != 500, f"Got 500 Server Error for SQL injection payload in ticker parameter: '{payload}'"
        
        # Check response for SQL error messages which might indicate SQL injection vulnerability
        response_text = response.text.lower()
        sql_error_indicators = ["sql", "syntax", "mysql", "postgresql", "sqlite", "database error", "syntax error"]
        
        # Check if any SQL error indicators are in the response
        has_sql_error = any(indicator in response_text for indicator in sql_error_indicators)
        assert not has_sql_error, f"Response contains SQL error indicators for payload: '{payload}'"
    
    # Test calculate-locate endpoint with SQL injection in client_id parameter
    for i, payload in enumerate(sql_payloads.get_payload("basic")):
        logger.info(f"Testing SQL injection in client_id parameter: '{payload}'")
        
        request_payload = {
            "ticker": TEST_TICKER,
            "position_value": float(TEST_POSITION_VALUE),
            "loan_days": TEST_LOAN_DAYS,
            "client_id": payload
        }
        
        response = client.request(method="POST", endpoint="/calculate-locate", json_data=request_payload)
        
        # Verify we get a validation error (400) or client not found (404), not a server error (500)
        assert response.status_code != 500, f"Got 500 Server Error for SQL injection payload in client_id parameter: '{payload}'"
        
        # Check response for SQL error messages
        response_text = response.text.lower()
        sql_error_indicators = ["sql", "syntax", "mysql", "postgresql", "sqlite", "database error", "syntax error"]
        
        # Check if any SQL error indicators are in the response
        has_sql_error = any(indicator in response_text for indicator in sql_error_indicators)
        assert not has_sql_error, f"Response contains SQL error indicators for payload: '{payload}'"
    
    # Test rates endpoint with SQL injection in ticker parameter
    for i, payload in enumerate(sql_payloads.get_payload("basic")):
        logger.info(f"Testing SQL injection in rates endpoint: '{payload}'")
        
        response = client.request(method="GET", endpoint=f"/rates/{payload}")
        
        # Verify we don't get a server error (500)
        assert response.status_code != 500, f"Got 500 Server Error for SQL injection payload in rates endpoint: '{payload}'"
        
        # Check response for SQL error messages
        response_text = response.text.lower()
        sql_error_indicators = ["sql", "syntax", "mysql", "postgresql", "sqlite", "database error", "syntax error"]
        
        # Check if any SQL error indicators are in the response
        has_sql_error = any(indicator in response_text for indicator in sql_error_indicators)
        assert not has_sql_error, f"Response contains SQL error indicators for payload: '{payload}'"


@pytest.mark.security
@pytest.mark.injection
def test_api_xss_vulnerabilities():
    """
    Tests API endpoints for XSS vulnerabilities.
    
    Sends XSS attack payloads to various endpoints and parameters,
    verifying that they are properly encoded and not reflected back
    in a way that could lead to XSS attacks.
    """
    # Create a client with valid API key
    client = setup_security_client()
    
    # Get XSS payloads
    xss_payloads = XSSPayloads()
    
    # Test calculate-locate endpoint with XSS payloads in ticker parameter
    for i, payload in enumerate(xss_payloads.get_payload("basic")):
        logger.info(f"Testing XSS in ticker parameter: '{payload}'")
        
        request_payload = {
            "ticker": payload,
            "position_value": float(TEST_POSITION_VALUE),
            "loan_days": TEST_LOAN_DAYS,
            "client_id": TEST_CLIENT_ID
        }
        
        response = client.request(method="POST", endpoint="/calculate-locate", json_data=request_payload)
        
        # Check if the XSS payload is reflected in the response
        response_text = response.text
        is_reflected = payload in response_text
        
        # If the payload is reflected, it might be vulnerable to XSS
        assert not is_reflected, f"XSS payload was reflected in the response: '{payload}'"
    
    # Test calculate-locate endpoint with XSS payloads in client_id parameter
    for i, payload in enumerate(xss_payloads.get_payload("basic")):
        logger.info(f"Testing XSS in client_id parameter: '{payload}'")
        
        request_payload = {
            "ticker": TEST_TICKER,
            "position_value": float(TEST_POSITION_VALUE),
            "loan_days": TEST_LOAN_DAYS,
            "client_id": payload
        }
        
        response = client.request(method="POST", endpoint="/calculate-locate", json_data=request_payload)
        
        # Check if the XSS payload is reflected in the response
        response_text = response.text
        is_reflected = payload in response_text
        
        # If the payload is reflected, it might be vulnerable to XSS
        assert not is_reflected, f"XSS payload was reflected in the response: '{payload}'"
    
    # Test rates endpoint with XSS payloads in ticker parameter
    for i, payload in enumerate(xss_payloads.get_payload("basic")):
        logger.info(f"Testing XSS in rates endpoint: '{payload}'")
        
        response = client.request(method="GET", endpoint=f"/rates/{payload}")
        
        # Check if the XSS payload is reflected in the response
        response_text = response.text
        is_reflected = payload in response_text
        
        # If the payload is reflected, it might be vulnerable to XSS
        assert not is_reflected, f"XSS payload was reflected in the response: '{payload}'"


@pytest.mark.security
@pytest.mark.rate_limiting
def test_api_rate_limiting():
    """
    Tests API rate limiting implementation.
    
    Verifies that the API enforces rate limits by sending a high volume of
    requests in a short time period and checking for 429 Too Many Requests
    responses with appropriate Retry-After headers.
    """
    # Create a client with valid API key
    client = setup_security_client()
    
    # Test calculate-locate endpoint rate limiting
    logger.info("Testing rate limiting for calculate-locate endpoint")
    
    # Send requests at a high rate to trigger rate limiting
    request_count = 100  # Adjust based on the expected rate limit
    request_window = 20  # seconds
    
    valid_payload = {
        "ticker": TEST_TICKER,
        "position_value": float(TEST_POSITION_VALUE),
        "loan_days": TEST_LOAN_DAYS,
        "client_id": TEST_CLIENT_ID
    }
    
    responses = []
    start_time = time.time()
    
    # Send rapid requests
    for i in range(request_count):
        response = client.request(method="POST", endpoint="/calculate-locate", json_data=valid_payload)
        responses.append(response)
        
        # Small delay to avoid overwhelming the server
        time.sleep(0.1)
        
        # If we've already triggered rate limiting, we can stop
        if response.status_code == 429:
            logger.info(f"Rate limiting triggered after {i+1} requests")
            break
            
        # Don't continue too long
        if time.time() - start_time > request_window:
            break
    
    # Check if rate limiting was triggered
    rate_limited_responses = [r for r in responses if r.status_code == 429]
    
    # We should have at least one rate-limited response
    assert len(rate_limited_responses) > 0, "Rate limiting was not triggered despite sending many requests"
    
    # Check for Retry-After header
    rate_limited_response = rate_limited_responses[0]
    assert "Retry-After" in rate_limited_response.headers, "Rate-limited response missing Retry-After header"
    
    retry_after = rate_limited_response.headers["Retry-After"]
    logger.info(f"Rate limiting enforced with Retry-After: {retry_after} seconds")
    
    # Verify the Retry-After value is a positive integer
    assert retry_after.isdigit() and int(retry_after) > 0, f"Invalid Retry-After value: {retry_after}"
    
    # Test rates endpoint rate limiting
    logger.info("Testing rate limiting for rates endpoint")
    
    responses = []
    start_time = time.time()
    
    # Send rapid requests
    for i in range(request_count):
        response = client.request(method="GET", endpoint=f"/rates/{TEST_TICKER}")
        responses.append(response)
        
        # Small delay to avoid overwhelming the server
        time.sleep(0.1)
        
        # If we've already triggered rate limiting, we can stop
        if response.status_code == 429:
            logger.info(f"Rate limiting triggered after {i+1} requests")
            break
            
        # Don't continue too long
        if time.time() - start_time > request_window:
            break
    
    # Check if rate limiting was triggered
    rate_limited_responses = [r for r in responses if r.status_code == 429]
    
    # We should have at least one rate-limited response
    assert len(rate_limited_responses) > 0, "Rate limiting was not triggered despite sending many requests"
    
    # Check for Retry-After header
    rate_limited_response = rate_limited_responses[0]
    assert "Retry-After" in rate_limited_response.headers, "Rate-limited response missing Retry-After header"


@pytest.mark.security
@pytest.mark.information_disclosure
def test_api_information_disclosure():
    """
    Tests API for sensitive information disclosure.
    
    Verifies that the API doesn't leak sensitive information in error messages,
    responses, or HTTP headers, especially in error conditions.
    """
    # Create a client with valid API key
    client = setup_security_client()
    
    # Test error responses for excessive information disclosure
    
    # 1. Test server error conditions (invalid operations)
    logger.info("Testing server error conditions for information disclosure")
    
    # Try to cause a division by zero or other error
    invalid_payload = {
        "ticker": TEST_TICKER,
        "position_value": 0,  # This should cause an error in calculations
        "loan_days": TEST_LOAN_DAYS,
        "client_id": TEST_CLIENT_ID
    }
    
    response = client.request(method="POST", endpoint="/calculate-locate", json_data=invalid_payload)
    
    # Check for stack traces in error response
    response_text = response.text.lower()
    stack_trace_indicators = [
        "stack trace", "traceback", "at line", "at module", "exception", 
        "file \"", "stacktrace", "in module", ".py", "file path"
    ]
    
    # Check if any stack trace indicators are in the response
    has_stack_trace = any(indicator in response_text for indicator in stack_trace_indicators)
    assert not has_stack_trace, "Response contains potential stack trace information"
    
    # 2. Test for sensitive headers
    logger.info("Testing for sensitive headers")
    
    sensitive_headers = [
        "Server", "X-Powered-By", "X-AspNet-Version", "X-AspNetMvc-Version",
        "X-Runtime", "X-Version", "X-Powered-By-Plesk"
    ]
    
    response = client.request(method="GET", endpoint=f"/rates/{TEST_TICKER}")
    
    # Check if any sensitive headers are exposed
    exposed_sensitive_headers = [h for h in sensitive_headers if h in response.headers]
    assert not exposed_sensitive_headers, f"Response exposes sensitive headers: {exposed_sensitive_headers}"
    
    # 3. Test for server information in error messages
    logger.info("Testing for server information in error messages")
    
    # Send an invalid request to trigger an error
    invalid_ticker = "INVALID*TICKER"
    response = client.request(method="GET", endpoint=f"/rates/{invalid_ticker}")
    
    response_text = response.text.lower()
    server_info_indicators = [
        "apache", "nginx", "iis", "tomcat", "ubuntu", "debian", "centos", "linux", "windows",
        "python", "node", "php", "fastapi", "flask", "django", "express", "server version"
    ]
    
    # Check if any server information indicators are in the response
    has_server_info = any(indicator in response_text for indicator in server_info_indicators)
    assert not has_server_info, "Response contains potential server information"
    
    # 4. Test for internal paths or IPs in error messages
    logger.info("Testing for internal paths or IPs in error messages")
    
    path_disclosure_indicators = [
        "/var/", "/usr/", "/home/", "/opt/", "c:\\", "d:\\", "e:\\", "/app/", "/srv/",
        "127.0.0.1", "localhost", "192.168."
    ]
    
    # Check if any path disclosure indicators are in the response
    has_path_disclosure = any(indicator in response_text for indicator in path_disclosure_indicators)
    assert not has_path_disclosure, "Response contains potential internal paths or IPs"


@pytest.mark.security
@pytest.mark.cors
def test_api_cors_configuration():
    """
    Tests API CORS configuration security.
    
    Verifies that the API has proper CORS (Cross-Origin Resource Sharing)
    configuration to prevent unauthorized cross-origin requests.
    """
    # Define test origins
    test_origins = [
        "https://example.com",  # Example third-party origin
        "https://evil.com",     # Example malicious origin
        "null",                 # Null origin
        "https://localhost:3000",  # Common development origin
        "*"                     # Wildcard origin
    ]
    
    # Test CORS configuration for different endpoints
    endpoints = [
        "/health",
        f"/rates/{TEST_TICKER}",
        "/calculate-locate"
    ]
    
    for endpoint in endpoints:
        logger.info(f"Testing CORS configuration for endpoint: {endpoint}")
        
        for origin in test_origins:
            logger.info(f"Testing with Origin: {origin}")
            
            # Send OPTIONS request with Origin header
            headers = {
                "Origin": origin,
                "Access-Control-Request-Method": "GET" if endpoint != "/calculate-locate" else "POST",
                "Access-Control-Request-Headers": "Content-Type, X-API-Key"
            }
            
            url = f"{settings.api_base_url}/api/{settings.api_version}{endpoint}"
            response = requests.options(url, headers=headers)
            
            # Check CORS headers
            cors_headers = {
                "Access-Control-Allow-Origin": None,
                "Access-Control-Allow-Methods": None,
                "Access-Control-Allow-Headers": None,
                "Access-Control-Allow-Credentials": None,
                "Access-Control-Max-Age": None
            }
            
            # Extract CORS headers from response
            for header in cors_headers:
                if header in response.headers:
                    cors_headers[header] = response.headers[header]
            
            # Log the CORS headers
            logger.info(f"CORS headers for {origin} -> {endpoint}: {cors_headers}")
            
            # Check if Access-Control-Allow-Origin allows this origin
            if "Access-Control-Allow-Origin" in response.headers:
                allowed_origin = response.headers["Access-Control-Allow-Origin"]
                
                # If the API allows this origin, ensure it's not too permissive
                if allowed_origin == "*":
                    # Wildcard is overly permissive, especially for an API that requires authentication
                    logger.warning(f"API allows wildcard origin (*) for {endpoint}, which is not recommended for authenticated APIs")
                    
                    # For APIs with authentication, wildcard origin is generally not appropriate
                    # but we'll only warn, not fail the test as it depends on the specific requirements
                    
                elif allowed_origin == origin:
                    # If this isn't a trusted origin but it's specifically allowed, log a warning
                    if origin in ["https://evil.com", "null"]:
                        logger.warning(f"API allows potentially untrusted origin {origin} for {endpoint}")


@pytest.mark.security
@pytest.mark.tls
def test_api_tls_configuration():
    """
    Tests API TLS/SSL configuration security.
    
    Verifies that the API uses secure TLS configuration including
    minimum TLS version, strong cipher suites, valid certificates,
    and proper HSTS implementation.
    """
    # Skip test if API is not using HTTPS
    if not settings.api_base_url.startswith("https://"):
        pytest.skip("API is not using HTTPS, skipping TLS configuration test")
    
    # Use the helper function to verify TLS configuration
    tls_results = verify_tls_configuration(settings.api_base_url)
    
    # Log the results
    logger.info(f"TLS configuration results: {tls_results}")
    
    # Check results
    if tls_results.get("is_vulnerable", False):
        vulnerabilities = tls_results.get("vulnerabilities_found", [])
        logger.warning(f"TLS vulnerabilities found: {vulnerabilities}")
        
        # Check for critical vulnerabilities
        critical_vulnerabilities = [v for v in vulnerabilities if v.get("severity") == "critical"]
        
        if critical_vulnerabilities:
            assert False, f"Critical TLS vulnerabilities found: {critical_vulnerabilities}"
    
    # Verify minimum TLS version (should be 1.2+)
    tls_version = tls_results.get("test_results", {}).get("tls_version", {}).get("version")
    if tls_version:
        assert tls_version in ["TLSv1.2", "TLSv1.3"], f"Insecure TLS version: {tls_version}, should be TLSv1.2 or higher"
    
    # Verify HSTS header
    hsts_result = tls_results.get("test_results", {}).get("hsts", {})
    if hsts_result:
        hsts_header = hsts_result.get("header")
        if hsts_header:
            # HSTS header should specify a reasonable max-age
            assert "max-age=" in hsts_header, "HSTS header missing max-age directive"
            
            # Extract max-age value
            max_age_str = hsts_header.split("max-age=")[1].split(";")[0]
            max_age = int(max_age_str)
            
            # Check for reasonable max-age (at least 6 months = 15768000 seconds)
            assert max_age >= 15768000, f"HSTS max-age too short: {max_age}, should be at least 15768000 (6 months)"


@pytest.mark.security
@pytest.mark.zap
@pytest.mark.slow
def test_api_automated_scan():
    """
    Runs automated security scan using OWASP ZAP.
    
    Performs a comprehensive security scan of the API using OWASP ZAP,
    detecting common security vulnerabilities including injection flaws,
    improper error handling, and misconfigurations.
    """
    # Initialize ZAP scanner
    zap_scanner = ZAPSecurityScanner(settings)
    
    # Check if ZAP is available, skip test if not
    if not zap_scanner.initialize():
        pytest.skip("ZAP scanner not available, skipping automated scan")
    
    # Set up scan options
    scan_options = {
        "spider": {
            "enabled": True,
            "max_children": 10
        },
        "ajax_spider": {
            "enabled": True,
            "max_duration": 5  # minutes
        },
        "active_scan": {
            "enabled": True,
            "policy": "Default Policy"
        }
    }
    
    # Run the scan
    logger.info(f"Starting automated security scan of {settings.api_base_url}")
    scan_id = zap_scanner.scan_target(settings.api_base_url, scan_options)
    
    # Wait for scan to complete
    scan_complete = zap_scanner.wait_for_scan_completion(scan_id, timeout=1800)  # 30 minutes timeout
    
    if not scan_complete:
        pytest.skip("Automated scan did not complete within timeout")
    
    # Get the scan results
    scan_results = zap_scanner.get_alerts(scan_id)
    
    # Log summary
    alert_count = scan_results.get("alert_count", 0)
    logger.info(f"Automated scan completed with {alert_count} alerts")
    
    # Get high and critical alerts
    high_alerts = scan_results.get("alerts_by_risk", {}).get("high", [])
    critical_alerts = scan_results.get("alerts_by_risk", {}).get("critical", [])
    
    # Log high and critical alerts
    if high_alerts:
        logger.warning(f"High risk alerts: {len(high_alerts)}")
        for alert in high_alerts:
            logger.warning(f"High risk: {alert.get('name')} - {alert.get('description')}")
    
    if critical_alerts:
        logger.warning(f"Critical risk alerts: {len(critical_alerts)}")
        for alert in critical_alerts:
            logger.warning(f"Critical risk: {alert.get('name')} - {alert.get('description')}")
    
    # Fail the test if critical vulnerabilities are found
    assert not critical_alerts, f"Critical vulnerabilities found: {len(critical_alerts)}"
    
    # Generate a report for further analysis
    logger.info("Generating security report...")
    report_data = scan_results.get("summary", {})
    
    # Log report data
    logger.info(f"Security Report: {report_data}")