"""
Package initialization file for the audit service module in the Borrow Rate & Locate Fee Pricing Engine.

This module provides comprehensive audit logging functionality for recording fee calculations, 
tracking data sources, and supporting regulatory compliance requirements. It exposes key 
components from the audit service submodules for easy access by other parts of the application.
"""

# Import from logger submodule
from .logger import (
    AuditLogger,
    format_calculation_for_audit
)

# Import from transactions submodule
from .transactions import (
    TransactionAuditor,
    calculate_fee_statistics,
    analyze_fallback_usage
)

# Import from utils submodule
from .utils import (
    create_data_source_entry,
    create_api_data_source,
    create_cache_data_source,
    create_database_data_source,
    format_decimal_for_audit,
    has_fallback_source,
    get_data_source_names,
    serialize_audit_data,
    deserialize_audit_data,
    create_audit_context
)

# Define what should be importable from this module
__all__ = [
    # AuditLogger class and related functions
    'AuditLogger',
    'format_calculation_for_audit',
    
    # TransactionAuditor class and related functions
    'TransactionAuditor',
    'calculate_fee_statistics',
    'analyze_fallback_usage',
    
    # Utility functions
    'create_data_source_entry',
    'create_api_data_source',
    'create_cache_data_source',
    'create_database_data_source',
    'format_decimal_for_audit',
    'has_fallback_source',
    'get_data_source_names',
    'serialize_audit_data',
    'deserialize_audit_data',
    'create_audit_context'
]