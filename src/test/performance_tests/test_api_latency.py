"""
Performance test module that measures and validates API latency for the Borrow Rate & Locate Fee Pricing Engine.
This module implements tests to verify that the API meets the required response time SLAs under various load
conditions, focusing on the critical endpoints for borrow rate retrieval and locate fee calculation.
"""

import pytest
import time
import logging
import random
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor

from .config.settings import get_test_settings
from .helpers.metrics_collector import get_api_metrics_collector, metrics_collection
from .helpers.analysis import analyze_performance_results, calculate_statistics
from src.test.e2e_tests.helpers.api_client import APIClient, create_api_client

# Configure logger
logger = logging.getLogger(__name__)

# Test data
TEST_TICKERS = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "JPM", "V", "PG"]
TEST_POSITION_VALUES = [10000, 50000, 100000, 500000, 1000000]
TEST_LOAN_DAYS = [1, 7, 30, 60, 90]
TEST_CLIENT_IDS = ["client_001", "client_002", "client_003"]


def generate_test_parameters(count):
    """
    Generate a list of test parameters for API latency tests
    
    Args:
        count (int): Number of parameter sets to generate
        
    Returns:
        list: List of parameter dictionaries for API requests
    """
    params = []
    for _ in range(count):
        params.append({
            "ticker": random.choice(TEST_TICKERS),
            "position_value": random.choice(TEST_POSITION_VALUES),
            "loan_days": random.choice(TEST_LOAN_DAYS),
            "client_id": random.choice(TEST_CLIENT_IDS)
        })
    return params


def execute_api_request(api_client, params, endpoint_type, metrics_collector):
    """
    Execute a single API request and record metrics
    
    Args:
        api_client (APIClient): Client for making API requests
        params (dict): Parameters for the API request
        endpoint_type (str): Type of endpoint to call
        metrics_collector: Collector for recording metrics
        
    Returns:
        dict: API response data
    """
    start_time = time.time()
    
    try:
        if endpoint_type == 'calculate_locate_fee':
            response = api_client.calculate_locate_fee(
                ticker=params['ticker'],
                position_value=params['position_value'],
                loan_days=params['loan_days'],
                client_id=params['client_id']
            )
        elif endpoint_type == 'get_borrow_rate':
            response = api_client.get_borrow_rate(ticker=params['ticker'])
        elif endpoint_type == 'health_check':
            response = api_client.health_check()
        else:
            raise ValueError(f"Unknown endpoint type: {endpoint_type}")
            
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Determine status code: 200 for success responses, appropriate error code otherwise
        status_code = 200
        if isinstance(response, dict) and response.get('status') == 'error':
            status_code = response.get('status_code', 500)
        
        # Record API request in metrics collector
        metrics_collector.record_api_request(
            endpoint=endpoint_type,
            response_time=response_time,
            status_code=status_code,
            method="GET" if endpoint_type in ['get_borrow_rate', 'health_check'] else "POST"
        )
        
        return response
        
    except Exception as e:
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Record failed request
        metrics_collector.record_api_request(
            endpoint=endpoint_type,
            response_time=response_time,
            status_code=500,
            method="GET" if endpoint_type in ['get_borrow_rate', 'health_check'] else "POST"
        )
        
        logger.error(f"Error executing {endpoint_type} request: {str(e)}")
        return {"status": "error", "error": str(e)}


def execute_concurrent_requests(param_list, endpoint_type, concurrency, metrics_collector):
    """
    Execute multiple API requests concurrently
    
    Args:
        param_list (list): List of parameter dictionaries for API requests
        endpoint_type (str): Type of endpoint to call
        concurrency (int): Maximum number of concurrent requests
        metrics_collector: Collector for recording metrics
        
    Returns:
        list: List of API response data
    """
    # Create API client instances (one per worker to avoid thread safety issues)
    api_clients = [create_api_client() for _ in range(concurrency)]
    
    results = []
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        
        for i, params in enumerate(param_list):
            # Use round-robin assignment of API clients
            client_index = i % concurrency
            api_client = api_clients[client_index]
            
            # Submit task to executor
            future = executor.submit(
                execute_api_request,
                api_client,
                params,
                endpoint_type,
                metrics_collector
            )
            futures.append(future)
        
        # Collect results as they complete
        for future in futures:
            results.append(future.result())
    
    return results


