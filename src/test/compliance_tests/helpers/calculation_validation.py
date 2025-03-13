"""
Helper module for validating calculation accuracy in compliance tests.

This module provides functions and classes to verify that financial calculations meet regulatory
requirements for precision, consistency, and mathematical correctness. Used by compliance tests
to ensure the system's calculations are accurate and compliant with financial regulations.
"""

import pytest  # pytest 7.4.0+
from decimal import Decimal  # standard library
from typing import Dict, List, Optional, Any, Union, Tuple  # standard library
import json  # standard library
import logging  # standard library

# Internal imports
from src.backend.core.constants import (
    DAYS_IN_YEAR,
    DEFAULT_MINIMUM_BORROW_RATE,
    DEFAULT_VOLATILITY_FACTOR,
    DEFAULT_EVENT_RISK_FACTOR,
    TransactionFeeType,
    BorrowStatus
)
from src.backend.utils.math import round_decimal
from src.backend.services.calculation.borrow_rate import calculate_borrow_rate
from src.backend.services.calculation.formulas import (
    calculate_volatility_adjustment,
    calculate_event_risk_adjustment,
    calculate_borrow_cost,
    calculate_markup_amount,
    calculate_fee
)
from src.backend.services.calculation.locate_fee import calculate_locate_fee

# Set constants for validation
CALCULATION_PRECISION_TOLERANCE = Decimal('0.0001')  # Tolerance for comparing decimal calculations
ROUNDING_PRECISION = 4  # Number of decimal places for rounding
REQUIRED_CALCULATION_FIELDS = ["total_fee", "breakdown", "borrow_rate_used"]
REQUIRED_BREAKDOWN_FIELDS = ["borrow_cost", "markup", "transaction_fees"]


def validate_calculation_structure(calculation_result: Dict[str, Any]) -> bool:
    """
    Validates that a calculation result contains all required fields with correct types.
    
    Args:
        calculation_result: The calculation result to validate
        
    Returns:
        True if calculation structure is valid, raises AssertionError otherwise
    """
    # Check that all required fields are present
    for field in REQUIRED_CALCULATION_FIELDS:
        assert field in calculation_result, f"Missing required field: {field}"
    
    # Validate total_fee
    assert isinstance(calculation_result["total_fee"], (float, int, Decimal)), \
        f"total_fee must be a numeric value, got {type(calculation_result['total_fee'])}"
    assert float(calculation_result["total_fee"]) >= 0, \
        f"total_fee must be non-negative, got {calculation_result['total_fee']}"
    
    # Validate breakdown
    breakdown = calculation_result["breakdown"]
    assert isinstance(breakdown, dict), f"breakdown must be a dictionary, got {type(breakdown)}"
    
    for field in REQUIRED_BREAKDOWN_FIELDS:
        assert field in breakdown, f"Missing required breakdown field: {field}"
        assert isinstance(breakdown[field], (float, int, Decimal)), \
            f"breakdown.{field} must be a numeric value, got {type(breakdown[field])}"
        assert float(breakdown[field]) >= 0, \
            f"breakdown.{field} must be non-negative, got {breakdown[field]}"
    
    # Validate borrow_rate_used
    assert isinstance(calculation_result["borrow_rate_used"], (float, int, Decimal)), \
        f"borrow_rate_used must be a numeric value, got {type(calculation_result['borrow_rate_used'])}"
    assert float(calculation_result["borrow_rate_used"]) >= 0, \
        f"borrow_rate_used must be non-negative, got {calculation_result['borrow_rate_used']}"
    
    return True


