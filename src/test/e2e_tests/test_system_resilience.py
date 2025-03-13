"""
End-to-end tests for system resilience features of the Borrow Rate & Locate Fee Pricing Engine.
Tests fallback mechanisms, error handling, recovery procedures, and system behavior under
various failure scenarios.
"""

import pytest
import requests
import time
import logging
import json
from typing import Dict, Any, Optional, Union, List

from .helpers.api_client import APIClient, create_api_client
from .helpers.validation import ResponseValidator, create_response_validator
from .config.settings import get_test_settings

# Configure logger
logger = logging.getLogger(__name__)

# Constants
MOCK_SERVER_TIMEOUT = 30  # Timeout for mock server operations in seconds

def setup_mock_server_state(server_name: str, state: str, config: dict) -> bool:
    """
    Sets up the mock server state for a specific test scenario
    
    Args:
        server_name: Name of the mock server ('seclend', 'market', or 'event')
        state: Desired server state ('error', 'timeout', 'partial_failure', etc.)
        config: Configuration parameters for the state
        
    Returns:
        True if setup was successful, False otherwise
    """
    settings = get_test_settings()
    
    try:
        # Construct the admin endpoint URL
        server_url = settings.get_mock_server_url(server_name)
        admin_url = f"{server_url}/admin/state/{state}"
        
        # Send request to set server state
        response = requests.post(
            admin_url,
            json=config,
            timeout=MOCK_SERVER_TIMEOUT
        )
        
        success = response.status_code == 200
        if success:
            logger.info(f"Successfully set {server_name} mock server to '{state}' state")
        else:
            logger.error(f"Failed to set {server_name} mock server state: {response.status_code} - {response.text}")
        
        return success
    except Exception as e:
        logger.error(f"Error setting {server_name} mock server state: {str(e)}")
        return False

