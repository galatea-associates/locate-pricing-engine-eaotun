"""
Implements the Circuit Breaker pattern for the Borrow Rate & Locate Fee Pricing Engine to prevent cascading failures when external services are unavailable. This pattern helps maintain system stability by temporarily stopping requests to failing services and providing fallback mechanisms.
"""

import time
import functools
import asyncio
import threading
from typing import Callable, TypeVar, Any, Optional, Dict

from ..utils.logging import setup_logger
from ..core.exceptions import ExternalAPIException

# Set up logger
logger = setup_logger('circuit_breaker')

# Define type variable for generic function return type
T = TypeVar('T')

# Circuit states
CLOSED = "CLOSED"
OPEN = "OPEN"
HALF_OPEN = "HALF_OPEN"

# Global dictionary to store circuit states for different services
circuit_states: Dict[str, Dict[str, Any]] = {}

# Lock for thread safety
state_lock = threading.RLock()

def get_circuit_state(service_name: str) -> Dict[str, Any]:
    """
    Retrieves the current state of a circuit for a specific service.
    
    Args:
        service_name: The name of the service to get state for
        
    Returns:
        Dict[str, Any]: Current circuit state information
    """
    with state_lock:
        if service_name not in circuit_states:
            # Initialize with default state
            circuit_states[service_name] = {
                "state": CLOSED,
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": 0,
                "open_time": 0
            }
        return circuit_states[service_name]

def update_circuit_state(
    service_name: str,
    success: bool,
    failure_threshold: int,
    timeout_seconds: int,
    success_threshold: int
) -> str:
    """
    Updates the state of a circuit based on the result of an operation.
    
    Args:
        service_name: The name of the service
        success: Whether the operation was successful
        failure_threshold: Number of failures before opening the circuit
        timeout_seconds: Seconds to wait before transitioning to HALF_OPEN
        success_threshold: Number of successes needed to close circuit
    
    Returns:
        str: The new state of the circuit (CLOSED, OPEN, or HALF_OPEN)
    """
    with state_lock:
        circuit_state = get_circuit_state(service_name)
        current_state = circuit_state["state"]
        
        if success:
            # Handle successful operation
            if current_state == CLOSED:
                # Reset failure count on success in CLOSED state
                circuit_state["failure_count"] = 0
            elif current_state == HALF_OPEN:
                # Increment success count in HALF_OPEN state
                circuit_state["success_count"] += 1
                
                # If success threshold reached, close the circuit
                if circuit_state["success_count"] >= success_threshold:
                    old_state = circuit_state["state"]
                    circuit_state["state"] = CLOSED
                    circuit_state["success_count"] = 0
                    circuit_state["failure_count"] = 0
                    logger.info(f"Circuit for {service_name} transitioned from {old_state} to {CLOSED}")
        else:
            # Handle failed operation
            circuit_state["last_failure_time"] = time.time()
            
            if current_state == CLOSED:
                # Increment failure count
                circuit_state["failure_count"] += 1
                
                # If failure threshold reached, open the circuit
                if circuit_state["failure_count"] >= failure_threshold:
                    old_state = circuit_state["state"]
                    circuit_state["state"] = OPEN
                    circuit_state["open_time"] = time.time()
                    logger.warning(f"Circuit for {service_name} transitioned from {old_state} to {OPEN} after {failure_threshold} failures")
            
            elif current_state == HALF_OPEN:
                # Transition back to OPEN on failure in HALF_OPEN state
                old_state = circuit_state["state"]
                circuit_state["state"] = OPEN
                circuit_state["open_time"] = time.time()
                circuit_state["success_count"] = 0
                logger.warning(f"Circuit for {service_name} transitioned from {old_state} back to {OPEN} after failure in HALF_OPEN state")
        
        # Check if we should transition from OPEN to HALF_OPEN
        if current_state == OPEN:
            elapsed_time = time.time() - circuit_state["open_time"]
            if elapsed_time >= timeout_seconds:
                old_state = circuit_state["state"]
                circuit_state["state"] = HALF_OPEN
                circuit_state["success_count"] = 0
                logger.info(f"Circuit for {service_name} transitioned from {old_state} to {HALF_OPEN} after {elapsed_time:.2f} seconds")
        
        return circuit_state["state"]

def circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    timeout_seconds: int = 60,
    success_threshold: int = 3,
    fallback_value: Optional[Any] = None
) -> Callable:
    """
    Decorator that implements the circuit breaker pattern for synchronous functions.
    
    Args:
        service_name: The name of the service being called
        failure_threshold: Number of failures before opening the circuit
        timeout_seconds: Seconds to wait before transitioning to HALF_OPEN
        success_threshold: Number of successes needed to close circuit
        fallback_value: Value to return when circuit is open
    
    Returns:
        Callable: Decorator function that implements circuit breaker logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            circuit_state = get_circuit_state(service_name)
            
            # Check if circuit is open
            if circuit_state["state"] == OPEN:
                elapsed_time = time.time() - circuit_state["open_time"]
                if elapsed_time < timeout_seconds:
                    # Circuit is open and timeout hasn't elapsed, so short-circuit
                    logger.info(f"Circuit for {service_name} is OPEN - short-circuiting call to {func.__name__}")
                    if fallback_value is not None:
                        return fallback_value
                    else:
                        raise ExternalAPIException(service_name, "Circuit breaker is open")
            
            # Circuit is closed or half-open, proceed with the call
            try:
                result = func(*args, **kwargs)
                update_circuit_state(service_name, True, failure_threshold, timeout_seconds, success_threshold)
                return result
            except Exception as e:
                update_circuit_state(service_name, False, failure_threshold, timeout_seconds, success_threshold)
                logger.error(f"Error calling {service_name}.{func.__name__}: {str(e)}")
                
                if fallback_value is not None:
                    return fallback_value
                raise  # Re-raise the exception if no fallback
        
        return wrapper
    
    return decorator

def async_circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    timeout_seconds: int = 60,
    success_threshold: int = 3,
    fallback_value: Optional[Any] = None
) -> Callable:
    """
    Decorator that implements the circuit breaker pattern for asynchronous functions.
    
    Args:
        service_name: The name of the service being called
        failure_threshold: Number of failures before opening the circuit
        timeout_seconds: Seconds to wait before transitioning to HALF_OPEN
        success_threshold: Number of successes needed to close circuit
        fallback_value: Value to return when circuit is open
    
    Returns:
        Callable: Decorator function that implements async circuit breaker logic
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            circuit_state = get_circuit_state(service_name)
            
            # Check if circuit is open
            if circuit_state["state"] == OPEN:
                elapsed_time = time.time() - circuit_state["open_time"]
                if elapsed_time < timeout_seconds:
                    # Circuit is open and timeout hasn't elapsed, so short-circuit
                    logger.info(f"Circuit for {service_name} is OPEN - short-circuiting call to {func.__name__}")
                    if fallback_value is not None:
                        return fallback_value
                    else:
                        raise ExternalAPIException(service_name, "Circuit breaker is open")
            
            # Circuit is closed or half-open, proceed with the call
            try:
                result = await func(*args, **kwargs)
                update_circuit_state(service_name, True, failure_threshold, timeout_seconds, success_threshold)
                return result
            except Exception as e:
                update_circuit_state(service_name, False, failure_threshold, timeout_seconds, success_threshold)
                logger.error(f"Error calling {service_name}.{func.__name__}: {str(e)}")
                
                if fallback_value is not None:
                    return fallback_value
                raise  # Re-raise the exception if no fallback
        
        return wrapper
    
    return decorator

def reset_circuit(service_name: str) -> None:
    """
    Manually resets a circuit to the CLOSED state.
    
    Args:
        service_name: The name of the service to reset
    """
    with state_lock:
        if service_name in circuit_states:
            old_state = circuit_states[service_name]["state"]
            circuit_states[service_name] = {
                "state": CLOSED,
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": 0,
                "open_time": 0
            }
            logger.info(f"Circuit for {service_name} manually reset from {old_state} to {CLOSED}")

def get_all_circuit_states() -> Dict[str, Dict[str, Any]]:
    """
    Returns the current state of all circuits for monitoring purposes.
    
    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of all circuit states by service name
    """
    with state_lock:
        # Return a copy to avoid thread safety issues
        return {k: v.copy() for k, v in circuit_states.items()}