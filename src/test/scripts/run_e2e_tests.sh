#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Error handling - display error message and exit on error
trap 'echo "Error occurred at line $LINENO"; exit 1' ERR

# Define global variables
SCRIPT_DIR=$(dirname "${BASH_SOURCE[0]}")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/../../..")
TEST_DIR="$PROJECT_ROOT/src/test"
E2E_TEST_DIR="$TEST_DIR/e2e_tests"
METRICS_DIR="$TEST_DIR/metrics"
REPORT_DIR="$TEST_DIR/reports"
DEFAULT_FAILURE_RATE="0"
DEFAULT_DELAY_RATE="0"
DEFAULT_TEST_MARKERS="e2e"
DEFAULT_PARALLEL_WORKERS="4"
DEFAULT_TIMEOUT="300"

# Import helper scripts
source "$SCRIPT_DIR/setup_test_env.sh" # version: N/A
source "$SCRIPT_DIR/run_mock_servers.sh" # version: N/A

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

    if ! command -v pytest &> /dev/null; then # version: latest
        echo "Error: pytest is not installed or not in PATH"
        return 2
    fi

    if ! command -v jq &> /dev/null; then # version: latest
        echo "Error: jq is not installed or not in PATH"
        return 2
    fi

    echo "All dependencies are available"
    return 0
}

# Function to run the end-to-end tests with specified parameters
run_e2e_tests() {
    local test_markers="$1"
    local parallel_workers="$2"
    local timeout="$3"
    local output_format="$4"

    print_header "Running E2E tests"

    # Change directory to E2E test directory
    cd "$E2E_TEST_DIR"

    # Build pytest command with specified parameters
    local pytest_cmd="pytest"

    # Add markers, parallel workers, timeout, and output format
    pytest_cmd="$pytest_cmd -m \"$test_markers\" -n $parallel_workers --timeout=$timeout --$output_format=$REPORT_DIR/e2e_report.$output_format"

    # Execute pytest command and capture output
    echo "Executing pytest command: $pytest_cmd"
    pytest_cmd="$pytest_cmd --cov=$PROJECT_ROOT/src --cov-report term-missing --cov-report xml:$REPORT_DIR/coverage.xml"
    eval "$pytest_cmd"
    local exit_code=$?

    # Change directory back to the script directory
    cd "$SCRIPT_DIR"

    # Return exit code from pytest execution
    return $exit_code
}

# Function to run a specific test scenario with custom configuration
run_specific_test_scenario() {
    local scenario_name="$1"
    local failure_rate="$2"
    local delay_rate="$3"

    print_header "Running specific test scenario: $scenario_name"

    # Configure mock servers with specified failure and delay rates
    configure_mock_servers "$failure_rate" "$delay_rate"
    local configure_exit_code=$?
    if [ $configure_exit_code -ne 0 ]; then
        echo "Error: Failed to configure mock servers"
        return $configure_exit_code
    fi

    # Build pytest command targeting the specific scenario
    local pytest_cmd="pytest -m \"$scenario_name\""

    # Execute pytest command and capture output
    echo "Executing pytest command: $pytest_cmd"
    eval "$pytest_cmd"
    local exit_code=$?

    # Return exit code from pytest execution
    return $exit_code
}

# Function to run tests for normal market conditions
run_normal_market_tests() {
    print_header "Running normal market condition tests"

    # Configure mock servers with normal market conditions
    configure_mock_servers "$DEFAULT_FAILURE_RATE" "$DEFAULT_DELAY_RATE"
    local configure_exit_code=$?
    if [ $configure_exit_code -ne 0 ]; then
        echo "Error: Failed to configure mock servers"
        return $configure_exit_code
    fi

    # Run tests with normal_market_scenario marker
    run_specific_test_scenario "normal_market_scenario" "$DEFAULT_FAILURE_RATE" "$DEFAULT_DELAY_RATE"
    local exit_code=$?

    # Return exit code from test execution
    return $exit_code
}

# Function to run tests for high volatility market conditions
run_high_volatility_tests() {
    print_header "Running high volatility market condition tests"

    # Configure mock servers with high volatility conditions
    configure_mock_servers "$DEFAULT_FAILURE_RATE" "$DEFAULT_DELAY_RATE"
    local configure_exit_code=$?
    if [ $configure_exit_code -ne 0 ]; then
        echo "Error: Failed to configure mock servers"
        return $configure_exit_code
    fi

    # Run tests with high_volatility_scenario marker
    run_specific_test_scenario "high_volatility_scenario" "$DEFAULT_FAILURE_RATE" "$DEFAULT_DELAY_RATE"
    local exit_code=$?

    # Return exit code from test execution
    return $exit_code
}

