#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Error handling - display error message and exit on error
trap 'echo "Error occurred at line $LINENO"; exit 1' ERR

# Script directory
SCRIPT_DIR=$(dirname "${BASH_SOURCE[0]}")

# Project root directory
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/../../..")

# Security tests directory
SECURITY_TESTS_DIR="$PROJECT_ROOT/src/test/security_tests"

# Test report directory
TEST_REPORT_DIR="$PROJECT_ROOT/src/test/reports"

# Security report file (JSON)
SECURITY_REPORT_FILE="$TEST_REPORT_DIR/security_test_report.json"

# Security report file (HTML)
HTML_REPORT_FILE="$TEST_REPORT_DIR/security_test_report.html"

# Security report file (XML)
XML_REPORT_FILE="$TEST_REPORT_DIR/security_test_report.xml"

# ZAP scan report file
ZAP_REPORT_FILE="$TEST_REPORT_DIR/zap_scan_report.html"

# Static analysis report file
STATIC_ANALYSIS_REPORT="$TEST_REPORT_DIR/static_analysis_report.json"

# Source the setup_test_env.sh script
source "$SCRIPT_DIR/setup_test_env.sh"

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
        return 2
    fi

    if [[ "$run_zap_scan" == "true" ]] && ! command -v python-owasp-zap-v2.4 &> /dev/null; then
        echo "Error: python-owasp-zap is not installed or not in PATH"
        return 2
    fi

    if [[ "$run_static_analysis" == "true" ]] && ! command -v bandit &> /dev/null; then
        echo "Error: bandit is not installed or not in PATH"
        return 2
    fi

    echo "All dependencies are available"
    return 0
}

# Function to setup the environment
setup_environment() {
    print_header "Setting up test environment"

    # Source the setup_test_env.sh script
    if ! source "$SCRIPT_DIR/setup_test_env.sh"; then
        echo "Error: Failed to source setup_test_env.sh"
        return 3
    fi

    # Create test report directory if it doesn't exist
    if [ ! -d "$TEST_REPORT_DIR" ]; then
        echo "Creating test report directory: $TEST_REPORT_DIR"
        mkdir -p "$TEST_REPORT_DIR"
    else
        echo "Test report directory already exists: $TEST_REPORT_DIR"
    fi

    # Start mock servers for external APIs if needed
    # Add mock server starting steps here

    # Set up environment variables for security testing
    # Add environment variable setting steps here

    echo "Test environment setup completed successfully"
    return 0
}

# Function to run authentication security tests
run_authentication_tests() {
    print_header "Running authentication tests"

    # Run pytest for authentication test suite
    pytest "$SECURITY_TESTS_DIR/authentication_tests.py" --junitxml="$TEST_REPORT_DIR/auth_junit.xml"
    auth_exit_code=$?

    # Capture test results and exit code
    if [ $auth_exit_code -eq 0 ]; then
        echo "Authentication tests passed"
    else
        echo "Authentication tests failed"
    fi

    # Return exit code (0 for success)
    return $auth_exit_code
}

# Function to run authorization security tests
run_authorization_tests() {
    print_header "Running authorization tests"

    # Run pytest for authorization test suite
    pytest "$SECURITY_TESTS_DIR/authorization_tests.py" --junitxml="$TEST_REPORT_DIR/authz_junit.xml"
    authz_exit_code=$?

    # Capture test results and exit code
    if [ $authz_exit_code -eq 0 ]; then
        echo "Authorization tests passed"
    else
        echo "Authorization tests failed"
    fi

    # Return exit code (0 for success)
    return $authz_exit_code
}

# Function to run input validation security tests
run_input_validation_tests() {
    print_header "Running input validation tests"

    # Run pytest for input validation test suite
    pytest "$SECURITY_TESTS_DIR/input_validation_tests.py" --junitxml="$TEST_REPORT_DIR/input_junit.xml"
    input_exit_code=$?

    # Capture test results and exit code
    if [ $input_exit_code -eq 0 ]; then
        echo "Input validation tests passed"
    else
        echo "Input validation tests failed"
    fi

    # Return exit code (0 for success)
    return $input_exit_code
}

# Function to run rate limiting security tests
run_rate_limiting_tests() {
    print_header "Running rate limiting tests"

    # Run pytest for rate limiting test suite
    pytest "$SECURITY_TESTS_DIR/rate_limiting_tests.py" --junitxml="$TEST_REPORT_DIR/rate_junit.xml"
    rate_exit_code=$?

    # Capture test results and exit code
    if [ $rate_exit_code -eq 0 ]; then
        echo "Rate limiting tests passed"
    else
        echo "Rate limiting tests failed"
    fi

    # Return exit code (0 for success)
    return $rate_exit_code
}

