#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Error handling - display error message and exit on error
trap 'echo "Error occurred at line $LINENO"; exit 1' ERR

# Global variables
SCRIPT_DIR=$(dirname "${BASH_SOURCE[0]}")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/../../..")
MOCK_SERVERS_DIR=$PROJECT_ROOT/src/test/mock_servers
DOCKER_COMPOSE_FILE=$MOCK_SERVERS_DIR/docker-compose.yml
DEFAULT_FAILURE_RATE=0
DEFAULT_DELAY_RATE=0
MOCK_SERVERS_LOG_FILE=/tmp/mock_servers.log

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
    
    if ! command -v docker &> /dev/null; then
        echo "Error: docker is not installed or not in PATH"
        return 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo "Error: docker-compose is not installed or not in PATH"
        return 1
    fi
    
    echo "All dependencies are available"
    return 0
}

# Function to start the mock servers
start_mock_servers() {
    local failure_rate=${1:-$DEFAULT_FAILURE_RATE}
    local delay_rate=${2:-$DEFAULT_DELAY_RATE}
    
    print_header "Starting mock servers"
    
    # Validate parameters
    if [[ ! "$failure_rate" =~ ^[0-9]+$ ]] || [ "$failure_rate" -lt 0 ] || [ "$failure_rate" -gt 100 ]; then
        echo "Error: failure_rate must be an integer between 0 and 100"
        return 1
    fi
    
    if [[ ! "$delay_rate" =~ ^[0-9]+$ ]] || [ "$delay_rate" -lt 0 ] || [ "$delay_rate" -gt 100 ]; then
        echo "Error: delay_rate must be an integer between 0 and 100"
        return 1
    fi
    
    echo "Starting mock servers with failure_rate=$failure_rate%, delay_rate=$delay_rate%"
    
    # Set environment variables for docker-compose
    export FAILURE_RATE=$failure_rate
    export DELAY_RATE=$delay_rate
    
    # Navigate to the mock servers directory and run docker-compose
    cd "$MOCK_SERVERS_DIR"
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d > "$MOCK_SERVERS_LOG_FILE" 2>&1
    
    # Wait for containers to be healthy
    if ! wait_for_healthy 60; then
        echo "Error: Failed to start mock servers. Check logs at $MOCK_SERVERS_LOG_FILE"
        return 3
    fi
    
    echo "Mock servers started successfully"
    echo "SecLend API:           http://localhost:8001"
    echo "Market Volatility API: http://localhost:8002"
    echo "Event Calendar API:    http://localhost:8003"
    
    return 0
}

# Function to stop the mock servers
stop_mock_servers() {
    print_header "Stopping mock servers"
    
    echo "Stopping and removing mock server containers"
    cd "$MOCK_SERVERS_DIR"
    docker-compose -f "$DOCKER_COMPOSE_FILE" down > "$MOCK_SERVERS_LOG_FILE" 2>&1
    
    echo "Mock servers stopped successfully"
    return 0
}

# Function to restart the mock servers
restart_mock_servers() {
    local failure_rate=${1:-$DEFAULT_FAILURE_RATE}
    local delay_rate=${2:-$DEFAULT_DELAY_RATE}
    
    print_header "Restarting mock servers"
    
    stop_mock_servers
    start_mock_servers "$failure_rate" "$delay_rate"
    
    return $?
}

# Function to configure the mock servers
configure_mock_servers() {
    local failure_rate=${1:-$DEFAULT_FAILURE_RATE}
    local delay_rate=${2:-$DEFAULT_DELAY_RATE}
    
    print_header "Configuring mock servers"
    
    # Validate parameters
    if [[ ! "$failure_rate" =~ ^[0-9]+$ ]] || [ "$failure_rate" -lt 0 ] || [ "$failure_rate" -gt 100 ]; then
        echo "Error: failure_rate must be an integer between 0 and 100"
        return 1
    fi
    
    if [[ ! "$delay_rate" =~ ^[0-9]+$ ]] || [ "$delay_rate" -lt 0 ] || [ "$delay_rate" -gt 100 ]; then
        echo "Error: delay_rate must be an integer between 0 and 100"
        return 1
    fi
    
    echo "Configuring mock servers with failure_rate=$failure_rate%, delay_rate=$delay_rate%"
    
    # Check if servers are running
    if ! check_mock_servers_status > /dev/null; then
        echo "Error: Mock servers are not running"
        return 4
    fi
    
    # Configure each mock server
    local status=0
    
    # Configure SecLend API
    if ! curl -s -X POST "http://localhost:8001/admin/configure" \
         -H "Content-Type: application/json" \
         -d "{\"failure_rate\": $failure_rate, \"delay_rate\": $delay_rate}" \
         > /dev/null; then
        echo "Error: Failed to configure SecLend API"
        status=5
    fi
    
    # Configure Market Volatility API
    if ! curl -s -X POST "http://localhost:8002/admin/configure" \
         -H "Content-Type: application/json" \
         -d "{\"failure_rate\": $failure_rate, \"delay_rate\": $delay_rate}" \
         > /dev/null; then
        echo "Error: Failed to configure Market Volatility API"
        status=5
    fi
    
    # Configure Event Calendar API
    if ! curl -s -X POST "http://localhost:8003/admin/configure" \
         -H "Content-Type: application/json" \
         -d "{\"failure_rate\": $failure_rate, \"delay_rate\": $delay_rate}" \
         > /dev/null; then
        echo "Error: Failed to configure Event Calendar API"
        status=5
    fi
    
    if [ $status -eq 0 ]; then
        echo "Mock servers configured successfully"
    fi
    
    return $status
}

