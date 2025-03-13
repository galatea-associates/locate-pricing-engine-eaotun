#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Error handling - display error message and exit on error
trap 'echo "Error occurred at line $LINENO"; exit 1' ERR

# Define global variables
SCRIPT_DIR=$(dirname "${BASH_SOURCE[0]}")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/../../..")
TEST_DIR="$PROJECT_ROOT/src/test"
PERFORMANCE_TEST_DIR="$TEST_DIR/performance_tests"
LOAD_TEST_DIR="$TEST_DIR/load_testing"
METRICS_DIR="$TEST_DIR/metrics"
REPORT_DIR="$TEST_DIR/reports"
DEFAULT_TARGET_RPS="1000"
DEFAULT_CONCURRENT_USERS="100"
DEFAULT_TEST_DURATION="300"
DEFAULT_TEST_MARKERS="performance"
DEFAULT_PARALLEL_WORKERS="4"
DEFAULT_TIMEOUT="600"

# Source setup_test_env.sh for environment setup and cleanup functions
source "$SCRIPT_DIR/setup_test_env.sh" # src_path: src/test/scripts/setup_test_env.sh - Import environment setup and cleanup functions

# Source run_mock_servers.sh for starting and configuring mock servers
source "$SCRIPT_DIR/run_mock_servers.sh" # src_path: src/test/scripts/run_mock_servers.sh - Import mock server management functions

# Function to print a formatted header
print_header() {
    local str="$1"
    echo "========================================================"
    echo "    ${str^^}"
    echo "========================================================"
}

# Function to check if required dependencies are installed
check_dependencies() {
    print_header "Checking dependencies"

    if ! command -v pytest &> /dev/null; then # package_version: 7.4.0+ - Check if pytest is installed
        echo "Error: pytest is not installed or not in PATH"
        return 2
    fi

    if ! command -v locust &> /dev/null; then # package_version: 2.15.0+ - Check if locust is installed
        echo "Error: locust is not installed or not in PATH"
        return 2
    fi

    if ! command -v jq &> /dev/null; then # package_version: latest - Check if jq is installed
        echo "Error: jq is not installed or not in PATH"
        return 2
    fi

    echo "All dependencies are available"
    return 0
}

# Function to run API latency performance tests
run_api_latency_tests() {
    local parallel_workers=${1:-$DEFAULT_PARALLEL_WORKERS}
    local timeout=${2:-$DEFAULT_TIMEOUT}
    local output_format=${3:-json}

    print_header "Running API Latency Tests"

    cd "$PERFORMANCE_TEST_DIR"

    local pytest_cmd="pytest test_api_latency.py -n $parallel_workers --timeout=$timeout --output-format=$output_format"

    echo "Executing command: $pytest_cmd"
    local output=$(eval "$pytest_cmd")
    local exit_code=$?

    echo "$output"

    # Parse test results and metrics using jq
    # Add parsing logic here if needed

    return $exit_code
}

# Function to run calculation speed performance tests
run_calculation_speed_tests() {
    local parallel_workers=${1:-$DEFAULT_PARALLEL_WORKERS}
    local timeout=${2:-$DEFAULT_TIMEOUT}
    local output_format=${3:-json}

    print_header "Running Calculation Speed Tests"

    cd "$PERFORMANCE_TEST_DIR"

    local pytest_cmd="pytest test_calculation_speed.py -n $parallel_workers --timeout=$timeout --output-format=$output_format"

    echo "Executing command: $pytest_cmd"
    local output=$(eval "$pytest_cmd")
    local exit_code=$?

    echo "$output"

    # Parse test results and metrics using jq
    # Add parsing logic here if needed

    return $exit_code
}

# Function to run throughput performance tests
run_throughput_tests() {
    local target_rps=${1:-$DEFAULT_TARGET_RPS}
    local timeout=${2:-$DEFAULT_TIMEOUT}
    local output_format=${3:-json}

    print_header "Running Throughput Tests"

    cd "$PERFORMANCE_TEST_DIR"

    local pytest_cmd="pytest test_throughput.py --timeout=$timeout --output-format=$output_format"
    export TARGET_RPS="$target_rps"

    echo "Executing command: $pytest_cmd"
    local output=$(eval "$pytest_cmd")
    local exit_code=$?

    echo "$output"

    # Parse test results and metrics using jq
    # Add parsing logic here if needed

    return $exit_code
}

