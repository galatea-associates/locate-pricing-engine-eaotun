import json
import logging
import random
import yaml
from locust import HttpUser, task, TaskSet, between, tag

# Set up logger
logger = logging.getLogger(__name__)

# Load configuration
try:
    with open("../../load_testing/config.yaml", "r") as config_file:
        CONFIG = yaml.safe_load(config_file)
except Exception as e:
    logger.error(f"Failed to load configuration: {str(e)}")
    CONFIG = {}  # Default empty config as fallback


class CalculateFeeTasks(TaskSet):
    """Task set defining the calculate fee API endpoint testing behavior"""
    
    def __init__(self, parent):
        """Initialize the task set with test data and configuration"""
        super().__init__(parent)
        
        # Load test data from configuration
        test_data = CONFIG.get("test_data", {})
        
        # Extract tickers from test data
        self.tickers = [ticker["symbol"] for ticker in test_data.get("tickers", [])]
        if not self.tickers:
            # Fallback tickers if config is missing
            self.tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "GME"]
            
        # Extract client IDs from test data
        self.client_ids = [client["id"] for client in test_data.get("client_ids", [])]
        if not self.client_ids:
            # Fallback client IDs if config is missing
            self.client_ids = ["big_fund_001", "retail_broker_002", "hedge_fund_003"]
            
        # Set up API headers with authentication
        env = CONFIG.get("environments", {}).get("development", {})
        self.headers = env.get("headers", {})
        api_key = env.get("api_key", "test_api_key")  # Default to test key if not provided
        self.headers["X-API-Key"] = api_key
        
        # Initialize metrics for tracking test results
        self.success_count = 0
        self.error_count = 0
    
    @task(2)
    @tag("calculate_fee", "get")
    def calculate_fee_get(self):
        """Task that simulates a user requesting a locate fee calculation using GET method"""
        # Select a random ticker from the test data
        ticker = random.choice(self.tickers)
        
        # Select a random client ID from the test data
        client_id = random.choice(self.client_ids)
        
        # Generate a random position value within configured range
        position_value = self.generate_position_value()
        
        # Generate a random loan days value within configured range
        loan_days = self.generate_loan_days()
        
        # Construct the API endpoint URL with query parameters
        params = {
            "ticker": ticker,
            "position_value": position_value,
            "loan_days": loan_days,
            "client_id": client_id
        }
        
        endpoint = CONFIG.get("scenarios", {}).get("calculate_fee", {}).get("endpoint", "/api/v1/calculate-locate")
        
        try:
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
                    response_data = response.json()
                    
                    # Check for expected fields in the response
                    if (response_data.get("status") == "success" and 
                        "total_fee" in response_data and 
                        "breakdown" in response_data and
                        "borrow_rate_used" in response_data):
                        
                        self.success_count += 1
                        logger.debug(f"Successful GET request for ticker {ticker}: total_fee={response_data.get('total_fee')}")
                        response.success()
                    else:
                        error_msg = f"Invalid response content: {response_data}"
                        logger.warning(error_msg)
                        response.failure(error_msg)
                        self.error_count += 1
                else:
                    error_msg = f"Request failed with status code {response.status_code}: {response.text}"
                    logger.warning(error_msg)
                    response.failure(error_msg)
                    self.error_count += 1
        
        except Exception as e:
            # Log relevant information about the request and response
            error_msg = f"Exception during GET request: {str(e)}"
            logger.error(error_msg)
            self.error_count += 1
    
    @task(3)
    @tag("calculate_fee", "post")
    def calculate_fee_post(self):
        """Task that simulates a user requesting a locate fee calculation using POST method"""
        # Select a random ticker from the test data
        ticker = random.choice(self.tickers)
        
        # Select a random client ID from the test data
        client_id = random.choice(self.client_ids)
        
        # Generate a random position value within configured range
        position_value = self.generate_position_value()
        
        # Generate a random loan days value within configured range
        loan_days = self.generate_loan_days()
        
        # Construct the API endpoint URL
        endpoint = CONFIG.get("scenarios", {}).get("calculate_fee", {}).get("endpoint", "/api/v1/calculate-locate")
        
        # Prepare the request payload with all parameters
        payload = {
            "ticker": ticker,
            "position_value": position_value,
            "loan_days": loan_days,
            "client_id": client_id
        }
        
        try:
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
                    response_data = response.json()
                    
                    # Check for expected fields in the response
                    if (response_data.get("status") == "success" and 
                        "total_fee" in response_data and 
                        "breakdown" in response_data and
                        "borrow_rate_used" in response_data):
                        
                        self.success_count += 1
                        logger.debug(f"Successful POST request for ticker {ticker}: total_fee={response_data.get('total_fee')}")
                        response.success()
                    else:
                        error_msg = f"Invalid response content: {response_data}"
                        logger.warning(error_msg)
                        response.failure(error_msg)
                        self.error_count += 1
                else:
                    error_msg = f"Request failed with status code {response.status_code}: {response.text}"
                    logger.warning(error_msg)
                    response.failure(error_msg)
                    self.error_count += 1
        
        except Exception as e:
            # Log relevant information about the request and response
            error_msg = f"Exception during POST request: {str(e)}"
            logger.error(error_msg)
            self.error_count += 1
    
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


class CalculateFeeScenario(HttpUser):
    """User class that simulates clients requesting fee calculations from the API"""
    
    # Define tasks for this user
    tasks = [CalculateFeeTasks]
    
    # Set wait time between requests
    wait_time = between(1, 5)  # Default 1-5 seconds between tasks
    
    def __init__(self, environment):
        """Initialize the user with configuration settings"""
        super().__init__(environment)
        
        # Configure wait time from config if available
        think_time = CONFIG.get("scenarios", {}).get("mixed_workload", {}).get("think_time", {})
        min_time = think_time.get("min", 1000) / 1000  # Convert ms to seconds
        max_time = think_time.get("max", 5000) / 1000  # Convert ms to seconds
        self.wait_time = between(min_time, max_time)
        
        # Configure host from environment or default configuration
        if not self.host:
            env = CONFIG.get("environments", {}).get("development", {})
            self.host = env.get("base_url", "https://dev-api.pricing-engine.example.com")
    
    def on_start(self):
        """Setup method called when a simulated user starts"""
        logger.info(f"Starting user simulation for {self.host}")
        # Initialize any user-specific state or configuration