"""
Test module for authentication functionality in the Borrow Rate & Locate Fee Pricing Engine API.
This file contains unit tests for API key authentication, rate limiting, token generation,
and error handling for authentication-related operations.
"""

import pytest  # pytest 7.0.0+
from fastapi import FastAPI, Request, Response, status  # fastapi 0.103.0+
from pyjwt import jwt  # For decoding and validating JWT tokens in tests

from src.backend.core.auth import (  # Internal imports
    get_api_key_from_header,
    authenticate_request,
    create_auth_token,
    validate_auth_token
)
from src.backend.middleware.authentication import AuthenticationMiddleware  # Internal imports
from src.backend.core.exceptions import AuthenticationException, RateLimitExceededException  # Internal imports
from src.backend.api.deps import get_auth_from_request  # Internal imports
from src.backend.tests.conftest import api_client, test_api_key_header, mock_redis_cache, test_db, seed_test_data  # Internal imports


@pytest.mark.unit
def test_get_api_key_from_header():
    """Test extracting API key from request headers"""
    # Create a mock request with X-API-Key header
    async def mock_request_with_key():
        req = Request({"type": "http", "path": "/", "method": "GET"})
        req.headers = {"x-api-key": "testkey"}
        return req
    
    # Call get_api_key_from_header with the mock request
    api_key = get_api_key_from_header(mock_request_with_key())
    
    # Assert that the returned API key matches the expected value
    assert api_key == "testkey"
    
    # Create a mock request without X-API-Key header
    async def mock_request_without_key():
        req = Request({"type": "http", "path": "/", "method": "GET"})
        req.headers = {}
        return req
    
    # Call get_api_key_from_header with the mock request
    api_key = get_api_key_from_header(mock_request_without_key())
    
    # Assert that the returned value is None
    assert api_key is None


@pytest.mark.integration
def test_authenticate_request_valid_key(test_db, seed_test_data):
    """Test authenticating a request with a valid API key"""
    # Create a valid API key for testing
    api_key = "valid_api_key"
    
    # Call authenticate_request with the API key
    auth_result = authenticate_request(api_key)
    
    # Assert that the authentication result contains client_id
    assert "client_id" in auth_result
    
    # Assert that the authentication result contains rate limit information
    assert "rate_limit" in auth_result


@pytest.mark.integration
def test_authenticate_request_invalid_key(test_db):
    """Test authenticating a request with an invalid API key"""
    # Create an invalid API key for testing
    api_key = "invalid_api_key"
    
    # Call authenticate_request with the invalid API key
    with pytest.raises(AuthenticationException) as exc_info:
        authenticate_request(api_key)
    
    # Assert that AuthenticationException is raised with appropriate message
    assert str(exc_info.value) == "Invalid API key"


@pytest.mark.integration
def test_rate_limit_exceeded(test_db, seed_test_data, mock_redis_cache):
    """Test rate limiting functionality"""
    # Create a valid API key for testing
    api_key = "valid_api_key"
    
    # Get client_id associated with the API key
    client_id = "test_client"
    
    # Set up mock Redis to simulate rate limit exceeded
    mock_redis_cache.set(f"rate_limit:{client_id}:0", 61, ex=60)
    
    # Call authenticate_request with the API key
    with pytest.raises(RateLimitExceededException) as exc_info:
        authenticate_request(api_key)
    
    # Assert that RateLimitExceededException is raised with appropriate retry-after value
    assert str(exc_info.value) == f"Rate limit exceeded for client '{client_id}'"
    assert exc_info.value.params["retry_after"] == 60


@pytest.mark.unit
def test_auth_middleware_exempt_paths():
    """Test that authentication middleware correctly exempts specified paths"""
    # Create an instance of AuthenticationMiddleware with default exempt paths
    middleware = AuthenticationMiddleware()
    
    # Test that health endpoint is exempt
    assert middleware.is_path_exempt("/health")
    
    # Test that docs endpoint is exempt
    assert middleware.is_path_exempt("/docs")
    
    # Test that openapi.json endpoint is exempt
    assert middleware.is_path_exempt("/openapi.json")
    
    # Test that a non-exempt path is not exempt
    assert not middleware.is_path_exempt("/protected")


@pytest.mark.unit
def test_auth_middleware_add_headers():
    """Test that authentication middleware adds appropriate headers to responses"""
    # Create an instance of AuthenticationMiddleware
    middleware = AuthenticationMiddleware()
    
    # Create a mock response
    response = Response()
    
    # Create a mock auth_result with rate limit information
    auth_result = {
        "client_id": "test_client",
        "rate_limit": {
            "limit": 60,
            "remaining": 30,
            "reset": 30
        }
    }
    
    # Call add_auth_headers with the response and auth_result
    response = middleware.add_auth_headers(response, auth_result)
    
    # Assert that X-RateLimit-Limit header is added with correct value
    assert response.headers["X-RateLimit-Limit"] == "60"
    
    # Assert that X-RateLimit-Remaining header is added with correct value
    assert response.headers["X-RateLimit-Remaining"] == "30"
    
    # Assert that X-RateLimit-Reset header is added with correct value
    assert response.headers["X-RateLimit-Reset"] == "30"


