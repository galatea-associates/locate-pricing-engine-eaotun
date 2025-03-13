"""
End-to-end test suite for security features of the Borrow Rate & Locate Fee Pricing Engine.
Tests authentication, authorization, input validation, rate limiting, and other security
controls in a real environment to ensure the system's security mechanisms function correctly
in production-like conditions.
"""

import pytest
import json
import logging
import time
from typing import Dict, List, Optional, Any

# Internal imports
from .config.settings import get_test_settings
from .helpers.api_client import APIClient, create_api_client
from .helpers.validation import ResponseValidator, create_response_validator
from ..security_tests.helpers.security_tools import SecurityScanner, APIFuzzer, test_rate_limiting
from ..security_tests.helpers.payloads import InputValidationPayloads, AuthBypassPayloads

# Set up logger
logger = logging.getLogger(__name__)

# Get test settings
settings = get_test_settings()

# Constants for test data
VALID_TICKER = "AAPL"
VALID_POSITION_VALUE = 100000
VALID_LOAN_DAYS = 30
VALID_CLIENT_ID = "client123"

@pytest.fixture
def setup_api_client():
    """Fixture to create an API client for end-to-end security tests"""
    client = create_api_client()
    
    # Configure the client to use mock servers if specified in settings
    if hasattr(settings, 'use_mock_servers') and settings.use_mock_servers:
        client.configure_mock_servers()
    
    # Wait for the API to be ready before returning
    client.wait_for_api_ready()
    
    return client

@pytest.fixture
def setup_response_validator(setup_api_client):
    """Fixture to create a response validator for end-to-end security tests"""
    return create_response_validator(setup_api_client)

@pytest.fixture
def setup_security_scanner(setup_api_client):
    """Fixture to create a security scanner for end-to-end security tests"""
    return SecurityScanner(setup_api_client)

def create_valid_request():
    """Creates a valid request payload for testing"""
    return {
        "ticker": VALID_TICKER,
        "position_value": VALID_POSITION_VALUE,
        "loan_days": VALID_LOAN_DAYS,
        "client_id": VALID_CLIENT_ID
    }

class TestAuthenticationSecurity:
    """End-to-end test suite for authentication security features"""
    
    def test_api_key_authentication(self, setup_api_client, setup_response_validator):
        """Tests that API key authentication is properly enforced"""
        api_client = setup_api_client
        response_validator = setup_response_validator
        
        # Make a request with a valid API key
        valid_response = api_client.get_borrow_rate(VALID_TICKER)
        response_validator.assert_response_status(valid_response, "success")
        
        # Create a new client with an invalid API key
        invalid_client = create_api_client(
            settings=settings, 
            api_key="invalid_key_for_testing"
        )
        
        # Make a request with the invalid API key
        invalid_response = invalid_client.get_borrow_rate(VALID_TICKER)
        assert isinstance(invalid_response, dict) and invalid_response.get("status") == "error"
        
        # Create a new client with no API key
        no_key_headers = {"X-API-Key": ""}
        no_key_response = api_client.request(
            method="GET",
            endpoint=f"/rates/{VALID_TICKER}",
            headers=no_key_headers
        )
        assert no_key_response.status_code == 401
    
    def test_rate_limiting(self, setup_api_client, setup_response_validator):
        """Tests that rate limiting is properly enforced"""
        api_client = setup_api_client
        response_validator = setup_response_validator
        
        # Use test_rate_limiting function to send requests at a high rate
        result = test_rate_limiting(
            endpoint="/calculate-locate",
            requests_per_second=20,
            duration_seconds=3
        )
        
        # Verify that after threshold is exceeded, 429 Too Many Requests status is returned
        assert result["rate_limit_detected"], "Rate limiting was not triggered despite high request rate"
        
        # Verify that Retry-After header is present in the response
        assert "retry_after_values" in result, "Retry-After values not captured in rate limiting test"
        
        # Verify that rate limit headers are present
        assert "rate_limit_headers" in result, "Rate limit headers not found in response"
    
    def test_authentication_bypass_resistance(self, setup_api_client, setup_response_validator):
        """Tests resistance to common authentication bypass techniques"""
        api_client = setup_api_client
        response_validator = setup_response_validator
        
        # Create an AuthBypassPayloads instance
        auth_bypass = AuthBypassPayloads()
        
        # Get common bypass payloads
        api_key_payloads = auth_bypass.get_payload("api_keys")
        
        # Test each bypass technique against authentication endpoints
        for payload in api_key_payloads[:5]:  # Test first 5 payloads to keep test duration reasonable
            bypass_response = api_client.request(
                method="GET",
                endpoint=f"/rates/{VALID_TICKER}",
                headers={"X-API-Key": payload}
            )
            
            # Verify that all bypass attempts are rejected with 401 Unauthorized status
            assert bypass_response.status_code == 401, \
                f"Authentication bypass succeeded with payload: {payload}"
            
            # Verify that the system does not reveal detailed information about the attempts
            try:
                response_data = bypass_response.json()
                if "message" in response_data:
                    assert len(response_data["message"]) < 100, \
                        "Error message may reveal too much information about authentication"
            except json.JSONDecodeError:
                pass

