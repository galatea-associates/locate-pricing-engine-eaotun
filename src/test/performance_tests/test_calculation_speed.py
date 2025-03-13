"""
Performance test module that measures and validates the calculation speed of the core calculation
services in the Borrow Rate & Locate Fee Pricing Engine. This module contains tests to ensure that
calculation functions meet the required performance thresholds under various load conditions and
market scenarios.
"""

import time  # standard library
import decimal  # standard library
import statistics  # standard library
from typing import Dict, List, Any  # standard library

import pytest  # pytest 7.4.0+

from src.test.performance_tests.config.settings import get_test_settings  # Import function to retrieve test settings with performance thresholds
from src.test.performance_tests.helpers.metrics_collector import get_calculation_metrics_collector  # Import function to get metrics collector for calculation performance
from src.test.performance_tests import metrics_collection  # Import context manager for metrics collection
from src.test.performance_tests import check_performance_thresholds  # Import function to validate metrics against performance thresholds
from src.test.performance_tests import analyze_performance_results  # Import function for analyzing performance test results
from src.test.performance_tests.fixtures.test_data import test_stocks  # Import fixture providing test stock data
from src.test.performance_tests.fixtures.test_data import test_brokers  # Import fixture providing test broker data
from src.test.performance_tests.fixtures.test_data import test_calculations  # Import fixture providing test calculation parameters
from src.test.performance_tests.fixtures.test_data import normal_market_scenario  # Import fixture providing normal market scenario test data
from src.test.performance_tests.fixtures.test_data import high_volatility_scenario  # Import fixture providing high volatility scenario test data
from src.backend.services.calculation.borrow_rate import calculate_borrow_rate  # Import function to calculate borrow rates for performance testing
from src.backend.services.calculation.locate_fee import calculate_locate_fee  # Import function to calculate locate fees for performance testing
from src.backend.core.constants import TransactionFeeType  # Import transaction fee type enumeration for test parameters

BORROW_RATE_THRESHOLD_MS = 50  # Define a global constant for the borrow rate threshold in milliseconds
LOCATE_FEE_THRESHOLD_MS = 30  # Define a global constant for the locate fee threshold in milliseconds
ITERATIONS_SMALL = 100  # Define a global constant for a small number of iterations
ITERATIONS_MEDIUM = 1000  # Define a global constant for a medium number of iterations
ITERATIONS_LARGE = 10000  # Define a global constant for a large number of iterations


def run_borrow_rate_calculation_test(ticker: str, min_rate: decimal.Decimal, use_cache: bool, iterations: int) -> Dict[str, Any]:
    """Runs a performance test for borrow rate calculation with the specified parameters

    Args:
        ticker (str): Stock ticker symbol
        min_rate (Decimal): Minimum borrow rate
        use_cache (bool): Whether to use cached data
        iterations (int): Number of iterations to run

    Returns:
        Dict: Dictionary containing performance metrics for the test run
    """
    metrics_collector = get_calculation_metrics_collector()  # Initialize metrics collector for calculation performance

    test_metadata = {
        "name": "borrow_rate_calculation",
        "ticker": ticker,
        "min_rate": str(min_rate),
        "use_cache": use_cache,
        "iterations": iterations
    }

    with metrics_collection(metrics_collector, test_metadata):  # Start metrics collection with test metadata
        for _ in range(iterations):  # Run the specified number of iterations of calculate_borrow_rate
            start_time = time.perf_counter()
            calculate_borrow_rate(ticker, min_rate=min_rate, use_cache=use_cache)
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
            metrics_collector.record_calculation("borrow_rate", execution_time)  # For each iteration, record calculation time using the metrics collector

    metrics = metrics_collector.stop_collection()  # Stop metrics collection and retrieve results

    execution_times = metrics["calculation"]["calculation_types"]["borrow_rate"]["execution_times"]
    statistics = calculate_statistics(execution_times)  # Calculate and add summary statistics (min, max, mean, median, p95, p99)
    metrics["calculation"]["calculation_types"]["borrow_rate"]["execution_times"] = statistics

    return metrics  # Return the metrics dictionary with all performance data


