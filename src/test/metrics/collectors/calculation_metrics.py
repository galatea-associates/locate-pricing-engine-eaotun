import logging
import time
import statistics
from collections import defaultdict
from decimal import Decimal

from .api_metrics import BaseMetricsCollector

logger = logging.getLogger(__name__)

class CalculationMetricsCollector(BaseMetricsCollector):
    """Collects and analyzes calculation performance metrics such as execution times, throughput, and accuracy"""
    
    def __init__(self, config=None):
        """Initialize the calculation metrics collector with default configuration.
        
        Args:
            config (dict, optional): Configuration dictionary. Defaults to None.
        """
        super().__init__(name="calculation_metrics", config=config or {})
        self._execution_times = defaultdict(list)    # Store execution times by calculation type
        self._accuracy_measurements = defaultdict(list)  # Store accuracy measurements by calculation type
        self._calculation_counts = defaultdict(int)   # Count calculations by type
        self._start_time = None
        self._end_time = None
        self._is_collecting = False
    
    def start_collection(self):
        """Start collecting calculation metrics.
        
        Returns:
            None
        """
        self._start_time = time.time()
        self._is_collecting = True
        self.reset()  # Reset internal counters and lists, but keep _start_time and _is_collecting
        logger.info(f"Started calculation metrics collection at {self._start_time}")
    
    def stop_collection(self):
        """Stop collecting calculation metrics.
        
        Returns:
            None
        """
        self._end_time = time.time()
        self._is_collecting = False
        duration = self._end_time - self._start_time if self._start_time else 0
        logger.info(f"Stopped calculation metrics collection after {duration:.2f} seconds")
    
    def record_calculation(self, calculation_type, execution_time):
        """Record a calculation execution with timing information.
        
        Args:
            calculation_type (str): The type of calculation (e.g., "borrow_rate", "locate_fee")
            execution_time (float): Execution time in seconds
            
        Returns:
            None
        """
        if not self._is_collecting:
            return
        
        self._calculation_counts[calculation_type] += 1
        self._execution_times[calculation_type].append(execution_time)
        
        logger.debug(f"Recorded calculation: {calculation_type} in {execution_time:.6f}s")
    
    def record_accuracy(self, calculation_type, expected_result, actual_result):
        """Record the accuracy of a calculation by comparing expected and actual results.
        
        Args:
            calculation_type (str): The type of calculation (e.g., "borrow_rate", "locate_fee")
            expected_result (Decimal): The expected result of the calculation
            actual_result (Decimal): The actual result of the calculation
            
        Returns:
            None
        """
        if not self._is_collecting:
            return
        
        # Calculate the difference between expected and actual results
        if expected_result == Decimal('0'):
            # Handle division by zero case
            accuracy = Decimal('1.0') if actual_result == Decimal('0') else Decimal('0.0')
        else:
            # Calculate relative error and then accuracy (1.0 - relative_error)
            difference = abs(expected_result - actual_result)
            relative_error = difference / abs(expected_result)
            accuracy = Decimal('1.0') - relative_error
        
        self._accuracy_measurements[calculation_type].append(float(accuracy))
        
        logger.debug(f"Recorded accuracy for {calculation_type}: {float(accuracy):.6f} " 
                     f"(expected: {expected_result}, actual: {actual_result})")
    
    def collect(self):
        """Collect and calculate calculation performance metrics.
        
        Returns:
            dict: Dictionary containing calculated metrics
        """
        if not self._start_time or not self._end_time:
            return {"error": "No collection period defined. Call start_collection() and stop_collection() first."}
        
        duration = self._end_time - self._start_time
        
        # Calculate overall metrics
        total_calculations = sum(self._calculation_counts.values())
        calculations_per_second = total_calculations / duration if duration > 0 else 0
        
        # Prepare results dictionary
        results = {
            "overall": {
                "total_calculations": total_calculations,
                "calculations_per_second": calculations_per_second,
                "duration_seconds": duration,
                "calculation_types": len(self._calculation_counts)
            },
            "calculation_types": {}
        }
        
        # Calculate per-calculation-type metrics
        for calc_type in self._calculation_counts:
            count = self._calculation_counts[calc_type]
            
            # Get execution time stats
            exec_time_stats = self.get_execution_time_stats(self._execution_times[calc_type])
            
            # Get accuracy stats if available
            accuracy_stats = self.get_accuracy_stats(self._accuracy_measurements[calc_type]) if calc_type in self._accuracy_measurements else None
            
            # Add to results
            results["calculation_types"][calc_type] = {
                "count": count,
                "calculations_per_second": count / duration if duration > 0 else 0,
                "execution_times": exec_time_stats,
                "accuracy": accuracy_stats
            }
            
            # Check performance against SLO target (<50ms)
            if exec_time_stats["p95"] > 0.050:  # 50ms expressed in seconds
                results["calculation_types"][calc_type]["performance_warning"] = True
                logger.warning(f"Performance warning: {calc_type} calculation p95 is {exec_time_stats['p95']*1000:.2f}ms (target: <50ms)")
            
            # Check accuracy against SLO target (100%)
            if accuracy_stats and accuracy_stats["perfect_percentage"] < 100:
                results["calculation_types"][calc_type]["accuracy_warning"] = True
                logger.warning(f"Accuracy warning: {calc_type} calculation has {accuracy_stats['perfect_percentage']:.2f}% " 
                              f"perfect accuracy (target: 100%)")
        
        return results
    
    def reset(self):
        """Reset all collected metrics.
        
        Returns:
            None
        """
        self._execution_times.clear()
        self._accuracy_measurements.clear()
        self._calculation_counts.clear()
        # Keep _start_time and _is_collecting state if already set
        if not self._is_collecting:
            self._start_time = None
            self._end_time = None
        logger.info("Reset calculation metrics collector")
    
    def calculate_percentile(self, execution_times, percentile):
        """Calculate a percentile value from a list of execution times.
        
        Args:
            execution_times (list): List of execution times
            percentile (float): Percentile to calculate (0-100)
            
        Returns:
            float: The calculated percentile value
        """
        if not execution_times:
            return 0
        
        sorted_times = sorted(execution_times)
        index = int(len(sorted_times) * (percentile / 100))
        # Ensure index is within bounds
        index = max(0, min(index, len(sorted_times) - 1))
        return sorted_times[index]
    
    def get_execution_time_stats(self, execution_times):
        """Calculate execution time statistics for a list of execution times.
        
        Args:
            execution_times (list): List of execution times
            
        Returns:
            dict: Dictionary with execution time statistics
        """
        if not execution_times:
            return {
                "min": 0,
                "max": 0,
                "avg": 0,
                "median": 0,
                "p95": 0,
                "p99": 0
            }
        
        return {
            "min": min(execution_times),
            "max": max(execution_times),
            "avg": sum(execution_times) / len(execution_times),
            "median": self.calculate_percentile(execution_times, 50),
            "p95": self.calculate_percentile(execution_times, 95),
            "p99": self.calculate_percentile(execution_times, 99)
        }
    
    def get_accuracy_stats(self, accuracy_measurements):
        """Calculate accuracy statistics for a list of accuracy measurements.
        
        Args:
            accuracy_measurements (list): List of accuracy measurements (0.0-1.0)
            
        Returns:
            dict: Dictionary with accuracy statistics
        """
        if not accuracy_measurements:
            return None
        
        # Count measurements with perfect accuracy (1.0)
        perfect_count = sum(1 for acc in accuracy_measurements if acc >= 0.9999)
        perfect_percentage = (perfect_count / len(accuracy_measurements)) * 100 if accuracy_measurements else 0
        
        return {
            "min": min(accuracy_measurements),
            "max": max(accuracy_measurements),
            "avg": sum(accuracy_measurements) / len(accuracy_measurements),
            "perfect_count": perfect_count,
            "perfect_percentage": perfect_percentage
        }