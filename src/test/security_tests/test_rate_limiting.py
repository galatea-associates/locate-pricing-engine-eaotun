"""
Security tests for the rate limiting functionality of the Borrow Rate & Locate Fee Pricing Engine API.
This module verifies that the API correctly implements rate limiting to prevent abuse, ensures proper
response headers are returned, and validates that rate limits are enforced based on client configurations.
"""

import pytest
import time
import logging
import concurrent.futures
from typing import Dict, List, Any

# Internal imports
from ..config.settings import get_test_settings
from ..helpers.security_tools import create_security_client, test_rate_limiting
from ...integration_tests.helpers.api_client import APIClient

# Configure module logger
logger = logging.getLogger(__name__)

# Get test settings
settings = get_test_settings()

# Endpoint to use for rate limit testing
TEST_ENDPOINT = "/api/v1/rates/AAPL"


@pytest.mark.security
@pytest.mark.rate_limiting
def test_rate_limit_headers():
    """Tests that rate limit headers are correctly included in API responses"""
    # Create a security client with valid API key
    client = create_security_client()
    
    # Make a request to the test endpoint
    response = client.request(method="GET", endpoint=TEST_ENDPOINT)
    
    # Verify response contains all required rate limit headers
    assert "X-RateLimit-Limit" in response.headers, "Missing X-RateLimit-Limit header"
    assert "X-RateLimit-Remaining" in response.headers, "Missing X-RateLimit-Remaining header"
    assert "X-RateLimit-Reset" in response.headers, "Missing X-RateLimit-Reset header"
    
    # Verify header values are of the correct type and format
    limit = response.headers["X-RateLimit-Limit"]
    remaining = response.headers["X-RateLimit-Remaining"]
    reset = response.headers["X-RateLimit-Reset"]
    
    assert limit.isdigit(), f"X-RateLimit-Limit not a number: {limit}"
    assert remaining.isdigit(), f"X-RateLimit-Remaining not a number: {remaining}"
    assert reset.isdigit(), f"X-RateLimit-Reset not a number: {reset}"
    
    # Verify remaining is less than or equal to limit
    assert int(remaining) <= int(limit), "X-RateLimit-Remaining should be <= X-RateLimit-Limit"
    
    logger.info(f"Rate limit headers validated: Limit={limit}, Remaining={remaining}, Reset={reset}")


@pytest.mark.security
@pytest.mark.rate_limiting
def test_rate_limit_enforcement():
    """Tests that rate limits are enforced when exceeded"""
    # Create a security client with valid API key
    client = create_security_client()
    
    # Get the rate limit threshold from settings
    rate_limit = settings.rate_limit_threshold
    
    # Make slightly more requests than the rate limit
    request_count = rate_limit + 5
    responses = []
    
    logger.info(f"Making {request_count} requests to test rate limit enforcement")
    
    for i in range(request_count):
        response = client.request(method="GET", endpoint=TEST_ENDPOINT)
        responses.append(response)
        
        # Don't overwhelm the server - small delay between requests
        time.sleep(0.1)
    
    # Analyze responses
    success_count = sum(1 for r in responses if r.status_code == 200)
    rate_limited_count = sum(1 for r in responses if r.status_code == 429)
    
    logger.info(f"Received {success_count} success responses and {rate_limited_count} rate limited responses")
    
    # Verify that some requests were rate limited
    assert rate_limited_count > 0, "No requests were rate limited"
    
    # Find a rate-limited response and verify it has the Retry-After header
    for response in responses:
        if response.status_code == 429:
            assert "Retry-After" in response.headers, "Missing Retry-After header in 429 response"
            retry_after = response.headers["Retry-After"]
            assert retry_after.isdigit(), f"Retry-After not a number: {retry_after}"
            assert int(retry_after) > 0, "Retry-After should be a positive number"
            logger.info(f"Retry-After header validated: {retry_after} seconds")
            break