def run_locate_fee_calculation_test(ticker: str, position_value: decimal.Decimal, loan_days: int, markup_percentage: decimal.Decimal, fee_type: TransactionFeeType, fee_amount: decimal.Decimal, use_cache: bool, iterations: int) -> Dict[str, Any]:
    """Runs a performance test for locate fee calculation with the specified parameters

    Args:
        ticker (str): Stock ticker symbol
        position_value (Decimal): Position value
        loan_days (int): Loan duration in days
        markup_percentage (Decimal): Markup percentage
        fee_type (TransactionFeeType): Transaction fee type
        fee_amount (Decimal): Transaction fee amount
        use_cache (bool): Whether to use cached data
        iterations (int): Number of iterations to run

    Returns:
        Dict: Dictionary containing performance metrics for the test run
    """
    metrics_collector = get_calculation_metrics_collector()  # Initialize metrics collector for calculation performance

    test_metadata = {
        "name": "locate_fee_calculation",
        "ticker": ticker,
        "position_value": str(position_value),
        "loan_days": loan_days,
        "markup_percentage": str(markup_percentage),
        "fee_type": fee_type.value,
        "fee_amount": str(fee_amount),
        "use_cache": use_cache,
        "iterations": iterations
    }

    with metrics_collection(metrics_collector, test_metadata):  # Start metrics collection with test metadata
        for _ in range(iterations):  # Run the specified number of iterations of calculate_locate_fee
            start_time = time.perf_counter()
            calculate_locate_fee(ticker, position_value, loan_days, markup_percentage, fee_type, fee_amount, use_cache=use_cache)
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
            metrics_collector.record_calculation("locate_fee", execution_time)  # For each iteration, record calculation time using the metrics collector

    metrics = metrics_collector.stop_collection()  # Stop metrics collection and retrieve results

    execution_times = metrics["calculation"]["calculation_types"]["locate_fee"]["execution_times"]
    statistics = calculate_statistics(execution_times)  # Calculate and add summary statistics (min, max, mean, median, p95, p99)
    metrics["calculation"]["calculation_types"]["locate_fee"]["execution_times"] = statistics

    return metrics  # Return the metrics dictionary with all performance data


def calculate_statistics(execution_times: List[float]) -> Dict[str, float]:
    """Calculates statistical measures from a list of execution times

    Args:
        execution_times (List): List of execution times

    Returns:
        Dict: Dictionary containing statistical measures
    """
    min_time = min(execution_times)  # Calculate minimum execution time
    max_time = max(execution_times)  # Calculate maximum execution time
    mean_time = statistics.mean(execution_times)  # Calculate mean execution time
    median_time = statistics.median(execution_times)  # Calculate median execution time
    p95_time = statistics.quantiles(execution_times, n=100)[94]  # Calculate 95th percentile execution time
    p99_time = statistics.quantiles(execution_times, n=100)[98]  # Calculate 99th percentile execution time

    return {  # Return dictionary with all statistical measures
        "min": min_time,
        "max": max_time,
        "mean": mean_time,
        "median": median_time,
        "p95": p95_time,
        "p99": p99_time
    }


def test_borrow_rate_calculation_speed(test_stocks):
    """Tests that borrow rate calculation meets performance requirements

    Args:
        test_stocks (fixture): Fixture providing test stock data
    """
    settings = get_test_settings()  # Get test settings for performance thresholds
    borrow_rate_threshold_ms = settings.get_response_time_threshold()
    sample_stocks = test_stocks[:5]  # Select a sample of stocks for testing

    for stock in sample_stocks:  # For each stock, run borrow rate calculation test with run_borrow_rate_calculation_test
        ticker = stock["ticker"]
        min_rate = stock["min_borrow_rate"]
        metrics = run_borrow_rate_calculation_test(ticker, min_rate, use_cache=False, iterations=ITERATIONS_MEDIUM)

        p95_execution_time = metrics["calculation"]["calculation_types"]["borrow_rate"]["execution_times"]["p95"]
        assert p95_execution_time < borrow_rate_threshold_ms, f"Borrow rate calculation exceeds threshold: {p95_execution_time}ms > {borrow_rate_threshold_ms}ms"  # Verify that p95 execution time is below BORROW_RATE_THRESHOLD_MS

        print(f"Borrow Rate Calculation Performance Metrics for {ticker}: {metrics}")  # Log detailed performance metrics


