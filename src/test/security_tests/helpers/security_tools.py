"""
Provides security testing tools and utilities for the Borrow Rate & Locate Fee Pricing Engine.
Implements functionality for security scanning, penetration testing, authentication testing,
and API security validation. This module serves as the core toolset for security tests to verify
the system's security controls.
"""

import requests  # version: 2.28.0+
import json  # standard library
import logging  # standard library
import typing  # standard library
from typing import Dict, List, Optional, Union, Any, Callable  # standard library
import time  # standard library
import subprocess  # standard library
import jwt  # version: 2.6.0

# Internal imports
from ..config.settings import get_test_settings, TestSettings
from ../../integration_tests.helpers.api_client import APIClient
from .payloads import SQLInjectionPayloads, XSSPayloads, AuthBypassPayloads, InputValidationPayloads

# Configure module logger
logger = logging.getLogger(__name__)

# Default values
DEFAULT_SCAN_TIMEOUT = 300  # 5 minutes
DEFAULT_REQUEST_TIMEOUT = 30  # 30 seconds
DEFAULT_RETRY_COUNT = 3


def create_security_client(settings: Optional[TestSettings] = None, api_key: Optional[str] = None) -> 'SecurityAPIClient':
    """
    Creates a security-focused API client for testing
    
    Args:
        settings: Optional test settings configuration
        api_key: Optional API key to use
        
    Returns:
        Configured security API client instance
    """
    if settings is None:
        settings = get_test_settings()
    
    if api_key is None:
        api_key = settings.test_api_key
    
    client = SecurityAPIClient(settings=settings, api_key=api_key)
    return client


