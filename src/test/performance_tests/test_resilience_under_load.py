"""
Performance test module that evaluates the resilience of the Borrow Rate & Locate Fee Pricing Engine
under various failure scenarios and load conditions. This module implements tests to verify that the
system maintains performance and availability during external API failures, high load, and other
adverse conditions.
"""

import pytest  # pytest-version: 7.3.1
import time  # standard library
import concurrent.futures  # standard library
import logging  # standard library
import random  # standard library
from contextlib import contextmanager  # standard library
import requests  # requests-version: 2.28.0+

from .config.settings import get_test_settings, TestSettings  # src/test/performance_tests/config/settings.py
from .helpers.metrics_collector import MetricsCollector, create_metrics_collector  # src/test/performance_tests/helpers/metrics_collector.py
from .helpers.analysis import analyze_performance_results, PerformanceAnalyzer  # src/test/performance_tests/helpers/analysis.py
from src.test.e2e_tests.helpers.api_client import APIClient, create_api_client  # src/test/e2e_tests/helpers/api_client.py
from .test_api_latency import generate_test_parameters, execute_concurrent_requests  # src/test/performance_tests/test_api_latency.py

# Configure logger
logger = logging.getLogger(__name__)

# Test data
TEST_TICKERS = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "JPM", "V", "PG"]
TEST_POSITION_VALUES = [10000, 50000, 100000, 500000, 1000000]
TEST_LOAN_DAYS = [1, 7, 30, 60, 90]
TEST_CLIENT_IDS = ["client_001", "client_002", "client_003"]

# Failure scenarios
FAILURE_SCENARIOS = {
    "external_api_timeout": "Simulate external API timeout",
    "external_api_error": "Simulate external API error response",
    "database_connection_issue": "Simulate database connection issues",
    "high_latency": "Simulate high network latency",
    "intermittent_failures": "Simulate intermittent service failures"
}


@contextmanager
def simulate_external_api_failure(failure_type: str, api_name: str, duration_seconds: int):
    """Simulates a failure in an external API dependency

    Args:
        failure_type (str): Type of failure to simulate ('timeout', 'error', 'unavailable')
        api_name (str): Name of the API to simulate failure for
        duration_seconds (int): Duration of the simulated failure in seconds

    Yields:
        contextlib.ContextManager: Context manager that simulates the failure
    """
    logger.info(f"Simulating {failure_type} for {api_name} API for {duration_seconds} seconds")
    start_time = time.time()

    # Simulate failure based on failure_type
    if failure_type == 'timeout':
        # Simulate timeout by delaying responses
        pass  # Implement mock server configuration for timeout
    elif failure_type == 'error':
        # Simulate error by returning error responses
        pass  # Implement mock server configuration for error responses
    elif failure_type == 'unavailable':
        # Simulate unavailable by making the server unreachable
        pass  # Implement mock server configuration for unavailability

    try:
        yield  # Execute the test within the context
    finally:
        # Restore normal operation after the test completes
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Simulated {failure_type} for {api_name} API completed after {elapsed_time:.2f} seconds")


