#!/usr/bin/env python3
"""
Performance benchmarking script for the Borrow Rate & Locate Fee Pricing Engine.

This script measures and analyzes the performance of core calculation functions, API endpoints, 
and external service integrations to ensure the system meets its performance requirements. 
It provides detailed metrics on execution time, throughput, and resource utilization for 
different components of the system.
"""

import argparse
import time
import statistics
import concurrent.futures
import logging
from decimal import Decimal
import matplotlib.pyplot as plt  # matplotlib 3.7.0+
import numpy as np  # numpy 1.24.0+
import pandas as pd  # pandas 2.0.0+
import requests  # requests 2.28.0+

# Import the Timer utility for precise timing
from ..utils.timing import Timer

# Import calculation functions to benchmark
from ..services.calculation.borrow_rate import calculate_borrow_rate
from ..services.calculation.locate_fee import calculate_locate_fee
from ..services.calculation.volatility import calculate_volatility_adjustment
from ..services.calculation.event_risk import calculate_event_risk_adjustment

# Import settings and logging configuration
from ..config.settings import get_settings
from ..config.logging_config import configure_logging

# Import constants
from ..core.constants import TransactionFeeType

# Set up logger
logger = logging.getLogger(__name__)

# Default benchmark parameters
DEFAULT_ITERATIONS = 1000
DEFAULT_CONCURRENCY = 10
DEFAULT_WARMUP_ITERATIONS = 100

# Test data for benchmarks
TEST_TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'GME', 'AMC', 'BBBY']
TEST_POSITION_VALUES = [Decimal('10000'), Decimal('50000'), Decimal('100000'), Decimal('500000'), Decimal('1000000')]
TEST_LOAN_DAYS = [1, 7, 30, 90, 180, 365]
TEST_MARKUP_PERCENTAGES = [Decimal('0.5'), Decimal('1.0'), Decimal('2.0'), Decimal('5.0')]
TEST_FEE_AMOUNTS = [Decimal('10.0'), Decimal('25.0'), Decimal('50.0'), Decimal('100.0')]


class BenchmarkResult:
    """Class for storing and analyzing benchmark results."""
    
    def __init__(self, name, execution_times, metadata=None):
        """
        Initialize a new benchmark result.
        
        Args:
            name: Name of the benchmark
            execution_times: List of execution times in milliseconds
            metadata: Additional information about the benchmark
        """
        self.name = name
        self.execution_times = execution_times
        self.metadata = metadata or {}
        self.statistics = {}
        self.calculate_statistics()
    
    def calculate_statistics(self):
        """
        Calculates statistical metrics from execution times.
        """
        if not self.execution_times:
            logger.warning(f"No execution times available for benchmark: {self.name}")
            return
        
        # Calculate basic statistics
        self.statistics['min'] = min(self.execution_times)
        self.statistics['max'] = max(self.execution_times)
        self.statistics['mean'] = statistics.mean(self.execution_times)
        self.statistics['median'] = statistics.median(self.execution_times)
        
        # Calculate percentiles
        self.statistics['p95'] = np.percentile(self.execution_times, 95)
        self.statistics['p99'] = np.percentile(self.execution_times, 99)
        
        # Calculate standard deviation
        if len(self.execution_times) > 1:
            self.statistics['std_dev'] = statistics.stdev(self.execution_times)
        else:
            self.statistics['std_dev'] = 0
        
        # Calculate operations per second
        if self.statistics['mean'] > 0:
            self.statistics['ops_per_second'] = 1000 / self.statistics['mean']
        else:
            self.statistics['ops_per_second'] = 0
    
    def to_dict(self):
        """
        Converts the benchmark result to a dictionary.
        
        Returns:
            Dictionary representation of the benchmark result
        """
        return {
            'name': self.name,
            'statistics': self.statistics,
            'metadata': self.metadata
        }
    
    def to_dataframe(self):
        """
        Converts the benchmark result to a pandas DataFrame.
        
        Returns:
            DataFrame representation of the benchmark result
        """
        # Create a DataFrame with the execution times
        df = pd.DataFrame({
            'execution_time_ms': self.execution_times
        })
        
        # Add benchmark name and metadata as columns
        df['benchmark'] = self.name
        
        # Add metadata as columns
        for key, value in self.metadata.items():
            df[key] = value
            
        return df
    
    def print_summary(self):
        """
        Prints a summary of the benchmark results.
        """
        print(f"\n=== Benchmark Results: {self.name} ===")
        print(f"Samples: {len(self.execution_times)}")
        print(f"Min: {self.statistics['min']:.2f} ms")
        print(f"Max: {self.statistics['max']:.2f} ms")
        print(f"Mean: {self.statistics['mean']:.2f} ms")
        print(f"Median: {self.statistics['median']:.2f} ms")
        print(f"95th Percentile: {self.statistics['p95']:.2f} ms")
        print(f"99th Percentile: {self.statistics['p99']:.2f} ms")
        print(f"Standard Deviation: {self.statistics['std_dev']:.2f} ms")
        print(f"Operations per Second: {self.statistics['ops_per_second']:.2f}")
        
        # Print metadata if available
        if self.metadata:
            print("\nMetadata:")
            for key, value in self.metadata.items():
                print(f"  {key}: {value}")


