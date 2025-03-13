#!/usr/bin/env python3
"""
Load Test Results Analyzer for Borrow Rate & Locate Fee Pricing Engine

This script analyzes the results of load tests performed with Locust,
generating reports, visualizations, and exporting metrics in various formats
for performance analysis and comparison with defined thresholds.
"""

import argparse
import logging
import os
import sys
import json
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

# Internal imports
import yaml
from test.metrics.visualizers.generate_charts import ChartGenerator
from test.metrics.exporters.csv import CSVExporter
from test.metrics.exporters.json import JSONExporter

# Configure logger
logger = logging.getLogger(__name__)

# Path to the default config file
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.yaml')


def setup_logging(log_level):
    """
    Configure logging for the analysis script

    Args:
        log_level (int): Logging level (e.g., logging.INFO)
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    root_logger.addHandler(console_handler)
    
    logger.debug("Logging configured successfully")


def load_config(config_file):
    """
    Load configuration from YAML file

    Args:
        config_file (str): Path to the configuration file

    Returns:
        dict: Configuration dictionary
    """
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {config_file}")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_file}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file: {e}")
        return {}


def load_test_results(results_dir):
    """
    Load test results from Locust CSV or JSON files

    Args:
        results_dir (str): Directory containing test results

    Returns:
        dict: Dictionary containing parsed test results
    """
    results = {
        'stats': None,
        'stats_history': None,
        'exceptions': None,
        'request_metrics': None,
        'distribution': None,
        'raw_data': {}
    }
    
    results_path = Path(results_dir)
    
    if not results_path.exists():
        logger.error(f"Results directory not found: {results_dir}")
        return results
    
    # Look for Locust stats CSV files
    stats_file = results_path / 'stats.csv'
    stats_history_file = results_path / 'stats_history.csv'
    
    # Look for Locust JSON result file
    json_result_file = results_path / 'results.json'
    
    # Parse CSV files if they exist
    if stats_file.exists():
        try:
            results['stats'] = pd.read_csv(stats_file)
            logger.info(f"Loaded stats from {stats_file}")
        except Exception as e:
            logger.error(f"Error loading stats file: {e}")
    
    if stats_history_file.exists():
        try:
            results['stats_history'] = pd.read_csv(stats_history_file)
            logger.info(f"Loaded stats history from {stats_history_file}")
        except Exception as e:
            logger.error(f"Error loading stats history file: {e}")
    
    # Parse JSON result file if it exists
    if json_result_file.exists():
        try:
            with open(json_result_file, 'r') as f:
                json_data = json.load(f)
                results['raw_data'] = json_data
                
                # Extract useful sections from the JSON data
                if 'stats' in json_data:
                    results['stats_json'] = json_data['stats']
                if 'stats_history' in json_data:
                    results['stats_history_json'] = json_data['stats_history']
                if 'exceptions' in json_data:
                    results['exceptions'] = json_data['exceptions']
                if 'percentiles' in json_data:
                    results['distribution'] = json_data['percentiles']
                
            logger.info(f"Loaded JSON results from {json_result_file}")
        except Exception as e:
            logger.error(f"Error loading JSON result file: {e}")
    
    # Look for any other results files in the directory
    for file in results_path.glob('*.csv'):
        if file.name not in ['stats.csv', 'stats_history.csv']:
            try:
                file_key = file.stem.replace('-', '_')
                results[file_key] = pd.read_csv(file)
                logger.info(f"Loaded additional data from {file}")
            except Exception as e:
                logger.error(f"Error loading file {file}: {e}")
    
    # Check if we have loaded any data
    if results['stats'] is None and results['stats_json'] is None:
        logger.warning("No test results data found in the specified directory")
    else:
        logger.info("Test results loaded successfully")
    
    return results


def process_metrics(test_results):
    """
    Process raw test results into structured metrics

    Args:
        test_results (dict): Dictionary containing test results

    Returns:
        dict: Dictionary containing processed metrics
    """
    metrics = {
        'api_metrics': {},
        'calculation_metrics': {},
        'resource_metrics': {}
    }
    
    # Process API metrics from stats data
    if test_results['stats'] is not None or test_results.get('stats_json') is not None:
        api_metrics = {}
        
        # Use DataFrame if available, otherwise use JSON data
        if test_results['stats'] is not None:
            stats_df = test_results['stats']
            
            # Overall metrics
            total_requests = stats_df['Request Count'].sum()
            total_failures = stats_df['Failure Count'].sum()
            total_median_response_time = stats_df['Median Response Time'].mean()
            total_avg_response_time = stats_df['Average Response Time'].mean()
            total_min_response_time = stats_df['Min Response Time'].min()
            total_max_response_time = stats_df['Max Response Time'].max()
            error_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
            
            # Extract percentiles if available
            percentiles = {}
            if 'p50' in stats_df:
                percentiles['p50'] = stats_df['p50'].mean()
            if 'p90' in stats_df:
                percentiles['p90'] = stats_df['p90'].mean()
            if 'p95' in stats_df:
                percentiles['p95'] = stats_df['p95'].mean()
            if 'p99' in stats_df:
                percentiles['p99'] = stats_df['p99'].mean()
            
            # Endpoint-specific metrics
            endpoints = {}
            for _, row in stats_df.iterrows():
                if row['Name'] != 'Aggregated':
                    endpoint = row['Name']
                    endpoints[endpoint] = {
                        'requests': row['Request Count'],
                        'failures': row['Failure Count'],
                        'median_response_time': row['Median Response Time'],
                        'avg_response_time': row['Average Response Time'],
                        'min_response_time': row['Min Response Time'],
                        'max_response_time': row['Max Response Time'],
                        'error_rate': (row['Failure Count'] / row['Request Count'] * 100) if row['Request Count'] > 0 else 0
                    }
                    
                    # Add percentiles if available
                    if 'p50' in row:
                        endpoints[endpoint]['p50'] = row['p50']
                    if 'p90' in row:
                        endpoints[endpoint]['p90'] = row['p90']
                    if 'p95' in row:
                        endpoints[endpoint]['p95'] = row['p95']
                    if 'p99' in row:
                        endpoints[endpoint]['p99'] = row['p99']
            
            # Get request rate over time if stats_history is available
            request_rate = []
            if test_results['stats_history'] is not None:
                history_df = test_results['stats_history']
                if 'Total RPS' in history_df:
                    for _, row in history_df.iterrows():
                        request_rate.append({
                            'timestamp': row['Timestamp'],
                            'requests_per_second': row['Total RPS']
                        })
            
            # Compile API metrics
            api_metrics = {
                'total_requests': total_requests,
                'total_failures': total_failures,
                'error_rate': error_rate,
                'response_time': {
                    'median': total_median_response_time,
                    'average': total_avg_response_time,
                    'min': total_min_response_time,
                    'max': total_max_response_time,
                    'percentiles': percentiles
                },
                'endpoints': endpoints,
                'request_rate': request_rate
            }
        
        else:
            # Extract metrics from JSON data
            stats_json = test_results['stats_json']
            
            # Calculate overall metrics
            total_requests = sum(stat.get('num_requests', 0) for stat in stats_json)
            total_failures = sum(stat.get('num_failures', 0) for stat in stats_json)
            error_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
            
            # Extract response time metrics from aggregated stats
            aggregated_stats = next((stat for stat in stats_json if stat.get('name') == 'Aggregated'), None)
            response_time = {
                'median': 0,
                'average': 0,
                'min': 0,
                'max': 0,
                'percentiles': {}
            }
            
            if aggregated_stats:
                response_time['median'] = aggregated_stats.get('median_response_time', 0)
                response_time['average'] = aggregated_stats.get('avg_response_time', 0)
                response_time['min'] = aggregated_stats.get('min_response_time', 0)
                response_time['max'] = aggregated_stats.get('max_response_time', 0)
            
            # Extract percentiles from distribution data if available
            if test_results.get('distribution'):
                for endpoint, percentiles in test_results['distribution'].items():
                    if endpoint == 'Aggregated':
                        for percentile, value in percentiles.items():
                            # Convert percentile key format from '0.XX' to 'pXX'
                            if percentile.startswith('0.'):
                                p_key = 'p' + percentile[2:]
                                response_time['percentiles'][p_key] = value
            
            # Extract endpoint-specific metrics
            endpoints = {}
            for stat in stats_json:
                if stat.get('name') != 'Aggregated':
                    endpoint = stat.get('name', '')
                    requests = stat.get('num_requests', 0)
                    failures = stat.get('num_failures', 0)
                    
                    endpoints[endpoint] = {
                        'requests': requests,
                        'failures': failures,
                        'median_response_time': stat.get('median_response_time', 0),
                        'avg_response_time': stat.get('avg_response_time', 0),
                        'min_response_time': stat.get('min_response_time', 0),
                        'max_response_time': stat.get('max_response_time', 0),
                        'error_rate': (failures / requests * 100) if requests > 0 else 0
                    }
                    
                    # Add percentiles from distribution data if available
                    if test_results.get('distribution') and endpoint in test_results['distribution']:
                        for percentile, value in test_results['distribution'][endpoint].items():
                            if percentile.startswith('0.'):
                                p_key = 'p' + percentile[2:]
                                endpoints[endpoint][p_key] = value
            
            # Get request rate over time if stats_history is available
            request_rate = []
            if test_results.get('stats_history_json'):
                for timestamp, history in test_results['stats_history_json'].items():
                    if 'total_rps' in history:
                        request_rate.append({
                            'timestamp': timestamp,
                            'requests_per_second': history['total_rps']
                        })
            
            # Compile API metrics
            api_metrics = {
                'total_requests': total_requests,
                'total_failures': total_failures,
                'error_rate': error_rate,
                'response_time': response_time,
                'endpoints': endpoints,
                'request_rate': request_rate
            }
        
        metrics['api_metrics'] = api_metrics
    
    # Extract calculation metrics if available
    # This might be in custom files or derived from API metrics for calculate-locate endpoint
    calculation_metrics = {}
    
    # Check if we have the calculate-locate endpoint in the API metrics
    if 'api_metrics' in metrics and 'endpoints' in metrics['api_metrics']:
        for endpoint, data in metrics['api_metrics']['endpoints'].items():
            if 'calculate-locate' in endpoint:
                # Extract calculation metrics from this endpoint
                calculation_metrics = {
                    'total_calculations': data.get('requests', 0),
                    'failed_calculations': data.get('failures', 0),
                    'error_rate': data.get('error_rate', 0),
                    'calculation_time': {
                        'median': data.get('median_response_time', 0),
                        'average': data.get('avg_response_time', 0),
                        'min': data.get('min_response_time', 0),
                        'max': data.get('max_response_time', 0)
                    }
                }
                
                # Add percentiles if available
                percentiles = {}
                for key, value in data.items():
                    if key.startswith('p') and key[1:].isdigit():
                        percentiles[key] = value
                
                if percentiles:
                    calculation_metrics['calculation_time']['percentiles'] = percentiles
                
                break
    
    # Add calculation metrics
    metrics['calculation_metrics'] = calculation_metrics
    
    # Process resource metrics if available in custom files
    resource_metrics = {}
    
    # Look for resource metrics in test_results
    resource_keys = [key for key in test_results.keys() if 'resource' in key]
    
    if resource_keys:
        # Process resource metrics from available data
        for key in resource_keys:
            if isinstance(test_results[key], pd.DataFrame):
                df = test_results[key]
                
                # Process CPU metrics
                if 'cpu_utilization' in df.columns:
                    resource_metrics['cpu'] = {
                        'utilization': {
                            'mean': df['cpu_utilization'].mean(),
                            'max': df['cpu_utilization'].max(),
                            'min': df['cpu_utilization'].min(),
                            'time_series': df[['timestamp', 'cpu_utilization']].to_dict('records')
                        }
                    }
                
                # Process memory metrics
                if 'memory_utilization' in df.columns:
                    resource_metrics['memory'] = {
                        'utilization': {
                            'mean': df['memory_utilization'].mean(),
                            'max': df['memory_utilization'].max(),
                            'min': df['memory_utilization'].min(),
                            'time_series': df[['timestamp', 'memory_utilization']].to_dict('records')
                        }
                    }
                
                # Process network metrics
                if 'network_throughput' in df.columns:
                    resource_metrics['network'] = {
                        'throughput': {
                            'mean': df['network_throughput'].mean(),
                            'max': df['network_throughput'].max(),
                            'min': df['network_throughput'].min(),
                            'time_series': df[['timestamp', 'network_throughput']].to_dict('records')
                        }
                    }
    
    # Add resource metrics
    metrics['resource_metrics'] = resource_metrics
    
    return metrics


def compare_with_thresholds(metrics, thresholds):
    """
    Compare metrics with defined performance thresholds

    Args:
        metrics (dict): Dictionary containing processed metrics
        thresholds (dict): Dictionary containing performance thresholds

    Returns:
        dict: Comparison results with pass/fail status
    """
    comparison = {
        'overall': {
            'status': 'PASS',
            'total_checks': 0,
            'passed_checks': 0,
            'failed_checks': 0
        },
        'response_time': {
            'status': 'PASS',
            'checks': []
        },
        'throughput': {
            'status': 'PASS',
            'checks': []
        },
        'error_rate': {
            'status': 'PASS',
            'checks': []
        },
        'resource_utilization': {
            'status': 'PASS',
            'checks': []
        }
    }
    
    # Extract threshold values
    rt_thresholds = thresholds.get('response_time', {})
    throughput_thresholds = thresholds.get('throughput', {})
    error_rate_thresholds = thresholds.get('error_rate', {})
    resource_thresholds = thresholds.get('resource_utilization', {})
    
    # Compare API response time metrics with thresholds
    if 'api_metrics' in metrics and metrics['api_metrics'] and 'response_time' in metrics['api_metrics']:
        response_time = metrics['api_metrics']['response_time']
        
        # Check average response time
        if 'average' in rt_thresholds and 'average' in response_time:
            threshold = rt_thresholds['average']
            actual = response_time['average']
            status = 'PASS' if actual <= threshold else 'FAIL'
            
            comparison['response_time']['checks'].append({
                'metric': 'average',
                'threshold': threshold,
                'actual': actual,
                'status': status
            })
            
            comparison['overall']['total_checks'] += 1
            if status == 'PASS':
                comparison['overall']['passed_checks'] += 1
            else:
                comparison['overall']['failed_checks'] += 1
                comparison['response_time']['status'] = 'FAIL'
        
        # Check p90 response time if available
        if 'p90' in rt_thresholds and 'percentiles' in response_time and 'p90' in response_time['percentiles']:
            threshold = rt_thresholds['p90']
            actual = response_time['percentiles']['p90']
            status = 'PASS' if actual <= threshold else 'FAIL'
            
            comparison['response_time']['checks'].append({
                'metric': 'p90',
                'threshold': threshold,
                'actual': actual,
                'status': status
            })
            
            comparison['overall']['total_checks'] += 1
            if status == 'PASS':
                comparison['overall']['passed_checks'] += 1
            else:
                comparison['overall']['failed_checks'] += 1
                comparison['response_time']['status'] = 'FAIL'
        
        # Check p95 response time if available
        if 'p95' in rt_thresholds and 'percentiles' in response_time and 'p95' in response_time['percentiles']:
            threshold = rt_thresholds['p95']
            actual = response_time['percentiles']['p95']
            status = 'PASS' if actual <= threshold else 'FAIL'
            
            comparison['response_time']['checks'].append({
                'metric': 'p95',
                'threshold': threshold,
                'actual': actual,
                'status': status
            })
            
            comparison['overall']['total_checks'] += 1
            if status == 'PASS':
                comparison['overall']['passed_checks'] += 1
            else:
                comparison['overall']['failed_checks'] += 1
                comparison['response_time']['status'] = 'FAIL'
        
        # Check p99 response time if available
        if 'p99' in rt_thresholds and 'percentiles' in response_time and 'p99' in response_time['percentiles']:
            threshold = rt_thresholds['p99']
            actual = response_time['percentiles']['p99']
            status = 'PASS' if actual <= threshold else 'FAIL'
            
            comparison['response_time']['checks'].append({
                'metric': 'p99',
                'threshold': threshold,
                'actual': actual,
                'status': status
            })
            
            comparison['overall']['total_checks'] += 1
            if status == 'PASS':
                comparison['overall']['passed_checks'] += 1
            else:
                comparison['overall']['failed_checks'] += 1
                comparison['response_time']['status'] = 'FAIL'
        
        # Check max response time
        if 'max' in rt_thresholds and 'max' in response_time:
            threshold = rt_thresholds['max']
            actual = response_time['max']
            status = 'PASS' if actual <= threshold else 'FAIL'
            
            comparison['response_time']['checks'].append({
                'metric': 'max',
                'threshold': threshold,
                'actual': actual,
                'status': status
            })
            
            comparison['overall']['total_checks'] += 1
            if status == 'PASS':
                comparison['overall']['passed_checks'] += 1
            else:
                comparison['overall']['failed_checks'] += 1
                comparison['response_time']['status'] = 'FAIL'
    
    # Compare throughput metrics with thresholds
    if 'api_metrics' in metrics and metrics['api_metrics'] and 'request_rate' in metrics['api_metrics']:
        request_rate = metrics['api_metrics']['request_rate']
        
        # Calculate average RPS
        if request_rate:
            rps_values = [item['requests_per_second'] for item in request_rate]
            avg_rps = sum(rps_values) / len(rps_values) if rps_values else 0
            
            # Check minimum throughput
            if 'min' in throughput_thresholds:
                threshold = throughput_thresholds['min']
                status = 'PASS' if avg_rps >= threshold else 'FAIL'
                
                comparison['throughput']['checks'].append({
                    'metric': 'min_throughput',
                    'threshold': threshold,
                    'actual': avg_rps,
                    'status': status
                })
                
                comparison['overall']['total_checks'] += 1
                if status == 'PASS':
                    comparison['overall']['passed_checks'] += 1
                else:
                    comparison['overall']['failed_checks'] += 1
                    comparison['throughput']['status'] = 'FAIL'
            
            # Check target throughput
            if 'target' in throughput_thresholds:
                threshold = throughput_thresholds['target']
                status = 'PASS' if avg_rps >= threshold else 'FAIL'
                
                comparison['throughput']['checks'].append({
                    'metric': 'target_throughput',
                    'threshold': threshold,
                    'actual': avg_rps,
                    'status': status
                })
                
                comparison['overall']['total_checks'] += 1
                if status == 'PASS':
                    comparison['overall']['passed_checks'] += 1
                else:
                    comparison['overall']['failed_checks'] += 1
                    comparison['throughput']['status'] = 'FAIL'
            
            # Check sustained throughput
            if 'sustained_min_duration' in throughput_thresholds and len(rps_values) > 1:
                threshold_duration = throughput_thresholds['sustained_min_duration']
                min_threshold = throughput_thresholds.get('min', 0)
                
                # Calculate the longest duration of sustained throughput above min threshold
                sustained_duration = 0
                current_duration = 0
                
                for rps in rps_values:
                    if rps >= min_threshold:
                        current_duration += 1
                    else:
                        sustained_duration = max(sustained_duration, current_duration)
                        current_duration = 0
                
                # Check final duration
                sustained_duration = max(sustained_duration, current_duration)
                
                # Convert to seconds (assuming 1 data point per second)
                sustained_seconds = sustained_duration
                status = 'PASS' if sustained_seconds >= threshold_duration else 'FAIL'
                
                comparison['throughput']['checks'].append({
                    'metric': 'sustained_throughput',
                    'threshold': f"{min_threshold} RPS for {threshold_duration}s",
                    'actual': f"{min_threshold} RPS for {sustained_seconds}s",
                    'status': status
                })
                
                comparison['overall']['total_checks'] += 1
                if status == 'PASS':
                    comparison['overall']['passed_checks'] += 1
                else:
                    comparison['overall']['failed_checks'] += 1
                    comparison['throughput']['status'] = 'FAIL'
    
    # Compare error rate metrics with thresholds
    if 'api_metrics' in metrics and metrics['api_metrics'] and 'error_rate' in metrics['api_metrics']:
        error_rate = metrics['api_metrics']['error_rate']
        
        # Check warning threshold
        if 'warning' in error_rate_thresholds:
            threshold = error_rate_thresholds['warning']
            status = 'PASS' if error_rate <= threshold else 'WARNING'
            
            comparison['error_rate']['checks'].append({
                'metric': 'warning_threshold',
                'threshold': threshold,
                'actual': error_rate,
                'status': status
            })
            
            comparison['overall']['total_checks'] += 1
            if status == 'PASS':
                comparison['overall']['passed_checks'] += 1
            else:
                # Warning doesn't count as a failure for overall status
                comparison['overall']['passed_checks'] += 1
        
        # Check critical threshold
        if 'critical' in error_rate_thresholds:
            threshold = error_rate_thresholds['critical']
            status = 'PASS' if error_rate <= threshold else 'FAIL'
            
            comparison['error_rate']['checks'].append({
                'metric': 'critical_threshold',
                'threshold': threshold,
                'actual': error_rate,
                'status': status
            })
            
            comparison['overall']['total_checks'] += 1
            if status == 'PASS':
                comparison['overall']['passed_checks'] += 1
            else:
                comparison['overall']['failed_checks'] += 1
                comparison['error_rate']['status'] = 'FAIL'
        
        # Check test failure threshold
        if 'test_failure' in error_rate_thresholds:
            threshold = error_rate_thresholds['test_failure']
            status = 'PASS' if error_rate <= threshold else 'FAIL'
            
            comparison['error_rate']['checks'].append({
                'metric': 'test_failure_threshold',
                'threshold': threshold,
                'actual': error_rate,
                'status': status
            })
            
            comparison['overall']['total_checks'] += 1
            if status == 'PASS':
                comparison['overall']['passed_checks'] += 1
            else:
                comparison['overall']['failed_checks'] += 1
                comparison['error_rate']['status'] = 'FAIL'
    
    # Compare resource utilization metrics with thresholds
    if 'resource_metrics' in metrics and metrics['resource_metrics']:
        resource_metrics = metrics['resource_metrics']
        
        # Check CPU utilization
        if 'cpu' in resource_metrics and 'cpu' in resource_thresholds:
            cpu_metrics = resource_metrics['cpu']
            cpu_thresholds = resource_thresholds['cpu']
            
            if 'utilization' in cpu_metrics and 'mean' in cpu_metrics['utilization']:
                cpu_util = cpu_metrics['utilization']['mean']
                
                # Check warning threshold
                if 'warning' in cpu_thresholds:
                    threshold = cpu_thresholds['warning']
                    status = 'PASS' if cpu_util <= threshold else 'WARNING'
                    
                    comparison['resource_utilization']['checks'].append({
                        'metric': 'cpu_warning',
                        'threshold': threshold,
                        'actual': cpu_util,
                        'status': status
                    })
                    
                    comparison['overall']['total_checks'] += 1
                    if status == 'PASS':
                        comparison['overall']['passed_checks'] += 1
                    else:
                        # Warning doesn't count as a failure for overall status
                        comparison['overall']['passed_checks'] += 1
                
                # Check critical threshold
                if 'critical' in cpu_thresholds:
                    threshold = cpu_thresholds['critical']
                    status = 'PASS' if cpu_util <= threshold else 'FAIL'
                    
                    comparison['resource_utilization']['checks'].append({
                        'metric': 'cpu_critical',
                        'threshold': threshold,
                        'actual': cpu_util,
                        'status': status
                    })
                    
                    comparison['overall']['total_checks'] += 1
                    if status == 'PASS':
                        comparison['overall']['passed_checks'] += 1
                    else:
                        comparison['overall']['failed_checks'] += 1
                        comparison['resource_utilization']['status'] = 'FAIL'
        
        # Check Memory utilization
        if 'memory' in resource_metrics and 'memory' in resource_thresholds:
            memory_metrics = resource_metrics['memory']
            memory_thresholds = resource_thresholds['memory']
            
            if 'utilization' in memory_metrics and 'mean' in memory_metrics['utilization']:
                memory_util = memory_metrics['utilization']['mean']
                
                # Check warning threshold
                if 'warning' in memory_thresholds:
                    threshold = memory_thresholds['warning']
                    status = 'PASS' if memory_util <= threshold else 'WARNING'
                    
                    comparison['resource_utilization']['checks'].append({
                        'metric': 'memory_warning',
                        'threshold': threshold,
                        'actual': memory_util,
                        'status': status
                    })
                    
                    comparison['overall']['total_checks'] += 1
                    if status == 'PASS':
                        comparison['overall']['passed_checks'] += 1
                    else:
                        # Warning doesn't count as a failure for overall status
                        comparison['overall']['passed_checks'] += 1
                
                # Check critical threshold
                if 'critical' in memory_thresholds:
                    threshold = memory_thresholds['critical']
                    status = 'PASS' if memory_util <= threshold else 'FAIL'
                    
                    comparison['resource_utilization']['checks'].append({
                        'metric': 'memory_critical',
                        'threshold': threshold,
                        'actual': memory_util,
                        'status': status
                    })
                    
                    comparison['overall']['total_checks'] += 1
                    if status == 'PASS':
                        comparison['overall']['passed_checks'] += 1
                    else:
                        comparison['overall']['failed_checks'] += 1
                        comparison['resource_utilization']['status'] = 'FAIL'
    
    # Set overall status based on failed checks
    if comparison['overall']['failed_checks'] > 0:
        comparison['overall']['status'] = 'FAIL'
    
    # Calculate pass percentage
    total_checks = comparison['overall']['total_checks']
    if total_checks > 0:
        pass_percentage = (comparison['overall']['passed_checks'] / total_checks) * 100
        comparison['overall']['pass_percentage'] = pass_percentage
    
    return comparison


def compare_with_previous(current_metrics, previous_results_path):
    """
    Compare current test results with previous results

    Args:
        current_metrics (dict): Dictionary containing current metrics
        previous_results_path (str): Path to previous results file

    Returns:
        dict: Comparison results showing changes and trends
    """
    comparison = {
        'status': 'SUCCESS',
        'has_previous_data': False,
        'api_metrics': {},
        'calculation_metrics': {},
        'resource_metrics': {}
    }
    
    # Check if previous results file exists
    if not os.path.exists(previous_results_path):
        logger.warning(f"Previous results file not found: {previous_results_path}")
        comparison['status'] = 'WARNING'
        comparison['message'] = f"Previous results file not found: {previous_results_path}"
        return comparison
    
    # Load previous results
    try:
        with open(previous_results_path, 'r') as f:
            previous_metrics = json.load(f)
        comparison['has_previous_data'] = True
    except Exception as e:
        logger.error(f"Error loading previous results: {e}")
        comparison['status'] = 'ERROR'
        comparison['message'] = f"Error loading previous results: {str(e)}"
        return comparison
    
    # Compare API metrics
    if 'api_metrics' in current_metrics and 'api_metrics' in previous_metrics:
        api_comparison = {}
        
        current_api = current_metrics['api_metrics']
        previous_api = previous_metrics['api_metrics']
        
        # Compare response time
        if 'response_time' in current_api and 'response_time' in previous_api:
            response_time_comp = {}
            
            # Compare average response time
            if 'average' in current_api['response_time'] and 'average' in previous_api['response_time']:
                current_avg = current_api['response_time']['average']
                previous_avg = previous_api['response_time']['average']
                delta = current_avg - previous_avg
                delta_percent = (delta / previous_avg * 100) if previous_avg > 0 else 0
                
                response_time_comp['average'] = {
                    'current': current_avg,
                    'previous': previous_avg,
                    'delta': delta,
                    'delta_percent': delta_percent,
                    'trend': 'IMPROVED' if delta < 0 else 'DEGRADED' if delta > 0 else 'UNCHANGED'
                }
            
            # Compare p95 response time
            if ('percentiles' in current_api['response_time'] and 
                'percentiles' in previous_api['response_time'] and
                'p95' in current_api['response_time']['percentiles'] and 
                'p95' in previous_api['response_time']['percentiles']):
                
                current_p95 = current_api['response_time']['percentiles']['p95']
                previous_p95 = previous_api['response_time']['percentiles']['p95']
                delta = current_p95 - previous_p95
                delta_percent = (delta / previous_p95 * 100) if previous_p95 > 0 else 0
                
                response_time_comp['p95'] = {
                    'current': current_p95,
                    'previous': previous_p95,
                    'delta': delta,
                    'delta_percent': delta_percent,
                    'trend': 'IMPROVED' if delta < 0 else 'DEGRADED' if delta > 0 else 'UNCHANGED'
                }
            
            api_comparison['response_time'] = response_time_comp
        
        # Compare error rate
        if 'error_rate' in current_api and 'error_rate' in previous_api:
            current_error = current_api['error_rate']
            previous_error = previous_api['error_rate']
            delta = current_error - previous_error
            delta_percent = (delta / previous_error * 100) if previous_error > 0 else 0
            
            api_comparison['error_rate'] = {
                'current': current_error,
                'previous': previous_error,
                'delta': delta,
                'delta_percent': delta_percent,
                'trend': 'IMPROVED' if delta < 0 else 'DEGRADED' if delta > 0 else 'UNCHANGED'
            }
        
        # Compare throughput
        if 'request_rate' in current_api and 'request_rate' in previous_api:
            current_rate = [item['requests_per_second'] for item in current_api['request_rate']]
            previous_rate = [item['requests_per_second'] for item in previous_api['request_rate']]
            
            current_avg_rps = sum(current_rate) / len(current_rate) if current_rate else 0
            previous_avg_rps = sum(previous_rate) / len(previous_rate) if previous_rate else 0
            
            delta = current_avg_rps - previous_avg_rps
            delta_percent = (delta / previous_avg_rps * 100) if previous_avg_rps > 0 else 0
            
            api_comparison['throughput'] = {
                'current': current_avg_rps,
                'previous': previous_avg_rps,
                'delta': delta,
                'delta_percent': delta_percent,
                'trend': 'IMPROVED' if delta > 0 else 'DEGRADED' if delta < 0 else 'UNCHANGED'
            }
        
        comparison['api_metrics'] = api_comparison
    
    # Compare calculation metrics
    if 'calculation_metrics' in current_metrics and 'calculation_metrics' in previous_metrics:
        calc_comparison = {}
        
        current_calc = current_metrics['calculation_metrics']
        previous_calc = previous_metrics['calculation_metrics']
        
        # Compare calculation time
        if 'calculation_time' in current_calc and 'calculation_time' in previous_calc:
            calc_time_comp = {}
            
            # Compare average calculation time
            if 'average' in current_calc['calculation_time'] and 'average' in previous_calc['calculation_time']:
                current_avg = current_calc['calculation_time']['average']
                previous_avg = previous_calc['calculation_time']['average']
                delta = current_avg - previous_avg
                delta_percent = (delta / previous_avg * 100) if previous_avg > 0 else 0
                
                calc_time_comp['average'] = {
                    'current': current_avg,
                    'previous': previous_avg,
                    'delta': delta,
                    'delta_percent': delta_percent,
                    'trend': 'IMPROVED' if delta < 0 else 'DEGRADED' if delta > 0 else 'UNCHANGED'
                }
            
            calc_comparison['calculation_time'] = calc_time_comp
        
        # Compare error rate
        if 'error_rate' in current_calc and 'error_rate' in previous_calc:
            current_error = current_calc['error_rate']
            previous_error = previous_calc['error_rate']
            delta = current_error - previous_error
            delta_percent = (delta / previous_error * 100) if previous_error > 0 else 0
            
            calc_comparison['error_rate'] = {
                'current': current_error,
                'previous': previous_error,
                'delta': delta,
                'delta_percent': delta_percent,
                'trend': 'IMPROVED' if delta < 0 else 'DEGRADED' if delta > 0 else 'UNCHANGED'
            }
        
        comparison['calculation_metrics'] = calc_comparison
    
    # Compare resource metrics
    if 'resource_metrics' in current_metrics and 'resource_metrics' in previous_metrics:
        resource_comparison = {}
        
        current_resource = current_metrics['resource_metrics']
        previous_resource = previous_metrics['resource_metrics']
        
        # Compare CPU utilization
        if 'cpu' in current_resource and 'cpu' in previous_resource:
            if ('utilization' in current_resource['cpu'] and 
                'utilization' in previous_resource['cpu'] and
                'mean' in current_resource['cpu']['utilization'] and 
                'mean' in previous_resource['cpu']['utilization']):
                
                current_cpu = current_resource['cpu']['utilization']['mean']
                previous_cpu = previous_resource['cpu']['utilization']['mean']
                delta = current_cpu - previous_cpu
                delta_percent = (delta / previous_cpu * 100) if previous_cpu > 0 else 0
                
                resource_comparison['cpu_utilization'] = {
                    'current': current_cpu,
                    'previous': previous_cpu,
                    'delta': delta,
                    'delta_percent': delta_percent,
                    'trend': 'IMPROVED' if delta < 0 else 'DEGRADED' if delta > 0 else 'UNCHANGED'
                }
        
        # Compare Memory utilization
        if 'memory' in current_resource and 'memory' in previous_resource:
            if ('utilization' in current_resource['memory'] and 
                'utilization' in previous_resource['memory'] and
                'mean' in current_resource['memory']['utilization'] and 
                'mean' in previous_resource['memory']['utilization']):
                
                current_mem = current_resource['memory']['utilization']['mean']
                previous_mem = previous_resource['memory']['utilization']['mean']
                delta = current_mem - previous_mem
                delta_percent = (delta / previous_mem * 100) if previous_mem > 0 else 0
                
                resource_comparison['memory_utilization'] = {
                    'current': current_mem,
                    'previous': previous_mem,
                    'delta': delta,
                    'delta_percent': delta_percent,
                    'trend': 'IMPROVED' if delta < 0 else 'DEGRADED' if delta > 0 else 'UNCHANGED'
                }
        
        comparison['resource_metrics'] = resource_comparison
    
    # Generate overall performance trend
    improved_metrics = 0
    degraded_metrics = 0
    unchanged_metrics = 0
    total_compared_metrics = 0
    
    # Count API metric trends
    for category, metrics in comparison.get('api_metrics', {}).items():
        if isinstance(metrics, dict):
            for metric, data in metrics.items():
                if isinstance(data, dict) and 'trend' in data:
                    total_compared_metrics += 1
                    if data['trend'] == 'IMPROVED':
                        improved_metrics += 1
                    elif data['trend'] == 'DEGRADED':
                        degraded_metrics += 1
                    else:
                        unchanged_metrics += 1
    
    # Count calculation metric trends
    for category, metrics in comparison.get('calculation_metrics', {}).items():
        if isinstance(metrics, dict):
            for metric, data in metrics.items():
                if isinstance(data, dict) and 'trend' in data:
                    total_compared_metrics += 1
                    if data['trend'] == 'IMPROVED':
                        improved_metrics += 1
                    elif data['trend'] == 'DEGRADED':
                        degraded_metrics += 1
                    else:
                        unchanged_metrics += 1
    
    # Count resource metric trends
    for metric, data in comparison.get('resource_metrics', {}).items():
        if isinstance(data, dict) and 'trend' in data:
            total_compared_metrics += 1
            if data['trend'] == 'IMPROVED':
                improved_metrics += 1
            elif data['trend'] == 'DEGRADED':
                degraded_metrics += 1
            else:
                unchanged_metrics += 1
    
    # Calculate overall trend
    if total_compared_metrics > 0:
        trend_score = (improved_metrics - degraded_metrics) / total_compared_metrics
        
        if trend_score > 0.1:
            overall_trend = 'IMPROVED'
        elif trend_score < -0.1:
            overall_trend = 'DEGRADED'
        else:
            overall_trend = 'UNCHANGED'
        
        comparison['overall_trend'] = {
            'trend': overall_trend,
            'improved_metrics': improved_metrics,
            'degraded_metrics': degraded_metrics,
            'unchanged_metrics': unchanged_metrics,
            'total_compared': total_compared_metrics,
            'score': trend_score
        }
    
    return comparison


def generate_summary_report(metrics, threshold_comparison, previous_comparison, output_dir):
    """
    Generate a summary report of test results and comparisons

    Args:
        metrics (dict): Dictionary containing processed metrics
        threshold_comparison (dict): Dictionary containing threshold comparison results
        previous_comparison (dict): Dictionary containing comparison with previous results
        output_dir (str): Directory to save the report

    Returns:
        str: Path to the generated summary report file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create report file path
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = os.path.join(output_dir, f'load_test_summary_{timestamp}.txt')
    
    # Generate report content
    report_lines = []
    
    # Add report header
    report_lines.extend([
        "=================================================================",
        " LOAD TEST SUMMARY REPORT - BORROW RATE & LOCATE FEE PRICING ENGINE",
        "=================================================================",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=================================================================",
        ""
    ])
    
    # Add overall results
    if 'overall' in threshold_comparison:
        overall_status = threshold_comparison['overall']['status']
        pass_percentage = threshold_comparison['overall'].get('pass_percentage', 0)
        total_checks = threshold_comparison['overall']['total_checks']
        passed_checks = threshold_comparison['overall']['passed_checks']
        failed_checks = threshold_comparison['overall']['failed_checks']
        
        report_lines.extend([
            "OVERALL RESULTS",
            "-----------------------------------------------------------------",
            f"Status: {overall_status}",
            f"Pass Rate: {pass_percentage:.1f}% ({passed_checks}/{total_checks} checks passed)",
            f"Failed Checks: {failed_checks}",
            ""
        ])
    
    # Add API metrics summary
    if 'api_metrics' in metrics and metrics['api_metrics']:
        api_metrics = metrics['api_metrics']
        
        report_lines.extend([
            "API PERFORMANCE METRICS",
            "-----------------------------------------------------------------"
        ])
        
        if 'total_requests' in api_metrics:
            report_lines.append(f"Total Requests: {api_metrics['total_requests']}")
        
        if 'error_rate' in api_metrics:
            report_lines.append(f"Error Rate: {api_metrics['error_rate']:.2f}%")
        
        if 'response_time' in api_metrics:
            rt = api_metrics['response_time']
            report_lines.append("Response Time (ms):")
            
            if 'average' in rt:
                report_lines.append(f"  Average: {rt['average']:.2f}")
            
            if 'median' in rt:
                report_lines.append(f"  Median: {rt['median']:.2f}")
            
            if 'min' in rt:
                report_lines.append(f"  Min: {rt['min']:.2f}")
            
            if 'max' in rt:
                report_lines.append(f"  Max: {rt['max']:.2f}")
            
            if 'percentiles' in rt:
                percentiles = rt['percentiles']
                if 'p50' in percentiles:
                    report_lines.append(f"  p50: {percentiles['p50']:.2f}")
                if 'p90' in percentiles:
                    report_lines.append(f"  p90: {percentiles['p90']:.2f}")
                if 'p95' in percentiles:
                    report_lines.append(f"  p95: {percentiles['p95']:.2f}")
                if 'p99' in percentiles:
                    report_lines.append(f"  p99: {percentiles['p99']:.2f}")
        
        # Add throughput metrics
        if 'request_rate' in api_metrics and api_metrics['request_rate']:
            rps_values = [item['requests_per_second'] for item in api_metrics['request_rate']]
            avg_rps = sum(rps_values) / len(rps_values) if rps_values else 0
            max_rps = max(rps_values) if rps_values else 0
            min_rps = min(rps_values) if rps_values else 0
            
            report_lines.extend([
                "",
                "Throughput:",
                f"  Average: {avg_rps:.2f} requests/second",
                f"  Peak: {max_rps:.2f} requests/second",
                f"  Min: {min_rps:.2f} requests/second"
            ])
        
        report_lines.append("")
    
    # Add calculation metrics summary
    if 'calculation_metrics' in metrics and metrics['calculation_metrics']:
        calc_metrics = metrics['calculation_metrics']
        
        report_lines.extend([
            "CALCULATION PERFORMANCE METRICS",
            "-----------------------------------------------------------------"
        ])
        
        if 'total_calculations' in calc_metrics:
            report_lines.append(f"Total Calculations: {calc_metrics['total_calculations']}")
        
        if 'error_rate' in calc_metrics:
            report_lines.append(f"Error Rate: {calc_metrics['error_rate']:.2f}%")
        
        if 'calculation_time' in calc_metrics:
            ct = calc_metrics['calculation_time']
            report_lines.append("Calculation Time (ms):")
            
            if 'average' in ct:
                report_lines.append(f"  Average: {ct['average']:.2f}")
            
            if 'median' in ct:
                report_lines.append(f"  Median: {ct['median']:.2f}")
            
            if 'min' in ct:
                report_lines.append(f"  Min: {ct['min']:.2f}")
            
            if 'max' in ct:
                report_lines.append(f"  Max: {ct['max']:.2f}")
            
            if 'percentiles' in ct:
                percentiles = ct['percentiles']
                if 'p50' in percentiles:
                    report_lines.append(f"  p50: {percentiles['p50']:.2f}")
                if 'p90' in percentiles:
                    report_lines.append(f"  p90: {percentiles['p90']:.2f}")
                if 'p95' in percentiles:
                    report_lines.append(f"  p95: {percentiles['p95']:.2f}")
                if 'p99' in percentiles:
                    report_lines.append(f"  p99: {percentiles['p99']:.2f}")
        
        report_lines.append("")
    
    # Add resource metrics summary
    if 'resource_metrics' in metrics and metrics['resource_metrics']:
        resource_metrics = metrics['resource_metrics']
        
        report_lines.extend([
            "RESOURCE UTILIZATION METRICS",
            "-----------------------------------------------------------------"
        ])
        
        if 'cpu' in resource_metrics and 'utilization' in resource_metrics['cpu']:
            cpu_util = resource_metrics['cpu']['utilization']
            report_lines.append("CPU Utilization (%):")
            
            if 'mean' in cpu_util:
                report_lines.append(f"  Average: {cpu_util['mean']:.2f}")
            
            if 'max' in cpu_util:
                report_lines.append(f"  Max: {cpu_util['max']:.2f}")
            
            if 'min' in cpu_util:
                report_lines.append(f"  Min: {cpu_util['min']:.2f}")
        
        if 'memory' in resource_metrics and 'utilization' in resource_metrics['memory']:
            mem_util = resource_metrics['memory']['utilization']
            report_lines.append("Memory Utilization (%):")
            
            if 'mean' in mem_util:
                report_lines.append(f"  Average: {mem_util['mean']:.2f}")
            
            if 'max' in mem_util:
                report_lines.append(f"  Max: {mem_util['max']:.2f}")
            
            if 'min' in mem_util:
                report_lines.append(f"  Min: {mem_util['min']:.2f}")
        
        report_lines.append("")
    
    # Add threshold comparison results
    report_lines.extend([
        "THRESHOLD COMPARISON RESULTS",
        "-----------------------------------------------------------------"
    ])
    
    # Response time thresholds
    if 'response_time' in threshold_comparison:
        rt_status = threshold_comparison['response_time']['status']
        rt_checks = threshold_comparison['response_time']['checks']
        
        report_lines.extend([
            f"Response Time: {rt_status}",
            "  Checks:"
        ])
        
        for check in rt_checks:
            report_lines.append(f"    {check['metric']}: {check['actual']:.2f} ms (Threshold: {check['threshold']} ms) - {check['status']}")
    
    # Throughput thresholds
    if 'throughput' in threshold_comparison:
        tp_status = threshold_comparison['throughput']['status']
        tp_checks = threshold_comparison['throughput']['checks']
        
        report_lines.extend([
            "",
            f"Throughput: {tp_status}",
            "  Checks:"
        ])
        
        for check in tp_checks:
            if isinstance(check['actual'], (int, float)):
                report_lines.append(f"    {check['metric']}: {check['actual']:.2f} (Threshold: {check['threshold']}) - {check['status']}")
            else:
                report_lines.append(f"    {check['metric']}: {check['actual']} (Threshold: {check['threshold']}) - {check['status']}")
    
    # Error rate thresholds
    if 'error_rate' in threshold_comparison:
        er_status = threshold_comparison['error_rate']['status']
        er_checks = threshold_comparison['error_rate']['checks']
        
        report_lines.extend([
            "",
            f"Error Rate: {er_status}",
            "  Checks:"
        ])
        
        for check in er_checks:
            report_lines.append(f"    {check['metric']}: {check['actual']:.2f}% (Threshold: {check['threshold']}%) - {check['status']}")
    
    # Resource utilization thresholds
    if 'resource_utilization' in threshold_comparison:
        ru_status = threshold_comparison['resource_utilization']['status']
        ru_checks = threshold_comparison['resource_utilization']['checks']
        
        report_lines.extend([
            "",
            f"Resource Utilization: {ru_status}",
            "  Checks:"
        ])
        
        for check in ru_checks:
            report_lines.append(f"    {check['metric']}: {check['actual']:.2f}% (Threshold: {check['threshold']}%) - {check['status']}")
    
    report_lines.append("")
    
    # Add comparison with previous results if available
    if previous_comparison and previous_comparison.get('has_previous_data', False):
        report_lines.extend([
            "COMPARISON WITH PREVIOUS RESULTS",
            "-----------------------------------------------------------------"
        ])
        
        # Add overall trend
        if 'overall_trend' in previous_comparison:
            trend = previous_comparison['overall_trend']
            report_lines.extend([
                f"Overall Trend: {trend['trend']}",
                f"  Improved Metrics: {trend['improved_metrics']}",
                f"  Degraded Metrics: {trend['degraded_metrics']}",
                f"  Unchanged Metrics: {trend['unchanged_metrics']}",
                f"  Trend Score: {trend['score']:.2f}",
                ""
            ])
        
        # API metrics comparison
        if 'api_metrics' in previous_comparison and previous_comparison['api_metrics']:
            api_comp = previous_comparison['api_metrics']
            
            report_lines.append("API Metrics Comparison:")
            
            # Response time comparison
            if 'response_time' in api_comp:
                rt_comp = api_comp['response_time']
                report_lines.append("  Response Time:")
                
                for metric, data in rt_comp.items():
                    delta_str = f"{data['delta']:.2f} ms ({data['delta_percent']:.1f}%)"
                    report_lines.append(f"    {metric}: {data['current']:.2f} ms vs {data['previous']:.2f} ms - {delta_str} - {data['trend']}")
            
            # Error rate comparison
            if 'error_rate' in api_comp:
                er_comp = api_comp['error_rate']
                delta_str = f"{er_comp['delta']:.2f}% ({er_comp['delta_percent']:.1f}%)"
                report_lines.append(f"  Error Rate: {er_comp['current']:.2f}% vs {er_comp['previous']:.2f}% - {delta_str} - {er_comp['trend']}")
            
            # Throughput comparison
            if 'throughput' in api_comp:
                tp_comp = api_comp['throughput']
                delta_str = f"{tp_comp['delta']:.2f} req/s ({tp_comp['delta_percent']:.1f}%)"
                report_lines.append(f"  Throughput: {tp_comp['current']:.2f} req/s vs {tp_comp['previous']:.2f} req/s - {delta_str} - {tp_comp['trend']}")
            
            report_lines.append("")
        
        # Calculation metrics comparison
        if 'calculation_metrics' in previous_comparison and previous_comparison['calculation_metrics']:
            calc_comp = previous_comparison['calculation_metrics']
            
            report_lines.append("Calculation Metrics Comparison:")
            
            # Calculation time comparison
            if 'calculation_time' in calc_comp:
                ct_comp = calc_comp['calculation_time']
                report_lines.append("  Calculation Time:")
                
                for metric, data in ct_comp.items():
                    delta_str = f"{data['delta']:.2f} ms ({data['delta_percent']:.1f}%)"
                    report_lines.append(f"    {metric}: {data['current']:.2f} ms vs {data['previous']:.2f} ms - {delta_str} - {data['trend']}")
            
            # Error rate comparison
            if 'error_rate' in calc_comp:
                er_comp = calc_comp['error_rate']
                delta_str = f"{er_comp['delta']:.2f}% ({er_comp['delta_percent']:.1f}%)"
                report_lines.append(f"  Error Rate: {er_comp['current']:.2f}% vs {er_comp['previous']:.2f}% - {delta_str} - {er_comp['trend']}")
            
            report_lines.append("")
        
        # Resource metrics comparison
        if 'resource_metrics' in previous_comparison and previous_comparison['resource_metrics']:
            res_comp = previous_comparison['resource_metrics']
            
            report_lines.append("Resource Metrics Comparison:")
            
            # CPU utilization comparison
            if 'cpu_utilization' in res_comp:
                cpu_comp = res_comp['cpu_utilization']
                delta_str = f"{cpu_comp['delta']:.2f}% ({cpu_comp['delta_percent']:.1f}%)"
                report_lines.append(f"  CPU Utilization: {cpu_comp['current']:.2f}% vs {cpu_comp['previous']:.2f}% - {delta_str} - {cpu_comp['trend']}")
            
            # Memory utilization comparison
            if 'memory_utilization' in res_comp:
                mem_comp = res_comp['memory_utilization']
                delta_str = f"{mem_comp['delta']:.2f}% ({mem_comp['delta_percent']:.1f}%)"
                report_lines.append(f"  Memory Utilization: {mem_comp['current']:.2f}% vs {mem_comp['previous']:.2f}% - {delta_str} - {mem_comp['trend']}")
            
            report_lines.append("")
    
    # Add recommendations based on results
    report_lines.extend([
        "RECOMMENDATIONS",
        "-----------------------------------------------------------------"
    ])
    
    # Generate recommendations based on test results
    recommendations = []
    
    # SLA compliance recommendations
    if threshold_comparison['overall']['status'] == 'FAIL':
        recommendations.append("- Address failed threshold checks to ensure compliance with SLAs.")
    
    # Response time recommendations
    if ('response_time' in threshold_comparison and 
        threshold_comparison['response_time']['status'] == 'FAIL'):
        
        recommendations.append("- Investigate response time issues:")
        
        for check in threshold_comparison['response_time']['checks']:
            if check['status'] == 'FAIL':
                recommendations.append(f"  * {check['metric']} response time ({check['actual']:.2f} ms) exceeds threshold ({check['threshold']} ms).")
        
        recommendations.append("  * Consider optimizing database queries, application code, or increasing resources.")
    
    # Throughput recommendations
    if ('throughput' in threshold_comparison and 
        threshold_comparison['throughput']['status'] == 'FAIL'):
        
        recommendations.append("- Address throughput limitations:")
        
        for check in threshold_comparison['throughput']['checks']:
            if check['status'] == 'FAIL':
                if isinstance(check['actual'], (int, float)) and isinstance(check['threshold'], (int, float)):
                    recommendations.append(f"  * {check['metric']} ({check['actual']:.2f} req/s) below target ({check['threshold']} req/s).")
                else:
                    recommendations.append(f"  * {check['metric']} check failed: {check['actual']} vs target {check['threshold']}.")
        
        recommendations.append("  * Consider scaling horizontally, optimizing resource utilization, or addressing bottlenecks.")
    
    # Error rate recommendations
    if ('error_rate' in threshold_comparison and 
        threshold_comparison['error_rate']['status'] == 'FAIL'):
        
        recommendations.append("- Reduce error rate:")
        
        for check in threshold_comparison['error_rate']['checks']:
            if check['status'] == 'FAIL':
                recommendations.append(f"  * Current error rate ({check['actual']:.2f}%) exceeds {check['metric']} ({check['threshold']}%).")
        
        recommendations.append("  * Analyze error patterns, improve error handling, and fix underlying issues.")
    
    # Resource utilization recommendations
    if ('resource_utilization' in threshold_comparison and 
        threshold_comparison['resource_utilization']['status'] == 'FAIL'):
        
        recommendations.append("- Optimize resource utilization:")
        
        for check in threshold_comparison['resource_utilization']['checks']:
            if check['status'] == 'FAIL':
                resource_type = check['metric'].split('_')[0]
                recommendations.append(f"  * {resource_type.upper()} utilization ({check['actual']:.2f}%) exceeds threshold ({check['threshold']}%).")
        
        recommendations.append("  * Consider vertical scaling, optimizing resource-intensive operations, or implementing caching.")
    
    # Add performance trend recommendations
    if previous_comparison and previous_comparison.get('has_previous_data', False):
        if 'overall_trend' in previous_comparison:
            if previous_comparison['overall_trend']['trend'] == 'DEGRADED':
                recommendations.append("- Investigate performance regression compared to previous test results.")
                
                # Check which metrics degraded
                if 'api_metrics' in previous_comparison:
                    for category, metrics in previous_comparison['api_metrics'].items():
                        if isinstance(metrics, dict):
                            for metric, data in metrics.items():
                                if isinstance(data, dict) and data.get('trend') == 'DEGRADED':
                                    if category == 'response_time':
                                        recommendations.append(f"  * {metric} response time increased by {data['delta']:.2f} ms ({data['delta_percent']:.1f}%).")
                                    elif category == 'error_rate':
                                        recommendations.append(f"  * Error rate increased by {data['delta']:.2f}% ({data['delta_percent']:.1f}%).")
                                    elif category == 'throughput':
                                        recommendations.append(f"  * Throughput decreased by {-data['delta']:.2f} req/s ({-data['delta_percent']:.1f}%).")
                
                if 'resource_metrics' in previous_comparison:
                    for metric, data in previous_comparison['resource_metrics'].items():
                        if isinstance(data, dict) and data.get('trend') == 'DEGRADED':
                            if 'cpu' in metric:
                                recommendations.append(f"  * CPU utilization increased by {data['delta']:.2f}% ({data['delta_percent']:.1f}%).")
                            elif 'memory' in metric:
                                recommendations.append(f"  * Memory utilization increased by {data['delta']:.2f}% ({data['delta_percent']:.1f}%).")
    
    # Add general recommendations if no specific issues found
    if not recommendations:
        recommendations = [
            "- System meets all performance requirements. Consider the following for further improvement:",
            "  * Implement additional caching for frequently accessed data.",
            "  * Review database indexes and query optimization.",
            "  * Monitor resource utilization trends over longer periods."
        ]
    
    # Add recommendations to report
    for recommendation in recommendations:
        report_lines.append(recommendation)
    
    # Add closing line
    report_lines.extend([
        "",
        "=================================================================",
        "END OF REPORT",
        "================================================================="
    ])
    
    # Write report to file
    with open(report_file, 'w') as f:
        f.write('\n'.join(report_lines))
    
    logger.info(f"Summary report generated: {report_file}")
    
    return report_file