def validate_fee_breakdown(calculation_result: Dict[str, Any]) -> bool:
    """
    Validates that fee breakdown components sum to the total fee.
    
    Args:
        calculation_result: The calculation result to validate
        
    Returns:
        True if fee breakdown is valid, raises AssertionError otherwise
    """
    total_fee = Decimal(str(calculation_result["total_fee"]))
    breakdown = calculation_result["breakdown"]
    
    # Convert all components to Decimal for precise calculation
    borrow_cost = Decimal(str(breakdown["borrow_cost"]))
    markup = Decimal(str(breakdown["markup"]))
    transaction_fees = Decimal(str(breakdown["transaction_fees"]))
    
    # Calculate the sum of all components
    components_sum = borrow_cost + markup + transaction_fees
    
    # Verify that the sum equals the total fee within tolerance
    difference = abs(total_fee - components_sum)
    assert difference <= CALCULATION_PRECISION_TOLERANCE, \
        f"Fee breakdown components ({components_sum}) do not sum to total fee ({total_fee}), difference: {difference}"
    
    return True


def validate_borrow_rate_calculation(
    base_rate: Decimal,
    volatility_index: Decimal,
    event_risk_factor: int,
    calculated_rate: Decimal,
    min_rate: Optional[Decimal] = None
) -> bool:
    """
    Validates that a borrow rate calculation is accurate.
    
    Args:
        base_rate: The base borrow rate
        volatility_index: The volatility index used
        event_risk_factor: The event risk factor used
        calculated_rate: The calculated borrow rate to validate
        min_rate: Optional minimum rate threshold
        
    Returns:
        True if borrow rate calculation is valid, raises AssertionError otherwise
    """
    # Calculate expected volatility adjustment
    volatility_adjustment = calculate_volatility_adjustment(volatility_index)
    
    # Apply volatility adjustment to base_rate
    volatility_adjusted_rate = base_rate * (Decimal('1') + volatility_adjustment)
    
    # Calculate expected event risk adjustment
    event_adjustment = calculate_event_risk_adjustment(event_risk_factor)
    
    # Apply event risk adjustment to volatility-adjusted rate
    expected_rate = volatility_adjusted_rate * (Decimal('1') + event_adjustment)
    
    # Apply minimum rate if provided
    if min_rate is not None:
        expected_rate = max(expected_rate, min_rate)
    else:
        expected_rate = max(expected_rate, DEFAULT_MINIMUM_BORROW_RATE)
    
    # Round to appropriate precision
    expected_rate = round_decimal(expected_rate, ROUNDING_PRECISION)
    
    # Compare with calculated rate
    difference = abs(calculated_rate - expected_rate)
    assert difference <= CALCULATION_PRECISION_TOLERANCE, \
        f"Calculated rate ({calculated_rate}) does not match expected rate ({expected_rate}), difference: {difference}"
    
    return True


def verify_volatility_adjustment(
    base_rate: Decimal,
    volatility_index: Decimal,
    adjusted_rate: Decimal,
    volatility_factor: Optional[Decimal] = None
) -> bool:
    """
    Verifies that volatility adjustment is correctly applied to a base rate.
    
    Args:
        base_rate: The base rate before adjustment
        volatility_index: The volatility index used
        adjusted_rate: The adjusted rate to verify
        volatility_factor: Optional custom volatility factor
        
    Returns:
        True if volatility adjustment is valid, raises AssertionError otherwise
    """
    if volatility_factor is None:
        volatility_factor = DEFAULT_VOLATILITY_FACTOR
    
    # Calculate expected volatility adjustment
    volatility_adjustment = volatility_index * volatility_factor
    expected_rate = base_rate * (Decimal('1') + volatility_adjustment)
    expected_rate = round_decimal(expected_rate, ROUNDING_PRECISION)
    
    # Compare with provided adjusted rate
    difference = abs(adjusted_rate - expected_rate)
    assert difference <= CALCULATION_PRECISION_TOLERANCE, \
        f"Volatility-adjusted rate ({adjusted_rate}) does not match expected rate ({expected_rate}), difference: {difference}"
    
    return True


