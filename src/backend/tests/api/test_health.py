"""
Unit tests for the health check endpoints of the Borrow Rate & Locate Fee Pricing Engine API.

This file contains test cases to verify the functionality of the health, readiness, and 
liveness check endpoints, ensuring they correctly report the status of system components
including database connectivity, cache service, and external API availability.
"""

import pytest  # pytest 7.4.0+
import json  # standard library
import httpx  # httpx 0.25.0+

# Import fixtures
from ..conftest import api_client, mock_redis_cache, mock_external_apis


def test_health_endpoint(api_client, mock_redis_cache, mock_external_apis):
    """
    Tests the /health endpoint to ensure it returns correct system status.
    """
    # Make GET request to /health endpoint
    response = api_client.get("/health")
    
    # Verify response status code is 200
    assert response.status_code == 200
    
    # Parse response JSON
    data = response.json()
    
    # Verify response contains expected fields
    assert "status" in data
    assert "version" in data
    assert "components" in data
    assert "timestamp" in data
    
    # Verify status is "healthy"
    assert data["status"] == "healthy"
    
    # Verify components contains expected entries
    assert "database" in data["components"]
    assert "cache" in data["components"]
    assert "external_apis" in data["components"]
    
    # Verify component statuses
    assert data["components"]["database"]["status"] == "connected"
    assert data["components"]["cache"]["status"] == "connected"
    
    # Verify external APIs
    external_apis = data["components"]["external_apis"]
    assert "seclend" in external_apis
    assert "market_volatility" in external_apis
    assert "event_calendar" in external_apis


def test_readiness_endpoint(api_client):
    """
    Tests the /ready endpoint to ensure it correctly reports system readiness.
    """
    # Make GET request to /ready endpoint
    response = api_client.get("/ready")
    
    # Verify response status code is 200
    assert response.status_code == 200
    
    # Parse response JSON
    data = response.json()
    
    # Verify response contains status field
    assert "status" in data
    
    # Verify status is "ready"
    assert data["status"] == "ready"


def test_liveness_endpoint(api_client):
    """
    Tests the /alive endpoint to ensure it correctly reports system liveness.
    """
    # Make GET request to /alive endpoint
    response = api_client.get("/alive")
    
    # Verify response status code is 200
    assert response.status_code == 200
    
    # Parse response JSON
    data = response.json()
    
    # Verify response contains status field
    assert "status" in data
    
    # Verify status is "alive"
    assert data["status"] == "alive"


def test_health_endpoint_with_database_failure(api_client, mock_redis_cache, mock_external_apis, monkeypatch):
    """
    Tests the /health endpoint when database connection fails.
    """
    # Mock database ping function to return False
    def mock_ping_database():
        return False
    
    # Apply monkeypatch
    from src.backend.db.session import ping_database
    monkeypatch.setattr("src.backend.db.session.ping_database", mock_ping_database)
    
    # Make GET request to /health endpoint
    response = api_client.get("/health")
    
    # Verify response status code is 200 (should still return 200 even with degraded status)
    assert response.status_code == 200
    
    # Parse response JSON
    data = response.json()
    
    # Verify status is "degraded"
    assert data["status"] == "degraded"
    
    # Verify database status is "disconnected"
    assert data["components"]["database"]["status"] == "disconnected"
    
    # Verify other components are still connected
    assert data["components"]["cache"]["status"] == "connected"
    
    # Verify external APIs status is still available
    external_apis = data["components"]["external_apis"]
    assert "seclend" in external_apis
    assert "market_volatility" in external_apis
    assert "event_calendar" in external_apis


def test_health_endpoint_with_cache_failure(api_client, mock_redis_cache, mock_external_apis, monkeypatch):
    """
    Tests the /health endpoint when cache connection fails.
    """
    # Mock Redis is_connected method to return False
    def mock_is_connected(self):
        return False
    
    # Apply monkeypatch
    monkeypatch.setattr(mock_redis_cache.__class__, "is_connected", mock_is_connected)
    
    # Make GET request to /health endpoint
    response = api_client.get("/health")
    
    # Verify response status code is 200 (should still return 200 even with degraded status)
    assert response.status_code == 200
    
    # Parse response JSON
    data = response.json()
    
    # Verify status is "degraded"
    assert data["status"] == "degraded"
    
    # Verify cache status is "disconnected"
    assert data["components"]["cache"]["status"] == "disconnected"
    
    # Verify database is still connected
    assert data["components"]["database"]["status"] == "connected"
    
    # Verify external APIs status is still available
    external_apis = data["components"]["external_apis"]
    assert "seclend" in external_apis
    assert "market_volatility" in external_apis
    assert "event_calendar" in external_apis


def test_health_endpoint_with_external_api_failure(api_client, mock_redis_cache, mock_external_apis):
    """
    Tests the /health endpoint when external APIs are unavailable.
    """
    # Configure mock_external_apis to return error responses
    for ticker in ['AAPL', 'MSFT', 'TSLA', 'GME', 'AMC']:
        mock_external_apis.get(
            f"https://api.seclend.com/borrow/{ticker}",
            status_code=500,
            json={"error": "Service Unavailable"}
        )
    
    # Make GET request to /health endpoint
    response = api_client.get("/health")
    
    # Verify response status code is 200
    assert response.status_code == 200
    
    # Parse response JSON
    data = response.json()
    
    # Verify status is "degraded"
    assert data["status"] == "degraded"
    
    # Verify database and cache are still connected
    assert data["components"]["database"]["status"] == "connected"
    assert data["components"]["cache"]["status"] == "connected"
    
    # Verify external APIs shows unavailable status for the failed APIs
    external_apis = data["components"]["external_apis"]
    assert "seclend" in external_apis
    assert external_apis["seclend"]["status"] == "disconnected"


def test_readiness_endpoint_with_database_failure(api_client, monkeypatch):
    """
    Tests the /ready endpoint when database connection fails.
    """
    # Mock database ping function to return False
    def mock_ping_database():
        return False
    
    # Apply monkeypatch
    from src.backend.db.session import ping_database
    monkeypatch.setattr("src.backend.db.session.ping_database", mock_ping_database)
    
    # Make GET request to /ready endpoint
    response = api_client.get("/ready")
    
    # Verify response status code is 503 (Service Unavailable)
    assert response.status_code == 503
    
    # Parse response JSON
    data = response.json()
    
    # Verify response contains error message about database connectivity
    assert "error" in data
    assert "database" in data["error"].lower()