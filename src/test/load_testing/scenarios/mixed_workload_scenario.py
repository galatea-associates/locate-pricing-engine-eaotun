import random
import logging
import json
from locust import HttpUser, task, TaskSet, between, tag

# Import the tasks from other scenarios
from .borrow_rate_scenario import BorrowRateTasks
from .calculate_fee_scenario import CalculateFeeTasks

# Import configuration module
from ...load_testing.config import yaml

# Initialize logger
logger = logging.getLogger(__name__)

# Load test configuration
CONFIG = yaml


class MixedWorkloadTasks(TaskSet):
    """Task set defining a mixed workload of borrow rate and fee calculation API requests"""

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
        self.metrics = {
            "successful_requests": 0,
            "failed_requests": 0,
            "borrow_rate_requests": 0,
            "calculate_fee_requests": 0
        }
        logger.info("MixedWorkloadTasks initialized with %d tickers and %d client IDs", 
                  len(self.tickers), len(self.client_ids))

    @task(4)
    @tag('mixed', 'borrow_rate')
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
                        self.metrics["successful_requests"] += 1
                        self.metrics["borrow_rate_requests"] += 1
                        response.success()
                    else:
                        logger.warning(f"Response missing required fields: {data}")
                        self.metrics["failed_requests"] += 1
                        response.failure("Response missing required fields")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response: {response.text}")
                    self.metrics["failed_requests"] += 1
                    response.failure("Invalid JSON response")
            else:
                logger.warning(f"Failed to get borrow rate for {ticker}: {response.status_code}")
                self.metrics["failed_requests"] += 1
                response.failure(f"HTTP {response.status_code}")

    @task(3)
    @tag('mixed', 'calculate_fee')
    def calculate_fee_post(self):
        """Task that simulates a user requesting a locate fee calculation using POST method"""
        if not self.tickers or not self.client_ids:
            logger.error("No tickers or client IDs available for testing")
            return
            
        # Select a random ticker from the test data
        ticker = random.choice(self.tickers)
        
        # Select a random client ID from the test data
        client_id = random.choice(self.client_ids)
        
        # Generate a random position value within configured range
        position_value = self.generate_position_value()
        
        # Generate a random loan days value within configured range
        loan_days = self.generate_loan_days()
        
        # Construct the API endpoint URL
        endpoint = "/api/v1/calculate-locate"
        
        # Prepare the request payload with all parameters
        payload = {
            "ticker": ticker,
            "position_value": position_value,
            "loan_days": loan_days,
            "client_id": client_id
        }
        
        # Send a POST request to the calculate-locate endpoint
        with self.client.post(
            endpoint, 
            json=payload,
            headers=self.headers,
            name="Calculate Fee (POST)",
            catch_response=True
        ) as response:
            # Validate the response status code and content
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check if required fields are present in response
                    if ("status" in data and 
                        data["status"] == "success" and
                        "total_fee" in data and 
                        "breakdown" in data and
                        "borrow_rate_used" in data):
                        logger.debug(f"Successfully calculated fee for {ticker}: {data['total_fee']}")
                        self.metrics["successful_requests"] += 1
                        self.metrics["calculate_fee_requests"] += 1
                        response.success()
                    else:
                        logger.warning(f"Response missing required fields: {data}")
                        self.metrics["failed_requests"] += 1
                        response.failure("Response missing required fields")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response: {response.text}")
                    self.metrics["failed_requests"] += 1
                    response.failure("Invalid JSON response")
            else:
                logger.warning(f"Failed to calculate fee for {ticker}: {response.status_code}")
                self.metrics["failed_requests"] += 1
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    @tag('mixed', 'custom_rate')
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
                        self.metrics["successful_requests"] += 1
                        self.metrics["borrow_rate_requests"] += 1
                        response.success()
                    else:
                        logger.warning(f"Response missing required fields: {data}")
                        self.metrics["failed_requests"] += 1
                        response.failure("Response missing required fields")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response: {response.text}")
                    self.metrics["failed_requests"] += 1
                    response.failure("Invalid JSON response")
            else:
                logger.warning(f"Failed to calculate custom rate for {ticker}: {response.status_code}")
                self.metrics["failed_requests"] += 1
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    @tag('mixed', 'calculate_fee_get')
    def calculate_fee_get(self):
        """Task that simulates a user requesting a locate fee calculation using GET method"""
        if not self.tickers or not self.client_ids:
            logger.error("No tickers or client IDs available for testing")
            return
            
        # Select a random ticker from the test data
        ticker = random.choice(self.tickers)
        
        # Select a random client ID from the test data
        client_id = random.choice(self.client_ids)
        
        # Generate a random position value within configured range
        position_value = self.generate_position_value()
        
        # Generate a random loan days value within configured range
        loan_days = self.generate_loan_days()
        
        # Construct the API endpoint URL with query parameters
        endpoint = "/api/v1/calculate-locate"
        params = {
            "ticker": ticker,
            "position_value": position_value,
            "loan_days": loan_days,
            "client_id": client_id
        }
        
        # Send a GET request to the calculate-locate endpoint
        with self.client.get(
            endpoint, 
            params=params,
            headers=self.headers,
            name="Calculate Fee (GET)",
            catch_response=True
        ) as response:
            # Validate the response status code and content
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check if required fields are present in response
                    if ("status" in data and 
                        data["status"] == "success" and
                        "total_fee" in data and 
                        "breakdown" in data and
                        "borrow_rate_used" in data):
                        logger.debug(f"Successfully calculated fee for {ticker}: {data['total_fee']}")
                        self.metrics["successful_requests"] += 1
                        self.metrics["calculate_fee_requests"] += 1
                        response.success()
                    else:
                        logger.warning(f"Response missing required fields: {data}")
                        self.metrics["failed_requests"] += 1
                        response.failure("Response missing required fields")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response: {response.text}")
                    self.metrics["failed_requests"] += 1
                    response.failure("Invalid JSON response")
            else:
                logger.warning(f"Failed to calculate fee for {ticker}: {response.status_code}")
                self.metrics["failed_requests"] += 1
                response.failure(f"HTTP {response.status_code}")

    def generate_position_value(self):
        """Generate a random position value based on configuration"""
        # Get min and max position values from configuration
        position_config = CONFIG.get("test_data", {}).get("position_values", {})
        min_value = position_config.get("parameters", {}).get("min", 10000)
        max_value = position_config.get("parameters", {}).get("max", 10000000)
        
        # Get distribution type from configuration
        distribution = position_config.get("distribution", "random")
        
        # Generate random value using appropriate distribution
        if distribution == "log_normal":
            # Log-normal distribution better models financial values
            mean = position_config.get("parameters", {}).get("mean", 100000)
            std_dev = position_config.get("parameters", {}).get("std_dev", 500000)
            
            # Generate log-normal value and scale to desired range
            value = random.lognormvariate(mean / std_dev, 1)
            value = min(max(value * mean, min_value), max_value)
        else:
            # Default to uniform distribution
            value = random.uniform(min_value, max_value)
        
        # Return the generated position value
        return round(value, 2)

    def generate_loan_days(self):
        """Generate a random loan days value based on configuration"""
        # Get min and max loan days from configuration
        loan_days_config = CONFIG.get("test_data", {}).get("loan_days", {})
        
        # Get distribution type from configuration
        distribution = loan_days_config.get("distribution", "random")
        
        # Generate random value using appropriate distribution
        if distribution == "weighted_range":
            ranges = loan_days_config.get("ranges", [])
            
            if ranges:
                # Select range based on weighted probability
                total_weight = sum(r.get("weight", 1) for r in ranges)
                r = random.random() * total_weight
                cumulative_weight = 0
                
                for range_item in ranges:
                    cumulative_weight += range_item.get("weight", 1)
                    if r <= cumulative_weight:
                        # Generate random days within selected range
                        min_days, max_days = range_item.get("range", [1, 30])
                        return random.randint(min_days, max_days)
                
            # Fallback if no ranges defined
            return random.randint(1, 30)
        else:
            # Default to uniform distribution between 1-180 days
            return random.randint(1, 180)

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


class MixedWorkloadScenario(HttpUser):
    """User class that simulates clients with a mixed pattern of borrow rate and fee calculation requests"""
    
    # Define the task set
    tasks = [MixedWorkloadTasks]
    
    # Set wait time between tasks using the between function
    wait_time = between(
        CONFIG.get("scenarios", {}).get("mixed_workload", {}).get("think_time", {}).get("min", 1000) / 1000,
        CONFIG.get("scenarios", {}).get("mixed_workload", {}).get("think_time", {}).get("max", 5000) / 1000
    )
    
    def __init__(self, environment):
        """Initialize the user with configuration settings"""
        super().__init__(environment)
        
        # Configure host from environment or default configuration
        if not self.host:
            env = CONFIG.get("environments", {}).get("staging", {})
            self.host = env.get("base_url", "")
            
    def on_start(self):
        """Setup method called when a simulated user starts"""
        logger.info("Starting MixedWorkloadScenario user")
        
        # Initialize any user-specific state or configuration