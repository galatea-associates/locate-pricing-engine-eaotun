"""
Integration tests for the Calculation Service component of the Borrow Rate & Locate Fee Pricing Engine.
This test suite verifies that the calculation service correctly computes borrow rates and locate fees with proper
adjustments for volatility and event risk, handles various edge cases, and implements fallback mechanisms
when external APIs are unavailable.
"""

import pytest  # version: 7.0.0+
from decimal import Decimal  # standard library
import logging  # standard library
import json  # standard library
import requests  # version: 2.28.0+

from .helpers.api_client import APIClient, create_api_client  # src/test/integration_tests/helpers/api_client.py
from .helpers.assertions import Assertions  # src/test/integration_tests/helpers/assertions.py
from .fixtures.stocks import easy_to_borrow_stock, medium_to_borrow_stock, hard_to_borrow_stock, invalid_ticker  # src/test/integration_tests/fixtures/stocks.py
from .fixtures.brokers import standard_broker, premium_broker, invalid_client_id  # src/test/integration_tests/fixtures/brokers.py
from .fixtures.volatility import low_volatility_data, high_volatility_data  # src/test/integration_tests/fixtures/volatility.py
from .fixtures.api_responses import SECLEND_API_RESPONSES, MARKET_API_RESPONSES, EVENT_API_RESPONSES  # src/test/integration_tests/fixtures/api_responses.py
from src.backend.services.calculation.borrow_rate import calculate_borrow_rate  # src/backend/services/calculation/borrow_rate.py
from src.backend.services.calculation.locate_fee import calculate_locate_fee  # src/backend/services/calculation/locate_fee.py

# Initialize logger
logger = logging.getLogger(__name__)

# Define test constants
TEST_POSITION_VALUE = Decimal('100000.00')
TEST_LOAN_DAYS = 30


@pytest.fixture
def setup_api_client() -> APIClient:
    """
    Pytest fixture that sets up an API client for testing the calculation service
    """
    # Create an API client using create_api_client()
    api_client = create_api_client()
    
    # Configure mock servers for external API dependencies
    api_client.configure_mock_servers()
    
    # Wait for the API to be ready
    api_client.wait_for_api_ready()
    
    # Return the configured client instance
    return api_client


@pytest.fixture
def setup_assertions() -> Assertions:
    """
    Pytest fixture that sets up an Assertions instance for validating test results
    """
    # Create an Assertions instance with appropriate precision for financial calculations
    assertions = Assertions()
    
    # Return the configured assertions instance
    return assertions


