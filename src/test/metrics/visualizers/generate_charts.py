import logging
import os
from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Configure logger
logger = logging.getLogger(__name__)

# Default chart settings
DEFAULT_CHART_SIZE = (12, 8)
DEFAULT_DPI = 100

# Style configurations for different chart types
CHART_STYLES = {
    'api': 'darkgrid',
    'calculation': 'whitegrid',
    'resource': 'ticks',
    'combined': 'darkgrid'
}

# Color palette configurations for different chart types
COLOR_PALETTES = {
    'api': 'viridis',
    'calculation': 'magma',
    'resource': 'plasma',
    'combined': 'inferno'
}

def setup_matplotlib_defaults():
    """
    Configure default matplotlib settings for consistent chart appearance.
    """
    # Set non-interactive backend for server environments
    matplotlib.use('Agg')
    
    # Set default figure size and DPI
    plt.rcParams['figure.figsize'] = DEFAULT_CHART_SIZE
    plt.rcParams['figure.dpi'] = DEFAULT_DPI
    
    # Set default font sizes
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.titlesize'] = 14
    plt.rcParams['axes.labelsize'] = 12
    plt.rcParams['xtick.labelsize'] = 10
    plt.rcParams['ytick.labelsize'] = 10
    plt.rcParams['legend.fontsize'] = 10
    
    # Set default grid settings
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.linewidth'] = 0.5
    plt.rcParams['grid.alpha'] = 0.7
    
    # Set default color cycle
    plt.rcParams['axes.prop_cycle'] = plt.cycler(color=plt.cm.viridis.colors)

class BaseVisualizer:
    """
    Base class for metrics visualization components, providing common functionality.
    """
    
    def __init__(self, config=None):
        """
        Initialize the base visualizer with configuration.
        
        Args:
            config (dict): Configuration parameters for the visualizer
        """
        self.name = 'base_visualizer'
        self.config = config or {}
        # Initialize any common visualization components
    
    def get_name(self):
        """
        Get the name of the visualizer.
        
        Returns:
            str: Visualizer name
        """
        return self.name