def test_locate_fee_calculation_speed(test_calculations, test_brokers):
    """Tests that locate fee calculation meets performance requirements

    Args:
        test_calculations (fixture): Fixture providing test calculation parameters
        test_brokers (fixture): Fixture providing test broker data
    """
    settings = get_test_settings()  # Get test settings for performance thresholds
    locate_fee_threshold_ms = settings.get_response_time_threshold()
    sample_calculations = test_calculations[:5]  # Select a sample of calculation parameters and brokers for testing
    sample_brokers = test_brokers[:5]

    for calc in sample_calculations:  # For each parameter set, run locate fee calculation test with run_locate_fee_calculation_test
        ticker = calc["ticker"]
        position_value = calc["position_value"]
        loan_days = calc["loan_days"]
        for broker in sample_brokers:
            markup_percentage = broker["markup_percentage"]
            fee_type = broker["transaction_fee_type"]
            fee_amount = broker["transaction_amount"]
            metrics = run_locate_fee_calculation_test(ticker, position_value, loan_days, markup_percentage, fee_type, fee_amount, use_cache=False, iterations=ITERATIONS_SMALL)

            p95_execution_time = metrics["calculation"]["calculation_types"]["locate_fee"]["execution_times"]["p95"]
            assert p95_execution_time < locate_fee_threshold_ms, f"Locate fee calculation exceeds threshold: {p95_execution_time}ms > {locate_fee_threshold_ms}ms"  # Verify that p95 execution time is below LOCATE_FEE_THRESHOLD_MS

            print(f"Locate Fee Calculation Performance Metrics for {ticker}: {metrics}")  # Log detailed performance metrics


def test_borrow_rate_calculation_with_cache(test_stocks):
    """Tests the performance improvement of borrow rate calculation with caching enabled

    Args:
        test_stocks (fixture): Fixture providing test stock data
    """
    sample_stocks = test_stocks[:3]  # Select a sample of stocks for testing

    for stock in sample_stocks:  # For each stock, run borrow rate calculation test without cache
        ticker = stock["ticker"]
        min_rate = stock["min_borrow_rate"]
        metrics_without_cache = run_borrow_rate_calculation_test(ticker, min_rate, use_cache=False, iterations=ITERATIONS_SMALL)

        metrics_with_cache = run_borrow_rate_calculation_test(ticker, min_rate, use_cache=True, iterations=ITERATIONS_SMALL)  # For each stock, run borrow rate calculation test with cache enabled

        p95_without_cache = metrics_without_cache["calculation"]["calculation_types"]["borrow_rate"]["execution_times"]["p95"]
        p95_with_cache = metrics_with_cache["calculation"]["calculation_types"]["borrow_rate"]["execution_times"]["p95"]

        assert p95_with_cache < p95_without_cache, "Caching did not improve performance"  # Compare execution times and verify significant improvement with caching
        assert p95_with_cache < (p95_without_cache * 0.2), "Cached execution time is not at least 80% faster than uncached"  # Verify that cached execution time is at least 80% faster than uncached

        print(f"Borrow Rate Calculation Performance Comparison for {ticker}: Without Cache - {p95_without_cache}ms, With Cache - {p95_with_cache}ms")  # Log performance comparison metrics