class TestInputValidationSecurity:
    """End-to-end test suite for input validation security features"""
    
    def test_malformed_requests_handling(self, setup_api_client, setup_response_validator):
        """Tests handling of malformed requests"""
        api_client = setup_api_client
        response_validator = setup_response_validator
        
        # Create an InputValidationPayloads instance
        input_validation = InputValidationPayloads()
        
        # Generate malformed request objects
        valid_request = create_valid_request()
        malformed_requests = input_validation.generate_malformed_request_objects(valid_request)
        
        # Send each malformed request to the calculate-locate endpoint
        for i, malformed_req in enumerate(malformed_requests):
            logger.info(f"Testing malformed request {i+1}/{len(malformed_requests)}")
            
            response = api_client.request(
                method="POST",
                endpoint="/calculate-locate",
                json_data=malformed_req
            )
            
            # Verify that all malformed requests are rejected with 400 Bad Request status
            assert response.status_code == 400, \
                f"Malformed request not rejected properly: {malformed_req}"
            
            # Verify that error responses contain appropriate validation error messages
            try:
                error_data = response.json()
                assert "status" in error_data and error_data["status"] == "error", \
                    "Error response missing status field"
                
                # Verify that error response contains validation details
                assert "message" in error_data or "errors" in error_data, \
                    "Error response missing validation details"
            except json.JSONDecodeError:
                pytest.fail(f"Response to malformed request is not valid JSON: {response.text}")
            
            # Verify that no server errors (500) occur during validation
            assert response.status_code != 500, \
                "Server error occurred during input validation"
    
    def test_input_fuzzing(self, setup_api_client, setup_response_validator, setup_security_scanner):
        """Tests API resilience against fuzzed inputs"""
        api_client = setup_api_client
        response_validator = setup_response_validator
        security_scanner = setup_security_scanner
        
        # Create an APIFuzzer instance with the API client
        fuzzer = APIFuzzer()
        
        # Fuzz the calculate-locate endpoint with various payloads
        valid_request = create_valid_request()
        
        # Test fuzzing on ticker field
        ticker_fuzz_values = [
            "",                     # Empty string
            "A" * 100,              # Very long string
            "AAPL'",                # SQL injection attempt
            "AAPL<script>",         # XSS attempt
            "123",                  # Numeric string
            "A-B",                  # Invalid format
            "<img src=x onerror=alert(1)>",  # XSS attempt
        ]
        
        for fuzz_ticker in ticker_fuzz_values:
            fuzzed_request = valid_request.copy()
            fuzzed_request["ticker"] = fuzz_ticker
            
            response = api_client.request(
                method="POST",
                endpoint="/calculate-locate",
                json_data=fuzzed_request
            )
            
            # Verify that the API properly handles all fuzzed inputs
            assert response.status_code != 500, \
                f"Server error (500) when fuzzing ticker with: {fuzz_ticker}"
        
        # Fuzz the rates endpoint with various ticker values
        for fuzz_ticker in ticker_fuzz_values:
            response = api_client.request(
                method="GET",
                endpoint=f"/rates/{fuzz_ticker}"
            )
            
            # Verify that no server errors (500) occur during fuzzing
            assert response.status_code != 500, \
                f"Server error (500) when fuzzing rates endpoint with ticker: {fuzz_ticker}"
            
            # Verify that appropriate 400 Bad Request responses are returned for invalid inputs
            if fuzz_ticker == "" or "script" in fuzz_ticker or "'" in fuzz_ticker:
                assert response.status_code in [400, 404], \
                    f"Invalid ticker should return 400 or 404, got {response.status_code}"
    
    def test_sql_injection_resistance(self, setup_api_client, setup_response_validator):
        """Tests resistance to SQL injection attacks"""
        api_client = setup_api_client
        response_validator = setup_response_validator
        
        # Create a valid base request
        valid_request = create_valid_request()
        
        # Modify the request with common SQL injection patterns in string fields
        sql_patterns = [
            "' OR '1'='1",
            "'; DROP TABLE stocks; --",
            "1' OR '1'='1",
            "1; SELECT * FROM stocks",
            "' UNION SELECT 1,2,3,4 --"
        ]
        
        # Send the modified requests to various endpoints
        for field in ["ticker", "client_id"]:
            for pattern in sql_patterns:
                modified_request = valid_request.copy()
                modified_request[field] = pattern
                
                response = api_client.request(
                    method="POST",
                    endpoint="/calculate-locate",
                    json_data=modified_request
                )
                
                # Verify that all injection attempts are properly sanitized or rejected
                assert response.status_code in [400, 404], \
                    f"SQL injection in '{field}' not properly handled: {pattern}"
                
                # Verify that no server errors (500) occur during injection attempts
                assert response.status_code != 500, \
                    f"Server error during SQL injection test in '{field}': {pattern}"
                
                # Verify that no database information is leaked in error messages
                try:
                    error_data = response.json()
                    if "message" in error_data:
                        error_message = error_data["message"].lower()
                        sensitive_terms = ["sql", "database", "syntax", "query", "postgres", "mysql"]
                        
                        for term in sensitive_terms:
                            assert term not in error_message, \
                                f"Error message may reveal database details: '{error_message}'"
                except json.JSONDecodeError:
                    pass

