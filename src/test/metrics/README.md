# Metrics Framework

## Purpose

The metrics framework provides a comprehensive solution for collecting, exporting, and visualizing performance metrics during testing of the Borrow Rate & Locate Fee Pricing Engine. It enables detailed analysis of API performance, calculation accuracy, and resource utilization to ensure the system meets its performance requirements.

## Key Features

- Modular architecture with collectors, exporters, and visualizers
- Support for API performance metrics (response time, throughput, error rates)
- Support for calculation metrics (execution time, accuracy, throughput)
- Support for resource utilization metrics (CPU, memory, network, disk)
- Multiple export formats (JSON, CSV, Prometheus)
- Visualization capabilities with charts and dashboards
- Integration with test automation framework

# Directory Structure

## Overview

The metrics framework is organized into the following directories:

- `collectors/`: Modules for collecting different types of metrics
- `exporters/`: Modules for exporting metrics to various formats
- `visualizers/`: Modules for generating visualizations from metrics data

## Collectors

- `api_metrics.py`: Collects API performance metrics (response time, throughput, error rates)
- `calculation_metrics.py`: Collects calculation performance metrics (execution time, accuracy)
- `resource_metrics.py`: Collects system resource utilization metrics (CPU, memory, network, disk)

## Exporters

- `prometheus.py`: Exports metrics to Prometheus format
- `csv.py`: Exports metrics to CSV files
- `json.py`: Exports metrics to JSON files

## Visualizers

- `generate_charts.py`: Generates charts and graphs from metrics data
- `dashboard.py`: Creates dashboards for visualizing metrics

# Usage Guide

## Basic Usage

```python
# Import the metrics manager
from metrics import MetricsManager

# Create a metrics manager instance
metrics_manager = MetricsManager()

# Start collecting metrics
metrics_manager.collect_metrics(['api_metrics', 'resource_metrics'])

# Run your tests here

# Export metrics to JSON format
results = metrics_manager.export_metrics(
    metrics_data,
    ['json'],
    'output/path'
)

# Generate visualizations
charts = metrics_manager.visualize_metrics(
    metrics_data,
    ['chart_generator'],
    'output/path'
)
```

## Integration with Test Framework

The metrics framework can be integrated with the test automation framework using pytest fixtures:

```python
@pytest.fixture(scope='session')
def metrics_manager():
    manager = MetricsManager()
    yield manager

@pytest.fixture(autouse=True)
def collect_metrics(metrics_manager, request):
    # Start collecting metrics before each test
    metrics_manager.collect_metrics(['api_metrics', 'resource_metrics'])
    
    yield
    
    # Export and visualize metrics after each test
    metrics_data = metrics_manager.collect_metrics(['api_metrics', 'resource_metrics'])
    metrics_manager.export_metrics(metrics_data, ['json'], 'test_results/metrics')
    metrics_manager.visualize_metrics(metrics_data, ['chart_generator'], 'test_results/charts')
```

## Recording API Metrics

To record API metrics during testing:

```python
from metrics.collectors.api_metrics import APIMetricsCollector

# Create collector instance
api_collector = APIMetricsCollector()

# Start collection
api_collector.start_collection()

# Record API requests
api_collector.record_request('/api/v1/calculate-locate', 45.3, False)  # 45.3ms, no error
api_collector.record_request('/api/v1/rates/AAPL', 32.1, False)  # 32.1ms, no error
api_collector.record_request('/api/v1/calculate-locate', 0, True)  # Error occurred

# Stop collection
api_collector.stop_collection()

# Collect metrics
metrics = api_collector.collect()
```

## Customizing Visualizations

The chart generator can be customized with different chart types and styles:

```python
from metrics.visualizers.generate_charts import ChartGenerator

# Create chart generator with custom configuration
chart_generator = ChartGenerator({
    'style': 'seaborn-v0_8-whitegrid',
    'dpi': 300,
    'figure_size': (10, 6)
})

# Generate visualizations
charts = chart_generator.visualize(metrics_data, 'output/path')
```

# Metrics Reference

## API Metrics

- `total_requests`: Total number of API requests recorded
- `total_errors`: Total number of API errors recorded
- `error_rate`: Percentage of requests that resulted in errors
- `requests_per_second`: Average number of requests per second
- `response_time_min`: Minimum response time in milliseconds
- `response_time_max`: Maximum response time in milliseconds
- `response_time_avg`: Average response time in milliseconds
- `response_time_p50`: Median (50th percentile) response time
- `response_time_p95`: 95th percentile response time
- `response_time_p99`: 99th percentile response time
- `endpoints`: Per-endpoint breakdown of the above metrics