def reset_mock_servers() -> bool:
    """
    Resets all mock servers to their default state
    
    Returns:
        True if reset was successful, False otherwise
    """
    settings = get_test_settings()
    server_names = ['seclend', 'market', 'event']
    success = True
    
    for server_name in server_names:
        try:
            server_url = settings.get_mock_server_url(server_name)
            reset_url = f"{server_url}/admin/reset"
            
            response = requests.post(
                reset_url,
                timeout=MOCK_SERVER_TIMEOUT
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to reset {server_name} mock server: {response.status_code} - {response.text}")
                success = False
        except Exception as e:
            logger.error(f"Error resetting {server_name} mock server: {str(e)}")
            success = False
    
    if success:
        logger.info("Successfully reset all mock servers")
    
    return success

class TestSystemResilience:
    """
    Test suite for system resilience features of the Borrow Rate & Locate Fee Pricing Engine
    """
    
    @classmethod
    def setup_class(cls):
        """Set up test class - runs once before all tests in the class"""
        cls.api_client = create_api_client()
        cls.validator = create_response_validator()
        
        # Wait for API to be ready
        cls.api_client.wait_for_api_ready()
        
        # Reset mock servers to default state
        reset_mock_servers()
        
        logger.info("TestSystemResilience setup completed")
    
    @classmethod
    def teardown_class(cls):
        """Tear down test class - runs once after all tests in the class"""
        # Reset mock servers to default state
        reset_mock_servers()
        
        logger.info("TestSystemResilience teardown completed")
    
    def setup_method(self, method):
        """Set up method - runs before each test method"""
        # Reset mock servers to default state before each test
        reset_mock_servers()
        
        logger.info(f"Starting test: {method.__name__}")
    
    def teardown_method(self, method):
        """Tear down method - runs after each test method"""
        # Reset mock servers to default state after each test
        reset_mock_servers()
        
        logger.info(f"Completed test: {method.__name__}")
    
    def test_seclend_api_fallback(self):
        """Tests the fallback mechanism when SecLend API is unavailable"""
        # Configure SecLend API mock to return errors
        setup_mock_server_state('seclend', 'error', {'error_code': 500, 'probability': 1.0})
        
        # Attempt to get borrow rate
        ticker = 'AAPL'
        response = self.api_client.get_borrow_rate(ticker)
        
        # Verify that we get a fallback rate
        self.validator.assert_response_status(response, 'success')
        assert response.current_rate is not None, "Expected a fallback rate, got None"
        assert response.borrow_status == 'HARD', f"Expected borrow status to be 'HARD' for fallback, got: {response.borrow_status}"
        
        # Verify that we can still calculate fees
        calc_response = self.api_client.calculate_locate_fee(
            ticker=ticker,
            position_value=100000,
            loan_days=30,
            client_id='broker1'
        )
        
        self.validator.assert_response_status(calc_response, 'success')
        
        # Reset mock server and verify normal operation
        reset_mock_servers()
        
        normal_response = self.api_client.get_borrow_rate(ticker)
        self.validator.assert_response_status(normal_response, 'success')
        assert normal_response.current_rate != response.current_rate, "Expected different rate after reset"
    
    def test_market_api_fallback(self):
        """Tests the fallback mechanism when Market Volatility API is unavailable"""
        # Configure Market API mock to return errors
        setup_mock_server_state('market', 'error', {'error_code': 500, 'probability': 1.0})
        
        # Attempt to get borrow rate
        ticker = 'TSLA'
        response = self.api_client.get_borrow_rate(ticker)
        
        # Verify that we get a response without volatility adjustment
        self.validator.assert_response_status(response, 'success')
        assert response.volatility_index is None, f"Expected volatility_index to be None, got: {response.volatility_index}"
        
        # Verify that we can still calculate fees
        calc_response = self.api_client.calculate_locate_fee(
            ticker=ticker,
            position_value=75000,
            loan_days=14,
            client_id='broker3'
        )
        
        self.validator.assert_response_status(calc_response, 'success')
        
        # Reset mock server and verify normal operation
        reset_mock_servers()
        
        normal_response = self.api_client.get_borrow_rate(ticker)
        self.validator.assert_response_status(normal_response, 'success')
        assert normal_response.volatility_index is not None, "Expected volatility_index after reset"
    
    def test_event_api_fallback(self):
        """Tests the fallback mechanism when Event Calendar API is unavailable"""
        # Configure Event API mock to return errors
        setup_mock_server_state('event', 'error', {'error_code': 500, 'probability': 1.0})
        
        # Attempt to get borrow rate for a ticker with known events
        ticker = 'GME'
        response = self.api_client.get_borrow_rate(ticker)
        
        # Verify that we get a response without event risk adjustment
        self.validator.assert_response_status(response, 'success')
        assert response.event_risk_factor is None, f"Expected event_risk_factor to be None, got: {response.event_risk_factor}"
        
        # Verify that we can still calculate fees
        calc_response = self.api_client.calculate_locate_fee(
            ticker=ticker,
            position_value=50000,
            loan_days=7,
            client_id='broker2'
        )
        
        self.validator.assert_response_status(calc_response, 'success')
        
        # Reset mock server and verify normal operation
        reset_mock_servers()
        
        normal_response = self.api_client.get_borrow_rate(ticker)
        self.validator.assert_response_status(normal_response, 'success')
        assert normal_response.event_risk_factor is not None, "Expected event_risk_factor after reset"
    
    def test_api_timeout_recovery(self):
        """Tests the system's ability to recover from API timeouts"""
        # Configure SecLend API mock to timeout
        setup_mock_server_state('seclend', 'timeout', {'delay': 5000, 'probability': 1.0})  # 5 second delay
        
        # Attempt to get borrow rate
        ticker = 'MSFT'
        response = self.api_client.get_borrow_rate(ticker)
        
        # Verify that we get a fallback rate after timeout
        self.validator.assert_response_status(response, 'success')
        assert response.current_rate is not None, "Expected a fallback rate, got None"
        
        # Reset mock server and verify normal operation
        reset_mock_servers()
        
        normal_response = self.api_client.get_borrow_rate(ticker)
        self.validator.assert_response_status(normal_response, 'success')
    
    def test_multiple_api_failures(self):
        """Tests the system's resilience when multiple external APIs fail simultaneously"""
        # Configure all mock servers to return errors
        setup_mock_server_state('seclend', 'error', {'error_code': 500, 'probability': 1.0})
        setup_mock_server_state('market', 'error', {'error_code': 500, 'probability': 1.0})
        setup_mock_server_state('event', 'error', {'error_code': 500, 'probability': 1.0})
        
        # Attempt to get borrow rate
        ticker = 'AAPL'
        response = self.api_client.get_borrow_rate(ticker)
        
        # Verify that we get a fallback rate
        self.validator.assert_response_status(response, 'success')
        assert response.current_rate is not None, "Expected a fallback rate, got None"
        assert response.volatility_index is None, f"Expected volatility_index to be None, got: {response.volatility_index}"
        assert response.event_risk_factor is None, f"Expected event_risk_factor to be None, got: {response.event_risk_factor}"
        
        # Verify that we can still calculate fees
        calc_response = self.api_client.calculate_locate_fee(
            ticker=ticker,
            position_value=100000,
            loan_days=30,
            client_id='broker1'
        )
        
        self.validator.assert_response_status(calc_response, 'success')
        
        # Reset mock servers and verify normal operation
        reset_mock_servers()
        
        normal_response = self.api_client.get_borrow_rate(ticker)
        self.validator.assert_response_status(normal_response, 'success')
        assert normal_response.volatility_index is not None, "Expected volatility_index after reset"
        assert normal_response.event_risk_factor is not None, "Expected event_risk_factor after reset"
    
    def test_circuit_breaker_pattern(self):
        """Tests the circuit breaker pattern implementation for external API calls"""
        # Configure SecLend API mock to return errors for a series of requests
        setup_mock_server_state('seclend', 'error', {'error_code': 500, 'probability': 1.0})
        
        ticker = 'AAPL'
        
        # Make multiple requests to trigger the circuit breaker
        responses = []
        for i in range(5):  # Assuming failure threshold is <= 5
            response = self.api_client.get_borrow_rate(ticker)
            responses.append(response)
            time.sleep(0.5)  # Small delay between requests
        
        # Verify that all responses have fallback rates
        for i, response in enumerate(responses):
            self.validator.assert_response_status(response, 'success')
            assert response.current_rate is not None, f"Expected a fallback rate for request {i}, got None"
        
        # The circuit should now be open, further requests should use fallback immediately
        # Reset the mock server but the circuit breaker should still prevent real API calls
        reset_mock_servers()
        
        # Attempt another request while circuit is open
        circuit_open_response = self.api_client.get_borrow_rate(ticker)
        self.validator.assert_response_status(circuit_open_response, 'success')
        
        # Wait for circuit breaker timeout period (should be configured in the application)
        logger.info("Waiting for circuit breaker timeout period...")
        time.sleep(10)  # Assuming timeout period is less than 10 seconds
        
        # After timeout, system should try real API again
        recovery_response = self.api_client.get_borrow_rate(ticker)
        self.validator.assert_response_status(recovery_response, 'success')
        assert recovery_response.volatility_index is not None, "Expected volatility_index after circuit reset"
    
    def test_partial_calculation_failure(self):
        """Tests the system's ability to handle partial calculation failures"""
        # Configure a scenario where part of the calculation pipeline fails
        # For example, make SecLend API return valid data but with some fields missing
        setup_mock_server_state('seclend', 'partial_failure', {'fields': ['volatility'], 'probability': 1.0})
        
        # Attempt a calculation
        ticker = 'TSLA'
        calc_response = self.api_client.calculate_locate_fee(
            ticker=ticker,
            position_value=75000,
            loan_days=14,
            client_id='broker3'
        )
        
        # Verify that we get a valid response with partial results
        self.validator.assert_response_status(calc_response, 'success')
        
        # Reset mock server and verify normal operation
        reset_mock_servers()
        
        normal_response = self.api_client.calculate_locate_fee(
            ticker=ticker,
            position_value=75000,
            loan_days=14,
            client_id='broker3'
        )
        
        self.validator.assert_response_status(normal_response, 'success')
    
    def test_error_response_handling(self):
        """Tests the system's handling of various error responses from external APIs"""
        error_scenarios = [
            {'code': 400, 'name': 'bad_request'},
            {'code': 403, 'name': 'forbidden'},
            {'code': 404, 'name': 'not_found'},
            {'code': 500, 'name': 'server_error'}
        ]
        
        ticker = 'AAPL'
        
        for scenario in error_scenarios:
            # Configure SecLend API mock to return specific error
            setup_mock_server_state('seclend', 'error', {'error_code': scenario['code'], 'probability': 1.0})
            
            # Attempt to get borrow rate
            response = self.api_client.get_borrow_rate(ticker)
            
            # Verify proper fallback for each error type
            self.validator.assert_response_status(response, 'success')
            assert response.current_rate is not None, f"Expected a fallback rate for {scenario['name']}, got None"
            
            # Reset mock server after each scenario
            reset_mock_servers()
            
            # Verify normal operation
            normal_response = self.api_client.get_borrow_rate(ticker)
            self.validator.assert_response_status(normal_response, 'success')
    
    def test_retry_mechanism(self):
        """Tests the retry mechanism for transient API failures"""
        # Configure SecLend API to fail the first 2 attempts then succeed
        setup_mock_server_state('seclend', 'intermittent', {'fail_count': 2, 'probability': 1.0})
        
        ticker = 'MSFT'
        
        # This should retry and eventually succeed
        response = self.api_client.get_borrow_rate(ticker)
        
        # Verify that we get a successful response with real data
        self.validator.assert_response_status(response, 'success')
        assert response.current_rate is not None, "Expected a real rate after retries, got None"
        assert response.volatility_index is not None, "Expected volatility_index after retries"