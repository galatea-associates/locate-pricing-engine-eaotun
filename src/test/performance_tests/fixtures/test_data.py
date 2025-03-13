"""
Provides test data fixtures for performance testing of the Borrow Rate & Locate Fee Pricing Engine.

This module contains predefined test data sets and data generation functions for various
market scenarios to support comprehensive performance testing under different conditions.
"""

import random
import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional

import pytest  # pytest 7.4.0+

from ..config.settings import get_test_settings
from src.backend.core.constants import BorrowStatus, TransactionFeeType
from src.backend.schemas.stock import StockSchema
from src.backend.schemas.broker import BrokerSchema

# Common test data
COMMON_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "BAC", "WMT"]
POSITION_VALUES = [10000, 50000, 100000, 500000, 1000000]
LOAN_DAYS = [1, 7, 30, 60, 90]


def generate_stock_data(count: int, scenario_type: str = "normal") -> List[Dict[str, Any]]:
    """
    Generates synthetic stock data for performance testing.
    
    Args:
        count: Number of stock records to generate
        scenario_type: Type of market scenario to simulate
            ("normal", "high_volatility", "corporate_events", "hard_to_borrow", "market_disruption")
            
    Returns:
        List of stock dictionaries conforming to StockSchema
    """
    settings = get_test_settings()
    
    # Determine borrow status distribution based on scenario type
    if scenario_type == "normal":
        # Normal market has mostly easy-to-borrow securities
        borrow_status_weights = {
            BorrowStatus.EASY: 0.7,    # 70% easy to borrow
            BorrowStatus.MEDIUM: 0.2,  # 20% medium difficulty
            BorrowStatus.HARD: 0.1     # 10% hard to borrow
        }
    elif scenario_type == "high_volatility":
        # High volatility has more medium and hard-to-borrow securities
        borrow_status_weights = {
            BorrowStatus.EASY: 0.4,    # 40% easy to borrow
            BorrowStatus.MEDIUM: 0.4,  # 40% medium difficulty
            BorrowStatus.HARD: 0.2     # 20% hard to borrow
        }
    elif scenario_type == "corporate_events":
        # Corporate events scenario has standard distribution
        borrow_status_weights = {
            BorrowStatus.EASY: 0.6,    # 60% easy to borrow
            BorrowStatus.MEDIUM: 0.3,  # 30% medium difficulty
            BorrowStatus.HARD: 0.1     # 10% hard to borrow
        }
    elif scenario_type == "hard_to_borrow":
        # Hard-to-borrow scenario has mostly hard and medium securities
        borrow_status_weights = {
            BorrowStatus.EASY: 0.2,    # 20% easy to borrow
            BorrowStatus.MEDIUM: 0.3,  # 30% medium difficulty
            BorrowStatus.HARD: 0.5     # 50% hard to borrow
        }
    elif scenario_type == "market_disruption":
        # Market disruption has extreme difficulty borrowing
        borrow_status_weights = {
            BorrowStatus.EASY: 0.1,    # 10% easy to borrow
            BorrowStatus.MEDIUM: 0.3,  # 30% medium difficulty
            BorrowStatus.HARD: 0.6     # 60% hard to borrow
        }
    else:
        # Default to normal distribution
        borrow_status_weights = {
            BorrowStatus.EASY: 0.7,
            BorrowStatus.MEDIUM: 0.2,
            BorrowStatus.HARD: 0.1
        }
    
    stocks = []
    
    # Generate random tickers (using common ones as a base)
    base_tickers = COMMON_TICKERS.copy()
    
    # Generate additional tickers if needed
    if count > len(base_tickers):
        for i in range(len(base_tickers), count):
            # Generate a random 3-5 letter ticker
            ticker_length = random.randint(3, 5)
            random_ticker = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=ticker_length))
            base_tickers.append(random_ticker)
    
    # Shuffle the tickers to randomize selection
    tickers = random.sample(base_tickers, min(count, len(base_tickers)))
    
    # Generate random stocks
    for i in range(count):
        # Select a ticker (or generate a random one if we run out)
        if i < len(tickers):
            ticker = tickers[i]
        else:
            ticker_length = random.randint(3, 5)
            ticker = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=ticker_length))
        
        # Determine borrow status based on the weights
        status_choices = list(borrow_status_weights.keys())
        status_weights = list(borrow_status_weights.values())
        borrow_status = random.choices(status_choices, weights=status_weights, k=1)[0]
        
        # Set the minimum borrow rate based on borrow status
        if borrow_status == BorrowStatus.EASY:
            min_rate = Decimal(str(random.uniform(0.01, 0.05)))
        elif borrow_status == BorrowStatus.MEDIUM:
            min_rate = Decimal(str(random.uniform(0.05, 0.20)))
        else:  # BorrowStatus.HARD
            min_rate = Decimal(str(random.uniform(0.20, 1.0)))
        
        # Round to 4 decimal places
        min_rate = min_rate.quantize(Decimal('0.0001'))
        
        # Generate a stock record
        stock = {
            "ticker": ticker,
            "borrow_status": borrow_status,
            "lender_api_id": f"SEC{random.randint(1000, 9999)}",
            "min_borrow_rate": min_rate,
            "last_updated": datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 30))
        }
        
        stocks.append(stock)
    
    return stocks


