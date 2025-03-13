#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Error handling - display error message and exit on error
trap 'echo "Error occurred at line $LINENO"; exit 1' ERR

# Define global variables
SCRIPT_DIR=$(dirname "${BASH_SOURCE[0]}")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/../../..")
TEST_DIR="$PROJECT_ROOT/src/test"
REPORT_DIR="$TEST_DIR/reports"
CONSOLIDATED_REPORT_FILE="$REPORT_DIR/all_tests_report.json"
HTML_REPORT_FILE="$REPORT_DIR/all_tests_report.html"
DEFAULT_FAILURE_RATE="0"
DEFAULT_DELAY_RATE="0"

# Source setup_test_env.sh to use its functions
# shellcheck source=/dev/null
source "$SCRIPT_DIR/setup_test_env.sh"

# Source run_integration_tests.sh to use its functions
# shellcheck source=/dev/null
source "$SCRIPT_DIR/run_integration_tests.sh"

# Source run_e2e_tests.sh to use its functions
# shellcheck source=/dev/null
source "$SCRIPT_DIR/run_e2e_tests.sh"

# Source run_performance_tests.sh to use its functions
# shellcheck source=/dev/null
source "$SCRIPT_DIR/run_performance_tests.sh"

# Source run_security_tests.sh to use its functions
# shellcheck source=/dev/null
source "$SCRIPT_DIR/run_security_tests.sh"

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

    if ! command -v jq &> /dev/null; then # package_name: jq, package_version: latest
        echo "Error: jq is not installed or not in PATH"
        return 1
    fi

    # Check if all test script files exist and are executable
    if [ ! -x "$SCRIPT_DIR/run_integration_tests.sh" ] || [ ! -x "$SCRIPT_DIR/run_e2e_tests.sh" ] || \
       [ ! -x "$SCRIPT_DIR/run_performance_tests.sh" ] || [ ! -x "$SCRIPT_DIR/run_security_tests.sh" ]; then
        echo "Error: One or more test script files are missing or not executable"
        return 1
    fi

    echo "All dependencies are available"
    return 0
}

# Function to set up the test environment
setup_environment() {
    local failure_rate="${1:-$DEFAULT_FAILURE_RATE}"
    local delay_rate="${2:-$DEFAULT_DELAY_RATE}"

    print_header "Setting up test environment"

    # Source setup_test_env.sh to use its functions
    # Call setup_test_environment with failure_rate and delay_rate parameters
    if ! setup_test_environment "$failure_rate" "$delay_rate"; then
        echo "Error: Failed to set up test environment"
        return 2
    fi

    # Create report directory if it doesn't exist
    if [ ! -d "$REPORT_DIR" ]; then
        echo "Creating report directory: $REPORT_DIR"
        mkdir -p "$REPORT_DIR"
    fi

    echo "Test environment setup completed successfully"
    return 0
}

# Function to run the integration test suite
run_integration_tests() {
    local verbose="${1:-false}"

    print_header "Running integration tests"

    # Build command with appropriate options
    local pytest_cmd="$SCRIPT_DIR/run_integration_tests.sh"

    # Add --verbose flag if verbose is true
    if [ "$verbose" = true ]; then
        pytest_cmd="$pytest_cmd --verbose"
    fi

    # Execute run_integration_tests.sh script
    echo "Executing command: $pytest_cmd"
    eval "$pytest_cmd"
    local exit_code=$?

    # Capture exit code and test results
    local test_results=$(echo "$output" | jq -c .)

    # Return exit code
    return $exit_code
}

# Function to run the end-to-end test suite
run_e2e_tests() {
    local verbose="${1:-false}"

    print_header "Running end-to-end tests"

    # Build command with appropriate options
    local pytest_cmd="$SCRIPT_DIR/run_e2e_tests.sh"

    # Add --verbose flag if verbose is true
    if [ "$verbose" = true ]; then
        pytest_cmd="$pytest_cmd --verbose"
    fi

    # Execute run_e2e_tests.sh script
    echo "Executing command: $pytest_cmd"
    eval "$pytest_cmd"
    local exit_code=$?

    # Capture exit code and test results
    local test_results=$(echo "$output" | jq -c .)

    # Return exit code
    return $exit_code
}

