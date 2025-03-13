"""
Performance tests for system resource utilization of the Borrow Rate & Locate Fee Pricing Engine.

This module implements tests to verify that the system operates within expected resource
constraints under various load conditions, monitoring CPU, memory, disk I/O, and
network usage to ensure efficient resource utilization.
"""

import pytest  # pytest 7.0.0+
import time  # standard library
import logging  # standard library
import requests  # requests 2.28.0+
from concurrent.futures import ThreadPoolExecutor  # standard library
import psutil  # psutil 5.9.0+

from src.test.performance_tests.config.settings import get_test_settings
from src.test.metrics.collectors.resource_metrics import ResourceMetricsCollector
from src.test.performance_tests.helpers.analysis import ResourceMetricAnalyzer
from src.test.performance_tests.helpers.reporting import generate_report
from src.test.performance_tests.helpers.metrics_collector import create_metrics_collector

# Configure logger
logger = logging.getLogger(__name__)

# Default resource utilization thresholds (percentages)
RESOURCE_THRESHOLDS = {
    "cpu_utilization": 80,  # 80% CPU utilization threshold
    "memory_utilization": 80,  # 80% memory utilization threshold
    "disk_io": 70,  # 70% disk I/O utilization threshold
    "network_io": 60  # 60% network I/O utilization threshold
}

# Test durations in seconds
TEST_DURATIONS = {
    "short": 30,    # 30 seconds for quick tests
    "medium": 300,  # 5 minutes for medium-length tests
    "long": 3600    # 1 hour for endurance tests
}


def generate_api_load(endpoint, requests_per_second, duration_seconds, request_params):
    """
    Generate load on the API by making concurrent requests.
    
    Args:
        endpoint (str): API endpoint to call
        requests_per_second (int): Target requests per second
        duration_seconds (int): Duration of load generation in seconds
        request_params (dict): Parameters to include in the requests
        
    Returns:
        dict: Summary of load generation results
    """
    total_requests = requests_per_second * duration_seconds
    logger.info(f"Generating load: {requests_per_second} RPS for {duration_seconds}s ({total_requests} total requests)")
    
    # Calculate total number of requests to make based on duration and rate
    batch_size = min(requests_per_second, 100)  # Limit batch size for better control
    
    # Track metrics
    successful_requests = 0
    failed_requests = 0
    response_times = []
    
    start_time = time.time()
    end_time = start_time + duration_seconds
    
    with ThreadPoolExecutor(max_workers=min(requests_per_second, 200)) as executor:
        while time.time() < end_time:
            batch_start = time.time()
            futures = []
            
            # Submit API request tasks to the executor
            for _ in range(batch_size):
                if time.time() >= end_time:
                    break
                futures.append(executor.submit(make_api_request, endpoint, request_params))
            
            # Process results from this batch
            for future in futures:
                try:
                    result = future.result()
                    if result.get('status_code', 500) < 400:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                    response_times.append(result.get('time', 0))
                except Exception as e:
                    logger.error(f"Error processing request: {str(e)}")
                    failed_requests += 1
            
            # Calculate sleep time to maintain the target rate
            batch_end = time.time()
            batch_duration = batch_end - batch_start
            expected_duration = batch_size / requests_per_second
            
            if batch_duration < expected_duration:
                time.sleep(expected_duration - batch_duration)
    
    # Calculate final metrics
    actual_duration = time.time() - start_time
    actual_rps = (successful_requests + failed_requests) / actual_duration if actual_duration > 0 else 0
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    result = {
        "target_rps": requests_per_second,
        "actual_rps": actual_rps,
        "duration": actual_duration,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "total_requests": successful_requests + failed_requests,
        "avg_response_time": avg_response_time
    }
    
    logger.info(f"Load generation complete: {result['total_requests']} requests, {result['actual_rps']:.2f} RPS")
    return result


def make_api_request(endpoint, params):
    """
    Make a single API request with the given parameters.
    
    Args:
        endpoint (str): API endpoint to call
        params (dict): Parameters to include in the request
        
    Returns:
        dict: Request result with timing information
    """
    settings = get_test_settings()
    api_url = settings.get_api_url(endpoint)
    api_key = settings.test_api_key
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    try:
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        status_code = response.status_code
        response_data = response.json() if response.status_code < 400 else {}
    except Exception as e:
        logger.error(f"Error making API request: {str(e)}")
        status_code = 500
        response_data = {}
    
    end_time = time.time()
    response_time = end_time - start_time
    
    return {
        "status_code": status_code,
        "time": response_time,
        "data": response_data
    }


