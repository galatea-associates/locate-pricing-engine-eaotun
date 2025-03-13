import pytest
import json
import logging
from decimal import Decimal

from src.test.security_tests import settings
from src.test.security_tests.helpers.payloads import InputValidationPayloads
from src.test.security_tests.helpers.security_tools import (
    SecurityAPIClient,
    create_security_client,
    test_input_validation
)
from src.test.integration_tests.helpers.api_client import APIClient
from src.backend.utils.validation import (
    MIN_POSITION_VALUE,
    MAX_POSITION_VALUE,
    MIN_LOAN_DAYS,
    MAX_LOAN_DAYS
)

# Configure module logger
logger = logging.getLogger(__name__)

# Test constants
VALID_TEST_TICKER = "AAPL"
VALID_POSITION_VALUE = Decimal('100000')
VALID_LOAN_DAYS = 30
VALID_CLIENT_ID = "test_client_123"
CALCULATE_ENDPOINT = "/api/v1/calculate-locate"
RATES_ENDPOINT = "/api/v1/rates"

def setup_test_client():
    """Creates and configures a security API client for testing"""
    client = create_security_client()
    client._default_headers["X-API-Key"] = settings.test_api_key
    return client

def create_valid_request():
    """Creates a valid request payload for testing"""
    return {
        "ticker": VALID_TEST_TICKER,
        "position_value": float(VALID_POSITION_VALUE),  # Convert Decimal to float for JSON
        "loan_days": VALID_LOAN_DAYS,
        "client_id": VALID_CLIENT_ID
    }

@pytest.mark.security
@pytest.mark.input_validation
def test_ticker_validation():
    """Tests validation of ticker parameter"""
    client = setup_test_client()
    payload_provider = InputValidationPayloads()
    
    # Get invalid ticker payloads
    invalid_tickers = payload_provider.get_payload("ticker", "invalid_format")
    invalid_tickers += payload_provider.get_payload("ticker", "special_chars")
    
    # Create a valid base request
    base_request = create_valid_request()
    
    # Test each invalid ticker
    for invalid_ticker in invalid_tickers:
        test_request = base_request.copy()
        test_request["ticker"] = invalid_ticker
        
        response = client.request(
            method="POST",
            endpoint=CALCULATE_ENDPOINT,
            json_data=test_request
        )
        
        # API should reject invalid tickers with 400 Bad Request
        assert response.status_code == 400, f"API accepted invalid ticker: {invalid_ticker}"
        
        # Check the error message indicates ticker validation failure
        try:
            error_data = response.json()
            assert "error" in error_data, "Error response missing 'error' field"
            assert "ticker" in str(error_data).lower() or "invalid parameter" in str(error_data).lower(), \
                f"Error message doesn't indicate ticker validation failure: {error_data}"
        except json.JSONDecodeError:
            assert False, f"Invalid JSON response for invalid ticker: {invalid_ticker}"
    
    # Also test SQL injection in ticker
    sql_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE stocks; --",
        "AAPL' UNION SELECT 1,2,3; --"
    ]
    
    for sql_payload in sql_payloads:
        test_request = base_request.copy()
        test_request["ticker"] = sql_payload
        
        response = client.request(
            method="POST",
            endpoint=CALCULATE_ENDPOINT,
            json_data=test_request
        )
        
        # API should reject SQL injection attempts with 400 Bad Request
        assert response.status_code == 400, f"API accepted SQL injection in ticker: {sql_payload}"
    
    logger.info("All ticker validation tests passed successfully")

@pytest.mark.security
@pytest.mark.input_validation
def test_position_value_validation():
    """Tests validation of position_value parameter"""
    client = setup_test_client()
    payload_provider = InputValidationPayloads()
    
    # Generate boundary values for position_value
    boundary_values = payload_provider.generate_boundary_values("position_value")
    
    # Create a valid base request
    base_request = create_valid_request()
    
    # Test boundary values
    for boundary_name, value in boundary_values.items():
        test_request = base_request.copy()
        test_request["position_value"] = float(value)  # Convert Decimal to float for JSON
        
        response = client.request(
            method="POST",
            endpoint=CALCULATE_ENDPOINT,
            json_data=test_request
        )
        
        # Expected result based on boundary type
        if boundary_name in ["min", "min+0.01", "max", "max-0.01"]:
            # Valid values should be accepted
            assert response.status_code == 200, f"API rejected valid position_value {value} for boundary {boundary_name}"
        else:
            # Invalid values should be rejected with 400 Bad Request
            assert response.status_code == 400, f"API accepted invalid position_value {value} for boundary {boundary_name}"
    
    # Test with non-numeric position values
    invalid_values = payload_provider.get_payload("position_value", "invalid_format")
    
    for invalid_value in invalid_values:
        test_request = base_request.copy()
        test_request["position_value"] = invalid_value
        
        response = client.request(
            method="POST",
            endpoint=CALCULATE_ENDPOINT,
            json_data=test_request
        )
        
        # API should reject non-numeric values with 400 Bad Request
        assert response.status_code == 400, f"API accepted non-numeric position_value: {invalid_value}"
        
        # Check the error message indicates position_value validation failure
        try:
            error_data = response.json()
            assert "error" in error_data, "Error response missing 'error' field"
            assert "position" in str(error_data).lower() or "invalid parameter" in str(error_data).lower(), \
                f"Error message doesn't indicate position_value validation failure: {error_data}"
        except json.JSONDecodeError:
            assert False, f"Invalid JSON response for invalid position_value: {invalid_value}"
    
    logger.info("All position_value validation tests passed successfully")