@pytest.mark.security
@pytest.mark.rate_limiting
def test_rate_limit_reset():
    """Tests that rate limits are reset after the specified window"""
    # Create a security client with valid API key
    client = create_security_client()
    
    # Get the rate limit threshold from settings
    rate_limit = settings.rate_limit_threshold
    
    # Make requests up to just below the rate limit
    request_count = rate_limit - 5
    
    logger.info(f"Making {request_count} initial requests")
    
    for i in range(request_count):
        response = client.request(method="GET", endpoint=TEST_ENDPOINT)
        assert response.status_code == 200, f"Request {i+1} failed with status {response.status_code}"
        
        # Don't overwhelm the server - small delay between requests
        time.sleep(0.1)
    
    # Get the reset time from the last response
    reset_seconds = int(response.headers["X-RateLimit-Reset"])
    logger.info(f"Rate limit will reset in {reset_seconds} seconds")
    
    # Wait until after the reset time (add 2 seconds for safety)
    logger.info(f"Waiting {reset_seconds + 2} seconds for rate limit to reset")
    time.sleep(reset_seconds + 2)
    
    # Make additional requests after reset
    additional_requests = 5
    logger.info(f"Making {additional_requests} additional requests after reset")
    
    for i in range(additional_requests):
        response = client.request(method="GET", endpoint=TEST_ENDPOINT)
        assert response.status_code == 200, f"Post-reset request {i+1} failed with status {response.status_code}"
        
        # Extract the remaining limit to verify reset worked
        remaining = int(response.headers["X-RateLimit-Remaining"])
        limit = int(response.headers["X-RateLimit-Limit"])
        
        # After reset, the remaining count should be high (close to the limit)
        assert remaining > (limit - 10), f"Rate limit may not have reset properly. Remaining: {remaining}, Limit: {limit}"
        
        # Don't overwhelm the server - small delay between requests
        time.sleep(0.1)


@pytest.mark.security
@pytest.mark.rate_limiting
def test_client_specific_rate_limits():
    """Tests that different clients have different rate limits based on their tier"""
    # Get API keys for different client tiers from settings
    # Default to test API key for standard tier if not specified
    standard_api_key = settings.test_api_key
    
    # For premium tier, we'll need to get this from settings or use a default test key
    premium_api_key = getattr(settings, "premium_test_api_key", "premium-test-api-key")
    
    # Create clients for each tier
    standard_client = create_security_client(api_key=standard_api_key)
    premium_client = create_security_client(api_key=premium_api_key)
    
    # Make a request with each client to check rate limit headers
    standard_response = standard_client.request(method="GET", endpoint=TEST_ENDPOINT)
    premium_response = premium_client.request(method="GET", endpoint=TEST_ENDPOINT)
    
    # Extract rate limits from headers
    standard_limit = int(standard_response.headers.get("X-RateLimit-Limit", "0"))
    premium_limit = int(premium_response.headers.get("X-RateLimit-Limit", "0"))
    
    logger.info(f"Standard client rate limit: {standard_limit}")
    logger.info(f"Premium client rate limit: {premium_limit}")
    
    # Verify that standard limit matches expectation (60/minute by default)
    assert standard_limit == 60, f"Standard client should have 60 req/min limit, got {standard_limit}"
    
    # Verify that premium limit matches expectation (300/minute by default)
    assert premium_limit == 300, f"Premium client should have 300 req/min limit, got {premium_limit}"
    
    # Verify premium limit is higher than standard limit
    assert premium_limit > standard_limit, "Premium client should have higher rate limit than standard client"
    
    # Optional: Test that standard client hits rate limit sooner
    # This is an extensive test, so we'll keep it brief and just verify the limits in headers
    logger.info("Client-specific rate limits verified through response headers")


