"""
Database test package for the Borrow Rate & Locate Fee Pricing Engine.

This package contains test modules specifically for database operations,
including database access layer testing, query performance, and error handling.
It provides common utilities, fixtures, and helper functions to facilitate
database testing across the system.
"""

import pytest  # pytest 7.4.0+
from .. import setup_test_environment  # Import the test environment setup function from parent package

# Database test package identifier
DB_TEST_PACKAGE = 'db'

def setup_db_test_environment():
    """
    Helper function to set up database-specific test environment configurations.
    
    This function initializes the test environment specifically for database
    tests, including configuration for test databases, connection pools,
    and other database-specific test settings.
    
    Returns:
        None
    """
    # Call the parent setup_test_environment function
    setup_test_environment()
    
    # Configure database-specific test settings
    # These settings might include test database URLs, credential handling,
    # transaction isolation levels, and other database-specific configurations
    
    # Initialize database test constants
    # These constants might include timeout values, retry counts,
    # and other database test parameters

# Define exports
__all__ = ["setup_db_test_environment", "DB_TEST_PACKAGE"]