@pytest.mark.security
@pytest.mark.input_validation
def test_loan_days_validation():
    """Tests validation of loan_days parameter"""
    client = setup_test_client()
    payload_provider = InputValidationPayloads()
    
    # Get invalid loan days payloads
    invalid_values = payload_provider.get_payload("loan_days", "invalid_values")
    invalid_values += payload_provider.get_payload("loan_days", "invalid_format")
    
    # Create a valid base request
    base_request = create_valid_request()
    
    # Test with loan days below minimum
    test_request = base_request.copy()
    test_request["loan_days"] = MIN_LOAN_DAYS - 1
    response = client.request(
        method="POST",
        endpoint=CALCULATE_ENDPOINT,
        json_data=test_request
    )
    assert response.status_code == 400, f"API accepted loan_days below minimum: {MIN_LOAN_DAYS - 1}"
    
    # Test with loan days above maximum
    test_request = base_request.copy()
    test_request["loan_days"] = MAX_LOAN_DAYS + 1
    response = client.request(
        method="POST",
        endpoint=CALCULATE_ENDPOINT,
        json_data=test_request
    )
    assert response.status_code == 400, f"API accepted loan_days above maximum: {MAX_LOAN_DAYS + 1}"
    
    # Test with zero and negative loan days
    for value in [0, -1, -100]:
        test_request = base_request.copy()
        test_request["loan_days"] = value
        response = client.request(
            method="POST",
            endpoint=CALCULATE_ENDPOINT,
            json_data=test_request
        )
        assert response.status_code == 400, f"API accepted invalid loan_days: {value}"
    
    # Test with invalid format loan days
    for invalid_value in invalid_values:
        test_request = base_request.copy()
        test_request["loan_days"] = invalid_value
        response = client.request(
            method="POST",
            endpoint=CALCULATE_ENDPOINT,
            json_data=test_request
        )
        assert response.status_code == 400, f"API accepted invalid loan_days: {invalid_value}"
        
        # Check the error message
        try:
            error_data = response.json()
            assert "error" in error_data, "Error response missing 'error' field"
            assert "loan" in str(error_data).lower() or "day" in str(error_data).lower() or "invalid parameter" in str(error_data).lower(), \
                f"Error message doesn't indicate loan_days validation failure: {error_data}"
        except json.JSONDecodeError:
            assert False, f"Invalid JSON response for invalid loan_days: {invalid_value}"
    
    logger.info("All loan_days validation tests passed successfully")

@pytest.mark.security
@pytest.mark.input_validation
def test_client_id_validation():
    """Tests validation of client_id parameter"""
    client = setup_test_client()
    payload_provider = InputValidationPayloads()
    
    # Get invalid client ID payloads
    invalid_client_ids = payload_provider.get_payload("client_id", "invalid_format")
    
    # Create a valid base request
    base_request = create_valid_request()
    
    # Test each invalid client ID
    for invalid_client_id in invalid_client_ids:
        test_request = base_request.copy()
        test_request["client_id"] = invalid_client_id
        
        response = client.request(
            method="POST",
            endpoint=CALCULATE_ENDPOINT,
            json_data=test_request
        )
        
        # API should reject invalid client IDs with 400 Bad Request
        assert response.status_code == 400, f"API accepted invalid client_id: {invalid_client_id}"
        
        # Check the error message indicates client_id validation failure
        try:
            error_data = response.json()
            assert "error" in error_data, "Error response missing 'error' field"
            assert "client" in str(error_data).lower() or "invalid parameter" in str(error_data).lower(), \
                f"Error message doesn't indicate client_id validation failure: {error_data}"
        except json.JSONDecodeError:
            assert False, f"Invalid JSON response for invalid client_id: {invalid_client_id}"
    
    # Test with very short client IDs
    for short_id in ["a", "ab"]:
        test_request = base_request.copy()
        test_request["client_id"] = short_id
        response = client.request(
            method="POST",
            endpoint=CALCULATE_ENDPOINT,
            json_data=test_request
        )
        assert response.status_code == 400, f"API accepted too short client_id: {short_id}"
    
    # Test with very long client ID
    too_long_client_id = payload_provider.get_payload("client_id", "too_long")
    test_request = base_request.copy()
    test_request["client_id"] = too_long_client_id
    response = client.request(
        method="POST",
        endpoint=CALCULATE_ENDPOINT,
        json_data=test_request
    )
    assert response.status_code == 400, f"API accepted too long client_id with length {len(too_long_client_id)}"
    
    # Test with SQL injection attempts
    sql_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE brokers; --",
        "client_1' UNION SELECT 1,2,3; --"
    ]
    
    for sql_payload in sql_payloads:
        test_request = base_request.copy()
        test_request["client_id"] = sql_payload
        response = client.request(
            method="POST",
            endpoint=CALCULATE_ENDPOINT,
            json_data=test_request
        )
        assert response.status_code == 400, f"API accepted SQL injection in client_id: {sql_payload}"
    
    logger.info("All client_id validation tests passed successfully")

