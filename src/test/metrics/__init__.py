"""
Initialization module for the metrics package, providing a unified interface for collecting,
exporting, and visualizing performance metrics during testing of the Borrow Rate & Locate Fee Pricing Engine.

This module serves as the entry point for the metrics subsystem, exposing key components 
from collectors, exporters, and visualizers subpackages.
"""

import logging
from typing import Dict, Any
from contextlib import contextmanager

# Import collectors
from .collectors import (
    MetricsCollector,
    APIMetricsCollector,
    CalculationMetricsCollector,
    ResourceMetricsCollector
)

# Import exporters
from .exporters import (
    MetricsExporter,
    PrometheusExporter,
    CSVExporter,
    JSONExporter
)

# Import visualizers
from .visualizers import (
    MetricsVisualizer,
    ChartGenerator,
    DashboardGenerator
)

# Setup logger
logger = logging.getLogger(__name__)

# Package version
__version__ = '1.0.0'

def get_collector(collector_type: str, config: Dict[str, Any] = None) -> MetricsCollector:
    """
    Factory function that returns an appropriate metrics collector based on the collector type.
    
    Args:
        collector_type: Type of collector to create ('api', 'calculation', 'resource')
        config: Configuration dictionary for the collector
        
    Returns:
        An instance of the requested metrics collector
        
    Raises:
        ValueError: If an unsupported collector type is provided
    """
    logger.info(f"Requesting metrics collector of type: {collector_type}")
    
    if collector_type == 'api':
        return APIMetricsCollector(config or {})
    elif collector_type == 'calculation':
        return CalculationMetricsCollector(config or {})
    elif collector_type == 'resource':
        return ResourceMetricsCollector(config or {})
    else:
        raise ValueError(f"Unsupported collector type: {collector_type}. "
                         f"Supported types are: api, calculation, resource")

def get_exporter(exporter_type: str, config: Dict[str, Any] = None) -> MetricsExporter:
    """
    Factory function that returns an appropriate metrics exporter based on the exporter type.
    
    Args:
        exporter_type: Type of exporter to create ('prometheus', 'csv', 'json')
        config: Configuration dictionary for the exporter
        
    Returns:
        An instance of the requested metrics exporter
        
    Raises:
        ValueError: If an unsupported exporter type is provided
    """
    logger.info(f"Requesting metrics exporter of type: {exporter_type}")
    
    if exporter_type == 'prometheus':
        return PrometheusExporter(config or {})
    elif exporter_type == 'csv':
        return CSVExporter(config or {})
    elif exporter_type == 'json':
        return JSONExporter(config or {})
    else:
        raise ValueError(f"Unsupported exporter type: {exporter_type}. "
                         f"Supported types are: prometheus, csv, json")

def get_visualizer(visualizer_type: str, config: Dict[str, Any] = None) -> MetricsVisualizer:
    """
    Factory function that returns an appropriate metrics visualizer based on the visualizer type.
    
    Args:
        visualizer_type: Type of visualizer to create ('chart', 'dashboard')
        config: Configuration dictionary for the visualizer
        
    Returns:
        An instance of the requested metrics visualizer
        
    Raises:
        ValueError: If an unsupported visualizer type is provided
    """
    logger.info(f"Requesting metrics visualizer of type: {visualizer_type}")
    
    if visualizer_type == 'chart':
        return ChartGenerator(config or {})
    elif visualizer_type == 'dashboard':
        return DashboardGenerator(config or {})
    else:
        raise ValueError(f"Unsupported visualizer type: {visualizer_type}. "
                         f"Supported types are: chart, dashboard")

@contextmanager
def collect_metrics(collector: MetricsCollector):
    """
    Context manager for collecting metrics during a test.
    
    This context manager handles starting and stopping the metrics collection process.
    After the context exits, you can retrieve the collected metrics by calling collector.collect().
    
    Args:
        collector: The metrics collector to use
        
    Yields:
        The metrics collector for use within the context
    
    Example:
        >>> collector = get_collector('api')
        >>> with collect_metrics(collector):
        >>>     # Run your test here
        >>>     api_client.make_request()
        >>> metrics_data = collector.collect()
    """
    logger.info(f"Starting metrics collection with {collector.get_name()}")
    collector.reset()
    
    try:
        # Start metrics collection
        collector.start_collection()
        
        # Yield control back to the caller
        yield collector
    finally:
        # Stop collection
        collector.stop_collection()
        logger.info(f"Completed metrics collection with {collector.get_name()}")

def export_metrics(metrics_data: Dict[str, Any], exporter: MetricsExporter, output_path: str) -> Dict[str, Any]:
    """
    Export collected metrics using the specified exporter.
    
    Args:
        metrics_data: Dictionary containing metrics data to export
        exporter: The metrics exporter to use
        output_path: Path where metrics should be exported
        
    Returns:
        Export results with file paths
    
    Example:
        >>> metrics_data = collector.collect()
        >>> exporter = get_exporter('json')
        >>> results = export_metrics(metrics_data, exporter, '/path/to/output')
    """
    logger.info(f"Exporting metrics with {exporter.get_name()} to {output_path}")
    
    result = exporter.export(metrics_data, output_path)
    
    logger.info(f"Completed metrics export with {exporter.get_name()}")
    return result

def visualize_metrics(metrics_data: Dict[str, Any], visualizer: MetricsVisualizer, output_path: str) -> Dict[str, Any]:
    """
    Generate visualizations from metrics data using the specified visualizer.
    
    Args:
        metrics_data: Dictionary containing metrics data to visualize
        visualizer: The metrics visualizer to use
        output_path: Path where visualizations should be saved
        
    Returns:
        Visualization results with file paths
    
    Example:
        >>> metrics_data = collector.collect()
        >>> visualizer = get_visualizer('chart')
        >>> results = visualize_metrics(metrics_data, visualizer, '/path/to/output')
    """
    logger.info(f"Visualizing metrics with {visualizer.get_name()} to {output_path}")
    
    result = visualizer.visualize(metrics_data, output_path)
    
    logger.info(f"Completed metrics visualization with {visualizer.get_name()}")
    return result