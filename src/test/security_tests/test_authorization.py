"""
Security test suite for authorization mechanisms in the Borrow Rate & Locate Fee Pricing Engine.
Tests role-based access controls, permission enforcement, resource access restrictions, and 
privilege escalation attempts to ensure the system's authorization controls are robust and secure.
"""

import pytest
import requests
import json
import logging

# Internal imports
from ..config.settings import get_test_settings, TestSettings
from ..helpers.security_tools import create_security_client, test_authorization, SecurityAPIClient

# Get test settings
settings = get_test_settings()

# Configure logger
logger = logging.getLogger(__name__)

# Test endpoints
TEST_ENDPOINTS = ['/api/v1/rates/AAPL', '/api/v1/calculate-locate']

# Test roles with their API keys and permissions
TEST_ROLES = {
    'client': {
        'api_key': settings.test_api_key,
        'permissions': ['calculate_fees', 'view_rates']
    },
    'admin': {
        'api_key': settings.admin_api_key,
        'permissions': ['calculate_fees', 'view_rates', 'modify_config', 'view_audit_logs']
    },
    'auditor': {
        'api_key': settings.auditor_api_key,
        'permissions': ['view_rates', 'view_audit_logs']
    }
}

def setup_module():
    """Setup function that runs once before all tests in the module."""
    # Configure logging for the test module
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting authorization security tests")
    
    # Verify that the API is accessible before running tests
    if not verify_api_accessibility():
        pytest.skip("API is not accessible, skipping authorization tests")

def teardown_module():
    """Teardown function that runs once after all tests in the module."""
    logger.info("Completed authorization security tests")

def verify_api_accessibility():
    """Verifies that the API is accessible before running tests."""
    try:
        client = create_security_client(settings, settings.test_api_key)
        response = client.request(method="GET", endpoint="/health")
        if response.status_code == 200:
            logger.info("API is accessible")
            return True
        else:
            logger.error(f"API returned status code {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error accessing API: {str(e)}")
        return False