# Function to run the performance test suite
run_performance_tests() {
    local verbose="${1:-false}"
    local quick_mode="${2:-false}"

    print_header "Running performance tests"

    # Build command with appropriate options
    local pytest_cmd="$SCRIPT_DIR/run_performance_tests.sh"

    # Add --verbose flag if verbose is true
    if [ "$verbose" = true ]; then
        pytest_cmd="$pytest_cmd --verbose"
    fi

    # Add --quick-mode flag if quick_mode is true to run shorter tests
    if [ "$quick_mode" = true ]; then
        pytest_cmd="$pytest_cmd --quick-mode"
    fi

    # Execute run_performance_tests.sh script
    echo "Executing command: $pytest_cmd"
    eval "$pytest_cmd"
    local exit_code=$?

    # Capture exit code and test results
    local test_results=$(echo "$output" | jq -c .)

    # Return exit code
    return $exit_code
}

# Function to run the security test suite
run_security_tests() {
    local verbose="${1:-false}"
    local skip_zap_scan="${2:-false}"

    print_header "Running security tests"

    # Build command with appropriate options
    local pytest_cmd="$SCRIPT_DIR/run_security_tests.sh"

    # Add --verbose flag if verbose is true
    if [ "$verbose" = true ]; then
        pytest_cmd="$pytest_cmd --verbose"
    fi

    # Add --skip-zap-scan flag if skip_zap_scan is true
    if [ "$skip_zap_scan" = true ]; then
        pytest_cmd="$pytest_cmd --skip-zap-scan"
    fi

    # Execute run_security_tests.sh script
    echo "Executing command: $pytest_cmd"
    eval "$pytest_cmd"
    local exit_code=$?

    # Capture exit code and test results
    local test_results=$(echo "$output" | jq -c .)

    # Return exit code
    return $exit_code
}

# Function to generate a consolidated report from all test results
generate_consolidated_report() {
    print_header "Generating consolidated report"

    # Collect all individual test reports
    local integration_report="$REPORT_DIR/integration_test_report.json"
    local e2e_report="$REPORT_DIR/e2e_report.json"
    local performance_report="$REPORT_DIR/performance_test_report.json"
    local security_report="$REPORT_DIR/security_test_report.json"

    # Merge reports into a consolidated JSON report
    echo "Merging reports into a consolidated JSON report"
    # Add merging logic here

    # Generate HTML report from consolidated JSON
    echo "Generating HTML report from consolidated JSON"
    # Add HTML report generation logic here

    # Print report location
    echo "Consolidated report location: $CONSOLIDATED_REPORT_FILE"
    echo "HTML report location: $HTML_REPORT_FILE"

    # Return 0 if successful
    return 0
}

# Function to clean up the test environment
cleanup_environment() {
    print_header "Cleaning up environment"

    # Source setup_test_env.sh to use its functions
    # Call cleanup_environment function
    if ! cleanup_environment; then
        echo "Error: Failed to clean up test environment"
        return 8
    fi

    echo "Environment cleanup completed"
    return 0
}

# Function to display usage information
show_usage() {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --skip-integration     Skip integration tests"
    echo "  --skip-e2e             Skip end-to-end tests"
    echo "  --skip-performance     Skip performance tests"
    echo "  --skip-security        Skip security tests"
    echo "  --quick-performance    Run performance tests in quick mode with reduced duration"
    echo "  --skip-zap-scan        Skip OWASP ZAP scan in security tests"
    echo "  --failure-rate <rate>  Percentage of mock API requests that should fail (0-100)"
    echo "  --delay-rate <rate>    Percentage of mock API requests that should be delayed (0-100)"
    echo "  --no-setup             Skip environment setup (assumes environment is already set up)"
    echo "  --no-cleanup           Skip environment cleanup after tests"
    echo "  --no-report            Skip consolidated report generation"
    echo "  --verbose              Enable verbose output for all tests"
    echo "  --help                 Show usage information"
    echo
    echo "Examples:"
    echo "  $0 --skip-integration --skip-e2e"
    echo "  $0 --failure-rate 20 --delay-rate 10"
    echo "  $0 --no-setup --no-cleanup --no-report"
    echo "  $0 --verbose"
}