@pytest.mark.integration
def test_api_endpoint_with_auth(api_client):
    """Test that API endpoints require authentication"""
    # Make a request to a protected endpoint without API key
    response = api_client.get("/api/v1/calculate-locate")
    
    # Assert that response status code is 401 Unauthorized
    assert response.status_code == 401
    
    # Make a request to a protected endpoint with invalid API key
    response = api_client.get("/api/v1/calculate-locate", headers={"X-API-Key": "invalid"})
    
    # Assert that response status code is 401 Unauthorized
    assert response.status_code == 401
    
    # Make a request to a protected endpoint with valid API key
    response = api_client.get("/api/v1/calculate-locate", headers={"X-API-Key": "valid_api_key"})
    
    # Assert that response status code is 200 OK
    assert response.status_code == 200


@pytest.mark.integration
def test_api_endpoint_rate_limit_headers(api_client, test_api_key_header):
    """Test that API responses include rate limit headers"""
    # Make a request to a protected endpoint with valid API key
    response = api_client.get("/api/v1/calculate-locate", headers=test_api_key_header)
    
    # Assert that response includes X-RateLimit-Limit header
    assert "X-RateLimit-Limit" in response.headers
    
    # Assert that response includes X-RateLimit-Remaining header
    assert "X-RateLimit-Remaining" in response.headers
    
    # Assert that response includes X-RateLimit-Reset header
    assert "X-RateLimit-Reset" in response.headers


@pytest.mark.unit
def test_create_auth_token():
    """Test creating JWT authentication tokens"""
    # Call create_auth_token with a client_id
    token = create_auth_token("test_client")
    
    # Assert that a token string is returned
    assert isinstance(token, str)
    
    # Decode the token using jwt.decode
    decoded_token = jwt.decode(token, "secret", algorithms=["HS256"])
    
    # Assert that the token contains the correct client_id
    assert decoded_token["client_id"] == "test_client"
    
    # Assert that the token contains an expiration claim
    assert "exp" in decoded_token


@pytest.mark.unit
def test_validate_auth_token():
    """Test validating JWT authentication tokens"""
    # Create a valid token using create_auth_token
    valid_token = create_auth_token("test_client")
    
    # Call validate_auth_token with the token
    decoded_payload = validate_auth_token(valid_token)
    
    # Assert that the decoded payload contains the correct client_id
    assert decoded_payload["client_id"] == "test_client"
    
    # Create an invalid token (malformed)
    invalid_token = "malformed_token"
    
    # Assert that validate_auth_token raises AuthenticationException for the invalid token
    with pytest.raises(AuthenticationException):
        validate_auth_token(invalid_token)
    
    # Create an expired token
    expired_token = create_auth_token("test_client", expires_delta=timedelta(minutes=-1))
    
    # Assert that validate_auth_token raises AuthenticationException for the expired token
    with pytest.raises(AuthenticationException):
        validate_auth_token(expired_token)


@pytest.mark.integration
def test_auth_dependency():
    """Test the authentication dependency used in API endpoints"""
    # Create a mock request with valid API key
    async def mock_request_with_valid_key():
        req = Request({"type": "http", "path": "/", "method": "GET"})
        req.headers = {"x-api-key": "valid_api_key"}
        return req
    
    # Call get_auth_from_request with the request
    auth_result = get_auth_from_request(mock_request_with_valid_key())
    
    # Assert that the result contains client_id
    assert "client_id" in auth_result
    
    # Create a mock request with invalid API key
    async def mock_request_with_invalid_key():
        req = Request({"type": "http", "path": "/", "method": "GET"})
        req.headers = {"x-api-key": "invalid_api_key"}
        return req
    
    # Assert that get_auth_from_request raises HTTPException with 401 status
    with pytest.raises(HTTPException) as exc_info:
        get_auth_from_request(mock_request_with_invalid_key())
    assert exc_info.value.status_code == 401
    
    # Create a mock request without API key
    async def mock_request_without_key():
        req = Request({"type": "http", "path": "/", "method": "GET"})
        req.headers = {}
        return req
    
    # Assert that get_auth_from_request raises HTTPException with 401 status
    with pytest.raises(HTTPException) as exc_info:
        get_auth_from_request(mock_request_without_key())
    assert exc_info.value.status_code == 401