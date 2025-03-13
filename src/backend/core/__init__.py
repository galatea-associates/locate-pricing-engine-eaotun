"""
Initialization file for the core module of the Borrow Rate & Locate Fee Pricing Engine.

This module exports essential components for authentication, error handling,
logging, and security that are used throughout the application.
"""

# Import and re-export constants
from .constants import (
    BorrowStatus,
    TransactionFeeType,
    ErrorCodes,
    ExternalAPIs,
)

# Import and re-export error handling functions
from .errors import (
    get_error_message,
    get_http_status_code,
    raise_http_exception,  # Note: This function may need to be implemented
    create_error_response,
)

# Import and re-export exception classes
from .exceptions import (
    BaseAPIException,
    ValidationException,
    AuthenticationException,
    TickerNotFoundException,
    ClientNotFoundException,
    RateLimitExceededException,
    CalculationException,
    ExternalAPIException,
)

# Import and re-export security functions
from .security import (
    generate_api_key,
    hash_api_key,  # Note: This function may need to be implemented
    verify_api_key,
    create_access_token,
    decode_access_token,
)

# Import and re-export authentication functions
from .auth import (
    authenticate_api_key,  # Note: This function may need to be implemented
    get_client_id_from_api_key,  # Note: This function may need to be implemented
    authenticate_request,
    RateLimiter,
)

# Import and re-export logging functions
from .logging import (
    init_logging,
    get_correlation_id,
    log_error,
    log_calculation,
    log_fallback_usage,
)

# Import and re-export middleware setup
from .middleware import setup_middleware