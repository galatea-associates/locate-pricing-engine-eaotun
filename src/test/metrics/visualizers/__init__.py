"""
Initialization module for the metrics visualizers package.

This module provides a unified interface for various metrics visualization tools used
during testing of the Borrow Rate & Locate Fee Pricing Engine.
"""

import logging
import abc
from .generate_charts import ChartGenerator
from .dashboard import DashboardGenerator

# Configure logger
logger = logging.getLogger(__name__)

# Export these classes
__all__ = ['MetricsVisualizer', 'ChartGenerator', 'DashboardGenerator']


class MetricsVisualizer(abc.ABC):
    """
    Abstract base class for all metrics visualizers, defining the common interface.
    """
    
    def __init__(self, config=None):
        """
        Initialize the base metrics visualizer with configuration.
        
        Args:
            config (dict): Configuration parameters for the visualizer
        """
        self.name = 'base_visualizer'
        self.config = config or {}
    
    @abc.abstractmethod
    def visualize(self, metrics_data, output_path):
        """
        Abstract method to generate visualizations from metrics data.
        
        Args:
            metrics_data (dict): Dictionary containing metrics data to visualize
            output_path (str): Path to save generated visualization files
            
        Returns:
            dict: Dictionary with paths to generated visualization files
        """
        pass
    
    def get_name(self):
        """
        Get the name of the visualizer.
        
        Returns:
            str: Visualizer name
        """
        return self.name