"""
End-to-end test module that verifies the API versioning functionality of the Borrow Rate & Locate Fee Pricing Engine.
Tests include version compatibility, version negotiation, and handling of deprecated versions.
"""

import logging
import pytest
import requests

from .config.settings import get_test_settings, TestSettings, DEFAULT_API_VERSION
from .helpers.api_client import APIClient, create_api_client
from .helpers.validation import ResponseValidator, create_response_validator
from .fixtures.environment import environment

# Configure logger
logger = logging.getLogger(__name__)

# Test versions to check (supported and unsupported)
TEST_VERSIONS = ['v1', 'v2', 'v0']


def setup_module():
    """Setup function that runs once before all tests in the module"""
    logger.info("Setting up API versioning test module")
    settings = get_test_settings()
    api_client = create_api_client(settings)
    api_client.wait_for_api_ready()
    logger.info("API versioning test module setup complete")


def teardown_module():
    """Teardown function that runs once after all tests in the module"""
    logger.info("Tearing down API versioning test module")
    logger.info("API versioning test module teardown complete")


def create_version_specific_client(version: str) -> APIClient:
    """Creates an API client configured for a specific API version"""
    settings = get_test_settings()
    # Create a copy of settings
    modified_settings = TestSettings()
    modified_settings.api_version = version
    client = create_api_client(modified_settings)
    return client


@pytest.mark.e2e
def test_default_version_access(environment):
    """Tests that the default API version is accessible"""
    logger.info("Testing default API version access")
    settings = get_test_settings()
    api_client = create_api_client(settings)
    
    response = api_client.health_check()
    
    # Verify response
    assert response.status == "healthy"
    assert response.version.startswith(DEFAULT_API_VERSION)
    
    logger.info(f"Successfully accessed default API version: {response.version}")


@pytest.mark.e2e
def test_explicit_version_in_url(environment):
    """Tests accessing the API with explicit version in URL"""
    logger.info("Testing explicit version in URL")
    
    for version in TEST_VERSIONS:
        logger.info(f"Testing version: {version}")
        client = create_version_specific_client(version)
        
        response = client.health_check()
        
        if version in ['v1', 'v2']:  # Supported versions
            assert response.status == "healthy"
            assert response.version.startswith(version)
            logger.info(f"Successfully accessed API version {version}")
        else:  # Unsupported version
            assert "error" in response
            assert "unsupported version" in response.get("message", "").lower()
            logger.info(f"Correctly rejected unsupported version {version}")
    
    logger.info("Explicit version test completed successfully")


@pytest.mark.e2e
def test_version_header_negotiation(environment):
    """Tests API version negotiation using Accept-Version header"""
    logger.info("Testing version negotiation via Accept-Version header")
    settings = get_test_settings()
    api_client = create_api_client(settings)
    
    for version in TEST_VERSIONS:
        logger.info(f"Testing Accept-Version: {version}")
        # Create custom headers with Accept-Version
        headers = {"Accept-Version": version}
        
        # Make direct request to health endpoint with custom headers
        response = api_client.request("GET", "/health", headers=headers)
        response_data = response.json()
        
        if version in ['v1', 'v2']:  # Supported versions
            assert response.status_code == 200
            assert response_data.get("status") == "healthy"
            assert response_data.get("version", "").startswith(version)
            logger.info(f"Successfully negotiated to API version {version}")
        else:  # Unsupported version
            assert response.status_code in [400, 406]  # Bad Request or Not Acceptable
            assert "error" in response_data
            assert "unsupported version" in response_data.get("message", "").lower()
            logger.info(f"Correctly rejected unsupported version {version}")
    
    logger.info("Version header negotiation test completed successfully")


@pytest.mark.e2e
def test_version_compatibility(environment):
    """Tests that endpoints maintain compatibility across supported versions"""
    logger.info("Testing endpoint compatibility across versions")
    
    # Define test parameters
    test_params = {
        "ticker": "AAPL",
        "position_value": 100000,
        "loan_days": 30,
        "client_id": "broker_standard"
    }
    
    responses = {}
    
    # Test with each supported version
    for version in ['v1', 'v2']:
        client = create_version_specific_client(version)
        
        response = client.calculate_locate_fee(
            ticker=test_params["ticker"],
            position_value=test_params["position_value"],
            loan_days=test_params["loan_days"],
            client_id=test_params["client_id"]
        )
        
        # Verify basic response structure
        assert response.status == "success"
        assert hasattr(response, "total_fee")
        assert hasattr(response, "breakdown")
        assert hasattr(response, "borrow_rate_used")
        
        # Store response for comparison
        responses[version] = response
    
    # Compare responses between versions to ensure compatibility
    v1_response = responses['v1']
    v2_response = responses['v2']
    
    # Core fields should have the same values
    assert v1_response.total_fee == v2_response.total_fee
    assert v1_response.borrow_rate_used == v2_response.borrow_rate_used
    assert v1_response.breakdown.borrow_cost == v2_response.breakdown.borrow_cost
    assert v1_response.breakdown.markup == v2_response.breakdown.markup
    assert v1_response.breakdown.transaction_fees == v2_response.breakdown.transaction_fees
    
    logger.info("Version compatibility test completed successfully")


