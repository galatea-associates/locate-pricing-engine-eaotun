#!/bin/bash
# run_tests.sh - Load Test Execution Script for Borrow Rate & Locate Fee Pricing Engine API
# This script orchestrates the execution of Locust-based load tests with various configurations,
# collects results, and triggers analysis of test metrics.

# Global variables
CONFIG_FILE="./config.yaml"
RESULTS_DIR="./results"
LOG_FILE="./results/load_test.log"
DEFAULT_TEST_TYPE="load"
DEFAULT_ENV="development"

# Print usage information
print_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "This script executes load tests against the Borrow Rate & Locate Fee Pricing Engine API."
    echo ""
    echo "Options:"
    echo "  --type=TYPE      Type of load test to run (load, stress, endurance, spike)"
    echo "                   Default: $DEFAULT_TEST_TYPE"
    echo "  --env=ENV        Target environment (development, staging, production)"
    echo "                   Default: $DEFAULT_ENV"
    echo "  --web            Start Locust with web UI instead of headless mode"
    echo "  --no-analyze     Skip result analysis after test execution"
    echo "  --help           Display this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --type=load --env=development"
    echo "  $0 --type=stress --env=staging"
    echo "  $0 --type=endurance --env=production"
    echo "  $0 --web --type=load --env=development"
    echo "  $0 --type=spike --env=staging --no-analyze"
    echo ""
}

# Log message to both console and log file
log() {
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] $1"
    echo "[$timestamp] $1" >> "$LOG_FILE"
}

# Set up the test environment and directories
setup_environment() {
    # Create results directory if it doesn't exist
    mkdir -p "$RESULTS_DIR"
    
    # Create log file with header
    echo "=== Load Test Execution Log - $(date) ===" > "$LOG_FILE"
    
    log "Starting load test execution script"
    log "Configuration file: $CONFIG_FILE"
    log "Results directory: $RESULTS_DIR"
    
    # Check if required tools are installed
    if ! command -v locust &> /dev/null; then
        log "ERROR: Locust is not installed. Please install Locust using 'pip install locust==2.15.0'."
        exit 1
    fi
    
    if ! command -v yq &> /dev/null; then
        log "ERROR: yq is not installed. Please install yq for YAML processing."
        exit 1
    fi
    
    # Verify config file exists
    if [ ! -f "$CONFIG_FILE" ]; then
        log "ERROR: Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    log "Environment setup complete"
}

# Extract a value from the YAML configuration file using yq
get_config_value() {
    local path="$1"
    local default="$2"
    
    # Use yq to extract the value (compatible with both older and newer yq versions)
    local value
    if yq --version 2>&1 | grep -q "version"; then
        # Newer version of yq (4.x+)
        value=$(yq eval "$path" "$CONFIG_FILE" 2>/dev/null)
    else
        # Older version of yq (3.x or earlier)
        value=$(yq read "$CONFIG_FILE" "$path" 2>/dev/null)
    fi
    
    # Check if the value is null or empty and return the default if it is
    if [ "$value" = "null" ] || [ -z "$value" ]; then
        echo "$default"
    else
        echo "$value"
    fi
}