# Function to run load tests using Locust
run_load_tests() {
    local target_rps=${1:-$DEFAULT_TARGET_RPS}
    local concurrent_users=${2:-$DEFAULT_CONCURRENT_USERS}
    local duration=${3:-$DEFAULT_TEST_DURATION}
    local scenario=${4:-mixed_workload}

    print_header "Running Load Tests"

    cd "$LOAD_TEST_DIR"

    local locust_cmd="locust -f locustfile.py --headless --users=$concurrent_users --spawn-rate=$concurrent_users --run-time=${duration}s --test-type=$scenario"

    export TARGET_RPS="$target_rps"
    export CONCURRENT_USERS="$concurrent_users"
    export TEST_DURATION="$duration"
    export TEST_SCENARIO="$scenario"

    echo "Executing command: $locust_cmd"
    local output=$(eval "$locust_cmd")
    local exit_code=$?

    echo "$output"

    # Capture and process test results
    # Add processing logic here if needed

    return $exit_code
}

# Function to run stress tests with high concurrency
run_stress_tests() {
    local target_rps=${1:-$DEFAULT_TARGET_RPS}
    local duration=${2:-$DEFAULT_TEST_DURATION}

    print_header "Running Stress Tests"

    # Set high concurrency (2000+ requests/second)
    local concurrent_users=2500

    # Call run_load_tests with stress test parameters
    run_load_tests "$target_rps" "$concurrent_users" "$duration"

    return $?
}

# Function to run endurance tests with sustained load
run_endurance_tests() {
    local target_rps=${1:-$DEFAULT_TARGET_RPS}
    local duration=${2:-$DEFAULT_TEST_DURATION}

    print_header "Running Endurance Tests"

    # Set moderate concurrency with extended duration
    local concurrent_users=100
    local duration=86400 # 24 hours

    # Call run_load_tests with endurance test parameters
    run_load_tests "$target_rps" "$concurrent_users" "$duration"

    return $?
}

# Function to run spike tests with sudden traffic increase
run_spike_tests() {
    local target_rps=${1:-$DEFAULT_TARGET_RPS}
    local duration=${2:-$DEFAULT_TEST_DURATION}

    print_header "Running Spike Tests"

    # Run baseline load for initial period
    local baseline_duration=300
    local baseline_rps=800
    local baseline_users=100
    run_load_tests "$baseline_rps" "$baseline_users" "$baseline_duration"

    # Suddenly increase to high concurrency (3000 requests/second)
    local spike_duration=60
    local spike_rps=3000
    local spike_users=300
    run_load_tests "$spike_rps" "$spike_users" "$spike_duration"

    # Measure system response to traffic spike
    # Add measurement logic here if needed

    return $?
}

# Function to run tests to measure resource utilization
run_resource_utilization_tests() {
    local target_rps=${1:-$DEFAULT_TARGET_RPS}
    local duration=${2:-$DEFAULT_TEST_DURATION}

    print_header "Running Resource Utilization Tests"

    cd "$PERFORMANCE_TEST_DIR"

    local pytest_cmd="pytest test_resource_utilization.py --timeout=$timeout --output-format=$output_format"
    export TARGET_RPS="$target_rps"
    export TEST_DURATION="$duration"

    echo "Executing command: $pytest_cmd"
    local output=$(eval "$pytest_cmd")
    local exit_code=$?

    echo "$output"

    # Parse test results and metrics using jq
    # Add parsing logic here if needed

    return $exit_code
}

# Function to run resilience tests under load
run_resilience_tests() {
    local target_rps=${1:-$DEFAULT_TARGET_RPS}
    local duration=${2:-$DEFAULT_TEST_DURATION}

    print_header "Running Resilience Tests Under Load"

    cd "$PERFORMANCE_TEST_DIR"

    local pytest_cmd="pytest test_resilience_under_load.py --timeout=$timeout --output-format=$output_format"
    export TARGET_RPS="$target_rps"
    export TEST_DURATION="$duration"

    echo "Executing command: $pytest_cmd"
    local output=$(eval "$pytest_cmd")
    local exit_code=$?

    echo "$output"

    # Parse test results and metrics using jq
    # Add parsing logic here if needed

    return $exit_code
}

