"""
Performance Analysis Module for Borrow Rate & Locate Fee Pricing Engine.

This module provides utilities to analyze collected performance metrics against
defined thresholds, detect anomalies, and generate comprehensive analysis results.
The analysis can be used for reporting and validation of system performance against SLAs.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
import numpy as np
import pandas as pd  # pandas 2.0.0+
from scipy import stats  # scipy 1.10.0+
from src.test.performance_tests.config.settings import get_test_settings, TestSettings

# Configure logging
logger = logging.getLogger(__name__)

# Default thresholds for performance metrics if not otherwise specified
DEFAULT_THRESHOLDS = {
    "response_time": 100,  # milliseconds (p95)
    "throughput": 1000,    # requests per second
    "error_rate": 0.1,     # percentage
    "cpu_utilization": 80, # percentage
    "memory_utilization": 80  # percentage
}

# Metrics considered critical for system functionality
CRITICAL_METRICS = ["response_time", "error_rate", "calculation_accuracy"]

def analyze_performance_results(metrics_data: Dict[str, Any], 
                               thresholds: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analyze performance test results against defined thresholds.
    
    Args:
        metrics_data: Dictionary containing performance metrics data
        thresholds: Dictionary of threshold values for each metric
        
    Returns:
        Dictionary with analysis results including pass/fail status for each metric
    """
    # Validate inputs
    if not metrics_data:
        logger.error("Empty metrics data provided for analysis")
        return {"status": "ERROR", "message": "No metrics data provided"}
    
    # Use provided thresholds or defaults
    if not thresholds:
        logger.info("No thresholds provided, using defaults")
        thresholds = DEFAULT_THRESHOLDS
    
    # Extract metrics by category
    api_metrics = extract_api_metrics(metrics_data)
    calculation_metrics = extract_calculation_metrics(metrics_data)
    resource_metrics = extract_resource_metrics(metrics_data)
    
    # Initialize results dictionary
    results = {
        "status": "PASS",
        "api_metrics": {},
        "calculation_metrics": {},
        "resource_metrics": {},
        "critical_failures": []
    }
    
    # Analyze API metrics
    if api_metrics:
        for metric, value in api_metrics.items():
            if metric in thresholds:
                threshold = thresholds[metric]
                # For response time and error rate, lower is better
                if metric in ["response_time", "error_rate"]:
                    status = "PASS" if value <= threshold else "FAIL"
                # For throughput, higher is better
                else:
                    status = "PASS" if value >= threshold else "FAIL"
                
                results["api_metrics"][metric] = {
                    "value": value,
                    "threshold": threshold,
                    "status": status
                }
                
                # Check if this is a critical metric failure
                if status == "FAIL" and metric in CRITICAL_METRICS:
                    results["critical_failures"].append(f"{metric}: {value} (threshold: {threshold})")
    
    # Analyze calculation metrics
    if calculation_metrics:
        for metric, value in calculation_metrics.items():
            if metric in thresholds:
                threshold = thresholds[metric]
                # For execution time, lower is better
                if "time" in metric:
                    status = "PASS" if value <= threshold else "FAIL"
                # For accuracy, higher is better
                else:
                    status = "PASS" if value >= threshold else "FAIL"
                
                results["calculation_metrics"][metric] = {
                    "value": value,
                    "threshold": threshold,
                    "status": status
                }
                
                # Check if this is a critical metric failure
                if status == "FAIL" and metric in CRITICAL_METRICS:
                    results["critical_failures"].append(f"{metric}: {value} (threshold: {threshold})")
    
    # Analyze resource metrics
    if resource_metrics:
        for metric, value in resource_metrics.items():
            if metric in thresholds:
                threshold = thresholds[metric]
                # For utilization metrics, lower is better
                status = "PASS" if value <= threshold else "FAIL"
                
                results["resource_metrics"][metric] = {
                    "value": value,
                    "threshold": threshold,
                    "status": status
                }
    
    # Set overall status based on critical failures
    if results["critical_failures"]:
        results["status"] = "FAIL"
    
    return results