# Execute a load test with the specified parameters
run_load_test() {
    local test_type="$1"
    local environment="$2"
    local web_ui="$3"
    
    log "Executing $test_type test against $environment environment"
    
    # Extract environment-specific configuration
    local base_url=$(get_config_value ".environments.$environment.base_url" "http://localhost:8000")
    local api_key=$(get_config_value ".environments.$environment.api_key" "\${${environment^^}_API_KEY}")
    local log_level=$(get_config_value ".environments.$environment.log_level" "info")
    local timeout=$(get_config_value ".environments.$environment.timeout" "30")
    
    # Extract test-specific configuration
    local users=$(get_config_value ".test_execution.$test_type.users" "10")
    local duration=$(get_config_value ".test_execution.$test_type.duration" "60")
    local ramp_up=$(get_config_value ".test_execution.$test_type.ramp_up" "10")
    local ramp_down=$(get_config_value ".test_execution.$test_type.ramp_down" "10")
    local requests_per_second=$(get_config_value ".test_execution.$test_type.requests_per_second" "10")
    local terminate_on_failure=$(get_config_value ".test_execution.$test_type.terminate_on_failure" "false")
    local failure_threshold=$(get_config_value ".test_execution.$test_type.failure_threshold" "5")
    
    log "Test configuration:"
    log "  Base URL: $base_url"
    log "  Users: $users"
    log "  Duration: $duration seconds"
    log "  Ramp Up: $ramp_up seconds"
    log "  Target RPS: $requests_per_second requests/second"
    log "  Terminate on Failure: $terminate_on_failure"
    log "  Failure Threshold: $failure_threshold%"
    
    # Set up environment variables for test configuration
    export LOAD_TEST_CONFIG="$CONFIG_FILE"
    export LOAD_TEST_TYPE="$test_type"
    export LOAD_TEST_ENV="$environment"
    export LOAD_TEST_LOG_LEVEL="$log_level"
    
    # Set up API keys based on environment
    local api_key_var="${environment^^}_API_KEY"  # Convert to uppercase for env var
    if [ -n "${!api_key_var}" ]; then
        export API_KEY="${!api_key_var}"
        log "Using API key from environment variable $api_key_var"
    else
        log "WARNING: No API key found in environment variable $api_key_var"
    fi
    
    # Define output files
    local results_json="$RESULTS_DIR/results.json"
    local stats_csv="$RESULTS_DIR/stats"
    
    # Construct the locust command base
    local locust_cmd="locust -f locustfile.py"
    
    # Add test-specific parameters
    locust_cmd="$locust_cmd --host=$base_url"
    
    # If web UI is requested, start Locust with the web interface
    if [ "$web_ui" = true ]; then
        log "Starting Locust with web interface. Please open http://localhost:8089 in your browser."
        $locust_cmd --web-port=8089
        exit_code=$?
    else
        # Run Locust in headless mode
        log "Running Locust in headless mode"
        
        # Add headless mode parameters
        locust_cmd="$locust_cmd --headless --users=$users --spawn-rate=$ramp_up --run-time=${duration}s"
        
        # Add CSV and JSON output parameters
        locust_cmd="$locust_cmd --csv=$stats_csv --json=$results_json"
        
        # Execute the Locust command
        log "Executing command: $locust_cmd"
        $locust_cmd
        exit_code=$?
        
        # Check if the test was successful
        if [ $exit_code -eq 0 ]; then
            log "Load test completed successfully"
            
            # Verify that result files were created
            if [ ! -f "$results_json" ]; then
                log "WARNING: JSON results file not created: $results_json"
            fi
            
            if [ ! -f "${stats_csv}_stats.csv" ]; then
                log "WARNING: Stats CSV file not created: ${stats_csv}_stats.csv"
            fi
        else
            log "ERROR: Load test failed with exit code $exit_code"
        fi
    fi
    
    return $exit_code
}

# Analyze test results and generate reports
analyze_test_results() {
    local test_type="$1"
    local environment="$2"
    
    log "Analyzing test results for $test_type test in $environment environment"
    
    # Check if results files exist
    if [ ! -f "$RESULTS_DIR/stats_stats.csv" ]; then
        log "WARNING: Stats CSV file not found: $RESULTS_DIR/stats_stats.csv"
    fi
    
    if [ ! -f "$RESULTS_DIR/results.json" ]; then
        log "WARNING: JSON results file not found: $RESULTS_DIR/results.json"
    fi
    
    if [ ! -f "$RESULTS_DIR/stats_stats.csv" ] && [ ! -f "$RESULTS_DIR/results.json" ]; then
        log "ERROR: No test result files found. Cannot perform analysis."
        return 1
    fi
    
    # Create analysis output directory
    mkdir -p "$RESULTS_DIR/analysis"
    
    # Execute the analysis script
    log "Running analysis script"
    python analyze_results.py --results-dir="$RESULTS_DIR" --output-dir="$RESULTS_DIR/analysis" --config="$CONFIG_FILE"
    exit_code=$?
    
    # Check if analysis was successful
    if [ $exit_code -eq 0 ]; then
        log "Analysis completed successfully. Results available in $RESULTS_DIR/analysis"
    else
        log "ERROR: Analysis failed with exit code $exit_code"
    fi
    
    return $exit_code
}

