import logging
import os
from pathlib import Path
import matplotlib
import matplotlib.gridspec as gridspec
import pandas as pd
from datetime import datetime
import jinja2

from .generate_charts import BaseVisualizer, ChartGenerator

# Configure logger
logger = logging.getLogger(__name__)

# Default dashboard settings
DEFAULT_DASHBOARD_SIZE = (16, 10)
DEFAULT_DPI = 100

# Dashboard template file names
DASHBOARD_TEMPLATES = {
    'executive': 'executive_dashboard.html.j2',
    'operational': 'operational_dashboard.html.j2',
    'technical': 'technical_dashboard.html.j2'
}

def ensure_output_directory(output_path):
    """
    Ensures that the output directory exists, creating it if necessary.
    
    Args:
        output_path (str): The path where output should be saved
        
    Returns:
        pathlib.Path: Path object representing the output directory
    """
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create dashboards subdirectory
    dashboard_dir = output_dir / 'dashboards'
    dashboard_dir.mkdir(exist_ok=True)
    
    return dashboard_dir

class DashboardGenerator(BaseVisualizer):
    """
    Generates comprehensive dashboards from collected metrics data for different user personas.
    """
    
    def __init__(self, config=None):
        """
        Initialize the dashboard generator with default configuration.
        
        Args:
            config (dict): Configuration parameters for the dashboard generator
        """
        super().__init__(config)
        self.name = 'dashboard_generator'
        self._dashboard_paths = {}  # Store paths to generated dashboards
        self._chart_generator = ChartGenerator(config)
        
        # Set up Jinja2 environment for HTML dashboard templates
        template_dir = self.config.get('template_dir', os.path.join(os.path.dirname(__file__), 'templates'))
        self._template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
    
    def visualize(self, metrics_data, output_path):
        """
        Generate dashboards from metrics data.
        
        Args:
            metrics_data (dict): Dictionary containing metrics data to visualize
            output_path (str): Path to save generated dashboards
            
        Returns:
            dict: Dictionary with paths to generated dashboard files
        """
        # Ensure output directory exists
        output_dir = ensure_output_directory(output_path)
        
        # Reset dashboard paths
        self._dashboard_paths = {}
        
        # Generate charts using the chart generator
        chart_paths = self._chart_generator.visualize(metrics_data, output_path)
        
        # Generate dashboards based on configuration
        if self.config.get('executive_dashboard', True):
            self._dashboard_paths['executive'] = self.generate_executive_dashboard(
                metrics_data, chart_paths, output_dir
            )
        
        if self.config.get('operational_dashboard', True):
            self._dashboard_paths['operational'] = self.generate_operational_dashboard(
                metrics_data, chart_paths, output_dir
            )
        
        if self.config.get('technical_dashboard', True):
            self._dashboard_paths['technical'] = self.generate_technical_dashboard(
                metrics_data, chart_paths, output_dir
            )
        
        return self._dashboard_paths
    
    def generate_executive_dashboard(self, metrics_data, chart_paths, output_dir):
        """
        Generate an executive dashboard with high-level metrics.
        
        Args:
            metrics_data (dict): Metrics data dictionary
            chart_paths (dict): Paths to generated charts
            output_dir (pathlib.Path): Directory to save the dashboard
            
        Returns:
            str: Path to the generated executive dashboard file
        """
        logger.info("Generating executive dashboard")
        
        # Create system health panel
        system_health = self.create_system_health_panel(metrics_data)
        
        # Create business metrics panel
        business_metrics = self.create_business_metrics_panel(metrics_data)
        
        # Create SLA metrics panel
        sla_metrics = self.create_sla_metrics_panel(metrics_data)
        
        # Create recent incidents summary (if available)
        incidents = {
            'open_incidents': 0,
            'recent_resolutions': 0,
            'mttr': '0 minutes'
        }
        
        if 'incidents' in metrics_data:
            incidents_data = metrics_data['incidents']
            incidents = {
                'open_incidents': incidents_data.get('open_count', 0),
                'recent_resolutions': incidents_data.get('recent_resolutions', 0),
                'mttr': incidents_data.get('mttr', '0 minutes')
            }
        
        # Prepare context data for the template
        context = {
            'title': 'Executive Dashboard - Borrow Rate & Fee Engine',
            'system_health': system_health,
            'business_metrics': business_metrics,
            'sla_metrics': sla_metrics,
            'incidents': incidents,
            'charts': {}
        }
        
        # Add relevant charts from chart_paths
        if 'combined' in chart_paths and 'overview' in chart_paths['combined']:
            context['charts']['overview'] = os.path.basename(chart_paths['combined']['overview'])
        
        # Render template
        html_content = self.render_dashboard_template('executive', context)
        
        # Save dashboard
        return self.save_dashboard(html_content, output_dir, 'executive_dashboard.html')
    
    def generate_operational_dashboard(self, metrics_data, chart_paths, output_dir):
        """
        Generate an operational dashboard with detailed performance metrics.
        
        Args:
            metrics_data (dict): Metrics data dictionary
            chart_paths (dict): Paths to generated charts
            output_dir (pathlib.Path): Directory to save the dashboard
            
        Returns:
            str: Path to the generated operational dashboard file
        """
        logger.info("Generating operational dashboard")
        
        # Create traffic metrics panel
        traffic_metrics = self.create_traffic_metrics_panel(metrics_data)
        
        # Create error analysis panel
        error_analysis = self.create_error_analysis_panel(metrics_data)
        
        # Create resource metrics panel
        resource_metrics = self.create_resource_metrics_panel(metrics_data)
        
        # Create external dependencies panel
        dependencies = {
            'seclend_api': {
                'status': 'Available' if metrics_data.get('external', {}).get('seclend_api', {}).get('available', False) else 'Unavailable',
                'latency': metrics_data.get('external', {}).get('seclend_api', {}).get('latency', 'N/A')
            },
            'market_data_api': {
                'status': 'Available' if metrics_data.get('external', {}).get('market_data_api', {}).get('available', False) else 'Unavailable',
                'latency': metrics_data.get('external', {}).get('market_data_api', {}).get('latency', 'N/A')
            },
            'event_calendar_api': {
                'status': 'Available' if metrics_data.get('external', {}).get('event_calendar_api', {}).get('available', False) else 'Unavailable',
                'latency': metrics_data.get('external', {}).get('event_calendar_api', {}).get('latency', 'N/A')
            }
        }
        
        # Prepare context data for the template
        context = {
            'title': 'Operational Dashboard - Borrow Rate & Fee Engine',
            'traffic_metrics': traffic_metrics,
            'error_analysis': error_analysis,
            'resource_metrics': resource_metrics,
            'dependencies': dependencies,
            'charts': {}
        }
        
        # Add relevant charts from chart_paths
        if 'api' in chart_paths:
            if 'request_rate' in chart_paths['api']:
                context['charts']['request_rate'] = os.path.basename(chart_paths['api']['request_rate'])
            if 'error_rate' in chart_paths['api']:
                context['charts']['error_rate'] = os.path.basename(chart_paths['api']['error_rate'])
                
        if 'resource' in chart_paths:
            if 'cpu' in chart_paths['resource']:
                context['charts']['cpu_utilization'] = os.path.basename(chart_paths['resource']['cpu'])
            if 'memory' in chart_paths['resource']:
                context['charts']['memory_utilization'] = os.path.basename(chart_paths['resource']['memory'])
        
        # Render template
        html_content = self.render_dashboard_template('operational', context)
        
        # Save dashboard
        return self.save_dashboard(html_content, output_dir, 'operational_dashboard.html')
    
    def generate_technical_dashboard(self, metrics_data, chart_paths, output_dir):
        """
        Generate a technical dashboard with detailed system performance metrics.
        
        Args:
            metrics_data (dict): Metrics data dictionary
            chart_paths (dict): Paths to generated charts
            output_dir (pathlib.Path): Directory to save the dashboard
            
        Returns:
            str: Path to the generated technical dashboard file
        """
        logger.info("Generating technical dashboard")
        
        # Create service performance panel
        service_performance = self.create_service_performance_panel(metrics_data)
        
        # Create database insights panel
        database_insights = self.create_database_insights_panel(metrics_data)
        
        # Create cache analytics panel
        cache_analytics = self.create_cache_analytics_panel(metrics_data)
        
        # Create API gateway metrics panel
        gateway_metrics = {
            'request_volume_by_client': {},
            'authentication_success_rate': metrics_data.get('api', {}).get('auth', {}).get('success_rate', 'N/A'),
            'rate_limiting_events': metrics_data.get('api', {}).get('rate_limit', {}).get('events_count', 0),
            'response_code_distribution': metrics_data.get('api', {}).get('response_codes', {})
        }
        
        if 'api' in metrics_data and 'clients' in metrics_data['api']:
            gateway_metrics['request_volume_by_client'] = metrics_data['api']['clients']
        
        # Prepare context data for the template
        context = {
            'title': 'Technical Dashboard - Borrow Rate & Fee Engine',
            'service_performance': service_performance,
            'database_insights': database_insights,
            'cache_analytics': cache_analytics,
            'gateway_metrics': gateway_metrics,
            'charts': {}
        }
        
        # Add relevant charts from chart_paths
        if 'calculation' in chart_paths:
            if 'execution_time' in chart_paths['calculation']:
                context['charts']['execution_time'] = os.path.basename(chart_paths['calculation']['execution_time'])
            if 'throughput' in chart_paths['calculation']:
                context['charts']['throughput'] = os.path.basename(chart_paths['calculation']['throughput'])
            if 'accuracy' in chart_paths['calculation']:
                context['charts']['accuracy'] = os.path.basename(chart_paths['calculation']['accuracy'])
        
        if 'api' in chart_paths and 'response_time' in chart_paths['api']:
            context['charts']['response_time'] = os.path.basename(chart_paths['api']['response_time'])
        
        if 'combined' in chart_paths:
            if 'api_resource_correlation' in chart_paths['combined']:
                context['charts']['correlation'] = os.path.basename(chart_paths['combined']['api_resource_correlation'])
        
        # Render template
        html_content = self.render_dashboard_template('technical', context)
        
        # Save dashboard
        return self.save_dashboard(html_content, output_dir, 'technical_dashboard.html')
    
    def create_system_health_panel(self, metrics_data):
        """
        Create a system health status panel for the executive dashboard.
        
        Args:
            metrics_data (dict): Metrics data dictionary
            
        Returns:
            dict: Dictionary with system health metrics and status indicators
        """
        # Default values
        overall_status = 'Green'
        component_status = {}
        availability_trend = []
        
        # Extract API error rate if available
        api_error_rate = metrics_data.get('api', {}).get('summary', {}).get('error_rate', 0)
        
        # Extract resource utilization if available
        cpu_utilization = metrics_data.get('resource', {}).get('cpu', {}).get('summary', {}).get('max_utilization', 0)
        memory_utilization = metrics_data.get('resource', {}).get('memory', {}).get('summary', {}).get('max_utilization', 0)
        
        # Extract response time if available
        response_time_p95 = metrics_data.get('api', {}).get('summary', {}).get('response_time', {}).get('p95', 0)
        
        # Determine overall status based on metrics
        if api_error_rate > 1.0 or cpu_utilization > 85 or memory_utilization > 85 or response_time_p95 > 250:
            overall_status = 'Red'
        elif api_error_rate > 0.1 or cpu_utilization > 70 or memory_utilization > 70 or response_time_p95 > 100:
            overall_status = 'Yellow'
        
        # Determine component status
        component_status = {
            'API Gateway': 'Green' if api_error_rate <= 0.1 and response_time_p95 <= 100 else 
                         ('Yellow' if api_error_rate <= 1.0 and response_time_p95 <= 250 else 'Red'),
            'Calculation Service': 'Green',  # Default to green if no specific metrics
            'Data Service': 'Green',  # Default to green if no specific metrics
            'Database': 'Green',  # Default to green if no specific metrics
            'Cache': 'Green'  # Default to green if no specific metrics
        }
        
        # Extract specific component statuses if available
        if 'components' in metrics_data:
            for component, status in metrics_data['components'].items():
                if component in component_status:
                    component_status[component] = status
        
        # Generate availability trend for the last 7 days
        # Use mock data if not available
        if 'availability' in metrics_data and 'daily' in metrics_data['availability']:
            availability_trend = metrics_data['availability']['daily']
        else:
            # Generate mock data for the last 7 days (99.9% - 100%)
            availability_trend = [99.9 + (i * 0.02) for i in range(7)]
            if len(availability_trend) > 7:
                availability_trend = availability_trend[-7:]
        
        # Build system health panel data
        return {
            'overall_status': overall_status,
            'component_status': component_status,
            'availability_trend': availability_trend
        }
    
    def create_business_metrics_panel(self, metrics_data):
        """
        Create a business metrics panel for the executive dashboard.
        
        Args:
            metrics_data (dict): Metrics data dictionary
            
        Returns:
            dict: Dictionary with business metrics
        """
        # Default values
        daily_calculation_volume = 0
        average_fee_amount = 0.0
        top_client_usage = {}
        revenue_impact = 0.0
        
        # Extract daily calculation volume if available
        if 'business' in metrics_data and 'volume' in metrics_data['business']:
            daily_calculation_volume = metrics_data['business']['volume'].get('daily', 0)
        
        # Extract average fee amount if available
        if 'business' in metrics_data and 'fees' in metrics_data['business']:
            average_fee_amount = metrics_data['business']['fees'].get('average', 0.0)
        
        # Extract top client usage if available
        if 'business' in metrics_data and 'clients' in metrics_data['business']:
            top_client_usage = metrics_data['business']['clients']
            # Limit to top 5 clients if more are available
            if len(top_client_usage) > 5:
                top_client_usage = dict(sorted(top_client_usage.items(), 
                                              key=lambda x: x[1], 
                                              reverse=True)[:5])
        
        # Calculate estimated revenue impact
        if 'business' in metrics_data and 'revenue' in metrics_data['business']:
            revenue_impact = metrics_data['business']['revenue'].get('impact', 0.0)
        else:
            # Estimate based on average fee and volume if available
            revenue_impact = average_fee_amount * daily_calculation_volume
        
        # Build business metrics panel data
        return {
            'daily_calculation_volume': daily_calculation_volume,
            'average_fee_amount': average_fee_amount,
            'top_client_usage': top_client_usage,
            'revenue_impact': revenue_impact
        }
    
    def create_sla_metrics_panel(self, metrics_data):
        """
        Create an SLA metrics panel for the executive dashboard.
        
        Args:
            metrics_data (dict): Metrics data dictionary
            
        Returns:
            dict: Dictionary with SLA metrics
        """
        # Default values
        availability = 99.95  # Target availability from requirements
        response_time = 85    # Target p95 response time
        calculation_accuracy = 100.0  # Target calculation accuracy
        
        # Extract availability from metrics if available
        if 'sla' in metrics_data and 'availability' in metrics_data['sla']:
            availability = metrics_data['sla']['availability']
        elif 'availability' in metrics_data:
            # Use the most recent availability value if available
            if 'current' in metrics_data['availability']:
                availability = metrics_data['availability']['current']
            elif 'daily' in metrics_data['availability'] and len(metrics_data['availability']['daily']) > 0:
                availability = metrics_data['availability']['daily'][-1]
        
        # Extract response time from metrics if available
        if 'sla' in metrics_data and 'response_time' in metrics_data['sla']:
            response_time = metrics_data['sla']['response_time']
        elif 'api' in metrics_data and 'summary' in metrics_data['api']:
            if 'response_time' in metrics_data['api']['summary']:
                response_time = metrics_data['api']['summary']['response_time'].get('p95', response_time)
        
        # Extract calculation accuracy from metrics if available
        if 'sla' in metrics_data and 'calculation_accuracy' in metrics_data['sla']:
            calculation_accuracy = metrics_data['sla']['calculation_accuracy']
        elif 'calculation' in metrics_data and 'summary' in metrics_data['calculation']:
            if 'accuracy' in metrics_data['calculation']['summary']:
                calculation_accuracy = metrics_data['calculation']['summary']['accuracy']
        
        # Build SLA metrics panel data
        return {
            'availability': availability,
            'response_time': response_time,
            'calculation_accuracy': calculation_accuracy
        }
    
    def create_traffic_metrics_panel(self, metrics_data):
        """
        Create a traffic metrics panel for the operational dashboard.
        
        Args:
            metrics_data (dict): Metrics data dictionary
            
        Returns:
            dict: Dictionary with traffic metrics
        """
        # Default values
        requests_per_second = 0
        response_time_distribution = {}
        endpoint_usage = {}
        
        # Extract requests per second if available
        if 'api' in metrics_data and 'summary' in metrics_data['api']:
            requests_per_second = metrics_data['api']['summary'].get('request_rate', {}).get('mean', 0)
        
        # Extract response time distribution if available
        if 'api' in metrics_data and 'percentiles' in metrics_data['api']:
            response_time_distribution = metrics_data['api']['percentiles']
        
        # Extract endpoint usage breakdown if available
        if 'api' in metrics_data and 'endpoints' in metrics_data['api']:
            endpoint_usage = metrics_data['api']['endpoints']
        
        # Build traffic metrics panel data
        return {
            'requests_per_second': requests_per_second,
            'response_time_distribution': response_time_distribution,
            'endpoint_usage': endpoint_usage
        }
    
    def create_error_analysis_panel(self, metrics_data):
        """
        Create an error analysis panel for the operational dashboard.
        
        Args:
            metrics_data (dict): Metrics data dictionary
            
        Returns:
            dict: Dictionary with error analysis metrics
        """
        # Default values
        error_rate_by_endpoint = {}
        top_error_types = {}
        client_error_distribution = {}
        
        # Extract error rate by endpoint if available
        if 'api' in metrics_data and 'error_rates' in metrics_data['api']:
            error_rate_by_endpoint = metrics_data['api']['error_rates']
        
        # Extract top error types if available
        if 'api' in metrics_data and 'errors' in metrics_data['api'] and 'types' in metrics_data['api']['errors']:
            top_error_types = metrics_data['api']['errors']['types']
        
        # Extract client error distribution if available
        if 'api' in metrics_data and 'errors' in metrics_data['api'] and 'by_client' in metrics_data['api']['errors']:
            client_error_distribution = metrics_data['api']['errors']['by_client']
        
        # Build error analysis panel data
        return {
            'error_rate_by_endpoint': error_rate_by_endpoint,
            'top_error_types': top_error_types,
            'client_error_distribution': client_error_distribution
        }
    
    def create_resource_metrics_panel(self, metrics_data):
        """
        Create a resource metrics panel for the operational dashboard.
        
        Args:
            metrics_data (dict): Metrics data dictionary
            
        Returns:
            dict: Dictionary with resource metrics
        """
        # Default values
        cpu_memory_by_service = {}
        database_connections = {}
        cache_hit_miss_ratio = {}
        
        # Extract CPU/Memory by service if available
        if 'resource' in metrics_data and 'by_service' in metrics_data['resource']:
            cpu_memory_by_service = metrics_data['resource']['by_service']
        
        # Extract database connection metrics if available
        if 'database' in metrics_data and 'connections' in metrics_data['database']:
            database_connections = metrics_data['database']['connections']
        
        # Extract cache hit/miss ratio if available
        if 'cache' in metrics_data and 'hit_miss' in metrics_data['cache']:
            cache_hit_miss_ratio = metrics_data['cache']['hit_miss']
        
        # Build resource metrics panel data
        return {
            'cpu_memory_by_service': cpu_memory_by_service,
            'database_connections': database_connections,
            'cache_hit_miss_ratio': cache_hit_miss_ratio
        }
    
    def create_service_performance_panel(self, metrics_data):
        """
        Create a service performance panel for the technical dashboard.
        
        Args:
            metrics_data (dict): Metrics data dictionary
            
        Returns:
            dict: Dictionary with service performance metrics
        """
        # Default values
        calculation_service_latency = {}
        data_service_api_calls = {}
        service_error_rates = {}
        service_instance_count = {}
        
        # Extract calculation service latency if available
        if 'services' in metrics_data and 'calculation' in metrics_data['services']:
            calculation_service_latency = metrics_data['services']['calculation'].get('latency', {})
        
        # Extract data service API calls if available
        if 'services' in metrics_data and 'data' in metrics_data['services']:
            data_service_api_calls = metrics_data['services']['data'].get('api_calls', {})
        
        # Extract service error rates if available
        if 'services' in metrics_data and 'error_rates' in metrics_data['services']:
            service_error_rates = metrics_data['services']['error_rates']
        
        # Extract service instance count if available
        if 'services' in metrics_data and 'instances' in metrics_data['services']:
            service_instance_count = metrics_data['services']['instances']
        
        # Build service performance panel data
        return {
            'calculation_service_latency': calculation_service_latency,
            'data_service_api_calls': data_service_api_calls,
            'service_error_rates': service_error_rates,
            'service_instance_count': service_instance_count
        }
    
    def create_database_insights_panel(self, metrics_data):
        """
        Create a database insights panel for the technical dashboard.
        
        Args:
            metrics_data (dict): Metrics data dictionary
            
        Returns:
            dict: Dictionary with database insights metrics
        """
        # Default values
        query_performance = {}
        connection_pool_status = {}
        transaction_volume = 0
        slow_query_analysis = {}
        
        # Extract query performance metrics if available
        if 'database' in metrics_data and 'query_performance' in metrics_data['database']:
            query_performance = metrics_data['database']['query_performance']
        
        # Extract connection pool status if available
        if 'database' in metrics_data and 'connection_pool' in metrics_data['database']:
            connection_pool_status = metrics_data['database']['connection_pool']
        
        # Extract transaction volume if available
        if 'database' in metrics_data and 'transactions' in metrics_data['database']:
            transaction_volume = metrics_data['database']['transactions'].get('volume', 0)
        
        # Extract slow query analysis if available
        if 'database' in metrics_data and 'slow_queries' in metrics_data['database']:
            slow_query_analysis = metrics_data['database']['slow_queries']
        
        # Build database insights panel data
        return {
            'query_performance': query_performance,
            'connection_pool_status': connection_pool_status,
            'transaction_volume': transaction_volume,
            'slow_query_analysis': slow_query_analysis
        }
    
    def create_cache_analytics_panel(self, metrics_data):
        """
        Create a cache analytics panel for the technical dashboard.
        
        Args:
            metrics_data (dict): Metrics data dictionary
            
        Returns:
            dict: Dictionary with cache analytics metrics
        """
        # Default values
        hit_rate_by_key_pattern = {}
        memory_usage = {}
        eviction_rate = 0
        key_expiration_analysis = {}
        
        # Extract hit rate by key pattern if available
        if 'cache' in metrics_data and 'hit_rate' in metrics_data['cache']:
            hit_rate_by_key_pattern = metrics_data['cache']['hit_rate']
        
        # Extract memory usage if available
        if 'cache' in metrics_data and 'memory' in metrics_data['cache']:
            memory_usage = metrics_data['cache']['memory']
        
        # Extract eviction rate if available
        if 'cache' in metrics_data and 'evictions' in metrics_data['cache']:
            eviction_rate = metrics_data['cache']['evictions'].get('rate', 0)
        
        # Extract key expiration analysis if available
        if 'cache' in metrics_data and 'expirations' in metrics_data['cache']:
            key_expiration_analysis = metrics_data['cache']['expirations']
        
        # Build cache analytics panel data
        return {
            'hit_rate_by_key_pattern': hit_rate_by_key_pattern,
            'memory_usage': memory_usage,
            'eviction_rate': eviction_rate,
            'key_expiration_analysis': key_expiration_analysis
        }
    
    def render_dashboard_template(self, template_name, context_data):
        """
        Render a dashboard template with metrics data and chart paths.
        
        Args:
            template_name (str): Name of the template to render
            context_data (dict): Context data for the template
            
        Returns:
            str: Rendered HTML dashboard content
        """
        # Get template file name from the DASHBOARD_TEMPLATES dictionary
        template_file = DASHBOARD_TEMPLATES.get(template_name)
        if not template_file:
            logger.warning(f"No template found for dashboard type: {template_name}")
            template_file = 'default_dashboard.html.j2'
        
        # Get the template
        template = self._template_env.get_template(template_file)
        
        # Add timestamp and dashboard generator version
        context_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        context_data['generator_version'] = '1.0.0'
        
        # Render the template
        return template.render(**context_data)
    
    def save_dashboard(self, html_content, output_dir, filename):
        """
        Save a rendered dashboard to an HTML file.
        
        Args:
            html_content (str): Rendered HTML dashboard content
            output_dir (pathlib.Path): Directory to save the dashboard
            filename (str): Name of the dashboard file
            
        Returns:
            str: Path to the saved dashboard file
        """
        # Construct full file path
        file_path = output_dir / filename
        
        # Write HTML content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Saved dashboard to {file_path}")
        return str(file_path)
    
    def get_name(self):
        """
        Get the name of the visualizer.
        
        Returns:
            str: Visualizer name
        """
        return self.name