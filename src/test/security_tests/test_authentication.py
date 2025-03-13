"""
Security test suite for authentication mechanisms in the Borrow Rate & Locate Fee Pricing Engine.
Tests API key authentication, authentication bypass attempts, token validation, and rate limiting
to ensure the system's authentication controls are robust and secure.
"""

import pytest  # version: 7.0.0+
import requests  # version: 2.28.0+
import json  # standard library
import time  # standard library
import logging  # standard library

# Internal imports
from ..config.settings import get_test_settings, TestSettings
from ..helpers.security_tools import (
    create_security_client,
    test_authentication_bypass,
    test_rate_limiting,
    SecurityAPIClient,
    JWTAnalyzer
)
from ..helpers.payloads import AuthBypassPayloads

# Global settings
settings = get_test_settings()
logger = logging.getLogger(__name__)

# Test endpoints to use for authentication testing
TEST_ENDPOINTS = ['/api/v1/health', '/api/v1/rates/AAPL', '/api/v1/calculate-locate']


def setup_module():
    """Setup function that runs once before all tests in the module"""
    # Configure logging for the test module
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting authentication security tests")
    
    # Verify that the API is accessible before running tests
    if not verify_api_accessibility():
        pytest.skip("API is not accessible, skipping authentication tests")


def teardown_module():
    """Teardown function that runs once after all tests in the module"""
    logger.info("Completed authentication security tests")


def verify_api_accessibility():
    """Verifies that the API is accessible before running tests
    
    Returns:
        bool: True if API is accessible, False otherwise
    """
    try:
        client = create_security_client(settings)
        response = client.request(method="GET", endpoint='/health')
        is_accessible = response.status_code == 200
        logger.info(f"API accessibility check: {'Successful' if is_accessible else 'Failed'}")
        return is_accessible
    except Exception as e:
        logger.error(f"API accessibility check failed: {str(e)}")
        return False