def parse_arguments():
    """
    Parses command-line arguments for configuring the benchmark run.
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Benchmark script for the Borrow Rate & Locate Fee Pricing Engine"
    )
    
    # Add argument for benchmark type
    parser.add_argument(
        '--type', 
        choices=['calculation', 'api', 'all'], 
        default='all',
        help='Type of benchmark to run (calculation, api, or all)'
    )
    
    # Add argument for number of iterations
    parser.add_argument(
        '--iterations', 
        type=int, 
        default=DEFAULT_ITERATIONS,
        help=f'Number of iterations for each benchmark (default: {DEFAULT_ITERATIONS})'
    )
    
    # Add argument for concurrency level
    parser.add_argument(
        '--concurrency', 
        type=int, 
        default=DEFAULT_CONCURRENCY,
        help=f'Level of concurrency for benchmarks (default: {DEFAULT_CONCURRENCY})'
    )
    
    # Add argument for warmup iterations
    parser.add_argument(
        '--warmup', 
        type=int, 
        default=DEFAULT_WARMUP_ITERATIONS,
        help=f'Number of warmup iterations before benchmarking (default: {DEFAULT_WARMUP_ITERATIONS})'
    )
    
    # Add argument for output format
    parser.add_argument(
        '--output', 
        choices=['console', 'csv', 'json'], 
        default='console',
        help='Output format for benchmark results (default: console)'
    )
    
    # Add argument for output file path
    parser.add_argument(
        '--output-file', 
        type=str, 
        help='File path for benchmark results output (required for csv/json output)'
    )
    
    # Add argument for visualization
    parser.add_argument(
        '--visualize', 
        action='store_true',
        help='Generate visualizations of benchmark results'
    )
    
    # Parse the arguments
    return parser.parse_args()


def setup_benchmark_environment():
    """
    Prepares the environment for benchmarking.
    """
    # Configure logging
    configure_logging()
    logger.info("Setting up benchmark environment")
    
    # Get settings
    settings = get_settings()
    logger.info(f"Using settings for environment: {settings.environment}")
    
    # Log benchmark environment details
    logger.info("Benchmark environment ready")


def benchmark_function(func, params, iterations):
    """
    Benchmarks a single function with given parameters.
    
    Args:
        func: Function to benchmark
        params: Dictionary of parameters to pass to the function
        iterations: Number of iterations to run
        
    Returns:
        dict: Benchmark results including execution times and statistics
    """
    logger.info(f"Benchmarking function {func.__name__} for {iterations} iterations")
    
    # Initialize results list
    execution_times = []
    timer = Timer()
    
    # Run the benchmark
    for i in range(iterations):
        timer.start()
        result = func(**params)
        timer.stop()
        execution_times.append(timer.elapsed_ms())
        
    # Create BenchmarkResult object to calculate statistics
    benchmark_result = BenchmarkResult(
        name=func.__name__,
        execution_times=execution_times,
        metadata=params
    )
    
    # Log completion
    logger.info(f"Benchmark complete for {func.__name__}: Mean: {benchmark_result.statistics['mean']:.2f} ms, "
                f"P95: {benchmark_result.statistics['p95']:.2f} ms")
    
    return benchmark_result


def benchmark_concurrent(func, param_sets, concurrency, iterations_per_set):
    """
    Benchmarks a function with concurrent execution.
    
    Args:
        func: Function to benchmark
        param_sets: List of parameter dictionaries for different function calls
        concurrency: Maximum number of concurrent executions
        iterations_per_set: Number of iterations for each parameter set
        
    Returns:
        dict: Benchmark results including execution times and throughput
    """
    logger.info(f"Running concurrent benchmark for {func.__name__} with concurrency {concurrency}")
    
    all_execution_times = []
    total_timer = Timer()
    
    # Create a function that will be executed by the ThreadPoolExecutor
    def run_benchmark(params):
        result_times = []
        for _ in range(iterations_per_set):
            timer = Timer()
            timer.start()
            func(**params)
            timer.stop()
            result_times.append(timer.elapsed_ms())
        return result_times
    
    # Start the timer for overall execution
    total_timer.start()
    
    # Use ThreadPoolExecutor for concurrent execution
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        # Submit all benchmark tasks
        future_to_params = {
            executor.submit(run_benchmark, params): params
            for params in param_sets
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_params):
            params = future_to_params[future]
            try:
                result_times = future.result()
                all_execution_times.extend(result_times)
            except Exception as e:
                logger.error(f"Error in concurrent benchmark: {str(e)}")
    
    # Stop the timer for overall execution
    total_elapsed = total_timer.stop()
    
    # Calculate throughput
    total_operations = len(param_sets) * iterations_per_set
    throughput = total_operations / total_elapsed if total_elapsed > 0 else 0
    
    # Create BenchmarkResult
    benchmark_result = BenchmarkResult(
        name=f"{func.__name__}_concurrent",
        execution_times=all_execution_times,
        metadata={
            'concurrency': concurrency,
            'param_sets': len(param_sets),
            'iterations_per_set': iterations_per_set,
            'total_operations': total_operations,
            'total_elapsed_seconds': total_elapsed,
            'throughput_ops_per_second': throughput * 1000  # Convert to ops/second
        }
    )
    
    logger.info(f"Concurrent benchmark complete: Throughput: {throughput * 1000:.2f} ops/sec, "
                f"Mean: {benchmark_result.statistics['mean']:.2f} ms")
    
    return benchmark_result


def benchmark_borrow_rate_calculation(iterations, concurrency):
    """
    Benchmarks the borrow rate calculation function.
    
    Args:
        iterations: Number of iterations for each parameter set
        concurrency: Level of concurrency for the benchmark
        
    Returns:
        dict: Benchmark results for borrow rate calculation
    """
    logger.info("Starting borrow rate calculation benchmark")
    
    # Create parameter sets with different tickers
    param_sets = [{'ticker': ticker} for ticker in TEST_TICKERS]
    
    # Perform warmup iterations
    logger.info(f"Performing {DEFAULT_WARMUP_ITERATIONS} warmup iterations")
    for params in param_sets:
        for _ in range(DEFAULT_WARMUP_ITERATIONS // len(param_sets)):
            calculate_borrow_rate(**params)
    
    # Run the actual benchmark
    result = benchmark_concurrent(
        calculate_borrow_rate,
        param_sets,
        concurrency,
        iterations // len(param_sets)
    )
    
    logger.info("Borrow rate calculation benchmark complete")
    return result


def benchmark_locate_fee_calculation(iterations, concurrency):
    """
    Benchmarks the locate fee calculation function.
    
    Args:
        iterations: Number of iterations for each parameter set
        concurrency: Level of concurrency for the benchmark
        
    Returns:
        dict: Benchmark results for locate fee calculation
    """
    logger.info("Starting locate fee calculation benchmark")
    
    # Create parameter sets with different combinations
    param_sets = []
    for ticker in TEST_TICKERS[:3]:  # Limit to first 3 tickers to keep the number of combinations reasonable
        for position_value in TEST_POSITION_VALUES[:3]:
            for loan_days in TEST_LOAN_DAYS[:3]:
                for markup_percentage in TEST_MARKUP_PERCENTAGES[:2]:
                    for fee_type in [TransactionFeeType.FLAT, TransactionFeeType.PERCENTAGE]:
                        fee_amount = TEST_FEE_AMOUNTS[0] if fee_type == TransactionFeeType.FLAT else TEST_MARKUP_PERCENTAGES[0]
                        params = {
                            'ticker': ticker,
                            'position_value': position_value,
                            'loan_days': loan_days,
                            'markup_percentage': markup_percentage,
                            'fee_type': fee_type,
                            'fee_amount': fee_amount
                        }
                        param_sets.append(params)
    
    # Limit the number of parameter sets if too many
    if len(param_sets) > 100:
        import random
        random.shuffle(param_sets)
        param_sets = param_sets[:100]
    
    # Perform warmup iterations
    logger.info(f"Performing {DEFAULT_WARMUP_ITERATIONS} warmup iterations")
    for params in param_sets[:min(10, len(param_sets))]:
        for _ in range(DEFAULT_WARMUP_ITERATIONS // min(10, len(param_sets))):
            calculate_locate_fee(**params)
    
    # Run the actual benchmark
    result = benchmark_concurrent(
        calculate_locate_fee,
        param_sets,
        concurrency,
        max(1, iterations // len(param_sets))
    )
    
    logger.info("Locate fee calculation benchmark complete")
    return result


def benchmark_volatility_adjustment(iterations, concurrency):
    """
    Benchmarks the volatility adjustment calculation function.
    
    Args:
        iterations: Number of iterations for each parameter set
        concurrency: Level of concurrency for the benchmark
        
    Returns:
        dict: Benchmark results for volatility adjustment calculation
    """
    logger.info("Starting volatility adjustment benchmark")
    
    # Create parameter sets with different volatility indices
    param_sets = []
    for volatility_index in [Decimal('10'), Decimal('20'), Decimal('30'), Decimal('40')]:
        params = {
            'volatility_index': volatility_index
        }
        param_sets.append(params)
    
    # Perform warmup iterations
    logger.info(f"Performing {DEFAULT_WARMUP_ITERATIONS} warmup iterations")
    for params in param_sets:
        for _ in range(DEFAULT_WARMUP_ITERATIONS // len(param_sets)):
            calculate_volatility_adjustment(**params)
    
    # Run the actual benchmark
    result = benchmark_concurrent(
        calculate_volatility_adjustment,
        param_sets,
        concurrency,
        iterations // len(param_sets)
    )
    
    logger.info("Volatility adjustment benchmark complete")
    return result


def benchmark_event_risk_adjustment(iterations, concurrency):
    """
    Benchmarks the event risk adjustment calculation function.
    
    Args:
        iterations: Number of iterations for each parameter set
        concurrency: Level of concurrency for the benchmark
        
    Returns:
        dict: Benchmark results for event risk adjustment calculation
    """
    logger.info("Starting event risk adjustment benchmark")
    
    # Create parameter sets with different risk factors
    param_sets = []
    for risk_factor in range(11):  # 0-10 inclusive
        params = {
            'risk_factor': risk_factor
        }
        param_sets.append(params)
    
    # Perform warmup iterations
    logger.info(f"Performing {DEFAULT_WARMUP_ITERATIONS} warmup iterations")
    for params in param_sets:
        for _ in range(DEFAULT_WARMUP_ITERATIONS // len(param_sets)):
            calculate_event_risk_adjustment(**params)
    
    # Run the actual benchmark
    result = benchmark_concurrent(
        calculate_event_risk_adjustment,
        param_sets,
        concurrency,
        iterations // len(param_sets)
    )
    
    logger.info("Event risk adjustment benchmark complete")
    return result


def benchmark_api_endpoint(endpoint, params, method='get', iterations=100, concurrency=10):
    """
    Benchmarks a specific API endpoint.
    
    Args:
        endpoint: API endpoint URL
        params: Parameters to include in the request
        method: HTTP method to use (get or post)
        iterations: Number of iterations to run
        concurrency: Level of concurrency for the benchmark
        
    Returns:
        dict: Benchmark results for API endpoint
    """
    logger.info(f"Starting benchmark for API endpoint: {endpoint}")
    
    # Create a session for connection reuse
    session = requests.Session()
    
    # Get base URL from settings
    settings = get_settings()
    base_url = f"http://localhost:8000"  # Default for local development
    
    # Function to make an API request
    def make_request(request_params):
        url = f"{base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method.lower() == 'get':
                return session.get(url, params=request_params, headers=headers)
            elif method.lower() == 'post':
                return session.post(url, json=request_params, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except Exception as e:
            logger.error(f"Error making API request: {str(e)}")
            raise
    
    # Create parameter sets for the benchmark
    param_sets = []
    if isinstance(params, list):
        param_sets = params
    else:
        param_sets = [params]
    
    # Define a wrapper function for the benchmark
    def api_request_function(request_params):
        response = make_request(request_params)
        if response.status_code != 200:
            logger.warning(f"API request failed: {response.status_code} - {response.text}")
        return response
    
    # Perform warmup iterations
    logger.info(f"Performing {min(DEFAULT_WARMUP_ITERATIONS, 10)} warmup iterations")
    for params in param_sets[:min(len(param_sets), 3)]:
        for _ in range(min(DEFAULT_WARMUP_ITERATIONS, 10) // min(len(param_sets), 3)):
            try:
                api_request_function(params)
            except Exception:
                logger.warning("Warmup request failed, continuing with benchmark")
    
    # Run the benchmark
    result = benchmark_concurrent(
        api_request_function,
        param_sets,
        concurrency,
        iterations // len(param_sets)
    )
    
    logger.info(f"API endpoint benchmark complete for {endpoint}")
    return result


def benchmark_calculate_endpoint(iterations, concurrency):
    """
    Benchmarks the calculate-locate API endpoint.
    
    Args:
        iterations: Number of iterations for each parameter set
        concurrency: Level of concurrency for the benchmark
        
    Returns:
        dict: Benchmark results for calculate-locate endpoint
    """
    logger.info("Starting calculate-locate endpoint benchmark")
    
    # Create parameter sets with different combinations
    param_sets = []
    for ticker in TEST_TICKERS[:3]:
        for position_value in TEST_POSITION_VALUES[:2]:
            for loan_days in TEST_LOAN_DAYS[:2]:
                params = {
                    'ticker': ticker,
                    'position_value': float(position_value),
                    'loan_days': loan_days,
                    'client_id': 'benchmark_client'
                }
                param_sets.append(params)
    
    # Run the benchmark
    result = benchmark_api_endpoint(
        endpoint='/api/v1/calculate-locate',
        params=param_sets,
        method='post',
        iterations=iterations,
        concurrency=concurrency
    )
    
    logger.info("Calculate-locate endpoint benchmark complete")
    return result


def benchmark_rates_endpoint(iterations, concurrency):
    """
    Benchmarks the rates API endpoint.
    
    Args:
        iterations: Number of iterations for each parameter set
        concurrency: Level of concurrency for the benchmark
        
    Returns:
        dict: Benchmark results for rates endpoint
    """
    logger.info("Starting rates endpoint benchmark")
    
    # Create parameter sets with different tickers
    param_sets = []
    for ticker in TEST_TICKERS:
        endpoint = f"/api/v1/rates/{ticker}"
        param_sets.append({})
    
    # Run the benchmark
    result = benchmark_api_endpoint(
        endpoint=f"/api/v1/rates/{TEST_TICKERS[0]}",  # This will be overridden
        params=param_sets,
        method='get',
        iterations=iterations,
        concurrency=concurrency
    )
    
    logger.info("Rates endpoint benchmark complete")
    return result


def visualize_results(results, output_path):
    """
    Creates visualizations of benchmark results.
    
    Args:
        results: Dictionary of benchmark results
        output_path: Path to save visualizations
    """
    logger.info("Generating visualizations of benchmark results")
    
    # Convert results to DataFrame
    dfs = []
    for name, result in results.items():
        df = pd.DataFrame({
            'benchmark': name,
            'execution_time_ms': result.execution_times
        })
        dfs.append(df)
    
    df = pd.concat(dfs, ignore_index=True)
    
    # Create plots directory if it doesn't exist
    import os
    plots_dir = os.path.join(output_path, 'plots')
    os.makedirs(plots_dir, exist_ok=True)
    
    # Plot 1: Bar chart of mean execution times
    plt.figure(figsize=(12, 6))
    mean_times = df.groupby('benchmark')['execution_time_ms'].mean()
    mean_times.plot(kind='bar')
    plt.title('Mean Execution Time by Benchmark')
    plt.ylabel('Time (ms)')
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'mean_execution_times.png'))
    
    # Plot 2: Box plot of execution time distributions
    plt.figure(figsize=(12, 6))
    df.boxplot(column='execution_time_ms', by='benchmark', vert=False, figsize=(12, 6))
    plt.title('Execution Time Distribution by Benchmark')
    plt.xlabel('Time (ms)')
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'execution_time_distributions.png'))
    
    # Plot 3: Line chart of p95 latencies
    plt.figure(figsize=(12, 6))
    p95_times = df.groupby('benchmark')['execution_time_ms'].apply(lambda x: np.percentile(x, 95))
    p95_times.plot(kind='bar')
    plt.title('95th Percentile Execution Time by Benchmark')
    plt.ylabel('Time (ms)')
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'p95_execution_times.png'))
    
    # Plot 4: Histogram of execution times for each benchmark
    for name in df['benchmark'].unique():
        plt.figure(figsize=(10, 5))
        subset = df[df['benchmark'] == name]
        subset['execution_time_ms'].hist(bins=50)
        plt.title(f'Execution Time Distribution - {name}')
        plt.xlabel('Time (ms)')
        plt.ylabel('Frequency')
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, f'histogram_{name}.png'))
    
    logger.info(f"Visualizations saved to {plots_dir}")


def export_results(results, format, output_path):
    """
    Exports benchmark results in the specified format.
    
    Args:
        results: Dictionary of benchmark results
        format: Output format (console, csv, json)
        output_path: File path for benchmark results output (if csv/json)
    """
    logger.info(f"Exporting benchmark results in {format} format")
    
    if format == 'console':
        # Print results to console
        for name, result in results.items():
            result.print_summary()
    
    elif format == 'csv':
        # Export as CSV
        dfs = []
        for name, result in results.items():
            df = result.to_dataframe()
            dfs.append(df)
        
        if dfs:
            combined_df = pd.concat(dfs, ignore_index=True)
            combined_df.to_csv(output_path, index=False)
            logger.info(f"CSV results saved to {output_path}")
        else:
            logger.warning("No results to export")
    
    elif format == 'json':
        # Export as JSON
        import json
        
        # Convert results to dictionary
        results_dict = {name: result.to_dict() for name, result in results.items()}
        
        with open(output_path, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        logger.info(f"JSON results saved to {output_path}")
    
    else:
        logger.error(f"Unsupported output format: {format}")


def run_all_benchmarks(iterations, concurrency):
    """
    Runs all benchmark tests.
    
    Args:
        iterations: Number of iterations for each benchmark
        concurrency: Level of concurrency for benchmarks
        
    Returns:
        dict: Combined results from all benchmarks
    """
    logger.info("Running all benchmarks")
    
    results = {}
    
    # Run calculation benchmarks
    results['borrow_rate'] = benchmark_borrow_rate_calculation(iterations, concurrency)
    results['locate_fee'] = benchmark_locate_fee_calculation(iterations, concurrency)
    results['volatility_adjustment'] = benchmark_volatility_adjustment(iterations, concurrency)
    results['event_risk_adjustment'] = benchmark_event_risk_adjustment(iterations, concurrency)
    
    # Run API benchmarks
    try:
        results['calculate_endpoint'] = benchmark_calculate_endpoint(iterations, concurrency)
        results['rates_endpoint'] = benchmark_rates_endpoint(iterations, concurrency)
    except Exception as e:
        logger.error(f"Error running API benchmarks: {str(e)}")
        logger.warning("API benchmarks skipped. Make sure the API server is running.")
    
    logger.info("All benchmarks complete")
    return results


def main():
    """
    Main entry point for the benchmark script.
    
    Returns:
        int: Exit code (0 for success)
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    # Set up the benchmark environment
    setup_benchmark_environment()
    
    logger.info(f"Starting benchmark with iterations={args.iterations}, concurrency={args.concurrency}")
    
    # Run the appropriate benchmarks based on the type argument
    results = {}
    if args.type == 'calculation' or args.type == 'all':
        # Run calculation benchmarks
        results['borrow_rate'] = benchmark_borrow_rate_calculation(args.iterations, args.concurrency)
        results['locate_fee'] = benchmark_locate_fee_calculation(args.iterations, args.concurrency)
        results['volatility_adjustment'] = benchmark_volatility_adjustment(args.iterations, args.concurrency)
        results['event_risk_adjustment'] = benchmark_event_risk_adjustment(args.iterations, args.concurrency)
    
    if args.type == 'api' or args.type == 'all':
        # Run API benchmarks
        try:
            results['calculate_endpoint'] = benchmark_calculate_endpoint(args.iterations, args.concurrency)
            results['rates_endpoint'] = benchmark_rates_endpoint(args.iterations, args.concurrency)
        except Exception as e:
            logger.error(f"Error running API benchmarks: {str(e)}")
            logger.warning("API benchmarks skipped. Make sure the API server is running.")
    
    # Export the results
    if args.output == 'console':
        export_results(results, 'console', None)
    else:
        if not args.output_file:
            logger.error(f"Output file path required for {args.output} format")
            return 1
        
        export_results(results, args.output, args.output_file)
    
    # Generate visualizations if requested
    if args.visualize:
        if not args.output_file:
            logger.error("Output file path required for visualizations")
            return 1
        
        import os
        output_dir = os.path.dirname(args.output_file) or '.'
        visualize_results(results, output_dir)
    
    logger.info("Benchmark complete")
    return 0


if __name__ == "__main__":
    exit(main())