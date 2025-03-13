"""
Entry point for the external services module that provides access to external APIs used by the Borrow Rate & Locate Fee Pricing Engine. This module exposes client implementations for SecLend API (borrow rates), Market Volatility API (volatility metrics), and Event Calendar API (event risk data), along with common utilities for external API interactions.
"""

# Import all client utilities for external API interactions
from .client import *

# Import all utility functions for external API interactions
from .utils import *

# Import all SecLend API functions for borrow rate data
from .seclend_api import *

# Import all Market Volatility API functions for volatility data
from .market_api import *

# Import all Event Calendar API functions for event risk data
from .event_api import *

# Import exception class for external API failures
from ...core.exceptions import ExternalAPIException

# Import external API constants for service identification
from ...core.constants import ExternalAPIs