import logging
import time
import statistics
from collections import defaultdict
from abc import ABC, abstractmethod
import threading

logger = logging.getLogger(__name__)

class BaseMetricsCollector(ABC):
    """Abstract base class defining the interface for all metrics collectors."""
    
    def __init__(self, name, config):
        """Initialize the base metrics collector with a name and configuration.
        
        Args:
            name (str): The name of the collector
            config (dict): Configuration dictionary for the collector
        """
        self.name = name
        self.config = config
        self._is_collecting = False
        self._start_time = None
        self._end_time = None
    
    @abstractmethod
    def start_collection(self):
        """Start collecting metrics.
        
        This method must be implemented by subclasses.
        Should set _start_time to current time.
        Should set _is_collecting to True.
        Should reset any internal counters or state.
        
        Returns:
            None
        """
        pass
    
    @abstractmethod
    def stop_collection(self):
        """Stop collecting metrics.
        
        This method must be implemented by subclasses.
        Should set _end_time to current time.
        Should set _is_collecting to False.
        
        Returns:
            None
        """
        pass
    
    @abstractmethod
    def collect(self):
        """Collect and calculate metrics.
        
        This method must be implemented by subclasses.
        Should process collected data and return metrics dictionary.
        
        Returns:
            dict: Dictionary containing calculated metrics
        """
        pass
    
    @abstractmethod
    def reset(self):
        """Reset all collected metrics.
        
        This method must be implemented by subclasses.
        Should clear all internal state and counters.
        
        Returns:
            None
        """
        pass
    
    def get_name(self):
        """Get the name of the collector.
        
        Returns:
            str: Collector name
        """
        return self.name


class APIMetricsCollector(BaseMetricsCollector):
    """Collects and analyzes API performance metrics such as request rates, response times, and error rates."""
    
    def __init__(self, config=None):
        """Initialize the API metrics collector with default configuration.
        
        Args:
            config (dict, optional): Configuration dictionary. Defaults to None.
        """
        super().__init__(name="api_metrics", config=config or {})
        self._response_times = defaultdict(list)  # Store response times by endpoint
        self._error_counts = defaultdict(int)     # Count errors by endpoint
        self._request_counts = defaultdict(int)   # Count requests by endpoint
        self._status_codes = defaultdict(lambda: defaultdict(int))  # Count status codes by endpoint
        self._start_time = None
        self._end_time = None
        self._is_collecting = False
    
    def start_collection(self):
        """Start collecting API metrics.
        
        Returns:
            None
        """
        self._start_time = time.time()
        self._is_collecting = True
        self.reset()  # Reset internal counters and lists
        logger.info(f"Started API metrics collection at {self._start_time}")
    
    def stop_collection(self):
        """Stop collecting API metrics.
        
        Returns:
            None
        """
        self._end_time = time.time()
        self._is_collecting = False
        duration = self._end_time - self._start_time if self._start_time else 0
        logger.info(f"Stopped API metrics collection after {duration:.2f} seconds")
    
    def record_request(self, endpoint, response_time, status_code, method="GET"):
        """Record an API request with timing and result information.
        
        Args:
            endpoint (str): The API endpoint called
            response_time (float): Response time in seconds
            status_code (int): HTTP status code returned
            method (str, optional): HTTP method used. Defaults to "GET".
            
        Returns:
            None
        """
        if not self._is_collecting:
            return
        
        self._request_counts[endpoint] += 1
        self._response_times[endpoint].append(response_time)
        self._status_codes[endpoint][status_code] += 1
        
        if status_code >= 400:
            self._error_counts[endpoint] += 1
        
        logger.debug(f"Recorded API request: {method} {endpoint} - {status_code} in {response_time:.4f}s")
    
    def collect(self):
        """Collect and calculate API metrics.
        
        Returns:
            dict: Dictionary containing calculated metrics
        """
        if not self._start_time or not self._end_time:
            return {"error": "No collection period defined. Call start_collection() and stop_collection() first."}
        
        duration = self._end_time - self._start_time
        
        # Calculate overall metrics
        total_requests = sum(self._request_counts.values())
        total_errors = sum(self._error_counts.values())
        error_rate = (total_errors / total_requests) * 100 if total_requests > 0 else 0
        requests_per_second = total_requests / duration if duration > 0 else 0
        
        # Prepare results dictionary
        results = {
            "overall": {
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": error_rate,
                "requests_per_second": requests_per_second,
                "duration_seconds": duration
            },
            "endpoints": {}
        }
        
        # Calculate per-endpoint metrics
        for endpoint in self._request_counts:
            requests = self._request_counts[endpoint]
            errors = self._error_counts[endpoint]
            endpoint_error_rate = (errors / requests) * 100 if requests > 0 else 0
            
            # Get response time stats
            rt_stats = self.get_response_time_stats(self._response_times[endpoint])
            
            # Get status code distribution
            status_distribution = dict(self._status_codes[endpoint])
            
            # Add to results
            results["endpoints"][endpoint] = {
                "requests": requests,
                "errors": errors,
                "error_rate": endpoint_error_rate,
                "requests_per_second": requests / duration if duration > 0 else 0,
                "response_times": rt_stats,
                "status_codes": status_distribution
            }
        
        return results
    
    def reset(self):
        """Reset all collected metrics.
        
        Returns:
            None
        """
        self._response_times.clear()
        self._error_counts.clear()
        self._request_counts.clear()
        self._status_codes.clear()
        # Keep _start_time and _is_collecting state if already set
        if not self._is_collecting:
            self._start_time = None
            self._end_time = None
        logger.info("Reset API metrics collector")
    
    def calculate_percentile(self, response_times, percentile):
        """Calculate a percentile value from a list of response times.
        
        Args:
            response_times (list): List of response times
            percentile (float): Percentile to calculate (0-100)
            
        Returns:
            float: The calculated percentile value
        """
        if not response_times:
            return 0
        
        sorted_times = sorted(response_times)
        index = int(len(sorted_times) * (percentile / 100))
        # Ensure index is within bounds
        index = max(0, min(index, len(sorted_times) - 1))
        return sorted_times[index]
    
    def get_response_time_stats(self, response_times):
        """Calculate response time statistics for a list of response times.
        
        Args:
            response_times (list): List of response times
            
        Returns:
            dict: Dictionary with response time statistics
        """
        if not response_times:
            return {
                "min": 0,
                "max": 0,
                "avg": 0,
                "median": 0,
                "p95": 0,
                "p99": 0
            }
        
        return {
            "min": min(response_times),
            "max": max(response_times),
            "avg": sum(response_times) / len(response_times),
            "median": self.calculate_percentile(response_times, 50),
            "p95": self.calculate_percentile(response_times, 95),
            "p99": self.calculate_percentile(response_times, 99)
        }