def detect_anomalies(metrics_data: Dict[str, Any], z_threshold: float = 3.0) -> Dict[str, List[Dict[str, Any]]]:
    """
    Detect anomalies in performance metrics using statistical methods.
    
    Args:
        metrics_data: Dictionary containing performance metrics data
        z_threshold: Z-score threshold for anomaly detection (default: 3.0)
        
    Returns:
        Dictionary of detected anomalies grouped by metric
    """
    anomalies = {}
    
    # Process each time series in the metrics data
    for metric_name, metric_data in metrics_data.items():
        # Skip non-time series data
        if not isinstance(metric_data, (list, np.ndarray, pd.Series)) or len(metric_data) < 5:
            continue
        
        # Convert to numpy array if needed
        values = np.array(metric_data)
        
        # Calculate mean and standard deviation
        mean = np.mean(values)
        std = np.std(values)
        
        # Avoid division by zero
        if std == 0:
            continue
        
        # Calculate z-scores
        z_scores = np.abs((values - mean) / std)
        
        # Find anomalies (values with z-score above threshold)
        anomaly_indices = np.where(z_scores > z_threshold)[0]
        
        if len(anomaly_indices) > 0:
            anomalies[metric_name] = []
            
            for idx in anomaly_indices:
                anomalies[metric_name].append({
                    "index": int(idx),
                    "value": float(values[idx]),
                    "z_score": float(z_scores[idx]),
                    "deviation_from_mean": float(values[idx] - mean)
                })
    
    return anomalies

def calculate_percentile(values: List[float], percentile: float) -> float:
    """
    Calculate a specific percentile for a series of values.
    
    Args:
        values: List of numeric values
        percentile: Percentile to calculate (0-100)
        
    Returns:
        The calculated percentile value
    """
    # Validate inputs
    if not values:
        raise ValueError("Empty list provided for percentile calculation")
    
    if not 0 <= percentile <= 100:
        raise ValueError(f"Percentile must be between 0 and 100, got {percentile}")
    
    # Calculate percentile using numpy
    return float(np.percentile(values, percentile))

def calculate_statistics(values: List[float]) -> Dict[str, float]:
    """
    Calculate basic statistics for a series of values.
    
    Args:
        values: List of numeric values
        
    Returns:
        Dictionary with min, max, mean, median, p95, p99 statistics
    """
    # Validate input
    if not values:
        raise ValueError("Empty list provided for statistics calculation")
    
    # Calculate basic statistics
    min_val = float(np.min(values))
    max_val = float(np.max(values))
    mean_val = float(np.mean(values))
    median_val = float(np.median(values))
    
    # Calculate percentiles
    p95 = calculate_percentile(values, 95)
    p99 = calculate_percentile(values, 99)
    
    return {
        "min": min_val,
        "max": max_val,
        "mean": mean_val,
        "median": median_val,
        "p95": p95,
        "p99": p99
    }

