"""
Metrics Collection Module for the Borrow Rate & Locate Fee Pricing Engine.

This module implements a comprehensive metrics collection system for performance testing
of the Borrow Rate & Locate Fee Pricing Engine. It coordinates the collection of API,
calculation, and resource metrics during test execution, providing a unified interface
for starting, stopping, and retrieving metrics across different collector types.
"""

import logging
import time
from datetime import datetime
import os
from pathlib import Path
import json
from typing import Dict, List, Any, Optional, Union

from src.test.performance_tests.config.settings import get_test_settings
from src.test.metrics.collectors.api_metrics import APIMetricsCollector
from src.test.metrics.collectors.calculation_metrics import CalculationMetricsCollector
from src.test.metrics.collectors.resource_metrics import ResourceMetricsCollector
from src.test.performance_tests.helpers.analysis import analyze_performance_results
from src.test.performance_tests.helpers.reporting import generate_report

# Configure logging
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_METRICS_CONFIG = {"api": {"enabled": True}, "calculation": {"enabled": True}, "resource": {"enabled": True, "collection_interval": 1.0}}

# Default output directory
DEFAULT_OUTPUT_DIR = Path("./metrics_output")


def create_metrics_collector(config: Dict) -> 'MetricsCollector':
    """
    Factory function to create a MetricsCollector instance with the specified configuration.
    
    Args:
        config: Configuration dictionary for the metrics collector
        
    Returns:
        Configured MetricsCollector instance
    """
    # Merge provided config with defaults
    merged_config = DEFAULT_METRICS_CONFIG.copy()
    for key, value in config.items():
        if key in merged_config and isinstance(merged_config[key], dict) and isinstance(value, dict):
            merged_config[key].update(value)
        else:
            merged_config[key] = value
    
    return MetricsCollector(merged_config)