# Main function
main() {
    local skip_integration=false
    local skip_e2e=false
    local skip_performance=false
    local skip_security=false
    local quick_performance=false
    local skip_zap_scan=false
    local failure_rate="$DEFAULT_FAILURE_RATE"
    local delay_rate="$DEFAULT_DELAY_RATE"
    local no_setup=false
    local no_cleanup=false
    local no_report=false
    local verbose=false

    # Process command line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --skip-integration)
                skip_integration=true
                shift
                ;;
            --skip-e2e)
                skip_e2e=true
                shift
                ;;
            --skip-performance)
                skip_performance=true
                shift
                ;;
            --skip-security)
                skip_security=true
                shift
                ;;
            --quick-performance)
                quick_performance=true
                shift
                ;;
            --skip-zap-scan)
                skip_zap_scan=true
                shift
                ;;
            --failure-rate)
                failure_rate="$2"
                shift 2
                ;;
            --delay-rate)
                delay_rate="$2"
                shift 2
                ;;
            --no-setup)
                no_setup=true
                shift
                ;;
            --no-cleanup)
                no_cleanup=true
                shift
                ;;
            --no-report)
                no_report=true
                shift
                ;;
            --verbose)
                verbose=true
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
    if ! check_dependencies; then
        return 1
    fi

    # Set up test environment if --no-setup is not specified
    if [ "$no_setup" = false ]; then
        if ! setup_environment "$failure_rate" "$delay_rate"; then
            local setup_exit_code=$?
            echo "Error: Environment setup failed with exit code $setup_exit_code"
            return 2
        fi
    fi

    # Run integration tests if --skip-integration is not specified
    if [ "$skip_integration" = false ]; then
        if ! run_integration_tests "$verbose"; then
            local integration_exit_code=$?
            echo "Error: Integration tests failed with exit code $integration_exit_code"
            exit_code=3
        fi
    fi

    # Run end-to-end tests if --skip-e2e is not specified
    if [ "$skip_e2e" = false ]; then
        if ! run_e2e_tests "$verbose"; then
            local e2e_exit_code=$?
            echo "Error: End-to-end tests failed with exit code $e2e_exit_code"
            exit_code=4
        fi
    fi

    # Run performance tests if --skip-performance is not specified
    if [ "$skip_performance" = false ]; then
        if ! run_performance_tests "$verbose" "$quick_performance"; then
            local performance_exit_code=$?
            echo "Error: Performance tests failed with exit code $performance_exit_code"
            exit_code=5
        fi
    fi

    # Run security tests if --skip-security is not specified
    if [ "$skip_security" = false ]; then
        if ! run_security_tests "$verbose" "$skip_zap_scan"; then
            local security_exit_code=$?
            echo "Error: Security tests failed with exit code $security_exit_code"
            exit_code=6
        fi
    fi

    # Generate consolidated report if --no-report is not specified
    if [ "$no_report" = false ]; then
        if ! generate_consolidated_report; then
            echo "Error: Report generation failed"
            exit_code=7
        fi
    fi

    # Clean up test environment if --no-cleanup is not specified
    if [ "$no_cleanup" = false ]; then
        if ! cleanup_environment; then
            echo "Error: Failed to clean up test environment"
            exit_code=8
        fi
    fi

    # Return appropriate exit code based on test results
    return $exit_code
}

# Execute main function with all arguments
main "$@"
exit $?