def verify_event_risk_adjustment(
    base_rate: Decimal,
    event_risk_factor: int,
    adjusted_rate: Decimal,
    risk_multiplier: Optional[Decimal] = None
) -> bool:
    """
    Verifies that event risk adjustment is correctly applied to a base rate.
    
    Args:
        base_rate: The base rate before adjustment
        event_risk_factor: The event risk factor used
        adjusted_rate: The adjusted rate to verify
        risk_multiplier: Optional custom risk multiplier
        
    Returns:
        True if event risk adjustment is valid, raises AssertionError otherwise
    """
    if risk_multiplier is None:
        risk_multiplier = DEFAULT_EVENT_RISK_FACTOR
    
    # Calculate expected event risk adjustment
    risk_ratio = Decimal(event_risk_factor) / Decimal('10')
    risk_adjustment = risk_ratio * risk_multiplier
    expected_rate = base_rate * (Decimal('1') + risk_adjustment)
    expected_rate = round_decimal(expected_rate, ROUNDING_PRECISION)
    
    # Compare with provided adjusted rate
    difference = abs(adjusted_rate - expected_rate)
    assert difference <= CALCULATION_PRECISION_TOLERANCE, \
        f"Event risk-adjusted rate ({adjusted_rate}) does not match expected rate ({expected_rate}), difference: {difference}"
    
    return True


def verify_base_borrow_cost(
    position_value: Decimal,
    borrow_rate: Decimal,
    loan_days: int,
    borrow_cost: Decimal
) -> bool:
    """
    Verifies that base borrow cost is correctly calculated.
    
    Args:
        position_value: The position value
        borrow_rate: The annualized borrow rate
        loan_days: The loan duration in days
        borrow_cost: The calculated borrow cost to verify
        
    Returns:
        True if base borrow cost is valid, raises AssertionError otherwise
    """
    # Calculate expected borrow cost
    daily_rate = borrow_rate / DAYS_IN_YEAR
    expected_cost = position_value * daily_rate * Decimal(loan_days)
    expected_cost = round_decimal(expected_cost, ROUNDING_PRECISION)
    
    # Compare with provided borrow cost
    difference = abs(borrow_cost - expected_cost)
    assert difference <= CALCULATION_PRECISION_TOLERANCE, \
        f"Borrow cost ({borrow_cost}) does not match expected cost ({expected_cost}), difference: {difference}"
    
    return True


def verify_broker_markup(
    base_value: Decimal,
    markup_percentage: Decimal,
    markup_amount: Decimal
) -> bool:
    """
    Verifies that broker markup is correctly calculated.
    
    Args:
        base_value: The base value to apply markup to
        markup_percentage: The markup percentage
        markup_amount: The calculated markup amount to verify
        
    Returns:
        True if broker markup is valid, raises AssertionError otherwise
    """
    # Calculate expected markup
    expected_markup = base_value * (markup_percentage / Decimal('100'))
    expected_markup = round_decimal(expected_markup, ROUNDING_PRECISION)
    
    # Compare with provided markup amount
    difference = abs(markup_amount - expected_markup)
    assert difference <= CALCULATION_PRECISION_TOLERANCE, \
        f"Markup amount ({markup_amount}) does not match expected markup ({expected_markup}), difference: {difference}"
    
    return True


def verify_transaction_fee(
    base_value: Decimal,
    fee_type: TransactionFeeType,
    fee_amount: Decimal,
    transaction_fee: Decimal
) -> bool:
    """
    Verifies that transaction fee is correctly calculated.
    
    Args:
        base_value: The base value for percentage-based fees
        fee_type: The fee type (FLAT or PERCENTAGE)
        fee_amount: The fee amount or percentage
        transaction_fee: The calculated transaction fee to verify
        
    Returns:
        True if transaction fee is valid, raises AssertionError otherwise
    """
    # Calculate expected transaction fee
    if fee_type == TransactionFeeType.FLAT:
        expected_fee = fee_amount
    elif fee_type == TransactionFeeType.PERCENTAGE:
        expected_fee = base_value * (fee_amount / Decimal('100'))
    else:
        raise ValueError(f"Unknown fee type: {fee_type}")
    
    expected_fee = round_decimal(expected_fee, ROUNDING_PRECISION)
    
    # Compare with provided transaction fee
    difference = abs(transaction_fee - expected_fee)
    assert difference <= CALCULATION_PRECISION_TOLERANCE, \
        f"Transaction fee ({transaction_fee}) does not match expected fee ({expected_fee}), difference: {difference}"
    
    return True