def save_metrics_to_file(metrics_data: Dict, output_path: str, filename: str) -> str:
    """
    Save collected metrics to a JSON file.
    
    Args:
        metrics_data: Dictionary containing metrics data
        output_path: Directory to save the file
        filename: Name of the file
        
    Returns:
        Path to the saved metrics file
    """
    # Ensure output directory exists
    output_dir = ensure_output_directory(output_path)
    
    # Create full file path
    file_path = output_dir / filename
    
    try:
        # Write metrics data to JSON file
        with open(file_path, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        logger.info(f"Saved metrics to {file_path}")
        return str(file_path)
    except Exception as e:
        logger.error(f"Failed to save metrics to {file_path}: {e}")
        return None


def load_metrics_from_file(file_path: str) -> Dict:
    """
    Load metrics data from a previously saved JSON file.
    
    Args:
        file_path: Path to the metrics file
        
    Returns:
        Loaded metrics data
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Metrics file not found: {file_path}")
    
    try:
        with open(path, 'r') as f:
            metrics_data = json.load(f)
        
        logger.info(f"Loaded metrics from {file_path}")
        return metrics_data
    except Exception as e:
        logger.error(f"Failed to load metrics from {file_path}: {e}")
        raise


def ensure_output_directory(output_path: str) -> Path:
    """
    Ensure the output directory exists, creating it if necessary.
    
    Args:
        output_path: Path to the output directory
        
    Returns:
        Path object for the output directory
    """
    path = Path(output_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


class MetricsCollector:
    """
    Main class that coordinates the collection of various metrics during performance testing.
    
    This class manages multiple specialized metrics collectors (API, calculation, resource)
    and provides a unified interface for starting, stopping, and retrieving metrics.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the MetricsCollector with the specified configuration.
        
        Args:
            config: Configuration dictionary for the metrics collector
        """
        self.config = config
        self.test_info = {}
        self.is_collecting = False
        self.start_time = None
        self.end_time = None
        self.last_metrics = {}
        
        # Initialize API metrics collector if enabled
        self.api_collector = None
        if config.get("api", {}).get("enabled", True):
            self.api_collector = APIMetricsCollector(config.get("api", {}))
        
        # Initialize calculation metrics collector if enabled
        self.calculation_collector = None
        if config.get("calculation", {}).get("enabled", True):
            self.calculation_collector = CalculationMetricsCollector(config.get("calculation", {}))
        
        # Initialize resource metrics collector if enabled
        self.resource_collector = None
        if config.get("resource", {}).get("enabled", True):
            self.resource_collector = ResourceMetricsCollector(config.get("resource", {}))
        
        logger.info(f"Initialized MetricsCollector with {len([c for c in [self.api_collector, self.calculation_collector, self.resource_collector] if c is not None])} enabled collectors")
    
    def start_collection(self, test_info: Dict):
        """
        Start collecting metrics across all enabled collectors.
        
        Args:
            test_info: Dictionary with information about the test being run
        """
        if self.is_collecting:
            logger.warning("Metrics collection already in progress")
            return
        
        # Update test info
        self.test_info = test_info or {}
        
        # Set start time
        self.start_time = time.time()
        self.is_collecting = True
        
        # Start API metrics collection if enabled
        if self.api_collector:
            self.api_collector.start_collection()
        
        # Start calculation metrics collection if enabled
        if self.calculation_collector:
            self.calculation_collector.start_collection()
        
        # Start resource metrics collection if enabled
        if self.resource_collector:
            self.resource_collector.start_collection()
        
        logger.info(f"Started metrics collection for test: {self.test_info.get('name', 'unnamed')}")
    
    def stop_collection(self) -> Dict:
        """
        Stop collecting metrics across all enabled collectors.
        
        Returns:
            Collected metrics data
        """
        if not self.is_collecting:
            logger.warning("No metrics collection in progress")
            return {}
        
        # Set end time
        self.end_time = time.time()
        
        # Stop API metrics collection if enabled
        if self.api_collector:
            self.api_collector.stop_collection()
        
        # Stop calculation metrics collection if enabled
        if self.calculation_collector:
            self.calculation_collector.stop_collection()
        
        # Stop resource metrics collection if enabled
        if self.resource_collector:
            self.resource_collector.stop_collection()
        
        # Set collection status
        self.is_collecting = False
        
        # Collect metrics from all collectors
        metrics = self.collect_metrics()
        
        # Store last metrics
        self.last_metrics = metrics
        
        duration = self.end_time - self.start_time
        logger.info(f"Stopped metrics collection after {duration:.2f} seconds")
        
        return metrics
    
    def collect_metrics(self) -> Dict:
        """
        Collect metrics from all enabled collectors.
        
        Returns:
            Collected metrics data
        """
        # Initialize metrics dictionary with test info
        metrics = {
            "test_info": self.test_info,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Add test duration
        if self.start_time and self.end_time:
            metrics["duration_seconds"] = self.end_time - self.start_time
        elif self.start_time:
            metrics["duration_seconds"] = time.time() - self.start_time
        
        # Collect API metrics if enabled
        if self.api_collector:
            api_metrics = self.api_collector.collect()
            metrics["api"] = api_metrics
        
        # Collect calculation metrics if enabled
        if self.calculation_collector:
            calculation_metrics = self.calculation_collector.collect()
            metrics["calculation"] = calculation_metrics
        
        # Collect resource metrics if enabled
        if self.resource_collector:
            resource_metrics = self.resource_collector.collect()
            metrics["resource"] = resource_metrics
        
        return metrics
    
    def record_api_request(self, endpoint: str, response_time: float, status_code: int, method: str = "GET"):
        """
        Record an API request with timing and result information.
        
        Args:
            endpoint: The API endpoint called
            response_time: Response time in seconds
            status_code: HTTP status code returned
            method: HTTP method used
        """
        if not self.api_collector:
            return
        
        if not self.is_collecting:
            return
        
        self.api_collector.record_request(endpoint, response_time, status_code, method)
        logger.debug(f"Recorded API request: {method} {endpoint} - {status_code} in {response_time:.6f}s")
    
    def record_calculation(self, calculation_type: str, execution_time: float):
        """
        Record a calculation execution with timing information.
        
        Args:
            calculation_type: The type of calculation (e.g., "borrow_rate", "locate_fee")
            execution_time: Execution time in seconds
        """
        if not self.calculation_collector:
            return
        
        if not self.is_collecting:
            return
        
        self.calculation_collector.record_calculation(calculation_type, execution_time)
        logger.debug(f"Recorded calculation: {calculation_type} in {execution_time:.6f}s")
    
    def record_calculation_accuracy(self, calculation_type: str, expected_result: float, actual_result: float):
        """
        Record the accuracy of a calculation by comparing expected and actual results.
        
        Args:
            calculation_type: The type of calculation (e.g., "borrow_rate", "locate_fee")
            expected_result: The expected result of the calculation
            actual_result: The actual result of the calculation
        """
        if not self.calculation_collector:
            return
        
        if not self.is_collecting:
            return
        
        self.calculation_collector.record_accuracy(calculation_type, expected_result, actual_result)
        logger.debug(f"Recorded calculation accuracy for {calculation_type}: expected={expected_result}, actual={actual_result}")
    
    def save_metrics(self, output_path: str, filename: str) -> str:
        """
        Save the last collected metrics to a file.
        
        Args:
            output_path: Directory to save the file
            filename: Name of the file
            
        Returns:
            Path to the saved metrics file
        """
        if not self.last_metrics:
            logger.warning("No metrics data available to save")
            return None
        
        if not output_path:
            output_path = str(DEFAULT_OUTPUT_DIR)
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            test_name = self.test_info.get("name", "unnamed").replace(" ", "_").lower()
            filename = f"metrics_{test_name}_{timestamp}.json"
        
        return save_metrics_to_file(self.last_metrics, output_path, filename)
    
    def analyze_metrics(self, custom_thresholds: Dict) -> Dict:
        """
        Analyze the last collected metrics against performance thresholds.
        
        Args:
            custom_thresholds: Custom performance thresholds
            
        Returns:
            Analysis results
        """
        if not self.last_metrics:
            logger.warning("No metrics data available to analyze")
            return {}
        
        # Get default thresholds from settings if not provided
        if not custom_thresholds:
            settings = get_test_settings()
            thresholds = {
                "response_time": settings.get_response_time_threshold(),
                "throughput": settings.get_throughput_threshold(),
                "error_rate": settings.get_error_rate_threshold()
            }
        else:
            thresholds = custom_thresholds
        
        # Analyze metrics against thresholds
        analysis_results = analyze_performance_results(self.last_metrics, thresholds)
        
        status = analysis_results.get("status", "UNKNOWN")
        logger.info(f"Metrics analysis completed with status: {status}")
        
        return analysis_results
    
    def generate_report(self, output_path: str, formats: List[str], include_charts: bool) -> Dict:
        """
        Generate a report from the last collected metrics.
        
        Args:
            output_path: Directory to save the report
            formats: List of output formats (html, pdf, json, csv)
            include_charts: Whether to include charts in the report
            
        Returns:
            Dictionary with paths to generated report files
        """
        if not self.last_metrics:
            logger.warning("No metrics data available for reporting")
            return {}
        
        if not output_path:
            output_path = str(DEFAULT_OUTPUT_DIR)
        
        if not formats:
            formats = ["html", "pdf", "json"]
        
        # Generate report
        report_paths = generate_report(
            self.last_metrics,
            output_path,
            formats,
            include_charts,
            self.test_info
        )
        
        logger.info(f"Generated performance report with formats: {formats}")
        
        return report_paths
    
    def reset(self):
        """
        Reset the metrics collector to its initial state.
        """
        # Reset individual collectors
        if self.api_collector:
            self.api_collector.reset()
        
        if self.calculation_collector:
            self.calculation_collector.reset()
        
        if self.resource_collector:
            self.resource_collector.reset()
        
        # Reset collector state
        self.test_info = {}
        self.is_collecting = False
        self.start_time = None
        self.end_time = None
        self.last_metrics = {}
        
        logger.info("Reset metrics collector")
    
    def get_test_duration(self) -> float:
        """
        Get the duration of the current or last test run.
        
        Returns:
            Test duration in seconds
        """
        if self.is_collecting and self.start_time:
            return time.time() - self.start_time
        elif self.start_time and self.end_time:
            return self.end_time - self.start_time
        else:
            return 0.0
    
    def is_api_metrics_enabled(self) -> bool:
        """
        Check if API metrics collection is enabled.
        
        Returns:
            True if API metrics collection is enabled
        """
        return self.api_collector is not None
    
    def is_calculation_metrics_enabled(self) -> bool:
        """
        Check if calculation metrics collection is enabled.
        
        Returns:
            True if calculation metrics collection is enabled
        """
        return self.calculation_collector is not None
    
    def is_resource_metrics_enabled(self) -> bool:
        """
        Check if resource metrics collection is enabled.
        
        Returns:
            True if resource metrics collection is enabled
        """
        return self.resource_collector is not None