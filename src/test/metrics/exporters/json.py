import logging
import os
import json
from datetime import datetime
from pathlib import Path
from .prometheus import BaseExporter

# Configure logger
logger = logging.getLogger(__name__)

class JSONExporter(BaseExporter):
    """
    Exports metrics in JSON format for programmatic analysis and visualization.
    Extends the BaseExporter class.
    """
    
    def __init__(self, config=None):
        """
        Initialize the JSON exporter with default configuration
        
        Args:
            config (dict): Configuration dictionary for the exporter
        """
        super().__init__(config)
        self.name = 'json'
        self._file_paths = {}  # Store paths to exported JSON files
        self._timestamp_format = config.get('timestamp_format', '%Y%m%d_%H%M%S')
    
    def ensure_output_directory(self, output_path):
        """
        Ensures that the output directory exists, creating it if necessary
        
        Args:
            output_path (str): Path where metrics should be exported
            
        Returns:
            Path: Path object representing the output directory
        """
        path = Path(output_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created output directory: {path}")
        return path
    
    def export(self, metrics_data, output_path):
        """
        Export metrics to JSON files
        
        Args:
            metrics_data (dict): Dictionary containing metrics to export
            output_path (str): Path where metrics should be exported
            
        Returns:
            dict: Export results with paths to exported JSON files
        """
        # Ensure output directory exists
        output_dir = self.ensure_output_directory(output_path)
        
        # Initialize results and file paths
        results = {'status': 'success', 'files': {}}
        self._file_paths = {}
        
        # Generate timestamp for file naming
        timestamp = datetime.now().strftime(self._timestamp_format)
        
        # Export API metrics if present
        if 'api_metrics' in metrics_data:
            api_result = self.export_api_metrics(metrics_data['api_metrics'], output_dir, timestamp)
            results['files'].update(api_result)
        
        # Export calculation metrics if present
        if 'calculation_metrics' in metrics_data:
            calc_result = self.export_calculation_metrics(metrics_data['calculation_metrics'], output_dir, timestamp)
            results['files'].update(calc_result)
        
        # Export resource metrics if present
        if 'resource_metrics' in metrics_data:
            resource_result = self.export_resource_metrics(metrics_data['resource_metrics'], output_dir, timestamp)
            results['files'].update(resource_result)
        
        # Export combined metrics if configured
        if self.config.get('combined_export', True):
            combined_result = self.export_combined_metrics(metrics_data, output_dir, timestamp)
            results['files'].update(combined_result)
        
        # Add file paths to results
        results['file_paths'] = self._file_paths
        
        return results
    
    def export_api_metrics(self, api_metrics, output_dir, timestamp):
        """
        Export API metrics to a JSON file
        
        Args:
            api_metrics (dict): Dictionary containing API metrics
            output_dir (Path): Output directory
            timestamp (str): Timestamp string for file naming
            
        Returns:
            dict: Dictionary with path to exported API metrics JSON file
        """
        # Create file path
        file_name = f"api_metrics_{timestamp}.json"
        file_path = output_dir / file_name
        
        # Add metadata
        data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'exporter': self.name,
                'type': 'api_metrics'
            },
            'metrics': api_metrics
        }
        
        # Write to file
        pretty_print = self.config.get('pretty_print', True)
        success = self.write_json(str(file_path), data, pretty_print)
        
        # Store file path
        if success:
            self._file_paths['api_metrics'] = str(file_path)
            return {'api_metrics': str(file_path)}
        
        return {'api_metrics': None}
    
    def export_calculation_metrics(self, calculation_metrics, output_dir, timestamp):
        """
        Export calculation metrics to a JSON file
        
        Args:
            calculation_metrics (dict): Dictionary containing calculation metrics
            output_dir (Path): Output directory
            timestamp (str): Timestamp string for file naming
            
        Returns:
            dict: Dictionary with path to exported calculation metrics JSON file
        """
        # Create file path
        file_name = f"calculation_metrics_{timestamp}.json"
        file_path = output_dir / file_name
        
        # Add metadata
        data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'exporter': self.name,
                'type': 'calculation_metrics'
            },
            'metrics': calculation_metrics
        }
        
        # Write to file
        pretty_print = self.config.get('pretty_print', True)
        success = self.write_json(str(file_path), data, pretty_print)
        
        # Store file path
        if success:
            self._file_paths['calculation_metrics'] = str(file_path)
            return {'calculation_metrics': str(file_path)}
        
        return {'calculation_metrics': None}
    
    def export_resource_metrics(self, resource_metrics, output_dir, timestamp):
        """
        Export resource metrics to a JSON file
        
        Args:
            resource_metrics (dict): Dictionary containing resource metrics
            output_dir (Path): Output directory
            timestamp (str): Timestamp string for file naming
            
        Returns:
            dict: Dictionary with path to exported resource metrics JSON file
        """
        # Create file path
        file_name = f"resource_metrics_{timestamp}.json"
        file_path = output_dir / file_name
        
        # Add metadata
        data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'exporter': self.name,
                'type': 'resource_metrics'
            },
            'metrics': resource_metrics
        }
        
        # Write to file
        pretty_print = self.config.get('pretty_print', True)
        success = self.write_json(str(file_path), data, pretty_print)
        
        # Store file path
        if success:
            self._file_paths['resource_metrics'] = str(file_path)
            return {'resource_metrics': str(file_path)}
        
        return {'resource_metrics': None}
    
    def export_combined_metrics(self, metrics_data, output_dir, timestamp):
        """
        Export all metrics to a single combined JSON file
        
        Args:
            metrics_data (dict): Dictionary containing all metrics
            output_dir (Path): Output directory
            timestamp (str): Timestamp string for file naming
            
        Returns:
            dict: Dictionary with path to exported combined metrics JSON file
        """
        # Create file path
        file_name = f"combined_metrics_{timestamp}.json"
        file_path = output_dir / file_name
        
        # Create combined data structure
        combined_data = {
            'api_metrics': metrics_data.get('api_metrics', {}),
            'calculation_metrics': metrics_data.get('calculation_metrics', {}),
            'resource_metrics': metrics_data.get('resource_metrics', {})
        }
        
        # Add metadata
        data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'exporter': self.name,
                'types': list(k for k in combined_data.keys() if combined_data[k])
            },
            'metrics': combined_data
        }
        
        # Write to file
        pretty_print = self.config.get('pretty_print', True)
        success = self.write_json(str(file_path), data, pretty_print)
        
        # Store file path
        if success:
            self._file_paths['combined_metrics'] = str(file_path)
            return {'combined_metrics': str(file_path)}
        
        return {'combined_metrics': None}
    
    def write_json(self, file_path, data, pretty_print=True):
        """
        Write data to a JSON file
        
        Args:
            file_path (str): Path to the JSON file
            data (dict): Data to be written
            pretty_print (bool): Whether to format the JSON with indentation
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(file_path, 'w') as f:
                if pretty_print:
                    json_str = json.dumps(data, indent=4)
                else:
                    json_str = json.dumps(data)
                f.write(json_str)
                
            logger.info(f"Successfully wrote metrics to JSON file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing to JSON file {file_path}: {str(e)}")
            return False
    
    def prepare_time_series_data(self, time_series_data):
        """
        Prepare time series data for JSON export with timestamps as keys
        
        Args:
            time_series_data (dict): Dictionary containing time series data
            
        Returns:
            dict: Dictionary with timestamps as keys and metric values as values
        """
        result = {}
        
        # Extract timestamps and corresponding values
        timestamps = time_series_data.get('timestamps', [])
        values = time_series_data.get('values', [])
        
        # Create a dictionary with timestamps as keys
        for i, timestamp in enumerate(timestamps):
            if i < len(values):
                result[timestamp] = values[i]
        
        return result