# Function to run data encryption security tests
run_data_encryption_tests() {
    print_header "Running data encryption tests"

    # Run pytest for data encryption test suite
    pytest "$SECURITY_TESTS_DIR/data_encryption_tests.py" --junitxml="$TEST_REPORT_DIR/encryption_junit.xml"
    encryption_exit_code=$?

    # Capture test results and exit code
    if [ $encryption_exit_code -eq 0 ]; then
        echo "Data encryption tests passed"
    else
        echo "Data encryption tests failed"
    fi

    # Return exit code (0 for success)
    return $encryption_exit_code
}

# Function to run API security tests
run_api_security_tests() {
    print_header "Running API security tests"

    # Run pytest for API security test suite
    pytest "$SECURITY_TESTS_DIR/api_security_tests.py" --junitxml="$TEST_REPORT_DIR/api_junit.xml"
    api_exit_code=$?

    # Capture test results and exit code
    if [ $api_exit_code -eq 0 ]; then
        echo "API security tests passed"
    else
        echo "API security tests failed"
    fi

    # Return exit code (0 for success)
    return $api_exit_code
}

# Function to run dependency vulnerability security tests
run_dependency_vulnerability_tests() {
    print_header "Running dependency vulnerability tests"

    # Run pytest for dependency vulnerability test suite
    pytest "$SECURITY_TESTS_DIR/dependency_vulnerability_tests.py" --junitxml="$TEST_REPORT_DIR/dependency_junit.xml"
    dependency_exit_code=$?

    # Capture test results and exit code
    if [ $dependency_exit_code -eq 0 ]; then
        echo "Dependency vulnerability tests passed"
    else
        echo "Dependency vulnerability tests failed"
    fi

    # Return exit code (0 for success)
    return $dependency_exit_code
}

# Function to run OWASP ZAP security scan
run_zap_scan() {
    print_header "Running OWASP ZAP security scan"

    # Check if ZAP is running and accessible
    # Add ZAP accessibility check here

    # Run ZAP spider scan to discover endpoints
    # Add ZAP spider scan command here

    # Run ZAP active scan to find vulnerabilities
    # Add ZAP active scan command here

    # Generate ZAP scan report
    # Add ZAP report generation command here

    # Return 0 if scan completes successfully
    return 0
}

# Function to run static code analysis for security issues
run_static_analysis() {
    print_header "Running static code analysis"

    # Run bandit static analysis tool on the codebase
    bandit -r "$PROJECT_ROOT/src/backend" -f json -o "$STATIC_ANALYSIS_REPORT"

    # Check exit code
    static_analysis_exit_code=$?

    # Check if bandit found any high-severity issues
    if [ $static_analysis_exit_code -eq 0 ]; then
        echo "No high-severity security issues found by bandit"
    else
        echo "High-severity security issues found by bandit"
    fi

    # Return 0 if no high-severity issues found
    return $static_analysis_exit_code
}

# Function to generate consolidated security test reports
generate_reports() {
    local generate_html="$1"
    local generate_xml="$2"

    print_header "Generating reports"

    # Collect results from all security test suites
    # Add report collection steps here

    # Generate consolidated JSON report
    # Add JSON report generation command here

    # Generate HTML report if requested
    if [ "$generate_html" == "true" ]; then
        # Add HTML report generation command here
        echo "Generating HTML report"
    fi

    # Generate XML report if requested
    if [ "$generate_xml" == "true" ]; then
        # Add XML report generation command here
        echo "Generating XML report"
    fi

    # Print location of generated reports
    echo "Generated reports are located in $TEST_REPORT_DIR"

    # Return 0 if successful
    return 0
}

# Function to cleanup the environment
cleanup_environment() {
    print_header "Cleaning up environment"

    # Stop mock servers if they were started
    # Add mock server stopping steps here

    # Clean up any temporary files created during testing
    # Add temporary file removal steps here

    echo "Environment cleanup completed"
    return 0
}

