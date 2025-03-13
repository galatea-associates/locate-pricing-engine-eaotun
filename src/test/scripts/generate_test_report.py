#!/usr/bin/env python3
"""
Generate Test Report Script

This script generates comprehensive test reports from collected metrics data.
It processes test results, performance metrics, and resource utilization data
to create detailed reports in various formats (JSON, CSV) along with visualizations
and dashboards for different stakeholders.

Usage:
    python generate_test_report.py --input-path <path_to_metrics> --output-dir <output_directory>
    python generate_test_report.py --input-path <path_to_metrics> --output-dir <output_directory> --formats json,csv,html,pdf
    python generate_test_report.py --input-path <path_to_metrics> --output-dir <output_directory> --dashboard-types executive,operational,technical
"""

import argparse
import logging
import os
import sys
import json
from pathlib import Path
from datetime import datetime

from src.test.metrics.exporters.json import JSONExporter
from src.test.metrics.exporters.csv import CSVExporter
from src.test.metrics.visualizers.generate_charts import ChartGenerator
from src.test.metrics.visualizers.dashboard import DashboardGenerator
from src.test.metrics.collectors.api_metrics import APIMetricsCollector
from src.test.metrics.collectors.calculation_metrics import CalculationMetricsCollector
from src.test.metrics.collectors.resource_metrics import ResourceMetricsCollector

# Configure logger
logger = logging.getLogger(__name__)

# Default constants
DEFAULT_OUTPUT_DIR = "./reports"
DEFAULT_CONFIG = {
    'json_export': True,
    'csv_export': True,
    'charts': True,
    'dashboards': True,
    'formats': ['json', 'csv', 'html', 'pdf']
}


def setup_logging(log_level):
    """Configure logging for the report generator
    
    Args:
        log_level (int): Logging level (e.g., logging.INFO, logging.DEBUG)
        
    Returns:
        None: No return value
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=log_level, format=log_format)
    
    # Add console handler to display logs in the terminal
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    logger.addHandler(console_handler)
    logger.info("Starting test report generation")


def parse_arguments():
    """Parse command-line arguments for the report generator
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Generate comprehensive test reports from metrics data"
    )
    
    # Required arguments
    parser.add_argument(
        "--input-path", 
        required=True,
        help="Path to metrics data file(s). Can be a single JSON file or a directory containing JSON files."
    )
    
    # Optional arguments
    parser.add_argument(
        "--output-dir", 
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to save generated reports. Default: {DEFAULT_OUTPUT_DIR}"
    )
    
    parser.add_argument(
        "--formats",
        default="json,csv",
        help="Comma-separated list of report formats to generate (json,csv,html,pdf). Default: json,csv"
    )
    
    parser.add_argument(
        "--dashboard-types",
        default="executive,operational,technical",
        help="Comma-separated list of dashboard types to generate. Default: executive,operational,technical"
    )
    
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level. Default: INFO"
    )
    
    # Boolean flags for enabling/disabling specific outputs
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Disable JSON export"
    )
    
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="Disable CSV export"
    )
    
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Disable chart generation"
    )
    
    parser.add_argument(
        "--no-dashboards",
        action="store_true",
        help="Disable dashboard generation"
    )
    
    return parser.parse_args()