def verify_total_fee(
    borrow_cost: Decimal,
    markup_amount: Decimal,
    transaction_fee: Decimal,
    total_fee: Decimal
) -> bool:
    """
    Verifies that total fee is correctly calculated as sum of components.
    
    Args:
        borrow_cost: The base borrow cost
        markup_amount: The broker markup amount
        transaction_fee: The transaction fee amount
        total_fee: The calculated total fee to verify
        
    Returns:
        True if total fee is valid, raises AssertionError otherwise
    """
    # Calculate expected total fee
    expected_total = borrow_cost + markup_amount + transaction_fee
    expected_total = round_decimal(expected_total, ROUNDING_PRECISION)
    
    # Compare with provided total fee
    difference = abs(total_fee - expected_total)
    assert difference <= CALCULATION_PRECISION_TOLERANCE, \
        f"Total fee ({total_fee}) does not match expected total ({expected_total}), difference: {difference}"
    
    return True


def generate_reference_calculation(
    ticker: str,
    position_value: Decimal,
    loan_days: int,
    borrow_rate: Decimal,
    markup_percentage: Decimal,
    fee_type: TransactionFeeType,
    fee_amount: Decimal
) -> Dict[str, Any]:
    """
    Generates a reference calculation for comparison with system calculation.
    
    Args:
        ticker: Stock symbol
        position_value: Position value
        loan_days: Loan duration in days
        borrow_rate: Borrow rate to use
        markup_percentage: Broker markup percentage
        fee_type: Transaction fee type
        fee_amount: Transaction fee amount
        
    Returns:
        Reference calculation result
    """
    # Calculate base borrow cost
    base_borrow_cost = calculate_borrow_cost(position_value, borrow_rate, loan_days)
    
    # Calculate markup amount
    markup_amount = calculate_markup_amount(base_borrow_cost, markup_percentage)
    
    # Calculate transaction fee
    transaction_fee = calculate_fee(base_value=position_value, fee_type=fee_type, fee_amount=fee_amount)
    
    # Calculate total fee
    total_fee = base_borrow_cost + markup_amount + transaction_fee
    total_fee = round_decimal(total_fee, ROUNDING_PRECISION)
    
    # Create result dictionary with the same structure as the system calculation
    result = {
        "total_fee": float(total_fee),
        "breakdown": {
            "borrow_cost": float(base_borrow_cost),
            "markup": float(markup_amount),
            "transaction_fees": float(transaction_fee)
        },
        "borrow_rate_used": float(borrow_rate)
    }
    
    return result