def setup_resource_metrics_collector():
    """
    Set up a resource metrics collector with appropriate configuration.
    
    Returns:
        ResourceMetricsCollector: Configured resource metrics collector
    """
    config = {
        "collection_interval": 1.0  # Collect metrics every 1 second
    }
    
    # Create resource metrics collector with appropriate configuration
    return ResourceMetricsCollector(config)


class TestResourceUtilization:
    """
    Test class for resource utilization performance tests.
    
    These tests verify that the system operates within expected resource constraints
    under various load conditions, from idle to heavy load scenarios.
    """
    
    @classmethod
    def setup_class(cls):
        """
        Set up test class with shared resources.
        
        This method is called once before any tests in the class are run.
        """
        # Initialize test settings
        cls.settings = get_test_settings()
        
        # Set up resource metrics collector
        cls.metrics_collector = setup_resource_metrics_collector()
        
        # Initialize resource metric analyzer with appropriate thresholds
        cls.metric_analyzer = ResourceMetricAnalyzer(RESOURCE_THRESHOLDS)
        
        logger.info("Initialized TestResourceUtilization test class")
    
    @classmethod
    def teardown_class(cls):
        """
        Clean up resources after all tests complete.
        
        This method is called once after all tests in the class are run.
        """
        # Ensure resource metrics collector is stopped
        if cls.metrics_collector and hasattr(cls.metrics_collector, '_is_collecting') and cls.metrics_collector._is_collecting:
            cls.metrics_collector.stop_collection()
        
        # Generate final report if needed
        if hasattr(cls, 'metrics_collector') and hasattr(cls.metrics_collector, 'last_metrics') and cls.metrics_collector.last_metrics:
            report_path = getattr(cls.settings, 'report_path', './reports')
            generate_report(cls.metrics_collector.last_metrics, report_path, formats=['html', 'json'], include_charts=True)
        
        logger.info("Cleaned up TestResourceUtilization test class")
    
    def test_idle_resource_utilization(self):
        """
        Test resource utilization when system is idle.
        
        This establishes a baseline for resource usage when the system is not under load.
        """
        # Start resource metrics collection
        self.metrics_collector.start_collection()
        
        # Wait for a short period (10 seconds) with no load
        time.sleep(10)
        
        # Stop resource metrics collection
        self.metrics_collector.stop_collection()
        
        # Collect and analyze resource metrics
        metrics = self.metrics_collector.collect()
        
        # Get baseline resource utilization
        cpu_util = metrics["overall"].get("cpu_avg", 0)
        memory_util = metrics["overall"].get("memory_avg", 0)
        
        # Assert that idle resource utilization is below minimum thresholds
        assert cpu_util < 50, f"Idle CPU utilization ({cpu_util}%) exceeds expected threshold (50%)"
        assert memory_util < 60, f"Idle memory utilization ({memory_util}%) exceeds expected threshold (60%)"
        
        logger.info(f"Idle resource utilization: CPU={cpu_util}%, Memory={memory_util}%")
    
    def test_normal_load_resource_utilization(self):
        """
        Test resource utilization under normal API load.
        
        This verifies that the system uses resources efficiently under typical load.
        """
        # Start resource metrics collection
        self.metrics_collector.start_collection()
        
        # Generate normal API load (500 requests/second for 30 seconds)
        request_params = {
            "ticker": "AAPL",
            "position_value": 100000,
            "loan_days": 30,
            "client_id": "test_client"
        }
        generate_api_load("/calculate-locate", 500, TEST_DURATIONS["short"], request_params)
        
        # Stop resource metrics collection
        self.metrics_collector.stop_collection()
        
        # Collect and analyze resource metrics
        metrics = self.metrics_collector.collect()
        analysis_result = self.metric_analyzer.analyze(metrics)
        
        # Assert that resource utilization is within normal thresholds
        assert analysis_result["status"] == "PASS", f"Resource utilization exceeds thresholds: {analysis_result.get('failures', [])}"
        
        # Log test results
        cpu_util = metrics["overall"].get("cpu_avg", 0)
        memory_util = metrics["overall"].get("memory_avg", 0)
        logger.info(f"Normal load resource utilization: CPU={cpu_util}%, Memory={memory_util}%")
    
    def test_high_load_resource_utilization(self):
        """
        Test resource utilization under high API load.
        
        This verifies that the system remains stable under high but expected load.
        """
        # Start resource metrics collection
        self.metrics_collector.start_collection()
        
        # Generate high API load (1000 requests/second for 30 seconds)
        request_params = {
            "ticker": "AAPL",
            "position_value": 100000,
            "loan_days": 30,
            "client_id": "test_client"
        }
        generate_api_load("/calculate-locate", 1000, TEST_DURATIONS["short"], request_params)
        
        # Stop resource metrics collection
        self.metrics_collector.stop_collection()
        
        # Collect and analyze resource metrics
        metrics = self.metrics_collector.collect()
        analysis_result = self.metric_analyzer.analyze(metrics)
        
        # Assert that resource utilization is within high load thresholds
        assert analysis_result["status"] == "PASS", f"Resource utilization exceeds thresholds: {analysis_result.get('failures', [])}"
        
        # Log test results
        cpu_util = metrics["overall"].get("cpu_max", 0)
        memory_util = metrics["overall"].get("memory_max", 0)
        logger.info(f"High load resource utilization: CPU peak={cpu_util}%, Memory peak={memory_util}%")
    
    @pytest.mark.stress
    def test_stress_load_resource_utilization(self):
        """
        Test resource utilization under stress API load.
        
        This test pushes the system beyond normal operating conditions to identify breaking points.
        """
        # Start resource metrics collection
        self.metrics_collector.start_collection()
        
        # Generate stress API load (2000+ requests/second for 30 seconds)
        request_params = {
            "ticker": "AAPL",
            "position_value": 100000,
            "loan_days": 30,
            "client_id": "test_client"
        }
        generate_api_load("/calculate-locate", 2000, TEST_DURATIONS["short"], request_params)
        
        # Stop resource metrics collection
        self.metrics_collector.stop_collection()
        
        # Collect and analyze resource metrics
        metrics = self.metrics_collector.collect()
        
        # We expect high resource usage but still want to avoid complete exhaustion
        cpu_util = metrics["overall"].get("cpu_max", 0)
        memory_util = metrics["overall"].get("memory_max", 0)
        
        # Assert that resource utilization is within stress thresholds
        assert cpu_util < 95, f"Stress test CPU utilization ({cpu_util}%) exceeds critical threshold (95%)"
        assert memory_util < 95, f"Stress test memory utilization ({memory_util}%) exceeds critical threshold (95%)"
        
        # Log test results
        logger.info(f"Stress load resource utilization: CPU peak={cpu_util}%, Memory peak={memory_util}%")
    
    @pytest.mark.endurance
    def test_endurance_resource_utilization(self):
        """
        Test resource utilization under sustained load over time.
        
        This verifies that the system maintains stable resource usage during extended operation.
        """
        # Start resource metrics collection
        self.metrics_collector.start_collection()
        
        # Generate sustained API load (700 requests/second for 5 minutes)
        request_params = {
            "ticker": "AAPL",
            "position_value": 100000,
            "loan_days": 30,
            "client_id": "test_client"
        }
        generate_api_load("/calculate-locate", 700, TEST_DURATIONS["medium"], request_params)
        
        # Stop resource metrics collection
        self.metrics_collector.stop_collection()
        
        # Collect and analyze resource metrics
        metrics = self.metrics_collector.collect()
        trend_analysis = self.metric_analyzer.analyze_resource_trends(metrics)
        
        # Analyze resource utilization trends over time
        assert trend_analysis["status"] != "WARN", f"Resource utilization shows concerning trends: {trend_analysis.get('concerns', [])}"
        
        # Assert that resource utilization remains stable
        cpu_util = metrics["overall"].get("cpu_avg", 0)
        memory_util = metrics["overall"].get("memory_avg", 0)
        
        # Verify no memory leaks (memory should not grow continuously)
        memory_trend = trend_analysis.get("trends", {}).get("memory", {})
        assert not memory_trend.get("is_concerning", False), "Memory usage shows concerning upward trend indicating possible memory leak"
        
        # Log test results
        logger.info(f"Endurance test resource utilization: CPU avg={cpu_util}%, Memory avg={memory_util}%")
    
    @pytest.mark.stress
    def test_spike_resource_utilization(self):
        """
        Test resource utilization during traffic spikes.
        
        This verifies that the system can handle sudden increases in load and return to normal.
        """
        # Start resource metrics collection
        self.metrics_collector.start_collection()
        
        request_params = {
            "ticker": "AAPL",
            "position_value": 100000,
            "loan_days": 30,
            "client_id": "test_client"
        }
        
        # Generate normal API load (500 requests/second for 30 seconds)
        generate_api_load("/calculate-locate", 500, 30, request_params)
        
        # Generate spike in load (3000 requests/second for 10 seconds)
        generate_api_load("/calculate-locate", 3000, 10, request_params)
        
        # Return to normal load (500 requests/second for 30 seconds)
        generate_api_load("/calculate-locate", 500, 30, request_params)
        
        # Stop resource metrics collection
        self.metrics_collector.stop_collection()
        
        # Collect and analyze resource metrics
        metrics = self.metrics_collector.collect()
        
        # Check maximum resource utilization during spike
        cpu_max = metrics["overall"].get("cpu_max", 0)
        memory_max = metrics["overall"].get("memory_max", 0)
        
        # Assert that system recovers after spike
        assert cpu_max < 95, f"CPU utilization during spike ({cpu_max}%) exceeds critical threshold (95%)"
        assert memory_max < 95, f"Memory utilization during spike ({memory_max}%) exceeds critical threshold (95%)"
        
        # Verify recovery if time series data is available
        time_series = self._extract_time_series(metrics)
        if time_series and len(time_series) >= 10:
            # Verify that CPU usage returns to normal levels after spike
            last_10_points = time_series[-10:]
            if all("cpu" in point for point in last_10_points):
                avg_cpu_end = sum(p["cpu"] for p in last_10_points) / len(last_10_points)
                assert avg_cpu_end < 70, f"CPU utilization did not return to normal after spike: {avg_cpu_end}%"
        
        # Log test results
        logger.info(f"Spike test resource utilization: CPU max={cpu_max}%, Memory max={memory_max}%")
    
    def test_calculation_intensive_resource_utilization(self):
        """
        Test resource utilization during calculation-intensive operations.
        
        This verifies that the system handles CPU-intensive calculations efficiently.
        """
        # Start resource metrics collection
        self.metrics_collector.start_collection()
        
        # Generate load focused on calculation-intensive endpoints
        request_params = {
            "ticker": "GME",  # A hard-to-borrow stock with complex calculations
            "position_value": 500000,
            "loan_days": 90,
            "client_id": "test_client"
        }
        generate_api_load("/calculate-locate", 300, TEST_DURATIONS["short"], request_params)
        
        # Stop resource metrics collection
        self.metrics_collector.stop_collection()
        
        # Collect and analyze resource metrics
        metrics = self.metrics_collector.collect()
        
        # Get CPU utilization
        cpu_util = metrics["overall"].get("cpu_avg", 0)
        
        # Assert that CPU utilization is within expected range
        assert cpu_util < RESOURCE_THRESHOLDS["cpu_utilization"], f"CPU utilization ({cpu_util}%) exceeds threshold for calculation-intensive operations"
        
        # Log test results
        logger.info(f"Calculation-intensive resource utilization: CPU avg={cpu_util}%")
    
    def test_data_intensive_resource_utilization(self):
        """
        Test resource utilization during data-intensive operations.
        
        This verifies that the system handles memory and I/O intensive operations efficiently.
        """
        # Start resource metrics collection
        self.metrics_collector.start_collection()
        
        # Generate load focused on data-intensive endpoints
        # Use multiple different tickers to force data fetching
        tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "FB", "TSLA", "NVDA", "NFLX", "PYPL", "ADBE"]
        
        for ticker in tickers:
            request_params = {
                "ticker": ticker,
                "position_value": 100000,
                "loan_days": 30,
                "client_id": "test_client"
            }
            # Lower RPS but across multiple tickers to stress data retrieval
            generate_api_load("/rates", 50, 5, {"ticker": ticker})
        
        # Stop resource metrics collection
        self.metrics_collector.stop_collection()
        
        # Collect and analyze resource metrics
        metrics = self.metrics_collector.collect()
        
        # Get memory and disk I/O utilization
        memory_util = metrics["overall"].get("memory_avg", 0)
        disk_io = metrics["overall"].get("disk_usage_avg", 0) if "disk_usage_avg" in metrics["overall"] else 0
        
        # Assert that memory and disk I/O are within expected ranges
        assert memory_util < RESOURCE_THRESHOLDS["memory_utilization"], f"Memory utilization ({memory_util}%) exceeds threshold for data-intensive operations"
        if disk_io > 0:  # Only assert if disk I/O metrics are available
            assert disk_io < RESOURCE_THRESHOLDS["disk_io"], f"Disk I/O utilization ({disk_io}%) exceeds threshold for data-intensive operations"
        
        # Log test results
        logger.info(f"Data-intensive resource utilization: Memory avg={memory_util}%, Disk I/O avg={disk_io}%")
    
    @pytest.mark.scaling
    def test_resource_scaling(self):
        """
        Test how resource utilization scales with increasing load.
        
        This verifies that resource usage scales linearly or sub-linearly with load.
        """
        load_levels = [200, 400, 600, 800, 1000]
        cpu_utilization = []
        memory_utilization = []
        
        request_params = {
            "ticker": "AAPL",
            "position_value": 100000,
            "loan_days": 30,
            "client_id": "test_client"
        }
        
        # Generate increasing levels of load
        for rps in load_levels:
            # Start resource metrics collection
            self.metrics_collector.start_collection()
            
            # Generate load at this level
            generate_api_load("/calculate-locate", rps, 20, request_params)
            
            # Stop resource metrics collection
            self.metrics_collector.stop_collection()
            
            # Collect and analyze resource metrics at each load level
            metrics = self.metrics_collector.collect()
            
            # Record utilization
            cpu_util = metrics["overall"].get("cpu_avg", 0)
            memory_util = metrics["overall"].get("memory_avg", 0)
            
            cpu_utilization.append(cpu_util)
            memory_utilization.append(memory_util)
            
            logger.info(f"Load level {rps} RPS: CPU={cpu_util}%, Memory={memory_util}%")
        
        # Calculate scaling factors for each resource type
        cpu_scaling = []
        memory_scaling = []
        
        for i in range(1, len(load_levels)):
            load_increase = load_levels[i] / load_levels[i-1]
            cpu_increase = cpu_utilization[i] / max(cpu_utilization[i-1], 0.1)  # Avoid division by zero
            memory_increase = memory_utilization[i] / max(memory_utilization[i-1], 0.1)  # Avoid division by zero
            
            cpu_scaling.append(cpu_increase / load_increase)
            memory_scaling.append(memory_increase / load_increase)
        
        # Calculate average scaling factors
        avg_cpu_scaling = sum(cpu_scaling) / len(cpu_scaling) if cpu_scaling else 0
        avg_memory_scaling = sum(memory_scaling) / len(memory_scaling) if memory_scaling else 0
        
        # Assert that resource utilization scales linearly or sub-linearly
        assert avg_cpu_scaling <= 1.2, f"CPU utilization scales super-linearly with load (factor: {avg_cpu_scaling})"
        assert avg_memory_scaling <= 1.2, f"Memory utilization scales super-linearly with load (factor: {avg_memory_scaling})"
        
        # Log test results
        logger.info(f"Resource scaling factors: CPU={avg_cpu_scaling}, Memory={avg_memory_scaling}")
    
    def _extract_time_series(self, metrics):
        """
        Extract time series data from metrics if available.
        
        Args:
            metrics (dict): Collected metrics
            
        Returns:
            list: Time series data points or empty list if not available
        """
        # Try to find time series data in the metrics
        if "cpu" in metrics and isinstance(metrics["cpu"], dict):
            if "time_series" in metrics["cpu"]:
                return metrics["cpu"]["time_series"]
            
        # If no explicit time series data, check if there might be sequential metrics
        # that could be used to infer time series behavior
        if "cpu" in metrics and isinstance(metrics["cpu"], dict):
            for key, value in metrics["cpu"].items():
                if isinstance(value, list) and len(value) > 0:
                    # Found a list of CPU-related metrics, could use as time series
                    return [{"cpu": v} for v in value]
        
        return []