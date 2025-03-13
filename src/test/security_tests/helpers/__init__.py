"""
Initializes the security_tests.helpers package, providing a convenient way to import
security testing utilities and payloads. This module exposes key classes and functions
from the security_tools and payloads modules to simplify imports in security test files.
"""

# Import classes and functions from security_tools module
from .security_tools import (
    ZAPSecurityScanner,
    JWTAnalyzer,
    APIFuzzer,
    SecurityScanner,
    get_zap_client,
    run_zap_spider,
    run_zap_active_scan,
    analyze_jwt_token,
    fuzz_endpoint,
    test_rate_limiting,
    scan_for_information_disclosure,
    test_cors_configuration,
    generate_security_report,
)

# Import classes and functions from payloads module
from .payloads import (
    SQLInjectionPayloads,
    XSSPayloads,
    AuthBypassPayloads,
    InputValidationPayloads,
    get_payload,
    generate_random_payload,
    customize_payload,
    generate_payload_variations,
    create_malformed_request,
)

# Define exported symbols
__all__ = [
    "ZAPSecurityScanner",
    "JWTAnalyzer",
    "APIFuzzer",
    "SecurityScanner",
    "SQLInjectionPayloads",
    "XSSPayloads",
    "AuthBypassPayloads",
    "InputValidationPayloads",
    "get_zap_client",
    "run_zap_spider",
    "run_zap_active_scan",
    "analyze_jwt_token",
    "fuzz_endpoint",
    "test_rate_limiting",
    "scan_for_information_disclosure",
    "test_cors_configuration",
    "generate_security_report",
    "get_payload",
    "generate_random_payload",
    "customize_payload",
    "generate_payload_variations",
    "create_malformed_request"
]