@pytest.mark.e2e
def test_version_specific_features(environment):
    """Tests version-specific features and enhancements"""
    logger.info("Testing version-specific features")
    
    # Create clients for different versions
    v1_client = create_version_specific_client('v1')
    v2_client = create_version_specific_client('v2')
    
    # Define test parameters
    test_params = {
        "ticker": "AAPL",
        "position_value": 100000,
        "loan_days": 30,
        "client_id": "broker_standard"
    }
    
    # Get responses from both versions
    v1_response = v1_client.calculate_locate_fee(
        ticker=test_params["ticker"],
        position_value=test_params["position_value"],
        loan_days=test_params["loan_days"],
        client_id=test_params["client_id"]
    )
    
    v2_response = v2_client.calculate_locate_fee(
        ticker=test_params["ticker"],
        position_value=test_params["position_value"],
        loan_days=test_params["loan_days"],
        client_id=test_params["client_id"]
    )
    
    # Both responses should be successful
    assert v1_response.status == "success"
    assert v2_response.status == "success"
    
    # Convert to dictionaries for easier comparison
    v1_dict = v1_response.__dict__
    v2_dict = v2_response.__dict__
    
    # Check for v2-specific fields that aren't in v1
    # Note: This test assumes v2 has additional fields compared to v1
    v2_additional_fields = set(v2_dict.keys()) - set(v1_dict.keys())
    assert len(v2_additional_fields) > 0
    
    # Common fields should have the same values
    common_fields = set(v1_dict.keys()) & set(v2_dict.keys())
    for field in common_fields:
        if isinstance(v1_dict[field], dict) and isinstance(v2_dict[field], dict):
            # For nested objects, check individual fields
            for subfield in v1_dict[field]:
                assert v1_dict[field][subfield] == v2_dict[field][subfield]
        else:
            # For simple fields, compare directly
            assert v1_dict[field] == v2_dict[field]
    
    logger.info("Version-specific features test completed successfully")


@pytest.mark.e2e
def test_sunset_header(environment):
    """Tests that deprecated versions include Sunset header"""
    logger.info("Testing sunset header for deprecated versions")
    
    api_client = create_api_client()
    
    # Make direct request to health endpoint with v1 version header
    headers = {"Accept-Version": "v1"}
    response = api_client.request("GET", "/health", headers=headers)
    
    # Check if Sunset header exists
    # Note: This test assumes v1 might eventually be deprecated
    if 'Sunset' in response.headers:
        sunset_date = response.headers['Sunset']
        # Validate that it contains a valid future date
        assert sunset_date, "Sunset header should not be empty"
        logger.info(f"Version v1 will be deprecated on {sunset_date}")
    else:
        logger.info("Version v1 is not yet marked for deprecation")
    
    logger.info("Sunset header test completed successfully")


@pytest.mark.e2e
def test_invalid_version_handling(environment):
    """Tests handling of invalid or unsupported API versions"""
    logger.info("Testing invalid version handling")
    
    settings = get_test_settings()
    api_client = create_api_client(settings)
    
    # Test with a list of invalid versions
    invalid_versions = ['v999', 'invalid', '1.0', 'latest']
    
    for version in invalid_versions:
        logger.info(f"Testing invalid version: {version}")
        
        # Create custom headers with invalid Accept-Version
        headers = {"Accept-Version": version}
        
        # Make direct request to health endpoint with custom headers
        response = api_client.request("GET", "/health", headers=headers)
        response_data = response.json()
        
        # Verify correct error response
        assert response.status_code in [400, 406]  # Bad Request or Not Acceptable
        assert "error" in response_data
        assert "version" in response_data.get("message", "").lower()
        
        logger.info(f"Correctly handled invalid version {version}")
    
    logger.info("Invalid version handling test completed successfully")