# Function to check the status of mock servers
check_mock_servers_status() {
    print_header "Checking mock servers status"
    
    local status=0
    
    # Check SecLend API
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:8001/health" | grep -q "200"; then
        echo "SecLend API:           RUNNING (http://localhost:8001)"
    else
        echo "SecLend API:           NOT RUNNING"
        status=4
    fi
    
    # Check Market Volatility API
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:8002/health" | grep -q "200"; then
        echo "Market Volatility API: RUNNING (http://localhost:8002)"
    else
        echo "Market Volatility API: NOT RUNNING"
        status=4
    fi
    
    # Check Event Calendar API
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:8003/health" | grep -q "200"; then
        echo "Event Calendar API:    RUNNING (http://localhost:8003)"
    else
        echo "Event Calendar API:    NOT RUNNING"
        status=4
    fi
    
    return $status
}

# Function to wait for all mock servers to be healthy
wait_for_healthy() {
    local timeout_seconds=${1:-60}
    local end_time=$(($(date +%s) + timeout_seconds))
    
    echo "Waiting for mock servers to be healthy (timeout: ${timeout_seconds}s)..."
    
    while [ $(date +%s) -lt $end_time ]; do
        # Check if all servers are healthy
        if curl -s -o /dev/null -w "%{http_code}" "http://localhost:8001/health" | grep -q "200" && \
           curl -s -o /dev/null -w "%{http_code}" "http://localhost:8002/health" | grep -q "200" && \
           curl -s -o /dev/null -w "%{http_code}" "http://localhost:8003/health" | grep -q "200"; then
            echo "All mock servers are healthy"
            return 0
        fi
        
        # Wait before checking again
        sleep 2
    done
    
    echo "Timeout reached waiting for mock servers to be healthy"
    return 1
}

# Function to display usage information
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "Manage mock servers for testing the Borrow Rate & Locate Fee Pricing Engine"
    echo
    echo "Commands:"
    echo "  start       Start the mock servers"
    echo "  stop        Stop the mock servers"
    echo "  restart     Restart the mock servers"
    echo "  status      Check the status of mock servers"
    echo "  configure   Configure running mock servers"
    echo
    echo "Options:"
    echo "  --failure-rate=RATE   Percentage of mock API requests that should fail (0-100)"
    echo "  --delay-rate=RATE     Percentage of mock API requests that should be delayed (0-100)"
    echo "  --timeout=SECONDS     Timeout in seconds when waiting for servers to be healthy"
    echo "  --help                Show this help message"
    echo
    echo "Examples:"
    echo "  $0 start                       # Start mock servers with default settings"
    echo "  $0 start --failure-rate=20     # Start with 20% simulated failures"
    echo "  $0 configure --delay-rate=10   # Configure 10% simulated delays"
    echo "  $0 status                      # Check servers status"
    echo "  $0 stop                        # Stop all mock servers"
}

# Main function
main() {
    local command=""
    local failure_rate=$DEFAULT_FAILURE_RATE
    local delay_rate=$DEFAULT_DELAY_RATE
    local timeout=60
    
    # Process command-line arguments
    for arg in "$@"; do
        case $arg in
            start|stop|restart|status|configure)
                command=$arg
                ;;
            --failure-rate=*)
                failure_rate="${arg#*=}"
                ;;
            --delay-rate=*)
                delay_rate="${arg#*=}"
                ;;
            --timeout=*)
                timeout="${arg#*=}"
                ;;
            --help)
                show_usage
                return 0
                ;;
            *)
                echo "Unknown argument: $arg"
                show_usage
                return 1
                ;;
        esac
    done
    
    # If no command is provided, show usage and exit
    if [ -z "$command" ]; then
        show_usage
        return 1
    fi
    
    # Check dependencies
    if ! check_dependencies; then
        return 2
    fi
    
    # Execute the appropriate command
    case $command in
        start)
            start_mock_servers "$failure_rate" "$delay_rate"
            return $?
            ;;
        stop)
            stop_mock_servers
            return $?
            ;;
        restart)
            restart_mock_servers "$failure_rate" "$delay_rate"
            return $?
            ;;
        status)
            check_mock_servers_status
            return $?
            ;;
        configure)
            configure_mock_servers "$failure_rate" "$delay_rate"
            return $?
            ;;
        *)
            echo "Unknown command: $command"
            show_usage
            return 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"