def generate_broker_data(count: int) -> List[Dict[str, Any]]:
    """
    Generates synthetic broker data for performance testing.
    
    Args:
        count: Number of broker records to generate
        
    Returns:
        List of broker dictionaries conforming to BrokerSchema
    """
    settings = get_test_settings()
    
    brokers = []
    
    for i in range(count):
        # Generate a unique client ID
        client_id = f"broker_{i+1:03d}"
        
        # Generate a random markup percentage (1% to 20%)
        markup_percentage = Decimal(str(random.uniform(1.0, 20.0))).quantize(Decimal('0.01'))
        
        # Randomly select fee type, with a 60% chance of FLAT
        fee_type = random.choices(
            [TransactionFeeType.FLAT, TransactionFeeType.PERCENTAGE],
            weights=[0.6, 0.4],
            k=1
        )[0]
        
        # Set transaction amount based on fee type
        if fee_type == TransactionFeeType.FLAT:
            # Flat fee between $10 and $50
            transaction_amount = Decimal(str(random.uniform(10.0, 50.0))).quantize(Decimal('0.01'))
        else:
            # Percentage fee between 0.1% and 2%
            transaction_amount = Decimal(str(random.uniform(0.1, 2.0))).quantize(Decimal('0.01'))
        
        # Generate a broker record
        broker = {
            "client_id": client_id,
            "markup_percentage": markup_percentage,
            "transaction_fee_type": fee_type,
            "transaction_amount": transaction_amount,
            "active": random.random() > 0.1,  # 90% chance of being active
            "last_updated": datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 90))
        }
        
        brokers.append(broker)
    
    return brokers