# Function to run tests for corporate event scenarios
run_corporate_event_tests() {
    print_header "Running corporate event scenario tests"

    # Configure mock servers with corporate event conditions
    configure_mock_servers "$DEFAULT_FAILURE_RATE" "$DEFAULT_DELAY_RATE"
    local configure_exit_code=$?
    if [ $configure_exit_code -ne 0 ]; then
        echo "Error: Failed to configure mock servers"
        return $configure_exit_code
    fi

    # Run tests with corporate_event_scenario marker
    run_specific_test_scenario "corporate_event_scenario" "$DEFAULT_FAILURE_RATE" "$DEFAULT_DELAY_RATE"
    local exit_code=$?

    # Return exit code from test execution
    return $exit_code
}

# Function to run tests for hard-to-borrow securities
run_hard_to_borrow_tests() {
    print_header "Running hard-to-borrow securities tests"

    # Configure mock servers with hard-to-borrow conditions
    configure_mock_servers "$DEFAULT_FAILURE_RATE" "$DEFAULT_DELAY_RATE"
    local configure_exit_code=$?
    if [ $configure_exit_code -ne 0 ]; then
        echo "Error: Failed to configure mock servers"
        return $configure_exit_code
    fi

    # Run tests with hard_to_borrow_scenario marker
    run_specific_test_scenario "hard_to_borrow_scenario" "$DEFAULT_FAILURE_RATE" "$DEFAULT_DELAY_RATE"
    local exit_code=$?

    # Return exit code from test execution
    return $exit_code
}

# Function to run tests with simulated API failures
run_api_failure_tests() {
    local failure_rate="$1"

    print_header "Running tests with simulated API failures (failure_rate=$failure_rate%)"

    # Configure mock servers with specified failure rate
    configure_mock_servers "$failure_rate" "$DEFAULT_DELAY_RATE"
    local configure_exit_code=$?
    if [ $configure_exit_code -ne 0 ]; then
        echo "Error: Failed to configure mock servers"
        return $configure_exit_code
    fi

    # Run tests with fallback_mechanism marker
    local pytest_cmd="pytest -m fallback_mechanism"
    echo "Executing pytest command: $pytest_cmd"
    eval "$pytest_cmd"
    local exit_code=$?

    # Return exit code from test execution
    return $exit_code
}

# Function to run tests with simulated API delays
run_api_delay_tests() {
    local delay_rate="$1"

    print_header "Running tests with simulated API delays (delay_rate=$delay_rate%)"

    # Configure mock servers with specified delay rate
    configure_mock_servers "$DEFAULT_FAILURE_RATE" "$delay_rate"
    local configure_exit_code=$?
    if [ $configure_exit_code -ne 0 ]; then
        echo "Error: Failed to configure mock servers"
        return $configure_exit_code
    fi

    # Run tests with timeout_handling marker
    local pytest_cmd="pytest -m timeout_handling"
    echo "Executing pytest command: $pytest_cmd"
    eval "$pytest_cmd"
    local exit_code=$?

    # Return exit code from test execution
    return $exit_code
}

# Function to generate test reports from collected metrics
generate_reports() {
    local metrics_dir="$1"
    local report_dir="$2"

    print_header "Generating test reports"

    # Check if metrics directory exists and contains data
    if [ ! -d "$metrics_dir" ] || [ "$(ls -A $metrics_dir)" ]; then
        echo "Error: Metrics directory does not exist or is empty: $metrics_dir"
        return 1
    fi

    # Create report directory if it doesn't exist
    if [ ! -d "$report_dir" ]; then
        echo "Creating report directory: $report_dir"
        mkdir -p "$report_dir"
    fi

    # Execute generate_test_report.py with appropriate parameters
    echo "Executing generate_test_report.py --input-path=$metrics_dir --output-dir=$report_dir"
    python "$SCRIPT_DIR/generate_test_report.py" --input-path="$metrics_dir" --output-dir="$report_dir"
    local exit_code=$?

    # Return exit code from report generation
    return $exit_code
}

# Function to display usage information
show_usage() {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --all               Run all test scenarios (default)"
    echo "  --normal-market     Run normal market condition tests only"
    echo "  --high-volatility   Run high volatility market condition tests only"
    echo "  --corporate-event   Run corporate event scenario tests only"
    echo "  --hard-to-borrow   Run hard-to-borrow securities tests only"
    echo "  --api-failure       Run tests with simulated API failures"
    echo "  --api-delay         Run tests with simulated API delays"
    echo "  --failure-rate RATE Percentage of mock API requests that should fail (0-100)"
    echo "  --delay-rate RATE   Percentage of mock API requests that should be delayed (0-100)"
    echo "  --parallel NUM      Number of parallel test workers"
    echo "  --timeout SEC       Test execution timeout in seconds"
    echo "  --skip-setup        Skip test environment setup"
    echo "  --skip-cleanup      Skip test environment cleanup"
    echo "  --skip-reports      Skip test report generation"
    echo "  --output-format FMT Test output format (json, xml, html)"
    echo "  --help              Show this help message"
    echo
    echo "Examples:"
    echo "  $0 --all"
    echo "  $0 --normal-market"
    echo "  $0 --api-failure --failure-rate=20"
    echo "  $0 --skip-setup --skip-cleanup"
}

