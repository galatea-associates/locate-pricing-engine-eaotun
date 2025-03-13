"""
Performance Test Reporting Module for the Borrow Rate & Locate Fee Pricing Engine.

This module implements comprehensive performance test reporting functionality, 
generating detailed reports in various formats (HTML, PDF, JSON, CSV) from 
collected metrics data, including visualizations, analysis results, and SLA compliance information.
"""

import logging
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

import jinja2  # jinja2 3.1.0+
from weasyprint import HTML  # weasyprint 59.0+

from src.test.performance_tests.config.settings import get_test_settings
from src.test.performance_tests.helpers.analysis import analyze_performance_results, PerformanceAnalyzer
from src.test.metrics.visualizers.generate_charts import ChartGenerator
from src.test.metrics.exporters.json import JSONExporter
from src.test.metrics.exporters.csv import CSVExporter

# Configure logger
logger = logging.getLogger(__name__)

# Default report configuration
DEFAULT_REPORT_CONFIG = {
    "formats": ["html", "pdf", "json", "csv"],
    "include_charts": True,
    "include_analysis": True,
    "include_sla_status": True,
    "include_recommendations": True
}

# Default output directory
DEFAULT_OUTPUT_DIR = Path("./reports")

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "reports"


def generate_report(metrics_data: Dict, output_path: str = None, 
                    formats: List = None, include_charts: bool = None,
                    test_info: Dict = None) -> Dict:
    """
    Generate performance test reports in various formats from collected metrics data.
    
    Args:
        metrics_data: Dictionary with performance metrics data
        output_path: Path to store generated reports
        formats: List of output formats (html, pdf, json, csv)
        include_charts: Whether to include charts in the reports
        test_info: Additional information about the test run
        
    Returns:
        Dictionary with paths to generated report files
    """
    # Validate input metrics_data
    if not metrics_data:
        logger.error("Empty metrics data provided for report generation")
        return {"error": "No metrics data provided"}
    
    # Set default formats if not provided
    if formats is None:
        formats = DEFAULT_REPORT_CONFIG["formats"]
    
    # Set default include_charts if not provided
    if include_charts is None:
        include_charts = DEFAULT_REPORT_CONFIG["include_charts"]
    
    # Create configuration dictionary
    config = {
        "formats": formats,
        "include_charts": include_charts,
        "include_analysis": DEFAULT_REPORT_CONFIG["include_analysis"],
        "include_sla_status": DEFAULT_REPORT_CONFIG["include_sla_status"],
        "include_recommendations": DEFAULT_REPORT_CONFIG["include_recommendations"]
    }
    
    # Create the reporter instance
    reporter = PerformanceReporter(config, test_info or {})
    
    # Generate the report
    return reporter.generate_report(metrics_data, output_path or str(DEFAULT_OUTPUT_DIR))


def generate_charts_for_report(metrics_data: Dict, output_path: str) -> Dict:
    """
    Generate charts for performance test reports.
    
    Args:
        metrics_data: Dictionary with performance metrics data
        output_path: Path to store generated charts
        
    Returns:
        Dictionary with paths to generated chart files
    """
    # Create chart generator with default configuration
    chart_generator = ChartGenerator()
    
    # Generate charts
    return chart_generator.visualize(metrics_data, output_path)


