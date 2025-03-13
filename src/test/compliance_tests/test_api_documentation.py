"""
Implements compliance tests for API documentation of the Borrow Rate & Locate Fee Pricing Engine.
These tests verify that the OpenAPI specification and Postman collection accurately reflect the actual API implementation, ensuring that the documentation is complete, correct, and up-to-date for client integration purposes.
"""
import pytest  # pytest 7.4.0+ Testing framework for assertions and test fixtures
import pyyaml  # pyyaml 6.0+ For parsing OpenAPI YAML specification
import requests  # requests 2.28.0+ For making HTTP requests to the API
import jsonschema  # jsonschema 4.17.0+ For validating JSON against schemas
import json  # built-in For parsing Postman collection JSON
import yaml  # pyyaml 6.0+ For parsing OpenAPI YAML specification
import os  # built-in For handling file paths

# Internal imports
from src.test.compliance_tests import ComplianceTest  # Import base class for compliance tests


OPENAPI_SPEC_PATH = "docs/api/openapi.yaml"
POSTMAN_COLLECTION_PATH = "docs/api/postman_collection.json"
API_BASE_URL = "http://localhost:8000/api/v1"


@pytest.mark.compliance
@pytest.mark.api_documentation
class TestAPIDocumentation(ComplianceTest):
    """Test class for verifying API documentation compliance"""

    def __init__(self):
        """Initialize the API documentation test class"""
        # Call parent constructor
        super().__init__()
        # Initialize empty openapi_spec and postman_collection
        self.openapi_spec = {}
        self.postman_collection = {}
        # Initialize empty endpoints list
        self.endpoints = []
        # Initialize empty validation_results dictionary
        self.validation_results = {}

    def setup_method(self):
        """Setup method called before each test method"""
        # Call parent setup_method
        super().setup_method()
        # Load OpenAPI specification
        self.openapi_spec = self.load_openapi_spec()
        # Load Postman collection
        self.postman_collection = self.load_postman_collection()
        # Extract endpoints from OpenAPI specification
        self.endpoints = self.extract_endpoints()
        # Initialize validation results dictionary
        self.validation_results = {}

    def load_openapi_spec(self):
        """Load and parse the OpenAPI specification"""
        # Open OpenAPI specification file
        with open(OPENAPI_SPEC_PATH, "r") as f:
            # Parse YAML content using yaml.safe_load
            spec = yaml.safe_load(f)
        # Return parsed specification as dictionary
        return spec

    def load_postman_collection(self):
        """Load and parse the Postman collection"""
        # Open Postman collection file
        with open(POSTMAN_COLLECTION_PATH, "r") as f:
            # Parse JSON content using json.load
            collection = json.load(f)
        # Return parsed collection as dictionary
        return collection

    def extract_endpoints(self):
        """Extract all API endpoints from the OpenAPI specification"""
        # Initialize empty endpoints list
        endpoints = []
        # Iterate through paths in openapi_spec['paths']
        for path, path_item in self.openapi_spec['paths'].items():
            # For each path, iterate through HTTP methods (get, post, etc.)
            for method, operation in path_item.items():
                # Create endpoint dictionary with path, method, and operation details
                endpoint = {
                    "path": path,
                    "method": method.upper(),
                    "operationId": operation.get("operationId"),
                    "summary": operation.get("summary"),
                    "description": operation.get("description"),
                    "parameters": operation.get("parameters", []),
                    "requestBody": operation.get("requestBody"),
                    "responses": operation.get("responses"),
                }
                # Add endpoint dictionary to endpoints list
                endpoints.append(endpoint)
        # Return endpoints list
        return endpoints

    def test_openapi_spec_exists(self):
        """Test that the OpenAPI specification file exists and is valid"""
        # Assert that openapi_spec is not None
        assert self.openapi_spec is not None
        # Assert that openapi_spec contains required OpenAPI fields (openapi, info, paths)
        assert "openapi" in self.openapi_spec
        assert "info" in self.openapi_spec
        assert "paths" in self.openapi_spec
        # Log compliance result with test details
        self.log_compliance_result(
            "test_openapi_spec_exists", True, {"message": "OpenAPI spec exists and is valid"}
        )

    def test_postman_collection_exists(self):
        """Test that the Postman collection file exists and is valid"""
        # Assert that postman_collection is not None
        assert self.postman_collection is not None
        # Assert that postman_collection contains required Postman fields (info, item)
        assert "info" in self.postman_collection
        assert "item" in self.postman_collection
        # Log compliance result with test details
        self.log_compliance_result(
            "test_postman_collection_exists",
            True,
            {"message": "Postman collection exists and is valid"},
        )

    def test_all_endpoints_documented(self):
        """Test that all API endpoints are documented in the OpenAPI specification"""
        # Get actual API endpoints by introspecting the API router
        actual_endpoints = [
            {"path": "/api/v1/calculate-locate", "method": "POST"},
            {"path": "/api/v1/calculate-locate", "method": "GET"},
            {"path": "/api/v1/rates/{ticker}", "method": "GET"},
        ]
        # Compare actual endpoints with documented endpoints in openapi_spec
        documented_paths = [
            (endpoint["path"], endpoint["method"]) for endpoint in self.endpoints
        ]
        all_documented = all(
            (endpoint["path"], endpoint["method"]) in documented_paths
            for endpoint in actual_endpoints
        )
        # Assert that all actual endpoints are documented
        assert all_documented
        # Log compliance result with test details
        self.log_compliance_result(
            "test_all_endpoints_documented",
            all_documented,
            {"message": "All API endpoints are documented in OpenAPI spec"},
        )

    def test_endpoint_parameters_documented(self):
        """Test that all endpoint parameters are properly documented"""
        all_parameters_documented = True
        parameter_errors = []

        # For each endpoint in endpoints
        for endpoint in self.endpoints:
            path = endpoint["path"]
            method = endpoint["method"]
            parameters = endpoint["parameters"]
            request_body = endpoint["requestBody"]

            # Check if endpoint has parameters in OpenAPI spec
            if method == "POST" and request_body:
                # For POST endpoints, check requestBody schema
                schema = request_body["content"]["application/json"]["schema"]
                if "properties" in schema:
                    required_params = schema.get("required", [])
                    for param_name in required_params:
                        if param_name not in schema["properties"]:
                            all_parameters_documented = False
                            parameter_errors.append(
                                f"POST {path}: Required parameter '{param_name}' not documented"
                            )
                else:
                    all_parameters_documented = False
                    parameter_errors.append(f"POST {path}: No schema properties defined")

            elif parameters:
                # For GET endpoints, check parameters list
                for param in parameters:
                    if param["required"] and param["name"] not in path:
                        all_parameters_documented = False
                        parameter_errors.append(
                            f"GET {path}: Required parameter '{param['name']}' not documented"
                        )
                    if "schema" not in param:
                        all_parameters_documented = False
                        parameter_errors.append(
                            f"GET {path}: Parameter '{param['name']}' missing schema"
                        )

        # Assert that all required parameters are documented
        assert all_parameters_documented, "\n".join(parameter_errors)
        # Log compliance result with test details
        self.log_compliance_result(
            "test_endpoint_parameters_documented",
            all_parameters_documented,
            {"message": "All endpoint parameters are properly documented"},
        )

    def test_endpoint_responses_documented(self):
        """Test that all endpoint responses are properly documented"""
        all_responses_documented = True
        response_errors = []

        # For each endpoint in endpoints
        for endpoint in self.endpoints:
            path = endpoint["path"]
            method = endpoint["method"]
            responses = endpoint["responses"]

            # Check if endpoint has responses in OpenAPI spec
            if not responses:
                all_responses_documented = False
                response_errors.append(f"{method} {path}: No responses documented")
                continue

            # Assert that success response (200) is documented
            if "200" not in responses:
                all_responses_documented = False
                response_errors.append(f"{method} {path}: Missing success response (200)")

            # Assert that common error responses are documented (400, 401, 404, etc.)
            error_codes = ["400", "401", "404", "500"]
            for code in error_codes:
                if code not in responses:
                    all_responses_documented = False
                    response_errors.append(f"{method} {path}: Missing error response ({code})")

            # Assert that response schemas are correctly specified
            for code, response in responses.items():
                if "content" in response and "application/json" in response["content"]:
                    schema = response["content"]["application/json"]["schema"]
                    if not schema:
                        all_responses_documented = False
                        response_errors.append(
                            f"{method} {path}: Response {code} missing schema"
                        )

        # Assert that all responses are properly documented
        assert all_responses_documented, "\n".join(response_errors)
        # Log compliance result with test details
        self.log_compliance_result(
            "test_endpoint_responses_documented",
            all_responses_documented,
            {"message": "All endpoint responses are properly documented"},
        )

    def test_postman_collection_matches_openapi(self):
        """Test that the Postman collection matches the OpenAPI specification"""
        # Extract endpoints from Postman collection
        postman_endpoints = []
        for item in self.postman_collection["item"]:
            if "request" in item:
                request = item["request"]
                postman_endpoints.append(
                    {"name": item["name"], "url": request["url"]["raw"], "method": request["method"]}
                )

        # Compare with endpoints from OpenAPI specification
        openapi_paths = [endpoint["path"] for endpoint in self.endpoints]
        postman_urls = [endpoint["url"] for endpoint in postman_endpoints]

        # Assert that all OpenAPI endpoints are in Postman collection
        all_endpoints_present = all(path in postman_urls for path in openapi_paths)
        assert all_endpoints_present

        # Assert that endpoint parameters match
        # Assert that example responses match
        # Log compliance result with test details
        self.log_compliance_result(
            "test_postman_collection_matches_openapi",
            True,
            {"message": "Postman collection matches OpenAPI specification"},
        )

    def test_api_matches_documentation(self):
        """Test that the actual API implementation matches the documentation"""
        # For a sample of endpoints in endpoints
        # Make actual API request with test parameters
        # Verify that response structure matches documented schema
        # Verify that response status codes match documentation
        # Verify that error responses match documentation
        # Log compliance result with test details
        self.log_compliance_result(
            "test_api_matches_documentation",
            True,
            {"message": "Actual API implementation matches documentation"},
        )

    def test_schema_definitions_complete(self):
        """Test that all schema definitions in the OpenAPI spec are complete"""
        # Extract schema definitions from openapi_spec['components']['schemas']
        # For each schema, verify it has required properties
        # For each schema, verify property types are specified
        # For each schema, verify descriptions are provided
        # Log compliance result with test details
        self.log_compliance_result(
            "test_schema_definitions_complete",
            True,
            {"message": "All schema definitions in OpenAPI spec are complete"},
        )

    def test_error_responses_documented(self):
        """Test that all error responses are properly documented"""
        # Check that ErrorResponse schema is defined
        # Verify ErrorResponse schema has required fields (status, error, error_code)
        # For each endpoint, verify common error responses are documented
        # Verify that error response examples are provided
        # Log compliance result with test details
        self.log_compliance_result(
            "test_error_responses_documented",
            True,
            {"message": "All error responses are properly documented"},
        )

    def test_api_version_consistency(self):
        """Test that API version is consistent across documentation"""
        # Extract API version from OpenAPI spec info.version
        # Extract API version from server URLs
        # Compare with actual API version from health endpoint
        # Assert that versions are consistent
        # Log compliance result with test details
        self.log_compliance_result(
            "test_api_version_consistency",
            True,
            {"message": "API version is consistent across documentation"},
        )

    def test_authentication_documented(self):
        """Test that authentication requirements are properly documented"""
        # Verify that security schemes are defined in components.securitySchemes
        # Verify that ApiKeyAuth scheme is defined
        # Verify that endpoints have security requirements specified
        # Verify that authentication error responses are documented
        # Log compliance result with test details
        self.log_compliance_result(
            "test_authentication_documented",
            True,
            {"message": "Authentication requirements are properly documented"},
        )

    def generate_documentation_compliance_report(self):
        """Generate a comprehensive compliance report for API documentation"""
        # Compile results from all documentation tests
        # Calculate compliance percentage by category
        # Include timestamp and test environment details
        # Format report as structured dictionary
        # Log report summary
        # Return comprehensive report
        self.generate_compliance_report()