# Main function
main() {
    local run_all=true
    local run_normal_market=false
    local run_high_volatility=false
    local run_corporate_event=false
    local run_hard_to_borrow=false
    local run_api_failure=false
    local run_api_delay=false
    local failure_rate="$DEFAULT_FAILURE_RATE"
    local delay_rate="$DEFAULT_DELAY_RATE"
    local parallel_workers="$DEFAULT_PARALLEL_WORKERS"
    local timeout="$DEFAULT_TIMEOUT"
    local skip_setup=false
    local skip_cleanup=false
    local skip_reports=false
    local output_format="$DEFAULT_OUTPUT_FORMAT"

    # Process command line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --all)
                run_all=true
                run_normal_market=false
                run_high_volatility=false
                run_corporate_event=false
                run_hard_to_borrow=false
                run_api_failure=false
                run_api_delay=false
                shift
                ;;
            --normal-market)
                run_all=false
                run_normal_market=true
                shift
                ;;
            --high-volatility)
                run_all=false
                run_high_volatility=true
                shift
                ;;
            --corporate-event)
                run_all=false
                run_corporate_event=true
                shift
                ;;
            --hard-to-borrow)
                run_all=false
                run_hard_to_borrow=true
                shift
                ;;
            --api-failure)
                run_all=false
                run_api_failure=true
                shift
                ;;
            --api-delay)
                run_all=false
                run_api_delay=true
                shift
                ;;
            --failure-rate=*)
                failure_rate="${1#*=}"
                shift
                ;;
            --delay-rate=*)
                delay_rate="${1#*=}"
                shift
                ;;
            --parallel=*)
                parallel_workers="${1#*=}"
                shift
                ;;
            --timeout=*)
                timeout="${1#*=}"
                shift
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
            --output-format=*)
                output_format="${1#*=}"
                shift
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
    local check_exit_code=0
    if ! check_dependencies; then
        check_exit_code=$?
        echo "Error: Missing dependencies"
        return $check_exit_code
    fi

    # Set up test environment if not skipped
    if [ "$skip_setup" = false ]; then
        setup_test_environment "$failure_rate" "$delay_rate"
        local setup_exit_code=$?
        if [ $setup_exit_code -ne 0 ]; then
            echo "Error: Failed to setup test environment"
            return $setup_exit_code
        fi
    fi

    # Run tests based on specified scenario or all scenarios
    local test_exit_code=0
    if $run_all; then
        run_e2e_tests "$DEFAULT_TEST_MARKERS" "$parallel_workers" "$timeout" "$output_format"
        test_exit_code=$?
    elif $run_normal_market; then
        run_normal_market_tests
        test_exit_code=$?
    elif $run_high_volatility; then
        run_high_volatility_tests
        test_exit_code=$?
    elif $run_corporate_event; then
        run_corporate_event_tests
        test_exit_code=$?
    elif $run_hard_to_borrow; then
        run_hard_to_borrow_tests
        test_exit_code=$?
    elif $run_api_failure; then
        run_api_failure_tests "$failure_rate"
        test_exit_code=$?
    elif $run_api_delay; then
        run_api_delay_tests "$delay_rate"
        test_exit_code=$?
    fi

    # Generate reports if not skipped
    local report_exit_code=0
    if [ "$skip_reports" = false ]; then
        generate_reports "$METRICS_DIR" "$REPORT_DIR"
        report_exit_code=$?
    fi

    # Clean up test environment if not skipped
    if [ "$skip_cleanup" = false ]; then
        cleanup_environment
        local cleanup_exit_code=$?
    fi

    # Determine overall exit code
    local exit_code=0
    if [ $check_exit_code -ne 0 ]; then
        exit_code=$check_exit_code
    elif [ $setup_exit_code -ne 0 ]; then
        exit_code=$setup_exit_code
    elif [ $test_exit_code -ne 0 ]; then
        exit_code=$test_exit_code
    elif [ $report_exit_code -ne 0 ]; then
        exit_code=$report_exit_code
    elif [ $cleanup_exit_code -ne 0 ]; then
        exit_code=$cleanup_exit_code
    fi

    # Return appropriate exit code
    return $exit_code
}

# Execute main function with all script arguments
main "$@"
exit $?