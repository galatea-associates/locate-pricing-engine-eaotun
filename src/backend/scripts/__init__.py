#!/usr/bin/env python
"""
Initialization file for the scripts package in the Borrow Rate & Locate Fee Pricing Engine.

This file exposes key functions from the script modules to allow them to be imported directly
from the scripts package, facilitating both command-line usage and programmatic access to
utility scripts.
"""

__version__ = "1.0.0"

# Import API key generation functionality
from .generate_api_key import generate_api_key  # Import API key generation functionality

# Import system health check functionality
from .health_check import get_system_health  # Import system health check functionality

# Import stock data seeding functionality
from .seed_data import seed_stocks  # Import stock data seeding functionality

# Import broker data seeding functionality
from .seed_data import seed_brokers  # Import broker data seeding functionality

# Import volatility data seeding functionality
from .seed_data import seed_volatility  # Import volatility data seeding functionality

# Import borrow rate calculation benchmarking functionality
from .benchmark import benchmark_borrow_rate  # Import borrow rate calculation benchmarking functionality

# Import locate fee calculation benchmarking functionality
from .benchmark import benchmark_locate_fee  # Import locate fee calculation benchmarking functionality

# Import database migration functionality
from .run_migrations import run_migrations  # Import database migration functionality

# Expose API key generation function for programmatic use
__all__ = [
    "generate_api_key",  # Export API key generation function for programmatic use
    "get_system_health",  # Export system health check function for programmatic use
    "seed_stocks",  # Export stock data seeding function for programmatic use
    "seed_brokers",  # Export broker data seeding function for programmatic use
    "seed_volatility",  # Export volatility data seeding function for programmatic use
    "benchmark_borrow_rate",  # Export borrow rate benchmarking function for programmatic use
    "benchmark_locate_fee",  # Export locate fee benchmarking function for programmatic use
    "run_migrations",  # Export database migration function for programmatic use
]