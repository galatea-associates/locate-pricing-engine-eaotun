#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Error handling - display error message and exit on error
trap 'echo "Error occurred at line $LINENO"; exit 1' ERR

# Define global variables
SCRIPT_DIR=$(dirname "${BASH_SOURCE[0]}")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/../../..")
TEST_DIR="$PROJECT_ROOT/src/test"
DOCKER_COMPOSE_FILE="$TEST_DIR/docker/docker-compose.test.yml"
ENV_FILE="$TEST_DIR/.env.test"
DEFAULT_ENV_FILE="$TEST_DIR/.env.example"
TEST_DATA_DIR="$TEST_DIR/data_generators"
TEST_REPORT_DIR="$TEST_DIR/reports"
DEFAULT_FAILURE_RATE="0"
DEFAULT_DELAY_RATE="0"

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
        return 2
    fi

    if ! command -v docker-compose &> /dev/null; then
        echo "Error: docker-compose is not installed or not in PATH"
        return 2
    fi

    if ! command -v psql &> /dev/null; then
        echo "Error: psql is not installed or not in PATH"
        return 2
    fi

    echo "All dependencies are available"
    return 0
}

# Function to create a test environment file if it doesn't exist
create_env_file() {
    print_header "Creating environment file"

    if [ ! -f "$ENV_FILE" ]; then
        echo "Creating $ENV_FILE from $DEFAULT_ENV_FILE"
        cp "$DEFAULT_ENV_FILE" "$ENV_FILE"
        echo "Please update the values in $ENV_FILE if needed"
    else
        echo "$ENV_FILE already exists"
    fi

    return 0
}

# Function to start the test environment containers
start_containers() {
    print_header "Starting containers"

    echo "Running docker-compose up -d"
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d > /dev/null 2>&1

    # Wait for containers to be healthy
    if ! wait_for_healthy; then
        echo "Error: Failed to start containers"
        return 3
    fi

    echo "Containers started successfully"
    return 0
}

# Function to start the mock external API servers
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

    # Call run_mock_servers.sh script to start mock servers
    if ! "$SCRIPT_DIR/run_mock_servers.sh" "$failure_rate" "$delay_rate"; then
        echo "Error: Failed to start mock servers"
        return 5
    fi

    echo "Mock servers started successfully"
    return 0
}

# Function to initialize the test database with schema and test data
initialize_database() {
    print_header "Initializing database"

    # Wait for database container to be ready
    echo "Waiting for database container to be ready..."
    sleep 10

    # Run database migrations using alembic
    echo "Running database migrations using alembic"
    cd "$PROJECT_ROOT/backend"
    alembic upgrade head
    cd "$SCRIPT_DIR"

    # Generate and load test data using data generators
    echo "Generating and loading test data using data generators"
    # Add data generation steps here

    echo "Database initialized successfully"
    return 0
}

# Function to initialize the Redis cache with any required data
initialize_redis() {
    print_header "Initializing Redis"

    # Wait for Redis container to be ready
    echo "Waiting for Redis container to be ready..."
    sleep 5

    # Flush Redis database to ensure clean state
    echo "Flushing Redis database to ensure clean state"
    docker exec -i $(docker-compose -f "$DOCKER_COMPOSE_FILE" ps -q redis) redis-cli flushall

    echo "Redis initialized successfully"
    return 0
}

# Function to create necessary directories for test execution
create_directories() {
    print_header "Creating directories"

    # Create test report directory if it doesn't exist
    if [ ! -d "$TEST_REPORT_DIR" ]; then
        echo "Creating test report directory: $TEST_REPORT_DIR"
        mkdir -p "$TEST_REPORT_DIR"
    else
        echo "Test report directory already exists: $TEST_REPORT_DIR"
    fi

    # Create any other required directories
    # Add directory creation steps here

    # Set appropriate permissions
    # Add permission setting steps here

    echo "Directories created successfully"
    return 0
}