def load_metrics_data(input_path):
    """Load metrics data from JSON files
    
    Args:
        input_path (str): Path to JSON metrics file or directory containing JSON files
        
    Returns:
        dict: Dictionary containing loaded metrics data
    """
    path = Path(input_path)
    metrics_data = {}
    
    if path.is_file():
        # Load a single metrics file
        logger.info(f"Loading metrics from file: {path}")
        try:
            with open(path, 'r') as f:
                metrics_data = json.load(f)
                
            logger.info(f"Successfully loaded metrics from {path}")
        except Exception as e:
            logger.error(f"Error loading metrics file {path}: {str(e)}")
            sys.exit(1)
    
    elif path.is_dir():
        # Load all JSON metrics files in the directory
        logger.info(f"Loading metrics from directory: {path}")
        metrics_data = {
            'api_metrics': {},
            'calculation_metrics': {},
            'resource_metrics': {}
        }
        
        json_files = list(path.glob('*.json'))
        if not json_files:
            logger.error(f"No JSON files found in directory: {path}")
            sys.exit(1)
            
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    file_data = json.load(f)
                
                # Determine the type of metrics data and merge accordingly
                if 'api_metrics' in file_data:
                    metrics_data['api_metrics'].update(file_data['api_metrics'])
                if 'calculation_metrics' in file_data:
                    metrics_data['calculation_metrics'].update(file_data['calculation_metrics'])
                if 'resource_metrics' in file_data:
                    metrics_data['resource_metrics'].update(file_data['resource_metrics'])
                    
                logger.debug(f"Loaded metrics from {json_file}")
            except Exception as e:
                logger.warning(f"Error loading metrics file {json_file}: {str(e)}")
    
    else:
        logger.error(f"Input path does not exist: {path}")
        sys.exit(1)
    
    # Validate the structure of loaded metrics data
    if not validate_metrics_data(metrics_data):
        logger.error("Invalid metrics data structure")
        sys.exit(1)
    
    return metrics_data


def validate_metrics_data(metrics_data):
    """Validate the structure of loaded metrics data
    
    Args:
        metrics_data (dict): Dictionary containing metrics to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Check if metrics_data is a dictionary
    if not isinstance(metrics_data, dict):
        logger.error("Metrics data is not a dictionary")
        return False
    
    # Check for required sections
    if not any(k in metrics_data for k in ['api_metrics', 'calculation_metrics', 'resource_metrics']):
        logger.error("No valid metrics sections found in data")
        return False
    
    # Validate each section if present
    if 'api_metrics' in metrics_data:
        # Basic validation for API metrics structure
        if not isinstance(metrics_data['api_metrics'], dict):
            logger.error("API metrics is not a dictionary")
            return False
    
    if 'calculation_metrics' in metrics_data:
        # Basic validation for calculation metrics structure
        if not isinstance(metrics_data['calculation_metrics'], dict):
            logger.error("Calculation metrics is not a dictionary")
            return False
    
    if 'resource_metrics' in metrics_data:
        # Basic validation for resource metrics structure
        if not isinstance(metrics_data['resource_metrics'], dict):
            logger.error("Resource metrics is not a dictionary")
            return False
    
    logger.info("Metrics data structure validation successful")
    return True


def generate_report(metrics_data, output_dir, config):
    """Generate comprehensive test report from metrics data
    
    Args:
        metrics_data (dict): Dictionary containing metrics to export
        output_dir (str): Path where reports should be exported
        config (dict): Configuration dictionary for report generation
        
    Returns:
        dict: Dictionary with paths to generated report files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Generating reports in directory: {output_dir}")
    
    # Initialize results dictionary to store report file paths
    results = {
        'json_files': {},
        'csv_files': {},
        'chart_files': {},
        'dashboard_files': {},
        'pdf_file': None,
        'summary_file': None
    }
    
    # Export metrics to JSON if enabled in config
    if config.get('json_export', True):
        logger.info("Generating JSON exports")
        results['json_files'] = export_json_metrics(metrics_data, output_dir)
    
    # Export metrics to CSV if enabled in config
    if config.get('csv_export', True):
        logger.info("Generating CSV exports")
        results['csv_files'] = export_csv_metrics(metrics_data, output_dir)
    
    # Generate charts if enabled in config
    if config.get('charts', True):
        logger.info("Generating charts")
        results['chart_files'] = generate_charts(metrics_data, output_dir)
    
    # Generate dashboards if enabled in config
    if config.get('dashboards', True):
        logger.info("Generating dashboards")
        dashboard_types = config.get('dashboard_types', ['executive', 'operational', 'technical'])
        results['dashboard_files'] = generate_dashboards(metrics_data, output_dir, dashboard_types)
    
    # Generate PDF report if enabled in config
    if 'pdf' in config.get('formats', []) and config.get('charts', True):
        logger.info("Generating PDF report")
        results['pdf_file'] = generate_pdf_report(
            metrics_data, 
            output_dir, 
            results.get('chart_files', {}), 
            results.get('dashboard_files', {})
        )
    
    # Generate summary report with links to all outputs
    results['summary_file'] = generate_summary_report(results, output_dir)
    
    logger.info(f"Report generation complete")
    return results