def test_locate_fee_calculation_with_cache(test_calculations, test_brokers):
    """Tests the performance improvement of locate fee calculation with caching enabled

    Args:
        test_calculations (fixture): Fixture providing test calculation parameters
        test_brokers (fixture): Fixture providing test broker data
    """
    sample_calculations = test_calculations[:3]  # Select a sample of calculation parameters and brokers for testing
    sample_brokers = test_brokers[:3]

    for calc in sample_calculations:  # For each parameter set, run locate fee calculation test without cache
        ticker = calc["ticker"]
        position_value = calc["position_value"]
        loan_days = calc["loan_days"]
        for broker in sample_brokers:
            markup_percentage = broker["markup_percentage"]
            fee_type = broker["transaction_fee_type"]
            fee_amount = broker["transaction_amount"]

            metrics_without_cache = run_locate_fee_calculation_test(ticker, position_value, loan_days, markup_percentage, fee_type, fee_amount, use_cache=False, iterations=ITERATIONS_SMALL)

            metrics_with_cache = run_locate_fee_calculation_test(ticker, position_value, loan_days, markup_percentage, fee_type, fee_amount, use_cache=True, iterations=ITERATIONS_SMALL)  # For each parameter set, run locate fee calculation test with cache enabled

            p95_without_cache = metrics_without_cache["calculation"]["calculation_types"]["locate_fee"]["execution_times"]["p95"]
            p95_with_cache = metrics_with_cache["calculation"]["calculation_types"]["locate_fee"]["execution_times"]["p95"]

            assert p95_with_cache < p95_without_cache, "Caching did not improve performance"  # Compare execution times and verify significant improvement with caching
            assert p95_with_cache < (p95_without_cache * 0.2), "Cached execution time is not at least 80% faster than uncached"  # Verify that cached execution time is at least 80% faster than uncached

            print(f"Locate Fee Calculation Performance Comparison for {ticker}: Without Cache - {p95_without_cache}ms, With Cache - {p95_with_cache}ms")  # Log performance comparison metrics


def test_borrow_rate_calculation_under_load(normal_market_scenario):
    """Tests borrow rate calculation performance under high load conditions

    Args:
        normal_market_scenario (fixture): Fixture providing normal market scenario test data
    """
    settings = get_test_settings()  # Get normal market scenario test data
    borrow_rate_threshold_ms = settings.get_response_time_threshold()
    sample_stocks = normal_market_scenario["stocks"][:5]

    for stock in sample_stocks:  # Run borrow rate calculation test with large number of iterations (ITERATIONS_LARGE)
        ticker = stock["ticker"]
        min_rate = stock["min_borrow_rate"]
        metrics = run_borrow_rate_calculation_test(ticker, min_rate, use_cache=True, iterations=ITERATIONS_LARGE)

        p95_execution_time = metrics["calculation"]["calculation_types"]["borrow_rate"]["execution_times"]["p95"]
        assert p95_execution_time < borrow_rate_threshold_ms, f"Borrow rate calculation exceeds threshold under load: {p95_execution_time}ms > {borrow_rate_threshold_ms}ms"  # Verify that p95 execution time remains below threshold even under load

        calculations_per_second = metrics["calculation"]["overall"]["calculations_per_second"]
        assert calculations_per_second > settings.get_throughput_threshold(), f"Borrow rate calculation throughput is below minimum requirements: {calculations_per_second} calc/sec < {settings.get_throughput_threshold()} calc/sec"  # Verify that throughput meets minimum requirements (calculations per second)

        print(f"Borrow Rate Calculation Load Test Metrics for {ticker}: {metrics}")  # Log load test performance metrics