def ensure_output_directory(output_path: str) -> Path:
    """
    Ensure the output directory exists, creating it if necessary.
    
    Args:
        output_path: Path to the output directory
        
    Returns:
        Path object for the output directory
    """
    path = Path(output_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_timestamp(timestamp: datetime) -> str:
    """
    Format a timestamp for use in report filenames.
    
    Args:
        timestamp: Datetime object to format
        
    Returns:
        Formatted timestamp string
    """
    return timestamp.strftime("%Y%m%d_%H%M%S")


class ReportExporter:
    """
    Base class for report exporters that can be added to the PerformanceReporter.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the ReportExporter with configuration.
        
        Args:
            config: Configuration dictionary for the exporter
        """
        self.name = "base_exporter"
        self.config = config or {}
    
    def export(self, report_data: Dict, output_path: str) -> Dict:
        """
        Export report in the specific format (to be implemented by subclasses).
        
        Args:
            report_data: Dictionary containing report data
            output_path: Path where the report should be exported
            
        Returns:
            Export results with file paths and status
        """
        raise NotImplementedError("Export method must be implemented by subclasses")


class PerformanceReporter:
    """
    Main class for generating comprehensive performance test reports in various formats.
    """
    
    def __init__(self, config: Dict = None, test_info: Dict = None):
        """
        Initialize the PerformanceReporter with configuration.
        
        Args:
            config: Configuration dictionary for the reporter
            test_info: Additional information about the test run
        """
        # Store configuration or use default
        self.config = config or DEFAULT_REPORT_CONFIG.copy()
        
        # Store test information
        self.test_info = test_info or {}
        
        # Initialize report paths
        self.report_paths = {}
        
        # Initialize exporters
        self.exporters = [
            JSONExporter({"pretty_print": True}),
            CSVExporter()
        ]
        
        # Initialize chart generator
        self.chart_generator = ChartGenerator(config.get("chart_config", {}))
        
        # Initialize analyzer with thresholds from test settings
        test_settings = get_test_settings()
        self.analyzer = PerformanceAnalyzer({
            "response_time": test_settings.get_response_time_threshold(),
            "throughput": test_settings.get_throughput_threshold(),
            "error_rate": test_settings.get_error_rate_threshold(),
            "calculation_accuracy": 100  # Always require 100% accuracy for calculations
        })
        
        # Initialize Jinja2 template environment
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def generate_report(self, metrics_data: Dict, output_path: str) -> Dict:
        """
        Generate performance test reports in all configured formats.
        
        Args:
            metrics_data: Dictionary with performance metrics data
            output_path: Path to store generated reports
            
        Returns:
            Dictionary with paths to generated report files
        """
        # Ensure output directory exists
        output_dir = ensure_output_directory(output_path)
        
        # Reset report paths
        self.report_paths = {}
        
        # Generate timestamp for report filenames
        timestamp = format_timestamp(datetime.now())
        
        # Analyze metrics data
        analysis_results = self.analyzer.analyze(metrics_data)
        
        # Generate charts if configured
        chart_paths = {}
        if self.config.get("include_charts", True):
            chart_paths = self.generate_charts(metrics_data, output_dir)
        
        # Generate reports in configured formats
        if "html" in self.config.get("formats", []):
            html_path = self.generate_html_report(
                metrics_data, analysis_results, chart_paths, output_dir, timestamp
            )
            self.report_paths["html"] = html_path
            
            # Generate PDF from HTML if configured
            if "pdf" in self.config.get("formats", []):
                pdf_path = self.generate_pdf_report(html_path, output_dir, timestamp)
                self.report_paths["pdf"] = pdf_path
        
        # Generate text report if configured
        if "text" in self.config.get("formats", []):
            text_path = self.generate_text_report(
                metrics_data, analysis_results, output_dir, timestamp
            )
            self.report_paths["text"] = text_path
        
        # Export metrics using exporters if configured
        if any(fmt in self.config.get("formats", []) for fmt in ["json", "csv"]):
            export_paths = self.export_metrics(metrics_data, output_dir)
            self.report_paths.update(export_paths)
        
        return self.report_paths
    
    def generate_html_report(self, metrics_data: Dict, analysis_results: Dict, 
                           chart_paths: Dict, output_dir: Path, timestamp: str) -> str:
        """
        Generate an HTML report from metrics data and analysis results.
        
        Args:
            metrics_data: Dictionary with performance metrics data
            analysis_results: Dictionary with analysis results
            chart_paths: Dictionary with paths to generated charts
            output_dir: Path to the output directory
            timestamp: Timestamp string for file naming
            
        Returns:
            Path to the generated HTML report
        """
        # Load HTML report template
        template = self.template_env.get_template("performance_report.html")
        
        # Get SLA status if configured
        sla_status = None
        if self.config.get("include_sla_status", True):
            sla_status = self.get_sla_status(analysis_results)
        
        # Generate recommendations if configured
        recommendations = None
        if self.config.get("include_recommendations", True):
            recommendations = self.generate_recommendations(analysis_results)
        
        # Prepare template context
        context = {
            "title": "Performance Test Report",
            "timestamp": datetime.now().isoformat(),
            "formatted_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": metrics_data,
            "analysis": analysis_results,
            "charts": chart_paths,
            "test_info": self.test_info,
            "sla_status": sla_status,
            "recommendations": recommendations,
            "config": self.config
        }
        
        # Render template
        html_content = template.render(**context)
        
        # Write HTML to file
        file_path = output_dir / f"performance_report_{timestamp}.html"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"Generated HTML report: {file_path}")
        return str(file_path)
    
    def generate_pdf_report(self, html_report_path: str, output_dir: Path, timestamp: str) -> str:
        """
        Generate a PDF report from the HTML report.
        
        Args:
            html_report_path: Path to the HTML report
            output_dir: Path to the output directory
            timestamp: Timestamp string for file naming
            
        Returns:
            Path to the generated PDF report
        """
        try:
            # Read HTML content
            with open(html_report_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # Create PDF file path
            pdf_path = output_dir / f"performance_report_{timestamp}.pdf"
            
            # Generate PDF from HTML
            HTML(string=html_content, base_url=str(output_dir)).write_pdf(pdf_path)
            
            logger.info(f"Generated PDF report: {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {str(e)}")
            return None
    
    def generate_text_report(self, metrics_data: Dict, analysis_results: Dict, 
                           output_dir: Path, timestamp: str) -> str:
        """
        Generate a plain text report with key metrics and analysis results.
        
        Args:
            metrics_data: Dictionary with performance metrics data
            analysis_results: Dictionary with analysis results
            output_dir: Path to the output directory
            timestamp: Timestamp string for file naming
            
        Returns:
            Path to the generated text report
        """
        # Create text file path
        text_path = output_dir / f"performance_report_{timestamp}.txt"
        
        # Format metrics and analysis as text
        metrics_text = self.format_metrics_for_text(metrics_data)
        analysis_text = self.format_analysis_for_text(analysis_results)
        
        # Get SLA status if configured
        sla_text = ""
        if self.config.get("include_sla_status", True):
            sla_status = self.get_sla_status(analysis_results)
            sla_text = "\n\nSLA STATUS\n==========\n"
            sla_text += f"Overall SLA Status: {sla_status['overall_status']}\n\n"
            for metric, status in sla_status.items():
                if metric != "overall_status":
                    sla_text += f"{metric}: {status['status']} (value: {status['value']}, target: {status['target']})\n"
        
        # Generate recommendations if configured
        recommendations_text = ""
        if self.config.get("include_recommendations", True):
            recommendations = self.generate_recommendations(analysis_results)
            if recommendations:
                recommendations_text = "\n\nRECOMMENDATIONS\n===============\n"
                for i, rec in enumerate(recommendations, 1):
                    recommendations_text += f"{i}. {rec}\n"
        
        # Combine all text
        report_text = (
            f"PERFORMANCE TEST REPORT\n"
            f"=======================\n"
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"{metrics_text}\n\n"
            f"{analysis_text}"
            f"{sla_text}"
            f"{recommendations_text}"
        )
        
        # Write to file
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        
        logger.info(f"Generated text report: {text_path}")
        return str(text_path)
    
    def export_metrics(self, metrics_data: Dict, output_dir: Path) -> Dict:
        """
        Export metrics using configured exporters.
        
        Args:
            metrics_data: Dictionary with performance metrics data
            output_dir: Path to the output directory
            
        Returns:
            Dictionary with paths to exported files
        """
        export_results = {}
        
        # Organize metrics into categories for exporters
        export_data = {
            "api_metrics": metrics_data.get("api", {}),
            "calculation_metrics": metrics_data.get("calculation", {}),
            "resource_metrics": metrics_data.get("resources", {})
        }
        
        # Use each exporter to export metrics
        for exporter in self.exporters:
            # Skip exporters whose formats are not requested
            if exporter.name == "json" and "json" not in self.config.get("formats", []):
                continue
            if exporter.name == "csv" and "csv" not in self.config.get("formats", []):
                continue
                
            try:
                # Export metrics
                exporter_results = exporter.export(export_data, str(output_dir))
                
                # Add results to export_results
                if hasattr(exporter_results, "get") and exporter_results.get("file_paths"):
                    for format_name, file_path in exporter_results["file_paths"].items():
                        export_results[f"{exporter.name}_{format_name}"] = file_path
                
                logger.info(f"Exported metrics using {exporter.name} exporter")
            except Exception as e:
                logger.error(f"Error exporting metrics with {exporter.name}: {str(e)}")
        
        return export_results
    
    def generate_charts(self, metrics_data: Dict, output_dir: Path) -> Dict:
        """
        Generate charts for the report.
        
        Args:
            metrics_data: Dictionary with performance metrics data
            output_dir: Path to the output directory
            
        Returns:
            Dictionary with paths to generated chart files
        """
        # Create charts directory if it doesn't exist
        charts_dir = output_dir / "charts"
        charts_dir.mkdir(exist_ok=True)
        
        # Generate charts
        try:
            chart_paths = self.chart_generator.visualize(metrics_data, str(charts_dir))
            logger.info(f"Generated {len(chart_paths)} charts for report")
            return chart_paths
        except Exception as e:
            logger.error(f"Error generating charts: {str(e)}")
            return {}
    
    def add_exporter(self, exporter) -> None:
        """
        Add a new exporter to the reporter.
        
        Args:
            exporter: Exporter object that implements the export method
        """
        # Validate that exporter has an export method
        if not hasattr(exporter, "export") or not callable(getattr(exporter, "export")):
            raise ValueError("Exporter must implement the export method")
        
        # Add to exporters list
        self.exporters.append(exporter)
        logger.info(f"Added {exporter.name} exporter to the reporter")
    
    def format_metrics_for_text(self, metrics_data: Dict) -> str:
        """
        Format metrics data as plain text.
        
        Args:
            metrics_data: Dictionary with performance metrics data
            
        Returns:
            Formatted metrics text
        """
        text = "KEY METRICS\n===========\n"
        
        # Format API metrics
        if "api" in metrics_data:
            api = metrics_data["api"]
            text += "\nAPI Metrics:\n"
            
            # Response time
            if "response_time" in api:
                text += f"- Response Time (p95): {api['response_time']} ms\n"
            
            # Throughput
            if "throughput" in api:
                text += f"- Throughput: {api['throughput']} req/sec\n"
            
            # Error rate
            if "error_rate" in api:
                text += f"- Error Rate: {api['error_rate']}%\n"
        
        # Format calculation metrics
        if "calculation" in metrics_data:
            calc = metrics_data["calculation"]
            text += "\nCalculation Metrics:\n"
            
            # Execution time
            if "execution_time" in calc:
                text += f"- Execution Time (p95): {calc['execution_time']} ms\n"
            
            # Calculation accuracy
            if "calculation_accuracy" in calc:
                text += f"- Accuracy: {calc['calculation_accuracy']}%\n"
        
        # Format resource metrics
        if "resources" in metrics_data:
            res = metrics_data["resources"]
            text += "\nResource Metrics:\n"
            
            # CPU utilization
            if "cpu_utilization" in res:
                text += f"- CPU Utilization: {res['cpu_utilization']}%\n"
            
            # Memory utilization
            if "memory_utilization" in res:
                text += f"- Memory Utilization: {res['memory_utilization']}%\n"
        
        return text
    
    def format_analysis_for_text(self, analysis_results: Dict) -> str:
        """
        Format analysis results as plain text.
        
        Args:
            analysis_results: Dictionary with analysis results
            
        Returns:
            Formatted analysis text
        """
        text = "ANALYSIS RESULTS\n================\n"
        
        # Overall status
        text += f"Overall Status: {analysis_results.get('status', 'UNKNOWN')}\n"
        
        # Critical failures
        if "critical_failures" in analysis_results and analysis_results["critical_failures"]:
            text += "\nCritical Failures:\n"
            for failure in analysis_results["critical_failures"]:
                text += f"- {failure}\n"
        
        # API metrics analysis
        if "api_metrics" in analysis_results:
            text += "\nAPI Metrics Analysis:\n"
            for metric, result in analysis_results["api_metrics"].items():
                status = result.get("status", "UNKNOWN")
                value = result.get("value", "N/A")
                threshold = result.get("threshold", "N/A")
                text += f"- {metric}: {status} (value: {value}, threshold: {threshold})\n"
        
        # Calculation metrics analysis
        if "calculation_metrics" in analysis_results:
            text += "\nCalculation Metrics Analysis:\n"
            for metric, result in analysis_results["calculation_metrics"].items():
                status = result.get("status", "UNKNOWN")
                value = result.get("value", "N/A")
                threshold = result.get("threshold", "N/A")
                text += f"- {metric}: {status} (value: {value}, threshold: {threshold})\n"
        
        # Resource metrics analysis
        if "resource_metrics" in analysis_results:
            text += "\nResource Metrics Analysis:\n"
            for metric, result in analysis_results["resource_metrics"].items():
                status = result.get("status", "UNKNOWN")
                value = result.get("value", "N/A")
                threshold = result.get("threshold", "N/A")
                text += f"- {metric}: {status} (value: {value}, threshold: {threshold})\n"
        
        return text
    
    def get_sla_status(self, analysis_results: Dict) -> Dict:
        """
        Determine SLA compliance status from analysis results.
        
        Args:
            analysis_results: Dictionary with analysis results
            
        Returns:
            SLA compliance status for each metric
        """
        sla_status = {
            "overall_status": "COMPLIANT"
        }
        
        # Extract critical metrics for SLA compliance
        # Response time
        if ("api_metrics" in analysis_results and 
                "response_time" in analysis_results["api_metrics"]):
            response_time = analysis_results["api_metrics"]["response_time"]
            sla_status["response_time"] = {
                "value": response_time["value"],
                "target": response_time["threshold"],
                "status": response_time["status"]
            }
            if response_time["status"] == "FAIL":
                sla_status["overall_status"] = "NON-COMPLIANT"
        
        # Error rate
        if ("api_metrics" in analysis_results and 
                "error_rate" in analysis_results["api_metrics"]):
            error_rate = analysis_results["api_metrics"]["error_rate"]
            sla_status["error_rate"] = {
                "value": error_rate["value"],
                "target": error_rate["threshold"],
                "status": error_rate["status"]
            }
            if error_rate["status"] == "FAIL":
                sla_status["overall_status"] = "NON-COMPLIANT"
        
        # Calculation accuracy
        if ("calculation_metrics" in analysis_results and 
                "calculation_accuracy" in analysis_results["calculation_metrics"]):
            calc_accuracy = analysis_results["calculation_metrics"]["calculation_accuracy"]
            sla_status["calculation_accuracy"] = {
                "value": calc_accuracy["value"],
                "target": calc_accuracy["threshold"],
                "status": calc_accuracy["status"]
            }
            if calc_accuracy["status"] == "FAIL":
                sla_status["overall_status"] = "NON-COMPLIANT"
        
        # System availability - derived from error rate and other factors
        availability = 100.0
        if "error_rate" in sla_status:
            # A high error rate affects availability
            availability -= sla_status["error_rate"]["value"] / 2
        
        sla_status["system_availability"] = {
            "value": availability,
            "target": 99.95,  # From requirements
            "status": "PASS" if availability >= 99.95 else "FAIL"
        }
        
        if sla_status["system_availability"]["status"] == "FAIL":
            sla_status["overall_status"] = "NON-COMPLIANT"
        
        return sla_status
    
    def generate_recommendations(self, analysis_results: Dict) -> List:
        """
        Generate recommendations based on analysis results.
        
        Args:
            analysis_results: Dictionary with analysis results
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Check for response time issues
        if ("api_metrics" in analysis_results and 
                "response_time" in analysis_results["api_metrics"] and
                analysis_results["api_metrics"]["response_time"]["status"] == "FAIL"):
            
            response_time = analysis_results["api_metrics"]["response_time"]["value"]
            threshold = analysis_results["api_metrics"]["response_time"]["threshold"]
            
            recommendations.append(
                f"Response time ({response_time}ms) exceeds the threshold ({threshold}ms). "
                "Consider optimizing database queries, implementing additional caching, "
                "or increasing server resources."
            )
        
        # Check for throughput issues
        if ("api_metrics" in analysis_results and 
                "throughput" in analysis_results["api_metrics"] and
                analysis_results["api_metrics"]["throughput"]["status"] == "FAIL"):
            
            throughput = analysis_results["api_metrics"]["throughput"]["value"]
            threshold = analysis_results["api_metrics"]["throughput"]["threshold"]
            
            recommendations.append(
                f"Throughput ({throughput} req/sec) is below the target ({threshold} req/sec). "
                "Consider implementing load balancing, horizontal scaling, or optimizing "
                "the calculation algorithms."
            )
        
        # Check for error rate issues
        if ("api_metrics" in analysis_results and 
                "error_rate" in analysis_results["api_metrics"] and
                analysis_results["api_metrics"]["error_rate"]["status"] == "FAIL"):
            
            error_rate = analysis_results["api_metrics"]["error_rate"]["value"]
            threshold = analysis_results["api_metrics"]["error_rate"]["threshold"]
            
            recommendations.append(
                f"Error rate ({error_rate}%) exceeds the threshold ({threshold}%). "
                "Investigate error patterns in logs, improve error handling, "
                "and consider implementing circuit breakers for external services."
            )
        
        # Check for calculation accuracy issues
        if ("calculation_metrics" in analysis_results and 
                "calculation_accuracy" in analysis_results["calculation_metrics"] and
                analysis_results["calculation_metrics"]["calculation_accuracy"]["status"] == "FAIL"):
            
            accuracy = analysis_results["calculation_metrics"]["calculation_accuracy"]["value"]
            
            recommendations.append(
                f"Calculation accuracy ({accuracy}%) is below the required 100%. "
                "This is critical for financial calculations. Review calculation formulas, "
                "implement additional validation, and verify external data sources."
            )
        
        # Check for resource utilization issues
        if "resource_metrics" in analysis_results:
            # CPU utilization
            if ("cpu_utilization" in analysis_results["resource_metrics"] and
                    analysis_results["resource_metrics"]["cpu_utilization"]["status"] == "FAIL"):
                
                cpu_util = analysis_results["resource_metrics"]["cpu_utilization"]["value"]
                threshold = analysis_results["resource_metrics"]["cpu_utilization"]["threshold"]
                
                recommendations.append(
                    f"CPU utilization ({cpu_util}%) exceeds the threshold ({threshold}%). "
                    "Consider optimizing CPU-intensive operations, implementing caching, "
                    "or scaling horizontally to distribute load."
                )
            
            # Memory utilization
            if ("memory_utilization" in analysis_results["resource_metrics"] and
                    analysis_results["resource_metrics"]["memory_utilization"]["status"] == "FAIL"):
                
                mem_util = analysis_results["resource_metrics"]["memory_utilization"]["value"]
                threshold = analysis_results["resource_metrics"]["memory_utilization"]["threshold"]
                
                recommendations.append(
                    f"Memory utilization ({mem_util}%) exceeds the threshold ({threshold}%). "
                    "Look for memory leaks, optimize memory-intensive operations, "
                    "or increase available memory resources."
                )
        
        return recommendations