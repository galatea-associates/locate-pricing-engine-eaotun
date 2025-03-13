"""
Initialization module for the security tests package that provides a centralized
access point for security testing components. This module imports and exposes key 
classes, functions, and configurations from the security tests submodules to 
simplify imports in security test files.
"""

# Import configuration classes and functions
from .config.settings import (
    TestEnvironment, 
    TestSettings,
    SecurityToolsConfig, 
    TestPayloadsConfig,
    get_test_settings,
    load_test_env
)

# Import security tools
from .helpers.security_tools import (
    ZAPSecurityScanner,
    JWTAnalyzer,
    APIFuzzer,  
    SecurityScanner
)

# Import payload generators
from .helpers.payloads import (
    SQLInjectionPayloads,
    XSSPayloads,
    AuthBypassPayloads,
    InputValidationPayloads
)

# Pre-initialize settings for convenience
settings = get_test_settings()

# Define all exports
__all__ = [
    "TestEnvironment", "TestSettings", "SecurityToolsConfig", "TestPayloadsConfig", 
    "get_test_settings", "load_test_env", "settings",
    "ZAPSecurityScanner", "JWTAnalyzer", "APIFuzzer", "SecurityScanner",
    "SQLInjectionPayloads", "XSSPayloads", "AuthBypassPayloads", "InputValidationPayloads",
    "get_zap_client", "run_zap_spider", "run_zap_active_scan", "analyze_jwt_token",
    "fuzz_endpoint", "test_rate_limiting", "scan_for_information_disclosure", 
    "test_cors_configuration", "generate_security_report", "get_payload",
    "generate_random_payload", "customize_payload", "generate_payload_variations",
    "create_malformed_request"
]

# Helper functions for common security operations
def get_zap_client():
    """Creates and returns a configured ZAP client for security testing"""
    zap_config = settings.get_security_tool_config("zap")
    return ZAPSecurityScanner(zap_config)

def run_zap_spider(target_url, **options):
    """Runs a ZAP spider scan against the target URL"""
    zap = get_zap_client()
    if not zap.initialize():
        return {"status": "error", "message": "Failed to initialize ZAP scanner"}
    spider_options = {"spider": {"enabled": True}}
    if options:
        spider_options["spider"].update(options)
    return zap.start_scan(target_url, spider_options)

def run_zap_active_scan(target_url, **options):
    """Runs a ZAP active scan against the target URL"""
    from .helpers.security_tools import run_security_scan
    return run_security_scan(target_url, options)

def analyze_jwt_token(token):
    """Analyzes a JWT token for security vulnerabilities"""
    analyzer = JWTAnalyzer()
    return analyzer.decode_token(token)

def fuzz_endpoint(endpoint, method, parameters, **options):
    """Fuzzes an API endpoint with various payloads"""
    from .helpers.security_tools import SecurityAPIClient
    client = SecurityAPIClient(settings)
    results = {}
    
    for param_name, param_type in parameters.items():
        fuzzer = InputValidationPayloads()
        results[param_name] = client.fuzz_parameter(
            method=method,
            endpoint=endpoint,
            param_name=param_name,
            param_type=param_type,
            **options
        )
    
    return results

def test_rate_limiting(endpoint, requests_per_second=10, duration_seconds=10):
    """Tests API rate limiting implementation"""
    from .helpers.security_tools import test_rate_limiting as _test_rate_limiting
    return _test_rate_limiting(endpoint, requests_per_second, duration_seconds)

def scan_for_information_disclosure(endpoints, test_requests=None):
    """Scans API responses for sensitive data exposure"""
    from .helpers.security_tools import scan_for_sensitive_data_exposure
    return scan_for_sensitive_data_exposure(endpoints, test_requests)

def test_cors_configuration(target_url):
    """Tests CORS configuration security"""
    from .helpers.security_tools import verify_tls_configuration
    return verify_tls_configuration(target_url)

def generate_security_report(requirements_file):
    """Generates comprehensive security test report"""
    from .helpers.security_tools import run_dependency_scan
    return run_dependency_scan(requirements_file)

def get_payload(category, payload_type, index=None):
    """Get security test payloads by category and type"""
    if category == "sql_injection":
        return SQLInjectionPayloads().get_payload(payload_type, index)
    elif category == "xss":
        return XSSPayloads().get_payload(payload_type, index)
    elif category == "auth_bypass":
        return AuthBypassPayloads().get_payload(payload_type, index)
    elif category == "input_validation":
        # This requires a parameter name and payload type
        # Default to "ticker" if no index is provided
        param = "ticker" if index is None else index
        return InputValidationPayloads().get_payload(param, payload_type)
    else:
        raise ValueError(f"Unknown payload category: {category}")

def generate_random_payload(category, payload_type):
    """Generate random security test payload"""
    if category == "sql_injection":
        return SQLInjectionPayloads().get_random_payload(payload_type)
    elif category == "xss":
        return XSSPayloads().get_random_payload(payload_type)
    elif category == "auth_bypass":
        return AuthBypassPayloads().get_random_payload(payload_type)
    else:
        from .helpers.payloads import get_random_payload as _get_random_payload
        return _get_random_payload(category, payload_type)

def customize_payload(base_json, malformation_type):
    """Customize security test payload"""
    from .helpers.payloads import generate_malformed_json
    return generate_malformed_json(base_json, malformation_type)

def generate_payload_variations(length, char_type):
    """Generate variations of security test payloads"""
    from .helpers.payloads import generate_random_string
    return generate_random_string(length, char_type)

def create_malformed_request(base_request):
    """Create malformed HTTP request for security testing"""
    fuzzer = InputValidationPayloads()
    return fuzzer.generate_malformed_request_objects(base_request)