def test_locate_fee_calculation_under_load(normal_market_scenario):
    """Tests locate fee calculation performance under high load conditions

    Args:
        normal_market_scenario (fixture): Fixture providing normal market scenario test data
    """
    settings = get_test_settings()  # Get normal market scenario test data
    locate_fee_threshold_ms = settings.get_response_time_threshold()
    sample_calculations = normal_market_scenario["calculations"][:5]
    sample_brokers = normal_market_scenario["brokers"][:5]

    for calc in sample_calculations:  # Run locate fee calculation test with large number of iterations (ITERATIONS_LARGE)
        ticker = calc["ticker"]
        position_value = calc["position_value"]
        loan_days = calc["loan_days"]
        for broker in sample_brokers:
            markup_percentage = broker["markup_percentage"]
            fee_type = broker["transaction_fee_type"]
            fee_amount = broker["transaction_amount"]
            metrics = run_locate_fee_calculation_test(ticker, position_value, loan_days, markup_percentage, fee_type, fee_amount, use_cache=True, iterations=ITERATIONS_LARGE)

            p95_execution_time = metrics["calculation"]["calculation_types"]["locate_fee"]["execution_times"]["p95"]
            assert p95_execution_time < locate_fee_threshold_ms, f"Locate fee calculation exceeds threshold under load: {p95_execution_time}ms > {locate_fee_threshold_ms}ms"  # Verify that p95 execution time remains below threshold even under load

            calculations_per_second = metrics["calculation"]["overall"]["calculations_per_second"]
            assert calculations_per_second > settings.get_throughput_threshold(), f"Locate fee calculation throughput is below minimum requirements: {calculations_per_second} calc/sec < {settings.get_throughput_threshold()} calc/sec"  # Verify that throughput meets minimum requirements (calculations per second)

            print(f"Locate Fee Calculation Load Test Metrics for {ticker}: {metrics}")  # Log load test performance metrics


def test_calculation_performance_high_volatility(high_volatility_scenario):
    """Tests calculation performance during high market volatility scenarios

    Args:
        high_volatility_scenario (fixture): Fixture providing high volatility scenario test data
    """
    settings = get_test_settings()  # Get high volatility scenario test data
    borrow_rate_threshold_ms = settings.get_response_time_threshold()
    locate_fee_threshold_ms = settings.get_response_time_threshold()
    sample_stocks = high_volatility_scenario["stocks"][:3]
    sample_calculations = high_volatility_scenario["calculations"][:3]
    sample_brokers = high_volatility_scenario["brokers"][:3]

    for stock in sample_stocks:  # Run borrow rate calculation tests with high volatility data
        ticker = stock["ticker"]
        min_rate = stock["min_borrow_rate"]
        metrics = run_borrow_rate_calculation_test(ticker, min_rate, use_cache=True, iterations=ITERATIONS_MEDIUM)

        p95_execution_time = metrics["calculation"]["calculation_types"]["borrow_rate"]["execution_times"]["p95"]
        assert p95_execution_time < borrow_rate_threshold_ms, f"High volatility borrow rate calculation exceeds threshold: {p95_execution_time}ms > {borrow_rate_threshold_ms}ms"

        print(f"High Volatility Borrow Rate Calculation Metrics for {ticker}: {metrics}")

    for calc in sample_calculations:  # Run locate fee calculation tests with high volatility data
        ticker = calc["ticker"]
        position_value = calc["position_value"]
        loan_days = calc["loan_days"]
        for broker in sample_brokers:
            markup_percentage = broker["markup_percentage"]
            fee_type = broker["transaction_fee_type"]
            fee_amount = broker["transaction_amount"]
            metrics = run_locate_fee_calculation_test(ticker, position_value, loan_days, markup_percentage, fee_type, fee_amount, use_cache=True, iterations=ITERATIONS_SMALL)

            p95_execution_time = metrics["calculation"]["calculation_types"]["locate_fee"]["execution_times"]["p95"]
            assert p95_execution_time < locate_fee_threshold_ms, f"High volatility locate fee calculation exceeds threshold: {p95_execution_time}ms > {locate_fee_threshold_ms}ms"

            print(f"High Volatility Locate Fee Calculation Metrics for {ticker}: {metrics}")

    # Compare performance metrics with normal market scenario
    # This part would involve loading metrics from a previous normal market scenario test run
    # and comparing the current metrics to those. This is not implemented here due to the lack of a baseline.

    print("High Volatility Calculation Performance Tests Completed")  # Log volatility impact on performance