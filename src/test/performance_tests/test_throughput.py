"""
Throughput performance tests for the Borrow Rate & Locate Fee Pricing Engine.

This module contains test cases that verify the system's ability to handle high
request volumes, measuring requests per second throughput under various load
conditions and validating against defined SLAs.
"""

import pytest
import time
import logging
import random
from decimal import Decimal
from typing import Dict, List, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor

from src.test.performance_tests.config.settings import get_test_settings
from src.test.performance_tests.helpers.metrics_collector import get_metrics_collector
from src.test.performance_tests.helpers.analysis import analyze_performance_results
from src.test.e2e_tests.helpers.api_client import APIClient

# Configure logger
logger = logging.getLogger(__name__)

# Test data constants
TEST_TICKERS = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "JPM", "V", "PG"]
TEST_CLIENT_IDS = ["client_001", "client_002", "client_003", "client_004", "client_005"]
TEST_POSITION_VALUES = [10000, 25000, 50000, 100000, 250000, 500000]
TEST_LOAN_DAYS = [1, 7, 14, 30, 60, 90]


def generate_random_request_params() -> Dict[str, Any]:
    """
    Generates random parameters for API requests.
    
    Returns:
        Dictionary with random ticker, position_value, loan_days, and client_id
    """
    return {
        "ticker": random.choice(TEST_TICKERS),
        "position_value": random.choice(TEST_POSITION_VALUES),
        "loan_days": random.choice(TEST_LOAN_DAYS),
        "client_id": random.choice(TEST_CLIENT_IDS)
    }


def execute_api_request(api_client: APIClient, request_type: str, params: Dict) -> Dict:
    """
    Executes a single API request with metrics collection.
    
    Args:
        api_client: API client instance
        request_type: Type of request ('calculate_locate_fee' or 'get_borrow_rate')
        params: Request parameters
        
    Returns:
        API response data and response time
    """
    start_time = time.time()
    
    if request_type == 'calculate_locate_fee':
        response = api_client.calculate_locate_fee(
            ticker=params['ticker'],
            position_value=params['position_value'],
            loan_days=params['loan_days'],
            client_id=params['client_id']
        )
    elif request_type == 'get_borrow_rate':
        response = api_client.get_borrow_rate(ticker=params['ticker'])
    else:
        raise ValueError(f"Unsupported request type: {request_type}")
    
    end_time = time.time()
    response_time = (end_time - start_time) * 1000  # Convert to milliseconds
    
    return {"response": response, "response_time": response_time}


def run_concurrent_requests(api_client: APIClient, request_type: str, num_requests: int, max_workers: int) -> tuple:
    """
    Executes multiple API requests concurrently.
    
    Args:
        api_client: API client instance
        request_type: Type of request ('calculate_locate_fee' or 'get_borrow_rate')
        num_requests: Number of requests to execute
        max_workers: Maximum number of concurrent workers
        
    Returns:
        Tuple of (list of responses, list of response times)
    """
    responses = []
    response_times = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a list of futures for all requests
        futures = []
        for _ in range(num_requests):
            params = generate_random_request_params()
            future = executor.submit(execute_api_request, api_client, request_type, params)
            futures.append(future)
        
        # Process results as they complete
        for future in futures:
            result = future.result()
            responses.append(result["response"])
            response_times.append(result["response_time"])
    
    return responses, response_times


def calculate_throughput(num_requests: int, total_time: float) -> float:
    """
    Calculates throughput in requests per second.
    
    Args:
        num_requests: Number of requests executed
        total_time: Total execution time in seconds
        
    Returns:
        Throughput in requests per second
    """
    return num_requests / total_time if total_time > 0 else 0


