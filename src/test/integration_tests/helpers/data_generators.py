"""
Provides utility functions and classes for generating test data for integration tests 
of the Borrow Rate & Locate Fee Pricing Engine. This module creates realistic test data 
for stocks, brokers, volatility metrics, and API responses to support comprehensive 
integration testing scenarios.
"""

import random
import datetime
import uuid
import logging
from decimal import Decimal
from faker import Faker
from typing import Dict, List, Any, Optional

from ..config.settings import get_test_settings, TestSettings
from src.backend.core.constants import BorrowStatus, TransactionFeeType

# Common stock tickers for test data
STOCK_TICKERS = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "GME", "AMC", "BBBY"]

# Common client IDs for test data
CLIENT_IDS = ["client_001", "premium_client", "hedge_fund_a", "broker_xyz", "test_client"]

# Default values for calculation requests
DEFAULT_POSITION_VALUE = Decimal('100000')
DEFAULT_LOAN_DAYS = 30

# Initialize faker for generating realistic data
faker = Faker()

# Setup logger
logger = logging.getLogger(__name__)


def generate_random_decimal(min_value: Decimal, max_value: Decimal, precision: int = 2) -> Decimal:
    """
    Generates a random decimal value within the specified range.
    
    Args:
        min_value: Minimum value (inclusive)
        max_value: Maximum value (inclusive)
        precision: Number of decimal places
        
    Returns:
        Random decimal value within the specified range
    """
    # Generate a random float between min_value and max_value
    random_float = random.uniform(float(min_value), float(max_value))
    
    # Round to the specified precision
    rounded_float = round(random_float, precision)
    
    # Convert to Decimal and return
    return Decimal(str(rounded_float))


def generate_iso_timestamp(days_ago: Optional[int] = None) -> str:
    """
    Generates an ISO format timestamp for the current time or with a specified offset.
    
    Args:
        days_ago: Optional number of days to subtract from current date
        
    Returns:
        ISO format timestamp string
    """
    # Get current datetime
    now = datetime.datetime.now()
    
    # If days_ago is provided, subtract that many days
    if days_ago is not None:
        now = now - datetime.timedelta(days=days_ago)
    
    # Return the datetime in ISO format
    return now.isoformat()