def export_metrics(metrics, output_dir, formats):
    """
    Export metrics to various formats using exporters

    Args:
        metrics (dict): Dictionary containing metrics to export
        output_dir (str): Directory to save exported files
        formats (list): List of export formats (e.g., 'csv', 'json')

    Returns:
        dict: Dictionary with paths to exported files
    """
    results = {}
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Export to CSV format if specified
    if 'csv' in formats:
        try:
            exporter = CSVExporter()
            csv_results = exporter.export(metrics, output_dir)
            results['csv'] = csv_results
            logger.info(f"Metrics exported to CSV format: {len(csv_results.get('files', []))} files")
        except Exception as e:
            logger.error(f"Error exporting to CSV format: {e}")
    
    # Export to JSON format if specified
    if 'json' in formats:
        try:
            exporter = JSONExporter()
            json_results = exporter.export(metrics, output_dir)
            results['json'] = json_results
            logger.info(f"Metrics exported to JSON format: {len(json_results.get('files', {}).keys())} files")
        except Exception as e:
            logger.error(f"Error exporting to JSON format: {e}")
    
    # Generate visualizations if specified
    if 'charts' in formats:
        try:
            chart_generator = ChartGenerator()
            chart_results = chart_generator.visualize(metrics, output_dir)
            results['charts'] = chart_results
            logger.info(f"Visualizations generated: {len(chart_results)} chart categories")
        except Exception as e:
            logger.error(f"Error generating visualizations: {e}")
    
    return results


