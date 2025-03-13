"""
Initialization module for the compliance tests helpers package that exports validation utilities for audit logs and calculation accuracy.
This module makes helper functions and classes from audit_validation.py and calculation_validation.py available to compliance test modules, simplifying imports and providing a unified interface for compliance validation.
"""

from .audit_validation import (
    validate_audit_log_structure,
    validate_data_sources,
    validate_calculation_breakdown,
    verify_audit_log_exists,
    verify_fallback_logging,
    verify_audit_retention,
    verify_calculation_accuracy,
    generate_audit_report,
    AuditValidator
)
from .calculation_validation import (
    validate_calculation_structure,
    validate_fee_breakdown,
    validate_borrow_rate_calculation,
    verify_volatility_adjustment,
    verify_event_risk_adjustment,
    verify_base_borrow_cost,
    verify_broker_markup,
    verify_transaction_fee,
    verify_total_fee,
    generate_reference_calculation,
    compare_calculations,
    CalculationValidator
)

VERSION = "1.0.0"
COMPLIANCE_TEST_CATEGORIES = ["audit_trail", "calculation_accuracy", "data_retention", "rate_conformity", "api_documentation"]

__all__ = [
    "validate_audit_log_structure",
    "validate_data_sources",
    "validate_calculation_breakdown",
    "verify_audit_log_exists",
    "verify_fallback_logging",
    "verify_audit_retention",
    "verify_calculation_accuracy",
    "generate_audit_report",
    "AuditValidator",
    "validate_calculation_structure",
    "validate_fee_breakdown",
    "validate_borrow_rate_calculation",
    "verify_volatility_adjustment",
    "verify_event_risk_adjustment",
    "verify_base_borrow_cost",
    "verify_broker_markup",
    "verify_transaction_fee",
    "verify_total_fee",
    "generate_reference_calculation",
    "compare_calculations",
    "CalculationValidator",
    "VERSION",
    "COMPLIANCE_TEST_CATEGORIES"
]