def compare_calculations(
    system_calculation: Dict[str, Any],
    reference_calculation: Dict[str, Any]
) -> Tuple[bool, Dict[str, Any]]:
    """
    Compares system calculation with reference calculation.
    
    Args:
        system_calculation: Calculation result from the system
        reference_calculation: Reference calculation result
        
    Returns:
        Tuple of (match status, detailed comparison)
    """
    # Validate structure of both calculations
    validate_calculation_structure(system_calculation)
    validate_calculation_structure(reference_calculation)
    
    # Extract values for comparison
    sys_total = Decimal(str(system_calculation["total_fee"]))
    ref_total = Decimal(str(reference_calculation["total_fee"]))
    
    sys_rate = Decimal(str(system_calculation["borrow_rate_used"]))
    ref_rate = Decimal(str(reference_calculation["borrow_rate_used"]))
    
    sys_breakdown = system_calculation["breakdown"]
    ref_breakdown = reference_calculation["breakdown"]
    
    # Compare all components
    total_match = abs(sys_total - ref_total) <= CALCULATION_PRECISION_TOLERANCE
    rate_match = abs(sys_rate - ref_rate) <= CALCULATION_PRECISION_TOLERANCE
    
    breakdown_matches = {}
    overall_breakdown_match = True
    
    for field in REQUIRED_BREAKDOWN_FIELDS:
        sys_value = Decimal(str(sys_breakdown[field]))
        ref_value = Decimal(str(ref_breakdown[field]))
        field_match = abs(sys_value - ref_value) <= CALCULATION_PRECISION_TOLERANCE
        breakdown_matches[field] = field_match
        overall_breakdown_match = overall_breakdown_match and field_match
    
    # Overall match status
    overall_match = total_match and rate_match and overall_breakdown_match
    
    # Create detailed comparison result
    comparison_result = {
        "match": overall_match,
        "total_fee": {
            "match": total_match,
            "system": float(sys_total),
            "reference": float(ref_total),
            "difference": float(abs(sys_total - ref_total))
        },
        "borrow_rate": {
            "match": rate_match,
            "system": float(sys_rate),
            "reference": float(ref_rate),
            "difference": float(abs(sys_rate - ref_rate))
        },
        "breakdown": {
            "match": overall_breakdown_match,
            "components": {}
        }
    }
    
    # Add breakdown component comparisons
    for field in REQUIRED_BREAKDOWN_FIELDS:
        sys_value = Decimal(str(sys_breakdown[field]))
        ref_value = Decimal(str(ref_breakdown[field]))
        difference = abs(sys_value - ref_value)
        
        comparison_result["breakdown"]["components"][field] = {
            "match": breakdown_matches[field],
            "system": float(sys_value),
            "reference": float(ref_value),
            "difference": float(difference)
        }
    
    return overall_match, comparison_result


