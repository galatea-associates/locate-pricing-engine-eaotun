"""
Initialization module for end-to-end test fixtures that exports all fixtures from
environment.py and test_data.py modules.

This file makes fixtures available to pytest for end-to-end testing of the
Borrow Rate & Locate Fee Pricing Engine.
"""

import logging
import pytest  # pytest: 7.4.0+

# Import fixtures from environment.py
from .environment import (
    test_environment,
    api_client,
    mock_seclend_api,
    mock_market_api,
    mock_event_api,
)

# Import fixtures from test_data.py
from .test_data import (
    test_data,
    test_stocks,
    test_brokers,
    test_volatility,
    test_scenarios,
    normal_market_scenario,
    high_volatility_scenario,
    corporate_event_scenario,
    hard_to_borrow_scenario,
    long_term_loan_scenario,
)

# Set up logger
logger = logging.getLogger(__name__)

# These fixtures are automatically exported to pytest
# No need for __all__ as pytest discovers fixtures by name

logger.debug("End-to-end test fixtures initialized and exported.")