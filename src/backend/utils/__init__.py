"""
Utility package for the Borrow Rate & Locate Fee Pricing Engine.

This package provides a collection of utility functions and classes for common operations
used throughout the application. By importing directly from this package instead of
individual modules, code becomes more concise and dependencies are easier to manage.

The utilities include date/time operations, mathematical calculations, validation,
logging, retry mechanisms, circuit breakers, and performance timing tools.
"""

# Date utilities
from .date import (
    format_date,
    parse_date,
    calculate_date_diff,
    get_today,
    add_days,
    is_business_day,
    get_next_business_day,
    calculate_business_days
)

# Math utilities
from .math import (
    round_decimal,
    calculate_percentage,
    calculate_borrow_cost,
    apply_markup,
    calculate_transaction_fee,
    adjust_rate_for_volatility,
    adjust_rate_for_event_risk
)

# Validation utilities
from .validation import (
    validate_ticker,
    validate_position_value,
    validate_loan_days,
    validate_client_id,
    validate_borrow_rate,
    validate_calculation_parameters,
    ValidationError
)

# Logging utilities
from .logging import (
    setup_logger,
    log_execution_time,
    log_exceptions,
    log_api_call,
    log_fallback_usage,
    log_calculation,
    LoggingContext,
    PerformanceTimer
)

# Retry utilities
from .retry import (
    retry,
    retry_with_fallback,
    retry_async,
    retry_async_with_fallback
)

# Circuit breaker utilities
from .circuit_breaker import (
    CircuitBreakerState,
    CircuitBreaker,
    CircuitBreakerRegistry,
    circuit_breaker,
    async_circuit_breaker
)

# Timing utilities
from .timing import (
    timed,
    async_timed,
    with_timeout,
    async_with_timeout,
    Timer,
    Timeout,
    AsyncTimeout
)

# Define what should be available when using "from utils import *"
__all__ = [
    "format_date",
    "parse_date",
    "calculate_date_diff",
    "get_today",
    "add_days",
    "is_business_day",
    "get_next_business_day",
    "calculate_business_days",
    "round_decimal",
    "calculate_percentage",
    "calculate_borrow_cost",
    "apply_markup",
    "calculate_transaction_fee",
    "adjust_rate_for_volatility",
    "adjust_rate_for_event_risk",
    "validate_ticker",
    "validate_position_value",
    "validate_loan_days",
    "validate_client_id",
    "validate_borrow_rate",
    "validate_calculation_parameters",
    "ValidationError",
    "setup_logger",
    "log_execution_time",
    "log_exceptions",
    "log_api_call",
    "log_fallback_usage",
    "log_calculation",
    "LoggingContext",
    "PerformanceTimer",
    "retry",
    "retry_with_fallback",
    "retry_async",
    "retry_async_with_fallback",
    "CircuitBreakerState",
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "circuit_breaker",
    "async_circuit_breaker",
    "timed",
    "async_timed",
    "with_timeout",
    "async_with_timeout",
    "Timer",
    "Timeout",
    "AsyncTimeout"
]