# Function to generate test reports from collected metrics
generate_reports() {
    local metrics_dir=${1:-$METRICS_DIR}
    local report_dir=${2:-$REPORT_DIR}
    local report_format=${3:-html}

    print_header "Generating Test Reports"

    # Check if metrics directory exists and contains data
    if [ ! -d "$metrics_dir" ] || [ "$(ls -A $metrics_dir)" ]; then
        echo "Error: Metrics directory does not exist or is empty: $metrics_dir"
        return 5
    fi

    # Create report directory if it doesn't exist
    if [ ! -d "$report_dir" ]; then
        echo "Creating report directory: $report_dir"
        mkdir -p "$report_dir"
    fi

    # Execute generate_test_report.py with appropriate parameters
    local report_cmd="python $SCRIPT_DIR/generate_test_report.py --input-path=$metrics_dir --output-dir=$report_dir --formats=$report_format"

    echo "Executing command: $report_cmd"
    local output=$(eval "$report_cmd")
    local exit_code=$?

    echo "$output"

    # Generate performance charts and visualizations
    # Add visualization logic here if needed

    return $exit_code
}

# Function to display usage information for the script
show_usage() {
    echo "Usage: $0 [options]"
    echo
    echo "This script automates the execution of performance tests for the Borrow Rate & Locate Fee Pricing Engine."
    echo
    echo "Options:"
    echo "  --all                   Run all performance test types (default)"
    echo "  --api-latency           Run API latency tests only"
    echo "  --calculation-speed     Run calculation speed tests only"
    echo "  --throughput            Run throughput tests only"
    echo "  --load                  Run load tests only"
    echo "  --stress                Run stress tests only"
    echo "  --endurance             Run endurance tests only"
    echo "  --spike                 Run spike tests only"
    echo "  --resource-utilization  Run resource utilization tests only"
    echo "  --resilience            Run resilience under load tests only"
    echo "  --target-rps <value>    Target requests per second for load tests (default: $DEFAULT_TARGET_RPS)"
    echo "  --concurrent-users <value> Number of concurrent users for load tests (default: $DEFAULT_CONCURRENT_USERS)"
    echo "  --duration <value>      Test duration in seconds (default: $DEFAULT_TEST_DURATION)"
    echo "  --scenario <value>      Load test scenario (borrow_rate, calculate_fee, mixed_workload) (default: mixed_workload)"
    echo "  --parallel <value>      Number of parallel test workers (default: $DEFAULT_PARALLEL_WORKERS)"
    echo "  --timeout <value>       Test execution timeout in seconds (default: $DEFAULT_TIMEOUT)"
    echo "  --skip-setup            Skip test environment setup"
    echo "  --skip-cleanup          Skip test environment cleanup"
    echo "  --skip-reports          Skip test report generation"
    echo "  --output-format <value> Test output format (json, xml, html) (default: json)"
    echo "  --report-format <value> Report format (html, pdf, dashboard) (default: html)"
    echo "  --help                  Show usage information"
    echo
    echo "Examples:"
    echo "  $0 --all"
    echo "  $0 --load --target-rps 2000 --duration 600"
    echo "  $0 --api-latency --parallel 8"
    echo "  $0 --skip-setup --skip-cleanup --skip-reports"
}