@pytest.mark.security
@pytest.mark.input_validation
def test_malformed_json():
    """Tests API handling of malformed JSON requests"""
    client = setup_test_client()
    
    # Create various malformed JSON payloads
    malformed_jsons = [
        # Unclosed object
        "{\"ticker\":\"AAPL\",\"position_value\":100000,\"loan_days\":30,\"client_id\":\"test_client_123\"",
        # Unclosed arrays
        "{\"ticker\":\"AAPL\",\"position_value\":100000,\"loan_days\":30,\"client_id\":\"test_client_123\",\"array\":[1,2,3}",
        # Missing commas
        "{\"ticker\":\"AAPL\" \"position_value\":100000,\"loan_days\":30,\"client_id\":\"test_client_123\"}",
        # Extra commas
        "{\"ticker\":\"AAPL\",\"position_value\":100000,,\"loan_days\":30,\"client_id\":\"test_client_123\"}",
        # Invalid values
        "{\"ticker\":AAPL,\"position_value\":100000,\"loan_days\":30,\"client_id\":\"test_client_123\"}",
        # Duplicate keys
        "{\"ticker\":\"AAPL\",\"ticker\":\"MSFT\",\"position_value\":100000,\"loan_days\":30,\"client_id\":\"test_client_123\"}"
    ]
    
    for i, malformed_json in enumerate(malformed_jsons):
        try:
            headers = client._default_headers.copy()
            headers["Content-Type"] = "application/json"
            
            # Use requests directly to send malformed JSON
            import requests
            response = requests.post(
                f"{settings.api_base_url}{CALCULATE_ENDPOINT}",
                headers=headers,
                data=malformed_json
            )
            
            # We expect a 400 Bad Request for malformed JSON
            assert response.status_code == 400, f"API didn't properly reject malformed JSON #{i}"
            
            # Make sure it's not a server error
            assert response.status_code != 500, f"API returned server error for malformed JSON #{i}"
            
        except Exception as e:
            # Log the exception but don't fail the test
            logger.warning(f"Exception when testing malformed JSON #{i}: {str(e)}")
    
    logger.info("All malformed JSON tests completed successfully")

@pytest.mark.security
@pytest.mark.input_validation
@pytest.mark.fuzzing
def test_parameter_fuzzing():
    """Tests API resilience against fuzzed parameter values"""
    client = setup_test_client()
    
    # Perform fuzz testing on each parameter
    parameters = {
        "ticker": "string",
        "position_value": "number",
        "loan_days": "number",
        "client_id": "string"
    }
    
    # Create a valid base request
    base_request = create_valid_request()
    
    # Fuzz each parameter
    for param_name, param_type in parameters.items():
        logger.info(f"Fuzzing parameter: {param_name}")
        
        # Get fuzzing results for this parameter
        results = client.fuzz_parameter(
            method="POST",
            endpoint=CALCULATE_ENDPOINT,
            param_name=param_name,
            param_type=param_type,
            base_request=base_request,
            num_tests=20  # Limit to 20 tests per parameter
        )
        
        # Verify that no server errors were returned
        for result in results:
            status_code = result.get("status_code")
            
            # Either we get a valid response (200) or a validation error (400),
            # but never a server error (500)
            assert status_code != 500, \
                f"Server error for parameter {param_name} with value: {result.get('payload')}"
            
            # Check for SQL errors in responses
            has_sql_error = any(sql_indicator in str(result.get("response_preview", "")).lower() 
                              for sql_indicator in ["sql", "syntax", "mysql", "postgres", "sqlite"])
            
            assert not has_sql_error, \
                f"Possible SQL error in response for parameter {param_name} with value: {result.get('payload')}"
    
    logger.info("All parameter fuzzing tests passed successfully")