def generate_calculation_data(count: int, stocks: List[Dict[str, Any]], brokers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generates test data for fee calculations.
    
    Args:
        count: Number of calculation parameter sets to generate
        stocks: List of stock dictionaries to select from
        brokers: List of broker dictionaries to select from
        
    Returns:
        List of calculation parameter dictionaries
    """
    if not stocks or not brokers:
        raise ValueError("Cannot generate calculation data without stocks and brokers")
    
    calculations = []
    
    for _ in range(count):
        # Randomly select a stock
        stock = random.choice(stocks)
        
        # Randomly select a position value
        position_value = random.choice(POSITION_VALUES)
        
        # Randomly select loan days
        loan_days = random.choice(LOAN_DAYS)
        
        # Randomly select a broker
        broker = random.choice(brokers)
        
        # Create calculation parameters
        calculation = {
            "ticker": stock["ticker"],
            "position_value": position_value,
            "loan_days": loan_days,
            "client_id": broker["client_id"]
        }
        
        calculations.append(calculation)
    
    return calculations


def generate_market_scenario_data(scenario_type: str, stock_count: int, broker_count: int, calculation_count: int) -> Dict[str, Any]:
    """
    Generates test data for a specific market scenario.
    
    Args:
        scenario_type: Type of market scenario to simulate
        stock_count: Number of stock records to generate
        broker_count: Number of broker records to generate
        calculation_count: Number of calculation parameter sets to generate
        
    Returns:
        Dictionary containing stocks, brokers, and calculation parameters
    """
    # Generate stock data
    stocks = generate_stock_data(stock_count, scenario_type)
    
    # Generate broker data
    brokers = generate_broker_data(broker_count)
    
    # Generate calculation data
    calculations = generate_calculation_data(calculation_count, stocks, brokers)
    
    return {
        "stocks": stocks,
        "brokers": brokers,
        "calculations": calculations
    }


@pytest.fixture
def test_stocks():
    """
    Pytest fixture providing a standard set of test stocks.
    
    Returns:
        List of stock dictionaries for normal market conditions
    """
    return generate_stock_data(100, "normal")


@pytest.fixture
def test_brokers():
    """
    Pytest fixture providing a standard set of test brokers.
    
    Returns:
        List of broker dictionaries
    """
    return generate_broker_data(10)


@pytest.fixture
def test_calculations(test_stocks, test_brokers):
    """
    Pytest fixture providing a standard set of calculation parameters.
    
    Returns:
        List of calculation parameter dictionaries
    """
    return generate_calculation_data(100, test_stocks, test_brokers)


@pytest.fixture
def normal_market_scenario():
    """
    Pytest fixture providing test data for normal market conditions.
    
    Returns:
        Dictionary containing stocks, brokers, and calculation parameters
    """
    settings = get_test_settings()
    data_size = settings.get_test_data_size()
    
    return generate_market_scenario_data(
        "normal",
        data_size["num_stocks"] // 5,  # Use a subset for faster tests
        data_size["num_brokers"] // 5,
        data_size["transactions_per_test"] // 10
    )


@pytest.fixture
def high_volatility_scenario():
    """
    Pytest fixture providing test data for high volatility market conditions.
    
    Returns:
        Dictionary containing stocks, brokers, and calculation parameters
    """
    settings = get_test_settings()
    data_size = settings.get_test_data_size()
    
    return generate_market_scenario_data(
        "high_volatility",
        data_size["num_stocks"] // 5,
        data_size["num_brokers"] // 5,
        data_size["transactions_per_test"] // 10
    )


@pytest.fixture
def corporate_events_scenario():
    """
    Pytest fixture providing test data for stocks with upcoming corporate events.
    
    Returns:
        Dictionary containing stocks, brokers, and calculation parameters
    """
    settings = get_test_settings()
    data_size = settings.get_test_data_size()
    
    return generate_market_scenario_data(
        "corporate_events",
        data_size["num_stocks"] // 5,
        data_size["num_brokers"] // 5,
        data_size["transactions_per_test"] // 10
    )


@pytest.fixture
def hard_to_borrow_scenario():
    """
    Pytest fixture providing test data for hard-to-borrow securities.
    
    Returns:
        Dictionary containing stocks, brokers, and calculation parameters
    """
    settings = get_test_settings()
    data_size = settings.get_test_data_size()
    
    return generate_market_scenario_data(
        "hard_to_borrow",
        data_size["num_stocks"] // 5,
        data_size["num_brokers"] // 5,
        data_size["transactions_per_test"] // 10
    )


@pytest.fixture
def market_disruption_scenario():
    """
    Pytest fixture providing test data for market disruption conditions.
    
    Returns:
        Dictionary containing stocks, brokers, and calculation parameters
    """
    settings = get_test_settings()
    data_size = settings.get_test_data_size()
    
    return generate_market_scenario_data(
        "market_disruption",
        data_size["num_stocks"] // 5,
        data_size["num_brokers"] // 5,
        data_size["transactions_per_test"] // 10
    )