def run_security_scan(
    target_url: str, 
    scan_options: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Runs a comprehensive security scan against the API
    
    Args:
        target_url: URL to scan
        scan_options: Optional scan configuration options
        timeout: Maximum time to wait for scan completion in seconds
        
    Returns:
        Security scan results with vulnerabilities found
    """
    # Get settings and ZAP configuration
    settings = get_test_settings()
    zap_config = settings.get_security_tool_config("zap")
    
    # Set default timeout if not provided
    if timeout is None:
        timeout = settings.security_scan_timeout if hasattr(settings, "security_scan_timeout") else DEFAULT_SCAN_TIMEOUT
    
    # Create ZAP scanner
    scanner = ZAPScanner(zap_config)
    
    try:
        # Initialize scanner
        if not scanner.initialize():
            return {
                "status": "error",
                "error": "Failed to initialize ZAP scanner",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Start the scan
        scan_id = scanner.start_scan(target_url, scan_options)
        
        # Wait for scan to complete or timeout
        scan_completed = scanner.wait_for_scan_completion(scan_id, timeout)
        
        if not scan_completed:
            return {
                "status": "timeout",
                "message": f"Scan did not complete within {timeout} seconds",
                "scan_id": scan_id,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Get scan results
        results = scanner.get_scan_results(scan_id)
        results["status"] = "completed"
        
        return results
        
    except Exception as e:
        logger.error(f"Error running security scan: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }


def test_authentication_bypass(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Tests API endpoints for authentication bypass vulnerabilities
    
    Args:
        endpoint: API endpoint to test
        params: Optional query parameters
        json_data: Optional JSON payload
        
    Returns:
        Test results with vulnerabilities found
    """
    # Get settings and create client with invalid key
    settings = get_test_settings()
    client = SecurityAPIClient(settings, api_key=settings.invalid_api_key)
    
    # Get authentication bypass payloads
    auth_payloads = AuthBypassPayloads()
    
    results = {
        "endpoint": endpoint,
        "tests_run": [],
        "vulnerabilities_found": [],
        "test_results": {}
    }
    
    # Test with missing authentication header
    results["tests_run"].append("missing_auth_header")
    try:
        headers = {}  # No auth header
        response = requests.request(
            method="GET" if not json_data else "POST",
            url=f"{settings.get_api_url()}{endpoint}",
            params=params,
            json=json_data,
            headers=headers
        )
        
        accepted = response.status_code < 400
        results["test_results"]["missing_auth_header"] = {
            "status_code": response.status_code,
            "accepted": accepted
        }
        
        if accepted:
            results["vulnerabilities_found"].append({
                "type": "missing_auth_header",
                "severity": "critical",
                "description": "Request without authentication header was accepted"
            })
    except Exception as e:
        results["test_results"]["missing_auth_header"] = {
            "error": str(e)
        }
    
    # Test with empty API key
    results["tests_run"].append("empty_api_key")
    try:
        headers = {"X-API-Key": ""}
        response = requests.request(
            method="GET" if not json_data else "POST",
            url=f"{settings.get_api_url()}{endpoint}",
            params=params,
            json=json_data,
            headers=headers
        )
        
        accepted = response.status_code < 400
        results["test_results"]["empty_api_key"] = {
            "status_code": response.status_code,
            "accepted": accepted
        }
        
        if accepted:
            results["vulnerabilities_found"].append({
                "type": "empty_api_key",
                "severity": "critical",
                "description": "Request with empty API key was accepted"
            })
    except Exception as e:
        results["test_results"]["empty_api_key"] = {
            "error": str(e)
        }
    
    # Test with various tampered API keys
    for api_key in auth_payloads.get_payload("api_keys"):
        test_name = f"tampered_api_key_{api_key}" if api_key else "tampered_api_key_empty"
        results["tests_run"].append(test_name)
        
        try:
            headers = {"X-API-Key": api_key}
            response = requests.request(
                method="GET" if not json_data else "POST",
                url=f"{settings.get_api_url()}{endpoint}",
                params=params,
                json=json_data,
                headers=headers
            )
            
            accepted = response.status_code < 400
            results["test_results"][test_name] = {
                "status_code": response.status_code,
                "accepted": accepted
            }
            
            if accepted:
                results["vulnerabilities_found"].append({
                    "type": test_name,
                    "severity": "critical",
                    "description": f"Request with tampered API key '{api_key}' was accepted"
                })
        except Exception as e:
            results["test_results"][test_name] = {
                "error": str(e)
            }
    
    # Try to get a JWT token if applicable
    try:
        auth_response = requests.post(
            url=f"{settings.get_api_url()}/auth/login",
            json={"username": "test", "password": "test"}
        )
        
        if auth_response.status_code == 200:
            token = auth_response.json().get("token")
            
            if token:
                # Test JWT vulnerabilities
                jwt_analyzer = JWTAnalyzer()
                jwt_results = jwt_analyzer.test_token_vulnerabilities(endpoint, token, client)
                
                # Merge JWT test results
                results["tests_run"].extend([f"jwt_{test}" for test in jwt_results["tests_run"]])
                results["vulnerabilities_found"].extend(jwt_results["vulnerabilities_found"])
                
                for key, value in jwt_results["test_results"].items():
                    results["test_results"][f"jwt_{key}"] = value
    except Exception:
        # JWT testing not applicable or failed
        pass
    
    # Add summary
    results["vulnerability_count"] = len(results["vulnerabilities_found"])
    results["is_vulnerable"] = results["vulnerability_count"] > 0
    results["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    return results


def test_authorization(
    endpoint: str,
    method: str,
    required_roles: List[str],
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Tests API endpoints for authorization vulnerabilities
    
    Args:
        endpoint: API endpoint to test
        method: HTTP method (GET, POST, etc.)
        required_roles: List of roles that should be able to access the endpoint
        params: Optional query parameters
        json_data: Optional JSON payload
        
    Returns:
        Test results with vulnerabilities found
    """
    # Get settings
    settings = get_test_settings()
    
    results = {
        "endpoint": endpoint,
        "method": method,
        "required_roles": required_roles,
        "tests_run": [],
        "vulnerabilities_found": [],
        "test_results": {}
    }
    
    # Define test roles
    test_roles = {
        "admin": settings.get_security_tool_config("jwt_analyzer").get("admin_api_key", settings.test_api_key),
        "user": settings.get_security_tool_config("jwt_analyzer").get("user_api_key", settings.invalid_api_key),
        "readonly": settings.get_security_tool_config("jwt_analyzer").get("readonly_api_key", settings.invalid_api_key),
        "none": settings.invalid_api_key
    }
    
    # Test access with each role
    for role, api_key in test_roles.items():
        test_name = f"role_{role}"
        results["tests_run"].append(test_name)
        
        client = SecurityAPIClient(settings, api_key=api_key)
        
        try:
            response = client.request(
                method=method,
                endpoint=endpoint,
                params=params,
                json_data=json_data
            )
            
            accepted = response.status_code < 400
            results["test_results"][test_name] = {
                "status_code": response.status_code,
                "accepted": accepted
            }
            
            # Check for authorization issues
            if accepted and role not in required_roles and role != "admin":
                results["vulnerabilities_found"].append({
                    "type": "unauthorized_role_access",
                    "severity": "high",
                    "description": f"Role '{role}' can access endpoint that requires {required_roles}"
                })
            
            if not accepted and role in required_roles:
                results["vulnerabilities_found"].append({
                    "type": "missing_authorized_access",
                    "severity": "medium",
                    "description": f"Role '{role}' should have access but was denied"
                })
                
        except Exception as e:
            results["test_results"][test_name] = {
                "error": str(e)
            }
    
    # Test for horizontal privilege escalation (accessing other users' resources)
    if "resource_id" in (params or {}) or "resource_id" in (json_data or {}):
        test_name = "horizontal_privilege_escalation"
        results["tests_run"].append(test_name)
        
        try:
            # Create a request with a different resource ID
            other_params = params.copy() if params else {}
            other_json = json_data.copy() if json_data else {}
            
            if "resource_id" in other_params:
                orig_id = other_params["resource_id"]
                other_params["resource_id"] = f"other-{orig_id}"
            elif "resource_id" in other_json:
                orig_id = other_json["resource_id"]
                other_json["resource_id"] = f"other-{orig_id}"
            else:
                # Add resource_id if not present
                other_json["resource_id"] = "other-resource"
            
            client = SecurityAPIClient(settings, api_key=test_roles["user"])
            response = client.request(
                method=method,
                endpoint=endpoint,
                params=other_params,
                json_data=other_json
            )
            
            accepted = response.status_code < 400
            results["test_results"][test_name] = {
                "status_code": response.status_code,
                "accepted": accepted
            }
            
            if accepted:
                results["vulnerabilities_found"].append({
                    "type": "horizontal_privilege_escalation",
                    "severity": "high",
                    "description": "User can access resources belonging to other users"
                })
                
        except Exception as e:
            results["test_results"][test_name] = {
                "error": str(e)
            }
    
    # Test for vertical privilege escalation (accessing admin functions)
    if any(role in required_roles for role in ["admin", "administrator"]):
        test_name = "vertical_privilege_escalation"
        results["tests_run"].append(test_name)
        
        try:
            # Test with parameter tampering
            tampered_params = params.copy() if params else {}
            tampered_json = json_data.copy() if json_data else {}
            
            # Add common admin flags
            tampered_params["admin"] = "true"
            tampered_params["is_admin"] = "true"
            tampered_json["admin"] = True
            tampered_json["is_admin"] = True
            
            client = SecurityAPIClient(settings, api_key=test_roles["user"])
            response = client.request(
                method=method,
                endpoint=endpoint,
                params=tampered_params,
                json_data=tampered_json
            )
            
            accepted = response.status_code < 400
            results["test_results"][test_name] = {
                "status_code": response.status_code,
                "accepted": accepted
            }
            
            if accepted:
                results["vulnerabilities_found"].append({
                    "type": "vertical_privilege_escalation",
                    "severity": "critical",
                    "description": "Non-admin user can access admin functions through parameter tampering"
                })
                
        except Exception as e:
            results["test_results"][test_name] = {
                "error": str(e)
            }
    
    # Add summary
    results["vulnerability_count"] = len(results["vulnerabilities_found"])
    results["is_vulnerable"] = results["vulnerability_count"] > 0
    results["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    return results


def test_input_validation(
    endpoint: str,
    method: str,
    field_specs: Dict[str, Dict[str, Any]],
    valid_request: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Tests API endpoints for input validation vulnerabilities
    
    Args:
        endpoint: API endpoint to test
        method: HTTP method (GET, POST, etc.)
        field_specs: Specifications for fields to test (type, limits, etc.)
        valid_request: Optional valid request to use as a base
        
    Returns:
        Test results with vulnerabilities found
    """
    # Get settings and create client
    settings = get_test_settings()
    client = SecurityAPIClient(settings, api_key=settings.test_api_key)
    
    results = {
        "endpoint": endpoint,
        "method": method,
        "tests_run": [],
        "vulnerabilities_found": [],
        "test_results": {}
    }
    
    # Create a valid base request if not provided
    base_request = valid_request.copy() if valid_request else {}
    for field, specs in field_specs.items():
        if field not in base_request:
            # Set a default valid value based on field type
            if specs.get("type") == "string":
                base_request[field] = specs.get("example", "test")
            elif specs.get("type") == "number":
                base_request[field] = specs.get("example", 100)
            elif specs.get("type") == "boolean":
                base_request[field] = specs.get("example", True)
            elif specs.get("type") == "object":
                base_request[field] = specs.get("example", {})
            elif specs.get("type") == "array":
                base_request[field] = specs.get("example", [])
    
    # Test each field
    for field, specs in field_specs.items():
        field_type = specs.get("type", "string")
        
        # 1. Test boundary values for numeric fields
        if field_type == "number":
            payload_provider = InputValidationPayloads()
            
            # Get boundary values
            if field == "position_value":
                boundary_values = payload_provider.generate_boundary_values("position_value")
            elif field == "loan_days":
                boundary_values = payload_provider.generate_boundary_values("loan_days")
            else:
                # Generic boundary values
                min_val = specs.get("minimum", 0)
                max_val = specs.get("maximum", 1000)
                boundary_values = {
                    "min": min_val,
                    "min-1": min_val - 1,
                    "max": max_val,
                    "max+1": max_val + 1,
                    "zero": 0,
                    "negative": -1
                }
            
            # Test each boundary value
            for boundary_name, value in boundary_values.items():
                test_name = f"{field}_boundary_{boundary_name}"
                results["tests_run"].append(test_name)
                
                try:
                    test_request = base_request.copy()
                    test_request[field] = value
                    
                    response = client.request(
                        method=method,
                        endpoint=endpoint,
                        json_data=test_request if method.upper() != "GET" else None,
                        params=test_request if method.upper() == "GET" else None
                    )
                    
                    # Expected result based on boundary type
                    should_be_valid = True
                    if "min-" in boundary_name or "max+" in boundary_name or boundary_name == "negative":
                        should_be_valid = False
                    
                    # Actually valid (accepted by API)
                    is_valid = response.status_code < 400
                    
                    results["test_results"][test_name] = {
                        "status_code": response.status_code,
                        "value_tested": value,
                        "is_valid": is_valid,
                        "should_be_valid": should_be_valid
                    }
                    
                    # Check for validation issues
                    if is_valid != should_be_valid:
                        severity = "medium"
                        if boundary_name in ["negative", "min-1"] and is_valid:
                            severity = "high"  # More serious issues
                            
                        results["vulnerabilities_found"].append({
                            "type": "boundary_validation",
                            "field": field,
                            "value": value,
                            "boundary": boundary_name,
                            "severity": severity,
                            "description": f"Field '{field}' accepts invalid {boundary_name} value: {value}"
                                if is_valid and not should_be_valid
                                else f"Field '{field}' rejects valid {boundary_name} value: {value}"
                        })
                        
                except Exception as e:
                    results["test_results"][test_name] = {
                        "error": str(e)
                    }
        
        # 2. Test invalid types
        test_name = f"{field}_invalid_type"
        results["tests_run"].append(test_name)
        
        try:
            test_request = base_request.copy()
            
            # Set value of wrong type
            if field_type == "string":
                test_request[field] = 12345  # Number instead of string
            elif field_type == "number":
                test_request[field] = "not_a_number"  # String instead of number
            elif field_type == "boolean":
                test_request[field] = "not_a_boolean"  # String instead of boolean
            elif field_type == "object":
                test_request[field] = "not_an_object"  # String instead of object
            elif field_type == "array":
                test_request[field] = "not_an_array"  # String instead of array
            
            response = client.request(
                method=method,
                endpoint=endpoint,
                json_data=test_request if method.upper() != "GET" else None,
                params=test_request if method.upper() == "GET" else None
            )
            
            # Should not be valid
            is_valid = response.status_code < 400
            
            results["test_results"][test_name] = {
                "status_code": response.status_code,
                "value_tested": test_request[field],
                "is_valid": is_valid,
                "should_be_valid": False
            }
            
            if is_valid:
                results["vulnerabilities_found"].append({
                    "type": "type_validation",
                    "field": field,
                    "value": test_request[field],
                    "severity": "medium",
                    "description": f"Field '{field}' accepts invalid type (should be {field_type})"
                })
                
        except Exception as e:
            results["test_results"][test_name] = {
                "error": str(e)
            }
        
        # 3. Test SQL injection for string fields
        if field_type == "string":
            payload_provider = SQLInjectionPayloads()
            sql_payloads = payload_provider.get_payload("basic")[:3]  # Limit to 3 payloads
            
            for i, payload in enumerate(sql_payloads):
                test_name = f"{field}_sql_injection_{i}"
                results["tests_run"].append(test_name)
                
                try:
                    test_request = base_request.copy()
                    test_request[field] = payload
                    
                    response = client.request(
                        method=method,
                        endpoint=endpoint,
                        json_data=test_request if method.upper() != "GET" else None,
                        params=test_request if method.upper() == "GET" else None
                    )
                    
                    # Check for SQL injection issues
                    sql_error_indicators = [
                        "sql", "syntax", "mysql", "postgres", "sqlite", "oracle",
                        "syntax error", "unterminated", "incorrect"
                    ]
                    
                    has_sql_error = False
                    try:
                        resp_body = response.json() if response.text else {}
                        error_msg = str(resp_body.get("error", {}).get("message", "")).lower()
                        has_sql_error = any(indicator in error_msg for indicator in sql_error_indicators)
                    except (json.JSONDecodeError, ValueError, AttributeError):
                        # Check in raw response if not JSON
                        has_sql_error = any(indicator in response.text.lower() for indicator in sql_error_indicators)
                    
                    is_valid = response.status_code < 400
                    
                    results["test_results"][test_name] = {
                        "status_code": response.status_code,
                        "value_tested": payload,
                        "is_valid": is_valid,
                        "has_sql_error": has_sql_error
                    }
                    
                    if has_sql_error:
                        results["vulnerabilities_found"].append({
                            "type": "sql_injection",
                            "field": field,
                            "payload": payload,
                            "severity": "critical",
                            "description": f"Field '{field}' is vulnerable to SQL injection"
                        })
                    elif is_valid:
                        results["vulnerabilities_found"].append({
                            "type": "sql_injection_possible",
                            "field": field,
                            "payload": payload,
                            "severity": "medium",
                            "description": f"Field '{field}' accepts SQL injection payload without validation"
                        })
                        
                except Exception as e:
                    results["test_results"][test_name] = {
                        "error": str(e)
                    }
        
        # 4. Test XSS for string fields
        if field_type == "string":
            payload_provider = XSSPayloads()
            xss_payloads = payload_provider.get_payload("basic")[:3]  # Limit to 3 payloads
            
            for i, payload in enumerate(xss_payloads):
                test_name = f"{field}_xss_{i}"
                results["tests_run"].append(test_name)
                
                try:
                    test_request = base_request.copy()
                    test_request[field] = payload
                    
                    response = client.request(
                        method=method,
                        endpoint=endpoint,
                        json_data=test_request if method.upper() != "GET" else None,
                        params=test_request if method.upper() == "GET" else None
                    )
                    
                    # Check if XSS payload is reflected in response
                    is_reflected = payload in response.text
                    is_valid = response.status_code < 400
                    
                    results["test_results"][test_name] = {
                        "status_code": response.status_code,
                        "value_tested": payload,
                        "is_valid": is_valid,
                        "is_reflected": is_reflected
                    }
                    
                    if is_reflected:
                        results["vulnerabilities_found"].append({
                            "type": "xss",
                            "field": field,
                            "payload": payload,
                            "severity": "high",
                            "description": f"Field '{field}' is vulnerable to XSS - payload is reflected in response"
                        })
                    elif is_valid:
                        results["vulnerabilities_found"].append({
                            "type": "xss_possible",
                            "field": field,
                            "payload": payload,
                            "severity": "medium",
                            "description": f"Field '{field}' accepts XSS payload without validation"
                        })
                        
                except Exception as e:
                    results["test_results"][test_name] = {
                        "error": str(e)
                    }
        
        # 5. Test oversized inputs
        test_name = f"{field}_oversized"
        results["tests_run"].append(test_name)
        
        try:
            test_request = base_request.copy()
            
            # Generate oversized input based on field type
            if field_type == "string":
                max_length = specs.get("maxLength", 100)
                test_request[field] = "A" * (max_length * 10)  # 10x the max length
            elif field_type == "number":
                max_value = specs.get("maximum", 1000000)
                test_request[field] = max_value * 1000  # 1000x the max value
            elif field_type == "array":
                max_items = specs.get("maxItems", 100)
                test_request[field] = ["item"] * (max_items * 10)  # 10x the max items
            
            response = client.request(
                method=method,
                endpoint=endpoint,
                json_data=test_request if method.upper() != "GET" else None,
                params=test_request if method.upper() == "GET" else None
            )
            
            # Should not be valid
            is_valid = response.status_code < 400
            
            results["test_results"][test_name] = {
                "status_code": response.status_code,
                "value_tested": str(test_request[field])[:100] + "...",  # Truncate for readability
                "is_valid": is_valid,
                "should_be_valid": False
            }
            
            if is_valid:
                results["vulnerabilities_found"].append({
                    "type": "oversized_input",
                    "field": field,
                    "severity": "medium",
                    "description": f"Field '{field}' accepts oversized input without validation"
                })
                
        except Exception as e:
            results["test_results"][test_name] = {
                "error": str(e)
            }
    
    # Add summary
    results["vulnerability_count"] = len(results["vulnerabilities_found"])
    results["is_vulnerable"] = results["vulnerability_count"] > 0
    results["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate most severe issue
    severity_levels = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
    if results["vulnerabilities_found"]:
        highest_severity = max(vulnerability["severity"] for vulnerability in results["vulnerabilities_found"])
        results["highest_severity"] = highest_severity
    else:
        results["highest_severity"] = "none"
    
    return results


def test_rate_limiting(
    endpoint: str,
    requests_per_second: int,
    duration_seconds: int
) -> Dict[str, Any]:
    """
    Tests API rate limiting implementation
    
    Args:
        endpoint: API endpoint to test
        requests_per_second: Number of requests per second to send
        duration_seconds: Duration of the test in seconds
        
    Returns:
        Test results with rate limiting effectiveness
    """
    # Get settings and create client
    settings = get_test_settings()
    client = SecurityAPIClient(settings, api_key=settings.test_api_key)
    
    results = {
        "endpoint": endpoint,
        "requests_per_second": requests_per_second,
        "duration_seconds": duration_seconds,
        "timestamp_start": time.strftime("%Y-%m-%d %H:%M:%S"),
        "responses": {
            "total": 0,
            "success": 0,
            "rate_limited": 0,
            "error": 0
        },
        "rate_limit_headers": {}
    }
    
    # Calculate total number of requests
    total_requests = requests_per_second * duration_seconds
    
    # Track when rate limiting was first encountered
    rate_limit_detected_at = None
    
    # Track response times
    response_times = []
    
    # Store retry-after values
    retry_after_values = []
    
    # Execute the requests
    start_time = time.time()
    for i in range(total_requests):
        try:
            # Calculate target request time
            target_time = start_time + (i / requests_per_second)
            current_time = time.time()
            
            # Sleep if needed to maintain the request rate
            if current_time < target_time:
                time.sleep(target_time - current_time)
            
            # Make the request
            request_start = time.time()
            response = client.request(
                method="GET",
                endpoint=endpoint
            )
            request_time = time.time() - request_start
            response_times.append(request_time)
            
            # Increment counters
            results["responses"]["total"] += 1
            
            if response.status_code == 429:  # Too Many Requests
                results["responses"]["rate_limited"] += 1
                
                # Record when rate limiting was first detected
                if rate_limit_detected_at is None:
                    rate_limit_detected_at = i + 1  # Request number (1-based)
                
                # Check for rate limit headers
                rate_limit_headers = {}
                for header in response.headers:
                    if "rate" in header.lower() or "limit" in header.lower():
                        rate_limit_headers[header] = response.headers[header]
                
                if "retry-after" in response.headers:
                    retry_after = response.headers["retry-after"]
                    retry_after_values.append(retry_after)
                    
                if rate_limit_headers and not results["rate_limit_headers"]:
                    results["rate_limit_headers"] = rate_limit_headers
                    
            elif response.status_code >= 400:
                results["responses"]["error"] += 1
            else:
                results["responses"]["success"] += 1
                
        except Exception as e:
            logger.error(f"Error during rate limit testing (request {i+1}/{total_requests}): {str(e)}")
            results["responses"]["error"] += 1
    
    # Calculate statistics
    end_time = time.time()
    actual_duration = end_time - start_time
    actual_rps = results["responses"]["total"] / actual_duration if actual_duration > 0 else 0
    
    results["timestamp_end"] = time.strftime("%Y-%m-%d %H:%M:%S")
    results["actual_duration"] = actual_duration
    results["actual_requests_per_second"] = actual_rps
    
    if response_times:
        results["response_times"] = {
            "min": min(response_times),
            "max": max(response_times),
            "avg": sum(response_times) / len(response_times)
        }
    
    # Determine rate limit threshold
    if rate_limit_detected_at is not None:
        results["rate_limit_detected"] = True
        results["rate_limit_threshold"] = rate_limit_detected_at
        
        if retry_after_values:
            results["retry_after_values"] = retry_after_values
            results["retry_after_avg"] = sum(float(v) for v in retry_after_values) / len(retry_after_values)
    else:
        results["rate_limit_detected"] = False
    
    # Evaluate rate limiting effectiveness
    settings_threshold = settings.rate_limit_threshold if hasattr(settings, "rate_limit_threshold") else 60
    
    if results["rate_limit_detected"]:
        threshold_effectiveness = abs(rate_limit_detected_at - settings_threshold) / settings_threshold if settings_threshold > 0 else 1
        
        if threshold_effectiveness <= 0.1:  # Within 10% of expected
            results["effectiveness"] = "excellent"
        elif threshold_effectiveness <= 0.2:  # Within 20% of expected
            results["effectiveness"] = "good"
        elif threshold_effectiveness <= 0.5:  # Within 50% of expected
            results["effectiveness"] = "fair"
        else:
            results["effectiveness"] = "poor"
            
        results["issues"] = []
        
        # Check for issues with rate limiting implementation
        if not results["rate_limit_headers"]:
            results["issues"].append("No rate limit headers returned")
            
        if "retry-after" not in results.get("rate_limit_headers", {}):
            results["issues"].append("Retry-After header not provided")
            
        if results["responses"]["rate_limited"] == 0:
            results["issues"].append("No requests were rate limited despite high request rate")
    else:
        if settings_threshold < total_requests:
            results["effectiveness"] = "missing"
            results["issues"] = ["Rate limiting not implemented or threshold too high"]
        else:
            results["effectiveness"] = "not_tested"
            results["issues"] = [f"Rate limit threshold likely higher than {total_requests} requests"]
    
    return results


def scan_for_sensitive_data_exposure(
    endpoints: List[str],
    test_requests: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Scans API responses for sensitive data exposure
    
    Args:
        endpoints: List of API endpoints to scan
        test_requests: Optional list of test requests to use
        
    Returns:
        Scan results with potential sensitive data exposures
    """
    # Get settings and create client
    settings = get_test_settings()
    client = SecurityAPIClient(settings, api_key=settings.test_api_key)
    
    results = {
        "endpoints_scanned": endpoints,
        "vulnerabilities_found": [],
        "test_results": {}
    }
    
    # Define patterns for sensitive data
    sensitive_patterns = {
        "password": r"password[\"']?\s*:\s*[\"']?[^\"']+[\"']?",
        "secret": r"secret[\"']?\s*:\s*[\"']?[^\"']+[\"']?",
        "token": r"token[\"']?\s*:\s*[\"']?[^\"']+[\"']?",
        "api_key": r"api[_-]?key[\"']?\s*:\s*[\"']?[^\"']+[\"']?",
        "access_key": r"access[_-]?key[\"']?\s*:\s*[\"']?[^\"']+[\"']?",
        "credit_card": r"(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})",
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "ssn": r"[0-9]{3}-[0-9]{2}-[0-9]{4}",
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "jwt": r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+"
    }
    
    import re
    
    # Create default test requests if not provided
    if not test_requests:
        test_requests = [
            {"method": "GET", "params": None, "json_data": None},
            {"method": "GET", "params": {"verbose": "true"}, "json_data": None},
            {"method": "GET", "params": {"debug": "true"}, "json_data": None}
        ]
    
    # Scan each endpoint
    for endpoint in endpoints:
        endpoint_results = {
            "exposures": [],
            "tests": []
        }
        
        for test_request in test_requests:
            method = test_request.get("method", "GET")
            params = test_request.get("params")
            json_data = test_request.get("json_data")
            
            test_name = f"{method}_{hash(str(params))}_{hash(str(json_data))}"
            
            try:
                response = client.request(
                    method=method,
                    endpoint=endpoint,
                    params=params,
                    json_data=json_data
                )
                
                # Check for sensitive data in response
                exposures = []
                for pattern_name, pattern in sensitive_patterns.items():
                    matches = re.findall(pattern, response.text, re.IGNORECASE)
                    if matches:
                        # Truncate matches for readability
                        truncated_matches = [match[:50] + "..." if len(match) > 50 else match for match in matches[:5]]
                        
                        exposure = {
                            "pattern": pattern_name,
                            "matches": truncated_matches,
                            "count": len(matches)
                        }
                        exposures.append(exposure)
                        
                        # Add to global vulnerabilities if not already present
                        already_found = any(
                            v["endpoint"] == endpoint and v["pattern"] == pattern_name
                            for v in results["vulnerabilities_found"]
                        )
                        
                        if not already_found:
                            results["vulnerabilities_found"].append({
                                "type": "sensitive_data_exposure",
                                "endpoint": endpoint,
                                "method": method,
                                "pattern": pattern_name,
                                "severity": "high" if pattern_name in ["password", "secret", "token", "api_key", "credit_card", "ssn"] else "medium",
                                "description": f"Endpoint exposes sensitive data matching pattern: {pattern_name}"
                            })
                
                # Check for excessive data exposure
                response_size = len(response.text)
                if response_size > 10000:  # Arbitrary threshold
                    endpoint_results["exposures"].append({
                        "type": "excessive_data",
                        "size": response_size,
                        "description": "Response contains excessive data which may include sensitive information"
                    })
                
                # Record test result
                endpoint_results["tests"].append({
                    "test_name": test_name,
                    "status_code": response.status_code,
                    "exposures": exposures,
                    "response_size": response_size
                })
                
                # Add exposures to endpoint results
                for exposure in exposures:
                    if exposure not in endpoint_results["exposures"]:
                        endpoint_results["exposures"].append(exposure)
                        
            except Exception as e:
                endpoint_results["tests"].append({
                    "test_name": test_name,
                    "error": str(e)
                })
        
        # Add endpoint results
        results["test_results"][endpoint] = endpoint_results
    
    # Add summary
    results["vulnerability_count"] = len(results["vulnerabilities_found"])
    results["is_vulnerable"] = results["vulnerability_count"] > 0
    results["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate most severe issue
    severity_levels = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
    if results["vulnerabilities_found"]:
        highest_severity = max(vulnerability["severity"] for vulnerability in results["vulnerabilities_found"])
        results["highest_severity"] = highest_severity
    else:
        results["highest_severity"] = "none"
    
    return results


def verify_tls_configuration(target_url: str) -> Dict[str, Any]:
    """
    Verifies the TLS/SSL configuration of the API endpoint
    
    Args:
        target_url: URL to verify
        
    Returns:
        Verification results with TLS configuration details
    """
    results = {
        "target_url": target_url,
        "checks_performed": [],
        "vulnerabilities_found": [],
        "test_results": {}
    }
    
    # Check if target URL is HTTPS
    if not target_url.startswith("https://"):
        results["vulnerabilities_found"].append({
            "type": "insecure_protocol",
            "severity": "critical",
            "description": "Target URL does not use HTTPS"
        })
        
        results["test_results"]["protocol"] = {
            "protocol": "http",
            "secure": False
        }
        
        results["is_vulnerable"] = True
        return results
    
    # 1. Check TLS version using OpenSSL
    check_name = "tls_version"
    results["checks_performed"].append(check_name)
    
    try:
        host = target_url.split("://")[1].split("/")[0]
        port = 443  # Default HTTPS port
        
        if ":" in host:
            host, port_str = host.split(":")
            port = int(port_str)
        
        # Run OpenSSL command to check TLS version
        cmd = ["openssl", "s_client", "-connect", f"{host}:{port}", "-tls1_2", "-servername", host]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(timeout=10)
        output = stdout.decode("utf-8", errors="ignore")
        
        tls_version = None
        for line in output.splitlines():
            if "Protocol" in line:
                tls_version = line.split(":")[1].strip()
                break
        
        if tls_version:
            results["test_results"][check_name] = {
                "version": tls_version,
                "secure": tls_version in ["TLSv1.2", "TLSv1.3"]
            }
            
            if tls_version not in ["TLSv1.2", "TLSv1.3"]:
                results["vulnerabilities_found"].append({
                    "type": "outdated_tls",
                    "severity": "high",
                    "description": f"Outdated TLS version detected: {tls_version}"
                })
        else:
            results["test_results"][check_name] = {
                "error": "Could not determine TLS version",
                "output": output[:500]
            }
    except Exception as e:
        results["test_results"][check_name] = {
            "error": str(e)
        }
    
    # 2. Check cipher suites
    check_name = "cipher_suites"
    results["checks_performed"].append(check_name)
    
    try:
        # Run OpenSSL command to check cipher suites
        cmd = ["openssl", "s_client", "-connect", f"{host}:{port}", "-cipher", "ALL", "-servername", host]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(timeout=10)
        output = stdout.decode("utf-8", errors="ignore")
        
        cipher = None
        for line in output.splitlines():
            if "Cipher" in line and "New" not in line and "is" in line:
                cipher = line.split(":")[1].strip()
                break
        
        weak_ciphers = ["RC4", "DES", "NULL", "EXPORT", "ANON"]
        
        if cipher:
            is_weak = any(weak in cipher for weak in weak_ciphers)
            
            results["test_results"][check_name] = {
                "cipher": cipher,
                "secure": not is_weak
            }
            
            if is_weak:
                results["vulnerabilities_found"].append({
                    "type": "weak_cipher",
                    "severity": "high",
                    "description": f"Weak cipher suite detected: {cipher}"
                })
        else:
            results["test_results"][check_name] = {
                "error": "Could not determine cipher suite",
                "output": output[:500]
            }
    except Exception as e:
        results["test_results"][check_name] = {
            "error": str(e)
        }
    
    # 3. Check certificate validity
    check_name = "certificate"
    results["checks_performed"].append(check_name)
    
    try:
        # Run OpenSSL command to check certificate
        cmd = ["openssl", "s_client", "-connect", f"{host}:{port}", "-servername", host]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(timeout=10)
        output = stdout.decode("utf-8", errors="ignore")
        
        # Extract certificate information
        cert_section = False
        cert_info = []
        
        for line in output.splitlines():
            if "-----BEGIN CERTIFICATE-----" in line:
                cert_section = True
            elif "-----END CERTIFICATE-----" in line:
                cert_info.append(line)
                cert_section = False
            elif cert_section:
                cert_info.append(line)
        
        # Save certificate to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem") as cert_file:
            cert_file.write("\n".join(cert_info))
            cert_file.flush()
            
            # Get certificate details
            cmd = ["openssl", "x509", "-in", cert_file.name, "-text", "-noout"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(timeout=10)
            cert_details = stdout.decode("utf-8", errors="ignore")
            
            # Extract expiration date
            expiry = None
            issuer = None
            subject = None
            
            for line in cert_details.splitlines():
                if "Not After" in line:
                    expiry = line.split(":", 1)[1].strip()
                elif "Issuer:" in line:
                    issuer = line.split(":", 1)[1].strip()
                elif "Subject:" in line:
                    subject = line.split(":", 1)[1].strip()
            
            # Check expiration
            import datetime
            expired = False
            
            if expiry:
                try:
                    expiry_date = datetime.datetime.strptime(expiry, "%b %d %H:%M:%S %Y %Z")
                    now = datetime.datetime.now()
                    expired = expiry_date < now
                except ValueError:
                    # Could not parse date format
                    pass
            
            results["test_results"][check_name] = {
                "issuer": issuer,
                "subject": subject,
                "expiry": expiry,
                "expired": expired,
                "secure": not expired
            }
            
            if expired:
                results["vulnerabilities_found"].append({
                    "type": "expired_certificate",
                    "severity": "critical",
                    "description": f"Certificate has expired: {expiry}"
                })
    except Exception as e:
        results["test_results"][check_name] = {
            "error": str(e)
        }
    
    # 4. Check HSTS header
    check_name = "hsts"
    results["checks_performed"].append(check_name)
    
    try:
        # Make a direct request to check headers
        response = requests.get(target_url, timeout=10)
        
        hsts_header = response.headers.get("Strict-Transport-Security")
        
        if hsts_header:
            # Check for max-age and includeSubDomains
            has_max_age = "max-age=" in hsts_header
            has_include_subdomains = "includeSubDomains" in hsts_header
            
            # Extract max-age value
            max_age = 0
            if has_max_age:
                try:
                    max_age_part = next(part for part in hsts_header.split(";") if "max-age=" in part)
                    max_age = int(max_age_part.split("=")[1].strip())
                except (StopIteration, IndexError, ValueError):
                    pass
            
            results["test_results"][check_name] = {
                "header": hsts_header,
                "has_max_age": has_max_age,
                "max_age": max_age,
                "has_include_subdomains": has_include_subdomains,
                "secure": has_max_age and max_age >= 15768000  # 6 months
            }
            
            if not has_max_age or max_age < 15768000:
                results["vulnerabilities_found"].append({
                    "type": "insufficient_hsts",
                    "severity": "medium",
                    "description": f"HSTS header has insufficient max-age ({max_age})"
                })
        else:
            results["test_results"][check_name] = {
                "header": None,
                "secure": False
            }
            
            results["vulnerabilities_found"].append({
                "type": "missing_hsts",
                "severity": "medium",
                "description": "HSTS header is not set"
            })
    except Exception as e:
        results["test_results"][check_name] = {
            "error": str(e)
        }
    
    # Add summary
    results["vulnerability_count"] = len(results["vulnerabilities_found"])
    results["is_vulnerable"] = results["vulnerability_count"] > 0
    results["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate most severe issue
    severity_levels = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
    if results["vulnerabilities_found"]:
        highest_severity = max(vulnerability["severity"] for vulnerability in results["vulnerabilities_found"])
        results["highest_severity"] = highest_severity
    else:
        results["highest_severity"] = "none"
    
    return results


def run_dependency_scan(requirements_file: str) -> Dict[str, Any]:
    """
    Scans project dependencies for known vulnerabilities
    
    Args:
        requirements_file: Path to requirements file
        
    Returns:
        Scan results with vulnerable dependencies
    """
    # Get settings and scan configuration
    settings = get_test_settings()
    scan_config = settings.get_security_tool_config("dependency_scanner")
    
    results = {
        "requirements_file": requirements_file,
        "vulnerabilities_found": [],
        "test_results": {}
    }
    
    # Determine scanner to use
    scanner = scan_config.get("scanner", "safety")
    
    if scanner == "safety":
        # Use safety CLI (https://github.com/pyupio/safety)
        try:
            cmd = ["safety", "check", "-r", requirements_file, "--json"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(timeout=60)
            output = stdout.decode("utf-8", errors="ignore")
            
            # Parse JSON output
            try:
                scan_results = json.loads(output)
                
                # Process vulnerabilities
                vulnerabilities = []
                
                if isinstance(scan_results, dict) and "vulnerabilities" in scan_results:
                    # Newer safety format
                    for vuln in scan_results["vulnerabilities"]:
                        vulnerabilities.append({
                            "package": vuln.get("package_name"),
                            "installed_version": vuln.get("installed_version"),
                            "vulnerable_versions": vuln.get("vulnerable_spec"),
                            "advisory": vuln.get("advisory"),
                            "cvss_v3": vuln.get("cvss_v3"),
                            "severity": vuln.get("severity", "unknown")
                        })
                else:
                    # Legacy safety format (list of vulnerabilities)
                    for vuln in scan_results:
                        vulnerabilities.append({
                            "package": vuln[0],
                            "installed_version": vuln[2],
                            "vulnerable_versions": vuln[1],
                            "advisory": vuln[3],
                            "cvss_v3": None,
                            "severity": "unknown"
                        })
                
                # Map to standard severity levels if needed
                for vuln in vulnerabilities:
                    if vuln["severity"] == "unknown" and vuln["cvss_v3"]:
                        cvss = float(vuln["cvss_v3"])
                        if cvss >= 9.0:
                            vuln["severity"] = "critical"
                        elif cvss >= 7.0:
                            vuln["severity"] = "high"
                        elif cvss >= 4.0:
                            vuln["severity"] = "medium"
                        else:
                            vuln["severity"] = "low"
                
                # Add to results
                results["test_results"]["safety"] = {
                    "vulnerabilities": vulnerabilities,
                    "count": len(vulnerabilities)
                }
                
                # Add to vulnerabilities found
                for vuln in vulnerabilities:
                    results["vulnerabilities_found"].append({
                        "type": "vulnerable_dependency",
                        "package": vuln["package"],
                        "installed_version": vuln["installed_version"],
                        "advisory": vuln["advisory"],
                        "severity": vuln["severity"],
                        "description": f"Vulnerable dependency: {vuln['package']} {vuln['installed_version']}"
                    })
                    
            except json.JSONDecodeError:
                # Could not parse JSON output
                results["test_results"]["safety"] = {
                    "error": "Could not parse safety output",
                    "output": output[:500]
                }
        except Exception as e:
            results["test_results"]["safety"] = {
                "error": str(e)
            }
    
    # Add summary
    results["vulnerability_count"] = len(results["vulnerabilities_found"])
    results["is_vulnerable"] = results["vulnerability_count"] > 0
    results["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate most severe issue
    severity_levels = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0, "none": 0}
    if results["vulnerabilities_found"]:
        severities = [vulnerability["severity"] for vulnerability in results["vulnerabilities_found"]]
        # Convert to numeric values and find max
        severity_values = [severity_levels.get(s, 0) for s in severities]
        highest_value = max(severity_values)
        # Convert back to string
        highest_severity = next(k for k, v in severity_levels.items() if v == highest_value)
        results["highest_severity"] = highest_severity
    else:
        results["highest_severity"] = "none"
    
    return results


class SecurityAPIClient:
    """Extended API client with security testing capabilities"""
    
    def __init__(
        self, 
        settings: TestSettings, 
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        retry_count: Optional[int] = None
    ):
        """
        Initializes the security API client with test settings
        
        Args:
            settings: Test settings configuration
            api_key: Optional API key to use for requests (overrides settings key)
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts for failed requests
        """
        # Set base URL
        self._settings = settings
        self._base_url = settings.get_api_url()
        
        # Set API key
        self._api_key = api_key if api_key is not None else settings.test_api_key
        
        # Set default headers
        self._default_headers = {}
        if self._api_key:
            self._default_headers["X-API-Key"] = self._api_key
        self._default_headers["Content-Type"] = "application/json"
        
        # Set timeout and retry parameters
        self._timeout = timeout if timeout is not None else DEFAULT_REQUEST_TIMEOUT
        self._retry_count = retry_count if retry_count is not None else DEFAULT_RETRY_COUNT
        
        logger.info(f"Initialized security API client with base URL: {self._base_url}")
    
    def request_with_payload(
        self, 
        method: str, 
        endpoint: str, 
        payload_type: str,
        payload_name: str,
        target_param: str, 
        base_params: Optional[Dict[str, Any]] = None,
        base_json: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """
        Makes a request with a security test payload
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            payload_type: Type of payload (sql_injection, xss, etc.)
            payload_name: Specific payload name or category
            target_param: Parameter to inject the payload into
            base_params: Base query parameters
            base_json: Base JSON payload
            
        Returns:
            HTTP response object
        """
        # Get the appropriate payload
        payload = None
        if payload_type == "sql_injection":
            payload = SQLInjectionPayloads().get_payload(payload_name)
        elif payload_type == "xss":
            payload = XSSPayloads().get_payload(payload_name)
        elif payload_type == "auth_bypass":
            payload = AuthBypassPayloads().get_payload(payload_name)
        elif payload_type == "input_validation":
            payload = InputValidationPayloads().get_payload(target_param, payload_name)
        else:
            raise ValueError(f"Unknown payload type: {payload_type}")
        
        # Create copies of base parameters or empty dicts if None
        params = base_params.copy() if base_params else {}
        json_data = base_json.copy() if base_json else {}
        
        # Inject payload into the target parameter
        if method.upper() in ["GET", "DELETE"]:
            # Inject into query parameters for GET/DELETE
            params[target_param] = payload
        else:
            # Inject into JSON payload for POST/PUT
            json_data[target_param] = payload
        
        # Make the request
        logger.debug(f"Injecting {payload_type} payload into {target_param}: {payload}")
        response = self.request(
            method=method,
            endpoint=endpoint,
            params=params,
            json_data=json_data
        )
        
        logger.debug(f"Response status: {response.status_code}")
        return response
    
    def fuzz_parameter(
        self, 
        method: str, 
        endpoint: str, 
        param_name: str, 
        param_type: str, 
        base_request: Optional[Dict[str, Any]] = None,
        num_tests: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs fuzz testing on a specific parameter
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            param_name: Name of the parameter to fuzz
            param_type: Type of parameter (string, number, etc.)
            base_request: Base request payload to use
            num_tests: Number of test variations to generate
            
        Returns:
            List of test results with payloads and responses
        """
        # Determine appropriate payload generator based on param_type
        if param_type == "string":
            if param_name == "ticker":
                payloads = InputValidationPayloads().get_payload(param_name, "invalid_format")
                payloads += InputValidationPayloads().get_payload(param_name, "special_chars")
            elif param_name == "client_id":
                payloads = InputValidationPayloads().get_payload(param_name, "invalid_format")
                payloads += [InputValidationPayloads().get_payload(param_name, "too_long")]
            else:
                # Generic string fuzzing
                payloads = ["", "A" * 1000, "<script>alert(1)</script>", "1' OR '1'='1", "../../../etc/passwd"]
        elif param_type == "number":
            if param_name == "position_value":
                payload_values = InputValidationPayloads().generate_boundary_values(param_name)
                payloads = list(payload_values.values())
                payloads += InputValidationPayloads().get_payload(param_name, "invalid_values")
                payloads += InputValidationPayloads().get_payload(param_name, "invalid_format")
            elif param_name == "loan_days":
                payload_values = InputValidationPayloads().generate_boundary_values(param_name)
                payloads = list(payload_values.values())
                payloads += InputValidationPayloads().get_payload(param_name, "invalid_values")
                payloads += InputValidationPayloads().get_payload(param_name, "invalid_format")
            else:
                # Generic number fuzzing
                payloads = [0, -1, "0", "not_a_number", 1e100, float('inf')]
        else:
            # Default payloads for unknown types
            payloads = ["", None, {}, [], 0, True, False, "null"]
        
        # Limit the number of tests if specified
        if num_tests and len(payloads) > num_tests:
            payloads = payloads[:num_tests]
        
        results = []
        base = base_request or {}
        
        # Run each test case
        for payload in payloads:
            # Create test request
            test_request = base.copy()
            
            # Determine whether to use query params or JSON body
            if method.upper() in ["GET", "DELETE"]:
                params = {param_name: payload}
                json_data = None
            else:
                params = None
                test_request[param_name] = payload
                json_data = test_request
            
            # Send the request
            try:
                response = self.request(
                    method=method,
                    endpoint=endpoint,
                    params=params,
                    json_data=json_data
                )
                
                # Analyze the response for issues
                issues = []
                if response.status_code >= 500:
                    issues.append("Server error (500) - possible crash or unhandled exception")
                    
                try:
                    response_json = response.json()
                    if "error" in response_json and "stack" in response_json["error"]:
                        issues.append("Stack trace exposed in error response")
                        
                    # Check for data leakage in error messages
                    error_msg = response_json.get("error", {}).get("message", "")
                    if "SQL" in error_msg or "syntax" in error_msg:
                        issues.append("Possible SQL error message exposed")
                        
                except (json.JSONDecodeError, ValueError, AttributeError):
                    # Non-JSON response is not necessarily an issue
                    pass
                
                # Record the test result
                result = {
                    "parameter": param_name,
                    "payload": payload,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "issues": issues,
                    "response_preview": response.text[:200] if response.text else ""
                }
                results.append(result)
                
            except Exception as e:
                # Record the error as a result
                result = {
                    "parameter": param_name,
                    "payload": payload,
                    "status_code": None,
                    "response_time": None,
                    "issues": [f"Request failed: {str(e)}"],
                    "response_preview": None
                }
                results.append(result)
        
        return results
    
    def test_csrf_protection(
        self, 
        endpoint: str, 
        valid_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Tests CSRF protection on state-changing endpoints
        
        Args:
            endpoint: API endpoint path
            valid_request: Valid request payload that would normally succeed
            
        Returns:
            Test results with CSRF protection status
        """
        results = {
            "endpoint": endpoint,
            "tests": [],
            "csrf_protection": "unknown"
        }
        
        # 1. Make a legitimate request to get CSRF token if implemented
        try:
            # First, check for a GET request to get a CSRF token
            get_response = self.request(
                method="GET",
                endpoint=endpoint
            )
            
            csrf_token = None
            # Look for CSRF token in response headers
            for header in get_response.headers:
                if "csrf" in header.lower():
                    csrf_token = get_response.headers[header]
                    break
                    
            # If not in headers, look in response body
            if not csrf_token and get_response.headers.get("content-type", "").startswith("application/json"):
                try:
                    response_json = get_response.json()
                    for key in response_json:
                        if "csrf" in key.lower() or "token" in key.lower():
                            csrf_token = response_json[key]
                            break
                except (json.JSONDecodeError, ValueError, AttributeError):
                    pass
            
            # Record the result
            results["tests"].append({
                "name": "csrf_token_retrieval",
                "success": csrf_token is not None,
                "token_found": csrf_token is not None,
                "status_code": get_response.status_code
            })
            
        except Exception as e:
            results["tests"].append({
                "name": "csrf_token_retrieval",
                "success": False,
                "error": str(e)
            })
            csrf_token = None
        
        # 2. Make a request without CSRF token
        try:
            no_token_headers = self._default_headers.copy()
            no_token_response = self.request(
                method="POST",
                endpoint=endpoint,
                json_data=valid_request,
                headers=no_token_headers
            )
            
            results["tests"].append({
                "name": "request_without_token",
                "success": True,
                "status_code": no_token_response.status_code,
                "blocked": no_token_response.status_code in [403, 401, 400]
            })
            
            if no_token_response.status_code < 400:
                # If successful without token, likely no CSRF protection
                results["csrf_protection"] = "not_implemented"
                
        except Exception as e:
            results["tests"].append({
                "name": "request_without_token",
                "success": False,
                "error": str(e)
            })
        
        # 3. If we found a token, try with an invalid token
        if csrf_token:
            try:
                invalid_token_headers = self._default_headers.copy()
                # Use the header name we found or a common one
                csrf_header = next((h for h in get_response.headers if "csrf" in h.lower()), "X-CSRF-Token")
                invalid_token_headers[csrf_header] = "invalid_token_value"
                
                invalid_token_response = self.request(
                    method="POST",
                    endpoint=endpoint,
                    json_data=valid_request,
                    headers=invalid_token_headers
                )
                
                results["tests"].append({
                    "name": "request_with_invalid_token",
                    "success": True,
                    "status_code": invalid_token_response.status_code,
                    "blocked": invalid_token_response.status_code in [403, 401, 400]
                })
                
                # If blocked with invalid token but allowed with valid token
                # then CSRF protection is likely implemented
                if invalid_token_response.status_code in [403, 401, 400]:
                    results["csrf_protection"] = "implemented"
                    
            except Exception as e:
                results["tests"].append({
                    "name": "request_with_invalid_token",
                    "success": False,
                    "error": str(e)
                })
        
        # 4. Make a request with the valid token if we found one
        if csrf_token:
            try:
                valid_token_headers = self._default_headers.copy()
                csrf_header = next((h for h in get_response.headers if "csrf" in h.lower()), "X-CSRF-Token")
                valid_token_headers[csrf_header] = csrf_token
                
                valid_token_response = self.request(
                    method="POST",
                    endpoint=endpoint,
                    json_data=valid_request,
                    headers=valid_token_headers
                )
                
                results["tests"].append({
                    "name": "request_with_valid_token",
                    "success": True,
                    "status_code": valid_token_response.status_code,
                    "accepted": valid_token_response.status_code < 400
                })
                
                # If accepted with valid token but blocked with invalid token
                # then CSRF protection is confirmed
                if (valid_token_response.status_code < 400 and 
                    results["tests"][-2]["status_code"] in [403, 401, 400]):
                    results["csrf_protection"] = "implemented"
                    
            except Exception as e:
                results["tests"].append({
                    "name": "request_with_valid_token",
                    "success": False,
                    "error": str(e)
                })
        
        # Final determination
        if results["csrf_protection"] == "unknown":
            # If we couldn't definitively determine, check patterns
            if any(t["name"] == "request_without_token" and t["status_code"] < 400 for t in results["tests"]):
                results["csrf_protection"] = "not_implemented"
            else:
                # Default to inconclusive
                results["csrf_protection"] = "inconclusive"
        
        return results
    
    def scan_endpoint(
        self, 
        endpoint: str, 
        method: str, 
        valid_request: Dict[str, Any],
        test_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Performs a comprehensive security scan on a specific endpoint
        
        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            valid_request: Valid request payload that would normally succeed
            test_types: Optional list of test types to run (defaults to all)
            
        Returns:
            Comprehensive scan results
        """
        # Initialize results
        results = {
            "endpoint": endpoint,
            "method": method,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tests_run": [],
            "issues_found": [],
            "test_results": {}
        }
        
        # Determine which tests to run
        available_tests = [
            "authentication", 
            "authorization", 
            "input_validation",
            "injection",
            "csrf",
            "rate_limiting",
            "sensitive_data"
        ]
        
        tests_to_run = test_types if test_types else available_tests
        
        # Run selected tests
        for test_type in tests_to_run:
            results["tests_run"].append(test_type)
            
            try:
                if test_type == "authentication":
                    # Test with no auth, invalid auth
                    invalid_client = SecurityAPIClient(self._settings, api_key="invalid_key")
                    auth_response = invalid_client.request(
                        method=method,
                        endpoint=endpoint,
                        json_data=valid_request if method.upper() != "GET" else None
                    )
                    
                    # Check if authentication is properly enforced
                    auth_results = {
                        "status_code": auth_response.status_code,
                        "auth_enforced": auth_response.status_code in [401, 403],
                        "issues": []
                    }
                    
                    if auth_response.status_code not in [401, 403]:
                        auth_results["issues"].append("Endpoint accessible without valid authentication")
                        results["issues_found"].append({
                            "test_type": "authentication",
                            "severity": "high",
                            "description": "Endpoint accessible without valid authentication"
                        })
                    
                    results["test_results"]["authentication"] = auth_results
                
                elif test_type == "input_validation":
                    # Test input validation for each parameter
                    validation_results = {"parameters": {}}
                    
                    for param_name, param_value in valid_request.items():
                        # Determine parameter type
                        if isinstance(param_value, str):
                            param_type = "string"
                        elif isinstance(param_value, (int, float)):
                            param_type = "number"
                        else:
                            param_type = "other"
                        
                        # Fuzz the parameter
                        fuzz_results = self.fuzz_parameter(
                            method=method,
                            endpoint=endpoint,
                            param_name=param_name,
                            param_type=param_type,
                            base_request=valid_request,
                            num_tests=5  # Limit to 5 tests per parameter for comprehensive scan
                        )
                        
                        # Analyze results
                        issues = []
                        for result in fuzz_results:
                            issues.extend(result.get("issues", []))
                        
                        validation_results["parameters"][param_name] = {
                            "issues_count": len(issues),
                            "issues": issues[:5]  # Limit to top 5 issues
                        }
                        
                        # Add significant issues to the main issues list
                        for issue in issues:
                            if "500" in issue or "crash" in issue or "SQL" in issue:
                                results["issues_found"].append({
                                    "test_type": "input_validation",
                                    "parameter": param_name,
                                    "severity": "high" if "500" in issue or "crash" in issue else "medium",
                                    "description": issue
                                })
                    
                    results["test_results"]["input_validation"] = validation_results
                
                elif test_type == "injection":
                    # Test SQL injection and XSS for string parameters
                    injection_results = {"sql": {}, "xss": {}}
                    
                    for param_name, param_value in valid_request.items():
                        if isinstance(param_value, str):
                            # SQL injection test
                            sql_response = self.request_with_payload(
                                method=method,
                                endpoint=endpoint,
                                payload_type="sql_injection",
                                payload_name="basic",
                                target_param=param_name,
                                base_json=valid_request if method.upper() != "GET" else None
                            )
                            
                            sql_issues = []
                            if sql_response.status_code >= 500:
                                sql_issues.append("Server error triggered by SQL injection payload")
                            
                            try:
                                resp_body = sql_response.json() if sql_response.text else {}
                                error_msg = resp_body.get("error", {}).get("message", "")
                                if "SQL" in error_msg or "syntax" in error_msg:
                                    sql_issues.append("SQL error message exposed in response")
                            except (json.JSONDecodeError, ValueError, AttributeError):
                                pass
                            
                            injection_results["sql"][param_name] = {
                                "status_code": sql_response.status_code,
                                "issues": sql_issues
                            }
                            
                            if sql_issues:
                                results["issues_found"].append({
                                    "test_type": "injection",
                                    "injection_type": "sql",
                                    "parameter": param_name,
                                    "severity": "high",
                                    "description": sql_issues[0]
                                })
                            
                            # XSS test
                            xss_response = self.request_with_payload(
                                method=method,
                                endpoint=endpoint,
                                payload_type="xss",
                                payload_name="basic",
                                target_param=param_name,
                                base_json=valid_request if method.upper() != "GET" else None
                            )
                            
                            xss_issues = []
                            if xss_response.status_code < 400:
                                # Check if XSS payload is reflected in response
                                xss_payload = XSSPayloads().get_random_payload("basic")
                                if xss_payload in xss_response.text:
                                    xss_issues.append("XSS payload reflected in response")
                            
                            injection_results["xss"][param_name] = {
                                "status_code": xss_response.status_code,
                                "issues": xss_issues
                            }
                            
                            if xss_issues:
                                results["issues_found"].append({
                                    "test_type": "injection",
                                    "injection_type": "xss",
                                    "parameter": param_name,
                                    "severity": "high",
                                    "description": xss_issues[0]
                                })
                    
                    results["test_results"]["injection"] = injection_results
                
                elif test_type == "csrf":
                    # Only test CSRF for state-changing methods
                    if method.upper() in ["POST", "PUT", "DELETE", "PATCH"]:
                        csrf_results = self.test_csrf_protection(endpoint, valid_request)
                        
                        if csrf_results["csrf_protection"] == "not_implemented":
                            results["issues_found"].append({
                                "test_type": "csrf",
                                "severity": "medium",
                                "description": "CSRF protection not implemented for state-changing endpoint"
                            })
                        
                        results["test_results"]["csrf"] = csrf_results
                
                elif test_type == "sensitive_data":
                    # Make a normal request and check for sensitive data in response
                    response = self.request(
                        method=method,
                        endpoint=endpoint,
                        json_data=valid_request if method.upper() != "GET" else None
                    )
                    
                    sensitive_patterns = [
                        r"password", r"secret", r"token", r"key", r"auth", 
                        r"credit.*card", r"card.*number", r"ssn", r"social.*security",
                        r"account.*number", r"routing.*number", r"address", r"email"
                    ]
                    
                    issues = []
                    for pattern in sensitive_patterns:
                        import re
                        if re.search(pattern, response.text, re.IGNORECASE):
                            issues.append(f"Possible sensitive data exposure: {pattern}")
                    
                    results["test_results"]["sensitive_data"] = {
                        "status_code": response.status_code,
                        "issues": issues
                    }
                    
                    for issue in issues:
                        results["issues_found"].append({
                            "test_type": "sensitive_data",
                            "severity": "high",
                            "description": issue
                        })
            
            except Exception as e:
                # Log exception but continue with other tests
                logger.error(f"Error running {test_type} test: {str(e)}")
                results["test_results"][test_type] = {
                    "error": str(e)
                }
        
        # Add overall summary
        results["issues_count"] = len(results["issues_found"])
        results["scan_duration"] = time.time() - time.mktime(time.strptime(results["timestamp"], "%Y-%m-%d %H:%M:%S"))
        
        severities = [issue["severity"] for issue in results["issues_found"]]
        results["highest_severity"] = max(severities) if severities else "none"
        
        return results
    
    def request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None, 
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None, 
        timeout: Optional[int] = None,
        retry_count: Optional[int] = None
    ) -> requests.Response:
        """
        Makes a generic HTTP request with security-focused logging
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON payload for POST/PUT requests
            headers: Additional HTTP headers
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts for failed requests
            
        Returns:
            HTTP response object
        """
        # Combine default headers with any provided headers
        request_headers = self._default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        # Build full URL
        url = f"{self._base_url}{endpoint}"
        
        # Set retry count and timeout
        retries = retry_count if retry_count is not None else self._retry_count
        req_timeout = timeout if timeout is not None else self._timeout
        
        logger.debug(f"Security test request: {method} {url}")
        if params:
            logger.debug(f"Request params: {params}")
        if json_data:
            logger.debug(f"Request payload: {json_data}")
        
        # Initialize attempts counter
        attempts = 0
        
        # Retry loop
        while True:
            attempts += 1
            
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=request_headers,
                    timeout=req_timeout,
                    allow_redirects=False  # Disable automatic redirects for security testing
                )
                
                # Log security-relevant headers
                security_headers = {
                    h: response.headers.get(h) for h in [
                        "X-Content-Type-Options", "X-Frame-Options", "Content-Security-Policy",
                        "Strict-Transport-Security", "X-XSS-Protection"
                    ] if h in response.headers
                }
                
                if security_headers:
                    logger.debug(f"Security headers: {security_headers}")
                else:
                    logger.debug("No security headers found in response")
                
                # Request succeeded, break out of retry loop
                break
                
            except requests.Timeout:
                logger.warning(f"Request timeout (attempt {attempts}/{retries+1}): {url}")
                if attempts <= retries:
                    time.sleep(1)  # Wait before retry
                    continue
                else:
                    logger.error(f"Max retries ({retries}) reached. Request timed out: {url}")
                    raise
                    
            except (requests.RequestException, ConnectionError) as e:
                logger.warning(f"Request error (attempt {attempts}/{retries+1}): {str(e)}")
                if attempts <= retries:
                    time.sleep(1)  # Wait before retry
                    continue
                else:
                    logger.error(f"Max retries ({retries}) reached. Request failed: {str(e)}")
                    raise
        
        # Log response status and size
        logger.debug(f"Response status: {response.status_code}, size: {len(response.content)} bytes")
        
        return response


class ZAPScanner:
    """Wrapper for OWASP ZAP API for automated security scanning"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the ZAP scanner with configuration
        
        Args:
            config: Configuration for ZAP scanner
        """
        self._config = config
        self._zap = None
        self._initialized = False
        logger.info("ZAP Scanner initialized with configuration")
    
    def initialize(self) -> bool:
        """
        Initializes the connection to ZAP API
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True
        
        try:
            # Import ZAP API client
            try:
                from zapv2 import ZAPv2 as zap
            except ImportError:
                logger.error("ZAP API client not available. Install python-owasp-zap-v2.4 package.")
                return False
            
            # Get ZAP API URL and credentials from config
            api_url = self._config.get("api_url", "http://localhost:8080")
            api_key = self._config.get("api_key", "")
            
            # Create ZAP API client
            self._zap = zap(apikey=api_key, proxies={"http": api_url, "https": api_url})
            
            # Test connection by getting ZAP version
            version = self._zap.core.version
            logger.info(f"Connected to ZAP API, version: {version}")
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ZAP scanner: {str(e)}")
            return False
    
    def start_scan(self, target_url: str, scan_options: Optional[Dict[str, Any]] = None) -> str:
        """
        Starts a security scan using ZAP
        
        Args:
            target_url: URL to scan
            scan_options: Optional scan configuration options
            
        Returns:
            Scan ID for tracking the scan
            
        Raises:
            RuntimeError: If ZAP scanner is not initialized
        """
        if not self._initialized and not self.initialize():
            raise RuntimeError("ZAP scanner not initialized")
        
        # Set up scan options by combining defaults with provided options
        options = {
            "contextName": self._config.get("context_name", "default_context"),
            "recurse": True,
            "inScopeOnly": True,
            "scanPolicyName": self._config.get("scan_policy", "Default Policy"),
            "method": "GET",
            "postData": "",
            "attack_mode": self._config.get("attack_mode", "STANDARD"),
            "max_children": self._config.get("max_children", 0)
        }
        
        if scan_options:
            options.update(scan_options)
        
        try:
            # Create a new context if needed
            context_name = options["contextName"]
            if context_name not in self._zap.context.context_list:
                self._zap.context.new_context(context_name)
            
            # Set include and exclude URLs for the context
            for include_regex in self._config.get("include_urls", [target_url]):
                self._zap.context.include_in_context(context_name, include_regex)
                
            for exclude_regex in self._config.get("exclude_urls", []):
                self._zap.context.exclude_from_context(context_name, exclude_regex)
            
            # Spider the target first if enabled
            spider_options = scan_options.get("spider", {})
            if spider_options.get("enabled", True):
                logger.info(f"Starting spider scan for {target_url}")
                spider_id = self._zap.spider.scan(
                    url=target_url,
                    maxchildren=options["max_children"],
                    recurse=options["recurse"],
                    contextname=context_name
                )
                
                # Wait for spider to complete
                max_spider_wait = spider_options.get("timeout", 300)  # 5 minutes default
                self._zap.spider.wait_for_scan_completion(scanid=spider_id, timeout=max_spider_wait)
                logger.info("Spider scan completed")
            
            # Run AJAX Spider if enabled
            ajax_options = scan_options.get("ajax_spider", {})
            if ajax_options.get("enabled", self._config.get("ajax_spider", False)):
                logger.info(f"Starting AJAX spider scan for {target_url}")
                self._zap.ajaxSpider.scan(url=target_url, inScope=options["inScopeOnly"])
                
                # Wait for AJAX spider to complete
                max_ajax_wait = ajax_options.get("timeout", 300)  # 5 minutes default
                self._zap.ajaxSpider.wait_until_not_running(max_ajax_wait * 1000)  # Convert to ms
                logger.info("AJAX spider scan completed")
            
            # Run passive scan
            logger.info("Waiting for passive scan to complete")
            passive_wait = self._config.get("passive_scan_wait_time", 1000)
            time.sleep(passive_wait / 1000)  # Convert ms to seconds
            
            # Start the active scan
            logger.info(f"Starting active scan for {target_url}")
            scan_id = self._zap.ascan.scan(
                url=target_url,
                scanpolicyname=options["scanPolicyName"],
                method=options["method"],
                postdata=options["postData"],
                contextid=self._zap.context.context_id(context_name)
            )
            
            logger.info(f"Active scan started with ID: {scan_id}")
            return scan_id
            
        except Exception as e:
            logger.error(f"Error starting ZAP scan: {str(e)}")
            raise
    
    def get_scan_status(self, scan_id: str) -> Dict[str, Any]:
        """
        Gets the current status of a running scan
        
        Args:
            scan_id: Scan ID for tracking the scan
            
        Returns:
            Scan status information
            
        Raises:
            RuntimeError: If ZAP scanner is not initialized
        """
        if not self._initialized and not self.initialize():
            raise RuntimeError("ZAP scanner not initialized")
        
        try:
            status = self._zap.ascan.status(scan_id)
            progress = self._zap.ascan.scan_progress(scan_id)
            
            return {
                "scan_id": scan_id,
                "status": status,
                "progress": progress,
                "is_running": int(progress) < 100,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            logger.error(f"Error getting scan status: {str(e)}")
            return {
                "scan_id": scan_id,
                "status": "error",
                "error": str(e),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def get_scan_results(self, scan_id: str) -> Dict[str, Any]:
        """
        Gets the results of a completed scan
        
        Args:
            scan_id: Scan ID for tracking the scan
            
        Returns:
            Scan results with vulnerabilities found
            
        Raises:
            RuntimeError: If ZAP scanner is not initialized
        """
        if not self._initialized and not self.initialize():
            raise RuntimeError("ZAP scanner not initialized")
        
        try:
            # Get alerts from ZAP
            alerts = self._zap.core.alerts()
            
            # Process and categorize alerts
            results = {
                "scan_id": scan_id,
                "scan_status": self._zap.ascan.status(scan_id),
                "alert_count": len(alerts),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "alerts_by_risk": {
                    "high": [],
                    "medium": [],
                    "low": [],
                    "informational": []
                },
                "alerts_by_type": {}
            }
            
            for alert in alerts:
                risk = alert.get("risk", "").lower()
                alert_type = alert.get("name", "Unknown")
                
                # Add alert to risk category
                if risk in results["alerts_by_risk"]:
                    results["alerts_by_risk"][risk].append(alert)
                else:
                    results["alerts_by_risk"]["informational"].append(alert)
                
                # Add alert to type category
                if alert_type not in results["alerts_by_type"]:
                    results["alerts_by_type"][alert_type] = []
                    
                results["alerts_by_type"][alert_type].append(alert)
            
            # Add summary statistics
            results["summary"] = {
                "high_risk_count": len(results["alerts_by_risk"]["high"]),
                "medium_risk_count": len(results["alerts_by_risk"]["medium"]),
                "low_risk_count": len(results["alerts_by_risk"]["low"]),
                "info_count": len(results["alerts_by_risk"]["informational"]),
                "unique_alert_types": len(results["alerts_by_type"])
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting scan results: {str(e)}")
            return {
                "scan_id": scan_id,
                "scan_status": "error",
                "error": str(e),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def wait_for_scan_completion(
        self, 
        scan_id: str, 
        timeout: int = 3600,
        check_interval: int = 10
    ) -> bool:
        """
        Waits for a scan to complete or timeout
        
        Args:
            scan_id: Scan ID for tracking the scan
            timeout: Maximum time to wait in seconds (default: 1 hour)
            check_interval: How often to check status in seconds
            
        Returns:
            True if scan completed, False if timed out
            
        Raises:
            RuntimeError: If ZAP scanner is not initialized
        """
        if not self._initialized and not self.initialize():
            raise RuntimeError("ZAP scanner not initialized")
        
        start_time = time.time()
        end_time = start_time + timeout
        
        logger.info(f"Waiting for scan {scan_id} to complete (timeout: {timeout}s)")
        
        while time.time() < end_time:
            status = self.get_scan_status(scan_id)
            progress = int(status["progress"]) if "progress" in status else 0
            
            if progress >= 100:
                logger.info(f"Scan {scan_id} completed in {time.time() - start_time:.2f} seconds")
                return True
            
            logger.debug(f"Scan {scan_id} progress: {progress}%")
            time.sleep(check_interval)
        
        logger.warning(f"Scan {scan_id} timed out after {timeout} seconds")
        return False


class JWTAnalyzer:
    """Utility for analyzing and testing JWT tokens"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the JWT analyzer with configuration
        
        Args:
            config: Optional configuration for JWT analyzer
        """
        # Get configuration from settings if not provided
        self._config = config or {}
        if not config:
            try:
                self._config = get_test_settings().get_security_tool_config("jwt_analyzer")
            except (ValueError, AttributeError):
                # Use defaults if not available in settings
                self._config = {
                    "check_signature": True,
                    "check_expiry": True,
                    "check_weak_keys": True,
                    "check_claims": ["sub", "iss", "exp"],
                    "allowed_algorithms": ["HS256", "HS384", "HS512", "RS256"],
                    "disallowed_algorithms": ["none", "HS1"]
                }
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decodes a JWT token without verification
        
        Args:
            token: JWT token to decode
            
        Returns:
            Decoded token payload
        """
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            return decoded
        except jwt.PyJWTError as e:
            logger.error(f"Error decoding JWT token: {str(e)}")
            return {"error": str(e)}
    
    def generate_tampered_token(
        self, 
        original_token: str, 
        tampering_type: str,
        tampering_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generates a tampered JWT token for testing
        
        Args:
            original_token: Original JWT token to tamper with
            tampering_type: Type of tampering to apply
            tampering_params: Optional parameters for tampering
            
        Returns:
            Tampered JWT token
        """
        params = tampering_params or {}
        
        try:
            # Decode the token without verification
            decoded_payload = jwt.decode(original_token, options={"verify_signature": False})
            
            # Get the header
            header_segment = original_token.split('.')[0]
            header = json.loads(base64.b64decode(header_segment + '==').decode('utf-8'))
            
            if tampering_type == "alg_none":
                # Change algorithm to 'none'
                header['alg'] = 'none'
                # Re-encode the token without signature
                segments = [
                    base64.urlsafe_b64encode(json.dumps(header).encode()).decode().replace('=', ''),
                    base64.urlsafe_b64encode(json.dumps(decoded_payload).encode()).decode().replace('=', '')
                ]
                return '.'.join(segments) + '.'
            
            elif tampering_type == "alg_change":
                # Change algorithm to a weaker one
                new_alg = params.get("new_alg", "HS256")
                header['alg'] = new_alg
                # Re-encode with a weak secret
                weak_secret = params.get("weak_secret", "0000000000000000")
                return jwt.encode(decoded_payload, weak_secret, algorithm=new_alg)
            
            elif tampering_type == "exp_extend":
                # Extend expiration time
                if 'exp' in decoded_payload:
                    extension_seconds = params.get("extension_seconds", 31536000)  # Default: 1 year
                    decoded_payload['exp'] = int(time.time()) + extension_seconds
                return jwt.encode(decoded_payload, params.get("secret", "tampered_secret"), algorithm=header.get('alg', 'HS256'))
            
            elif tampering_type == "role_escalation":
                # Modify role or permissions claim
                role_claim = params.get("role_claim", "role")
                new_role = params.get("new_role", "admin")
                
                if role_claim in decoded_payload:
                    decoded_payload[role_claim] = new_role
                elif "permissions" in decoded_payload:
                    decoded_payload["permissions"] = params.get("new_permissions", ["admin", "read", "write", "delete"])
                elif "scope" in decoded_payload:
                    decoded_payload["scope"] = params.get("new_scope", "admin read write delete")
                else:
                    # Add a role claim if none exists
                    decoded_payload[role_claim] = new_role
                
                return jwt.encode(decoded_payload, params.get("secret", "tampered_secret"), algorithm=header.get('alg', 'HS256'))
            
            elif tampering_type == "signature_strip":
                # Strip signature part
                parts = original_token.split('.')
                if len(parts) >= 2:
                    return '.'.join(parts[:2]) + '.'
                return original_token
            
            else:
                # Invalid tampering type, return original token
                logger.warning(f"Unknown tampering type: {tampering_type}")
                return original_token
        
        except Exception as e:
            logger.error(f"Error generating tampered token: {str(e)}")
            return original_token
    
    def test_token_vulnerabilities(
        self, 
        endpoint: str, 
        valid_token: str, 
        client: SecurityAPIClient
    ) -> Dict[str, Any]:
        """
        Tests JWT implementation for common vulnerabilities
        
        Args:
            endpoint: API endpoint to test
            valid_token: Valid JWT token to test with
            client: SecurityAPIClient instance for making requests
            
        Returns:
            Test results with vulnerabilities found
        """
        results = {
            "endpoint": endpoint,
            "tests_run": [],
            "vulnerabilities_found": [],
            "test_results": {}
        }
        
        # Generate various tampered tokens for testing
        tampered_tokens = {
            "alg_none": self.generate_tampered_token(valid_token, "alg_none"),
            "alg_weak": self.generate_tampered_token(valid_token, "alg_change", {"new_alg": "HS256", "weak_secret": "weak"}),
            "exp_extended": self.generate_tampered_token(valid_token, "exp_extend"),
            "role_escalation": self.generate_tampered_token(valid_token, "role_escalation"),
            "signature_stripped": self.generate_tampered_token(valid_token, "signature_strip")
        }
        
        # Test each tampered token
        for tampering_type, token in tampered_tokens.items():
            results["tests_run"].append(tampering_type)
            
            try:
                # Use the tampered token in a request
                headers = {"Authorization": f"Bearer {token}"}
                response = client.request(
                    method="GET",
                    endpoint=endpoint,
                    headers=headers
                )
                
                # Check if the token was accepted
                accepted = response.status_code < 400
                
                results["test_results"][tampering_type] = {
                    "status_code": response.status_code,
                    "accepted": accepted
                }
                
                # If accepted, this is a vulnerability
                if accepted:
                    results["vulnerabilities_found"].append({
                        "type": tampering_type,
                        "severity": "high",
                        "description": f"JWT token with {tampering_type} accepted by the server"
                    })
            
            except Exception as e:
                results["test_results"][tampering_type] = {
                    "error": str(e)
                }
        
        # Summarize results
        results["vulnerability_count"] = len(results["vulnerabilities_found"])
        results["is_vulnerable"] = results["vulnerability_count"] > 0
        
        # Analyze vulnerabilities for specific issues
        if results["test_results"].get("alg_none", {}).get("accepted", False):
            results["none_algorithm_vulnerability"] = True
        
        if results["test_results"].get("signature_stripped", {}).get("accepted", False):
            results["signature_verification_vulnerability"] = True
        
        if results["test_results"].get("exp_extended", {}).get("accepted", False):
            results["expiration_validation_vulnerability"] = True
        
        if results["test_results"].get("role_escalation", {}).get("accepted", False):
            results["role_validation_vulnerability"] = True
        
        return results