class TestAPILatency:
    """
    Test class for API latency performance tests
    """
    
    @classmethod
    def setup_class(cls):
        """
        Set up test class with shared resources
        
        Args:
            cls (TestAPILatency): The test class
        """
        # Get test settings
        cls.settings = get_test_settings()
        
        # Create API client
        cls.api_client = create_api_client()
        
        # Wait for API to be ready
        cls.api_client.wait_for_api_ready()
        
        # Get metrics collector
        cls.metrics_collector = get_api_metrics_collector()
        
        logger.info("TestAPILatency setup complete")
    
    @classmethod
    def teardown_class(cls):
        """
        Clean up resources after all tests complete
        
        Args:
            cls (TestAPILatency): The test class
        """
        # Generate performance report from collected metrics
        cls.metrics_collector.generate_report(
            output_path="./performance_reports",
            formats=["html", "json"],
            include_charts=True
        )
        
        logger.info("TestAPILatency teardown complete")
    
    @pytest.mark.performance
    def test_health_endpoint_latency(self):
        """
        Test latency of the health check endpoint
        """
        logger.info("Starting health endpoint latency test")
        
        # Use metrics_collection context manager
        with metrics_collection(self.metrics_collector, test_info={"name": "health_endpoint_latency"}):
            # Execute health check requests multiple times
            for _ in range(50):  # 50 requests for health check
                execute_api_request(
                    self.api_client,
                    {},
                    'health_check',
                    self.metrics_collector
                )
        
        # Calculate response time statistics
        response_times = self.metrics_collector.api_collector.collect()["endpoints"].get("health_check", {}).get("response_times", [])
        stats = calculate_statistics(response_times)
        
        # Verify p95 response time is below threshold
        p95_threshold = self.settings.get_response_time_threshold()
        assert stats['p95'] < p95_threshold, f"Health endpoint p95 latency ({stats['p95']:.2f}ms) exceeds threshold ({p95_threshold}ms)"
        
        logger.info(f"Health endpoint latency statistics: min={stats['min']:.2f}ms, avg={stats['mean']:.2f}ms, p95={stats['p95']:.2f}ms, max={stats['max']:.2f}ms")
    
    @pytest.mark.performance
    def test_borrow_rate_endpoint_latency(self):
        """
        Test latency of the borrow rate endpoint
        """
        logger.info("Starting borrow rate endpoint latency test")
        
        # Generate test parameters for borrow rate requests
        test_params = generate_test_parameters(100)  # 100 requests for borrow rate
        
        # Use metrics_collection context manager
        with metrics_collection(self.metrics_collector, test_info={"name": "borrow_rate_endpoint_latency"}):
            # Execute borrow rate requests for each test parameter
            for params in test_params:
                execute_api_request(
                    self.api_client,
                    params,
                    'get_borrow_rate',
                    self.metrics_collector
                )
        
        # Calculate response time statistics
        response_times = self.metrics_collector.api_collector.collect()["endpoints"].get("get_borrow_rate", {}).get("response_times", [])
        stats = calculate_statistics(response_times)
        
        # Verify p95 response time is below threshold
        p95_threshold = self.settings.get_response_time_threshold()
        assert stats['p95'] < p95_threshold, f"Borrow rate endpoint p95 latency ({stats['p95']:.2f}ms) exceeds threshold ({p95_threshold}ms)"
        
        logger.info(f"Borrow rate endpoint latency statistics: min={stats['min']:.2f}ms, avg={stats['mean']:.2f}ms, p95={stats['p95']:.2f}ms, max={stats['max']:.2f}ms")
    
    @pytest.mark.performance
    def test_calculate_locate_endpoint_latency(self):
        """
        Test latency of the calculate locate fee endpoint
        """
        logger.info("Starting calculate locate fee endpoint latency test")
        
        # Generate test parameters for locate fee calculations
        test_params = generate_test_parameters(100)  # 100 requests for locate fee
        
        # Use metrics_collection context manager
        with metrics_collection(self.metrics_collector, test_info={"name": "calculate_locate_endpoint_latency"}):
            # Execute calculate locate fee requests for each test parameter
            for params in test_params:
                execute_api_request(
                    self.api_client,
                    params,
                    'calculate_locate_fee',
                    self.metrics_collector
                )
        
        # Calculate response time statistics
        response_times = self.metrics_collector.api_collector.collect()["endpoints"].get("calculate_locate_fee", {}).get("response_times", [])
        stats = calculate_statistics(response_times)
        
        # Verify p95 response time is below threshold
        p95_threshold = self.settings.get_response_time_threshold()
        assert stats['p95'] < p95_threshold, f"Calculate locate endpoint p95 latency ({stats['p95']:.2f}ms) exceeds threshold ({p95_threshold}ms)"
        
        logger.info(f"Calculate locate endpoint latency statistics: min={stats['min']:.2f}ms, avg={stats['mean']:.2f}ms, p95={stats['p95']:.2f}ms, max={stats['max']:.2f}ms")
    
    @pytest.mark.performance
    @pytest.mark.load
    def test_api_latency_under_load(self):
        """
        Test API latency under concurrent load
        """
        logger.info("Starting API latency under load test")
        
        # Get concurrency level and request count from test settings
        concurrency = self.settings.concurrent_users
        request_count = self.settings.target_rps
        
        logger.info(f"Running load test with {concurrency} concurrent users and {request_count} requests")
        
        # Generate test parameters for API requests
        test_params = generate_test_parameters(request_count)
        
        # Use metrics_collection context manager
        with metrics_collection(self.metrics_collector, test_info={"name": "api_latency_under_load"}):
            # Execute concurrent API requests using execute_concurrent_requests
            execute_concurrent_requests(
                test_params,
                'calculate_locate_fee',
                concurrency,
                self.metrics_collector
            )
        
        # Calculate response time statistics
        response_times = self.metrics_collector.api_collector.collect()["endpoints"].get("calculate_locate_fee", {}).get("response_times", [])
        stats = calculate_statistics(response_times)
        
        # Verify p95 response time is below threshold under load
        p95_threshold = self.settings.get_response_time_threshold()
        assert stats['p95'] < p95_threshold, f"API under load p95 latency ({stats['p95']:.2f}ms) exceeds threshold ({p95_threshold}ms)"
        
        throughput = len(response_times) / (max(response_times) / 1000)
        logger.info(f"API under load latency statistics: min={stats['min']:.2f}ms, avg={stats['mean']:.2f}ms, p95={stats['p95']:.2f}ms, max={stats['max']:.2f}ms")
        logger.info(f"Achieved throughput: {throughput:.2f} requests/second")
    
    @pytest.mark.performance
    @pytest.mark.stress
    def test_api_latency_stress_test(self):
        """
        Stress test API latency with high concurrency
        """
        logger.info("Starting API latency stress test")
        
        # Set high concurrency level (2000+ requests/second)
        concurrency = 100
        request_count = 2000
        
        logger.info(f"Running stress test with {concurrency} concurrent users and {request_count} requests")
        
        # Generate test parameters for API requests
        test_params = generate_test_parameters(request_count)
        
        # Use metrics_collection context manager
        with metrics_collection(self.metrics_collector, test_info={"name": "api_latency_stress_test"}):
            # Execute concurrent API requests using execute_concurrent_requests
            execute_concurrent_requests(
                test_params,
                'calculate_locate_fee',
                concurrency,
                self.metrics_collector
            )
        
        # Calculate response time statistics
        response_times = self.metrics_collector.api_collector.collect()["endpoints"].get("calculate_locate_fee", {}).get("response_times", [])
        stats = calculate_statistics(response_times)
        
        # For stress test, we use a higher threshold (150% of normal)
        stress_threshold = self.settings.get_response_time_threshold() * 1.5
        assert stats['p95'] < stress_threshold, f"API stress test p95 latency ({stats['p95']:.2f}ms) exceeds threshold ({stress_threshold}ms)"
        
        throughput = len(response_times) / (max(response_times) / 1000)
        logger.info(f"API stress test latency statistics: min={stats['min']:.2f}ms, avg={stats['mean']:.2f}ms, p95={stats['p95']:.2f}ms, max={stats['max']:.2f}ms")
        logger.info(f"Stress test throughput: {throughput:.2f} requests/second")
    
    @pytest.mark.performance
    @pytest.mark.spike
    def test_api_latency_spike_test(self):
        """
        Test API latency during traffic spikes
        """
        logger.info("Starting API latency spike test")
        
        # Execute baseline requests at normal load
        baseline_concurrency = 20
        baseline_count = 100
        
        logger.info(f"Running baseline load with {baseline_concurrency} concurrent users and {baseline_count} requests")
        
        # Generate test parameters for baseline
        baseline_params = generate_test_parameters(baseline_count)
        
        # Execute baseline requests
        execute_concurrent_requests(
            baseline_params,
            'calculate_locate_fee',
            baseline_concurrency,
            self.metrics_collector
        )
        
        # Suddenly increase to high concurrency (3000 requests/second)
        spike_concurrency = 150
        spike_count = 3000
        
        logger.info(f"Running spike load with {spike_concurrency} concurrent users and {spike_count} requests")
        
        # Generate test parameters for spike
        spike_params = generate_test_parameters(spike_count)
        
        # Use metrics_collection context manager
        with metrics_collection(self.metrics_collector, test_info={"name": "api_latency_spike_test"}):
            # Execute concurrent API requests using execute_concurrent_requests
            execute_concurrent_requests(
                spike_params,
                'calculate_locate_fee',
                spike_concurrency,
                self.metrics_collector
            )
        
        # Calculate response time statistics
        response_times = self.metrics_collector.api_collector.collect()["endpoints"].get("calculate_locate_fee", {}).get("response_times", [])
        stats = calculate_statistics(response_times)
        
        # For spike test, we use an even higher threshold (200% of normal)
        spike_threshold = self.settings.get_response_time_threshold() * 2
        assert stats['p95'] < spike_threshold, f"API spike test p95 latency ({stats['p95']:.2f}ms) exceeds threshold ({spike_threshold}ms)"
        
        throughput = len(response_times) / (max(response_times) / 1000)
        logger.info(f"API spike test latency statistics: min={stats['min']:.2f}ms, avg={stats['mean']:.2f}ms, p95={stats['p95']:.2f}ms, max={stats['max']:.2f}ms")
        logger.info(f"Spike test throughput: {throughput:.2f} requests/second")