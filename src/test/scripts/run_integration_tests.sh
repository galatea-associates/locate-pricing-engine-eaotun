#!/bin/bash
#
# run_integration_tests.sh - Script to run integration tests for the Borrow Rate & Locate Fee Pricing Engine.
# This script automates the execution of integration tests, sets up the test environment,
# and generates a summary of the test results.

# Exit immediately if a command exits with a non-zero status
set -e

# Error handling - display error message and exit on error
trap 'echo "Error occurred at line $LINENO"; exit 1' ERR

# Global variables
SCRIPT_DIR=$(dirname "${BASH_SOURCE[0]}")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/../../..")
TEST_DIR="$PROJECT_ROOT/src/test"
INTEGRATION_TEST_DIR="$TEST_DIR/integration_tests"
TEST_REPORT_DIR="$TEST_DIR/reports"
TEST_REPORT_FILE="$TEST_REPORT_DIR/integration_test_report.xml"
TEST_JSON_REPORT_FILE="$TEST_REPORT_DIR/integration_test_report.json"
DEFAULT_FAILURE_RATE="0"
DEFAULT_DELAY_RATE="0"
DEFAULT_TEST_PATTERN="test_*.py"

# Import internal scripts
# shellcheck source=/dev/null
source "$SCRIPT_DIR/setup_test_env.sh" # Import setup_test_environment and cleanup_environment functions
# shellcheck source=/dev/null
source "$SCRIPT_DIR/run_mock_servers.sh" # Import start_mock_servers and configure_mock_servers functions

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

    if ! command -v pytest &> /dev/null; then
        echo "Error: pytest is not installed or not in PATH"
        return 1
    fi

    if ! command -v jq &> /dev/null; then
        echo "Error: jq is not installed or not in PATH"
        return 1
    fi

    echo "All dependencies are available"
    return 0
}

# Function to run the integration tests with specified parameters
run_integration_tests() {
    local test_pattern="${1:-$DEFAULT_TEST_PATTERN}"
    local use_mock_servers="${2:-true}"
    local failure_rate="${3:-$DEFAULT_FAILURE_RATE}"
    local delay_rate="${4:-$DEFAULT_DELAY_RATE}"
    local verbose="${5:-false}"

    print_header "Running integration tests"

    # Build pytest command with appropriate options
    local pytest_cmd="pytest $INTEGRATION_TEST_DIR"

    # Add -v flag if verbose is true
    if [ "$verbose" = true ]; then
        pytest_cmd="$pytest_cmd -v"
    fi

    # Add --junitxml flag for XML report generation
    pytest_cmd="$pytest_cmd --junitxml=$TEST_REPORT_FILE"

    # Add --json flag for JSON report generation
    pytest_cmd="$pytest_cmd --json=$TEST_JSON_REPORT_FILE"

    # Add --mock-external flag based on use_mock_servers
    if [ "$use_mock_servers" = true ]; then
        pytest_cmd="$pytest_cmd --mock-external"
    fi

    # Add --env=integration flag to specify test environment
    pytest_cmd="$pytest_cmd --env=integration"

    # Add test pattern to specify which tests to run
    pytest_cmd="$pytest_cmd $test_pattern"

    # Execute pytest command and capture exit code
    echo "Executing command: $pytest_cmd"
    eval "$pytest_cmd"
    local pytest_exit_code=$?

    return $pytest_exit_code
}

# Function to generate a summary of test results from the JSON report
generate_test_summary() {
    print_header "Generating test summary"

    # Check if JSON report file exists
    if [ ! -f "$TEST_JSON_REPORT_FILE" ]; then
        echo "Error: JSON report file not found: $TEST_JSON_REPORT_FILE"
        return 1
    fi

    # Use jq to extract test statistics (total, passed, failed, skipped)
    local total=$(jq '.summary.total' "$TEST_JSON_REPORT_FILE")
    local passed=$(jq '.summary.passed' "$TEST_JSON_REPORT_FILE")
    local failed=$(jq '.summary.failed' "$TEST_JSON_REPORT_FILE")
    local skipped=$(jq '.summary.skipped' "$TEST_JSON_REPORT_FILE")

    # Calculate pass percentage
    local pass_percentage=$(echo "scale=2; $passed / $total * 100" | bc)

    # Print formatted summary with colorized output
    echo "Test Summary:"
    echo "  Total:   $total"
    echo "  Passed:  $passed"
    echo "  Failed:  $failed"
    echo "  Skipped: $skipped"
    echo "  Pass %:  $pass_percentage%"

    return 0
}

