"""
Initialization module for performance test fixtures that exports all fixtures from the fixtures package.
This module makes fixtures for test data, environment setup, and metrics collection available to 
performance tests without requiring direct imports from individual fixture modules.
"""

# Import test data fixtures
from .test_data import (
    test_stocks,
    test_brokers,
    test_calculations,
    normal_market_scenario,
    high_volatility_scenario,
    corporate_events_scenario,
    hard_to_borrow_scenario,
    market_disruption_scenario,
    generate_stock_data,
    generate_broker_data,
    generate_calculation_data,
    generate_market_scenario_data
)

# Import environment fixtures
from .environment import (
    performance_environment,
    api_client,
    metrics_collector,
    PerformanceEnvironment
)

# Export all fixtures
__all__ = [
    # Test data fixtures
    'test_stocks',
    'test_brokers',
    'test_calculations',
    'normal_market_scenario',
    'high_volatility_scenario',
    'corporate_events_scenario',
    'hard_to_borrow_scenario',
    'market_disruption_scenario',
    
    # Test data generation functions
    'generate_stock_data',
    'generate_broker_data',
    'generate_calculation_data',
    'generate_market_scenario_data',
    
    # Environment fixtures
    'performance_environment',
    'api_client',
    'metrics_collector',
    'PerformanceEnvironment'
]