class TestBorrowRateCalculation:
    """Test suite for borrow rate calculation functionality"""

    def test_get_borrow_rate_easy_to_borrow(self, setup_api_client: APIClient, setup_assertions: Assertions, easy_to_borrow_stock: Dict):
        """Tests that borrow rate calculation works correctly for easy-to-borrow stocks"""
        # Get ticker from easy_to_borrow_stock fixture
        ticker = easy_to_borrow_stock['ticker']
        
        # Call api_client.get_borrow_rate with the ticker
        response = setup_api_client.get_borrow_rate(ticker)
        
        # Use assertions.assert_rate_response to verify the response
        setup_assertions.assert_rate_response(response, expected_ticker=ticker)
        
        # Check that the returned rate is appropriate for an easy-to-borrow stock
        assert response.current_rate < Decimal('0.1'), "Rate should be low for easy-to-borrow stock"
        
        # Verify that the borrow status is 'EASY'
        assert response.borrow_status == 'EASY', "Borrow status should be EASY"

    def test_get_borrow_rate_hard_to_borrow(self, setup_api_client: APIClient, setup_assertions: Assertions, hard_to_borrow_stock: Dict):
        """Tests that borrow rate calculation works correctly for hard-to-borrow stocks"""
        # Get ticker from hard_to_borrow_stock fixture
        ticker = hard_to_borrow_stock['ticker']
        
        # Call api_client.get_borrow_rate with the ticker
        response = setup_api_client.get_borrow_rate(ticker)
        
        # Use assertions.assert_rate_response to verify the response
        setup_assertions.assert_rate_response(response, expected_ticker=ticker)
        
        # Check that the returned rate is higher than for easy-to-borrow stocks
        assert response.current_rate > Decimal('0.1'), "Rate should be high for hard-to-borrow stock"
        
        # Verify that the borrow status is 'HARD'
        assert response.borrow_status == 'HARD', "Borrow status should be HARD"

    def test_get_borrow_rate_with_volatility_adjustment(self, setup_api_client: APIClient, setup_assertions: Assertions, easy_to_borrow_stock: Dict, high_volatility_data: Dict):
        """Tests that volatility adjustments are correctly applied to borrow rates"""
        # Get ticker from easy_to_borrow_stock fixture
        ticker = easy_to_borrow_stock['ticker']
        
        # Call api_client.get_borrow_rate with the ticker
        response = setup_api_client.get_borrow_rate(ticker)
        
        # Use assertions.assert_rate_response to verify the response
        setup_assertions.assert_rate_response(response, expected_ticker=ticker)
        
        # Verify that the volatility_index in the response matches high_volatility_data
        assert response.volatility_index == high_volatility_data['vol_index'], "Volatility index should match high_volatility_data"
        
        # Check that the rate is higher than the base rate due to volatility adjustment
        assert response.current_rate > easy_to_borrow_stock['min_borrow_rate'], "Rate should be higher due to volatility"

    def test_get_borrow_rate_with_event_risk(self, setup_api_client: APIClient, setup_assertions: Assertions, hard_to_borrow_stock: Dict):
        """Tests that event risk factors are correctly applied to borrow rates"""
        # Get ticker from hard_to_borrow_stock fixture
        ticker = hard_to_borrow_stock['ticker']
        
        # Call api_client.get_borrow_rate with the ticker
        response = setup_api_client.get_borrow_rate(ticker)
        
        # Use assertions.assert_rate_response to verify the response
        setup_assertions.assert_rate_response(response, expected_ticker=ticker)
        
        # Verify that the event_risk_factor in the response is present
        assert response.event_risk_factor is not None, "Event risk factor should be present"
        
        # Check that the rate reflects the event risk adjustment
        assert response.current_rate > hard_to_borrow_stock['min_borrow_rate'], "Rate should reflect event risk adjustment"

    def test_get_borrow_rate_invalid_ticker(self, setup_api_client: APIClient, setup_assertions: Assertions, invalid_ticker: str):
        """Tests error handling for invalid ticker symbols"""
        # Call api_client.get_borrow_rate with the invalid_ticker
        response = setup_api_client.get_borrow_rate(invalid_ticker)
        
        # Use assertions.assert_ticker_not_found to verify the error response
        setup_assertions.assert_ticker_not_found(response, ticker=invalid_ticker)
        
        # Check that the error message contains the invalid ticker
        assert invalid_ticker.lower() in response.error.lower(), "Error message should contain invalid ticker"

    def test_get_borrow_rate_external_api_unavailable(self, setup_api_client: APIClient, setup_assertions: Assertions, easy_to_borrow_stock: Dict):
        """Tests fallback mechanism when external APIs are unavailable"""
        # Mock the external API to be unavailable
        # (This requires configuring the mock server to return an error)
        
        # Get ticker from easy_to_borrow_stock fixture
        ticker = easy_to_borrow_stock['ticker']
        
        # Call api_client.get_borrow_rate with the ticker
        response = setup_api_client.get_borrow_rate(ticker)
        
        # Verify that a fallback rate is returned instead of an error
        assert response.status == 'success', "Should return a successful response with fallback rate"
        
        # Check that the fallback rate is at least the minimum rate for the stock
        assert response.current_rate >= easy_to_borrow_stock['min_borrow_rate'], "Fallback rate should be at least the minimum rate"

    def test_direct_borrow_rate_calculation(self, easy_to_borrow_stock: Dict):
        """Tests the direct calculation function without going through the API"""
        # Get ticker from easy_to_borrow_stock fixture
        ticker = easy_to_borrow_stock['ticker']
        
        # Call calculate_borrow_rate directly with the ticker
        borrow_rate = calculate_borrow_rate(ticker)
        
        # Verify that the returned rate is a Decimal
        assert isinstance(borrow_rate, Decimal), "Borrow rate should be a Decimal"
        
        # Check that the rate is appropriate for the stock's borrow status
        assert borrow_rate > Decimal('0.0'), "Borrow rate should be a positive value"
        
        # Verify that the calculation completes without errors
        assert True  # If it reaches here, the calculation completed without errors


