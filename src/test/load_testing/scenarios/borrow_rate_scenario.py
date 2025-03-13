import random
import logging
import json
from locust import HttpUser, task, TaskSet, between, tag
import yaml  # from ../../load_testing/config

# Initialize logger
logger = logging.getLogger(__name__)

# Load test configuration from yaml module
CONFIG = yaml


class BorrowRateTasks(TaskSet):
    """Task set defining the borrow rate API endpoint testing behavior"""

    def __init__(self, parent):
        """Initialize the task set with test data and configuration"""
        super().__init__(parent)
        
        # Load test data from configuration
        self.tickers = [item["symbol"] for item in CONFIG.get("test_data", {}).get("tickers", [])]
        self.client_ids = [item["id"] for item in CONFIG.get("test_data", {}).get("client_ids", [])]
        
        # Set up API headers with authentication
        env = CONFIG.get("environments", {}).get("staging", {})  # Default to staging
        self.headers = env.get("headers", {"Content-Type": "application/json", "Accept": "application/json"})
        self.headers["X-API-Key"] = env.get("api_key", "${API_KEY}")  # API key will be replaced at runtime
        
        # Initialize metrics for tracking test results
        self.successful_requests = 0
        self.failed_requests = 0
        logger.info("BorrowRateTasks initialized with %d tickers and %d client IDs", 
                    len(self.tickers), len(self.client_ids))

    @task(3)
    @tag("borrow_rate", "get")
    def get_borrow_rate(self):
        """Task that simulates a user requesting the current borrow rate for a random ticker"""
        if not self.tickers:
            logger.error("No tickers available for testing")
            return
            
        # Select a random ticker from the test data
        ticker = random.choice(self.tickers)
        
        # Construct the API endpoint URL
        endpoint = f"/api/v1/rates/{ticker}"
        
        # Send a GET request to the borrow rate endpoint
        with self.client.get(
            endpoint, 
            headers=self.headers, 
            name="Get Borrow Rate",
            catch_response=True
        ) as response:
            # Validate the response status code and content
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check if required fields are present in response
                    if "current_rate" in data and "borrow_status" in data:
                        logger.debug(f"Successfully retrieved borrow rate for {ticker}: {data['current_rate']}")
                        self.successful_requests += 1
                        response.success()
                    else:
                        logger.warning(f"Response missing required fields: {data}")
                        self.failed_requests += 1
                        response.failure("Response missing required fields")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response: {response.text}")
                    self.failed_requests += 1
                    response.failure("Invalid JSON response")
            else:
                logger.warning(f"Failed to get borrow rate for {ticker}: {response.status_code}")
                self.failed_requests += 1
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    @tag("borrow_rate", "custom")
    def get_borrow_rate_with_custom_params(self):
        """Task that simulates a user requesting a borrow rate with custom volatility and event risk parameters"""
        if not self.tickers:
            logger.error("No tickers available for testing")
            return
            
        # Select a random ticker from the test data
        ticker = random.choice(self.tickers)
        
        # Generate random volatility index within configured range
        volatility_index = self.generate_volatility_index()
        
        # Generate random event risk factor within configured range
        event_risk_factor = self.generate_event_risk_factor()
        
        # Construct the API endpoint URL with query parameters
        endpoint = f"/api/v1/calculate-rate?ticker={ticker}&volatility_index={volatility_index}&event_risk_factor={event_risk_factor}"
        
        # Send a GET request to the calculate custom rate endpoint
        with self.client.get(
            endpoint, 
            headers=self.headers, 
            name="Get Custom Borrow Rate",
            catch_response=True
        ) as response:
            # Validate the response status code and content
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check if required fields are present in response
                    if "calculated_rate" in data:
                        logger.debug(f"Successfully calculated custom rate for {ticker}: {data['calculated_rate']}")
                        self.successful_requests += 1
                        response.success()
                    else:
                        logger.warning(f"Response missing required fields: {data}")
                        self.failed_requests += 1
                        response.failure("Response missing required fields")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response: {response.text}")
                    self.failed_requests += 1
                    response.failure("Invalid JSON response")
            else:
                logger.warning(f"Failed to calculate custom rate for {ticker}: {response.status_code}")
                self.failed_requests += 1
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    @tag("borrow_rate", "status")
    def get_borrow_rates_by_status(self):
        """Task that simulates a user requesting borrow rates for stocks with a specific status"""
        # Select a random borrow status (EASY, MEDIUM, HARD)
        statuses = ["EASY", "MEDIUM", "HARD"]
        status = random.choice(statuses)
        
        # Construct the API endpoint URL
        endpoint = f"/api/v1/rates?status={status}"
        
        # Send a GET request to the borrow rates by status endpoint
        with self.client.get(
            endpoint, 
            headers=self.headers, 
            name="Get Borrow Rates By Status",
            catch_response=True
        ) as response:
            # Validate the response status code and content
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check if response is a list of rate data
                    if isinstance(data, list):
                        logger.debug(f"Successfully retrieved {len(data)} {status} borrow rates")
                        self.successful_requests += 1
                        response.success()
                    else:
                        logger.warning(f"Expected list response but got: {type(data)}")
                        self.failed_requests += 1
                        response.failure("Expected list response")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response: {response.text}")
                    self.failed_requests += 1
                    response.failure("Invalid JSON response")
            else:
                logger.warning(f"Failed to get {status} borrow rates: {response.status_code}")
                self.failed_requests += 1
                response.failure(f"HTTP {response.status_code}")

    def generate_volatility_index(self):
        """Generate a random volatility index based on configuration"""
        # Default range if configuration is not available
        min_volatility = 10.0
        max_volatility = 50.0
        
        # Try to get range from configuration
        volatility_config = CONFIG.get("test_data", {}).get("volatility_index", {})
        if isinstance(volatility_config, dict):
            min_volatility = float(volatility_config.get("min", min_volatility))
            max_volatility = float(volatility_config.get("max", max_volatility))
        
        # Generate random value within the range
        return round(random.uniform(min_volatility, max_volatility), 2)

    def generate_event_risk_factor(self):
        """Generate a random event risk factor based on configuration"""
        # Default range if configuration is not available
        min_risk = 0
        max_risk = 10
        
        # Try to get range from configuration
        risk_config = CONFIG.get("test_data", {}).get("event_risk_factor", {})
        if isinstance(risk_config, dict):
            min_risk = int(risk_config.get("min", min_risk))
            max_risk = int(risk_config.get("max", max_risk))
        
        # Generate random integer value within the range
        return random.randint(min_risk, max_risk)


class BorrowRateScenario(HttpUser):
    """User class that simulates clients requesting borrow rates from the API"""
    tasks = [BorrowRateTasks]
    
    # Set wait time between tasks using the between function
    wait_time = between(
        CONFIG.get("scenarios", {}).get("mixed_workload", {}).get("think_time", {}).get("min", 1000) / 1000,
        CONFIG.get("scenarios", {}).get("mixed_workload", {}).get("think_time", {}).get("max", 5000) / 1000
    )
    
    def on_start(self):
        """Setup method called when a simulated user starts"""
        logger.info("Starting BorrowRateScenario user")
        
        # Get default environment from configuration
        environment = CONFIG.get("environments", {}).get("staging", {})
        
        # Set host if not already specified via command line
        if not self.host:
            self.host = environment.get("base_url", "")
            logger.info(f"Using host from configuration: {self.host}")