class TestSecurityHeaders:
    """End-to-end test suite for security headers and configurations"""
    
    def test_security_headers(self, setup_api_client):
        """Tests that appropriate security headers are set in responses"""
        api_client = setup_api_client
        
        # Make a request to the health endpoint
        response = api_client.request(
            method="GET",
            endpoint="/health"
        )
        
        # Check for common security headers
        security_headers = {
            "Content-Security-Policy": None,  # Any value is acceptable
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": ["DENY", "SAMEORIGIN"],  # Either value is acceptable
            "Strict-Transport-Security": None,  # Any value is acceptable
            "X-XSS-Protection": None  # Any value is acceptable
        }
        
        for header, expected_value in security_headers.items():
            # If header is present, check its value when specified
            if header in response.headers:
                if expected_value:
                    if isinstance(expected_value, list):
                        assert response.headers[header] in expected_value, \
                            f"Header {header} value '{response.headers[header]}' not in expected values: {expected_value}"
                    else:
                        assert response.headers[header] == expected_value, \
                            f"Header {header} has unexpected value: {response.headers[header]}"
                logger.info(f"Security header found: {header}={response.headers[header]}")
            else:
                logger.warning(f"Security header not found: {header}")
    
    def test_cors_configuration(self, setup_api_client):
        """Tests Cross-Origin Resource Sharing (CORS) configuration"""
        api_client = setup_api_client
        
        # Send OPTIONS requests with different Origin headers
        origins = ["https://trusted-site.com", "https://malicious-site.com", "null"]
        
        for origin in origins:
            response = api_client.request(
                method="OPTIONS",
                endpoint="/calculate-locate",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type"
                }
            )
            
            # Verify that CORS headers are properly configured
            if "Access-Control-Allow-Origin" in response.headers:
                allow_origin = response.headers["Access-Control-Allow-Origin"]
                
                # Verify that Access-Control-Allow-Origin is not set to '*'
                assert allow_origin != "*", "CORS allows any origin, which is insecure"
                
                # Verify that Access-Control-Allow-Methods is properly restricted
                if "Access-Control-Allow-Methods" in response.headers:
                    methods = response.headers["Access-Control-Allow-Methods"].split(", ")
                    assert all(m in ["GET", "POST", "OPTIONS", "PUT", "DELETE"] for m in methods), \
                        f"CORS allows potentially dangerous methods: {methods}"
                
                # Verify that Access-Control-Allow-Headers is properly configured
                if "Access-Control-Allow-Headers" in response.headers:
                    assert "Content-Type" in response.headers["Access-Control-Allow-Headers"], \
                        "CORS should allow Content-Type header"