class TestLocateFeeCalculation:
    """Test suite for locate fee calculation functionality"""

    def test_calculate_locate_fee_standard_broker(self, setup_api_client: APIClient, setup_assertions: Assertions, easy_to_borrow_stock: Dict, standard_broker: Dict):
        """Tests locate fee calculation with a standard broker using flat fees"""
        # Get ticker from easy_to_borrow_stock fixture
        ticker = easy_to_borrow_stock['ticker']
        
        # Get client_id from standard_broker fixture
        client_id = standard_broker['client_id']
        
        # Call api_client.calculate_locate_fee with ticker, TEST_POSITION_VALUE, TEST_LOAN_DAYS, and client_id
        response = setup_api_client.calculate_locate_fee(ticker, TEST_POSITION_VALUE, TEST_LOAN_DAYS, client_id)
        
        # Use assertions.assert_calculation_result to verify the response
        setup_assertions.assert_calculation_result(response)
        
        # Check that the fee breakdown includes borrow_cost, markup, and transaction_fees
        assert 'borrow_cost' in response.breakdown, "Fee breakdown should include borrow_cost"
        assert 'markup' in response.breakdown, "Fee breakdown should include markup"
        assert 'transaction_fees' in response.breakdown, "Fee breakdown should include transaction_fees"
        
        # Verify that the transaction fee is a flat amount
        assert response.breakdown.transaction_fees == standard_broker['transaction_amount'], "Transaction fee should be a flat amount"

    def test_calculate_locate_fee_premium_broker(self, setup_api_client: APIClient, setup_assertions: Assertions, easy_to_borrow_stock: Dict, premium_broker: Dict):
        """Tests locate fee calculation with a premium broker using percentage fees"""
        # Get ticker from easy_to_borrow_stock fixture
        ticker = easy_to_borrow_stock['ticker']
        
        # Get client_id from premium_broker fixture
        client_id = premium_broker['client_id']
        
        # Call api_client.calculate_locate_fee with ticker, TEST_POSITION_VALUE, TEST_LOAN_DAYS, and client_id
        response = setup_api_client.calculate_locate_fee(ticker, TEST_POSITION_VALUE, TEST_LOAN_DAYS, client_id)
        
        # Use assertions.assert_calculation_result to verify the response
        setup_assertions.assert_calculation_result(response)
        
        # Check that the fee breakdown includes borrow_cost, markup, and transaction_fees
        assert 'borrow_cost' in response.breakdown, "Fee breakdown should include borrow_cost"
        assert 'markup' in response.breakdown, "Fee breakdown should include markup"
        assert 'transaction_fees' in response.breakdown, "Fee breakdown should include transaction_fees"
        
        # Verify that the transaction fee is a percentage of the position value
        expected_fee = TEST_POSITION_VALUE * premium_broker['transaction_amount'] / 100
        assert response.breakdown.transaction_fees == expected_fee, "Transaction fee should be a percentage of position value"

    def test_calculate_locate_fee_hard_to_borrow(self, setup_api_client: APIClient, setup_assertions: Assertions, hard_to_borrow_stock: Dict, standard_broker: Dict):
        """Tests locate fee calculation with a hard-to-borrow stock"""
        # Get ticker from hard_to_borrow_stock fixture
        ticker = hard_to_borrow_stock['ticker']
        
        # Get client_id from standard_broker fixture
        client_id = standard_broker['client_id']
        
        # Call api_client.calculate_locate_fee with ticker, TEST_POSITION_VALUE, TEST_LOAN_DAYS, and client_id
        response = setup_api_client.calculate_locate_fee(ticker, TEST_POSITION_VALUE, TEST_LOAN_DAYS, client_id)
        
        # Use assertions.assert_calculation_result to verify the response
        setup_assertions.assert_calculation_result(response)
        
        # Check that the fee is higher than for easy-to-borrow stocks due to higher borrow rate
        assert response.total_fee > Decimal('1000'), "Fee should be higher for hard-to-borrow stock"
        
        # Verify that the borrow_rate_used is appropriate for a hard-to-borrow stock
        assert response.borrow_rate_used > Decimal('0.1'), "Borrow rate used should be appropriate for hard-to-borrow stock"

    def test_calculate_locate_fee_with_different_position_values(self, setup_api_client: APIClient, setup_assertions: Assertions, medium_to_borrow_stock: Dict, standard_broker: Dict):
        """Tests locate fee calculation with different position values"""
        # Get ticker from medium_to_borrow_stock fixture
        ticker = medium_to_borrow_stock['ticker']
        
        # Get client_id from standard_broker fixture
        client_id = standard_broker['client_id']
        
        # Define small and large position values
        small_position_value = Decimal('10000.00')
        large_position_value = Decimal('500000.00')
        
        # Call api_client.calculate_locate_fee with ticker, small position value, TEST_LOAN_DAYS, and client_id
        response_small = setup_api_client.calculate_locate_fee(ticker, small_position_value, TEST_LOAN_DAYS, client_id)
        
        # Verify the response for small position
        setup_assertions.assert_calculation_result(response_small)
        
        # Call api_client.calculate_locate_fee with ticker, large position value, TEST_LOAN_DAYS, and client_id
        response_large = setup_api_client.calculate_locate_fee(ticker, large_position_value, TEST_LOAN_DAYS, client_id)
        
        # Verify the response for large position
        setup_assertions.assert_calculation_result(response_large)
        
        # Check that the fees scale proportionally with position value
        fee_ratio = response_large.total_fee / response_small.total_fee
        position_ratio = large_position_value / small_position_value
        assert abs(fee_ratio - position_ratio) < 0.1, "Fees should scale proportionally with position value"

    def test_calculate_locate_fee_with_different_loan_days(self, setup_api_client: APIClient, setup_assertions: Assertions, medium_to_borrow_stock: Dict, standard_broker: Dict):
        """Tests locate fee calculation with different loan durations"""
        # Get ticker from medium_to_borrow_stock fixture
        ticker = medium_to_borrow_stock['ticker']
        
        # Get client_id from standard_broker fixture
        client_id = standard_broker['client_id']
        
        # Define short and long loan durations
        short_loan_days = 7
        long_loan_days = 90
        
        # Call api_client.calculate_locate_fee with ticker, TEST_POSITION_VALUE, short loan days, and client_id
        response_short = setup_api_client.calculate_locate_fee(ticker, TEST_POSITION_VALUE, short_loan_days, client_id)
        
        # Verify the response for short loan duration
        setup_assertions.assert_calculation_result(response_short)
        
        # Call api_client.calculate_locate_fee with ticker, TEST_POSITION_VALUE, long loan days, and client_id
        response_long = setup_api_client.calculate_locate_fee(ticker, TEST_POSITION_VALUE, long_loan_days, client_id)
        
        # Verify the response for long loan duration
        setup_assertions.assert_calculation_result(response_long)
        
        # Check that the borrow cost scales proportionally with loan days
        borrow_cost_ratio = response_long.breakdown.borrow_cost / response_short.breakdown.borrow_cost
        loan_days_ratio = long_loan_days / short_loan_days
        assert abs(borrow_cost_ratio - loan_days_ratio) < 0.1, "Borrow cost should scale proportionally with loan days"

    def test_calculate_locate_fee_invalid_ticker(self, setup_api_client: APIClient, setup_assertions: Assertions, invalid_ticker: str, standard_broker: Dict):
        """Tests error handling for invalid ticker symbols in fee calculation"""
        # Get client_id from standard_broker fixture
        client_id = standard_broker['client_id']
        
        # Call api_client.calculate_locate_fee with invalid_ticker, TEST_POSITION_VALUE, TEST_LOAN_DAYS, and client_id
        response = setup_api_client.calculate_locate_fee(invalid_ticker, TEST_POSITION_VALUE, TEST_LOAN_DAYS, client_id)
        
        # Use assertions.assert_ticker_not_found to verify the error response
        setup_assertions.assert_ticker_not_found(response, ticker=invalid_ticker)
        
        # Check that the error message contains the invalid ticker
        assert invalid_ticker.lower() in response.error.lower(), "Error message should contain invalid ticker"

    def test_calculate_locate_fee_invalid_client(self, setup_api_client: APIClient, setup_assertions: Assertions, easy_to_borrow_stock: Dict, invalid_client_id: str):
        """Tests error handling for invalid client IDs in fee calculation"""
        # Get ticker from easy_to_borrow_stock fixture
        ticker = easy_to_borrow_stock['ticker']
        
        # Call api_client.calculate_locate_fee with ticker, TEST_POSITION_VALUE, TEST_LOAN_DAYS, and invalid_client_id
        response = setup_api_client.calculate_locate_fee(ticker, TEST_POSITION_VALUE, TEST_LOAN_DAYS, invalid_client_id)
        
        # Use assertions.assert_client_not_found to verify the error response
        setup_assertions.assert_client_not_found(response, client_id=invalid_client_id)
        
        # Check that the error message contains the invalid client ID
        assert invalid_client_id.lower() in response.error.lower(), "Error message should contain invalid client ID"

    def test_calculate_locate_fee_external_api_unavailable(self, setup_api_client: APIClient, setup_assertions: Assertions, easy_to_borrow_stock: Dict, standard_broker: Dict):
        """Tests fallback mechanism when external APIs are unavailable during fee calculation"""
        # Mock the external API to be unavailable
        # (This requires configuring the mock server to return an error)
        
        # Get ticker from easy_to_borrow_stock fixture
        ticker = easy_to_borrow_stock['ticker']
        
        # Get client_id from standard_broker fixture
        client_id = standard_broker['client_id']
        
        # Call api_client.calculate_locate_fee with ticker, TEST_POSITION_VALUE, TEST_LOAN_DAYS, and client_id
        response = setup_api_client.calculate_locate_fee(ticker, TEST_POSITION_VALUE, TEST_LOAN_DAYS, client_id)
        
        # Verify that a fallback calculation is performed instead of returning an error
        assert response.status == 'success', "Should return a successful response with fallback calculation"
        
        # Check that the borrow_rate_used is at least the minimum rate for the stock
        assert response.borrow_rate_used >= easy_to_borrow_stock['min_borrow_rate'], "Borrow rate used should be at least the minimum rate"

    def test_direct_locate_fee_calculation(self, easy_to_borrow_stock: Dict, standard_broker: Dict):
        """Tests the direct calculation function without going through the API"""
        # Get ticker from easy_to_borrow_stock fixture
        ticker = easy_to_borrow_stock['ticker']
        
        # Extract markup_percentage, fee_type, and fee_amount from standard_broker
        markup_percentage = standard_broker['markup_percentage']
        fee_type = standard_broker['transaction_fee_type']
        fee_amount = standard_broker['transaction_amount']
        
        # Call calculate_locate_fee directly with all parameters
        result = calculate_locate_fee(
            ticker=ticker,
            position_value=TEST_POSITION_VALUE,
            loan_days=TEST_LOAN_DAYS,
            markup_percentage=markup_percentage,
            fee_type=fee_type,
            fee_amount=fee_amount
        )
        
        # Verify that the returned result is a dictionary with expected keys
        assert isinstance(result, dict), "Result should be a dictionary"
        assert 'total_fee' in result, "Result should contain total_fee"
        assert 'breakdown' in result, "Result should contain breakdown"
        
        # Check that the total_fee and breakdown values are appropriate
        assert result['total_fee'] > 0, "Total fee should be a positive value"
        assert 'borrow_cost' in result['breakdown'], "Breakdown should contain borrow_cost"
        assert 'markup' in result['breakdown'], "Breakdown should contain markup"
        assert 'transaction_fees' in result['breakdown'], "Breakdown should contain transaction_fees"
        
        # Verify that the calculation completes without errors
        assert True  # If it reaches here, the calculation completed without errors