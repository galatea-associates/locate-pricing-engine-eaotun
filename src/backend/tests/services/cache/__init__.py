"""
Tests for the cache service component of the Borrow Rate & Locate Fee Pricing Engine.

This package contains tests for:
1. Redis cache implementation
2. Cache data handling with appropriate TTLs
3. Fallback mechanisms when external data sources are unavailable
4. Multi-level caching strategies

The tests in this package ensure the caching system correctly handles:
- Caching frequently accessed data like borrow rates and volatility metrics
- Implementing appropriate TTL settings for different data types
- Fallback to cached data when external sources are unavailable
- Cache invalidation mechanisms
"""

# Import testing frameworks
import pytest
from unittest.mock import MagicMock, patch

# Import Redis mocking library
import fakeredis  # fakeredis 2.10.0+

# These imports are made available to all test modules in this package
__all__ = ['pytest', 'MagicMock', 'patch', 'fakeredis']