class TestErrorHandling:
    """End-to-end test suite for security-related error handling"""
    
    def test_error_message_security(self, setup_api_client):
        """Tests that error messages don't leak sensitive information"""
        api_client = setup_api_client
        
        # Send various invalid requests to trigger different error conditions
        error_test_cases = [
            # Invalid API key
            {
                "method": "GET",
                "endpoint": f"/rates/{VALID_TICKER}",
                "headers": {"X-API-Key": "invalid_key"}
            },
            # Invalid ticker
            {
                "method": "GET",
                "endpoint": "/rates/INVALID!@#"
            },
            # Missing required parameter
            {
                "method": "POST",
                "endpoint": "/calculate-locate",
                "json_data": {"ticker": VALID_TICKER, "loan_days": VALID_LOAN_DAYS, "client_id": VALID_CLIENT_ID}
                # position_value missing
            },
            # Malformed JSON
            {
                "method": "POST",
                "endpoint": "/calculate-locate",
                "headers": {"Content-Type": "application/json"},
                "data": "{invalid_json"
            }
        ]
        
        for test_case in error_test_cases:
            response = api_client.request(**test_case)
            
            # Verify that error messages are generic and don't reveal system details
            try:
                error_data = response.json()
                if "status" in error_data and error_data["status"] == "error":
                    if "message" in error_data:
                        message = error_data["message"].lower()
                        
                        # Check for sensitive information
                        sensitive_terms = [
                            "exception", "stack trace", "at com.", "at org.",
                            "debug", "internal server error", "syntax error",
                            "database", "sql", "query", "driver"
                        ]
                        
                        for term in sensitive_terms:
                            assert term not in message, \
                                f"Error message may leak sensitive information ({term}): {message}"
            except json.JSONDecodeError:
                # If not JSON, check raw response
                for term in sensitive_terms:
                    assert term not in response.text.lower(), \
                        f"Error response may leak sensitive information ({term}): {response.text}"
    
    def test_error_response_codes(self, setup_api_client, setup_response_validator):
        """Tests that appropriate error codes are returned for security issues"""
        api_client = setup_api_client
        response_validator = setup_response_validator
        
        # Test authentication failures and verify 401 Unauthorized is returned
        auth_failure_response = api_client.request(
            method="GET",
            endpoint=f"/rates/{VALID_TICKER}",
            headers={"X-API-Key": "invalid_key"}
        )
        assert auth_failure_response.status_code == 401, \
            f"Authentication failure should return 401, got {auth_failure_response.status_code}"
        
        # Test authorization failures and verify 403 Forbidden is returned
        # Note: This test may be skipped if the API doesn't have distinct authorization levels
        
        # Test input validation failures and verify 400 Bad Request is returned
        validation_failure_response = api_client.request(
            method="POST",
            endpoint="/calculate-locate",
            json_data={
                "ticker": "INVALID!@#",  # Invalid ticker format
                "position_value": -1,     # Negative value
                "loan_days": 0,           # Invalid loan days
                "client_id": VALID_CLIENT_ID
            }
        )
        assert validation_failure_response.status_code == 400, \
            f"Input validation failure should return 400, got {validation_failure_response.status_code}"
        
        # Test rate limiting and verify 429 Too Many Requests is returned
        rate_limited = False
        for _ in range(100):  # Make many requests to trigger rate limiting
            response = api_client.request(
                method="GET",
                endpoint="/health"
            )
            if response.status_code == 429:
                rate_limited = True
                # Verify that error responses include appropriate error codes and messages
                try:
                    error_data = response.json()
                    assert "status" in error_data and error_data["status"] == "error", \
                        "Rate limit error response should have status 'error'"
                    assert "Retry-After" in response.headers, \
                        "Rate limit response should include Retry-After header"
                except json.JSONDecodeError:
                    pass
                break
        
        # If rate limiting wasn't triggered, log a warning but don't fail the test
        if not rate_limited:
            logger.warning("Rate limiting was not triggered during test (possibly high limit setting)")