# Main function
main() {
    local run_all=true
    local run_api_latency=false
    local run_calculation_speed=false
    local run_throughput=false
    local run_load=false
    local run_stress=false
    local run_endurance=false
    local run_spike=false
    local run_resource_utilization=false
    local run_resilience=false
    local target_rps="$DEFAULT_TARGET_RPS"
    local concurrent_users="$DEFAULT_CONCURRENT_USERS"
    local duration="$DEFAULT_TEST_DURATION"
    local scenario="mixed_workload"
    local parallel_workers="$DEFAULT_PARALLEL_WORKERS"
    local timeout="$DEFAULT_TIMEOUT"
    local skip_setup=false
    local skip_cleanup=false
    local skip_reports=false
    local output_format="json"
    local report_format="html"

    # Process command line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --all)
                run_all=true
                shift
                ;;
            --api-latency)
                run_all=false
                run_api_latency=true
                shift
                ;;
            --calculation-speed)
                run_all=false
                run_calculation_speed=true
                shift
                ;;
            --throughput)
                run_all=false
                run_throughput=true
                shift
                ;;
            --load)
                run_all=false
                run_load=true
                shift
                ;;
            --stress)
                run_all=false
                run_stress=true
                shift
                ;;
            --endurance)
                run_all=false
                run_endurance=true
                shift
                ;;
            --spike)
                run_all=false
                run_spike=true
                shift
                ;;
            --resource-utilization)
                run_all=false
                run_resource_utilization=true
                shift
                ;;
            --resilience)
                run_all=false
                run_resilience=true
                shift
                ;;
            --target-rps)
                target_rps="$2"
                shift 2
                ;;
            --concurrent-users)
                concurrent_users="$2"
                shift 2
                ;;
            --duration)
                duration="$2"
                shift 2
                ;;
            --scenario)
                scenario="$2"
                shift 2
                ;;
            --parallel)
                parallel_workers="$2"
                shift 2
                ;;
            --timeout)
                timeout="$2"
                shift 2
                ;;
            --skip-setup)
                skip_setup=true
                shift
                ;;
            --skip-cleanup)
                skip_cleanup=true
                shift
                ;;
            --skip-reports)
                skip_reports=true
                shift
                ;;
            --output-format)
                output_format="$2"
                shift 2
                ;;
            --report-format)
                report_format="$2"
                shift 2
                ;;
            --help)
                show_usage
                return 0
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                return 1
                ;;
        esac
    done

    # Check dependencies
    if ! check_dependencies; then
        return 2
    fi

    # Set up test environment if not skipped
    if [ "$skip_setup" = false ]; then
        setup_test_environment
        local setup_exit_code=$?
        if [ $setup_exit_code -ne 0 ]; then
            echo "Error: Test environment setup failed"
            return 3
        fi
    fi

    # Run tests based on specified test type or all tests
    local test_exit_code=0
    if [ "$run_all" = true ] || [ "$run_api_latency" = true ]; then
        run_api_latency_tests "$parallel_workers" "$timeout" "$output_format"
        test_exit_code=$?
        if [ $test_exit_code -ne 0 ]; then
            echo "Error: API latency tests failed"
        fi
    fi

    if [ "$run_all" = true ] || [ "$run_calculation_speed" = true ]; then
        run_calculation_speed_tests "$parallel_workers" "$timeout" "$output_format"
        test_exit_code=$?
        if [ $test_exit_code -ne 0 ]; then
            echo "Error: Calculation speed tests failed"
        fi
    fi

    if [ "$run_all" = true ] || [ "$run_throughput" = true ]; then
        run_throughput_tests "$target_rps" "$timeout" "$output_format"
        test_exit_code=$?
        if [ $test_exit_code -ne 0 ]; then
            echo "Error: Throughput tests failed"
        fi
    fi

    if [ "$run_all" = true ] || [ "$run_load" = true ]; then
        run_load_tests "$target_rps" "$concurrent_users" "$duration" "$scenario"
        test_exit_code=$?
        if [ $test_exit_code -ne 0 ]; then
            echo "Error: Load tests failed"
        fi
    fi

    if [ "$run_all" = true ] || [ "$run_stress" = true ]; then
        run_stress_tests "$target_rps" "$duration"
        test_exit_code=$?
        if [ $test_exit_code -ne 0 ]; then
            echo "Error: Stress tests failed"
        fi
    fi

    if [ "$run_all" = true ] || [ "$run_endurance" = true ]; then
        run_endurance_tests "$target_rps" "$duration"
        test_exit_code=$?
        if [ $test_exit_code -ne 0 ]; then
            echo "Error: Endurance tests failed"
        fi
    fi

    if [ "$run_all" = true ] || [ "$run_spike" = true ]; then
        run_spike_tests "$target_rps" "$duration"
        test_exit_code=$?
        if [ $test_exit_code -ne 0 ]; then
            echo "Error: Spike tests failed"
        fi
    fi

    if [ "$run_all" = true ] || [ "$run_resource_utilization" = true ]; then
        run_resource_utilization_tests "$target_rps" "$duration"
        test_exit_code=$?
        if [ $test_exit_code -ne 0 ]; then
            echo "Error: Resource utilization tests failed"
        fi
    fi

    if [ "$run_all" = true ] || [ "$run_resilience" = true ]; then
        run_resilience_tests "$target_rps" "$duration"
        test_exit_code=$?
        if [ $test_exit_code -ne 0 ]; then
            echo "Error: Resilience tests failed"
        fi
    fi

    # Generate reports if not skipped
    if [ "$skip_reports" = false ]; then
        generate_reports "$METRICS_DIR" "$REPORT_DIR" "$report_format"
        local report_exit_code=$?
        if [ $report_exit_code -ne 0 ]; then
            echo "Error: Report generation failed"
            test_exit_code=$report_exit_code
        fi
    fi

    # Clean up test environment if not skipped
    if [ "$skip_cleanup" = false ]; then
        cleanup_environment
        local cleanup_exit_code=$?
        if [ $cleanup_exit_code -ne 0 ]; then
            echo "Error: Test environment cleanup failed"
            test_exit_code=$cleanup_exit_code
        fi
    fi

    # Return appropriate exit code
    return $test_exit_code
}

# Execute main function with all arguments
main "$@"
exit $?