class ThroughputTest:
    """Base class for throughput performance tests."""
    
    def __init__(self):
        """
        Initializes the throughput test with API client and metrics collector.
        """
        self.settings = get_test_settings()
        self.api_client = APIClient()
        self.metrics_collector = get_metrics_collector()
        logger.info("Initialized ThroughputTest with settings from environment")
    
    def setup(self):
        """
        Sets up the test environment.
        """
        # Ensure API is ready
        if not self.api_client.wait_for_api_ready():
            pytest.fail("API is not available for testing")
        
        # Configure metrics collector with test info
        self.metrics_collector.configure({
            "collection_interval": 1.0,  # 1 second interval for resource metrics
            "include_request_details": True
        })
        
        logger.info("Test setup complete")
    
    def teardown(self):
        """
        Cleans up after test execution.
        """
        # Stop metrics collection if active
        if self.metrics_collector.is_collecting:
            self.metrics_collector.stop_collection()
        
        # Save metrics to file for analysis
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.metrics_collector.save_metrics(
            output_path="./metrics_output",
            filename=f"throughput_test_{timestamp}.json"
        )
        
        logger.info("Test teardown complete")
    
    def run_throughput_test(self, request_type: str, num_requests: int, max_workers: int, ramp_up_time: float = 0) -> Dict:
        """
        Runs a throughput test with specified parameters.
        
        Args:
            request_type: Type of request ('calculate_locate_fee' or 'get_borrow_rate')
            num_requests: Number of requests to execute
            max_workers: Maximum number of concurrent workers
            ramp_up_time: Time in seconds to ramp up to full load
            
        Returns:
            Test results including throughput and response times
        """
        # Start metrics collection
        self.metrics_collector.start_collection({
            "name": f"throughput_test_{request_type}",
            "type": "throughput",
            "request_type": request_type,
            "num_requests": num_requests,
            "max_workers": max_workers,
            "ramp_up_time": ramp_up_time
        })
        
        logger.info(
            f"Starting throughput test: {request_type}, "
            f"{num_requests} requests, {max_workers} workers, "
            f"{ramp_up_time}s ramp-up"
        )
        
        start_time = time.time()
        
        # Execute concurrent requests
        responses, response_times = run_concurrent_requests(
            self.api_client, request_type, num_requests, max_workers
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate throughput
        throughput = calculate_throughput(num_requests, total_time)
        
        # Analyze response times and error rates
        successful_responses = [r for r in responses if hasattr(r, 'status') and r.status == "success"]
        error_count = len(responses) - len(successful_responses)
        error_rate = (error_count / num_requests) * 100 if num_requests > 0 else 0
        
        # Calculate response time percentiles
        response_times.sort()
        p50 = response_times[int(len(response_times) * 0.5)] if response_times else 0
        p90 = response_times[int(len(response_times) * 0.9)] if response_times else 0
        p95 = response_times[int(len(response_times) * 0.95)] if response_times else 0
        p99 = response_times[int(len(response_times) * 0.99)] if response_times else 0
        
        # Compile results
        results = {
            "throughput": throughput,
            "total_time": total_time,
            "num_requests": num_requests,
            "successful_requests": len(successful_responses),
            "error_count": error_count,
            "error_rate": error_rate,
            "response_times": {
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "mean": sum(response_times) / len(response_times) if response_times else 0,
                "p50": p50,
                "p90": p90,
                "p95": p95,
                "p99": p99
            }
        }
        
        # Stop metrics collection
        self.metrics_collector.stop_collection()
        
        logger.info(
            f"Completed throughput test: {results['throughput']:.2f} req/sec, "
            f"p95 response time: {results['response_times']['p95']:.2f}ms, "
            f"error rate: {results['error_rate']:.2f}%"
        )
        
        return results
    
    def validate_results(self, results: Dict) -> bool:
        """
        Validates test results against performance thresholds.
        
        Args:
            results: Test results dictionary
            
        Returns:
            True if results meet thresholds, False otherwise
        """
        # Get thresholds from settings
        throughput_threshold = self.settings.get_throughput_threshold()
        response_time_threshold = self.settings.get_response_time_threshold()
        error_rate_threshold = self.settings.get_error_rate_threshold()
        
        # Validate throughput
        throughput_pass = results['throughput'] >= throughput_threshold
        if not throughput_pass:
            logger.warning(
                f"Throughput below threshold: {results['throughput']:.2f} req/sec "
                f"(threshold: {throughput_threshold} req/sec)"
            )
        
        # Validate response time (p95)
        response_time_pass = results['response_times']['p95'] <= response_time_threshold
        if not response_time_pass:
            logger.warning(
                f"P95 response time above threshold: {results['response_times']['p95']:.2f}ms "
                f"(threshold: {response_time_threshold}ms)"
            )
        
        # Validate error rate
        error_rate_pass = results['error_rate'] <= error_rate_threshold
        if not error_rate_pass:
            logger.warning(
                f"Error rate above threshold: {results['error_rate']:.2f}% "
                f"(threshold: {error_rate_threshold}%)"
            )
        
        # Overall validation result
        passed = throughput_pass and response_time_pass and error_rate_pass
        
        if passed:
            logger.info("Test passed all performance thresholds")
        else:
            logger.warning("Test failed one or more performance thresholds")
        
        return passed


@pytest.fixture
def throughput_test():
    """Fixture that provides a configured ThroughputTest instance."""
    test = ThroughputTest()
    test.setup()
    yield test
    test.teardown()


def test_baseline_throughput(throughput_test):
    """
    Test baseline throughput with moderate load (500 requests).
    
    This test establishes a performance baseline using a moderate number of
    concurrent requests and validates that the system meets minimum performance
    requirements under normal conditions.
    """
    # Run test with moderate load
    results = throughput_test.run_throughput_test(
        request_type='calculate_locate_fee',
        num_requests=500,
        max_workers=50
    )
    
    # Validate test results
    assert throughput_test.validate_results(results), "Baseline throughput test failed to meet performance thresholds"
    
    # Additional specific assertions for baseline test
    assert results['throughput'] >= 100, "Baseline throughput should be at least 100 req/sec"
    assert results['response_times']['p95'] <= 150, "Baseline p95 response time should be under 150ms"
    assert results['error_rate'] <= 0.1, "Baseline error rate should be under 0.1%"


def test_target_throughput(throughput_test):
    """
    Test target throughput with high load (1000 requests/second).
    
    This test validates that the system can handle the target throughput of
    1000 requests per second as specified in the requirements.
    """
    # Run test with high load
    results = throughput_test.run_throughput_test(
        request_type='calculate_locate_fee',
        num_requests=1000,
        max_workers=100
    )
    
    # Validate test results
    assert throughput_test.validate_results(results), "Target throughput test failed to meet performance thresholds"
    
    # Additional specific assertions for target test
    assert results['throughput'] >= 1000, "Target throughput should be at least 1000 req/sec"
    assert results['response_times']['p95'] <= 100, "Target p95 response time should be under 100ms"
    assert results['error_rate'] <= 0.1, "Target error rate should be under 0.1%"


def test_stress_throughput(throughput_test):
    """
    Test stress throughput with very high load (2000+ requests/second).
    
    This test evaluates system behavior under stress conditions with a load
    double the target requirement to identify potential breaking points.
    """
    # Run test with very high load
    results = throughput_test.run_throughput_test(
        request_type='calculate_locate_fee',
        num_requests=2500,
        max_workers=250
    )
    
    # For stress test, we still log results but don't necessarily expect
    # to meet all thresholds - the purpose is to observe behavior under extreme load
    throughput_test.validate_results(results)
    
    # Log detailed stress test results
    logger.info(
        f"Stress test results: Throughput={results['throughput']:.2f} req/sec, "
        f"p95={results['response_times']['p95']:.2f}ms, "
        f"p99={results['response_times']['p99']:.2f}ms, "
        f"Error rate={results['error_rate']:.2f}%"
    )
    
    # Assert minimum acceptable performance even under stress
    assert results['throughput'] >= 1500, "Even under stress, throughput should exceed 1500 req/sec"
    assert results['error_rate'] <= 2.0, "Even under stress, error rate should stay under 2%"


def test_spike_throughput(throughput_test):
    """
    Test spike throughput with sudden increase to 3000 requests/second.
    
    This test simulates a sudden traffic spike to verify the system's ability
    to handle unexpected load increases without failure.
    """
    # First run with moderate load
    logger.info("Starting with moderate load before spike")
    throughput_test.run_throughput_test(
        request_type='calculate_locate_fee',
        num_requests=300,
        max_workers=30
    )
    
    # Small delay to simulate normal operation
    time.sleep(2)
    
    # Now spike with very high load
    logger.info("Applying spike load of 3000 requests")
    spike_results = throughput_test.run_throughput_test(
        request_type='calculate_locate_fee',
        num_requests=3000,
        max_workers=300
    )
    
    # For spike test, we're interested in system stability rather than meeting all thresholds
    throughput_test.validate_results(spike_results)
    
    # Log detailed spike test results
    logger.info(
        f"Spike test results: Throughput={spike_results['throughput']:.2f} req/sec, "
        f"p95={spike_results['response_times']['p95']:.2f}ms, "
        f"Error rate={spike_results['error_rate']:.2f}%"
    )
    
    # Assert system remains functional during spike
    assert spike_results['error_rate'] <= 5.0, "During spike, error rate should stay under 5%"
    assert spike_results['throughput'] >= 1000, "During spike, throughput should still exceed 1000 req/sec"


def test_sustained_throughput(throughput_test):
    """
    Test sustained throughput over a longer period (5+ minutes).
    
    This test validates the system's ability to maintain consistent performance
    over an extended period, which is important for production reliability.
    """
    # Test parameters
    test_duration_seconds = 300  # 5 minutes
    batch_size = 500
    max_workers = 50
    
    # Track results over time
    start_time = time.time()
    end_time = start_time + test_duration_seconds
    batches_completed = 0
    all_response_times = []
    total_requests = 0
    total_errors = 0
    
    logger.info(f"Starting sustained throughput test for {test_duration_seconds} seconds")
    
    # Run batches of requests until test duration is reached
    while time.time() < end_time:
        batch_results = throughput_test.run_throughput_test(
            request_type='calculate_locate_fee',
            num_requests=batch_size,
            max_workers=max_workers
        )
        
        # Collect metrics
        batches_completed += 1
        total_requests += batch_results['num_requests']
        total_errors += batch_results['error_count']
        all_response_times.extend([batch_results['response_times']['p95']])
        
        # Log batch completion
        elapsed = time.time() - start_time
        remaining = max(0, test_duration_seconds - elapsed)
        logger.info(
            f"Completed batch {batches_completed}: "
            f"Throughput={batch_results['throughput']:.2f} req/sec, "
            f"p95={batch_results['response_times']['p95']:.2f}ms. "
            f"Time remaining: {remaining:.1f}s"
        )
        
        # Small delay between batches
        if remaining > 5:  # Only delay if we have time left
            time.sleep(2)
    
    # Calculate overall results
    actual_duration = time.time() - start_time
    overall_throughput = total_requests / actual_duration
    overall_error_rate = (total_errors / total_requests) * 100 if total_requests > 0 else 0
    
    # Calculate response time statistics
    avg_p95 = sum(all_response_times) / len(all_response_times) if all_response_times else 0
    
    # Compile final results
    sustained_results = {
        "throughput": overall_throughput,
        "total_time": actual_duration,
        "num_requests": total_requests,
        "error_count": total_errors,
        "error_rate": overall_error_rate,
        "response_times": {
            "p95": avg_p95
        },
        "batches_completed": batches_completed
    }
    
    # Log final results
    logger.info(
        f"Sustained test completed: {batches_completed} batches, "
        f"{total_requests} total requests over {actual_duration:.1f} seconds. "
        f"Throughput={sustained_results['throughput']:.2f} req/sec, "
        f"Avg p95={avg_p95:.2f}ms, "
        f"Error rate={overall_error_rate:.2f}%"
    )
    
    # Validate results
    assert throughput_test.validate_results(sustained_results), "Sustained throughput test failed to meet performance thresholds"
    
    # Additional assertions specific to sustained test
    assert sustained_results['throughput'] >= get_test_settings().get_throughput_threshold(), \
        "Sustained throughput should meet the target threshold"
    assert sustained_results['error_rate'] <= 0.2, "Sustained error rate should be under 0.2%"


def test_mixed_endpoint_throughput(throughput_test):
    """
    Test throughput with mixed endpoint calls (calculate_locate_fee and get_borrow_rate).
    
    This test simulates real-world usage patterns where different API endpoints
    are called concurrently, verifying that the system maintains performance
    across all endpoints.
    """
    # Test parameters
    num_locate_requests = 500
    num_rate_requests = 500
    total_requests = num_locate_requests + num_rate_requests
    max_workers = 100
    
    logger.info(f"Starting mixed endpoint test with {total_requests} total requests")
    
    # Start metrics collection
    throughput_test.metrics_collector.start_collection({
        "name": "mixed_endpoint_throughput_test",
        "type": "throughput",
        "num_locate_requests": num_locate_requests,
        "num_rate_requests": num_rate_requests,
        "max_workers": max_workers
    })
    
    start_time = time.time()
    
    # Create a thread pool
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit locate fee requests
        locate_futures = []
        for _ in range(num_locate_requests):
            params = generate_random_request_params()
            future = executor.submit(
                execute_api_request,
                throughput_test.api_client,
                'calculate_locate_fee',
                params
            )
            locate_futures.append(future)
        
        # Submit borrow rate requests
        rate_futures = []
        for _ in range(num_rate_requests):
            params = {"ticker": random.choice(TEST_TICKERS)}
            future = executor.submit(
                execute_api_request,
                throughput_test.api_client,
                'get_borrow_rate',
                params
            )
            rate_futures.append(future)
        
        # Collect all futures
        all_futures = locate_futures + rate_futures
        
        # Process results
        locate_response_times = []
        rate_response_times = []
        locate_errors = 0
        rate_errors = 0
        
        # Process locate fee results
        for future in locate_futures:
            result = future.result()
            locate_response_times.append(result["response_time"])
            response = result["response"]
            if not hasattr(response, 'status') or response.status != "success":
                locate_errors += 1
        
        # Process borrow rate results
        for future in rate_futures:
            result = future.result()
            rate_response_times.append(result["response_time"])
            response = result["response"]
            if not hasattr(response, 'status') or response.status != "success":
                rate_errors += 1
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate overall throughput
    throughput = calculate_throughput(total_requests, total_time)
    
    # Calculate error rates
    locate_error_rate = (locate_errors / num_locate_requests) * 100 if num_locate_requests > 0 else 0
    rate_error_rate = (rate_errors / num_rate_requests) * 100 if num_rate_requests > 0 else 0
    overall_error_rate = ((locate_errors + rate_errors) / total_requests) * 100 if total_requests > 0 else 0
    
    # Calculate response time percentiles
    locate_response_times.sort()
    rate_response_times.sort()
    all_response_times = locate_response_times + rate_response_times
    all_response_times.sort()
    
    # Compile results
    mixed_results = {
        "throughput": throughput,
        "total_time": total_time,
        "num_requests": total_requests,
        "error_rate": overall_error_rate,
        "locate_fee": {
            "requests": num_locate_requests,
            "errors": locate_errors,
            "error_rate": locate_error_rate,
            "p95": locate_response_times[int(len(locate_response_times) * 0.95)] if locate_response_times else 0
        },
        "borrow_rate": {
            "requests": num_rate_requests,
            "errors": rate_errors,
            "error_rate": rate_error_rate,
            "p95": rate_response_times[int(len(rate_response_times) * 0.95)] if rate_response_times else 0
        },
        "response_times": {
            "min": min(all_response_times) if all_response_times else 0,
            "max": max(all_response_times) if all_response_times else 0,
            "mean": sum(all_response_times) / len(all_response_times) if all_response_times else 0,
            "p95": all_response_times[int(len(all_response_times) * 0.95)] if all_response_times else 0
        }
    }
    
    # Stop metrics collection
    throughput_test.metrics_collector.stop_collection()
    
    # Log results
    logger.info(
        f"Mixed endpoint test results: "
        f"Throughput={mixed_results['throughput']:.2f} req/sec, "
        f"Overall p95={mixed_results['response_times']['p95']:.2f}ms, "
        f"Locate p95={mixed_results['locate_fee']['p95']:.2f}ms, "
        f"Rate p95={mixed_results['borrow_rate']['p95']:.2f}ms, "
        f"Error rate={mixed_results['error_rate']:.2f}%"
    )
    
    # Validate results
    assert throughput_test.validate_results(mixed_results), "Mixed endpoint throughput test failed to meet performance thresholds"
    
    # Additional specific assertions
    assert mixed_results['throughput'] >= 800, "Mixed endpoint throughput should be at least 800 req/sec"
    assert mixed_results['locate_fee']['p95'] <= 150, "Locate fee p95 response time should be under 150ms"
    assert mixed_results['borrow_rate']['p95'] <= 100, "Borrow rate p95 response time should be under 100ms"
    assert mixed_results['error_rate'] <= 0.2, "Mixed endpoint error rate should be under 0.2%"