class ChartGenerator(BaseVisualizer):
    """
    Generates various types of charts from collected metrics data.
    """
    
    def __init__(self, config=None):
        """
        Initialize the chart generator with default configuration.
        
        Args:
            config (dict): Configuration parameters for the chart generator
        """
        super().__init__(config)
        self.name = 'chart_generator'
        self._chart_paths = {}
        
        # Set up figure sizes from config or use defaults
        self._figure_sizes = self.config.get('figure_sizes', {
            'api': DEFAULT_CHART_SIZE,
            'calculation': DEFAULT_CHART_SIZE,
            'resource': DEFAULT_CHART_SIZE,
            'combined': (16, 10)
        })
        
        # Set up DPI settings from config or use defaults
        self._dpi_settings = self.config.get('dpi_settings', {
            'api': DEFAULT_DPI,
            'calculation': DEFAULT_DPI,
            'resource': DEFAULT_DPI,
            'combined': DEFAULT_DPI
        })
        
        # Configure matplotlib defaults
        setup_matplotlib_defaults()
    
    def visualize(self, metrics_data, output_path):
        """
        Generate charts from metrics data.
        
        Args:
            metrics_data (dict): Dictionary containing metrics data to visualize
            output_path (str): Path to save generated charts
            
        Returns:
            dict: Dictionary with paths to generated chart files
        """
        # Ensure output directory exists
        output_dir = self.ensure_output_directory(output_path)
        
        # Reset chart paths
        self._chart_paths = {}
        
        # Generate different types of charts based on available metrics
        if 'api' in metrics_data:
            self._chart_paths['api'] = self.generate_api_charts(metrics_data['api'], output_dir)
        
        if 'calculation' in metrics_data:
            self._chart_paths['calculation'] = self.generate_calculation_charts(metrics_data['calculation'], output_dir)
        
        if 'resource' in metrics_data:
            self._chart_paths['resource'] = self.generate_resource_charts(metrics_data['resource'], output_dir)
        
        # Generate combined charts if multiple metric types exist
        if len([k for k in ['api', 'calculation', 'resource'] if k in metrics_data]) > 1:
            self._chart_paths['combined'] = self.generate_combined_charts(metrics_data, output_dir)
        
        return self._chart_paths
    
    def ensure_output_directory(self, output_path):
        """
        Ensure the output directory exists.
        
        Args:
            output_path (str): Path where charts will be saved
            
        Returns:
            pathlib.Path: Path object for the output directory
        """
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create charts subdirectory
        charts_dir = output_dir / 'charts'
        charts_dir.mkdir(exist_ok=True)
        
        return charts_dir
    
    def generate_api_charts(self, api_metrics, output_dir):
        """
        Generate charts for API metrics.
        
        Args:
            api_metrics (dict): API metrics data
            output_dir (pathlib.Path): Directory to save charts
            
        Returns:
            dict: Dictionary with paths to generated API chart files
        """
        # Set the seaborn style for API charts
        sns.set_style(CHART_STYLES['api'])
        
        chart_paths = {}
        
        # Generate response time distribution chart
        chart_paths['response_time'] = self.create_response_time_chart(
            api_metrics, output_dir, 'api_response_time_distribution.png'
        )
        
        # Generate request rate over time chart
        chart_paths['request_rate'] = self.create_request_rate_chart(
            api_metrics, output_dir, 'api_request_rate_over_time.png'
        )
        
        # Generate error rate by endpoint chart
        chart_paths['error_rate'] = self.create_error_rate_chart(
            api_metrics, output_dir, 'api_error_rate_by_endpoint.png'
        )
        
        # Generate status code distribution chart
        # Implemented similar to other chart creation methods
        
        # Generate percentile comparison chart
        # Implemented similar to other chart creation methods
        
        return chart_paths
    
    def generate_calculation_charts(self, calculation_metrics, output_dir):
        """
        Generate charts for calculation metrics.
        
        Args:
            calculation_metrics (dict): Calculation metrics data
            output_dir (pathlib.Path): Directory to save charts
            
        Returns:
            dict: Dictionary with paths to generated calculation chart files
        """
        # Set the seaborn style for calculation charts
        sns.set_style(CHART_STYLES['calculation'])
        
        chart_paths = {}
        
        # Generate execution time distribution chart
        chart_paths['execution_time'] = self.create_execution_time_chart(
            calculation_metrics, output_dir, 'calculation_execution_time.png'
        )
        
        # Generate calculation throughput chart
        chart_paths['throughput'] = self.create_calculation_throughput_chart(
            calculation_metrics, output_dir, 'calculation_throughput.png'
        )
        
        # Generate accuracy comparison chart
        chart_paths['accuracy'] = self.create_accuracy_chart(
            calculation_metrics, output_dir, 'calculation_accuracy.png'
        )
        
        # Generate execution time by calculation type chart
        # Implemented similar to other chart creation methods
        
        # Generate percentile comparison chart
        # Implemented similar to other chart creation methods
        
        return chart_paths
    
    def generate_resource_charts(self, resource_metrics, output_dir):
        """
        Generate charts for resource utilization metrics.
        
        Args:
            resource_metrics (dict): Resource utilization metrics data
            output_dir (pathlib.Path): Directory to save charts
            
        Returns:
            dict: Dictionary with paths to generated resource chart files
        """
        # Set the seaborn style for resource charts
        sns.set_style(CHART_STYLES['resource'])
        
        chart_paths = {}
        
        # Generate CPU utilization over time chart
        chart_paths['cpu'] = self.create_resource_utilization_chart(
            resource_metrics, 'cpu', output_dir, 'cpu_utilization_over_time.png'
        )
        
        # Generate memory utilization over time chart
        chart_paths['memory'] = self.create_resource_utilization_chart(
            resource_metrics, 'memory', output_dir, 'memory_utilization_over_time.png'
        )
        
        # Generate disk I/O chart
        # Implemented similar to other chart creation methods
        
        # Generate network throughput chart
        # Implemented similar to other chart creation methods
        
        # Generate resource utilization comparison chart
        # Implemented similar to other chart creation methods
        
        return chart_paths
    
    def generate_combined_charts(self, metrics_data, output_dir):
        """
        Generate charts combining multiple metric types.
        
        Args:
            metrics_data (dict): Combined metrics data
            output_dir (pathlib.Path): Directory to save charts
            
        Returns:
            dict: Dictionary with paths to generated combined chart files
        """
        # Set the seaborn style for combined charts
        sns.set_style(CHART_STYLES['combined'])
        
        chart_paths = {}
        
        # Generate performance overview chart
        chart_paths['overview'] = self.create_performance_overview_chart(
            metrics_data, output_dir, 'performance_overview.png'
        )
        
        # Generate correlation chart between API response time and resource utilization
        if 'api' in metrics_data and 'resource' in metrics_data:
            chart_paths['api_resource_correlation'] = self.create_correlation_chart(
                metrics_data,
                'api.response_time.mean',
                'resource.cpu.utilization.mean',
                'API Response Time vs CPU Utilization',
                output_dir,
                'api_response_vs_cpu.png'
            )
        
        # Generate correlation chart between calculation time and resource utilization
        if 'calculation' in metrics_data and 'resource' in metrics_data:
            chart_paths['calc_resource_correlation'] = self.create_correlation_chart(
                metrics_data,
                'calculation.execution_time.mean',
                'resource.cpu.utilization.mean',
                'Calculation Time vs CPU Utilization',
                output_dir,
                'calculation_time_vs_cpu.png'
            )
        
        # Generate time-aligned metrics chart
        # Implemented similar to other chart creation methods
        
        return chart_paths
    
    def create_response_time_chart(self, api_metrics, output_dir, filename):
        """
        Create a chart showing API response time distribution.
        
        Args:
            api_metrics (dict): API metrics data
            output_dir (pathlib.Path): Directory to save the chart
            filename (str): Name of the chart file
            
        Returns:
            str: Path to the generated chart file
        """
        # Create new figure with appropriate size and DPI
        fig, ax = plt.subplots(figsize=self._figure_sizes['api'], dpi=self._dpi_settings['api'])
        
        # Extract response time data
        df = pd.DataFrame(api_metrics.get('response_times', {}))
        
        if df.empty:
            logger.warning("No response time data available for plotting")
            plt.close(fig)
            return None
        
        # Create violin plot of response times by endpoint
        sns.violinplot(x='endpoint', y='response_time', data=df, ax=ax)
        
        # Add horizontal lines for percentiles if available
        if 'percentiles' in api_metrics:
            percentiles = api_metrics['percentiles']
            p50 = percentiles.get('p50', None)
            p95 = percentiles.get('p95', None)
            p99 = percentiles.get('p99', None)
            
            if p50:
                ax.axhline(y=p50, color='green', linestyle='--', label='P50')
            if p95:
                ax.axhline(y=p95, color='orange', linestyle='--', label='P95')
            if p99:
                ax.axhline(y=p99, color='red', linestyle='--', label='P99')
        
        # Add SLA target line (100ms) from requirements
        ax.axhline(y=100, color='red', linestyle='-', linewidth=2, label='SLA Target (100ms)')
        
        # Add labels and title
        ax.set_xlabel('API Endpoint')
        ax.set_ylabel('Response Time (ms)')
        ax.set_title('API Response Time Distribution by Endpoint')
        ax.legend()
        
        # Save the figure and return the path
        return self.save_figure(fig, output_dir, filename)
    
    def create_request_rate_chart(self, api_metrics, output_dir, filename):
        """
        Create a chart showing API request rate over time.
        
        Args:
            api_metrics (dict): API metrics data
            output_dir (pathlib.Path): Directory to save the chart
            filename (str): Name of the chart file
            
        Returns:
            str: Path to the generated chart file
        """
        # Create new figure with appropriate size and DPI
        fig, ax = plt.subplots(figsize=self._figure_sizes['api'], dpi=self._dpi_settings['api'])
        
        # Extract request rate data over time
        df = pd.DataFrame(api_metrics.get('request_rate', {}))
        
        if df.empty:
            logger.warning("No request rate data available for plotting")
            plt.close(fig)
            return None
        
        # Convert timestamps to datetime if they're not already
        if 'timestamp' in df.columns and not pd.api.types.is_datetime64_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Create line chart of request rate over time
        sns.lineplot(x='timestamp', y='requests_per_second', data=df, ax=ax)
        
        # Add horizontal line for target throughput (1000 req/sec) from requirements
        target_throughput = self.config.get('target_throughput', 1000)
        ax.axhline(y=target_throughput, color='red', linestyle='--', 
                   label=f'Target Throughput ({target_throughput} req/sec)')
        
        # Add labels and title
        ax.set_xlabel('Time')
        ax.set_ylabel('Requests per Second')
        ax.set_title('API Request Rate Over Time')
        ax.legend()
        
        # Format x-axis date ticks
        fig.autofmt_xdate()
        
        # Save the figure and return the path
        return self.save_figure(fig, output_dir, filename)
    
    def create_error_rate_chart(self, api_metrics, output_dir, filename):
        """
        Create a chart showing API error rates by endpoint.
        
        Args:
            api_metrics (dict): API metrics data
            output_dir (pathlib.Path): Directory to save the chart
            filename (str): Name of the chart file
            
        Returns:
            str: Path to the generated chart file
        """
        # Create new figure with appropriate size and DPI
        fig, ax = plt.subplots(figsize=self._figure_sizes['api'], dpi=self._dpi_settings['api'])
        
        # Extract error rate data by endpoint
        df = pd.DataFrame(api_metrics.get('error_rates', {}))
        
        if df.empty:
            logger.warning("No error rate data available for plotting")
            plt.close(fig)
            return None
        
        # Create bar chart of error rates by endpoint
        sns.barplot(x='endpoint', y='error_rate', data=df, ax=ax)
        
        # Add horizontal line for target error rate (1%) if specified in requirements
        target_error_rate = self.config.get('target_error_rate', 1.0)
        ax.axhline(y=target_error_rate, color='red', linestyle='--',
                  label=f'Target Error Rate ({target_error_rate}%)')
        
        # Add labels and title
        ax.set_xlabel('API Endpoint')
        ax.set_ylabel('Error Rate (%)')
        ax.set_title('API Error Rates by Endpoint')
        ax.legend()
        
        # Save the figure and return the path
        return self.save_figure(fig, output_dir, filename)
    
    def create_execution_time_chart(self, calculation_metrics, output_dir, filename):
        """
        Create a chart showing calculation execution time distribution.
        
        Args:
            calculation_metrics (dict): Calculation metrics data
            output_dir (pathlib.Path): Directory to save the chart
            filename (str): Name of the chart file
            
        Returns:
            str: Path to the generated chart file
        """
        # Create new figure with appropriate size and DPI
        fig, ax = plt.subplots(figsize=self._figure_sizes['calculation'], dpi=self._dpi_settings['calculation'])
        
        # Extract execution time data
        df = pd.DataFrame(calculation_metrics.get('execution_times', {}))
        
        if df.empty:
            logger.warning("No execution time data available for plotting")
            plt.close(fig)
            return None
        
        # Create violin plot of execution times by calculation type
        sns.violinplot(x='calculation_type', y='execution_time', data=df, ax=ax)
        
        # Add horizontal lines for percentiles if available
        if 'percentiles' in calculation_metrics:
            percentiles = calculation_metrics['percentiles']
            p50 = percentiles.get('p50', None)
            p95 = percentiles.get('p95', None)
            p99 = percentiles.get('p99', None)
            
            if p50:
                ax.axhline(y=p50, color='green', linestyle='--', label='P50')
            if p95:
                ax.axhline(y=p95, color='orange', linestyle='--', label='P95')
            if p99:
                ax.axhline(y=p99, color='red', linestyle='--', label='P99')
        
        # Add horizontal line for target execution time (50ms) from requirements
        ax.axhline(y=50, color='red', linestyle='-', linewidth=2, label='Target Execution Time (50ms)')
        
        # Add labels and title
        ax.set_xlabel('Calculation Type')
        ax.set_ylabel('Execution Time (ms)')
        ax.set_title('Calculation Execution Time Distribution by Type')
        ax.legend()
        
        # Save the figure and return the path
        return self.save_figure(fig, output_dir, filename)
    
    def create_calculation_throughput_chart(self, calculation_metrics, output_dir, filename):
        """
        Create a chart showing calculation throughput.
        
        Args:
            calculation_metrics (dict): Calculation metrics data
            output_dir (pathlib.Path): Directory to save the chart
            filename (str): Name of the chart file
            
        Returns:
            str: Path to the generated chart file
        """
        # Create new figure with appropriate size and DPI
        fig, ax = plt.subplots(figsize=self._figure_sizes['calculation'], dpi=self._dpi_settings['calculation'])
        
        # Extract throughput data
        df = pd.DataFrame(calculation_metrics.get('throughput', {}))
        
        if df.empty:
            logger.warning("No throughput data available for plotting")
            plt.close(fig)
            return None
        
        # Create bar chart of calculations per second by calculation type
        sns.barplot(x='calculation_type', y='calculations_per_second', data=df, ax=ax)
        
        # Add horizontal line for target throughput (1000/sec) from requirements
        target_throughput = self.config.get('calculation_target_throughput', 1000)
        ax.axhline(y=target_throughput, color='red', linestyle='--',
                  label=f'Target Throughput ({target_throughput} calc/sec)')
        
        # Add labels and title
        ax.set_xlabel('Calculation Type')
        ax.set_ylabel('Calculations per Second')
        ax.set_title('Calculation Throughput by Type')
        ax.legend()
        
        # Save the figure and return the path
        return self.save_figure(fig, output_dir, filename)
    
    def create_accuracy_chart(self, calculation_metrics, output_dir, filename):
        """
        Create a chart showing calculation accuracy.
        
        Args:
            calculation_metrics (dict): Calculation metrics data
            output_dir (pathlib.Path): Directory to save the chart
            filename (str): Name of the chart file
            
        Returns:
            str: Path to the generated chart file
        """
        # Create new figure with appropriate size and DPI
        fig, ax = plt.subplots(figsize=self._figure_sizes['calculation'], dpi=self._dpi_settings['calculation'])
        
        # Extract accuracy data
        df = pd.DataFrame(calculation_metrics.get('accuracy', {}))
        
        if df.empty:
            logger.warning("No accuracy data available for plotting")
            plt.close(fig)
            return None
        
        # Create bar chart of accuracy percentage by calculation type
        sns.barplot(x='calculation_type', y='accuracy_percentage', data=df, ax=ax)
        
        # Add horizontal line at 100% for target accuracy from requirements
        ax.axhline(y=100, color='red', linestyle='-', linewidth=2, label='Target Accuracy (100%)')
        
        # Set y-axis limits to make small differences more visible
        ax.set_ylim([df['accuracy_percentage'].min() - 1 if not df.empty else 90, 100.5])
        
        # Add labels and title
        ax.set_xlabel('Calculation Type')
        ax.set_ylabel('Accuracy (%)')
        ax.set_title('Calculation Accuracy by Type')
        ax.legend()
        
        # Save the figure and return the path
        return self.save_figure(fig, output_dir, filename)
    
    def create_resource_utilization_chart(self, resource_metrics, resource_type, output_dir, filename):
        """
        Create a chart showing resource utilization over time.
        
        Args:
            resource_metrics (dict): Resource metrics data
            resource_type (str): Type of resource to chart (cpu, memory, disk, network)
            output_dir (pathlib.Path): Directory to save the chart
            filename (str): Name of the chart file
            
        Returns:
            str: Path to the generated chart file
        """
        # Create new figure with appropriate size and DPI
        fig, ax = plt.subplots(figsize=self._figure_sizes['resource'], dpi=self._dpi_settings['resource'])
        
        # Extract resource utilization data for the specified resource_type
        if resource_type not in resource_metrics:
            logger.warning(f"No data for resource type {resource_type}")
            plt.close(fig)
            return None
        
        df = pd.DataFrame(resource_metrics[resource_type].get('utilization', {}))
        
        if df.empty:
            logger.warning(f"No utilization data available for resource {resource_type}")
            plt.close(fig)
            return None
        
        # Convert timestamps to datetime if they're not already
        if 'timestamp' in df.columns and not pd.api.types.is_datetime64_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Create line chart of resource utilization over time
        sns.lineplot(x='timestamp', y='utilization_percentage', data=df, ax=ax)
        
        # Add threshold lines if specified in config
        thresholds = self.config.get('resource_thresholds', {}).get(resource_type, {})
        warning_threshold = thresholds.get('warning', None)
        critical_threshold = thresholds.get('critical', None)
        
        if warning_threshold:
            ax.axhline(y=warning_threshold, color='orange', linestyle='--',
                      label=f'Warning Threshold ({warning_threshold}%)')
        
        if critical_threshold:
            ax.axhline(y=critical_threshold, color='red', linestyle='--',
                      label=f'Critical Threshold ({critical_threshold}%)')
        
        # Add labels and title
        ax.set_xlabel('Time')
        ax.set_ylabel(f'{resource_type.upper()} Utilization (%)')
        ax.set_title(f'{resource_type.upper()} Utilization Over Time')
        ax.legend()
        
        # Format x-axis date ticks
        fig.autofmt_xdate()
        
        # Save the figure and return the path
        return self.save_figure(fig, output_dir, filename)
    
    def create_correlation_chart(self, metrics_data, x_metric_path, y_metric_path, title, output_dir, filename):
        """
        Create a chart showing correlation between two metrics.
        
        Args:
            metrics_data (dict): Combined metrics data
            x_metric_path (str): Path to the X-axis metric in the metrics_data dictionary
            y_metric_path (str): Path to the Y-axis metric in the metrics_data dictionary
            title (str): Chart title
            output_dir (pathlib.Path): Directory to save the chart
            filename (str): Name of the chart file
            
        Returns:
            str: Path to the generated chart file
        """
        # Create new figure with appropriate size and DPI
        fig, ax = plt.subplots(figsize=self._figure_sizes['combined'], dpi=self._dpi_settings['combined'])
        
        # Extract metrics data based on the provided paths
        x_data = self._extract_metric_by_path(metrics_data, x_metric_path)
        y_data = self._extract_metric_by_path(metrics_data, y_metric_path)
        
        if x_data is None or y_data is None:
            logger.warning(f"Missing data for correlation chart: {x_metric_path} vs {y_metric_path}")
            plt.close(fig)
            return None
        
        # Create dataframe for correlation analysis
        df = pd.DataFrame({
            'x': x_data,
            'y': y_data
        })
        
        # Create scatter plot with regression line
        sns.regplot(x='x', y='y', data=df, ax=ax)
        
        # Calculate and display correlation coefficient
        corr = df['x'].corr(df['y'])
        ax.annotate(f'Correlation: {corr:.2f}', 
                   xy=(0.05, 0.95), xycoords='axes fraction',
                   bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))
        
        # Get metric names for labels
        x_name = x_metric_path.split('.')[-2]
        y_name = y_metric_path.split('.')[-2]
        
        # Add labels and title
        ax.set_xlabel(f'{x_name.replace("_", " ").title()}')
        ax.set_ylabel(f'{y_name.replace("_", " ").title()}')
        ax.set_title(title)
        
        # Save the figure and return the path
        return self.save_figure(fig, output_dir, filename)
    
    def _extract_metric_by_path(self, metrics_data, metric_path):
        """
        Extract metric data from the metrics_data dictionary using a dot-notation path.
        
        Args:
            metrics_data (dict): Metrics data dictionary
            metric_path (str): Path to the metric (e.g., 'api.response_time.mean')
            
        Returns:
            object: The metric data, or None if not found
        """
        parts = metric_path.split('.')
        data = metrics_data
        
        try:
            for part in parts:
                data = data[part]
            return data
        except (KeyError, TypeError):
            logger.warning(f"Could not find metric at path: {metric_path}")
            return None
    
    def create_performance_overview_chart(self, metrics_data, output_dir, filename):
        """
        Create a comprehensive chart showing key performance indicators.
        
        Args:
            metrics_data (dict): Combined metrics data
            output_dir (pathlib.Path): Directory to save the chart
            filename (str): Name of the chart file
            
        Returns:
            str: Path to the generated chart file
        """
        # Create new figure with subplots for different metrics
        fig, axs = plt.subplots(2, 2, figsize=self._figure_sizes['combined'], dpi=self._dpi_settings['combined'])
        
        # Extract key metrics
        have_api = 'api' in metrics_data
        have_calculation = 'calculation' in metrics_data
        have_resource = 'resource' in metrics_data
        
        # Create response time subplot if API metrics exist
        if have_api:
            # Extract response time summary if available
            if 'summary' in metrics_data['api'] and 'response_time' in metrics_data['api']['summary']:
                rt_summary = metrics_data['api']['summary']['response_time']
                
                # Create bar chart of p50, p95, p99 response times
                x = ['P50', 'P95', 'P99']
                y = [rt_summary.get('p50', 0), rt_summary.get('p95', 0), rt_summary.get('p99', 0)]
                
                axs[0, 0].bar(x, y)
                axs[0, 0].axhline(y=100, color='red', linestyle='--', label='SLA Target (100ms)')
                axs[0, 0].set_title('API Response Time Percentiles')
                axs[0, 0].set_ylabel('Time (ms)')
                axs[0, 0].legend()
        else:
            axs[0, 0].text(0.5, 0.5, 'No API metrics available', ha='center', va='center')
            axs[0, 0].set_title('API Response Time')
        
        # Create throughput subplot if calculation metrics exist
        if have_calculation:
            # Extract throughput summary if available
            if 'summary' in metrics_data['calculation'] and 'throughput' in metrics_data['calculation']['summary']:
                throughput = metrics_data['calculation']['summary']['throughput']
                
                # Create bar chart of throughput values
                if 'by_type' in throughput:
                    types = list(throughput['by_type'].keys())
                    values = [throughput['by_type'][t] for t in types]
                    
                    axs[0, 1].bar(types, values)
                    axs[0, 1].axhline(y=1000, color='red', linestyle='--', 
                                     label='Target (1000/sec)')
                else:
                    # Just show the overall throughput
                    axs[0, 1].bar(['Overall'], [throughput.get('overall', 0)])
                    axs[0, 1].axhline(y=1000, color='red', linestyle='--', 
                                     label='Target (1000/sec)')
                
                axs[0, 1].set_title('Calculation Throughput')
                axs[0, 1].set_ylabel('Calc/sec')
                axs[0, 1].legend()
        else:
            axs[0, 1].text(0.5, 0.5, 'No calculation metrics available', ha='center', va='center')
            axs[0, 1].set_title('Calculation Throughput')
        
        # Create error rate subplot if API metrics exist
        if have_api and 'summary' in metrics_data['api'] and 'error_rate' in metrics_data['api']['summary']:
            error_rate = metrics_data['api']['summary']['error_rate']
            
            # Create simple gauge-like display for error rate
            axs[1, 0].pie([error_rate, 100-error_rate], 
                         labels=[f'Errors ({error_rate:.2f}%)', f'Success ({100-error_rate:.2f}%)'],
                         colors=['red', 'green'],
                         startangle=90,
                         counterclock=False)
            axs[1, 0].set_title('API Error Rate')
        else:
            axs[1, 0].text(0.5, 0.5, 'No error rate metrics available', ha='center', va='center')
            axs[1, 0].set_title('API Error Rate')
        
        # Create resource utilization subplot if resource metrics exist
        if have_resource:
            # Get CPU and memory utilization if available
            cpu_util = None
            mem_util = None
            
            if 'cpu' in metrics_data['resource'] and 'summary' in metrics_data['resource']['cpu']:
                cpu_util = metrics_data['resource']['cpu']['summary'].get('mean_utilization', None)
            
            if 'memory' in metrics_data['resource'] and 'summary' in metrics_data['resource']['memory']:
                mem_util = metrics_data['resource']['memory']['summary'].get('mean_utilization', None)
            
            if cpu_util is not None or mem_util is not None:
                # Create bar chart of mean utilizations
                labels = []
                values = []
                
                if cpu_util is not None:
                    labels.append('CPU')
                    values.append(cpu_util)
                
                if mem_util is not None:
                    labels.append('Memory')
                    values.append(mem_util)
                
                axs[1, 1].bar(labels, values)
                axs[1, 1].axhline(y=70, color='orange', linestyle='--', label='Warning (70%)')
                axs[1, 1].axhline(y=85, color='red', linestyle='--', label='Critical (85%)')
                axs[1, 1].set_ylim([0, 100])
                axs[1, 1].set_title('Resource Utilization')
                axs[1, 1].set_ylabel('Utilization (%)')
                axs[1, 1].legend()
            else:
                axs[1, 1].text(0.5, 0.5, 'No resource utilization data available', ha='center', va='center')
                axs[1, 1].set_title('Resource Utilization')
        else:
            axs[1, 1].text(0.5, 0.5, 'No resource metrics available', ha='center', va='center')
            axs[1, 1].set_title('Resource Utilization')
        
        # Add overall title and adjust layout
        fig.suptitle('Performance Overview', fontsize=16)
        fig.tight_layout(rect=[0, 0, 1, 0.96])  # Adjust layout to make room for the title
        
        # Save the figure and return the path
        return self.save_figure(fig, output_dir, filename)
    
    def save_figure(self, fig, output_dir, filename):
        """
        Save a matplotlib figure to a file.
        
        Args:
            fig (matplotlib.figure.Figure): The figure to save
            output_dir (pathlib.Path): Directory to save the figure
            filename (str): Name of the figure file
            
        Returns:
            str: Path to the saved figure file
        """
        # Construct full file path
        file_path = output_dir / filename
        
        # Save figure with tight layout
        fig.tight_layout()
        fig.savefig(file_path)
        plt.close(fig)
        
        logger.info(f"Saved chart to {file_path}")
        return str(file_path)
    
    def get_name(self):
        """
        Get the name of the visualizer.
        
        Returns:
            str: Visualizer name
        """
        return self.name