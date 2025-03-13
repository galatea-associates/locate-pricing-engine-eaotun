import pytest
import time
import asyncio
from ../../utils/circuit_breaker import (
    circuit_breaker, async_circuit_breaker, 
    reset_circuit, get_all_circuit_states
)
from ../../core/exceptions import ExternalAPIException

def test_circuit_breaker_closed_state():
    # Define a test service name
    service_name = "test_service_closed"
    
    # Reset the circuit to ensure clean state
    reset_circuit(service_name)
    
    # Define a test function decorated with circuit_breaker
    @circuit_breaker(service_name)
    def test_function():
        return "success"
    
    # Call the function and verify it executes successfully
    assert test_function() == "success"
    
    # Get circuit state to verify it's still CLOSED
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["state"] == "CLOSED"
    
    # Verify that the failure count is zero
    assert circuit_states[service_name]["failure_count"] == 0

def test_circuit_breaker_open_state():
    # Define a test service name
    service_name = "test_service_open"
    
    # Reset the circuit to ensure clean state
    reset_circuit(service_name)
    
    # Define a test function that raises an exception, decorated with circuit_breaker
    @circuit_breaker(service_name, failure_threshold=3)
    def failing_function():
        raise ValueError("Simulated failure")
    
    # Call the function multiple times to exceed the failure threshold
    for _ in range(3):
        try:
            failing_function()
        except ValueError:
            pass  # Expected exception
    
    # Verify that the circuit state transitions to OPEN
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["state"] == "OPEN"
    
    # Verify that subsequent calls raise ExternalAPIException without calling the function
    with pytest.raises(ExternalAPIException):
        failing_function()

def test_circuit_breaker_half_open_state():
    # Define a test service name
    service_name = "test_service_half_open"
    
    # Reset the circuit to ensure clean state
    reset_circuit(service_name)
    
    # Define a test function that raises an exception, decorated with circuit_breaker
    @circuit_breaker(service_name, failure_threshold=3, timeout_seconds=5)
    def failing_function():
        raise ValueError("Simulated failure")
    
    # Call the function multiple times to transition to OPEN state
    for _ in range(3):
        try:
            failing_function()
        except ValueError:
            pass  # Expected exception
    
    # Verify that the circuit is OPEN
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["state"] == "OPEN"
    
    # Modify the circuit's open_time to simulate timeout period elapsed
    circuit_states[service_name]["open_time"] = time.time() - 6  # 6 seconds ago
    
    # Call the function again and verify it attempts to execute (HALF_OPEN state)
    try:
        failing_function()
    except ValueError:
        pass  # Expected exception
    
    # Verify that the circuit state is now HALF_OPEN
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["state"] == "HALF_OPEN"

def test_circuit_breaker_recovery():
    # Define a test service name
    service_name = "test_service_recovery"
    
    # Reset the circuit to ensure clean state
    reset_circuit(service_name)
    
    # Define a counter to control the function's behavior
    failure_count = 0
    
    # Define a test function that initially fails but then succeeds
    @circuit_breaker(service_name, failure_threshold=3, timeout_seconds=5, success_threshold=2)
    def test_function():
        nonlocal failure_count
        if failure_count < 3:
            failure_count += 1
            raise ValueError("Simulated failure")
        return "success"
    
    # Call the function multiple times to transition to OPEN state
    for _ in range(3):
        try:
            test_function()
        except ValueError:
            pass  # Expected exception
    
    # Verify that the circuit is OPEN
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["state"] == "OPEN"
    
    # Modify the circuit's open_time to simulate timeout period elapsed
    circuit_states[service_name]["open_time"] = time.time() - 6  # 6 seconds ago
    
    # Call the function twice (meeting success threshold) to transition to CLOSED
    result1 = test_function()
    result2 = test_function()
    
    # Verify results
    assert result1 == "success"
    assert result2 == "success"
    
    # Verify that the circuit state transitions back to CLOSED
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["state"] == "CLOSED"
    
    # Verify that subsequent calls execute normally
    assert test_function() == "success"

def test_circuit_breaker_fallback():
    # Define a test service name
    service_name = "test_service_fallback"
    
    # Reset the circuit to ensure clean state
    reset_circuit(service_name)
    
    # Define a test function with a fallback value, decorated with circuit_breaker
    @circuit_breaker(service_name, failure_threshold=3, fallback_value="fallback")
    def failing_function():
        raise ValueError("Simulated failure")
    
    # Call the function multiple times to transition to OPEN state
    for _ in range(3):
        try:
            failing_function()
        except ValueError:
            pass  # Expected exception
    
    # Verify that the circuit is OPEN
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["state"] == "OPEN"
    
    # Verify that subsequent calls return the fallback value instead of raising an exception
    assert failing_function() == "fallback"

@pytest.mark.asyncio
async def test_async_circuit_breaker():
    # Define a test service name
    service_name = "test_service_async"
    
    # Reset the circuit to ensure clean state
    reset_circuit(service_name)
    
    # Define an async test function decorated with async_circuit_breaker
    @async_circuit_breaker(service_name)
    async def test_async_function():
        await asyncio.sleep(0.1)
        return "async success"
    
    # Call the function and verify it executes successfully
    result = await test_async_function()
    assert result == "async success"
    
    # Define an async function that raises an exception
    @async_circuit_breaker(service_name, failure_threshold=3)
    async def failing_async_function():
        await asyncio.sleep(0.1)
        raise ValueError("Simulated async failure")
    
    # Call the function multiple times to transition to OPEN state
    for _ in range(3):
        try:
            await failing_async_function()
        except ValueError:
            pass  # Expected exception
    
    # Verify that the circuit is OPEN
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["state"] == "OPEN"
    
    # Verify that subsequent calls raise ExternalAPIException
    with pytest.raises(ExternalAPIException):
        await failing_async_function()