def export_json_metrics(metrics_data, output_dir):
    """Export metrics data to JSON format
    
    Args:
        metrics_data (dict): Dictionary containing metrics to export
        output_dir (str): Path where JSON files should be exported
        
    Returns:
        dict: Dictionary with paths to exported JSON files
    """
    # Create JSONExporter instance with default configuration
    json_exporter = JSONExporter({
        'pretty_print': True,
        'timestamp_format': '%Y%m%d_%H%M%S',
        'combined_export': True
    })
    
    # Export metrics data to JSON files
    json_dir = os.path.join(output_dir, 'json')
    os.makedirs(json_dir, exist_ok=True)
    
    export_results = json_exporter.export(metrics_data, json_dir)
    
    # Log export results
    if export_results.get('status') == 'success':
        logger.info(f"Successfully exported metrics to JSON files")
        for file_type, file_path in export_results.get('file_paths', {}).items():
            logger.debug(f"Exported {file_type} to: {file_path}")
    else:
        logger.warning("JSON export may have encountered issues")
    
    return export_results.get('file_paths', {})


def export_csv_metrics(metrics_data, output_dir):
    """Export metrics data to CSV format
    
    Args:
        metrics_data (dict): Dictionary containing metrics to export
        output_dir (str): Path where CSV files should be exported
        
    Returns:
        dict: Dictionary with paths to exported CSV files
    """
    # Create CSVExporter instance with default configuration
    csv_exporter = CSVExporter({
        'timestamp_format': '%Y%m%d_%H%M%S'
    })
    
    # Export metrics data to CSV files
    csv_dir = os.path.join(output_dir, 'csv')
    os.makedirs(csv_dir, exist_ok=True)
    
    export_results = csv_exporter.export(metrics_data, csv_dir)
    
    # Log export results
    if export_results.get('file_paths'):
        logger.info(f"Successfully exported metrics to CSV files")
        for file_type, file_path in export_results.get('file_paths', {}).items():
            logger.debug(f"Exported {file_type} to: {file_path}")
    else:
        logger.warning("CSV export may have encountered issues")
    
    return export_results.get('file_paths', {})