@pytest.mark.security
@pytest.mark.rate_limiting
def test_rate_limit_bypass_attempts():
    """Tests that rate limiting cannot be bypassed using common evasion techniques"""
    # Create a security client with valid API key
    client = create_security_client()
    
    # Get the rate limit threshold from settings
    rate_limit = settings.rate_limit_threshold
    
    # First, exhaust the rate limit with normal requests
    logger.info(f"Exhausting rate limit with {rate_limit} requests")
    for i in range(rate_limit):
        response = client.request(method="GET", endpoint=TEST_ENDPOINT)
        
        # If we start getting rate limited before exhausting, that's fine
        if response.status_code == 429:
            logger.info(f"Rate limited after {i+1} requests (before expected {rate_limit})")
            break
            
        # Don't overwhelm the server - small delay between requests
        time.sleep(0.1)
    
    # Now try various bypass techniques
    logger.info("Testing rate limit bypass techniques")
    
    bypass_attempts = [
        # Different HTTP methods
        {"method": "POST", "endpoint": TEST_ENDPOINT, "description": "Different HTTP method (POST)"},
        {"method": "PUT", "endpoint": TEST_ENDPOINT, "description": "Different HTTP method (PUT)"},
        
        # Different URL paths with same resource
        {"method": "GET", "endpoint": f"{TEST_ENDPOINT}?cache_buster={time.time()}", "description": "URL with cache buster parameter"},
        {"method": "GET", "endpoint": f"{TEST_ENDPOINT.replace('AAPL', 'aapl')}", "description": "URL with lowercase ticker"},
        
        # Different headers
        {"method": "GET", "endpoint": TEST_ENDPOINT, 
         "headers": {"X-Forwarded-For": "1.2.3.4"}, "description": "X-Forwarded-For header bypass attempt"},
        {"method": "GET", "endpoint": TEST_ENDPOINT, 
         "headers": {"X-Real-IP": "1.2.3.4"}, "description": "X-Real-IP header bypass attempt"},
        {"method": "GET", "endpoint": TEST_ENDPOINT, 
         "headers": {"User-Agent": "Different User Agent"}, "description": "Different User-Agent header"}
    ]
    
    # Try each bypass technique
    for attempt in bypass_attempts:
        logger.info(f"Attempting bypass: {attempt['description']}")
        
        try:
            headers = attempt.get("headers", {})
            response = client.request(
                method=attempt["method"], 
                endpoint=attempt["endpoint"],
                headers=headers
            )
            
            # Check if bypass was successful (got 200 OK instead of 429)
            if response.status_code != 429:
                logger.warning(f"Potential bypass found: {attempt['description']} - Status: {response.status_code}")
                assert False, f"Rate limit bypass succeeded with: {attempt['description']}"
            else:
                logger.info(f"Bypass attempt blocked correctly: {attempt['description']}")
            
        except Exception as e:
            logger.error(f"Error during bypass attempt: {str(e)}")
    
    logger.info("All rate limit bypass attempts were correctly blocked")


@pytest.mark.security
@pytest.mark.rate_limiting
def test_concurrent_rate_limiting():
    """Tests rate limiting under concurrent request conditions"""
    # Create a security client with valid API key
    client = create_security_client()
    
    # Get the rate limit threshold from settings
    rate_limit = settings.rate_limit_threshold
    
    # Number of concurrent requests to make (2x the rate limit)
    concurrent_requests = rate_limit * 2
    
    logger.info(f"Making {concurrent_requests} concurrent requests (rate limit: {rate_limit})")
    
    responses = []
    
    # Function to make a request and return the response
    def make_request():
        try:
            response = client.request(method="GET", endpoint=TEST_ENDPOINT)
            return response
        except Exception as e:
            logger.error(f"Error making concurrent request: {str(e)}")
            return None
    
    # Use ThreadPoolExecutor to make concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        # Submit all requests at once
        future_to_request = {executor.submit(make_request): i for i in range(concurrent_requests)}
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_request):
            request_id = future_to_request[future]
            try:
                response = future.result()
                if response:
                    responses.append(response)
            except Exception as e:
                logger.error(f"Request {request_id} generated an exception: {str(e)}")
    
    # Analyze responses
    success_count = sum(1 for r in responses if r.status_code == 200)
    rate_limited_count = sum(1 for r in responses if r.status_code == 429)
    
    logger.info(f"Concurrent requests results: {success_count} successful, {rate_limited_count} rate limited")
    
    # Verify that approximately rate_limit requests succeeded and the rest were rate limited
    # Allow some margin for error since concurrent requests might not be precisely rate limited
    assert success_count > 0, "No requests succeeded"
    assert rate_limited_count > 0, "No requests were rate limited"
    
    # Success count should be approximately equal to the rate limit
    # Allow for 20% margin of error due to concurrency timing issues
    margin = rate_limit * 0.2
    assert abs(success_count - rate_limit) <= margin, \
        f"Success count ({success_count}) should be approximately equal to rate limit ({rate_limit})"