def test_reset_circuit():
    # Define a test service name
    service_name = "test_service_reset"
    
    # Define a test function that raises an exception, decorated with circuit_breaker
    @circuit_breaker(service_name, failure_threshold=3)
    def failing_function():
        raise ValueError("Simulated failure")
    
    # Call the function multiple times to transition to OPEN state
    for _ in range(3):
        try:
            failing_function()
        except ValueError:
            pass  # Expected exception
    
    # Verify that the circuit is OPEN
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["state"] == "OPEN"
    
    # Call reset_circuit to reset the circuit state
    reset_circuit(service_name)
    
    # Verify that the circuit is now CLOSED with reset counters
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["state"] == "CLOSED"
    assert circuit_states[service_name]["failure_count"] == 0
    
    # Verify that the function can be called again
    try:
        failing_function()
    except ValueError:
        pass  # Expected exception
    
    # Verify that the failure count was incremented
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["failure_count"] == 1

def test_get_all_circuit_states():
    # Define multiple test service names
    service1 = "test_service_get_all_1"
    service2 = "test_service_get_all_2"
    
    # Reset all circuits to ensure clean state
    reset_circuit(service1)
    reset_circuit(service2)
    
    # Create test functions for each service with different circuit_breaker configurations
    @circuit_breaker(service1, failure_threshold=3)
    def service1_function():
        raise ValueError("Simulated failure")
    
    @circuit_breaker(service2, failure_threshold=5)
    def service2_function():
        return "success"
    
    # Call service1_function to create OPEN state
    for _ in range(3):
        try:
            service1_function()
        except ValueError:
            pass  # Expected exception
    
    # Call service2_function to keep it in CLOSED state
    assert service2_function() == "success"
    
    # Call get_all_circuit_states to retrieve all circuit states
    circuit_states = get_all_circuit_states()
    
    # Verify that the returned dictionary contains both services with correct states
    assert service1 in circuit_states
    assert service2 in circuit_states
    assert circuit_states[service1]["state"] == "OPEN"
    assert circuit_states[service2]["state"] == "CLOSED"

def test_circuit_breaker_different_services():
    # Define two different test service names
    service1 = "test_service_diff_1"
    service2 = "test_service_diff_2"
    
    # Reset all circuits to ensure clean state
    reset_circuit(service1)
    reset_circuit(service2)
    
    # Define test functions for each service decorated with circuit_breaker
    @circuit_breaker(service1, failure_threshold=3)
    def service1_function():
        raise ValueError("Service 1 failure")
    
    @circuit_breaker(service2, failure_threshold=3)
    def service2_function():
        return "service 2 success"
    
    # Make service1 fail and transition to OPEN state
    for _ in range(3):
        try:
            service1_function()
        except ValueError:
            pass  # Expected exception
    
    # Verify that service1 is OPEN but service2 remains CLOSED
    circuit_states = get_all_circuit_states()
    assert circuit_states[service1]["state"] == "OPEN"
    assert circuit_states[service2]["state"] == "CLOSED"
    
    # Verify that calls to service1 fail while calls to service2 succeed
    with pytest.raises(ExternalAPIException):
        service1_function()
    
    assert service2_function() == "service 2 success"

def test_circuit_breaker_custom_thresholds():
    # Define a test service name
    service_name = "test_service_custom_thresholds"
    
    # Reset the circuit to ensure clean state
    reset_circuit(service_name)
    
    # Custom threshold values
    custom_failure_threshold = 2
    custom_timeout_seconds = 4
    custom_success_threshold = 3
    
    # Define a counter to control the function's behavior
    failure_count = 0
    
    # Define a test function with custom thresholds
    @circuit_breaker(
        service_name,
        failure_threshold=custom_failure_threshold,
        timeout_seconds=custom_timeout_seconds,
        success_threshold=custom_success_threshold
    )
    def test_function():
        nonlocal failure_count
        if failure_count < custom_failure_threshold:
            failure_count += 1
            raise ValueError("Simulated failure")
        return "success"
    
    # Verify that the circuit requires exactly custom_failure_threshold failures to open
    try:
        test_function()
    except ValueError:
        pass  # Expected exception
    
    # Check circuit is still closed after n-1 failures
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["state"] == "CLOSED"
    
    # One more failure should open the circuit
    try:
        test_function()
    except ValueError:
        pass  # Expected exception
    
    # Check circuit is now open
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["state"] == "OPEN"
    
    # Modify the circuit's open_time to simulate timeout period elapsed
    circuit_states[service_name]["open_time"] = time.time() - (custom_timeout_seconds + 1)
    
    # Call the function again to transition to HALF_OPEN
    failure_count = custom_failure_threshold  # Make it succeed now
    result = test_function()
    assert result == "success"
    
    # Verify circuit is HALF_OPEN
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["state"] == "HALF_OPEN"
    
    # Verify that the circuit requires exactly custom_success_threshold successes to close
    for _ in range(custom_success_threshold - 1):
        test_function()
    
    # Should still be HALF_OPEN after n-1 successes
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["state"] == "HALF_OPEN"
    
    # One more success should close the circuit
    test_function()
    
    # Should now be CLOSED
    circuit_states = get_all_circuit_states()
    assert circuit_states[service_name]["state"] == "CLOSED"