def extract_api_metrics(metrics_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract and summarize API metrics from raw metrics data.
    
    Args:
        metrics_data: Dictionary containing performance metrics data
        
    Returns:
        Summarized API metrics
    """
    api_metrics = {}
    
    # Check if metrics_data contains API metrics
    if not metrics_data.get("api", {}):
        return api_metrics
    
    api_data = metrics_data["api"]
    
    # Extract response times if available
    if "response_times" in api_data and api_data["response_times"]:
        response_times = api_data["response_times"]
        
        # Calculate response time percentiles
        api_metrics["response_time"] = calculate_percentile(response_times, 95)
        api_metrics["response_time_p99"] = calculate_percentile(response_times, 99)
    
    # Calculate throughput (requests per second)
    if "request_count" in api_data and "duration_seconds" in api_data:
        request_count = api_data["request_count"]
        duration = api_data["duration_seconds"]
        
        if duration > 0:
            api_metrics["throughput"] = request_count / duration
    
    # Calculate error rate
    if "error_count" in api_data and "request_count" in api_data:
        error_count = api_data["error_count"]
        request_count = api_data["request_count"]
        
        if request_count > 0:
            api_metrics["error_rate"] = (error_count / request_count) * 100
    
    return api_metrics

def extract_calculation_metrics(metrics_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract and summarize calculation metrics from raw metrics data.
    
    Args:
        metrics_data: Dictionary containing performance metrics data
        
    Returns:
        Summarized calculation metrics
    """
    calculation_metrics = {}
    
    # Check if metrics_data contains calculation metrics
    if not metrics_data.get("calculation", {}):
        return calculation_metrics
    
    calc_data = metrics_data["calculation"]
    
    # Extract execution times by calculation type
    if "execution_times" in calc_data:
        exec_times = calc_data["execution_times"]
        
        # Overall execution time statistics
        all_times = []
        for calc_type, times in exec_times.items():
            if times:
                all_times.extend(times)
                # Per-type p95 execution time
                calculation_metrics[f"{calc_type}_execution_time"] = calculate_percentile(times, 95)
        
        # Overall p95 execution time
        if all_times:
            calculation_metrics["execution_time"] = calculate_percentile(all_times, 95)
    
    # Extract calculation accuracy
    if "accuracy" in calc_data:
        accuracy = calc_data["accuracy"]
        
        if isinstance(accuracy, (int, float)):
            calculation_metrics["calculation_accuracy"] = float(accuracy)
        elif isinstance(accuracy, dict):
            # If accuracy is broken down by calculation type
            total_correct = sum(accuracy.get("correct", {}).values())
            total_calculations = sum(accuracy.get("total", {}).values())
            
            if total_calculations > 0:
                calculation_metrics["calculation_accuracy"] = (total_correct / total_calculations) * 100
    
    return calculation_metrics

def extract_resource_metrics(metrics_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract and summarize resource utilization metrics from raw metrics data.
    
    Args:
        metrics_data: Dictionary containing performance metrics data
        
    Returns:
        Summarized resource metrics
    """
    resource_metrics = {}
    
    # Check if metrics_data contains resource metrics
    if not metrics_data.get("resources", {}):
        return resource_metrics
    
    resource_data = metrics_data["resources"]
    
    # Process CPU utilization
    if "cpu" in resource_data:
        cpu_data = resource_data["cpu"]
        
        if isinstance(cpu_data, (list, np.ndarray)) and cpu_data:
            resource_metrics["cpu_utilization"] = float(np.mean(cpu_data))
            resource_metrics["cpu_utilization_peak"] = float(np.max(cpu_data))
            resource_metrics["cpu_utilization_p95"] = calculate_percentile(cpu_data, 95)
    
    # Process memory utilization
    if "memory" in resource_data:
        memory_data = resource_data["memory"]
        
        if isinstance(memory_data, (list, np.ndarray)) and memory_data:
            resource_metrics["memory_utilization"] = float(np.mean(memory_data))
            resource_metrics["memory_utilization_peak"] = float(np.max(memory_data))
            resource_metrics["memory_utilization_p95"] = calculate_percentile(memory_data, 95)
    
    # Process network utilization
    if "network" in resource_data:
        network_data = resource_data["network"]
        
        if isinstance(network_data, (list, np.ndarray)) and network_data:
            resource_metrics["network_utilization"] = float(np.mean(network_data))
            resource_metrics["network_utilization_peak"] = float(np.max(network_data))
            resource_metrics["network_utilization_p95"] = calculate_percentile(network_data, 95)
    
    return resource_metrics

def compare_with_baseline(current_metrics: Dict[str, Any], 
                         baseline_metrics: Dict[str, Any],
                         threshold_percentages: Dict[str, float]) -> Dict[str, Any]:
    """
    Compare current metrics with a baseline to identify regressions.
    
    Args:
        current_metrics: Dictionary of current performance metrics
        baseline_metrics: Dictionary of baseline performance metrics
        threshold_percentages: Dictionary of acceptable percentage differences by metric
        
    Returns:
        Comparison results with regression indicators
    """
    # Validate inputs
    if not current_metrics or not baseline_metrics:
        logger.error("Empty metrics data provided for comparison")
        return {"status": "ERROR", "message": "Incomplete data for comparison"}
    
    if not threshold_percentages:
        # Default threshold percentages by metric type
        threshold_percentages = {
            "response_time": 10,  # 10% degradation allowed
            "throughput": -15,    # 15% reduction allowed (negative because lower is worse)
            "error_rate": 25,     # 25% increase in errors allowed
            "execution_time": 15, # 15% slower execution allowed
            "cpu_utilization": 20,  # 20% higher CPU usage allowed
            "memory_utilization": 20  # 20% higher memory usage allowed
        }
    
    comparison = {
        "status": "PASS",
        "metrics": {},
        "regressions": []
    }
    
    # Compare each metric in current_metrics
    for metric_name, current_value in current_metrics.items():
        # Skip if metric is not in baseline or not numeric
        if metric_name not in baseline_metrics or not isinstance(current_value, (int, float)):
            continue
        
        baseline_value = baseline_metrics[metric_name]
        
        # Skip if baseline value is zero (avoid division by zero)
        if baseline_value == 0:
            continue
        
        # Calculate percentage difference
        percentage_diff = ((current_value - baseline_value) / baseline_value) * 100
        
        # Determine threshold for this metric
        threshold = threshold_percentages.get(metric_name)
        if threshold is None:
            # Try to find a threshold by looking for the metric type in the name
            for metric_type, threshold_value in threshold_percentages.items():
                if metric_type in metric_name:
                    threshold = threshold_value
                    break
            
            # If still not found, use a default 10%
            if threshold is None:
                threshold = 10
        
        # Check if difference exceeds threshold
        is_regression = False
        
        # For metrics where lower is better (response_time, error_rate, etc.)
        if any(bad_metric in metric_name for bad_metric in ["time", "error", "utilization"]):
            is_regression = percentage_diff > threshold
        # For metrics where higher is better (throughput, accuracy, etc.)
        else:
            is_regression = percentage_diff < -abs(threshold)  # Negative percentage is bad
        
        comparison["metrics"][metric_name] = {
            "current": current_value,
            "baseline": baseline_value,
            "difference_percent": percentage_diff,
            "threshold_percent": threshold,
            "is_regression": is_regression
        }
        
        if is_regression:
            comparison["regressions"].append(f"{metric_name}: {percentage_diff:.2f}% change (threshold: {threshold}%)")
    
    # Set overall status
    if comparison["regressions"]:
        comparison["status"] = "REGRESSION"
    
    return comparison

def generate_summary_statistics(metrics_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a comprehensive summary of all performance metrics.
    
    Args:
        metrics_data: Dictionary containing performance metrics data
        
    Returns:
        Summary statistics for all metrics
    """
    # Extract metrics by category
    api_metrics = extract_api_metrics(metrics_data)
    calculation_metrics = extract_calculation_metrics(metrics_data)
    resource_metrics = extract_resource_metrics(metrics_data)
    
    # Combine into a single summary
    summary = {
        "api": api_metrics,
        "calculation": calculation_metrics,
        "resources": resource_metrics,
        "timestamp": metrics_data.get("timestamp", None),
        "duration": metrics_data.get("duration_seconds", None),
        "test_id": metrics_data.get("test_id", None)
    }
    
    return summary


class MetricAnalyzer:
    """
    Base class for specialized metric analyzers.
    """
    
    def __init__(self, thresholds: Optional[Dict[str, Any]] = None):
        """
        Initialize the MetricAnalyzer with thresholds.
        
        Args:
            thresholds: Dictionary of threshold values for metrics
        """
        self._thresholds = thresholds or {}
    
    def analyze(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze metrics against thresholds.
        
        Args:
            metrics: Dictionary of metrics to analyze
            
        Returns:
            Analysis results
        """
        raise NotImplementedError("Subclasses must implement analyze method")
    
    def set_thresholds(self, thresholds: Dict[str, Any]) -> None:
        """
        Set new thresholds for analysis.
        
        Args:
            thresholds: Dictionary of threshold values
        """
        self._thresholds = thresholds
    
    def get_thresholds(self) -> Dict[str, Any]:
        """
        Get current thresholds.
        
        Returns:
            Current thresholds dictionary
        """
        return self._thresholds.copy()


class APIMetricAnalyzer(MetricAnalyzer):
    """
    Specialized analyzer for API performance metrics.
    """
    
    def __init__(self, thresholds: Optional[Dict[str, Any]] = None):
        """
        Initialize the APIMetricAnalyzer with API-specific thresholds.
        
        Args:
            thresholds: Dictionary of threshold values for API metrics
        """
        super().__init__(thresholds)
        
        # Ensure required thresholds are present
        if "response_time" not in self._thresholds:
            self._thresholds["response_time"] = DEFAULT_THRESHOLDS["response_time"]
        
        if "throughput" not in self._thresholds:
            self._thresholds["throughput"] = DEFAULT_THRESHOLDS["throughput"]
        
        if "error_rate" not in self._thresholds:
            self._thresholds["error_rate"] = DEFAULT_THRESHOLDS["error_rate"]
    
    def analyze(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze API metrics against thresholds.
        
        Args:
            metrics: Dictionary of API metrics
            
        Returns:
            Analysis results for API metrics
        """
        results = {
            "status": "PASS",
            "metrics": {},
            "failures": []
        }
        
        # Check response time (p95)
        if "response_time" in metrics:
            response_time = metrics["response_time"]
            threshold = self._thresholds["response_time"]
            status = "PASS" if response_time <= threshold else "FAIL"
            
            results["metrics"]["response_time"] = {
                "value": response_time,
                "threshold": threshold,
                "status": status
            }
            
            if status == "FAIL":
                results["failures"].append(
                    f"Response time (p95): {response_time}ms exceeds threshold of {threshold}ms"
                )
        
        # Check throughput
        if "throughput" in metrics:
            throughput = metrics["throughput"]
            threshold = self._thresholds["throughput"]
            status = "PASS" if throughput >= threshold else "FAIL"
            
            results["metrics"]["throughput"] = {
                "value": throughput,
                "threshold": threshold,
                "status": status
            }
            
            if status == "FAIL":
                results["failures"].append(
                    f"Throughput: {throughput} req/s below threshold of {threshold} req/s"
                )
        
        # Check error rate
        if "error_rate" in metrics:
            error_rate = metrics["error_rate"]
            threshold = self._thresholds["error_rate"]
            status = "PASS" if error_rate <= threshold else "FAIL"
            
            results["metrics"]["error_rate"] = {
                "value": error_rate,
                "threshold": threshold,
                "status": status
            }
            
            if status == "FAIL":
                results["failures"].append(
                    f"Error rate: {error_rate}% exceeds threshold of {threshold}%"
                )
        
        # Set overall status
        if results["failures"]:
            results["status"] = "FAIL"
        
        return results
    
    def analyze_by_endpoint(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze API metrics broken down by endpoint.
        
        Args:
            metrics: Dictionary of API metrics grouped by endpoint
            
        Returns:
            Analysis results by endpoint
        """
        results = {
            "overall_status": "PASS",
            "endpoints": {}
        }
        
        # Skip if no endpoint-specific data
        if "endpoints" not in metrics:
            return results
        
        # Analyze each endpoint
        for endpoint, endpoint_metrics in metrics["endpoints"].items():
            endpoint_result = self.analyze(endpoint_metrics)
            results["endpoints"][endpoint] = endpoint_result
            
            # If any endpoint fails, the overall status is FAIL
            if endpoint_result["status"] == "FAIL":
                results["overall_status"] = "FAIL"
        
        return results


class CalculationMetricAnalyzer(MetricAnalyzer):
    """
    Specialized analyzer for calculation performance metrics.
    """
    
    def __init__(self, thresholds: Optional[Dict[str, Any]] = None):
        """
        Initialize the CalculationMetricAnalyzer with calculation-specific thresholds.
        
        Args:
            thresholds: Dictionary of threshold values for calculation metrics
        """
        super().__init__(thresholds)
        
        # Ensure required thresholds are present
        if "execution_time" not in self._thresholds:
            self._thresholds["execution_time"] = 50  # 50ms default
        
        if "calculation_accuracy" not in self._thresholds:
            self._thresholds["calculation_accuracy"] = 100  # 100% accuracy required
    
    def analyze(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze calculation metrics against thresholds.
        
        Args:
            metrics: Dictionary of calculation metrics
            
        Returns:
            Analysis results for calculation metrics
        """
        results = {
            "status": "PASS",
            "metrics": {},
            "failures": []
        }
        
        # Check execution time
        if "execution_time" in metrics:
            execution_time = metrics["execution_time"]
            threshold = self._thresholds["execution_time"]
            status = "PASS" if execution_time <= threshold else "FAIL"
            
            results["metrics"]["execution_time"] = {
                "value": execution_time,
                "threshold": threshold,
                "status": status
            }
            
            if status == "FAIL":
                results["failures"].append(
                    f"Execution time (p95): {execution_time}ms exceeds threshold of {threshold}ms"
                )
        
        # Check calculation accuracy
        if "calculation_accuracy" in metrics:
            accuracy = metrics["calculation_accuracy"]
            threshold = self._thresholds["calculation_accuracy"]
            status = "PASS" if accuracy >= threshold else "FAIL"
            
            results["metrics"]["calculation_accuracy"] = {
                "value": accuracy,
                "threshold": threshold,
                "status": status
            }
            
            if status == "FAIL":
                results["failures"].append(
                    f"Calculation accuracy: {accuracy}% below threshold of {threshold}%"
                )
        
        # Set overall status
        if results["failures"]:
            results["status"] = "FAIL"
        
        return results
    
    def analyze_by_calculation_type(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze calculation metrics broken down by calculation type.
        
        Args:
            metrics: Dictionary of calculation metrics grouped by calculation type
            
        Returns:
            Analysis results by calculation type
        """
        results = {
            "overall_status": "PASS",
            "calculation_types": {}
        }
        
        # Skip if no calculation type-specific data
        if "by_type" not in metrics:
            return results
        
        # Analyze each calculation type
        for calc_type, type_metrics in metrics["by_type"].items():
            type_result = self.analyze(type_metrics)
            results["calculation_types"][calc_type] = type_result
            
            # If any calculation type fails, the overall status is FAIL
            if type_result["status"] == "FAIL":
                results["overall_status"] = "FAIL"
        
        return results


class ResourceMetricAnalyzer(MetricAnalyzer):
    """
    Specialized analyzer for resource utilization metrics.
    """
    
    def __init__(self, thresholds: Optional[Dict[str, Any]] = None):
        """
        Initialize the ResourceMetricAnalyzer with resource-specific thresholds.
        
        Args:
            thresholds: Dictionary of threshold values for resource metrics
        """
        super().__init__(thresholds)
        
        # Ensure required thresholds are present
        if "cpu_utilization" not in self._thresholds:
            self._thresholds["cpu_utilization"] = DEFAULT_THRESHOLDS["cpu_utilization"]
        
        if "memory_utilization" not in self._thresholds:
            self._thresholds["memory_utilization"] = DEFAULT_THRESHOLDS["memory_utilization"]
    
    def analyze(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze resource metrics against thresholds.
        
        Args:
            metrics: Dictionary of resource metrics
            
        Returns:
            Analysis results for resource metrics
        """
        results = {
            "status": "PASS",
            "metrics": {},
            "failures": []
        }
        
        # Check CPU utilization
        if "cpu_utilization" in metrics:
            cpu_util = metrics["cpu_utilization"]
            threshold = self._thresholds["cpu_utilization"]
            status = "PASS" if cpu_util <= threshold else "FAIL"
            
            results["metrics"]["cpu_utilization"] = {
                "value": cpu_util,
                "threshold": threshold,
                "status": status
            }
            
            if status == "FAIL":
                results["failures"].append(
                    f"CPU utilization: {cpu_util}% exceeds threshold of {threshold}%"
                )
        
        # Check memory utilization
        if "memory_utilization" in metrics:
            memory_util = metrics["memory_utilization"]
            threshold = self._thresholds["memory_utilization"]
            status = "PASS" if memory_util <= threshold else "FAIL"
            
            results["metrics"]["memory_utilization"] = {
                "value": memory_util,
                "threshold": threshold,
                "status": status
            }
            
            if status == "FAIL":
                results["failures"].append(
                    f"Memory utilization: {memory_util}% exceeds threshold of {threshold}%"
                )
        
        # Check network utilization if threshold defined
        if "network_utilization" in metrics and "network_utilization" in self._thresholds:
            network_util = metrics["network_utilization"]
            threshold = self._thresholds["network_utilization"]
            status = "PASS" if network_util <= threshold else "FAIL"
            
            results["metrics"]["network_utilization"] = {
                "value": network_util,
                "threshold": threshold,
                "status": status
            }
            
            if status == "FAIL":
                results["failures"].append(
                    f"Network utilization: {network_util}% exceeds threshold of {threshold}%"
                )
        
        # Set overall status
        if results["failures"]:
            results["status"] = "FAIL"
        
        return results
    
    def analyze_resource_trends(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze trends in resource utilization over time.
        
        Args:
            metrics: Dictionary of resource metrics with time series data
            
        Returns:
            Trend analysis results
        """
        results = {
            "status": "PASS",
            "trends": {},
            "concerns": []
        }
        
        # Process time series data if available
        for resource in ["cpu", "memory", "network"]:
            resource_key = f"{resource}_time_series"
            if resource_key not in metrics or not metrics[resource_key]:
                continue
                
            time_series = metrics[resource_key]
            
            # Skip if not enough data points
            if len(time_series) < 5:
                continue
                
            # Calculate trend using linear regression
            x = np.arange(len(time_series))
            y = np.array(time_series)
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            # Calculate projected end value
            projected_end = intercept + slope * (len(time_series) - 1)
            
            # Determine if trend is concerning (steep upward slope)
            is_concerning = slope > 0.5 and projected_end > self._thresholds.get(f"{resource}_utilization", 80)
            
            results["trends"][resource] = {
                "slope": slope,
                "r_value": r_value,
                "projected_end": projected_end,
                "is_concerning": is_concerning
            }
            
            if is_concerning:
                results["concerns"].append(
                    f"{resource.capitalize()} utilization shows a concerning upward trend "
                    f"(slope: {slope:.2f}, projected end: {projected_end:.2f}%)"
                )
        
        # Set overall status
        if results["concerns"]:
            results["status"] = "WARN"
        
        return results


class PerformanceAnalyzer:
    """
    Class that provides comprehensive performance analysis capabilities.
    """
    
    def __init__(self, thresholds: Optional[Dict[str, Any]] = None, 
                baseline: Optional[Dict[str, Any]] = None,
                z_threshold: float = 3.0):
        """
        Initialize the PerformanceAnalyzer with thresholds and settings.
        
        Args:
            thresholds: Dictionary of threshold values for metrics
            baseline: Baseline metrics for comparison
            z_threshold: Z-score threshold for anomaly detection
        """
        # Get settings from configuration
        self._settings = get_test_settings()
        
        # Set thresholds from provided values or settings
        if thresholds:
            self._thresholds = thresholds
        else:
            self._thresholds = {
                "response_time": self._settings.get_response_time_threshold(),
                "throughput": self._settings.get_throughput_threshold(),
                "error_rate": self._settings.get_error_rate_threshold(),
                "cpu_utilization": 80,
                "memory_utilization": 80,
                "execution_time": 50,
                "calculation_accuracy": 100
            }
        
        # Store baseline metrics if provided
        self._baseline = baseline
        
        # Set z-threshold for anomaly detection
        self._z_threshold = z_threshold
        
        logger.info(f"Initialized PerformanceAnalyzer with thresholds: {self._thresholds}")
    
    def analyze(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of performance metrics.
        
        Args:
            metrics_data: Dictionary containing performance metrics data
            
        Returns:
            Comprehensive analysis results
        """
        # Generate summary statistics
        summary = generate_summary_statistics(metrics_data)
        
        # Analyze against thresholds
        threshold_analysis = analyze_performance_results(metrics_data, self._thresholds)
        
        # Detect anomalies
        anomalies = self.detect_anomalies(metrics_data)
        
        # Compare with baseline if available
        baseline_comparison = self.compare_with_baseline(metrics_data) if self._baseline else {}
        
        # Combine all analyses into comprehensive results
        results = {
            "status": threshold_analysis.get("status", "PASS"),
            "summary": summary,
            "threshold_analysis": threshold_analysis,
            "anomalies": anomalies,
            "baseline_comparison": baseline_comparison,
            "timestamp": metrics_data.get("timestamp", None),
            "test_id": metrics_data.get("test_id", None)
        }
        
        # If baseline comparison shows regression, update overall status
        if baseline_comparison.get("status") == "REGRESSION" and results["status"] == "PASS":
            results["status"] = "WARN"
        
        return results
    
    def detect_anomalies(self, metrics_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect anomalies in the provided metrics data.
        
        Args:
            metrics_data: Dictionary containing performance metrics data
            
        Returns:
            Detected anomalies by metric
        """
        return detect_anomalies(metrics_data, self._z_threshold)
    
    def compare_with_baseline(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare metrics with stored baseline.
        
        Args:
            metrics_data: Dictionary containing performance metrics data
            
        Returns:
            Comparison results with regression indicators
        """
        if not self._baseline:
            return {}
        
        # Generate summary statistics for current metrics
        current_summary = generate_summary_statistics(metrics_data)
        
        # Flatten summaries for comparison
        current_flat = {}
        baseline_flat = {}
        
        # Flatten current summary
        for category, metrics in current_summary.items():
            if isinstance(metrics, dict):
                for metric, value in metrics.items():
                    if isinstance(value, (int, float)):
                        current_flat[f"{category}_{metric}"] = value
        
        # Flatten baseline summary
        for category, metrics in self._baseline.items():
            if isinstance(metrics, dict):
                for metric, value in metrics.items():
                    if isinstance(value, (int, float)):
                        baseline_flat[f"{category}_{metric}"] = value
        
        # Default threshold percentages by metric type
        threshold_percentages = {
            "response_time": 10,    # 10% increase allowed
            "throughput": -15,      # 15% decrease allowed
            "error_rate": 25,       # 25% increase allowed
            "execution_time": 15,   # 15% increase allowed
            "utilization": 20       # 20% increase allowed
        }
        
        # Compare the flattened metrics
        return compare_with_baseline(current_flat, baseline_flat, threshold_percentages)
    
    def set_baseline(self, baseline_metrics: Dict[str, Any]) -> None:
        """
        Set a new baseline for future comparisons.
        
        Args:
            baseline_metrics: New baseline metrics dictionary
        """
        if not isinstance(baseline_metrics, dict):
            raise ValueError("Baseline metrics must be a dictionary")
        
        self._baseline = baseline_metrics
        logger.info("Set new baseline metrics for comparisons")
    
    def set_thresholds(self, thresholds: Dict[str, Any]) -> None:
        """
        Set new thresholds for performance analysis.
        
        Args:
            thresholds: New thresholds dictionary
        """
        if not isinstance(thresholds, dict):
            raise ValueError("Thresholds must be a dictionary")
        
        self._thresholds = thresholds
        logger.info(f"Set new performance thresholds: {thresholds}")
    
    def get_thresholds(self) -> Dict[str, Any]:
        """
        Get the current thresholds used for analysis.
        
        Returns:
            Current thresholds dictionary
        """
        return self._thresholds.copy()
    
    def get_baseline(self) -> Optional[Dict[str, Any]]:
        """
        Get the current baseline used for comparison.
        
        Returns:
            Current baseline metrics or None if not set
        """
        return self._baseline.copy() if self._baseline else None