class DataGenerator:
    """
    Utility class for generating test data for integration tests.
    """
    
    def __init__(self, settings: Optional[TestSettings] = None):
        """
        Initializes the DataGenerator with optional test settings.
        
        Args:
            settings: Test settings to use (will get default if None)
        """
        # Get test settings using get_test_settings() if not provided
        self._settings = settings if settings is not None else get_test_settings()
        
        # Initialize Faker instance for generating realistic data
        self._faker = faker
        
        logger.info("Initialized data generator for test data creation")
    
    def generate_stock(
        self, 
        ticker: Optional[str] = None, 
        borrow_status: Optional[str] = None, 
        min_borrow_rate: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Generates test stock data with optional parameters.
        
        Args:
            ticker: Stock ticker symbol (random if None)
            borrow_status: Borrow status (random if None)
            min_borrow_rate: Minimum borrow rate (derived from status if None)
            
        Returns:
            Generated stock data dictionary
        """
        # If ticker is not provided, randomly select from STOCK_TICKERS
        if ticker is None:
            ticker = random.choice(STOCK_TICKERS)
        
        # If borrow_status is not provided, randomly select from BorrowStatus values
        if borrow_status is None:
            borrow_status = random.choice([status.value for status in BorrowStatus])
        
        # If min_borrow_rate is not provided, generate based on borrow_status
        if min_borrow_rate is None:
            if borrow_status == BorrowStatus.EASY.value:
                min_borrow_rate = generate_random_decimal(Decimal('0.01'), Decimal('0.10'), 4)
            elif borrow_status == BorrowStatus.MEDIUM.value:
                min_borrow_rate = generate_random_decimal(Decimal('0.10'), Decimal('0.30'), 4)
            else:  # HARD
                min_borrow_rate = generate_random_decimal(Decimal('0.30'), Decimal('0.80'), 4)
        
        # Create lender_api_id based on ticker
        lender_api_id = f"SEC_{ticker}"
        
        # Set last_updated to current timestamp
        last_updated = generate_iso_timestamp()
        
        # Return dictionary with all stock data
        return {
            "ticker": ticker,
            "borrow_status": borrow_status,
            "lender_api_id": lender_api_id,
            "min_borrow_rate": min_borrow_rate,
            "last_updated": last_updated
        }
    
    def generate_broker(
        self,
        client_id: Optional[str] = None,
        markup_percentage: Optional[Decimal] = None,
        transaction_fee_type: Optional[str] = None,
        transaction_amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Generates test broker data with optional parameters.
        
        Args:
            client_id: Client identifier (random if None)
            markup_percentage: Percentage markup over base rate (random if None)
            transaction_fee_type: Fee type (FLAT or PERCENTAGE, random if None)
            transaction_amount: Fee amount (derived from type if None)
            
        Returns:
            Generated broker data dictionary
        """
        # If client_id is not provided, randomly select from CLIENT_IDS
        if client_id is None:
            client_id = random.choice(CLIENT_IDS)
        
        # If markup_percentage is not provided, generate random value between 1 and 10
        if markup_percentage is None:
            markup_percentage = generate_random_decimal(Decimal('1'), Decimal('10'), 2)
        
        # If transaction_fee_type is not provided, randomly select
        if transaction_fee_type is None:
            transaction_fee_type = random.choice([fee_type.value for fee_type in TransactionFeeType])
        
        # If transaction_amount is not provided, generate based on transaction_fee_type
        if transaction_amount is None:
            if transaction_fee_type == TransactionFeeType.FLAT.value:
                transaction_amount = generate_random_decimal(Decimal('10'), Decimal('50'), 2)
            else:  # PERCENTAGE
                transaction_amount = generate_random_decimal(Decimal('0.1'), Decimal('1.0'), 3)
        
        # Return dictionary with all broker data
        return {
            "client_id": client_id,
            "markup_percentage": markup_percentage,
            "transaction_fee_type": transaction_fee_type,
            "transaction_amount": transaction_amount,
            "active": True
        }
    
    def generate_volatility(
        self,
        stock_id: Optional[str] = None,
        vol_index: Optional[Decimal] = None,
        event_risk_factor: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generates test volatility data for a stock.
        
        Args:
            stock_id: Stock ticker symbol (random if None)
            vol_index: Volatility index value (random if None)
            event_risk_factor: Event risk factor 0-10 (random if None)
            
        Returns:
            Generated volatility data dictionary
        """
        # If stock_id is not provided, randomly select from STOCK_TICKERS
        if stock_id is None:
            stock_id = random.choice(STOCK_TICKERS)
        
        # If vol_index is not provided, generate random value between 10 and 40
        if vol_index is None:
            vol_index = generate_random_decimal(Decimal('10'), Decimal('40'), 1)
        
        # If event_risk_factor is not provided, generate random value between 0 and 10
        if event_risk_factor is None:
            event_risk_factor = random.randint(0, 10)
        
        # Set timestamp to current timestamp
        timestamp = generate_iso_timestamp()
        
        # Return dictionary with all volatility data
        return {
            "stock_id": stock_id,
            "vol_index": vol_index,
            "event_risk_factor": event_risk_factor,
            "timestamp": timestamp
        }
    
    def generate_api_key(
        self,
        client_id: Optional[str] = None,
        rate_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generates test API key data.
        
        Args:
            client_id: Client identifier (random if None)
            rate_limit: Request rate limit (default 60 if None)
            
        Returns:
            Generated API key data dictionary
        """
        # If client_id is not provided, randomly select from CLIENT_IDS
        if client_id is None:
            client_id = random.choice(CLIENT_IDS)
        
        # Generate random key_id using uuid
        key_id = str(uuid.uuid4())
        
        # If rate_limit is not provided, set to 60
        if rate_limit is None:
            rate_limit = 60
        
        # Set created_at to current timestamp
        created_at = generate_iso_timestamp()
        
        # Set expires_at to 90 days from now
        expires_at = generate_iso_timestamp(days_ago=-90)
        
        # Return dictionary with all API key data
        return {
            "key_id": key_id,
            "client_id": client_id,
            "rate_limit": rate_limit,
            "created_at": created_at,
            "expires_at": expires_at
        }
    
    def generate_seclend_response(
        self,
        ticker: str,
        rate: Optional[Decimal] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates test SecLend API response data.
        
        Args:
            ticker: Stock ticker symbol
            rate: Borrow rate (derived from status if None)
            status: Borrow status (random if None)
            
        Returns:
            Generated SecLend API response
        """
        # If status is not provided, randomly select from BorrowStatus values
        if status is None:
            status = random.choice([status.value for status in BorrowStatus])
        
        # If rate is not provided, generate based on status or random value
        if rate is None:
            if status == BorrowStatus.EASY.value:
                rate = generate_random_decimal(Decimal('0.01'), Decimal('0.10'), 4)
            elif status == BorrowStatus.MEDIUM.value:
                rate = generate_random_decimal(Decimal('0.10'), Decimal('0.30'), 4)
            else:  # HARD
                rate = generate_random_decimal(Decimal('0.30'), Decimal('0.80'), 4)
        
        # Create response dictionary with rate, status, and timestamp
        return {
            "ticker": ticker,
            "rate": rate,
            "status": status,
            "timestamp": generate_iso_timestamp()
        }
    
    def generate_market_volatility_response(
        self,
        ticker: Optional[str] = None,
        volatility_index: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Generates test Market Volatility API response data.
        
        Args:
            ticker: Optional stock ticker symbol
            volatility_index: Volatility index value (random if None)
            
        Returns:
            Generated Market Volatility API response
        """
        # If volatility_index is not provided, generate random value between 10 and 40
        if volatility_index is None:
            volatility_index = generate_random_decimal(Decimal('10'), Decimal('40'), 1)
        
        # Create response dictionary with volatility_index, ticker (if provided), and timestamp
        response = {
            "value": volatility_index,
            "timestamp": generate_iso_timestamp()
        }
        
        if ticker is not None:
            response["ticker"] = ticker
        
        return response
    
    def generate_event_risk_response(
        self,
        ticker: str,
        risk_factor: Optional[int] = None,
        events: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generates test Event Calendar API response data.
        
        Args:
            ticker: Stock ticker symbol
            risk_factor: Event risk factor 0-10 (random if None)
            events: List of events (generated if None)
            
        Returns:
            Generated Event Calendar API response
        """
        # If risk_factor is not provided, generate random value between 0 and 10
        if risk_factor is None:
            risk_factor = random.randint(0, 10)
        
        # If events is not provided, generate random events based on risk_factor
        if events is None:
            events = []
            # Higher risk_factor means more events
            event_count = risk_factor // 3 + 1
            
            event_types = ["earnings", "dividend", "stock_split", "merger", "acquisition"]
            
            for _ in range(event_count):
                event_type = random.choice(event_types)
                # Generate a date within the next 30 days
                event_date = (datetime.datetime.now() + 
                             datetime.timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
                
                events.append({
                    "type": event_type,
                    "date": event_date,
                    "risk_factor": random.randint(1, 10)
                })
        
        # Create response dictionary with events list, risk_factor, and ticker
        return {
            "ticker": ticker,
            "events": events,
            "risk_factor": risk_factor
        }
    
    def generate_calculation_request(
        self,
        ticker: Optional[str] = None,
        position_value: Optional[Decimal] = None,
        loan_days: Optional[int] = None,
        client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates test calculation request data.
        
        Args:
            ticker: Stock ticker symbol (random if None)
            position_value: Position value in USD (default if None)
            loan_days: Duration of loan in days (default if None)
            client_id: Client identifier (random if None)
            
        Returns:
            Generated calculation request data
        """
        # If ticker is not provided, randomly select from STOCK_TICKERS
        if ticker is None:
            ticker = random.choice(STOCK_TICKERS)
        
        # If position_value is not provided, use DEFAULT_POSITION_VALUE
        if position_value is None:
            position_value = DEFAULT_POSITION_VALUE
        
        # If loan_days is not provided, use DEFAULT_LOAN_DAYS
        if loan_days is None:
            loan_days = DEFAULT_LOAN_DAYS
        
        # If client_id is not provided, randomly select from CLIENT_IDS
        if client_id is None:
            client_id = random.choice(CLIENT_IDS)
        
        # Return dictionary with all request parameters
        return {
            "ticker": ticker,
            "position_value": position_value,
            "loan_days": loan_days,
            "client_id": client_id
        }
    
    def generate_invalid_request(
        self,
        invalid_field: str,
        invalid_value: Any
    ) -> Dict[str, Any]:
        """
        Generates invalid request data for testing validation errors.
        
        Args:
            invalid_field: Field name to make invalid
            invalid_value: Invalid value to use
            
        Returns:
            Generated invalid request data
        """
        # Generate a valid request using generate_calculation_request
        request = self.generate_calculation_request()
        
        # Replace the specified field with the invalid value
        request[invalid_field] = invalid_value
        
        return request
    
    def generate_test_scenario(
        self,
        scenario_type: str
    ) -> Dict[str, Any]:
        """
        Generates a complete test scenario with all required data.
        
        Args:
            scenario_type: Type of scenario ('normal', 'high_volatility', 
                          'corporate_event', 'hard_to_borrow', 'market_disruption')
            
        Returns:
            Complete test scenario data
        """
        scenario_data = {}
        
        if scenario_type == "normal":
            # Normal market conditions
            ticker = "AAPL"
            broker_client_id = "client_001"
            
            scenario_data["stock"] = self.generate_stock(
                ticker=ticker,
                borrow_status=BorrowStatus.EASY.value,
                min_borrow_rate=Decimal('0.05')
            )
            
            scenario_data["broker"] = self.generate_broker(
                client_id=broker_client_id,
                markup_percentage=Decimal('5.0'),
                transaction_fee_type=TransactionFeeType.FLAT.value,
                transaction_amount=Decimal('25.0')
            )
            
            scenario_data["volatility"] = self.generate_volatility(
                stock_id=ticker,
                vol_index=Decimal('15.0'),
                event_risk_factor=0
            )
            
            scenario_data["seclend_response"] = self.generate_seclend_response(
                ticker=ticker,
                rate=Decimal('0.05'),
                status=BorrowStatus.EASY.value
            )
            
            scenario_data["market_response"] = self.generate_market_volatility_response(
                ticker=ticker,
                volatility_index=Decimal('15.0')
            )
            
            scenario_data["event_response"] = self.generate_event_risk_response(
                ticker=ticker,
                risk_factor=0,
                events=[]
            )
            
            scenario_data["request"] = self.generate_calculation_request(
                ticker=ticker,
                position_value=DEFAULT_POSITION_VALUE,
                loan_days=DEFAULT_LOAN_DAYS,
                client_id=broker_client_id
            )
            
        elif scenario_type == "high_volatility":
            # High volatility market
            ticker = "TSLA"
            broker_client_id = "premium_client"
            
            scenario_data["stock"] = self.generate_stock(
                ticker=ticker,
                borrow_status=BorrowStatus.MEDIUM.value,
                min_borrow_rate=Decimal('0.20')
            )
            
            scenario_data["broker"] = self.generate_broker(
                client_id=broker_client_id,
                markup_percentage=Decimal('7.5'),
                transaction_fee_type=TransactionFeeType.PERCENTAGE.value,
                transaction_amount=Decimal('0.5')
            )
            
            scenario_data["volatility"] = self.generate_volatility(
                stock_id=ticker,
                vol_index=Decimal('35.0'),
                event_risk_factor=3
            )
            
            scenario_data["seclend_response"] = self.generate_seclend_response(
                ticker=ticker,
                rate=Decimal('0.25'),
                status=BorrowStatus.MEDIUM.value
            )
            
            scenario_data["market_response"] = self.generate_market_volatility_response(
                ticker=ticker,
                volatility_index=Decimal('35.0')
            )
            
            scenario_data["event_response"] = self.generate_event_risk_response(
                ticker=ticker,
                risk_factor=3,
                events=[{
                    "type": "earnings",
                    "date": (datetime.datetime.now() + datetime.timedelta(days=15)).strftime("%Y-%m-%d"),
                    "risk_factor": 3
                }]
            )
            
            scenario_data["request"] = self.generate_calculation_request(
                ticker=ticker,
                position_value=Decimal('150000'),
                loan_days=60,
                client_id=broker_client_id
            )
            
        elif scenario_type == "corporate_event":
            # Corporate event scenario
            ticker = "MSFT"
            broker_client_id = "hedge_fund_a"
            
            scenario_data["stock"] = self.generate_stock(
                ticker=ticker,
                borrow_status=BorrowStatus.MEDIUM.value,
                min_borrow_rate=Decimal('0.15')
            )
            
            scenario_data["broker"] = self.generate_broker(
                client_id=broker_client_id,
                markup_percentage=Decimal('8.0'),
                transaction_fee_type=TransactionFeeType.FLAT.value,
                transaction_amount=Decimal('40.0')
            )
            
            scenario_data["volatility"] = self.generate_volatility(
                stock_id=ticker,
                vol_index=Decimal('20.0'),
                event_risk_factor=8
            )
            
            scenario_data["seclend_response"] = self.generate_seclend_response(
                ticker=ticker,
                rate=Decimal('0.18'),
                status=BorrowStatus.MEDIUM.value
            )
            
            scenario_data["market_response"] = self.generate_market_volatility_response(
                ticker=ticker,
                volatility_index=Decimal('20.0')
            )
            
            # Event with high risk factor
            scenario_data["event_response"] = self.generate_event_risk_response(
                ticker=ticker,
                risk_factor=8,
                events=[
                    {
                        "type": "earnings",
                        "date": (datetime.datetime.now() + datetime.timedelta(days=5)).strftime("%Y-%m-%d"),
                        "risk_factor": 8
                    },
                    {
                        "type": "dividend",
                        "date": (datetime.datetime.now() + datetime.timedelta(days=10)).strftime("%Y-%m-%d"),
                        "risk_factor": 6
                    }
                ]
            )
            
            scenario_data["request"] = self.generate_calculation_request(
                ticker=ticker,
                position_value=Decimal('200000'),
                loan_days=15,
                client_id=broker_client_id
            )
            
        elif scenario_type == "hard_to_borrow":
            # Hard-to-borrow securities
            ticker = "GME"
            broker_client_id = "broker_xyz"
            
            scenario_data["stock"] = self.generate_stock(
                ticker=ticker,
                borrow_status=BorrowStatus.HARD.value,
                min_borrow_rate=Decimal('0.50')
            )
            
            scenario_data["broker"] = self.generate_broker(
                client_id=broker_client_id,
                markup_percentage=Decimal('10.0'),
                transaction_fee_type=TransactionFeeType.PERCENTAGE.value,
                transaction_amount=Decimal('1.0')
            )
            
            scenario_data["volatility"] = self.generate_volatility(
                stock_id=ticker,
                vol_index=Decimal('30.0'),
                event_risk_factor=5
            )
            
            scenario_data["seclend_response"] = self.generate_seclend_response(
                ticker=ticker,
                rate=Decimal('0.65'),
                status=BorrowStatus.HARD.value
            )
            
            scenario_data["market_response"] = self.generate_market_volatility_response(
                ticker=ticker,
                volatility_index=Decimal('30.0')
            )
            
            scenario_data["event_response"] = self.generate_event_risk_response(
                ticker=ticker,
                risk_factor=5,
                events=[{
                    "type": "earnings",
                    "date": (datetime.datetime.now() + datetime.timedelta(days=20)).strftime("%Y-%m-%d"),
                    "risk_factor": 5
                }]
            )
            
            scenario_data["request"] = self.generate_calculation_request(
                ticker=ticker,
                position_value=Decimal('50000'),
                loan_days=7,
                client_id=broker_client_id
            )
            
        elif scenario_type == "market_disruption":
            # Market disruption / extreme volatility
            ticker = "AMC"
            broker_client_id = "test_client"
            
            scenario_data["stock"] = self.generate_stock(
                ticker=ticker,
                borrow_status=BorrowStatus.HARD.value,
                min_borrow_rate=Decimal('0.60')
            )
            
            scenario_data["broker"] = self.generate_broker(
                client_id=broker_client_id,
                markup_percentage=Decimal('12.0'),
                transaction_fee_type=TransactionFeeType.FLAT.value,
                transaction_amount=Decimal('50.0')
            )
            
            scenario_data["volatility"] = self.generate_volatility(
                stock_id=ticker,
                vol_index=Decimal('40.0'),
                event_risk_factor=10
            )
            
            scenario_data["seclend_response"] = self.generate_seclend_response(
                ticker=ticker,
                rate=Decimal('0.80'),
                status=BorrowStatus.HARD.value
            )
            
            scenario_data["market_response"] = self.generate_market_volatility_response(
                ticker=ticker,
                volatility_index=Decimal('40.0')
            )
            
            scenario_data["event_response"] = self.generate_event_risk_response(
                ticker=ticker,
                risk_factor=10,
                events=[
                    {
                        "type": "merger",
                        "date": (datetime.datetime.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d"),
                        "risk_factor": 10
                    },
                    {
                        "type": "earnings",
                        "date": (datetime.datetime.now() + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
                        "risk_factor": 9
                    }
                ]
            )
            
            scenario_data["request"] = self.generate_calculation_request(
                ticker=ticker,
                position_value=Decimal('75000'),
                loan_days=3,
                client_id=broker_client_id
            )
            
        else:
            raise ValueError(f"Unknown scenario type: {scenario_type}")
        
        return scenario_data