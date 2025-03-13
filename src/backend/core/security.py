"""
Core security module for the Borrow Rate & Locate Fee Pricing Engine.

This module provides functions for API key verification, JWT token generation and validation,
password hashing, and encryption utilities. It serves as the foundation for the application's
security architecture.
"""

import jwt  # pyjwt 2.6.0+
from passlib.context import CryptContext  # passlib 1.7.4+
from cryptography.fernet import Fernet  # cryptography 40.0.0+
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from ..config.settings import get_settings
from .constants import ErrorCodes
from .exceptions import AuthenticationException
from ..utils.logging import setup_logger

# Set up module logger
logger = setup_logger('core.security')

# Configure the password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Token lifetime of 15 minutes


def verify_api_key(api_key: str) -> bool:
    """
    Verifies if an API key is valid by checking against stored configurations.
    
    Args:
        api_key: The API key to verify
        
    Returns:
        bool: True if the API key is valid, False otherwise
    """
    settings = get_settings()
    api_key_config = settings.get_api_key_config(api_key)
    
    is_valid = api_key_config is not None
    logger.info(f"API key verification: {'successful' if is_valid else 'failed'}")
    
    return is_valid


def get_client_for_api_key(api_key: str) -> Optional[str]:
    """
    Retrieves the client ID associated with an API key.
    
    Args:
        api_key: The API key to look up
        
    Returns:
        Optional[str]: Client ID if the API key is valid, None otherwise
    """
    settings = get_settings()
    api_key_config = settings.get_api_key_config(api_key)
    
    if api_key_config is not None:
        return api_key_config.get("client_id")
    
    return None


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token with an expiration time.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    settings = get_settings()
    # Get JWT secret key from settings
    jwt_secret_key = settings.get_calculation_setting("jwt_secret_key")
    
    encoded_jwt = jwt.encode(to_encode, jwt_secret_key, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a JWT access token.
    
    Args:
        token: The JWT token to decode
        
    Returns:
        Dict[str, Any]: Decoded token payload
        
    Raises:
        AuthenticationException: If the token is invalid or expired
    """
    settings = get_settings()
    jwt_secret_key = settings.get_calculation_setting("jwt_secret_key")
    
    try:
        payload = jwt.decode(token, jwt_secret_key, algorithms=[ALGORITHM])
        logger.info("Token validation successful")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token validation failed: expired token")
        raise AuthenticationException("Token has expired", ErrorCodes.UNAUTHORIZED)
    except jwt.InvalidTokenError:
        logger.warning("Token validation failed: invalid token")
        raise AuthenticationException("Invalid token", ErrorCodes.UNAUTHORIZED)


def hash_password(password: str) -> str:
    """
    Hashes a password using bcrypt.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a password against a hash.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to check against
        
    Returns:
        bool: True if the password matches the hash, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_api_key(length: int = 32) -> str:
    """
    Generates a new cryptographically secure API key.
    
    Args:
        length: Length of the API key (default: 32)
        
    Returns:
        str: Generated API key
    """
    # Generate a random URL-safe string
    key = secrets.token_urlsafe(length)
    
    # Ensure it's exactly the right length (token_urlsafe can generate strings slightly longer)
    key = key[:length]
    
    return key


def encrypt_sensitive_data(data: str) -> str:
    """
    Encrypts sensitive data using Fernet symmetric encryption.
    
    Args:
        data: The string data to encrypt
        
    Returns:
        str: Encrypted data as a base64-encoded string
    """
    settings = get_settings()
    encryption_key = settings.get_calculation_setting("encryption_key")
    
    f = Fernet(encryption_key)
    encrypted_data = f.encrypt(data.encode())
    
    return encrypted_data.decode()


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    Decrypts data that was encrypted with encrypt_sensitive_data.
    
    Args:
        encrypted_data: The encrypted data to decrypt
        
    Returns:
        str: Decrypted data as a string
        
    Raises:
        AuthenticationException: If decryption fails
    """
    settings = get_settings()
    encryption_key = settings.get_calculation_setting("encryption_key")
    
    try:
        f = Fernet(encryption_key)
        decrypted_data = f.decrypt(encrypted_data.encode())
        return decrypted_data.decode()
    except Exception as e:
        logger.error(f"Decryption error: {str(e)}")
        raise AuthenticationException("Failed to decrypt data", ErrorCodes.UNAUTHORIZED)


class APIKeyGenerator:
    """
    Utility class for generating and managing API keys.
    """
    
    def __init__(self):
        """
        Initializes the API key generator.
        """
        pass
    
    def generate_key(self, length: int = 32) -> str:
        """
        Generates a new API key with specified length.
        
        Args:
            length: Length of the API key (default: 32)
            
        Returns:
            str: Generated API key
        """
        return generate_api_key(length)
    
    def create_key_config(self, client_id: str, rate_limit: int = 60, expiry_days: Optional[int] = None) -> Dict[str, Any]:
        """
        Creates a configuration for a new API key.
        
        Args:
            client_id: The client identifier to associate with the key
            rate_limit: Requests per minute allowed (default: 60)
            expiry_days: Days until the key expires (default: API_KEY_EXPIRY_DAYS)
            
        Returns:
            Dict[str, Any]: API key configuration
        """
        # Generate new API key
        api_key = self.generate_key()
        
        # Calculate expiration date
        if expiry_days is None:
            # Import here to avoid circular import
            from .constants import API_KEY_EXPIRY_DAYS
            expiry_days = API_KEY_EXPIRY_DAYS
            
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(days=expiry_days)
        
        # Create configuration
        config = {
            "key": api_key,
            "client_id": client_id,
            "rate_limit": rate_limit,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat()
        }
        
        return config