def parse_arguments():
    """
    Parse command line arguments for the script

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Analyze load test results for the Borrow Rate & Locate Fee Pricing Engine'
    )
    
    parser.add_argument(
        '--results-dir',
        required=True,
        help='Directory containing the load test results to analyze'
    )
    
    parser.add_argument(
        '--output-dir',
        default='./analysis-results',
        help='Directory to save analysis results (default: ./analysis-results)'
    )
    
    parser.add_argument(
        '--config',
        default=CONFIG_FILE,
        help=f'Path to configuration file (default: {CONFIG_FILE})'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--export-formats',
        nargs='+',
        choices=['json', 'csv', 'charts'],
        default=['json', 'csv', 'charts'],
        help='Export formats for the metrics (default: json csv charts)'
    )
    
    parser.add_argument(
        '--previous-results',
        help='Path to previous results file for comparison'
    )
    
    parser.add_argument(
        '--generate-charts',
        action='store_true',
        help='Generate charts and visualizations'
    )
    
    return parser.parse_args()


class ResultAnalyzer:
    """
    Analyzes load test results and generates reports and visualizations
    """
    
    def __init__(self, config):
        """
        Initialize the result analyzer with configuration

        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.metrics = {}
        self.threshold_comparison = {}
        self.previous_comparison = {}
    
    def analyze(self, test_results, output_dir, previous_results_path=None):
        """
        Analyze test results and generate reports

        Args:
            test_results (dict): Test results to analyze
            output_dir (str): Directory to save analysis results
            previous_results_path (str, optional): Path to previous results file for comparison

        Returns:
            dict: Analysis results including report paths and comparison results
        """
        results = {}
        
        # Process metrics from test results
        self.metrics = self.process_metrics(test_results)
        results['metrics'] = self.metrics
        
        # Compare metrics with thresholds
        self.threshold_comparison = self.compare_with_thresholds()
        results['threshold_comparison'] = self.threshold_comparison
        
        # Compare with previous results if provided
        if previous_results_path:
            self.previous_comparison = self.compare_with_previous(previous_results_path)
            results['previous_comparison'] = self.previous_comparison
        
        # Generate summary report
        report_path = self.generate_summary_report(output_dir)
        results['summary_report'] = report_path
        
        # Export metrics to all specified formats
        export_formats = self.config.get('reporting', {}).get('formats', ['json', 'csv'])
        if isinstance(export_formats, str):
            export_formats = [export_formats]
        
        export_results = self.export_metrics(output_dir, export_formats)
        results['exports'] = export_results
        
        # Generate visualizations if configured or explicitly requested
        if 'charts' in export_formats or self.config.get('reporting', {}).get('charts'):
            chart_results = self.generate_visualizations(output_dir)
            results['visualizations'] = chart_results
        
        return results
    
    def process_metrics(self, test_results):
        """
        Process raw test results into structured metrics

        Args:
            test_results (dict): Test results to process

        Returns:
            dict: Processed metrics dictionary
        """
        # Process metrics using the standalone function
        self.metrics = process_metrics(test_results)
        return self.metrics
    
    def compare_with_thresholds(self):
        """
        Compare metrics with defined performance thresholds

        Returns:
            dict: Comparison results with pass/fail status
        """
        # Get thresholds from configuration
        thresholds = self.config.get('performance_thresholds', {})
        
        # Compare metrics with thresholds using the standalone function
        self.threshold_comparison = compare_with_thresholds(self.metrics, thresholds)
        return self.threshold_comparison
    
    def compare_with_previous(self, previous_results_path):
        """
        Compare current metrics with previous test results

        Args:
            previous_results_path (str): Path to previous results file

        Returns:
            dict: Comparison results showing changes and trends
        """
        # Compare with previous results using the standalone function
        self.previous_comparison = compare_with_previous(self.metrics, previous_results_path)
        return self.previous_comparison
    
    def generate_summary_report(self, output_dir):
        """
        Generate a summary report of test results and comparisons

        Args:
            output_dir (str): Directory to save the report

        Returns:
            str: Path to the generated summary report file
        """
        # Generate summary report using the standalone function
        return generate_summary_report(
            self.metrics,
            self.threshold_comparison,
            self.previous_comparison,
            output_dir
        )
    
    def export_metrics(self, output_dir, formats):
        """
        Export metrics to various formats

        Args:
            output_dir (str): Directory to save exported files
            formats (list): List of export formats

        Returns:
            dict: Dictionary with paths to exported files
        """
        # Export metrics using the standalone function
        return export_metrics(self.metrics, output_dir, formats)
    
    def generate_visualizations(self, output_dir):
        """
        Generate charts and visualizations from metrics

        Args:
            output_dir (str): Directory to save visualizations

        Returns:
            dict: Dictionary with paths to generated visualization files
        """
        # Create visualization output directory
        vis_dir = os.path.join(output_dir, 'visualizations')
        os.makedirs(vis_dir, exist_ok=True)
        
        # Initialize chart generator with configuration
        chart_config = self.config.get('reporting', {}).get('charts', {})
        chart_generator = ChartGenerator(chart_config)
        
        # Generate visualizations
        return chart_generator.visualize(self.metrics, vis_dir)


def main():
    """
    Main function to orchestrate the analysis process

    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Set up logging
        log_level = getattr(logging, args.log_level)
        setup_logging(log_level)
        
        logger.info(f"Starting load test analysis for {args.results_dir}")
        
        # Load configuration
        config = load_config(args.config)
        if not config:
            logger.error("Failed to load configuration. Exiting.")
            return 1
        
        # Load test results
        test_results = load_test_results(args.results_dir)
        if not test_results or (not test_results.get('stats') and not test_results.get('stats_json')):
            logger.error("Failed to load test results. Exiting.")
            return 1
        
        # Create result analyzer
        analyzer = ResultAnalyzer(config)
        
        # Analyze results
        results = analyzer.analyze(
            test_results,
            args.output_dir,
            args.previous_results
        )
        
        logger.info(f"Analysis completed successfully. Report generated at {results.get('summary_report', 'unknown')}")
        
        return 0
    
    except Exception as e:
        logger.exception(f"Error during analysis: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())