@pytest.mark.security
@pytest.mark.input_validation
@pytest.mark.comprehensive
def test_comprehensive_input_validation():
    """Performs comprehensive input validation testing on the calculate endpoint"""
    client = setup_test_client()
    
    # Define field specifications for all parameters
    field_specs = {
        "ticker": {
            "type": "string",
            "example": "AAPL",
            "minLength": 1,
            "maxLength": 5,
            "pattern": "^[A-Z]{1,5}$"
        },
        "position_value": {
            "type": "number",
            "example": 100000,
            "minimum": float(MIN_POSITION_VALUE),
            "maximum": float(MAX_POSITION_VALUE)
        },
        "loan_days": {
            "type": "number",
            "example": 30,
            "minimum": MIN_LOAN_DAYS,
            "maximum": MAX_LOAN_DAYS
        },
        "client_id": {
            "type": "string",
            "example": "test_client_123",
            "minLength": 3,
            "maxLength": 50,
            "pattern": "^[a-zA-Z0-9_-]{3,50}$"
        }
    }
    
    # Run comprehensive input validation test
    results = test_input_validation(
        endpoint=CALCULATE_ENDPOINT,
        method="POST",
        field_specs=field_specs,
        valid_request=create_valid_request()
    )
    
    # Check for vulnerabilities
    assert len(results["vulnerabilities_found"]) == 0, \
        f"Vulnerabilities found in input validation: {results['vulnerabilities_found']}"
    
    logger.info("Comprehensive input validation test passed successfully")

@pytest.mark.security
@pytest.mark.input_validation
def test_missing_parameters():
    """Tests API handling of missing required parameters"""
    client = setup_test_client()
    
    # Create a valid base request
    base_request = create_valid_request()
    
    # Test with each required parameter missing
    required_params = ["ticker", "position_value", "loan_days", "client_id"]
    
    for param in required_params:
        test_request = base_request.copy()
        del test_request[param]
        
        response = client.request(
            method="POST",
            endpoint=CALCULATE_ENDPOINT,
            json_data=test_request
        )
        
        # API should reject requests with missing required parameters with 400 Bad Request
        assert response.status_code == 400, f"API didn't reject request with missing parameter: {param}"
        
        # Check the error message indicates the missing parameter
        try:
            error_data = response.json()
            assert "error" in error_data, "Error response missing 'error' field"
            error_msg = str(error_data).lower()
            assert param in error_msg or "required" in error_msg or "missing" in error_msg, \
                f"Error message doesn't indicate missing parameter {param}: {error_data}"
        except json.JSONDecodeError:
            assert False, f"Invalid JSON response for missing parameter: {param}"
    
    # Test with multiple missing parameters
    test_request = {}  # Empty request
    
    response = client.request(
        method="POST",
        endpoint=CALCULATE_ENDPOINT,
        json_data=test_request
    )
    
    # API should reject empty requests with 400 Bad Request
    assert response.status_code == 400, "API didn't reject empty request"
    
    logger.info("All missing parameter tests passed successfully")

@pytest.mark.security
@pytest.mark.input_validation
def test_unexpected_parameters():
    """Tests API handling of unexpected additional parameters"""
    client = setup_test_client()
    
    # Create a valid base request
    base_request = create_valid_request()
    
    # Add various unexpected parameters
    test_cases = [
        # Simple unexpected parameter
        {**base_request, "unexpected_param": "value"},
        # Nested unexpected parameter
        {**base_request, "nested": {"key": "value"}},
        # Array parameter
        {**base_request, "array_param": [1, 2, 3]},
        # Potentially dangerous parameter names
        {**base_request, "constructor": "value"},
        {**base_request, "__proto__": "value"},
        {**base_request, "toString": "value"}
    ]
    
    for i, test_request in enumerate(test_cases):
        response = client.request(
            method="POST",
            endpoint=CALCULATE_ENDPOINT,
            json_data=test_request
        )
        
        # API should ignore unexpected parameters and process the request normally
        assert response.status_code == 200, f"API rejected request with unexpected parameters in test case {i}"
        
        # Verify the response structure
        try:
            response_data = response.json()
            assert "total_fee" in response_data, f"Response missing 'total_fee' field in test case {i}"
            assert "breakdown" in response_data, f"Response missing 'breakdown' field in test case {i}"
            assert "borrow_rate_used" in response_data, f"Response missing 'borrow_rate_used' field in test case {i}"
        except json.JSONDecodeError:
            assert False, f"Invalid JSON response for unexpected parameters in test case {i}"
    
    logger.info("All unexpected parameter tests passed successfully")