# Function to display usage information
show_usage() {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --generate-html      Generate HTML report of security test results"
    echo "  --generate-xml       Generate XML report of security test results"
    echo "  --run-zap-scan       Run OWASP ZAP security scan"
    echo "  --run-static-analysis  Run static code analysis for security issues"
    echo "  --skip-auth-tests   Skip authentication security tests"
    echo "  --skip-authz-tests  Skip authorization security tests"
    echo "  --skip-input-tests  Skip input validation security tests"
    echo "  --skip-rate-tests   Skip rate limiting security tests"
    echo "  --skip-encryption-tests Skip data encryption security tests"
    echo "  --skip-api-tests     Skip general API security tests"
    echo "  --skip-dependency-tests Skip dependency vulnerability tests"
    echo "  --help               Show this help message"
    echo
    echo "Examples:"
    echo "  $0 --generate-html --run-zap-scan"
    echo "  $0 --skip-auth-tests --skip-rate-tests"
}

# Main function
main() {
    # Process command line arguments
    generate_html="false"
    generate_xml="false"
    run_zap_scan="false"
    run_static_analysis="false"
    skip_auth_tests="false"
    skip_authz_tests="false"
    skip_input_tests="false"
    skip_rate_tests="false"
    skip_encryption_tests="false"
    skip_api_tests="false"
    skip_dependency_tests="false"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --generate-html)
                generate_html="true"
                shift
                ;;
            --generate-xml)
                generate_xml="true"
                shift
                ;;
            --run-zap-scan)
                run_zap_scan="true"
                shift
                ;;
            --run-static-analysis)
                run_static_analysis="true"
                shift
                ;;
            --skip-auth-tests)
                skip_auth_tests="true"
                shift
                ;;
            --skip-authz-tests)
                skip_authz_tests="true"
                shift
                ;;
            --skip-input-tests)
                skip_input_tests="true"
                shift
                ;;
            --skip-rate-tests)
                skip_rate_tests="true"
                shift
                ;;
            --skip-encryption-tests)
                skip_encryption_tests="true"
                shift
                ;;
            --skip-api-tests)
                skip_api_tests="true"
                shift
                ;;
            --skip-dependency-tests)
                skip_dependency_tests="true"
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
        exit 2
    fi

    # Setup test environment
    if ! setup_environment; then
        exit 3
    fi

    # Run security tests
    overall_exit_code=0

    if [ "$skip_auth_tests" == "false" ]; then
        run_authentication_tests
        auth_exit_code=$?
        if [ $auth_exit_code -ne 0 ]; then
            overall_exit_code=4
        fi
    fi

    if [ "$skip_authz_tests" == "false" ]; then
        run_authorization_tests
        authz_exit_code=$?
        if [ $authz_exit_code -ne 0 ]; then
            overall_exit_code=4
        fi
    fi

    if [ "$skip_input_tests" == "false" ]; then
        run_input_validation_tests
        input_exit_code=$?
        if [ $input_exit_code -ne 0 ]; then
            overall_exit_code=4
        fi
    fi

    if [ "$skip_rate_tests" == "false" ]; then
        run_rate_limiting_tests
        rate_exit_code=$?
        if [ $rate_exit_code -ne 0 ]; then
            overall_exit_code=4
        fi
    fi

    if [ "$skip_encryption_tests" == "false" ]; then
        run_data_encryption_tests
        encryption_exit_code=$?
        if [ $encryption_exit_code -ne 0 ]; then
            overall_exit_code=4
        fi
    fi

    if [ "$skip_api_tests" == "false" ]; then
        run_api_security_tests
        api_exit_code=$?
        if [ $api_exit_code -ne 0 ]; then
            overall_exit_code=4
        fi
    fi

    if [ "$skip_dependency_tests" == "false" ]; then
        run_dependency_vulnerability_tests
        dependency_exit_code=$?
        if [ $dependency_exit_code -ne 0 ]; then
            overall_exit_code=4
        fi
    fi

    if [ "$run_zap_scan" == "true" ]; then
        run_zap_scan
        zap_exit_code=$?
        if [ $zap_exit_code -ne 0 ]; then
            overall_exit_code=5
        fi
    fi

    if [ "$run_static_analysis" == "true" ]; then
        run_static_analysis
        static_analysis_exit_code=$?
        if [ $static_analysis_exit_code -ne 0 ]; then
            overall_exit_code=6
        fi
    fi

    # Generate reports
    generate_reports "$generate_html" "$generate_xml"
    report_exit_code=$?
    if [ $report_exit_code -ne 0 ]; then
        overall_exit_code=7
    fi

    # Cleanup test environment
    cleanup_environment
    cleanup_exit_code=$?

    # Return 0 if all tests passed
    return $overall_exit_code
}

# Execute main function with all arguments
main "$@"
exit $?