## Calculation Metrics

- `total_calculations`: Total number of calculations performed
- `calculation_errors`: Number of calculation errors or inaccuracies
- `accuracy_rate`: Percentage of calculations that were accurate
- `calculations_per_second`: Average number of calculations per second
- `execution_time_min`: Minimum calculation execution time in milliseconds
- `execution_time_max`: Maximum calculation execution time in milliseconds
- `execution_time_avg`: Average calculation execution time in milliseconds
- `execution_time_p50`: Median execution time
- `execution_time_p95`: 95th percentile execution time
- `execution_time_p99`: 99th percentile execution time
- `calculation_types`: Per-calculation-type breakdown of metrics

## Resource Metrics

- `cpu_utilization`: CPU utilization percentage over time
- `memory_usage`: Memory usage in MB over time
- `memory_percentage`: Memory usage as percentage of available memory
- `network_received`: Network bytes received over time
- `network_sent`: Network bytes sent over time
- `disk_read`: Disk read operations over time
- `disk_write`: Disk write operations over time
- `disk_usage`: Disk space usage percentage

# Export Formats

## JSON Format

Exports metrics to JSON files with the following structure:

```json
{
  "metadata": {
    "timestamp": "20230815_143022",
    "metrics_type": "api_metrics",
    "version": "1.0.0",
    "datetime": "2023-08-15T14:30:22.123456"
  },
  "metrics": {
    "total_requests": 1500,
    "total_errors": 15,
    "error_rate": 1.0,
    "requests_per_second": 750.0,
    "response_time_min": 15.2,
    "response_time_max": 245.7,
    "response_time_avg": 85.3,
    "response_time_p50": 78.5,
    "response_time_p95": 180.2,
    "response_time_p99": 220.1,
    "endpoints": {
      "/api/v1/calculate-locate": {
        "requests": 1000,
        "errors": 10,
        "error_rate": 1.0,
        "response_time_stats": {
          "min": 20.5,
          "max": 245.7,
          "avg": 90.2,
          "p50": 85.1,
          "p95": 185.3,
          "p99": 225.6
        }
      }
    }
  }
}
```

## CSV Format

Exports metrics to CSV files with headers and values. Multiple CSV files are generated for different metric types and levels of detail.

## Prometheus Format

Exports metrics in Prometheus exposition format for integration with Prometheus monitoring system:

```
# HELP api_total_requests Total number of API requests
# TYPE api_total_requests counter
api_total_requests 1500

# HELP api_response_time_seconds API response time in seconds
# TYPE api_response_time_seconds histogram
api_response_time_seconds_bucket{le="0.05"} 250
api_response_time_seconds_bucket{le="0.1"} 800
api_response_time_seconds_bucket{le="0.2"} 1400
api_response_time_seconds_bucket{le="0.5"} 1500
api_response_time_seconds_bucket{le="+Inf"} 1500
api_response_time_seconds_sum 127.95
api_response_time_seconds_count 1500
```

# Visualization Types

## API Performance Charts

- Response time distribution histogram
- Response time percentiles (p50, p95, p99) bar chart
- Requests per second over time line chart
- Error rate over time line chart
- Endpoint comparison bar chart

## Calculation Performance Charts

- Execution time distribution histogram
- Execution time percentiles bar chart
- Calculations per second over time line chart
- Accuracy rate pie chart
- Calculation type comparison bar chart

## Resource Utilization Charts

- CPU utilization over time line chart
- Memory usage over time line chart
- Network I/O over time line chart
- Disk I/O over time line chart
- Resource utilization heatmap

## Dashboard

The dashboard generator creates HTML dashboards with interactive charts for comprehensive visualization of all metrics.

# Configuration

## Global Configuration

The metrics framework can be configured with the following options:

```python
config = {
    'log_level': 'INFO',  # Logging level (DEBUG, INFO, WARNING, ERROR)
    'timestamp_format': '%Y%m%d_%H%M%S',  # Format for timestamp in filenames
    'output_path': 'test_results/metrics',  # Default output path
    'collectors': {  # Collector-specific configuration
        'api_metrics': {
            'include_endpoints': ['*'],  # Endpoints to include (default all)
            'exclude_endpoints': []  # Endpoints to exclude
        },
        'calculation_metrics': {
            'accuracy_threshold': 0.0001  # Threshold for accuracy comparison
        },
        'resource_metrics': {
            'sample_interval': 1.0  # Sampling interval in seconds
        }
    },
    'exporters': {  # Exporter-specific configuration
        'json': {
            'pretty_print': True  # Whether to format JSON with indentation
        },
        'csv': {
            'delimiter': ','  # CSV delimiter character
        },
        'prometheus': {
            'include_histograms': True  # Whether to include histogram metrics
        }
    },
    'visualizers': {  # Visualizer-specific configuration
        'chart_generator': {
            'style': 'seaborn-v0_8-darkgrid',  # Matplotlib style
            'dpi': 100,  # Chart resolution
            'figure_size': (8, 6)  # Default figure size (width, height)
        }
    }
}

# Create metrics manager with configuration
metrics_manager = MetricsManager(config)
```

## Environment Variables

The following environment variables can be used to configure the metrics framework:

- `METRICS_LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `METRICS_OUTPUT_PATH`: Default output path for metrics files
- `METRICS_TIMESTAMP_FORMAT`: Format for timestamp in filenames
- `METRICS_PRETTY_PRINT`: Whether to format JSON with indentation (TRUE/FALSE)
- `METRICS_CHART_DPI`: Resolution for generated charts (e.g., 100)

# Contributing

## Adding New Collectors

To add a new metrics collector:

1. Create a new file in the `collectors/` directory
2. Implement a class that inherits from `BaseMetricsCollector`
3. Implement the required methods: `start_collection()`, `stop_collection()`, `collect()`, and `reset()`
4. Register the collector in `__init__.py`

## Adding New Exporters

To add a new metrics exporter:

1. Create a new file in the `exporters/` directory
2. Implement a class with an `export(metrics_data, output_path)` method
3. Register the exporter in `__init__.py`

## Adding New Visualizers

To add a new metrics visualizer:

1. Create a new file in the `visualizers/` directory
2. Implement a class with a `visualize(metrics_data, output_path)` method
3. Register the visualizer in `__init__.py`

# Examples

## Load Testing

Example of using the metrics framework for load testing:

```python
from metrics import MetricsManager
from locust import HttpUser, task, between

class LoadTestUser(HttpUser):
    wait_time = between(1, 3)
    metrics_manager = MetricsManager()
    
    def on_start(self):
        self.metrics_manager.collect_metrics(['api_metrics', 'resource_metrics'])
    
    @task
    def calculate_locate_fee(self):
        start_time = time.time()
        response = self.client.post(
            "/api/v1/calculate-locate",
            json={
                "ticker": "AAPL",
                "position_value": 100000,
                "loan_days": 30,
                "client_id": "test_client"
            }
        )
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        
        # Record metrics manually
        self.metrics_manager.collectors['api_metrics'].record_request(
            '/api/v1/calculate-locate',
            response_time_ms,
            response.status_code >= 400
        )
    
    def on_stop(self):
        metrics_data = self.metrics_manager.collect_metrics(['api_metrics', 'resource_metrics'])
        self.metrics_manager.export_metrics(metrics_data, ['json', 'csv'], 'load_test_results')
        self.metrics_manager.visualize_metrics(metrics_data, ['chart_generator'], 'load_test_results/charts')
```

## Performance Benchmarking

Example of using the metrics framework for performance benchmarking:

```python
from metrics import MetricsManager
import requests
import time
import statistics

def benchmark_api_endpoint(url, payload, num_requests=1000):
    metrics_manager = MetricsManager()
    metrics_manager.collect_metrics(['api_metrics'])
    
    for _ in range(num_requests):
        start_time = time.time()
        response = requests.post(url, json=payload)
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        
        metrics_manager.collectors['api_metrics'].record_request(
            url,
            response_time_ms,
            response.status_code >= 400
        )
    
    metrics_data = metrics_manager.collect_metrics(['api_metrics'])
    metrics_manager.export_metrics(metrics_data, ['json'], 'benchmark_results')
    metrics_manager.visualize_metrics(metrics_data, ['chart_generator'], 'benchmark_results/charts')
    
    return metrics_data

# Run benchmark
results = benchmark_api_endpoint(
    'http://localhost:8000/api/v1/calculate-locate',
    {
        "ticker": "AAPL",
        "position_value": 100000,
        "loan_days": 30,
        "client_id": "test_client"
    },
    num_requests=1000
)

# Print summary
print(f"Average response time: {results['api_metrics']['response_time_avg']:.2f} ms")
print(f"95th percentile: {results['api_metrics']['response_time_p95']:.2f} ms")
print(f"Requests per second: {results['api_metrics']['requests_per_second']:.2f}")
```