"""
Initialization module for the data services test package in the Borrow Rate & Locate Fee Pricing Engine.

This module makes test modules discoverable by pytest and provides common imports and utilities
for testing data services. It addresses the following requirements:
- Real-Time Borrow Rate Calculation
- Client-Specific Fee Calculation
- Data Caching System
- Error Handling and Validation
- Fallback Mechanisms
"""
import pytest  # pytest 7.4.0+

# List of test modules in the data services test package
__all__ = ['test_stocks', 'test_brokers', 'test_volatility', 'test_audit']