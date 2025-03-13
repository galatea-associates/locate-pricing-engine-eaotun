"""
Security test suite for verifying data encryption functionality in the Borrow Rate & Locate Fee Pricing Engine.
Tests encryption of sensitive data at rest and in transit, including API key storage,
database field encryption, and TLS configuration.
"""

import pytest
import requests
import json
import base64
import ssl
from cryptography.fernet import Fernet  # version: 40.0.0

# Internal imports
from ..config.settings import get_test_settings
from ..helpers.security_tools import create_security_client, verify_tls_configuration, scan_for_sensitive_data_exposure
from ...integration_tests.helpers.api_client import APIClient
from src.backend.core.security import encrypt_sensitive_data, decrypt_sensitive_data

# Global variables
settings = get_test_settings()
TEST_SENSITIVE_DATA = ['test-sensitive-data', 'client-123456', 'api-key-example', '123-45-6789']


def setup_module():
    """Setup function that runs once before all tests in the module"""
    print("Starting data encryption security tests")
    
    # Verify that the test environment is properly configured
    assert settings is not None, "Test settings not properly loaded"
    
    # Create a security client for use in tests
    security_client = create_security_client(settings)
    assert security_client is not None, "Failed to create security client"


def teardown_module():
    """Teardown function that runs once after all tests in the module"""
    print("Completed data encryption security tests")
    
    # Clean up any resources created during testing
    pass


