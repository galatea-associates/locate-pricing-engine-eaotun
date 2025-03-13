"""
Utility module providing timing-related functionality for the Borrow Rate & Locate Fee Pricing Engine.

This module includes decorators for measuring function execution time, context managers for
implementing timeouts, and utility classes for precise time measurement. These tools are 
essential for performance monitoring, implementing timeouts for external API calls, and
ensuring the system meets its performance requirements.
"""
import time
import functools
import asyncio
import logging
import typing
from typing import Any, Callable, TypeVar, cast, Optional, Union
import contextlib
import signal

# Type variables for decorator typing
F = TypeVar('F', bound=Callable[..., Any])
AsyncF = TypeVar('AsyncF', bound=Callable[..., Any])

# Set up logger
logger = logging.getLogger(__name__)

# Default timeout in seconds
DEFAULT_TIMEOUT = 30.0


def get_current_time_ms() -> float:
    """
    Returns the current time in milliseconds.
    
    Returns:
        float: Current time in milliseconds
    """
    return time.time() * 1000


def timed(logger: Optional[logging.Logger] = None) -> Callable[[F], F]:
    """
    Decorator that measures and logs the execution time of a function.
    
    Args:
        logger: Logger to use for logging. If None, uses module logger.
        
    Returns:
        Callable: Decorated function
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            elapsed_time = (end_time - start_time) * 1000  # Convert to ms
            logger.debug(f"{func.__name__} executed in {elapsed_time:.2f} ms")
            return result
        return cast(F, wrapper)
    return decorator


def async_timed(logger: Optional[logging.Logger] = None) -> Callable[[AsyncF], AsyncF]:
    """
    Decorator that measures and logs the execution time of an async function.
    
    Args:
        logger: Logger to use for logging. If None, uses module logger.
        
    Returns:
        Callable: Decorated async function
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    def decorator(func: AsyncF) -> AsyncF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            result = await func(*args, **kwargs)
            end_time = time.perf_counter()
            elapsed_time = (end_time - start_time) * 1000  # Convert to ms
            logger.debug(f"{func.__name__} executed in {elapsed_time:.2f} ms")
            return result
        return cast(AsyncF, wrapper)
    return decorator


class TimeoutError(Exception):
    """Custom exception raised when a timeout occurs."""
    
    def __init__(self, message: str) -> None:
        """
        Initialize the timeout error.
        
        Args:
            message: Error message
        """
        super().__init__(message)


class Timeout:
    """Context manager for applying timeout to synchronous code blocks."""
    
    def __init__(self, seconds: float) -> None:
        """
        Initialize the timeout context manager.
        
        Args:
            seconds: Timeout duration in seconds.
        """
        self.seconds = seconds
        self.original_handler = None
        
    def _timeout_handler(self, signum: int, frame: Any) -> None:
        """
        Signal handler for timeout.
        
        Args:
            signum: Signal number
            frame: Current stack frame
            
        Raises:
            TimeoutError: When timeout occurs
        """
        raise TimeoutError(f"Operation timed out after {self.seconds} seconds")
        
    def __enter__(self) -> 'Timeout':
        """
        Enter the timeout context.
        
        Returns:
            Timeout: Self reference for context manager
        """
        self.original_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, self._timeout_handler)
        signal.alarm(int(self.seconds))
        return self
        
    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], 
                 exc_tb: Optional[Any]) -> bool:
        """
        Exit the timeout context.
        
        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
            
        Returns:
            bool: False to propagate exceptions
        """
        signal.alarm(0)
        signal.signal(signal.SIGALRM, self.original_handler)
        return False  # Propagate exceptions


class AsyncTimeout:
    """Context manager for applying timeout to asynchronous code blocks."""
    
    def __init__(self, seconds: float) -> None:
        """
        Initialize the async timeout context manager.
        
        Args:
            seconds: Timeout duration in seconds.
        """
        self.seconds = seconds
        
    async def __aenter__(self) -> 'AsyncTimeout':
        """
        Enter the async timeout context.
        
        Returns:
            AsyncTimeout: Self reference for context manager
        """
        return self
        
    async def __aexit__(self, exc_type: Optional[type], exc_val: Optional[Exception],
                        exc_tb: Optional[Any]) -> bool:
        """
        Exit the async timeout context.
        
        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
            
        Returns:
            bool: False to propagate exceptions
        """
        return False  # Propagate exceptions


def with_timeout(seconds: float = DEFAULT_TIMEOUT) -> Callable[[F], F]:
    """
    Decorator that applies a timeout to a function execution.
    
    Args:
        seconds: Timeout duration in seconds.
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                with Timeout(seconds):
                    return func(*args, **kwargs)
            except TimeoutError as e:
                logger.error(f"Function {func.__name__} timed out after {seconds} seconds")
                raise
        return cast(F, wrapper)
    return decorator


def async_with_timeout(seconds: float = DEFAULT_TIMEOUT) -> Callable[[AsyncF], AsyncF]:
    """
    Decorator that applies a timeout to an async function execution.
    
    Args:
        seconds: Timeout duration in seconds.
        
    Returns:
        Callable: Decorated async function
    """
    def decorator(func: AsyncF) -> AsyncF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.error(f"Async function {func.__name__} timed out after {seconds} seconds")
                raise TimeoutError(f"Async operation timed out after {seconds} seconds")
        return cast(AsyncF, wrapper)
    return decorator


class Timer:
    """Class for measuring elapsed time with millisecond precision."""
    
    def __init__(self) -> None:
        """Initialize the timer in a stopped state."""
        self._start_time: Optional[float] = None
        self._stop_time: Optional[float] = None
        self._running: bool = False
        
    def start(self) -> None:
        """
        Start the timer.
        
        Returns:
            None
        """
        if self._running:
            logger.warning("Timer already running")
            return
            
        self._start_time = time.perf_counter()
        self._stop_time = None
        self._running = True
        
    def stop(self) -> float:
        """
        Stop the timer.
        
        Returns:
            float: Elapsed time in seconds
        """
        if not self._running:
            logger.warning("Timer not running")
            return 0.0
            
        self._stop_time = time.perf_counter()
        self._running = False
        return self._stop_time - self._start_time  # type: ignore
        
    def reset(self) -> None:
        """
        Reset the timer to initial state.
        
        Returns:
            None
        """
        self._start_time = None
        self._stop_time = None
        self._running = False
        
    def elapsed(self) -> float:
        """
        Get the elapsed time in seconds.
        
        Returns:
            float: Elapsed time in seconds
        """
        if self._running and self._start_time is not None:
            # Timer is still running
            return time.perf_counter() - self._start_time
        elif self._start_time is not None and self._stop_time is not None:
            # Timer was stopped
            return self._stop_time - self._start_time
        else:
            # Timer was never started
            return 0.0
            
    def elapsed_ms(self) -> float:
        """
        Get the elapsed time in milliseconds.
        
        Returns:
            float: Elapsed time in milliseconds
        """
        return self.elapsed() * 1000