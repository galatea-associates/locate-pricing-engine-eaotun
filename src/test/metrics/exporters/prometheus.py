import logging
import os
import time
import threading
import abc
from prometheus_client import Counter, Gauge, Histogram, Summary, start_http_server, generate_latest, REGISTRY

# Configure logger
logger = logging.getLogger(__name__)

class BaseExporter(abc.ABC):
    """
    Abstract base class for all metrics exporters, defining the common interface 
    that all exporters must implement.
    """
    
    def __init__(self, config=None):
        """
        Initialize the base exporter with a name and configuration
        
        Args:
            config (dict): Configuration dictionary for the exporter
        """
        self.name = 'base'
        self.config = config or {}
    
    @abc.abstractmethod
    def export(self, metrics_data, output_path=None):
        """
        Export metrics to the target format or system
        
        Args:
            metrics_data (dict): Dictionary containing metrics to export
            output_path (str): Path where metrics should be exported
            
        Returns:
            dict: Export results with relevant information
        """
        pass
    
    def get_name(self):
        """
        Get the name of the exporter
        
        Returns:
            str: The name of the exporter
        """
        return self.name


class PrometheusExporter(BaseExporter):
    """
    Exports metrics in Prometheus format and exposes them via HTTP for scraping.
    Implements the BaseExporter interface for the Prometheus monitoring system.
    """
    
    def __init__(self, config=None):
        """
        Initialize the Prometheus exporter with default configuration
        
        Args:
            config (dict): Configuration dictionary for the exporter
        """
        super().__init__(config)
        self.name = 'prometheus'
        self._metrics = {}  # Store Prometheus metric objects
        self._server_thread = None
        self._server_running = False
        self._server_port = self.config.get('port', 8000)
        
        # Register default metrics if enabled
        if self.config.get('default_metrics', True):
            # Initialize default collectors
            REGISTRY.collect()
        
    def export(self, metrics_data, output_path=None):
        """
        Export metrics to Prometheus format and optionally start an HTTP server for scraping
        
        Args:
            metrics_data (dict): Dictionary containing metrics to export
            output_path (str): Path where metrics should be exported (file path for Prometheus text format)
            
        Returns:
            dict: Export results with server information
        """
        # Clear existing metrics registry if configured
        if self.config.get('clear_registry_on_export', False):
            self._metrics = {}
        
        # Process API metrics
        if 'api_metrics' in metrics_data:
            self.process_api_metrics(metrics_data['api_metrics'])
        
        # Process calculation metrics
        if 'calculation_metrics' in metrics_data:
            self.process_calculation_metrics(metrics_data['calculation_metrics'])
        
        # Process resource metrics
        if 'resource_metrics' in metrics_data:
            self.process_resource_metrics(metrics_data['resource_metrics'])
        
        # Write to file if output path provided
        if output_path:
            self.write_metrics_to_file(output_path)
        
        # Start HTTP server if configured
        if self.config.get('auto_start_server', True) and not self._server_running:
            self.start_http_server(self._server_port)
        
        return {
            'status': 'success',
            'server_running': self._server_running,
            'server_port': self._server_port,
            'metrics_count': len(self._metrics),
            'output_path': output_path
        }
    
    def start_http_server(self, port=None):
        """
        Start an HTTP server to expose metrics for Prometheus scraping
        
        Args:
            port (int): Port to run the server on
            
        Returns:
            bool: True if server started successfully, False otherwise
        """
        # If server is already running, return
        if self._server_running:
            logger.warning("Prometheus HTTP server is already running on port %s", self._server_port)
            return False
        
        # Set port
        self._server_port = port or self._server_port
        
        try:
            # Start server in a daemon thread (will automatically terminate when main program exits)
            start_http_server(self._server_port)
            self._server_running = True
            logger.info("Started Prometheus HTTP server on port %s", self._server_port)
            return True
        except Exception as e:
            logger.error(f"Failed to start Prometheus HTTP server: {str(e)}")
            return False
    
    def stop_http_server(self):
        """
        Mark the HTTP server as stopped. Due to limitations in prometheus_client,
        we can't actually stop the server once started, but we can prevent further
        interaction with it.
        
        Returns:
            bool: True if marked as stopped, False if not running
        """
        if not self._server_running:
            logger.warning("Prometheus HTTP server is not running")
            return False
        
        self._server_running = False
        logger.info("Marked Prometheus HTTP server as stopped (note: the server will continue running until program exit)")
        return True
    
    def process_api_metrics(self, api_metrics):
        """
        Process API metrics and create Prometheus metrics
        
        Args:
            api_metrics (dict): Dictionary containing API metrics
        """
        # Total requests counter
        total_requests = self.get_or_create_metric(
            'counter', 'api_total_requests', 
            'Total number of API requests', []
        )
        total_requests.inc(api_metrics.get('total_requests', 0))
        
        # Error rate gauge
        error_rate = self.get_or_create_metric(
            'gauge', 'api_error_rate',
            'API error rate as a percentage', []
        )
        error_rate.set(api_metrics.get('error_rate', 0))
        
        # Response time histogram with appropriate buckets for API latency
        response_time = self.get_or_create_metric(
            'histogram', 'api_response_time',
            'API response time in seconds',
            [], buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
        )
        # Add response time observations
        for rt in api_metrics.get('response_times', []):
            response_time.observe(rt)
        
        # Requests per second gauge
        rps = self.get_or_create_metric(
            'gauge', 'api_requests_per_second',
            'API requests per second', []
        )
        rps.set(api_metrics.get('requests_per_second', 0))
        
        # Process endpoint-specific metrics
        for endpoint, metrics in api_metrics.get('endpoints', {}).items():
            # Endpoint request counter
            endpoint_requests = self.get_or_create_metric(
                'counter', 'api_endpoint_requests',
                'Number of requests per endpoint',
                ['endpoint']
            )
            endpoint_requests.labels(endpoint=endpoint).inc(metrics.get('requests', 0))
            
            # Endpoint error rate
            endpoint_error_rate = self.get_or_create_metric(
                'gauge', 'api_endpoint_error_rate',
                'Error rate per endpoint as a percentage',
                ['endpoint']
            )
            endpoint_error_rate.labels(endpoint=endpoint).set(metrics.get('error_rate', 0))
            
            # Endpoint response time
            endpoint_response_time = self.get_or_create_metric(
                'histogram', 'api_endpoint_response_time',
                'Response time per endpoint in seconds',
                ['endpoint'], buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0]
            )
            # Add response time observations for this endpoint
            for rt in metrics.get('response_times', []):
                endpoint_response_time.labels(endpoint=endpoint).observe(rt)
        
        logger.debug("Processed API metrics successfully")
    
    def process_calculation_metrics(self, calculation_metrics):
        """
        Process calculation metrics and create Prometheus metrics
        
        Args:
            calculation_metrics (dict): Dictionary containing calculation metrics
        """
        # Total calculations counter
        total_calculations = self.get_or_create_metric(
            'counter', 'calculation_total',
            'Total number of calculations performed', []
        )
        total_calculations.inc(calculation_metrics.get('total_calculations', 0))
        
        # Calculation error rate gauge
        error_rate = self.get_or_create_metric(
            'gauge', 'calculation_error_rate',
            'Calculation error rate as a percentage', []
        )
        error_rate.set(calculation_metrics.get('error_rate', 0))
        
        # Calculation time histogram
        calculation_time = self.get_or_create_metric(
            'histogram', 'calculation_time',
            'Calculation time in seconds',
            [], buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0]
        )
        # Add calculation time observations
        for ct in calculation_metrics.get('calculation_times', []):
            calculation_time.observe(ct)
        
        # Calculations per second gauge
        cps = self.get_or_create_metric(
            'gauge', 'calculations_per_second',
            'Calculations per second', []
        )
        cps.set(calculation_metrics.get('calculations_per_second', 0))
        
        # Calculation accuracy gauge
        accuracy = self.get_or_create_metric(
            'gauge', 'calculation_accuracy',
            'Calculation accuracy as a percentage', []
        )
        accuracy.set(calculation_metrics.get('accuracy', 100.0))
        
        # Process calculation type-specific metrics
        for calc_type, metrics in calculation_metrics.get('calculation_types', {}).items():
            # Calculation type counter
            type_calculations = self.get_or_create_metric(
                'counter', 'calculation_type_total',
                'Number of calculations by type',
                ['type']
            )
            type_calculations.labels(type=calc_type).inc(metrics.get('count', 0))
            
            # Calculation type error rate
            type_error_rate = self.get_or_create_metric(
                'gauge', 'calculation_type_error_rate',
                'Error rate by calculation type as a percentage',
                ['type']
            )
            type_error_rate.labels(type=calc_type).set(metrics.get('error_rate', 0))
            
            # Calculation type timing
            type_calculation_time = self.get_or_create_metric(
                'histogram', 'calculation_type_time',
                'Calculation time by type in seconds',
                ['type'], buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5]
            )
            # Add calculation time observations for this type
            for ct in metrics.get('calculation_times', []):
                type_calculation_time.labels(type=calc_type).observe(ct)
        
        logger.debug("Processed calculation metrics successfully")
    
    def process_resource_metrics(self, resource_metrics):
        """
        Process resource metrics and create Prometheus metrics
        
        Args:
            resource_metrics (dict): Dictionary containing resource metrics
        """
        # CPU utilization gauge
        cpu_utilization = self.get_or_create_metric(
            'gauge', 'cpu_utilization',
            'CPU utilization as a percentage', []
        )
        cpu_utilization.set(resource_metrics.get('cpu_utilization', 0))
        
        # Memory utilization gauge
        memory_utilization = self.get_or_create_metric(
            'gauge', 'memory_utilization',
            'Memory utilization as a percentage', []
        )
        memory_utilization.set(resource_metrics.get('memory_utilization', 0))
        
        # Disk utilization gauge
        disk_utilization = self.get_or_create_metric(
            'gauge', 'disk_utilization',
            'Disk utilization as a percentage', []
        )
        disk_utilization.set(resource_metrics.get('disk_utilization', 0))
        
        # Network throughput gauge
        network_throughput = self.get_or_create_metric(
            'gauge', 'network_throughput',
            'Network throughput in bytes per second', []
        )
        network_throughput.set(resource_metrics.get('network_throughput', 0))
        
        # Process component-specific resource metrics
        for component, metrics in resource_metrics.get('components', {}).items():
            # Component CPU utilization
            component_cpu = self.get_or_create_metric(
                'gauge', 'component_cpu_utilization',
                'CPU utilization by component as a percentage',
                ['component']
            )
            component_cpu.labels(component=component).set(metrics.get('cpu_utilization', 0))
            
            # Component memory utilization
            component_memory = self.get_or_create_metric(
                'gauge', 'component_memory_utilization',
                'Memory utilization by component as a percentage',
                ['component']
            )
            component_memory.labels(component=component).set(metrics.get('memory_utilization', 0))
            
        logger.debug("Processed resource metrics successfully")
    
    def get_or_create_metric(self, metric_type, name, description, labels=None, **kwargs):
        """
        Get an existing metric or create a new one if it doesn't exist
        
        Args:
            metric_type (str): Type of metric ('counter', 'gauge', 'histogram', 'summary')
            name (str): Name of the metric
            description (str): Description of the metric
            labels (list): List of label names for the metric
            **kwargs: Additional arguments for specific metric types
            
        Returns:
            object: Prometheus metric object
        """
        # Use empty list if labels is None
        labels = labels or []
        
        # Check if metric already exists
        metric_key = f"{metric_type}_{name}_{','.join(labels)}"
        if metric_key in self._metrics:
            return self._metrics[metric_key]
        
        # Create new metric based on type
        if metric_type == 'counter':
            metric = Counter(name, description, labels)
        elif metric_type == 'gauge':
            metric = Gauge(name, description, labels)
        elif metric_type == 'histogram':
            buckets = kwargs.get('buckets', Histogram.DEFAULT_BUCKETS)
            metric = Histogram(name, description, labels, buckets=buckets)
        elif metric_type == 'summary':
            quantiles = kwargs.get('quantiles', {0.5: 0.05, 0.9: 0.01, 0.99: 0.001})
            metric = Summary(name, description, labels, quantiles=quantiles)
        else:
            raise ValueError(f"Unknown metric type: {metric_type}")
        
        # Store metric for future reference
        self._metrics[metric_key] = metric
        return metric
    
    def write_metrics_to_file(self, file_path):
        """
        Write current metrics to a text file in Prometheus exposition format
        
        Args:
            file_path (str): Path to write the metrics file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Generate metrics in text format
            metrics_data = generate_latest()
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            # Write to file
            with open(file_path, 'wb') as f:
                f.write(metrics_data)
            
            logger.info(f"Written metrics to file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing metrics to file {file_path}: {str(e)}")
            return False