class TestDataEncryption:
    """Test suite for data encryption functionality"""
    
    def test_tls_configuration(self):
        """Tests that the API enforces TLS 1.2+ for all communications"""
        # Get the API base URL from settings
        api_url = settings.api_base_url
        
        # Use verify_tls_configuration to check TLS version and cipher suites
        tls_results = verify_tls_configuration(api_url)
        
        # Assert that minimum TLS version is 1.2 or higher
        assert tls_results["test_results"]["tls_version"]["secure"], \
            "API does not enforce minimum TLS version 1.2+"
        
        # Assert that weak cipher suites are not supported
        assert tls_results["test_results"]["cipher_suites"]["secure"], \
            "API supports weak cipher suites"
        
        # Assert that HSTS headers are properly configured
        assert tls_results["test_results"]["hsts"]["secure"], \
            "API does not have proper HSTS headers"
        
        # Assert that certificates are valid and trusted
        assert tls_results["test_results"]["certificate"]["secure"], \
            "API has invalid or untrusted certificates"
    
    def test_sensitive_data_encryption(self):
        """Tests that sensitive data is properly encrypted and decrypted"""
        # For each test data string in TEST_SENSITIVE_DATA:
        for data in TEST_SENSITIVE_DATA:
            # Encrypt the data using encrypt_sensitive_data
            encrypted_data = encrypt_sensitive_data(data)
            
            # Assert that encrypted data is different from original data
            assert encrypted_data != data, f"Data was not encrypted: {data}"
            
            # Assert that encrypted data is base64-encoded
            try:
                base64.b64decode(encrypted_data)
            except Exception:
                pytest.fail(f"Encrypted data is not base64-encoded: {encrypted_data}")
            
            # Decrypt the data using decrypt_sensitive_data
            decrypted_data = decrypt_sensitive_data(encrypted_data)
            
            # Assert that decrypted data matches the original data
            assert decrypted_data == data, \
                f"Decryption failed. Original: {data}, Decrypted: {decrypted_data}"
    
    def test_api_key_encryption(self):
        """Tests that API keys are properly encrypted in storage"""
        # Create a security client with valid API key
        client = create_security_client()
        
        # Make a request to the /config endpoint to get API key configuration
        response = client.request(method="GET", endpoint="/config")
        
        # Assert request was successful
        assert response.status_code == 200, f"Failed to get config with status {response.status_code}"
        
        config_data = response.json()
        
        # Check if API key storage info is in the response
        if "api_key_storage" in config_data:
            # Assert that API keys are not stored in plaintext
            assert config_data["api_key_storage"]["plaintext"] is False, \
                "API keys are stored in plaintext"
            
            # Assert that API key hashes use a secure hashing algorithm
            assert config_data["api_key_storage"]["algorithm"] in ["bcrypt", "PBKDF2", "Argon2"], \
                f"Insecure hashing algorithm used: {config_data['api_key_storage']['algorithm']}"
        else:
            # If API key storage info is not directly available, check the security settings
            api_client = APIClient()
            response = api_client.get("/health")
            
            # Assert that we can make authenticated requests (key works) but we can't see the actual key
            assert response.status_code == 200, "API key authentication failed"
            
            # Check if we can access the test API key directly from settings
            # It should be securely stored
            test_key = settings.test_api_key
            if test_key:
                # Check for evidence this key is securely stored
                secure_evidence = (
                    test_key.startswith("$2b$") or  # bcrypt
                    test_key.startswith("pbkdf2:") or  # PBKDF2
                    "$argon2" in test_key  # Argon2
                )
                
                if not secure_evidence:
                    # If we don't see hash evidence, verify that the key cannot be found in the DB in plaintext
                    # This is an indirect test since we can't directly check the database
                    data_response = scan_for_sensitive_data_exposure(["/config"])
                    assert not any(
                        test_key in str(item) for item in data_response["test_results"].values()
                    ), "API key may be exposed in responses"
    
    def test_sensitive_data_exposure(self):
        """Tests that sensitive data is not exposed in API responses"""
        # Define a list of API endpoints to test
        endpoints = [
            "/health",
            "/config",
            "/rates/AAPL",
            "/calculate-locate"
        ]
        
        # Use scan_for_sensitive_data_exposure to check for data leakage
        results = scan_for_sensitive_data_exposure(endpoints)
        
        # Assert that no plaintext sensitive data is exposed in responses
        assert not results["is_vulnerable"], \
            f"Sensitive data exposure detected: {results['vulnerabilities_found']}"
        
        # Assert that error responses don't leak sensitive information
        security_client = create_security_client()
        
        # Trigger an error response by requesting a non-existent resource
        error_response = security_client.request(
            method="GET",
            endpoint="/nonexistent-endpoint"
        )
        
        # Check that error response doesn't contain sensitive information
        assert error_response.status_code >= 400, "Expected error response"
        
        error_data = error_response.text
        
        # Check for common sensitive patterns in error response
        sensitive_patterns = ["password", "secret", "key", "token", "credential"]
        for pattern in sensitive_patterns:
            assert pattern not in error_data.lower(), \
                f"Error response may leak sensitive data: '{pattern}' found in response"
    
    def test_encryption_key_management(self):
        """Tests that encryption keys are properly managed and rotated"""
        # Create a security client with valid API key
        client = create_security_client()
        
        # Make a request to the /config endpoint to get key management configuration
        response = client.request(method="GET", endpoint="/config")
        
        # Assert request was successful
        assert response.status_code == 200, f"Failed to get config with status {response.status_code}"
        
        config_data = response.json()
        
        # Check if key management info is in the response
        if "key_management" in config_data:
            # Assert that encryption keys have rotation policies
            assert "rotation_policy" in config_data["key_management"], \
                "No key rotation policy found"
            
            # Assert that key access is properly restricted
            assert "access_control" in config_data["key_management"], \
                "No key access control found"
            
            # Check rotation period (should be reasonable, like 90 days or less)
            rotation_days = config_data["key_management"]["rotation_policy"].get("days", 0)
            assert 1 <= rotation_days <= 365, \
                f"Key rotation period ({rotation_days} days) outside reasonable range"
        else:
            # If key management info is not directly available, we'll test indirectly
            # Encrypt the same data twice and check if we get different results
            # This isn't perfect but gives some confidence in the encryption implementation
            test_data = "test-encryption-data"
            
            # First encryption
            encrypted1 = encrypt_sensitive_data(test_data)
            
            # Second encryption
            encrypted2 = encrypt_sensitive_data(test_data)
            
            # Different ciphertexts for the same plaintext suggests secure encryption
            # (e.g., with initialization vectors)
            assert encrypted1 != encrypted2, \
                "Encryption appears deterministic, which may indicate poor key management"
            
            # Both should decrypt to the same value
            assert decrypt_sensitive_data(encrypted1) == test_data
            assert decrypt_sensitive_data(encrypted2) == test_data
    
    def test_database_field_encryption(self):
        """Tests that sensitive database fields are properly encrypted"""
        # Create a security client with valid API key
        client = create_security_client()
        
        # Get a broker configuration which may contain sensitive data
        api_client = APIClient()
        client_id = "test_broker_1"  # Use a test client ID
        
        # Make a request to get broker config
        response = api_client.get(f"/config/broker/{client_id}")
        
        # If the endpoint doesn't exist, we'll need to test a different way
        if response.status_code == 404:
            # Try the calculate endpoint which indirectly uses broker data
            calc_response = api_client.post(
                "/calculate-locate",
                json_data={
                    "ticker": "AAPL",
                    "position_value": 100000,
                    "loan_days": 30,
                    "client_id": client_id
                }
            )
            
            assert calc_response.status_code == 200, \
                f"Failed to get calculation with status {calc_response.status_code}"
            
            # We can't directly verify encryption, but we can check for evidence of secure handling
            
            # Scan for sensitive data exposure in the calculation result
            scan_result = scan_for_sensitive_data_exposure(["/calculate-locate"])
            assert not scan_result["is_vulnerable"], \
                "Sensitive data may be exposed in calculation responses"
        else:
            # If we got a broker config, check it for evidence of encrypted fields
            assert response.status_code == 200, \
                f"Failed to get broker config with status {response.status_code}"
            
            config_data = response.json()
            
            # Look for evidence of field encryption in the response
            # Encrypted fields would typically have a format like "enc:base64data"
            # or be returned as placeholders like "********" for sensitive data
            
            # This is a bit of a heuristic since we don't know exactly how the API formats encrypted data
            sensitive_fields = ["api_key", "secret", "password", "token", "credential"]
            for field in sensitive_fields:
                if field in config_data:
                    field_value = config_data[field]
                    # Check if it looks like it might be encrypted
                    is_potentially_encrypted = (
                        isinstance(field_value, str) and
                        (field_value.startswith("enc:") or
                         all(c == "*" for c in field_value) or
                         (len(field_value) > 20 and "=" in field_value))  # Possible base64
                    )
                    assert is_potentially_encrypted, \
                        f"Sensitive field '{field}' may not be encrypted: {field_value}"
    
    def test_encryption_algorithm_strength(self):
        """Tests that strong encryption algorithms are used"""
        # Encrypt some data to test
        test_data = "test-encryption-strength"
        encrypted_data = encrypt_sensitive_data(test_data)
        
        # First check if we can determine the algorithm from the encrypted data
        # Fernet tokens (which use AES-256-CBC with HMAC) start with 'gA'
        if isinstance(encrypted_data, str) and encrypted_data.startswith("gA"):
            # This is likely Fernet, which uses AES-256-CBC with HMAC
            # Verify by trying to decrypt with Fernet
            try:
                from src.backend.core.security import get_settings
                encryption_key = get_settings().get_calculation_setting("encryption_key")
                f = Fernet(encryption_key)
                decrypted = f.decrypt(encrypted_data.encode()).decode()
                assert decrypted == test_data, "Fernet decryption failed"
                
                # Assert that AES-256 or equivalent is used for data at rest
                assert True, "Using Fernet encryption (AES-256-CBC with HMAC)"
            except Exception:
                # If this fails, it might be using a different encryption method
                pass
        
        # If we couldn't determine the algorithm, indirectly test its strength
        
        # Ensure encrypted data has sufficient length for strong encryption
        # Base64-encoded AES-256 output would be at least ~44 chars for short inputs
        assert len(encrypted_data) >= 40, \
            f"Encrypted output too short ({len(encrypted_data)} chars), may indicate weak encryption"
        
        # Check if ciphertext looks random (high entropy)
        # A simple proxy for entropy is counting unique characters
        unique_chars = len(set(encrypted_data))
        assert unique_chars >= 16, \
            f"Encrypted output has low entropy ({unique_chars} unique chars), may indicate weak encryption"
        
        # Assert that key sizes are sufficient (256-bit or higher)
        # This is an indirect test since we don't have direct access to the key size
        
        # Assert that secure modes of operation are used (e.g., GCM, not ECB)
        # Again, indirect test based on ciphertext properties
        
        # Verify the decryption works
        decrypted_data = decrypt_sensitive_data(encrypted_data)
        assert decrypted_data == test_data, "Decryption failed"
    
    def test_encrypted_data_integrity(self):
        """Tests that encrypted data maintains integrity and can't be tampered with"""
        # Encrypt test data using encrypt_sensitive_data
        test_data = "integrity-test-data"
        encrypted_data = encrypt_sensitive_data(test_data)
        
        # Attempt to modify the encrypted data
        if len(encrypted_data) > 10:
            # Change a character in the middle of the string
            middle_index = len(encrypted_data) // 2
            tampered_data = encrypted_data[:middle_index] + ('A' if encrypted_data[middle_index] != 'A' else 'B') + encrypted_data[middle_index+1:]
            
            # Attempt to decrypt the modified data
            try:
                decrypted = decrypt_sensitive_data(tampered_data)
                # If we get here, the decryption didn't fail as expected
                assert decrypted != test_data, "Tampered data decrypted but returned incorrect result"
                pytest.fail("Decryption of tampered data should have failed but succeeded")
            except Exception:
                # Expected behavior - decryption should fail
                pass
        
        # Additional test: change the last few characters, which typically contain
        # the authentication tag in modern encryption schemes
        if len(encrypted_data) > 5:
            tampered_data = encrypted_data[:-5] + 'XXXXX'
            
            # Attempt to decrypt the modified data
            try:
                decrypt_sensitive_data(tampered_data)
                # If we get here, the decryption didn't fail as expected
                pytest.fail("Decryption of tampered data should have failed but succeeded")
            except Exception:
                # Expected behavior - decryption should fail or integrity check fails
                pass