class TestAuthorization:
    """Test class for authorization security testing."""
    
    @classmethod
    def setup_class(cls):
        """Setup method that runs once before all tests in the class."""
        # Create security clients for different roles
        cls.client_api = create_security_client(settings, TEST_ROLES['client']['api_key'])
        cls.admin_api = create_security_client(settings, TEST_ROLES['admin']['api_key'])
        cls.auditor_api = create_security_client(settings, TEST_ROLES['auditor']['api_key'])
        
        # Initialize test data for authorization testing
        cls.test_data = {
            'calculate_locate': {
                'ticker': 'AAPL',
                'position_value': 100000,
                'loan_days': 30,
                'client_id': 'test_broker_1'
            }
        }
        
        logger.info("Test class setup completed")
    
    @classmethod
    def teardown_class(cls):
        """Teardown method that runs once after all tests in the class."""
        logger.info("Test class teardown completed")
    
    def test_role_based_access(self):
        """Tests that different roles have appropriate access to endpoints."""
        # For each role, test access to each endpoint
        for role, role_data in TEST_ROLES.items():
            api_key = role_data['api_key']
            permissions = role_data['permissions']
            client = create_security_client(settings, api_key)
            
            for endpoint in TEST_ENDPOINTS:
                # Determine expected access based on permissions
                should_have_access = False
                if endpoint == '/api/v1/rates/AAPL' and 'view_rates' in permissions:
                    should_have_access = True
                elif endpoint == '/api/v1/calculate-locate' and 'calculate_fees' in permissions:
                    should_have_access = True
                
                # Test access to the endpoint
                method = "GET" if "rates" in endpoint else "POST"
                json_data = None
                if method == "POST":
                    json_data = self.test_data['calculate_locate']
                
                response = client.request(method=method, endpoint=endpoint, json_data=json_data)
                
                # Check if access matches expectation
                has_access = response.status_code < 400
                
                if should_have_access:
                    assert has_access, f"Role '{role}' should have access to {endpoint} but got status {response.status_code}"
                else:
                    assert not has_access, f"Role '{role}' should not have access to {endpoint} but got status {response.status_code}"
                
                logger.info(f"Role '{role}' access to {endpoint}: expected={should_have_access}, actual={has_access}")
    
    def test_resource_access_restrictions(self):
        """Tests that users can only access resources they are authorized for."""
        # Test client role accessing own resources
        client = self.client_api
        own_client_id = "test_broker_1"
        other_client_id = "test_broker_2"
        
        # Test access to own resource
        response = client.request(
            method="POST",
            endpoint="/api/v1/calculate-locate",
            json_data={
                'ticker': 'AAPL',
                'position_value': 100000,
                'loan_days': 30,
                'client_id': own_client_id
            }
        )
        assert response.status_code < 400, f"Client should be able to access own resources but got status {response.status_code}"
        
        # Test access to other client's resource
        response = client.request(
            method="POST",
            endpoint="/api/v1/calculate-locate",
            json_data={
                'ticker': 'AAPL',
                'position_value': 100000,
                'loan_days': 30,
                'client_id': other_client_id
            }
        )
        assert response.status_code >= 400, f"Client should not be able to access other client's resources but got status {response.status_code}"
        
        # Test that admin role can access all resources
        admin = self.admin_api
        response = admin.request(
            method="POST",
            endpoint="/api/v1/calculate-locate",
            json_data={
                'ticker': 'AAPL',
                'position_value': 100000,
                'loan_days': 30,
                'client_id': other_client_id
            }
        )
        assert response.status_code < 400, f"Admin should be able to access any client's resources but got status {response.status_code}"
        
        logger.info("Resource access restrictions tested successfully")
    
    def test_horizontal_privilege_escalation(self):
        """Tests for horizontal privilege escalation vulnerabilities."""
        # Attempt to access resources of other clients by manipulating request parameters
        client = self.client_api
        own_client_id = "test_broker_1"
        target_client_id = "test_broker_2"
        
        # Test direct client_id manipulation
        response = client.request(
            method="POST",
            endpoint="/api/v1/calculate-locate",
            json_data={
                'ticker': 'AAPL',
                'position_value': 100000,
                'loan_days': 30,
                'client_id': target_client_id
            }
        )
        assert response.status_code >= 400, "Horizontal privilege escalation via direct client_id manipulation should be prevented"
        
        # Test parameter tampering with special characters or encoding
        response = client.request(
            method="POST",
            endpoint="/api/v1/calculate-locate",
            json_data={
                'ticker': 'AAPL',
                'position_value': 100000,
                'loan_days': 30,
                'client_id': f"{own_client_id}' OR client_id='{target_client_id}"
            }
        )
        assert response.status_code >= 400, "Horizontal privilege escalation via SQL injection-like parameter tampering should be prevented"
        
        # Test direct object reference manipulation
        if hasattr(settings, 'calculation_id_format') and settings.calculation_id_format == 'numeric':
            # If IDs are numeric and potentially predictable
            response = client.request(
                method="GET",
                endpoint="/api/v1/calculations/12345"  # Assuming this is another client's calculation ID
            )
            assert response.status_code >= 400, "Direct object reference manipulation should be prevented"
        
        logger.info("Horizontal privilege escalation tests completed successfully")
    
    def test_vertical_privilege_escalation(self):
        """Tests for vertical privilege escalation vulnerabilities."""
        # Attempt to access admin functions with client role
        client = self.client_api
        
        # Test accessing configuration endpoints (admin only)
        admin_endpoints = [
            '/api/v1/admin/configuration',
            '/api/v1/admin/users',
            '/api/v1/admin/logs'
        ]
        
        for endpoint in admin_endpoints:
            response = client.request(method="GET", endpoint=endpoint)
            assert response.status_code >= 400, f"Vertical privilege escalation to admin endpoint {endpoint} should be prevented"
        
        # Test accessing audit logs with client role
        response = client.request(method="GET", endpoint="/api/v1/audit-logs")
        assert response.status_code >= 400, "Vertical privilege escalation to audit logs should be prevented"
        
        # Test parameter tampering to gain admin privileges
        response = client.request(
            method="POST",
            endpoint="/api/v1/calculate-locate",
            json_data={
                'ticker': 'AAPL',
                'position_value': 100000,
                'loan_days': 30,
                'client_id': 'test_broker_1',
                'admin': True,  # Adding admin flag that shouldn't be honored
                'is_admin': True
            }
        )
        
        # Check that the response doesn't contain admin-specific information
        if response.status_code < 400:
            response_data = response.json()
            assert 'admin_info' not in response_data, "Response should not contain admin-specific information"
            assert 'confidential' not in str(response_data), "Response should not contain confidential information"
        
        logger.info("Vertical privilege escalation tests completed successfully")
    
    def test_function_level_authorization(self):
        """Tests authorization at the function level within endpoints."""
        # Test endpoints that support multiple operations
        
        # Auditor should be able to view rates but not calculate fees
        auditor = self.auditor_api
        
        # Should succeed - viewing rates is allowed for auditors
        response = auditor.request(method="GET", endpoint="/api/v1/rates/AAPL")
        assert response.status_code < 400, "Auditor should be able to view rates"
        
        # Should fail - calculating fees is not allowed for auditors
        response = auditor.request(
            method="POST",
            endpoint="/api/v1/calculate-locate",
            json_data={
                'ticker': 'AAPL',
                'position_value': 100000,
                'loan_days': 30,
                'client_id': 'test_broker_1'
            }
        )
        assert response.status_code >= 400, "Auditor should not be able to calculate fees"
        
        # Client should be able to both view rates and calculate fees
        client = self.client_api
        
        # Should succeed - viewing rates is allowed for clients
        response = client.request(method="GET", endpoint="/api/v1/rates/AAPL")
        assert response.status_code < 400, "Client should be able to view rates"
        
        # Should succeed - calculating fees is allowed for clients
        response = client.request(
            method="POST",
            endpoint="/api/v1/calculate-locate",
            json_data={
                'ticker': 'AAPL',
                'position_value': 100000,
                'loan_days': 30,
                'client_id': 'test_broker_1'
            }
        )
        assert response.status_code < 400, "Client should be able to calculate fees"
        
        logger.info("Function-level authorization tests completed successfully")
    
    def test_data_level_authorization(self):
        """Tests authorization at the data level within responses."""
        # Make requests with different roles to endpoints that return data
        
        # Admin should see full data including sensitive fields
        admin = self.admin_api
        admin_response = admin.request(method="GET", endpoint="/api/v1/rates/AAPL")
        assert admin_response.status_code < 400, "Admin should be able to view rates"
        
        if admin_response.status_code < 400:
            admin_data = admin_response.json()
            
            # Client should see limited data with sensitive fields masked or removed
            client = self.client_api
            client_response = client.request(method="GET", endpoint="/api/v1/rates/AAPL")
            assert client_response.status_code < 400, "Client should be able to view rates"
            
            if client_response.status_code < 400:
                client_data = client_response.json()
                
                # Check if admin response has more fields than client response
                assert len(str(admin_data)) >= len(str(client_data)), "Admin should receive at least as much data as client"
                
                # Check for specific fields that might be masked or filtered
                # Note: The exact fields would depend on the API design
                sensitive_fields = ['internal_id', 'data_source_details', 'admin_notes', 'raw_api_response']
                
                for field in sensitive_fields:
                    if field in admin_data:
                        assert field not in client_data or admin_data[field] != client_data[field], f"Sensitive field {field} should be masked or removed for client role"
        
        logger.info("Data-level authorization tests completed successfully")
    
    def test_authorization_bypass_attempts(self):
        """Tests various authorization bypass techniques."""
        # Create client without authentication
        unauthenticated_client = create_security_client(settings, api_key=None)
        
        # Test URL manipulation to bypass authorization checks
        bypass_attempts = [
            # Path traversal
            "/api/../admin/configuration",
            "/api/v1/..%2f..%2fadmin%2fconfiguration",
            "/api/v1/rates/../../admin/users",
            
            # Case sensitivity
            "/API/v1/admin/configuration",
            "/api/V1/admin/configuration",
            
            # Double extensions
            "/api/v1/rates.json/AAPL",
            "/api/v1/calculate-locate.json"
        ]
        
        for attempt in bypass_attempts:
            response = unauthenticated_client.request(method="GET", endpoint=attempt)
            assert response.status_code >= 400, f"Authorization bypass attempt via URL manipulation should be prevented: {attempt}"
        
        # Test HTTP method switching (GET vs POST)
        # Try to use GET on a POST-only endpoint
        response = self.client_api.request(method="GET", endpoint="/api/v1/calculate-locate")
        assert response.status_code >= 400, "HTTP method switching from POST to GET should be prevented"
        
        # Try to use POST on a GET-only endpoint
        response = self.client_api.request(method="POST", endpoint="/api/v1/rates/AAPL")
        assert response.status_code >= 400, "HTTP method switching from GET to POST should be prevented"
        
        # Test request header manipulation
        headers_to_test = {
            "X-Original-URL": "/admin/configuration",
            "X-Rewrite-URL": "/admin/configuration",
            "X-Forwarded-For": "127.0.0.1",
            "X-Forwarded-Host": "internal-admin.example.com",
            "Host": "internal-admin.example.com"
        }
        
        for header_name, header_value in headers_to_test.items():
            custom_headers = {header_name: header_value}
            response = self.client_api.request(
                method="GET", 
                endpoint="/api/v1/rates/AAPL",
                headers=custom_headers
            )
            # The request should either be rejected or processed normally without granting additional access
            if response.status_code < 400:
                # If it succeeds, it should not contain admin data
                response_data = response.json() if hasattr(response, 'json') else {}
                assert 'admin_info' not in str(response_data), f"Header manipulation {header_name}:{header_value} should not grant additional access"
        
        logger.info("Authorization bypass attempt tests completed successfully")
    
    def test_authorization_headers(self):
        """Tests the security of authorization-related headers."""
        # Make authorized requests and examine response headers
        response = self.client_api.request(method="GET", endpoint="/api/v1/rates/AAPL")
        
        if response.status_code < 400:
            # Check that authorization details are not leaked in headers
            sensitive_headers = ['Authorization', 'X-API-Key', 'Cookie', 'Set-Cookie']
            for header in sensitive_headers:
                assert header not in response.headers or not response.headers[header], f"Sensitive header {header} should not be exposed in response"
            
            # Check that no sensitive role information is exposed
            for header_name, header_value in response.headers.items():
                assert 'role' not in header_name.lower(), f"Header {header_name} may expose role information"
                assert 'admin' not in header_value.lower(), f"Header {header_name} may expose admin information"
                assert 'permission' not in header_value.lower(), f"Header {header_name} may expose permission information"
        
        # Check CORS headers if present
        if 'Access-Control-Allow-Origin' in response.headers:
            origin = response.headers['Access-Control-Allow-Origin']
            assert origin != '*', "CORS should not allow all origins for endpoints requiring authorization"
            assert 'null' not in origin, "CORS should not allow 'null' origin for endpoints requiring authorization"
        
        logger.info("Authorization header tests completed successfully")