def generate_charts(metrics_data, output_dir):
    """Generate charts and visualizations from metrics data
    
    Args:
        metrics_data (dict): Dictionary containing metrics to visualize
        output_dir (str): Path where charts should be saved
        
    Returns:
        dict: Dictionary with paths to generated chart files
    """
    # Create ChartGenerator instance with default configuration
    chart_generator = ChartGenerator({
        'figure_sizes': {
            'api': (12, 8),
            'calculation': (12, 8),
            'resource': (12, 8),
            'combined': (16, 10)
        },
        'dpi_settings': {
            'api': 100,
            'calculation': 100,
            'resource': 100,
            'combined': 100
        },
        'target_throughput': 1000,  # 1000 req/sec from requirements
        'target_error_rate': 1.0,   # 1% error rate threshold
        'calculation_target_throughput': 1000,  # 1000 calc/sec from requirements
        'resource_thresholds': {
            'cpu': {'warning': 70, 'critical': 85},
            'memory': {'warning': 70, 'critical': 85},
            'disk': {'warning': 75, 'critical': 90}
        }
    })
    
    # Generate charts from metrics data
    charts_dir = os.path.join(output_dir, 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    
    chart_results = chart_generator.visualize(metrics_data, charts_dir)
    
    # Log chart generation results
    if chart_results:
        logger.info(f"Successfully generated charts")
        for chart_type, type_charts in chart_results.items():
            for chart_name, chart_path in type_charts.items():
                if chart_path:  # Some charts might be None if data was missing
                    logger.debug(f"Generated {chart_type} chart '{chart_name}': {chart_path}")
    else:
        logger.warning("Chart generation may have encountered issues")
    
    return chart_results


def generate_dashboards(metrics_data, output_dir, dashboard_types):
    """Generate comprehensive dashboards from metrics data
    
    Args:
        metrics_data (dict): Dictionary containing metrics to visualize
        output_dir (str): Path where dashboards should be saved
        dashboard_types (list): List of dashboard types to generate
        
    Returns:
        dict: Dictionary with paths to generated dashboard files
    """
    # Create DashboardGenerator instance with configuration based on dashboard_types
    dashboard_generator = DashboardGenerator({
        'executive_dashboard': 'executive' in dashboard_types,
        'operational_dashboard': 'operational' in dashboard_types,
        'technical_dashboard': 'technical' in dashboard_types,
        'template_dir': None  # Use default template directory
    })
    
    # Generate dashboards from metrics data
    dashboards_dir = os.path.join(output_dir, 'dashboards')
    os.makedirs(dashboards_dir, exist_ok=True)
    
    dashboard_results = dashboard_generator.visualize(metrics_data, dashboards_dir)
    
    # Log dashboard generation results
    if dashboard_results:
        logger.info(f"Successfully generated dashboards")
        for dashboard_type, dashboard_path in dashboard_results.items():
            logger.debug(f"Generated {dashboard_type} dashboard: {dashboard_path}")
    else:
        logger.warning("Dashboard generation may have encountered issues")
    
    return dashboard_results


def generate_pdf_report(metrics_data, output_dir, chart_paths, dashboard_paths):
    """Generate a comprehensive PDF report from metrics data and visualizations
    
    Args:
        metrics_data (dict): Dictionary containing metrics data
        output_dir (str): Path where the PDF report should be saved
        chart_paths (dict): Dictionary with paths to generated chart files
        dashboard_paths (dict): Dictionary with paths to generated dashboard files
        
    Returns:
        str: Path to the generated PDF report
    """
    # Create report template with title, date, and summary
    pdf_dir = os.path.join(output_dir, 'pdf')
    os.makedirs(pdf_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_path = os.path.join(pdf_dir, f"test_report_{timestamp}.pdf")
    
    # Add key metrics summary section
    summary_data = {
        'api': {
            'total_requests': metrics_data.get('api_metrics', {}).get('overall', {}).get('total_requests', 0),
            'error_rate': metrics_data.get('api_metrics', {}).get('overall', {}).get('error_rate', 0),
            'avg_response_time': metrics_data.get('api_metrics', {}).get('summary', {}).get('response_time', {}).get('avg', 0)
        },
        'calculation': {
            'total_calculations': metrics_data.get('calculation_metrics', {}).get('overall', {}).get('total_calculations', 0),
            'avg_execution_time': metrics_data.get('calculation_metrics', {}).get('summary', {}).get('execution_time', {}).get('avg', 0),
            'accuracy': metrics_data.get('calculation_metrics', {}).get('summary', {}).get('accuracy', 100)
        },
        'resource': {
            'avg_cpu': metrics_data.get('resource_metrics', {}).get('overall', {}).get('cpu_avg', 0),
            'max_cpu': metrics_data.get('resource_metrics', {}).get('overall', {}).get('cpu_max', 0),
            'avg_memory': metrics_data.get('resource_metrics', {}).get('overall', {}).get('memory_avg', 0)
        }
    }
    
    # Add performance analysis section with charts
    performance_charts = []
    if chart_paths.get('api', {}).get('response_time'):
        performance_charts.append(chart_paths['api']['response_time'])
    if chart_paths.get('calculation', {}).get('execution_time'):
        performance_charts.append(chart_paths['calculation']['execution_time'])
    if chart_paths.get('combined', {}).get('overview'):
        performance_charts.append(chart_paths['combined']['overview'])
    
    # Add resource utilization section with charts
    resource_charts = []
    if chart_paths.get('resource', {}).get('cpu'):
        resource_charts.append(chart_paths['resource']['cpu'])
    if chart_paths.get('resource', {}).get('memory'):
        resource_charts.append(chart_paths['resource']['memory'])
    
    # Add conclusion and recommendations section
    
    # In a real implementation, we would use a PDF generation library like ReportLab or WeasyPrint
    # For now, create a placeholder text file with the content structure
    with open(pdf_path, 'w') as f:
        f.write(f"TEST REPORT - Generated at {datetime.now().isoformat()}\n\n")
        f.write("=================== SUMMARY ===================\n")
        f.write(f"API Requests: {summary_data['api']['total_requests']}\n")
        f.write(f"API Error Rate: {summary_data['api']['error_rate']}%\n")
        f.write(f"Average Response Time: {summary_data['api']['avg_response_time']} ms\n")
        f.write(f"Total Calculations: {summary_data['calculation']['total_calculations']}\n")
        f.write(f"Average CPU: {summary_data['resource']['avg_cpu']}%\n\n")
        
        f.write("=============== PERFORMANCE ANALYSIS ==============\n")
        f.write("Key performance metrics show the following results:\n")
        f.write(f"- API Response Time (p95): {metrics_data.get('api_metrics', {}).get('summary', {}).get('response_time', {}).get('p95', 0)} ms\n")
        f.write(f"- Calculation Execution Time (p95): {metrics_data.get('calculation_metrics', {}).get('summary', {}).get('execution_time', {}).get('p95', 0)} ms\n")
        f.write(f"- Calculation Accuracy: {summary_data['calculation']['accuracy']}%\n\n")
        f.write("Charts included:\n")
        for chart in performance_charts:
            f.write(f"- {os.path.basename(chart)}\n")
        f.write("\n")
        
        f.write("============= RESOURCE UTILIZATION ===============\n")
        f.write(f"CPU Utilization: {summary_data['resource']['avg_cpu']}% avg, {summary_data['resource']['max_cpu']}% max\n")
        f.write(f"Memory Utilization: {summary_data['resource']['avg_memory']}% avg\n")
        f.write("Charts included:\n")
        for chart in resource_charts:
            f.write(f"- {os.path.basename(chart)}\n")
        f.write("\n")
        
        f.write("=========== CONCLUSIONS & RECOMMENDATIONS ===========\n")
        f.write("Based on the test results, the system's performance is ")
        if summary_data['api']['avg_response_time'] < 100 and summary_data['resource']['max_cpu'] < 70:
            f.write("within acceptable parameters.\n")
        else:
            f.write("showing signs of stress under load.\n")
        
        f.write("\nRecommendations:\n")
        if summary_data['api']['avg_response_time'] > 100:
            f.write("- Optimize API response times to achieve <100ms target\n")
        if summary_data['resource']['max_cpu'] > 70:
            f.write("- Address CPU utilization to prevent performance degradation\n")
        if summary_data['api']['error_rate'] > 1.0:
            f.write("- Investigate API errors to reduce error rate below 1%\n")
    
    logger.info(f"Generated PDF report: {pdf_path}")
    return pdf_path


def generate_summary_report(report_paths, output_dir):
    """Generate a summary report with links to all outputs
    
    Args:
        report_paths (dict): Dictionary with paths to all generated files
        output_dir (str): Path where the summary report should be saved
        
    Returns:
        str: Path to the generated summary report
    """
    # Create HTML summary template
    summary_path = os.path.join(output_dir, "report_summary.html")
    
    with open(summary_path, 'w') as f:
        f.write("<!DOCTYPE html>\n")
        f.write("<html>\n<head>\n")
        f.write("  <title>Test Report Summary</title>\n")
        f.write("  <style>\n")
        f.write("    body { font-family: Arial, sans-serif; margin: 20px; }\n")
        f.write("    h1, h2 { color: #333; }\n")
        f.write("    .section { margin-bottom: 20px; }\n")
        f.write("    .files { margin-left: 20px; }\n")
        f.write("    a { color: #0066cc; text-decoration: none; }\n")
        f.write("    a:hover { text-decoration: underline; }\n")
        f.write("    .footer { margin-top: 30px; font-size: 12px; color: #666; }\n")
        f.write("  </style>\n")
        f.write("</head>\n<body>\n")
        
        # Header
        f.write("  <h1>Test Report Summary</h1>\n")
        f.write(f"  <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n")
        
        # Add links to all generated reports, charts, and dashboards
        # JSON files section
        if report_paths.get('json_files'):
            f.write("  <div class='section'>\n")
            f.write("    <h2>JSON Reports</h2>\n")
            f.write("    <div class='files'>\n")
            for file_type, file_path in report_paths['json_files'].items():
                rel_path = os.path.relpath(file_path, output_dir)
                f.write(f"      <p><a href='{rel_path}'>{file_type}</a></p>\n")
            f.write("    </div>\n")
            f.write("  </div>\n")
        
        # CSV files section
        if report_paths.get('csv_files'):
            f.write("  <div class='section'>\n")
            f.write("    <h2>CSV Reports</h2>\n")
            f.write("    <div class='files'>\n")
            for file_type, file_path in report_paths['csv_files'].items():
                rel_path = os.path.relpath(file_path, output_dir)
                f.write(f"      <p><a href='{rel_path}'>{file_type}</a></p>\n")
            f.write("    </div>\n")
            f.write("  </div>\n")
        
        # Charts section
        if report_paths.get('chart_files'):
            f.write("  <div class='section'>\n")
            f.write("    <h2>Charts and Visualizations</h2>\n")
            for chart_type, type_charts in report_paths['chart_files'].items():
                f.write(f"    <h3>{chart_type.capitalize()} Charts</h3>\n")
                f.write("    <div class='files'>\n")
                for chart_name, chart_path in type_charts.items():
                    if chart_path:  # Some charts might be None if they couldn't be generated
                        rel_path = os.path.relpath(chart_path, output_dir)
                        f.write(f"      <p><a href='{rel_path}'>{chart_name}</a></p>\n")
                f.write("    </div>\n")
            f.write("  </div>\n")
        
        # Dashboards section
        if report_paths.get('dashboard_files'):
            f.write("  <div class='section'>\n")
            f.write("    <h2>Dashboards</h2>\n")
            f.write("    <div class='files'>\n")
            for dashboard_type, dashboard_path in report_paths['dashboard_files'].items():
                rel_path = os.path.relpath(dashboard_path, output_dir)
                f.write(f"      <p><a href='{rel_path}'>{dashboard_type.capitalize()} Dashboard</a></p>\n")
            f.write("    </div>\n")
            f.write("  </div>\n")
        
        # PDF section
        if report_paths.get('pdf_file'):
            f.write("  <div class='section'>\n")
            f.write("    <h2>PDF Report</h2>\n")
            f.write("    <div class='files'>\n")
            rel_path = os.path.relpath(report_paths['pdf_file'], output_dir)
            f.write(f"      <p><a href='{rel_path}'>Comprehensive PDF Report</a></p>\n")
            f.write("    </div>\n")
            f.write("  </div>\n")
        
        # Add timestamp and generation information
        f.write("  <div class='footer'>\n")
        f.write("    <p>Generated by Borrow Rate & Fee Engine Test Report Generator</p>\n")
        f.write(f"    <p>Timestamp: {datetime.now().isoformat()}</p>\n")
        f.write("  </div>\n")
        
        f.write("</body>\n</html>\n")
    
    logger.info(f"Generated summary report: {summary_path}")
    return summary_path


def main():
    """Main entry point for the report generator
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    # Set up logging with specified log level
    log_level = getattr(logging, args.log_level)
    setup_logging(log_level)
    
    try:
        # Load metrics data from input path
        logger.info(f"Loading metrics data from: {args.input_path}")
        metrics_data = load_metrics_data(args.input_path)
        
        # Validate metrics data structure
        if not validate_metrics_data(metrics_data):
            logger.error("Invalid metrics data structure")
            return 1
        
        # Prepare configuration for report generation
        config = DEFAULT_CONFIG.copy()
        config['json_export'] = not args.no_json
        config['csv_export'] = not args.no_csv
        config['charts'] = not args.no_charts
        config['dashboards'] = not args.no_dashboards
        config['formats'] = [f.strip() for f in args.formats.split(',')]
        config['dashboard_types'] = [d.strip() for d in args.dashboard_types.split(',')]
        
        # Generate report with specified configuration
        logger.info(f"Generating reports in directory: {args.output_dir}")
        report_results = generate_report(metrics_data, args.output_dir, config)
        
        # Log completion message with paths to generated files
        logger.info(f"Report generation complete. Summary report: {report_results['summary_file']}")
        
        return 0  # Success
    
    except Exception as e:
        logger.error(f"Error generating reports: {str(e)}", exc_info=True)
        return 1  # Failure


if __name__ == "__main__":
    sys.exit(main())