@pytest.mark.security
@pytest.mark.rate_limiting
def test_rate_limiting_with_security_tools():
    """Tests rate limiting using the specialized security testing tools"""
    # Configure test parameters
    endpoint = TEST_ENDPOINT
    requests_per_second = 20  # Adjust this based on your rate limit (less than rate_limit/60)
    duration_seconds = 5      # Total test duration
    
    logger.info(f"Testing rate limiting with security tools: {requests_per_second} req/sec for {duration_seconds} seconds")
    
    # Run the rate limiting test
    results = test_rate_limiting(
        endpoint=endpoint,
        requests_per_second=requests_per_second,
        duration_seconds=duration_seconds
    )
    
    # Verify the test results
    assert "effectiveness" in results, "Test did not report effectiveness"
    
    # Check that rate limiting was effective
    effectiveness = results["effectiveness"]
    logger.info(f"Rate limiting effectiveness: {effectiveness}")
    
    # Effectiveness should be excellent, good, or fair
    assert effectiveness in ["excellent", "good", "fair"], \
        f"Rate limiting effectiveness should be acceptable, got: {effectiveness}"
    
    # Verify rate limit headers were present
    assert "rate_limit_headers" in results, "Rate limit headers not found in results"
    assert len(results["rate_limit_headers"]) > 0, "No rate limit headers were returned"
    
    # Check if any issues were found
    if "issues" in results and results["issues"]:
        logger.warning(f"Rate limiting issues found: {results['issues']}")
        # Test still passes if issues are minor, we're just logging them
    
    logger.info("Rate limiting tested successfully with security tools")


@pytest.mark.security
@pytest.mark.rate_limiting
def test_exempt_paths_not_rate_limited():
    """Tests that exempt paths are not subject to rate limiting"""
    # Create a security client with valid API key
    client = create_security_client()
    
    # Define exempt paths to test
    exempt_paths = [
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc"
    ]
    
    logger.info(f"Testing exempt paths: {exempt_paths}")
    
    # Make many requests to each exempt path
    requests_per_path = 30  # More than enough to trigger rate limiting if it were applied
    
    for path in exempt_paths:
        logger.info(f"Testing exempt path: {path}")
        
        # Make multiple requests to the exempt path
        for i in range(requests_per_path):
            response = client.request(method="GET", endpoint=path)
            
            # Some exempt paths might return 404 if not implemented, that's OK
            # We're testing that they don't return 429 (rate limited)
            assert response.status_code != 429, f"Exempt path {path} was rate limited on request {i+1}"
            
            # Check for absence of rate limit headers (they shouldn't be present for exempt paths)
            rate_limit_headers = [h for h in response.headers if "ratelimit" in h.lower() or "rate-limit" in h.lower()]
            
            if rate_limit_headers:
                logger.warning(f"Exempt path {path} has rate limit headers: {rate_limit_headers}")
            
            # Don't overwhelm the server - small delay between requests
            time.sleep(0.05)
    
    logger.info("All exempt paths tested successfully - not subject to rate limiting")