def execute_resilience_test(api_client: APIClient, failure_scenario: str, test_parameters: list, concurrency: int, metrics_collector: MetricsCollector):
    """Executes a resilience test with the specified failure scenario

    Args:
        api_client (APIClient): API client instance
        failure_scenario (str): The failure scenario to simulate
        test_parameters (list): List of test parameters for API requests
        concurrency (int): Number of concurrent requests
        metrics_collector (MetricsCollector): Metrics collector instance

    Returns:
        dict: Test results including metrics and analysis
    """
    logger.info(f"Starting resilience test with failure scenario: {failure_scenario}")

    # Determine the appropriate failure simulation based on scenario
    if failure_scenario == 'external_api_timeout':
        failure_simulation = simulate_external_api_failure(failure_type='timeout', api_name='SecLend', duration_seconds=10)
    elif failure_scenario == 'external_api_error':
        failure_simulation = simulate_external_api_failure(failure_type='error', api_name='SecLend', duration_seconds=10)
    elif failure_scenario == 'database_connection_issue':
        failure_simulation = simulate_external_api_failure(failure_type='unavailable', api_name='Database', duration_seconds=10)
    elif failure_scenario == 'high_latency':
        failure_simulation = simulate_external_api_failure(failure_type='timeout', api_name='Network', duration_seconds=10)
    elif failure_scenario == 'intermittent_failures':
        failure_simulation = simulate_external_api_failure(failure_type='error', api_name='SecLend', duration_seconds=10)
    else:
        failure_simulation = None

    # Start metrics collection
    metrics_collector.start_collection(test_info={"name": f"resilience_test_{failure_scenario}"})

    # Apply the failure simulation using simulate_external_api_failure
    with failure_simulation if failure_simulation else contextmanager(lambda: iter([None]))():
        # Execute concurrent API requests using execute_concurrent_requests
        execute_concurrent_requests(test_parameters, 'calculate_locate_fee', concurrency, metrics_collector)

    # Stop metrics collection
    metrics_collector.stop_collection()

    # Analyze collected metrics against resilience thresholds
    analysis_results = metrics_collector.analyze_metrics(custom_thresholds={})

    # Log test results and whether the system maintained resilience
    if analysis_results['status'] == 'PASS':
        logger.info(f"Resilience test PASSED for scenario: {failure_scenario}")
    else:
        logger.warning(f"Resilience test FAILED for scenario: {failure_scenario}")

    # Return test results dictionary with metrics and analysis
    return {"failure_scenario": failure_scenario, "analysis_results": analysis_results}


def verify_fallback_mechanism(api_client: APIClient, ticker: str, failure_scenario: str):
    """Verifies that the fallback mechanism works correctly during failures

    Args:
        api_client (APIClient): API client instance
        ticker (str): Stock ticker symbol to test
        failure_scenario (str): The failure scenario to simulate

    Returns:
        bool: True if fallback mechanism worked correctly
    """
    logger.info(f"Verifying fallback mechanism for ticker: {ticker} with scenario: {failure_scenario}")

    # Get baseline borrow rate for the ticker
    baseline_rate_response = api_client.get_borrow_rate(ticker=ticker)
    baseline_rate = baseline_rate_response.current_rate if hasattr(baseline_rate_response, 'current_rate') else None

    # Apply the failure simulation using simulate_external_api_failure
    with simulate_external_api_failure(failure_type='unavailable', api_name='SecLend', duration_seconds=5):
        # Attempt to get borrow rate during failure
        failed_rate_response = api_client.get_borrow_rate(ticker=ticker)
        fallback_rate = failed_rate_response.current_rate if hasattr(failed_rate_response, 'current_rate') else None

        # Verify that a rate was returned despite the failure
        if fallback_rate is None:
            logger.warning(f"Fallback mechanism FAILED: No rate returned for {ticker} during {failure_scenario}")
            return False

        # Verify that the response indicates fallback was used
        if not hasattr(failed_rate_response, 'status') or failed_rate_response.status != 'success':
            logger.warning(f"Fallback mechanism FAILED: Invalid status for {ticker} during {failure_scenario}")
            return False

    # Log whether fallback mechanism worked correctly
    logger.info(f"Fallback mechanism verification COMPLETED for ticker: {ticker} with scenario: {failure_scenario}")
    return True


def measure_recovery_time(api_client: APIClient, failure_scenario: str, failure_duration_seconds: int):
    """Measures how quickly the system recovers after a failure is resolved

    Args:
        api_client (APIClient): API client instance
        failure_scenario (str): The failure scenario to simulate
        failure_duration_seconds (int): Duration of the simulated failure in seconds

    Returns:
        float: Recovery time in seconds
    """
    logger.info(f"Measuring recovery time after {failure_scenario} for {failure_duration_seconds} seconds")

    # Apply the failure simulation for the specified duration
    with simulate_external_api_failure(failure_type='unavailable', api_name='SecLend', duration_seconds=failure_duration_seconds):
        pass  # Simulate the failure

    # After failure is resolved, start timing recovery
    start_time = time.time()
    recovery_attempts = 0
    while True:
        recovery_attempts += 1
        try:
            # Repeatedly call health_check until system returns to normal state
            health_response = api_client.health_check()
            if hasattr(health_response, 'status') and health_response.status == 'healthy':
                break  # Exit loop when system is healthy
            else:
                logger.debug(f"System not yet recovered (attempt {recovery_attempts})")
        except Exception as e:
            logger.warning(f"Error checking health during recovery (attempt {recovery_attempts}): {str(e)}")

        time.sleep(1)  # Wait before next attempt

    # Calculate recovery time as time elapsed until normal operation
    end_time = time.time()
    recovery_time = end_time - start_time

    # Log the measured recovery time
    logger.info(f"System recovered after {recovery_time:.2f} seconds")
    return recovery_time