class CalculationValidator:
    """
    Helper class for validating calculations against compliance requirements.
    """
    
    def __init__(self):
        """
        Initialize the calculation validator.
        """
        self._validation_results = {}
        self._logger = logging.getLogger(__name__)
    
    def validate_calculation(self, calculation_result: Dict[str, Any]) -> bool:
        """
        Performs comprehensive validation of a calculation result.
        
        Args:
            calculation_result: The calculation result to validate
            
        Returns:
            True if calculation is valid, False otherwise
        """
        self._validation_results = {
            "structure_valid": False,
            "breakdown_valid": False,
            "non_negative_values": False,
            "overall_valid": False,
            "details": {}
        }
        
        try:
            # Validate structure
            validate_calculation_structure(calculation_result)
            self._validation_results["structure_valid"] = True
            
            # Validate fee breakdown
            validate_fee_breakdown(calculation_result)
            self._validation_results["breakdown_valid"] = True
            
            # Validate non-negative values
            total_fee = Decimal(str(calculation_result["total_fee"]))
            borrow_rate = Decimal(str(calculation_result["borrow_rate_used"]))
            breakdown = calculation_result["breakdown"]
            
            non_negative = (
                total_fee >= 0 and
                borrow_rate >= 0 and
                Decimal(str(breakdown["borrow_cost"])) >= 0 and
                Decimal(str(breakdown["markup"])) >= 0 and
                Decimal(str(breakdown["transaction_fees"])) >= 0
            )
            
            self._validation_results["non_negative_values"] = non_negative
            
            # Overall validation
            self._validation_results["overall_valid"] = (
                self._validation_results["structure_valid"] and
                self._validation_results["breakdown_valid"] and
                self._validation_results["non_negative_values"]
            )
            
            return self._validation_results["overall_valid"]
            
        except AssertionError as e:
            self._logger.error(f"Validation error: {str(e)}")
            self._validation_results["details"]["error"] = str(e)
            return False
        except Exception as e:
            self._logger.error(f"Unexpected error during validation: {str(e)}")
            self._validation_results["details"]["error"] = f"Unexpected error: {str(e)}"
            return False
    
    def validate_against_reference(
        self,
        system_calculation: Dict[str, Any],
        reference_calculation: Dict[str, Any]
    ) -> bool:
        """
        Validates a system calculation against a reference calculation.
        
        Args:
            system_calculation: The system calculation to validate
            reference_calculation: The reference calculation to compare against
            
        Returns:
            True if calculations match, False otherwise
        """
        try:
            match, comparison = compare_calculations(system_calculation, reference_calculation)
            self._validation_results = {
                "matches_reference": match,
                "comparison": comparison
            }
            return match
        except Exception as e:
            self._logger.error(f"Error comparing calculations: {str(e)}")
            self._validation_results = {
                "matches_reference": False,
                "error": str(e)
            }
            return False
    
    def validate_with_parameters(
        self,
        system_calculation: Dict[str, Any],
        ticker: str,
        position_value: Decimal,
        loan_days: int,
        borrow_rate: Decimal,
        markup_percentage: Decimal,
        fee_type: TransactionFeeType,
        fee_amount: Decimal
    ) -> bool:
        """
        Validates a calculation by generating a reference calculation from parameters.
        
        Args:
            system_calculation: The system calculation to validate
            ticker: Stock symbol
            position_value: Position value
            loan_days: Loan duration in days
            borrow_rate: Borrow rate
            markup_percentage: Broker markup percentage
            fee_type: Transaction fee type
            fee_amount: Transaction fee amount
            
        Returns:
            True if calculation matches reference, False otherwise
        """
        try:
            # Generate reference calculation
            reference = generate_reference_calculation(
                ticker,
                position_value,
                loan_days,
                borrow_rate,
                markup_percentage,
                fee_type,
                fee_amount
            )
            
            # Compare with system calculation
            return self.validate_against_reference(system_calculation, reference)
        except Exception as e:
            self._logger.error(f"Error validating with parameters: {str(e)}")
            self._validation_results = {
                "matches_reference": False,
                "error": str(e)
            }
            return False
    
    def validate_precision(self, calculation_result: Dict[str, Any], required_precision: int) -> bool:
        """
        Validates that a calculation maintains required decimal precision.
        
        Args:
            calculation_result: The calculation result to validate
            required_precision: The required decimal precision
            
        Returns:
            True if precision requirements are met, False otherwise
        """
        self._validation_results = {
            "precision_valid": False,
            "details": {}
        }
        
        try:
            # Check total_fee precision
            total_fee_str = str(calculation_result["total_fee"])
            if '.' in total_fee_str:
                decimal_places = len(total_fee_str.split('.')[1])
                total_fee_precision_valid = decimal_places >= required_precision
            else:
                total_fee_precision_valid = True  # Integer values have 0 decimal places
                
            # Check borrow_rate_used precision
            rate_str = str(calculation_result["borrow_rate_used"])
            if '.' in rate_str:
                decimal_places = len(rate_str.split('.')[1])
                rate_precision_valid = decimal_places >= required_precision
            else:
                rate_precision_valid = True
                
            # Check breakdown components precision
            breakdown = calculation_result["breakdown"]
            breakdown_precision_valid = True
            
            for field in REQUIRED_BREAKDOWN_FIELDS:
                field_str = str(breakdown[field])
                if '.' in field_str:
                    decimal_places = len(field_str.split('.')[1])
                    field_precision_valid = decimal_places >= required_precision
                else:
                    field_precision_valid = True
                    
                breakdown_precision_valid = breakdown_precision_valid and field_precision_valid
                self._validation_results["details"][f"{field}_precision"] = field_precision_valid
            
            # Overall precision validation
            self._validation_results["total_fee_precision"] = total_fee_precision_valid
            self._validation_results["rate_precision"] = rate_precision_valid
            self._validation_results["breakdown_precision"] = breakdown_precision_valid
            
            self._validation_results["precision_valid"] = (
                total_fee_precision_valid and
                rate_precision_valid and
                breakdown_precision_valid
            )
            
            return self._validation_results["precision_valid"]
            
        except Exception as e:
            self._logger.error(f"Error validating precision: {str(e)}")
            self._validation_results["details"]["error"] = str(e)
            return False
    
    def get_validation_results(self) -> Dict[str, Any]:
        """
        Returns the detailed results of the last validation.
        
        Returns:
            Detailed validation results
        """
        return self._validation_results