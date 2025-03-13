"""
Initialization module for the calculation service package in the Borrow Rate & Locate Fee Pricing Engine.

This module serves as the primary entry point for accessing calculation functionality related to
borrow rates and locate fees. It exports a clean interface of core calculation functions that
abstract the internal implementation details from other services.
"""

import logging

# Import borrow rate calculation functions
from .borrow_rate import (
    calculate_borrow_rate,
    get_real_time_borrow_rate,
    get_fallback_borrow_rate
)

# Import locate fee calculation functions
from .locate_fee import (
    calculate_locate_fee,
    calculate_base_borrow_cost,
    calculate_broker_markup,
    calculate_transaction_fee,
    get_default_broker_config
)

# Import volatility adjustment functions
from .volatility import (
    calculate_volatility_adjustment,
    apply_volatility_adjustment
)

# Import event risk adjustment functions
from .event_risk import calculate_event_risk_adjustment

# Import utility functions
from .utils import (
    validate_calculation_inputs,
    format_rate_percentage,
    create_fee_breakdown
)

# Set up module-level logger
logger = logging.getLogger(__name__)

# Package version
__version__ = '1.0.0'

# Export public API
__all__ = [
    # Borrow rate calculation
    'calculate_borrow_rate',
    'get_real_time_borrow_rate',
    'get_fallback_borrow_rate',
    
    # Locate fee calculation
    'calculate_locate_fee',
    'calculate_base_borrow_cost',
    'calculate_broker_markup',
    'calculate_transaction_fee',
    'get_default_broker_config',
    
    # Volatility adjustments
    'calculate_volatility_adjustment',
    'apply_volatility_adjustment',
    
    # Event risk adjustments
    'calculate_event_risk_adjustment',
    
    # Utilities
    'validate_calculation_inputs',
    'format_rate_percentage',
    'create_fee_breakdown'
]