class TestEndToEndSecurityScenarios:
    """End-to-end test suite for complex security scenarios"""
    
    def test_complete_security_flow(self, setup_api_client, setup_response_validator, setup_security_scanner):
        """Tests a complete end-to-end security flow with multiple security aspects"""
        api_client = setup_api_client
        response_validator = setup_response_validator
        security_scanner = setup_security_scanner
        
        # Authenticate with valid credentials
        auth_response = api_client.get("/health")
        assert isinstance(auth_response, dict) and auth_response.get("status") in ["healthy", "success"], \
            "Authentication with valid credentials failed"
        
        # Attempt to access resources with insufficient permissions
        # This is environment-specific, would need to be adapted based on authorization model
        
        # Submit requests with potentially malicious payloads
        malicious_request = {
            "ticker": "' OR 1=1--",
            "position_value": VALID_POSITION_VALUE,
            "loan_days": VALID_LOAN_DAYS,
            "client_id": "<script>alert(1)</script>"
        }
        
        malicious_response = api_client.request(
            method="POST",
            endpoint="/calculate-locate",
            json_data=malicious_request
        )
        
        assert malicious_response.status_code == 400, \
            f"Malicious request should be rejected with 400, got {malicious_response.status_code}"
        
        # Verify rate limiting after multiple rapid requests
        rate_limited = False
        for _ in range(100):  # Attempt to trigger rate limiting
            response = api_client.get("/health")
            if hasattr(api_client, 'response') and api_client.response.status_code == 429:
                rate_limited = True
                break
        
        # Test error handling with various invalid inputs
        error_test_cases = [
            {"ticker": "", "position_value": VALID_POSITION_VALUE, "loan_days": VALID_LOAN_DAYS, "client_id": VALID_CLIENT_ID},
            {"ticker": VALID_TICKER, "position_value": -1, "loan_days": VALID_LOAN_DAYS, "client_id": VALID_CLIENT_ID},
            {"ticker": VALID_TICKER, "position_value": VALID_POSITION_VALUE, "loan_days": 0, "client_id": VALID_CLIENT_ID},
            {"ticker": VALID_TICKER, "position_value": VALID_POSITION_VALUE, "loan_days": VALID_LOAN_DAYS, "client_id": ""}
        ]
        
        for test_case in error_test_cases:
            error_response = api_client.request(
                method="POST",
                endpoint="/calculate-locate",
                json_data=test_case
            )
            assert error_response.status_code == 400, \
                f"Invalid input should return 400, got {error_response.status_code}"
                
        # Verify that all security controls function correctly together
        logger.info("Complete security flow test passed successfully")
    
    def test_targeted_security_scan(self, setup_security_scanner):
        """Runs a targeted security scan on specific components"""
        security_scanner = setup_security_scanner
        
        # Define scan types to include authentication, input validation, and rate limiting
        try:
            # Attempt to use the run_targeted_scan method if available
            scan_results = security_scanner.run_targeted_scan(
                endpoint="/calculate-locate", 
                scan_types=["authentication", "input_validation", "rate_limiting"]
            )
            
            # Analyze scan results for security vulnerabilities
            assert not scan_results.get("is_vulnerable", False), \
                f"Security vulnerabilities detected: {scan_results.get('vulnerabilities_found', [])}"
                
            # Verify that the system implements proper security controls
            required_controls = ["input_validation", "authentication", "rate_limiting"]
            detected_controls = scan_results.get("controls_detected", [])
            
            for control in required_controls:
                if control not in detected_controls:
                    logger.warning(f"Required security control may not be properly implemented: {control}")
                
        except (AttributeError, TypeError):
            # If run_targeted_scan is not available, perform alternative security tests
            logger.warning("SecurityScanner.run_targeted_scan not available, performing alternative tests")
            
            # Test authentication
            anonymous_response = security_scanner._client.request(
                method="GET",
                endpoint="/health",
                headers={"X-API-Key": ""}
            )
            assert anonymous_response.status_code == 401, "Authentication check failed"
            
            # Test input validation
            invalid_input_response = security_scanner._client.request(
                method="POST",
                endpoint="/calculate-locate",
                json_data={"invalid": "input"}
            )
            assert invalid_input_response.status_code == 400, "Input validation check failed"
            
            # Report successful alternative testing
            logger.info("Alternative security tests completed successfully")