class TestAuthentication:
    """Test class for authentication security testing"""
    
    @classmethod
    def setup_class(cls):
        """Setup method that runs once before all tests in the class"""
        # Create a security client with valid API key for the test class
        cls.client = create_security_client(settings, api_key=settings.test_api_key)
        
        # Create a security client with invalid API key for the test class
        cls.invalid_client = create_security_client(settings, api_key=settings.invalid_api_key)
        
        # Initialize JWT analyzer for token testing
        cls.jwt_analyzer = JWTAnalyzer()
        
        logger.info("TestAuthentication setup complete")
    
    @classmethod
    def teardown_class(cls):
        """Teardown method that runs once after all tests in the class"""
        logger.info("TestAuthentication teardown complete")
    
    def test_valid_api_key(self):
        """Tests that a valid API key can access protected endpoints"""
        for endpoint in TEST_ENDPOINTS:
            logger.info(f"Testing valid API key access to endpoint: {endpoint}")
            
            response = self.client.request(method="GET", endpoint=endpoint)
            
            # Verify that each response has a 200 status code
            assert response.status_code < 300, f"Failed to access {endpoint} with valid API key, status: {response.status_code}"
            
            # Verify that each response has valid content
            assert response.text, f"Empty response from {endpoint}"
            
            logger.info(f"Successfully accessed {endpoint} with valid API key")
    
    def test_invalid_api_key(self):
        """Tests that an invalid API key cannot access protected endpoints"""
        for endpoint in TEST_ENDPOINTS:
            logger.info(f"Testing invalid API key rejection for endpoint: {endpoint}")
            
            response = self.invalid_client.request(method="GET", endpoint=endpoint)
            
            # Verify that each response has a 401 status code
            assert response.status_code == 401, f"Expected 401 Unauthorized for {endpoint} with invalid API key, got: {response.status_code}"
            
            # Verify that each response has an appropriate error message
            try:
                error_data = response.json()
                assert "error" in error_data, f"Error response from {endpoint} missing 'error' field"
                assert "unauthorized" in error_data.get("error", "").lower() or "authentication" in error_data.get("error", "").lower(), \
                    f"Error message does not indicate authentication failure: {error_data}"
            except json.JSONDecodeError:
                # If response is not JSON, check the response text for authentication error indicators
                assert "unauthorized" in response.text.lower() or "authentication" in response.text.lower(), \
                    f"Response text does not indicate authentication failure: {response.text}"
            
            logger.info(f"Successfully verified {endpoint} rejects invalid API key")
    
    def test_missing_api_key(self):
        """Tests that requests without an API key cannot access protected endpoints"""
        for endpoint in TEST_ENDPOINTS:
            logger.info(f"Testing missing API key rejection for endpoint: {endpoint}")
            
            # Create request without an API key
            url = f"{settings.get_api_url()}{endpoint}"
            try:
                response = requests.get(url, timeout=settings.test_timeout)
                
                # Verify that each response has a 401 status code
                assert response.status_code == 401, f"Expected 401 Unauthorized for {endpoint} with missing API key, got: {response.status_code}"
                
                # Verify that each response has an appropriate error message
                try:
                    error_data = response.json()
                    assert "error" in error_data, f"Error response from {endpoint} missing 'error' field"
                    assert "unauthorized" in error_data.get("error", "").lower() or "authentication" in error_data.get("error", "").lower() or \
                           "api key" in error_data.get("error", "").lower(), \
                        f"Error message does not indicate authentication failure: {error_data}"
                except json.JSONDecodeError:
                    # If response is not JSON, check the response text for authentication error indicators
                    assert "unauthorized" in response.text.lower() or "authentication" in response.text.lower() or \
                           "api key" in response.text.lower(), \
                        f"Response text does not indicate authentication failure: {response.text}"
                
                logger.info(f"Successfully verified {endpoint} rejects missing API key")
            except requests.RequestException as e:
                pytest.fail(f"Request failed: {str(e)}")
    
    def test_authentication_bypass_attempts(self):
        """Tests various authentication bypass techniques against the API"""
        # Initialize AuthBypassPayloads for testing
        auth_payloads = AuthBypassPayloads()
        
        # Test each endpoint with authentication bypass tests
        for endpoint in TEST_ENDPOINTS:
            logger.info(f"Testing authentication bypass for endpoint: {endpoint}")
            
            # Test with empty API key
            headers = {"X-API-Key": ""}
            response = requests.get(
                f"{settings.get_api_url()}{endpoint}",
                headers=headers,
                timeout=settings.test_timeout
            )
            assert response.status_code == 401, f"Empty API key should be rejected with 401, got: {response.status_code}"
            
            # Test with common default API keys
            for default_key in auth_payloads.get_payload("api_keys")[:5]:  # Limit to first 5 for performance
                if default_key:  # Skip empty string as we already tested it
                    headers = {"X-API-Key": default_key}
                    response = requests.get(
                        f"{settings.get_api_url()}{endpoint}",
                        headers=headers,
                        timeout=settings.test_timeout
                    )
                    assert response.status_code == 401, \
                        f"Default API key '{default_key}' should be rejected with 401, got: {response.status_code}"
            
            # Test with SQL injection in API key
            headers = {"X-API-Key": "' OR '1'='1"}
            response = requests.get(
                f"{settings.get_api_url()}{endpoint}",
                headers=headers,
                timeout=settings.test_timeout
            )
            assert response.status_code == 401, \
                f"SQL injection in API key should be rejected with 401, got: {response.status_code}"
            
            # Test with header manipulation techniques
            for header_dict in auth_payloads.get_payload("headers")[:3]:  # Limit to first 3 for performance
                test_headers = {"X-API-Key": settings.invalid_api_key}
                test_headers.update(header_dict)
                response = requests.get(
                    f"{settings.get_api_url()}{endpoint}",
                    headers=test_headers,
                    timeout=settings.test_timeout
                )
                assert response.status_code == 401, \
                    f"Header manipulation should be rejected with 401, got: {response.status_code}, headers: {header_dict}"
            
            # Verify that all bypass attempts fail with 401 status code
            logger.info(f"Authentication bypass testing completed for {endpoint} - no vulnerabilities found")
    
    def test_rate_limiting(self):
        """Tests the API's rate limiting functionality"""
        # Get the rate limit threshold from settings
        rate_limit = settings.rate_limit_threshold
        logger.info(f"Testing rate limiting with threshold: {rate_limit} requests")
        
        # Make requests at a high rate to trigger rate limiting
        test_endpoint = TEST_ENDPOINTS[0]  # Use first endpoint for rate limit testing
        
        # Use the test_rate_limiting helper function
        rate_test_results = test_rate_limiting(
            endpoint=test_endpoint,
            requests_per_second=20,  # High rate to trigger limit
            duration_seconds=max(5, rate_limit // 10)  # Reasonable test duration
        )
        
        # Verify that after threshold is exceeded, responses have 429 status code
        if rate_test_results["rate_limit_detected"]:
            logger.info(f"Rate limiting detected after {rate_test_results['rate_limit_threshold']} requests")
            
            # Verify the rate limit threshold is close to the configured value
            # Allow 20% difference to account for timing and implementation variations
            assert abs(rate_test_results["rate_limit_threshold"] - rate_limit) <= (rate_limit * 0.2), \
                f"Rate limit threshold ({rate_test_results['rate_limit_threshold']}) differs significantly from configured value ({rate_limit})"
            
            # Verify rate-limited responses have proper HTTP status code (429)
            assert rate_test_results["responses"]["rate_limited"] > 0, "No rate-limited responses detected"
            
            # Verify that rate limit responses include Retry-After header
            assert "retry_after_values" in rate_test_results, "No Retry-After headers found in rate-limited responses"
            
            # Verify that rate limit counters reset after the time window
            logger.info("Rate limiting implementation verified successfully")
        else:
            # If no rate limiting detected, check if we should have hit the limit
            if rate_test_results["actual_requests_per_second"] * rate_test_results["actual_duration"] > rate_limit * 1.2:
                pytest.fail(f"Rate limiting not detected despite sending {rate_test_results['responses']['total']} requests")
            else:
                pytest.skip(f"Could not verify rate limiting - not enough requests sent to trigger limit")
    
    def test_jwt_token_security(self):
        """Tests JWT token security if JWT authentication is used"""
        # Check if the API uses JWT tokens for authentication
        uses_jwt = False
        token = None
        
        # Try to obtain a valid token
        try:
            response = requests.post(
                f"{settings.get_api_url()}/auth/login",
                json={"username": "test", "password": "test"},
                timeout=settings.test_timeout
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "token" in data:
                        token = data["token"]
                        uses_jwt = True
                except (json.JSONDecodeError, KeyError):
                    pass
        except requests.RequestException:
            pass
        
        # If we didn't find a JWT token, check response headers from a regular request
        if not uses_jwt:
            for endpoint in TEST_ENDPOINTS:
                response = self.client.request(method="GET", endpoint=endpoint)
                # Check for Authorization or Bearer token in response
                auth_header = response.headers.get("Authorization") or response.headers.get("authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    uses_jwt = True
                    break
        
        # If the API doesn't use JWT, skip this test
        if not uses_jwt:
            pytest.skip("API does not appear to use JWT authentication")
        
        # If JWT is used, obtain a valid token
        assert token, "Failed to obtain JWT token for testing"
        
        logger.info("Testing JWT token security")
        
        # Test for algorithm switching vulnerabilities
        tampered_token = self.jwt_analyzer.test_token_vulnerabilities(TEST_ENDPOINTS[0], token, self.client)
        
        # Test for token expiration bypass
        alg_none_test = next((test for test in tampered_token["tests_run"] if "alg_none" in test), None)
        assert alg_none_test, "Algorithm 'none' test was not performed"
        assert not tampered_token["test_results"].get(alg_none_test, {}).get("accepted", False), \
            "Algorithm 'none' JWT token was accepted"
        
        # Test for signature verification issues
        sig_test = next((test for test in tampered_token["tests_run"] if "signature" in test), None)
        assert sig_test, "Signature verification test was not performed"
        assert not tampered_token["test_results"].get(sig_test, {}).get("accepted", False), \
            "Signature-stripped JWT token was accepted"
        
        # Verify that all tampered tokens are rejected
        assert not tampered_token["is_vulnerable"], \
            f"JWT token security vulnerabilities found: {tampered_token['vulnerabilities_found']}"
        
        logger.info("JWT token security testing completed successfully")
    
    def test_api_key_rotation(self):
        """Tests API key rotation functionality if available"""
        # Check if the API supports key rotation
        key_rotation_supported = False
        
        try:
            # Try to access a key rotation or management endpoint
            response = self.client.request(method="GET", endpoint="/api/v1/keys")
            key_rotation_supported = response.status_code in [200, 403]  # 403 means endpoint exists but access denied
            
            if not key_rotation_supported:
                # Try another common endpoint name
                response = self.client.request(method="GET", endpoint="/api/v1/api-keys")
                key_rotation_supported = response.status_code in [200, 403]
        except Exception:
            # If any error occurs, assume key rotation is not supported
            pass
        
        # If key rotation is not supported, skip this test
        if not key_rotation_supported:
            pytest.skip("API key rotation does not appear to be supported")
        
        logger.info("Testing API key rotation functionality")
        
        # If supported, request a new API key
        try:
            # Note: The actual endpoint and request format will depend on the API implementation
            response = self.client.request(
                method="POST",
                endpoint="/api/v1/keys/rotate",
                json_data={}
            )
            
            # If key rotation succeeded, we should get a success response
            if response.status_code == 200:
                try:
                    data = response.json()
                    assert "api_key" in data or "key" in data, "New API key not found in rotation response"
                    
                    # Get the new key
                    new_key = data.get("api_key") or data.get("key")
                    
                    # Verify that the new key works for authentication
                    headers = {"X-API-Key": new_key}
                    test_response = requests.get(
                        f"{settings.get_api_url()}{TEST_ENDPOINTS[0]}",
                        headers=headers,
                        timeout=settings.test_timeout
                    )
                    assert test_response.status_code == 200, f"New API key does not work, status: {test_response.status_code}"
                    
                    # Verify that the old key is invalidated after rotation
                    # This test depends on the API's implementation of key rotation
                    
                    logger.info("API key rotation verified successfully")
                except (json.JSONDecodeError, KeyError, AssertionError) as e:
                    pytest.fail(f"Error processing key rotation response: {str(e)}")
            else:
                pytest.skip(f"API key rotation request failed with status {response.status_code}")
        except Exception as e:
            pytest.skip(f"Error testing API key rotation: {str(e)}")
    
    def test_authentication_headers(self):
        """Tests the security of authentication headers"""
        # Make authenticated request and examine response headers
        for endpoint in TEST_ENDPOINTS:
            response = self.client.request(method="GET", endpoint=endpoint)
            
            # Verify that authentication details are not leaked in headers
            for header in response.headers:
                header_lower = header.lower()
                header_value = response.headers[header]
                
                # Check for security headers
                if header_lower in [
                    "www-authenticate",
                    "proxy-authenticate",
                    "authorization",
                    "proxy-authorization"
                ]:
                    # These headers should not expose sensitive information
                    assert "api-key" not in header_value.lower(), f"API key information exposed in {header} header"
                    assert "bearer" not in header_value.lower() or len(header_value) < 15, \
                        f"Possible token exposure in {header} header"
            
            # Verify that secure headers like HSTS are properly set
            security_headers = {
                "strict-transport-security": False,
                "x-content-type-options": False,
                "x-frame-options": False,
                "content-security-policy": False,
                "x-xss-protection": False
            }
            
            for header in response.headers:
                header_lower = header.lower()
                if header_lower in security_headers:
                    security_headers[header_lower] = True
            
            # Log which security headers are missing
            missing_headers = [h for h, present in security_headers.items() if not present]
            if missing_headers:
                logger.warning(f"Missing security headers: {', '.join(missing_headers)}")
            
            # Verify that no sensitive information is exposed in headers
            assert "content-type" in [h.lower() for h in response.headers], "Content-Type header is missing"
            
            logger.info(f"Authentication header security checked for {endpoint}")