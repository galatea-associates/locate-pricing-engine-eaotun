import logging
import time
import statistics
from collections import defaultdict
import psutil
import threading
from .api_metrics import BaseMetricsCollector

logger = logging.getLogger(__name__)

class ResourceMetricsCollector(BaseMetricsCollector):
    """Collects and analyzes system resource utilization metrics including CPU, memory, disk I/O, and network usage"""
    
    def __init__(self, config=None):
        """Initialize the resource metrics collector with default configuration
        
        Args:
            config (dict, optional): Configuration dictionary. Defaults to None.
        """
        super().__init__(name="resource_metrics", config=config or {})
        self._cpu_metrics = defaultdict(list)
        self._memory_metrics = defaultdict(list)
        self._disk_metrics = defaultdict(list)
        self._network_metrics = defaultdict(list)
        self._collection_interval = config.get('collection_interval', 1.0)  # seconds
        self._collection_thread = None
        self._stop_collection_flag = False
        self._start_time = None
        self._end_time = None
        self._is_collecting = False
    
    def start_collection(self):
        """Start collecting resource metrics in a background thread
        
        Returns:
            None: No return value
        """
        self._start_time = time.time()
        self._is_collecting = True
        self.reset()  # Reset internal metrics collections
        self._stop_collection_flag = False
        
        # Start collection thread
        self._collection_thread = threading.Thread(target=self._collect_metrics_loop)
        self._collection_thread.daemon = True
        self._collection_thread.start()
        
        logger.info(f"Started resource metrics collection at {self._start_time}")
    
    def stop_collection(self):
        """Stop collecting resource metrics
        
        Returns:
            None: No return value
        """
        self._stop_collection_flag = True
        
        # Wait for collection thread to terminate
        if self._collection_thread and self._collection_thread.is_alive():
            self._collection_thread.join(timeout=5.0)
        
        self._end_time = time.time()
        self._is_collecting = False
        self._collection_thread = None
        
        duration = self._end_time - self._start_time if self._start_time else 0
        logger.info(f"Stopped resource metrics collection after {duration:.2f} seconds")
    
    def _collect_metrics_loop(self):
        """Background loop that periodically collects resource metrics
        
        Returns:
            None: No return value
        """
        while not self._stop_collection_flag:
            # Collect all metrics
            self.collect_cpu_metrics()
            self.collect_memory_metrics()
            self.collect_disk_metrics()
            self.collect_network_metrics()
            
            # Sleep for collection interval
            time.sleep(self._collection_interval)
            
        logger.debug("Resource metrics collection thread terminated")
    
    def collect_cpu_metrics(self):
        """Collect current CPU utilization metrics
        
        Returns:
            dict: Dictionary with current CPU metrics
        """
        # Get CPU percentages (gives per-CPU and overall utilization)
        per_cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
        cpu_overall_percent = psutil.cpu_percent(interval=0.1)
        
        # Get CPU times percentages (user, system, idle)
        cpu_times = psutil.cpu_times_percent()
        
        # Get CPU stats (context switches, interrupts)
        cpu_stats = psutil.cpu_stats()
        
        # Get CPU frequency if available
        try:
            cpu_freq = psutil.cpu_freq()
            current_freq = cpu_freq.current if cpu_freq else None
        except Exception:
            current_freq = None
        
        # Store metrics
        current_metrics = {
            'cpu_overall_percent': cpu_overall_percent,
            'cpu_user_percent': cpu_times.user,
            'cpu_system_percent': cpu_times.system,
            'cpu_idle_percent': cpu_times.idle,
            'context_switches': cpu_stats.ctx_switches,
            'interrupts': cpu_stats.interrupts,
            'cpu_freq_mhz': current_freq
        }
        
        # Store per-CPU percentages
        for i, cpu_percent in enumerate(per_cpu_percent):
            current_metrics[f'cpu_{i}_percent'] = cpu_percent
            self._cpu_metrics[f'cpu_{i}_percent'].append(cpu_percent)
        
        # Store other metrics
        for key, value in current_metrics.items():
            if value is not None:  # Don't store None values
                self._cpu_metrics[key].append(value)
        
        return current_metrics
    
    def collect_memory_metrics(self):
        """Collect current memory utilization metrics
        
        Returns:
            dict: Dictionary with current memory metrics
        """
        # Get virtual memory stats
        virtual_memory = psutil.virtual_memory()
        memory_percent = virtual_memory.percent
        
        # Get swap memory stats
        swap_memory = psutil.swap_memory()
        swap_percent = swap_memory.percent
        
        # Store metrics
        current_metrics = {
            'memory_total_bytes': virtual_memory.total,
            'memory_available_bytes': virtual_memory.available,
            'memory_used_bytes': virtual_memory.used,
            'memory_percent': memory_percent,
            'swap_total_bytes': swap_memory.total,
            'swap_used_bytes': swap_memory.used,
            'swap_percent': swap_percent
        }
        
        # Store in metrics collection
        for key, value in current_metrics.items():
            self._memory_metrics[key].append(value)
        
        return current_metrics
    
    def collect_disk_metrics(self):
        """Collect current disk I/O and utilization metrics
        
        Returns:
            dict: Dictionary with current disk metrics
        """
        # Get disk I/O counters
        disk_io = psutil.disk_io_counters(perdisk=True)
        
        # Get disk usage
        disk_usage = psutil.disk_usage('/')
        disk_percent = disk_usage.percent
        
        # Store basic metrics
        current_metrics = {
            'disk_space_total_bytes': disk_usage.total,
            'disk_space_used_bytes': disk_usage.used,
            'disk_space_percent': disk_percent,
        }
        
        # Calculate read/write rates if we have previous measurements
        for disk_name, io_stats in disk_io.items():
            # Store current read/write counters
            current_metrics[f'{disk_name}_read_bytes'] = io_stats.read_bytes
            current_metrics[f'{disk_name}_write_bytes'] = io_stats.write_bytes
            current_metrics[f'{disk_name}_read_count'] = io_stats.read_count
            current_metrics[f'{disk_name}_write_count'] = io_stats.write_count
            
            # Calculate rates based on previous values
            prev_read_bytes = self._disk_metrics.get(f'{disk_name}_read_bytes', [0])[-1] if self._disk_metrics.get(f'{disk_name}_read_bytes') else 0
            prev_write_bytes = self._disk_metrics.get(f'{disk_name}_write_bytes', [0])[-1] if self._disk_metrics.get(f'{disk_name}_write_bytes') else 0
            
            if prev_read_bytes != 0 and prev_write_bytes != 0:
                read_bytes_rate = (io_stats.read_bytes - prev_read_bytes) / self._collection_interval
                write_bytes_rate = (io_stats.write_bytes - prev_write_bytes) / self._collection_interval
                
                current_metrics[f'{disk_name}_read_bytes_per_sec'] = read_bytes_rate
                current_metrics[f'{disk_name}_write_bytes_per_sec'] = write_bytes_rate
                
                self._disk_metrics[f'{disk_name}_read_bytes_per_sec'].append(read_bytes_rate)
                self._disk_metrics[f'{disk_name}_write_bytes_per_sec'].append(write_bytes_rate)
        
        # Store in metrics collection
        for key, value in current_metrics.items():
            if key not in self._disk_metrics or not key.endswith('_per_sec'):  # Avoid duplicating rate metrics
                self._disk_metrics[key].append(value)
        
        return current_metrics
    
    def collect_network_metrics(self):
        """Collect current network throughput and utilization metrics
        
        Returns:
            dict: Dictionary with current network metrics
        """
        # Get network I/O counters
        net_io = psutil.net_io_counters(pernic=True)
        
        # Get network connections count
        connections = psutil.net_connections()
        conn_count = len(connections)
        
        # Store basic metrics
        current_metrics = {
            'network_connection_count': conn_count,
        }
        
        # Process each network interface
        for nic_name, io_stats in net_io.items():
            # Skip loopback interface
            if nic_name.startswith('lo'):
                continue
                
            # Store current counters
            current_metrics[f'{nic_name}_bytes_sent'] = io_stats.bytes_sent
            current_metrics[f'{nic_name}_bytes_recv'] = io_stats.bytes_recv
            current_metrics[f'{nic_name}_packets_sent'] = io_stats.packets_sent
            current_metrics[f'{nic_name}_packets_recv'] = io_stats.packets_recv
            current_metrics[f'{nic_name}_errin'] = io_stats.errin
            current_metrics[f'{nic_name}_errout'] = io_stats.errout
            
            # Calculate rates based on previous values
            prev_bytes_sent = self._network_metrics.get(f'{nic_name}_bytes_sent', [0])[-1] if self._network_metrics.get(f'{nic_name}_bytes_sent') else 0
            prev_bytes_recv = self._network_metrics.get(f'{nic_name}_bytes_recv', [0])[-1] if self._network_metrics.get(f'{nic_name}_bytes_recv') else 0
            
            if prev_bytes_sent != 0 and prev_bytes_recv != 0:
                bytes_sent_rate = (io_stats.bytes_sent - prev_bytes_sent) / self._collection_interval
                bytes_recv_rate = (io_stats.bytes_recv - prev_bytes_recv) / self._collection_interval
                
                current_metrics[f'{nic_name}_bytes_sent_per_sec'] = bytes_sent_rate
                current_metrics[f'{nic_name}_bytes_recv_per_sec'] = bytes_recv_rate
                
                # Estimate network utilization (assuming 1Gbps interface)
                # This is a rough estimation and should be adjusted based on actual interface speed
                interface_speed_bits = 1000000000  # 1 Gbps in bits/second
                bytes_total_rate = bytes_sent_rate + bytes_recv_rate
                bits_total_rate = bytes_total_rate * 8  # Convert to bits/second
                utilization_percent = (bits_total_rate / interface_speed_bits) * 100
                
                current_metrics[f'{nic_name}_utilization_percent'] = min(100, utilization_percent)  # Cap at 100%
                
                self._network_metrics[f'{nic_name}_bytes_sent_per_sec'].append(bytes_sent_rate)
                self._network_metrics[f'{nic_name}_bytes_recv_per_sec'].append(bytes_recv_rate)
                self._network_metrics[f'{nic_name}_utilization_percent'].append(min(100, utilization_percent))
        
        # Store in metrics collection
        for key, value in current_metrics.items():
            if key not in self._network_metrics or not key.endswith(('_per_sec', '_utilization_percent')):  # Avoid duplicating rate metrics
                self._network_metrics[key].append(value)
        
        return current_metrics
    
    def collect(self):
        """Collect and calculate resource utilization metrics
        
        Returns:
            dict: Dictionary containing calculated resource metrics
        """
        if not self._start_time or not self._end_time:
            return {"error": "No collection period defined. Call start_collection() and stop_collection() first."}
        
        duration = self._end_time - self._start_time
        
        # Prepare results dictionary
        results = {
            "overall": {
                "duration_seconds": duration
            },
            "cpu": {},
            "memory": {},
            "disk": {},
            "network": {}
        }
        
        # Process CPU metrics
        for metric_name, values in self._cpu_metrics.items():
            if values:  # Skip empty metrics
                stats = self.get_statistics(values)
                results["cpu"][metric_name] = stats
                
                # Add overall CPU metrics to top level for convenience
                if metric_name == 'cpu_overall_percent':
                    results["overall"]["cpu_min"] = stats["min"]
                    results["overall"]["cpu_max"] = stats["max"]
                    results["overall"]["cpu_avg"] = stats["avg"]
                    results["overall"]["cpu_p95"] = stats["p95"]
        
        # Process memory metrics
        for metric_name, values in self._memory_metrics.items():
            if values:  # Skip empty metrics
                stats = self.get_statistics(values)
                results["memory"][metric_name] = stats
                
                # Add overall memory metrics to top level for convenience
                if metric_name == 'memory_percent':
                    results["overall"]["memory_min"] = stats["min"]
                    results["overall"]["memory_max"] = stats["max"]
                    results["overall"]["memory_avg"] = stats["avg"]
                    results["overall"]["memory_p95"] = stats["p95"]
        
        # Process disk metrics
        for metric_name, values in self._disk_metrics.items():
            if values:  # Skip empty metrics
                stats = self.get_statistics(values)
                results["disk"][metric_name] = stats
                
                # Add overall disk metrics to top level for convenience
                if metric_name == 'disk_space_percent':
                    results["overall"]["disk_usage_min"] = stats["min"]
                    results["overall"]["disk_usage_max"] = stats["max"]
                    results["overall"]["disk_usage_avg"] = stats["avg"]
                    results["overall"]["disk_usage_p95"] = stats["p95"]
        
        # Process network metrics
        for metric_name, values in self._network_metrics.items():
            if values:  # Skip empty metrics
                stats = self.get_statistics(values)
                results["network"][metric_name] = stats
                
                # Add network utilization to top level if available
                if metric_name.endswith('_utilization_percent'):
                    results["overall"]["network_util_min"] = stats["min"]
                    results["overall"]["network_util_max"] = stats["max"]
                    results["overall"]["network_util_avg"] = stats["avg"]
                    results["overall"]["network_util_p95"] = stats["p95"]
        
        return results
    
    def reset(self):
        """Reset all collected metrics
        
        Returns:
            None: No return value
        """
        self._cpu_metrics.clear()
        self._memory_metrics.clear()
        self._disk_metrics.clear()
        self._network_metrics.clear()
        
        if not self._is_collecting:
            self._start_time = None
            self._end_time = None
        
        logger.info("Reset resource metrics collector")
    
    def calculate_percentile(self, measurements, percentile):
        """Calculate a percentile value from a list of measurements
        
        Args:
            measurements (list): List of numeric measurements
            percentile (float): Percentile to calculate (0-100)
            
        Returns:
            float: The calculated percentile value
        """
        if not measurements:
            return 0
        
        sorted_values = sorted(measurements)
        index = int(len(sorted_values) * (percentile / 100))
        # Ensure index is within bounds
        index = max(0, min(index, len(sorted_values) - 1))
        return sorted_values[index]
    
    def get_statistics(self, measurements):
        """Calculate statistics for a list of measurements
        
        Args:
            measurements (list): List of numeric measurements
            
        Returns:
            dict: Dictionary with statistical measures
        """
        if not measurements:
            return {
                "min": 0,
                "max": 0,
                "avg": 0,
                "median": 0,
                "p95": 0,
                "p99": 0
            }
        
        return {
            "min": min(measurements),
            "max": max(measurements),
            "avg": sum(measurements) / len(measurements),
            "median": self.calculate_percentile(measurements, 50),
            "p95": self.calculate_percentile(measurements, 95),
            "p99": self.calculate_percentile(measurements, 99)
        }