# Function to wait for containers to report healthy status
wait_for_healthy() {
    local service_name
    local timeout_seconds

    # Wait for API service to be healthy
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" wait api; then
        echo "Error: API service did not become healthy"
        return 1
    fi

    # Wait for DB service to be healthy
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" wait db; then
        echo "Error: DB service did not become healthy"
        return 1
    fi

    # Wait for Redis service to be healthy
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" wait redis; then
        echo "Error: Redis service did not become healthy"
        return 1
    fi

    # Wait for SecLend API service to be healthy
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" wait seclend-api; then
        echo "Error: SecLend API service did not become healthy"
        return 1
    fi

    # Wait for Market API service to be healthy
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" wait market-api; then
        echo "Error: Market API service did not become healthy"
        return 1
    fi

    # Wait for Event API service to be healthy
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" wait event-api; then
        echo "Error: Event API service did not become healthy"
        return 1
    fi

    return 0
}

# Function to set up the complete test environment
setup_test_environment() {
    local failure_rate=${1:-$DEFAULT_FAILURE_RATE}
    local delay_rate=${2:-$DEFAULT_DELAY_RATE}

    print_header "Setting up test environment"

    # Check dependencies
    if ! check_dependencies; then
        return 2
    fi

    # Create environment file
    if ! create_env_file; then
        return 1
    fi

    # Create necessary directories
    if ! create_directories; then
        return 1
    fi

    # Start containers
    if ! start_containers; then
        return 3
    fi

    # Start mock servers with specified failure and delay rates
    if ! start_mock_servers "$failure_rate" "$delay_rate"; then
        return 5
    fi

    # Initialize database
    if ! initialize_database; then
        return 4
    fi

    # Initialize Redis
    if ! initialize_redis; then
        return 4
    fi

    echo "Test environment setup completed successfully"
    echo "API URL:           http://localhost:8000"
    echo "Database URL:      postgresql://postgres:postgres@localhost:5433/borrow_rate_engine_test"
    echo "Redis URL:         redis://localhost:6380/0"
    echo "SecLend API:           http://localhost:8001"
    echo "Market Volatility API: http://localhost:8002"
    echo "Event Calendar API:    http://localhost:8003"

    return 0
}

# Function to clean up the test environment
cleanup_environment() {
    print_header "Cleaning up environment"

    # Stop and remove containers
    echo "Stopping and removing containers"
    docker-compose -f "$DOCKER_COMPOSE_FILE" down > /dev/null 2>&1

    # Stop mock servers
    echo "Stopping mock servers"
    # Add mock server stopping steps here

    # Remove any temporary files
    echo "Removing any temporary files"
    # Add temporary file removal steps here

    echo "Environment cleanup completed"
    return 0
}

# Function to display usage information
show_usage() {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --setup         Set up the test environment (default action)"
    echo "  --cleanup       Clean up the test environment"
    echo "  --failure-rate  Percentage of mock API requests that should fail (0-100)"
    echo "  --delay-rate    Percentage of mock API requests that should be delayed (0-100)"
    echo "  --help          Show this help message"
    echo
    echo "Examples:"
    echo "  $0 --setup"
    echo "  $0 --cleanup"
    echo "  $0 --failure-rate=20"
    echo "  $0 --delay-rate=10"
}

# Main function
main() {
    local action="setup"
    local failure_rate="$DEFAULT_FAILURE_RATE"
    local delay_rate="$DEFAULT_DELAY_RATE"

    # Process command line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --setup)
                action="setup"
                shift
                ;;
            --cleanup)
                action="cleanup"
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
            --help)
                show_usage
                return 0
                ;;
            *)
                echo "Unknown parameter: $1"
                show_usage
                return 1
                ;;
        esac
    done

    # Execute the appropriate action
    case $action in
        setup)
            setup_test_environment "$failure_rate" "$delay_rate"
            local exit_code=$?
            ;;
        cleanup)
            cleanup_environment
            local exit_code=$?
            ;;
        *)
            echo "Invalid action: $action"
            show_usage
            local exit_code=1
            ;;
    esac

    return $exit_code
}

# Execute main function with all arguments
main "$@"
exit $?