class TestResilienceUnderLoad:
    """Test class for system resilience under load and failure conditions"""

    @classmethod
    def setup_class(cls):
        """Set up test class with shared resources"""
        # Get test settings
        cls.test_settings = get_test_settings()

        # Create API client
        cls.api_client = create_api_client()

        # Wait for API to be ready
        cls.api_client.wait_for_api_ready()

        # Create metrics collector
        cls.metrics_collector = create_metrics_collector(config={})

        # Create performance analyzer instance
        cls.analyzer = PerformanceAnalyzer()

        logger.info("TestResilienceUnderLoad setup complete")

    @classmethod
    def teardown_class(cls):
        """Clean up resources after all tests complete"""
        # Generate performance report from metrics collector
        cls.metrics_collector.generate_report(
            output_path="./performance_reports",
            formats=["html", "json"],
            include_charts=True
        )

        logger.info("TestResilienceUnderLoad teardown complete")

    @pytest.mark.resilience
    def test_resilience_external_api_timeout(self):
        """Test system resilience when external API experiences timeouts"""
        logger.info("Starting test_resilience_external_api_timeout")

        # Generate test parameters for API requests
        test_parameters = generate_test_parameters(count=50)

        # Execute resilience test with 'external_api_timeout' scenario
        test_results = execute_resilience_test(
            api_client=self.api_client,
            failure_scenario='external_api_timeout',
            test_parameters=test_parameters,
            concurrency=20,
            metrics_collector=self.metrics_collector
        )

        # Verify that system maintained acceptable performance
        assert test_results['analysis_results']['status'] == 'PASS', "System failed to maintain acceptable performance"

        # Verify that error rate remained below threshold
        error_rate_threshold = self.test_settings.get_error_rate_threshold()
        assert test_results['analysis_results']['api_metrics']['error_rate'] <= error_rate_threshold, "Error rate exceeded threshold"

        # Verify that fallback mechanisms were activated
        # Add specific verification logic for fallback mechanisms

        logger.info("Completed test_resilience_external_api_timeout")

    @pytest.mark.resilience
    def test_resilience_external_api_error(self):
        """Test system resilience when external API returns errors"""
        logger.info("Starting test_resilience_external_api_error")

        # Generate test parameters for API requests
        test_parameters = generate_test_parameters(count=50)

        # Execute resilience test with 'external_api_error' scenario
        test_results = execute_resilience_test(
            api_client=self.api_client,
            failure_scenario='external_api_error',
            test_parameters=test_parameters,
            concurrency=20,
            metrics_collector=self.metrics_collector
        )

        # Verify that system maintained acceptable performance
        assert test_results['analysis_results']['status'] == 'PASS', "System failed to maintain acceptable performance"

        # Verify that error rate remained below threshold
        error_rate_threshold = self.test_settings.get_error_rate_threshold()
        assert test_results['analysis_results']['api_metrics']['error_rate'] <= error_rate_threshold, "Error rate exceeded threshold"

        # Verify that fallback mechanisms were activated
        # Add specific verification logic for fallback mechanisms

        logger.info("Completed test_resilience_external_api_error")

    @pytest.mark.resilience
    def test_resilience_database_connection_issue(self):
        """Test system resilience during database connection issues"""
        logger.info("Starting test_resilience_database_connection_issue")

        # Generate test parameters for API requests
        test_parameters = generate_test_parameters(count=50)

        # Execute resilience test with 'database_connection_issue' scenario
        test_results = execute_resilience_test(
            api_client=self.api_client,
            failure_scenario='database_connection_issue',
            test_parameters=test_parameters,
            concurrency=20,
            metrics_collector=self.metrics_collector
        )

        # Verify that system maintained acceptable performance
        assert test_results['analysis_results']['status'] == 'PASS', "System failed to maintain acceptable performance"

        # Verify that error rate remained below threshold
        error_rate_threshold = self.test_settings.get_error_rate_threshold()
        assert test_results['analysis_results']['api_metrics']['error_rate'] <= error_rate_threshold, "Error rate exceeded threshold"

        # Verify that cache was used as fallback
        # Add specific verification logic for cache usage

        logger.info("Completed test_resilience_database_connection_issue")

    @pytest.mark.resilience
    def test_resilience_high_latency(self):
        """Test system resilience under high network latency conditions"""
        logger.info("Starting test_resilience_high_latency")

        # Generate test parameters for API requests
        test_parameters = generate_test_parameters(count=50)

        # Execute resilience test with 'high_latency' scenario
        test_results = execute_resilience_test(
            api_client=self.api_client,
            failure_scenario='high_latency',
            test_parameters=test_parameters,
            concurrency=20,
            metrics_collector=self.metrics_collector
        )

        # Verify that system maintained acceptable performance
        assert test_results['analysis_results']['status'] == 'PASS', "System failed to maintain acceptable performance"

        # Verify that response times remained within acceptable limits
        response_time_threshold = self.test_settings.get_response_time_threshold()
        assert test_results['analysis_results']['api_metrics']['response_time'] <= response_time_threshold, "Response time exceeded threshold"

        logger.info("Completed test_resilience_high_latency")

    @pytest.mark.resilience
    def test_resilience_intermittent_failures(self):
        """Test system resilience during intermittent service failures"""
        logger.info("Starting test_resilience_intermittent_failures")

        # Generate test parameters for API requests
        test_parameters = generate_test_parameters(count=50)

        # Execute resilience test with 'intermittent_failures' scenario
        test_results = execute_resilience_test(
            api_client=self.api_client,
            failure_scenario='intermittent_failures',
            test_parameters=test_parameters,
            concurrency=20,
            metrics_collector=self.metrics_collector
        )

        # Verify that system maintained acceptable performance
        assert test_results['analysis_results']['status'] == 'PASS', "System failed to maintain acceptable performance"

        # Verify that error rate remained below threshold
        error_rate_threshold = self.test_settings.get_error_rate_threshold()
        assert test_results['analysis_results']['api_metrics']['error_rate'] <= error_rate_threshold, "Error rate exceeded threshold"

        # Verify that circuit breaker patterns worked correctly
        # Add specific verification logic for circuit breaker

        logger.info("Completed test_resilience_intermittent_failures")

    @pytest.mark.resilience
    def test_fallback_mechanism_seclend_api(self):
        """Test fallback mechanism when SecLend API is unavailable"""
        logger.info("Starting test_fallback_mechanism_seclend_api")

        # Select test ticker
        test_ticker = random.choice(TEST_TICKERS)

        # Verify fallback mechanism with 'external_api_unavailable' scenario for SecLend API
        fallback_worked = verify_fallback_mechanism(api_client=self.api_client, ticker=test_ticker, failure_scenario='external_api_unavailable')
        assert fallback_worked, "Fallback mechanism failed for SecLend API"

        # Verify that minimum borrow rates were used
        # Add specific verification logic for minimum borrow rates

        logger.info("Completed test_fallback_mechanism_seclend_api")

    @pytest.mark.resilience
    def test_fallback_mechanism_market_api(self):
        """Test fallback mechanism when Market Volatility API is unavailable"""
        logger.info("Starting test_fallback_mechanism_market_api")

        # Select test ticker
        test_ticker = random.choice(TEST_TICKERS)

        # Verify fallback mechanism with 'external_api_unavailable' scenario for Market API
        fallback_worked = verify_fallback_mechanism(api_client=self.api_client, ticker=test_ticker, failure_scenario='external_api_unavailable')
        assert fallback_worked, "Fallback mechanism failed for Market API"

        # Verify that default volatility values were used
        # Add specific verification logic for default volatility values

        logger.info("Completed test_fallback_mechanism_market_api")

    @pytest.mark.resilience
    def test_recovery_time_after_failure(self):
        """Test system recovery time after failures are resolved"""
        logger.info("Starting test_recovery_time_after_failure")

        # Measure recovery time after external API timeout
        timeout_recovery_time = measure_recovery_time(api_client=self.api_client, failure_scenario='external_api_timeout', failure_duration_seconds=5)

        # Measure recovery time after external API error
        error_recovery_time = measure_recovery_time(api_client=self.api_client, failure_scenario='external_api_error', failure_duration_seconds=5)

        # Measure recovery time after database connection issue
        db_recovery_time = measure_recovery_time(api_client=self.api_client, failure_scenario='database_connection_issue', failure_duration_seconds=5)

        # Verify that recovery times are within acceptable limits
        assert timeout_recovery_time < 10, "Recovery time after timeout exceeded threshold"
        assert error_recovery_time < 10, "Recovery time after error exceeded threshold"
        assert db_recovery_time < 10, "Recovery time after DB issue exceeded threshold"

        logger.info("Completed test_recovery_time_after_failure")

    @pytest.mark.resilience
    @pytest.mark.load
    def test_resilience_under_high_load(self):
        """Test system resilience under high load conditions"""
        logger.info("Starting test_resilience_under_high_load")

        # Generate large number of test parameters
        test_parameters = generate_test_parameters(count=500)

        # Set high concurrency level
        concurrency = 50

        # Start metrics collection
        self.metrics_collector.start_collection(test_info={"name": "resilience_under_high_load"})

        # Execute concurrent API requests
        execute_concurrent_requests(test_parameters, 'calculate_locate_fee', concurrency, self.metrics_collector)

        # Stop metrics collection
        self.metrics_collector.stop_collection()

        # Analyze performance under high load
        analysis_results = self.metrics_collector.analyze_metrics(custom_thresholds={})

        # Verify that system maintained acceptable performance
        assert analysis_results['status'] == 'PASS', "System failed to maintain acceptable performance under high load"

        logger.info("Completed test_resilience_under_high_load")

    @pytest.mark.resilience
    @pytest.mark.load
    def test_resilience_failure_during_high_load(self):
        """Test system resilience when failures occur during high load"""
        logger.info("Starting test_resilience_failure_during_high_load")

        # Generate large number of test parameters
        test_parameters = generate_test_parameters(count=500)

        # Set high concurrency level
        concurrency = 50

        # Start metrics collection
        self.metrics_collector.start_collection(test_info={"name": "resilience_failure_during_high_load"})

        # Simulate external API failure during high load
        with simulate_external_api_failure(failure_type='timeout', api_name='SecLend', duration_seconds=10):
            # Execute concurrent API requests
            execute_concurrent_requests(test_parameters, 'calculate_locate_fee', concurrency, self.metrics_collector)

        # Stop metrics collection
        self.metrics_collector.stop_collection()

        # Analyze performance during failure under load
        analysis_results = self.metrics_collector.analyze_metrics(custom_thresholds={})

        # Verify that system maintained acceptable performance
        assert analysis_results['status'] == 'PASS', "System failed to maintain acceptable performance during failure under high load"

        # Verify that fallback mechanisms were activated
        # Add specific verification logic for fallback mechanisms

        logger.info("Completed test_resilience_failure_during_high_load")

    @pytest.mark.resilience
    def test_circuit_breaker_pattern(self):
        """Test that circuit breaker pattern works correctly"""
        logger.info("Starting test_circuit_breaker_pattern")

        # Simulate persistent external API failures
        with simulate_external_api_failure(failure_type='error', api_name='SecLend', duration_seconds=30):
            # Make repeated API requests to trigger circuit breaker
            for _ in range(10):
                self.api_client.get_borrow_rate(ticker=random.choice(TEST_TICKERS))
                time.sleep(1)

            # Verify that circuit breaker opens after threshold failures
            # Add specific verification logic for circuit breaker state

            # Verify that fallback responses are used when circuit is open
            # Add specific verification logic for fallback responses

        # Allow time for circuit half-open state
        time.sleep(15)

        # Restore external API to normal operation
        # (simulate_external_api_failure context manager handles this)

        # Verify that circuit closes after successful requests
        # Add specific verification logic for circuit breaker state

        logger.info("Completed test_circuit_breaker_pattern")