# Perform cleanup after test execution
cleanup() {
    log "Performing cleanup"
    
    # Remove any temporary files
    rm -f "$RESULTS_DIR/locust_stats_*.tmp" 2>/dev/null
    
    # Organize result files
    if [ -d "$RESULTS_DIR" ]; then
        # Create a timestamped subdirectory for this test run
        local timestamp=$(date +"%Y%m%d_%H%M%S")
        local archive_dir="$RESULTS_DIR/run_$timestamp"
        
        if [ -f "$RESULTS_DIR/results.json" ] || [ -f "$RESULTS_DIR/stats_stats.csv" ]; then
            mkdir -p "$archive_dir"
            
            # Move result files to the archive directory
            mv "$RESULTS_DIR"/stats_*.csv "$archive_dir"/ 2>/dev/null
            mv "$RESULTS_DIR"/results.json "$archive_dir"/ 2>/dev/null
            
            # Copy the log file (don't move since we're still writing to it)
            cp "$LOG_FILE" "$archive_dir"/ 2>/dev/null
            
            # Move analysis directory if it exists
            if [ -d "$RESULTS_DIR/analysis" ]; then
                mv "$RESULTS_DIR/analysis" "$archive_dir"/ 2>/dev/null
            fi
            
            log "Test results archived to $archive_dir"
        fi
    fi
    
    log "Cleanup completed"
}

# Main function
main() {
    # Default values
    local test_type="$DEFAULT_TEST_TYPE"
    local environment="$DEFAULT_ENV"
    local web_ui=false
    local skip_analyze=false
    
    # Parse command line arguments
    for arg in "$@"; do
        case $arg in
            --type=*)
                test_type="${arg#*=}"
                ;;
            --env=*)
                environment="${arg#*=}"
                ;;
            --web)
                web_ui=true
                ;;
            --no-analyze)
                skip_analyze=true
                ;;
            --help)
                print_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $arg"
                print_usage
                exit 1
                ;;
        esac
    done
    
    # Validate test type
    case $test_type in
        load|stress|endurance|spike)
            # Valid test type
            ;;
        *)
            echo "ERROR: Invalid test type: $test_type"
            print_usage
            exit 1
            ;;
    esac
    
    # Validate environment
    case $environment in
        development|staging|production)
            # Valid environment
            ;;
        *)
            echo "ERROR: Invalid environment: $environment"
            print_usage
            exit 1
            ;;
    esac
    
    # Set up the environment
    setup_environment
    
    # Run the load test
    run_load_test "$test_type" "$environment" "$web_ui"
    local test_exit_code=$?
    
    # If test was successful and analysis is not skipped, analyze results
    if [ $test_exit_code -eq 0 ] && [ "$skip_analyze" = false ] && [ "$web_ui" = false ]; then
        analyze_test_results "$test_type" "$environment"
        local analyze_exit_code=$?
    else
        if [ "$skip_analyze" = true ]; then
            log "Skipping result analysis as requested"
        elif [ "$web_ui" = true ]; then
            log "Skipping result analysis for web UI mode"
        elif [ $test_exit_code -ne 0 ]; then
            log "Skipping result analysis due to test failure"
        fi
    fi
    
    # Perform cleanup
    cleanup
    
    log "Load test script execution completed"
    
    # Return appropriate exit code
    if [ $test_exit_code -ne 0 ]; then
        return $test_exit_code
    elif [ "$skip_analyze" = false ] && [ "$web_ui" = false ] && [ "${analyze_exit_code:-0}" -ne 0 ]; then
        return $analyze_exit_code
    else
        return 0
    fi
}

# Execute main function with all script arguments
main "$@"
exit $?