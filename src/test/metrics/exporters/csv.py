import logging
import os
import csv
from datetime import datetime
from pathlib import Path

from .prometheus import BaseExporter

# Configure logger
logger = logging.getLogger(__name__)

class CSVExporter(BaseExporter):
    """
    Exports metrics in CSV format for analysis in spreadsheet applications and data visualization tools.
    Extends the BaseExporter class.
    """
    
    def __init__(self, config=None):
        """
        Initialize the CSV exporter with default configuration
        
        Args:
            config (dict): Configuration dictionary for the exporter
        """
        super().__init__(config)
        self.name = 'csv'
        self._file_paths = {}  # Store paths to exported CSV files
        self._timestamp_format = config.get('timestamp_format', '%Y%m%d_%H%M%S') if config else '%Y%m%d_%H%M%S'
    
    def ensure_output_directory(self, output_path):
        """
        Ensures that the output directory exists, creating it if necessary
        
        Args:
            output_path (str): Path to the output directory
            
        Returns:
            Path: Path object representing the output directory
        """
        path = Path(output_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created output directory: {path}")
        return path
    
    def export(self, metrics_data, output_path=None):
        """
        Export metrics to CSV files
        
        Args:
            metrics_data (dict): Dictionary containing metrics to export
            output_path (str, optional): Path where metrics should be exported
            
        Returns:
            dict: Export results with paths to exported CSV files
        """
        if not output_path:
            raise ValueError("Output path is required for CSV export")
            
        # Ensure output directory exists
        output_dir = self.ensure_output_directory(output_path)
        
        # Initialize results and file paths
        results = {
            'status': 'success',
            'files': []
        }
        self._file_paths = {}
        
        # Generate timestamp for file naming
        timestamp = datetime.now().strftime(self._timestamp_format)
        
        # Export API metrics if present
        if 'api_metrics' in metrics_data:
            api_results = self.export_api_metrics(metrics_data['api_metrics'], output_dir, timestamp)
            results['files'].extend(api_results.get('files', []))
            self._file_paths.update(api_results.get('file_paths', {}))
        
        # Export calculation metrics if present
        if 'calculation_metrics' in metrics_data:
            calc_results = self.export_calculation_metrics(metrics_data['calculation_metrics'], output_dir, timestamp)
            results['files'].extend(calc_results.get('files', []))
            self._file_paths.update(calc_results.get('file_paths', {}))
        
        # Export resource metrics if present
        if 'resource_metrics' in metrics_data:
            resource_results = self.export_resource_metrics(metrics_data['resource_metrics'], output_dir, timestamp)
            results['files'].extend(resource_results.get('files', []))
            self._file_paths.update(resource_results.get('file_paths', {}))
        
        # Add file_paths to results
        results['file_paths'] = self._file_paths
        
        return results
    
    def export_api_metrics(self, api_metrics, output_dir, timestamp):
        """
        Export API metrics to a CSV file
        
        Args:
            api_metrics (dict): Dictionary containing API metrics
            output_dir (Path): Directory where the CSV file should be written
            timestamp (str): Timestamp string for file naming
            
        Returns:
            dict: Dictionary with path to exported API metrics CSV file
        """
        results = {
            'files': [],
            'file_paths': {}
        }
        
        # Export overall API metrics
        overall_file = output_dir / f"api_metrics_{timestamp}.csv"
        headers, rows = self.flatten_metrics(api_metrics, '')
        
        if self.write_csv(str(overall_file), headers, rows):
            results['files'].append(str(overall_file))
            results['file_paths']['api_overall'] = str(overall_file)
            logger.info(f"Exported API metrics to {overall_file}")
        
        # Export endpoint-specific metrics if present
        if 'endpoints' in api_metrics and api_metrics['endpoints']:
            endpoints_file = output_dir / f"api_endpoints_{timestamp}.csv"
            
            # Create headers and rows for endpoints
            endpoint_headers = ['endpoint']
            endpoint_data = []
            
            for endpoint, metrics in api_metrics['endpoints'].items():
                row_data = {'endpoint': endpoint}
                
                # Flatten endpoint metrics
                for key, value in metrics.items():
                    if isinstance(value, (int, float, str, bool)):
                        if key not in endpoint_headers:
                            endpoint_headers.append(key)
                        row_data[key] = value
                    elif isinstance(value, list) and key == 'response_times':
                        # Handle response times separately
                        continue
                
                endpoint_data.append(row_data)
            
            # Convert endpoint_data to rows
            endpoint_rows = []
            for data in endpoint_data:
                row = []
                for header in endpoint_headers:
                    row.append(data.get(header, ''))
                endpoint_rows.append(row)
            
            if self.write_csv(str(endpoints_file), endpoint_headers, endpoint_rows):
                results['files'].append(str(endpoints_file))
                results['file_paths']['api_endpoints'] = str(endpoints_file)
                logger.info(f"Exported API endpoint metrics to {endpoints_file}")
            
            # Export response times as time series if present
            if any('response_times' in metrics for _, metrics in api_metrics['endpoints'].items()):
                response_times_file = output_dir / f"api_response_times_{timestamp}.csv"
                
                # Process response times for each endpoint
                rt_headers = ['endpoint', 'response_time']
                rt_rows = []
                
                for endpoint, metrics in api_metrics['endpoints'].items():
                    if 'response_times' in metrics and metrics['response_times']:
                        for rt in metrics['response_times']:
                            rt_rows.append([endpoint, rt])
                
                if self.write_csv(str(response_times_file), rt_headers, rt_rows):
                    results['files'].append(str(response_times_file))
                    results['file_paths']['api_response_times'] = str(response_times_file)
                    logger.info(f"Exported API response times to {response_times_file}")
        
        return results
    
    def export_calculation_metrics(self, calculation_metrics, output_dir, timestamp):
        """
        Export calculation metrics to a CSV file
        
        Args:
            calculation_metrics (dict): Dictionary containing calculation metrics
            output_dir (Path): Directory where the CSV file should be written
            timestamp (str): Timestamp string for file naming
            
        Returns:
            dict: Dictionary with path to exported calculation metrics CSV file
        """
        results = {
            'files': [],
            'file_paths': {}
        }
        
        # Export overall calculation metrics
        overall_file = output_dir / f"calculation_metrics_{timestamp}.csv"
        headers, rows = self.flatten_metrics(calculation_metrics, '')
        
        if self.write_csv(str(overall_file), headers, rows):
            results['files'].append(str(overall_file))
            results['file_paths']['calculation_overall'] = str(overall_file)
            logger.info(f"Exported calculation metrics to {overall_file}")
        
        # Export calculation type-specific metrics if present
        if 'calculation_types' in calculation_metrics and calculation_metrics['calculation_types']:
            calc_types_file = output_dir / f"calculation_types_{timestamp}.csv"
            
            # Create headers and rows for calculation types
            type_headers = ['calculation_type']
            type_data = []
            
            for calc_type, metrics in calculation_metrics['calculation_types'].items():
                row_data = {'calculation_type': calc_type}
                
                # Flatten calculation type metrics
                for key, value in metrics.items():
                    if isinstance(value, (int, float, str, bool)):
                        if key not in type_headers:
                            type_headers.append(key)
                        row_data[key] = value
                    elif isinstance(value, list) and key == 'calculation_times':
                        # Handle calculation times separately
                        continue
                
                type_data.append(row_data)
            
            # Convert type_data to rows
            type_rows = []
            for data in type_data:
                row = []
                for header in type_headers:
                    row.append(data.get(header, ''))
                type_rows.append(row)
            
            if self.write_csv(str(calc_types_file), type_headers, type_rows):
                results['files'].append(str(calc_types_file))
                results['file_paths']['calculation_types'] = str(calc_types_file)
                logger.info(f"Exported calculation type metrics to {calc_types_file}")
            
            # Export calculation times as time series if present
            if any('calculation_times' in metrics for _, metrics in calculation_metrics['calculation_types'].items()):
                calc_times_file = output_dir / f"calculation_times_{timestamp}.csv"
                
                # Process calculation times for each type
                ct_headers = ['calculation_type', 'calculation_time']
                ct_rows = []
                
                for calc_type, metrics in calculation_metrics['calculation_types'].items():
                    if 'calculation_times' in metrics and metrics['calculation_times']:
                        for ct in metrics['calculation_times']:
                            ct_rows.append([calc_type, ct])
                
                if self.write_csv(str(calc_times_file), ct_headers, ct_rows):
                    results['files'].append(str(calc_times_file))
                    results['file_paths']['calculation_times'] = str(calc_times_file)
                    logger.info(f"Exported calculation times to {calc_times_file}")
        
        return results
    
    def export_resource_metrics(self, resource_metrics, output_dir, timestamp):
        """
        Export resource metrics to a CSV file
        
        Args:
            resource_metrics (dict): Dictionary containing resource metrics
            output_dir (Path): Directory where the CSV file should be written
            timestamp (str): Timestamp string for file naming
            
        Returns:
            dict: Dictionary with path to exported resource metrics CSV file
        """
        results = {
            'files': [],
            'file_paths': {}
        }
        
        # Export overall resource metrics
        overall_file = output_dir / f"resource_metrics_{timestamp}.csv"
        headers, rows = self.flatten_metrics(resource_metrics, '')
        
        if self.write_csv(str(overall_file), headers, rows):
            results['files'].append(str(overall_file))
            results['file_paths']['resource_overall'] = str(overall_file)
            logger.info(f"Exported resource metrics to {overall_file}")
        
        # Export component-specific resource metrics if present
        if 'components' in resource_metrics and resource_metrics['components']:
            components_file = output_dir / f"resource_components_{timestamp}.csv"
            
            # Create headers and rows for components
            component_headers = ['component']
            component_data = []
            
            for component, metrics in resource_metrics['components'].items():
                row_data = {'component': component}
                
                # Flatten component metrics
                for key, value in metrics.items():
                    if isinstance(value, (int, float, str, bool)):
                        if key not in component_headers:
                            component_headers.append(key)
                        row_data[key] = value
                
                component_data.append(row_data)
            
            # Convert component_data to rows
            component_rows = []
            for data in component_data:
                row = []
                for header in component_headers:
                    row.append(data.get(header, ''))
                component_rows.append(row)
            
            if self.write_csv(str(components_file), component_headers, component_rows):
                results['files'].append(str(components_file))
                results['file_paths']['resource_components'] = str(components_file)
                logger.info(f"Exported resource component metrics to {components_file}")
        
        # Export time series resource metrics if present
        if 'time_series' in resource_metrics and resource_metrics['time_series']:
            ts_file = output_dir / f"resource_time_series_{timestamp}.csv"
            
            # Convert time series data to headers and rows
            ts_headers, ts_rows = self.prepare_time_series_data(resource_metrics['time_series'])
            
            if self.write_csv(str(ts_file), ts_headers, ts_rows):
                results['files'].append(str(ts_file))
                results['file_paths']['resource_time_series'] = str(ts_file)
                logger.info(f"Exported resource time series to {ts_file}")
        
        return results
    
    def write_csv(self, file_path, headers, rows):
        """
        Write data to a CSV file
        
        Args:
            file_path (str): Path to the CSV file
            headers (list): List of column headers
            rows (list): List of row data (list of lists)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                writer.writerows(rows)
            
            logger.debug(f"Successfully wrote CSV file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing CSV file {file_path}: {str(e)}")
            return False
    
    def flatten_metrics(self, metrics, prefix=''):
        """
        Flatten nested metrics dictionary into rows suitable for CSV export
        
        Args:
            metrics (dict): Dictionary containing metrics
            prefix (str): Prefix for nested keys
            
        Returns:
            tuple: Tuple containing (headers, rows)
        """
        headers = []
        row_data = {}
        
        for key, value in metrics.items():
            # Skip nested dictionaries that will be handled separately
            if key in ('endpoints', 'calculation_types', 'components', 'time_series'):
                continue
            
            # Skip list values that are handled separately
            if isinstance(value, list) and key in ('response_times', 'calculation_times'):
                continue
            
            # Handle flat values
            if isinstance(value, (int, float, str, bool)):
                col_name = f"{prefix}{key}" if prefix else key
                headers.append(col_name)
                row_data[col_name] = value
            # Handle nested dictionaries
            elif isinstance(value, dict):
                nested_prefix = f"{prefix}{key}_" if prefix else f"{key}_"
                nested_headers, nested_data = self.flatten_metrics(value, nested_prefix)
                
                headers.extend(nested_headers)
                row_data.update(nested_data)
            # Handle other types (convert to string)
            elif value is not None:
                col_name = f"{prefix}{key}" if prefix else key
                headers.append(col_name)
                row_data[col_name] = str(value)
        
        # Create a single row with all values
        row = []
        for header in headers:
            row.append(row_data.get(header, ''))
        
        return headers, [row]
    
    def prepare_time_series_data(self, time_series_data):
        """
        Prepare time series data for CSV export with timestamps as rows
        
        Args:
            time_series_data (dict): Dictionary containing time series data
            
        Returns:
            tuple: Tuple containing (headers, rows)
        """
        # Extract timestamps and metrics
        timestamps = []
        metrics = {}
        
        for timestamp, data in time_series_data.items():
            timestamps.append(timestamp)
            for key, value in data.items():
                if key not in metrics:
                    metrics[key] = {}
                metrics[key][timestamp] = value
        
        # Sort timestamps
        timestamps.sort()
        
        # Create headers: timestamp followed by metric names
        headers = ['timestamp'] + list(metrics.keys())
        
        # Create rows
        rows = []
        for timestamp in timestamps:
            row = [timestamp]
            for metric_name in headers[1:]:
                row.append(metrics[metric_name].get(timestamp, ''))
            rows.append(row)
        
        return headers, rows