# Function to set up the test environment for integration tests
setup_environment() {
    local use_mock_servers="${1:-true}"
    local failure_rate="${2:-$DEFAULT_FAILURE_RATE}"
    local delay_rate="${3:-$DEFAULT_DELAY_RATE}"

    print_header "Setting up test environment"

    # Source setup_test_env.sh to use its functions
    # Call setup_test_environment with appropriate parameters
    if ! setup_test_environment "$failure_rate" "$delay_rate"; then
        echo "Error: Failed to set up test environment"
        return 2
    fi

    # If use_mock_servers is true, configure mock servers with failure_rate and delay_rate
    if [ "$use_mock_servers" = true ]; then
        if ! configure_mock_servers "$failure_rate" "$delay_rate"; then
            echo "Error: Failed to configure mock servers"
            return 3
        fi
    fi

    echo "Test environment setup completed successfully"
    return 0
}

# Function to clean up the test environment after tests complete
cleanup_test_environment() {
    print_header "Cleaning up environment"

    # Source setup_test_env.sh to use its functions
    # Call cleanup_environment function
    if ! cleanup_environment; then
        echo "Error: Failed to clean up test environment"
        return 4
    fi

    echo "Environment cleanup completed"
    return 0
}

# Function to display usage information
show_usage() {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --test-pattern <pattern>  Pattern to select which tests to run (e.g., 'test_api_*.py')"
    echo "                              Default: '$DEFAULT_TEST_PATTERN'"
    echo "  --no-mock                 Disable mock servers and use real external APIs"
    echo "  --failure-rate <rate>     Percentage of mock API requests that should fail (0-100)"
    echo "                              Default: $DEFAULT_FAILURE_RATE"
    echo "  --delay-rate <rate>       Percentage of mock API requests that should be delayed (0-100)"
    echo "                              Default: $DEFAULT_DELAY_RATE"
    echo "  --no-setup                Skip environment setup (assumes environment is already set up)"
    echo "  --no-cleanup              Skip environment cleanup after tests"
    echo "  --verbose                 Enable verbose output for tests"
    echo "  --help                    Show this help message"
    echo

    echo "Examples:"
    echo "  $0 --test-pattern test_api_*.py"
    echo "  $0 --no-mock"
    echo "  $0 --failure-rate 20"
    echo "  $0 --delay-rate 10"
    echo "  $0 --no-setup"
    echo "  $0 --no-cleanup"
    echo "  $0 --verbose"
    echo "  $0 --help"
}

# Main function
main() {
    local test_pattern="$DEFAULT_TEST_PATTERN"
    local use_mock_servers="true"
    local failure_rate="$DEFAULT_FAILURE_RATE"
    local delay_rate="$DEFAULT_DELAY_RATE"
    local skip_setup=false
    local skip_cleanup=false
    local verbose=false

    # Process command line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --test-pattern)
                test_pattern="$2"
                shift
                shift
                ;;
            --no-mock)
                use_mock_servers="false"
                shift
                ;;
            --failure-rate)
                failure_rate="$2"
                shift
                shift
                ;;
            --delay-rate)
                delay_rate="$2"
                shift
                shift
                ;;
            --no-setup)
                skip_setup=true
                shift
                ;;
            --no-cleanup)
                skip_cleanup=true
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
                echo "Error: Unknown option: $1"
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
    if [ "$skip_setup" = false ]; then
        if ! setup_environment "$use_mock_servers" "$failure_rate" "$delay_rate"; then
            local setup_exit_code=$?
            echo "Error: Environment setup failed with exit code $setup_exit_code"
            return 2
        fi
    fi

    # Run integration tests with specified parameters
    if ! run_integration_tests "$test_pattern" "$use_mock_servers" "$failure_rate" "$delay_rate" "$verbose"; then
        local test_exit_code=$?
        echo "Error: Integration tests failed with exit code $test_exit_code"
        # If tests failed, return a specific exit code
        test_exit_code=5
    else
        local test_exit_code=0
    fi

    # Generate test summary
    if ! generate_test_summary; then
        echo "Error: Failed to generate test summary"
    fi

    # Clean up test environment if --no-cleanup is not specified
    if [ "$skip_cleanup" = false ]; then
        if ! cleanup_test_environment; then
            echo "Error: Failed to clean up test environment"
            return 4
        fi
    fi

    # Return appropriate exit code based on test results
    return $test_exit_code
}

# Execute main function with all arguments
main "$@"
exit $?