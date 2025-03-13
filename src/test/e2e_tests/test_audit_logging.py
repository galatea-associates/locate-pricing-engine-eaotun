"""
End-to-end test module that verifies the audit logging functionality of the Borrow Rate & Locate Fee Pricing Engine.
Tests ensure that all fee calculations are properly logged with detailed information for regulatory compliance,
troubleshooting, and audit trail requirements.
"""

import logging
import pytest
import requests
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from .config.settings import get_test_settings, TestEnvironment
from .helpers.api_client import APIClient, create_api_client
from .helpers.validation import ResponseValidator, create_response_validator
from .helpers.test_data import get_test_scenario, TEST_CALCULATION_SCENARIOS
from .fixtures.environment import environment
from .fixtures.test_data import test_data_manager

from src.backend.schemas.audit import AuditLogSchema, AuditLogFilterSchema
from src.backend.schemas.response import CalculateLocateResponse

# Configure logger
logger = logging.getLogger(__name__)

# Endpoint for audit API
AUDIT_API_ENDPOINT = "/api/v1/audit"


def setup_module():
    """Setup function that runs once before all tests in the module."""
    logger.info("Setting up audit logging test module")
    
    # Get test settings
    settings = get_test_settings()
    
    # Create API client and wait for API to be ready
    api_client = create_api_client()
    api_client.wait_for_api_ready()
    
    logger.info("Audit logging test module setup complete")


def teardown_module():
    """Teardown function that runs once after all tests in the module."""
    logger.info("Tearing down audit logging test module")
    
    # Any necessary cleanup
    
    logger.info("Audit logging test module teardown complete")


def get_audit_logs(api_client: APIClient, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Helper function to retrieve audit logs from the API.
    
    Args:
        api_client: API client instance
        filters: Optional filter parameters
        
    Returns:
        Audit logs response
    """
    url = AUDIT_API_ENDPOINT
    
    # Add filters as query parameters
    params = filters if filters else {}
    
    # Make the request
    response = api_client.get(url, params=params)
    
    # Verify response status code is 200
    assert response.status_code == 200, f"Failed to retrieve audit logs: {response.text}"
    
    # Return the parsed JSON response
    return response.json()


def get_audit_log_by_id(api_client: APIClient, audit_id: str) -> Optional[Dict[str, Any]]:
    """
    Helper function to retrieve a specific audit log by ID.
    
    Args:
        api_client: API client instance
        audit_id: ID of the audit log to retrieve
        
    Returns:
        Audit log or None if not found
    """
    url = f"{AUDIT_API_ENDPOINT}/{audit_id}"
    
    # Make the request
    response = api_client.get(url)
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        return None
    else:
        raise Exception(f"Failed to retrieve audit log {audit_id}: {response.text}")


def get_client_audit_logs(api_client: APIClient, client_id: str) -> List[Dict[str, Any]]:
    """
    Helper function to retrieve audit logs for a specific client.
    
    Args:
        api_client: API client instance
        client_id: Client ID to filter by
        
    Returns:
        List of audit logs for the client
    """
    response = get_audit_logs(api_client, {"client_id": client_id})
    return response.get("items", [])


def get_ticker_audit_logs(api_client: APIClient, ticker: str) -> List[Dict[str, Any]]:
    """
    Helper function to retrieve audit logs for a specific ticker.
    
    Args:
        api_client: API client instance
        ticker: Ticker symbol to filter by
        
    Returns:
        List of audit logs for the ticker
    """
    response = get_audit_logs(api_client, {"ticker": ticker})
    return response.get("items", [])


@pytest.mark.e2e
def test_audit_logging_basic(environment):
    """Tests that basic fee calculations are properly logged in the audit system."""
    logger.info("Starting basic audit logging test")
    
    # Create API client
    api_client = create_api_client()
    response_validator = create_response_validator()
    
    # Get test scenario for normal market conditions
    scenario = get_test_scenario("normal_market")
    ticker = scenario["ticker"]
    position_value = scenario["position_value"]
    loan_days = scenario["loan_days"]
    client_id = scenario["client_id"]
    
    # Make a fee calculation request
    calculation_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    # Verify calculation response is successful
    assert calculation_response.status == "success"
    
    # Wait briefly for audit log to be written (small delay)
    time.sleep(1)
    
    # Retrieve audit logs for the client
    audit_logs = get_client_audit_logs(api_client, client_id)
    
    # Verify that at least one audit log exists for the calculation
    assert len(audit_logs) > 0, "No audit logs found for client"
    
    # Find the matching audit log entry by comparing parameters
    matching_logs = [log for log in audit_logs 
                    if log.get("ticker") == ticker 
                    and Decimal(str(log.get("position_value"))) == position_value
                    and log.get("loan_days") == loan_days]
    
    assert len(matching_logs) > 0, "No matching audit logs found"
    audit_log = matching_logs[0]
    
    # Verify that the audit log contains all required fields
    assert "audit_id" in audit_log
    assert "timestamp" in audit_log
    assert "client_id" in audit_log
    assert "ticker" in audit_log
    assert "position_value" in audit_log
    assert "loan_days" in audit_log
    assert "borrow_rate_used" in audit_log
    assert "total_fee" in audit_log
    
    # Verify that the audit log values match the calculation request and response
    assert audit_log["client_id"] == client_id
    assert audit_log["ticker"] == ticker
    assert Decimal(str(audit_log["position_value"])) == position_value
    assert audit_log["loan_days"] == loan_days
    assert Decimal(str(audit_log["borrow_rate_used"])) == calculation_response.borrow_rate_used
    assert Decimal(str(audit_log["total_fee"])) == calculation_response.total_fee
    
    logger.info("Basic audit logging test successful")


@pytest.mark.e2e
def test_audit_log_contains_data_sources(environment):
    """Tests that audit logs contain information about data sources used in calculations."""
    logger.info("Starting data sources audit test")
    
    # Create API client
    api_client = create_api_client()
    
    # Get test scenario for high volatility conditions
    scenario = get_test_scenario("high_volatility")
    ticker = scenario["ticker"]
    position_value = scenario["position_value"]
    loan_days = scenario["loan_days"]
    client_id = scenario["client_id"]
    
    # Make a fee calculation request
    calculation_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    # Verify calculation response is successful
    assert calculation_response.status == "success"
    
    # Wait briefly for audit log to be written
    time.sleep(1)
    
    # Retrieve audit logs for the ticker
    audit_logs = get_ticker_audit_logs(api_client, ticker)
    
    # Find the matching audit log entry
    matching_logs = [log for log in audit_logs 
                    if log.get("client_id") == client_id 
                    and Decimal(str(log.get("position_value"))) == position_value
                    and log.get("loan_days") == loan_days]
    
    assert len(matching_logs) > 0, "No matching audit logs found"
    audit_log = matching_logs[0]
    
    # Verify that the audit log contains data_sources field
    assert "data_sources" in audit_log
    
    # Verify that data_sources includes entries for borrow_rate, volatility, and event_risk
    data_sources = audit_log["data_sources"]
    assert "borrow_rate" in data_sources
    assert "volatility" in data_sources
    assert "event_risk" in data_sources
    
    # Verify that the source values are non-empty strings
    assert data_sources["borrow_rate"]
    assert data_sources["volatility"]
    assert data_sources["event_risk"]
    
    logger.info("Data sources audit test successful")


@pytest.mark.e2e
def test_audit_log_contains_calculation_breakdown(environment):
    """Tests that audit logs contain detailed breakdown of calculation steps."""
    logger.info("Starting calculation breakdown audit test")
    
    # Create API client
    api_client = create_api_client()
    
    # Get test scenario for corporate event conditions
    scenario = get_test_scenario("corporate_event")
    ticker = scenario["ticker"]
    position_value = scenario["position_value"]
    loan_days = scenario["loan_days"]
    client_id = scenario["client_id"]
    
    # Make a fee calculation request
    calculation_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    # Verify calculation response is successful
    assert calculation_response.status == "success"
    
    # Wait briefly for audit log to be written
    time.sleep(1)
    
    # Retrieve audit logs for the ticker
    audit_logs = get_ticker_audit_logs(api_client, ticker)
    
    # Find the matching audit log entry
    matching_logs = [log for log in audit_logs 
                    if log.get("client_id") == client_id 
                    and Decimal(str(log.get("position_value"))) == position_value
                    and log.get("loan_days") == loan_days]
    
    assert len(matching_logs) > 0, "No matching audit logs found"
    audit_log = matching_logs[0]
    
    # Verify that the audit log contains calculation_breakdown field
    assert "calculation_breakdown" in audit_log
    
    # Verify that calculation_breakdown includes fee_components, base_borrow_rate, etc.
    breakdown = audit_log["calculation_breakdown"]
    assert "fee_components" in breakdown
    assert "base_borrow_rate" in breakdown
    assert "final_borrow_rate" in breakdown
    assert "annualized_rate" in breakdown
    assert "time_factor" in breakdown
    
    # Verify that fee_components contains borrow_cost, markup, and transaction_fees
    fee_components = breakdown["fee_components"]
    assert "borrow_cost" in fee_components
    assert "markup" in fee_components
    assert "transaction_fees" in fee_components
    
    # Verify that the breakdown values are consistent with the total fee
    borrow_cost = Decimal(str(fee_components["borrow_cost"]))
    markup = Decimal(str(fee_components["markup"]))
    transaction_fees = Decimal(str(fee_components["transaction_fees"]))
    
    # Calculate sum of components and compare to total fee (within small tolerance)
    total_from_components = borrow_cost + markup + transaction_fees
    total_fee = Decimal(str(audit_log["total_fee"]))
    assert abs(total_fee - total_from_components) < Decimal('0.01'), \
        f"Total fee {total_fee} does not match sum of components {total_from_components}"
    
    logger.info("Calculation breakdown audit test successful")


@pytest.mark.e2e
def test_audit_log_retrieval_by_client(environment):
    """Tests retrieving audit logs filtered by client ID."""
    logger.info("Starting client audit retrieval test")
    
    # Create API client
    api_client = create_api_client()
    
    # Get test scenarios for different clients
    scenario1 = get_test_scenario("normal_market")
    scenario2 = get_test_scenario("high_volatility")
    
    client1 = scenario1["client_id"]
    client2 = scenario2["client_id"]
    
    # Make multiple fee calculations for different clients
    api_client.calculate_locate_fee(
        ticker=scenario1["ticker"],
        position_value=scenario1["position_value"],
        loan_days=scenario1["loan_days"],
        client_id=client1
    )
    
    api_client.calculate_locate_fee(
        ticker=scenario2["ticker"],
        position_value=scenario2["position_value"],
        loan_days=scenario2["loan_days"],
        client_id=client2
    )
    
    # Wait briefly for audit logs to be written
    time.sleep(1)
    
    # Retrieve audit logs for client1
    client1_logs = get_client_audit_logs(api_client, client1)
    
    # Verify that all returned logs have client_id matching client1
    for log in client1_logs:
        assert log["client_id"] == client1
    
    # Retrieve audit logs for client2
    client2_logs = get_client_audit_logs(api_client, client2)
    
    # Verify that all returned logs have client_id matching client2
    for log in client2_logs:
        assert log["client_id"] == client2
    
    logger.info("Client audit retrieval test successful")


@pytest.mark.e2e
def test_audit_log_retrieval_by_ticker(environment):
    """Tests retrieving audit logs filtered by ticker symbol."""
    logger.info("Starting ticker audit retrieval test")
    
    # Create API client
    api_client = create_api_client()
    
    # Get test scenarios for different tickers
    scenario1 = get_test_scenario("normal_market")
    scenario2 = get_test_scenario("high_volatility")
    
    ticker1 = scenario1["ticker"]
    ticker2 = scenario2["ticker"]
    
    # Make multiple fee calculations for different tickers
    api_client.calculate_locate_fee(
        ticker=ticker1,
        position_value=scenario1["position_value"],
        loan_days=scenario1["loan_days"],
        client_id=scenario1["client_id"]
    )
    
    api_client.calculate_locate_fee(
        ticker=ticker2,
        position_value=scenario2["position_value"],
        loan_days=scenario2["loan_days"],
        client_id=scenario2["client_id"]
    )
    
    # Wait briefly for audit logs to be written
    time.sleep(1)
    
    # Retrieve audit logs for ticker1
    ticker1_logs = get_ticker_audit_logs(api_client, ticker1)
    
    # Verify that all returned logs have ticker matching ticker1
    for log in ticker1_logs:
        assert log["ticker"] == ticker1
    
    # Retrieve audit logs for ticker2
    ticker2_logs = get_ticker_audit_logs(api_client, ticker2)
    
    # Verify that all returned logs have ticker matching ticker2
    for log in ticker2_logs:
        assert log["ticker"] == ticker2
    
    logger.info("Ticker audit retrieval test successful")


@pytest.mark.e2e
def test_audit_log_retrieval_by_date_range(environment):
    """Tests retrieving audit logs filtered by date range."""
    logger.info("Starting date range audit retrieval test")
    
    # Create API client
    api_client = create_api_client()
    
    # Record current time as start_time
    start_time = datetime.utcnow()
    
    # Make a fee calculation request
    scenario = get_test_scenario("normal_market")
    api_client.calculate_locate_fee(
        ticker=scenario["ticker"],
        position_value=scenario["position_value"],
        loan_days=scenario["loan_days"],
        client_id=scenario["client_id"]
    )
    
    # Wait briefly
    time.sleep(1)
    
    # Make another fee calculation request
    api_client.calculate_locate_fee(
        ticker=scenario["ticker"],
        position_value=scenario["position_value"] + Decimal('10000'),  # slightly different
        loan_days=scenario["loan_days"],
        client_id=scenario["client_id"]
    )
    
    # Record current time as end_time
    end_time = datetime.utcnow()
    
    # Wait briefly
    time.sleep(1)
    
    # Make a third fee calculation request
    api_client.calculate_locate_fee(
        ticker=scenario["ticker"],
        position_value=scenario["position_value"] + Decimal('20000'),  # different again
        loan_days=scenario["loan_days"],
        client_id=scenario["client_id"]
    )
    
    # Retrieve audit logs with start_date=start_time and end_date=end_time
    response = get_audit_logs(api_client, {
        "start_date": start_time.isoformat() + "Z",
        "end_date": end_time.isoformat() + "Z"
    })
    
    logs = response.get("items", [])
    
    # Verify that returned logs have timestamps between start_time and end_time
    for log in logs:
        log_time = datetime.fromisoformat(log["timestamp"].replace("Z", "+00:00"))
        assert log_time >= start_time, f"Log time {log_time} is before start time {start_time}"
        assert log_time <= end_time, f"Log time {log_time} is after end time {end_time}"
    
    # Verify that the third calculation (after end_time) is not included
    recent_calculation_logs = [
        log for log in logs 
        if Decimal(str(log.get("position_value"))) == scenario["position_value"] + Decimal('20000')
    ]
    assert len(recent_calculation_logs) == 0, "Found log entry that should be after the end_time"
    
    logger.info("Date range audit retrieval test successful")


@pytest.mark.e2e
def test_audit_log_contains_request_context(environment):
    """Tests that audit logs contain request context information."""
    logger.info("Starting request context audit test")
    
    # Create API client
    api_client = create_api_client()
    
    # Get test scenario
    scenario = get_test_scenario("normal_market")
    ticker = scenario["ticker"]
    position_value = scenario["position_value"]
    loan_days = scenario["loan_days"]
    client_id = scenario["client_id"]
    
    # Make a fee calculation request with custom headers (User-Agent, X-Request-ID)
    headers = {
        "User-Agent": "E2E-Test-Client/1.0",
        "X-Request-ID": "test-request-123"
    }
    
    calculation_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id,
        headers=headers
    )
    
    # Wait briefly for audit log to be written
    time.sleep(1)
    
    # Retrieve audit logs for the ticker
    audit_logs = get_ticker_audit_logs(api_client, ticker)
    
    # Find the matching audit log entry
    matching_logs = [log for log in audit_logs 
                    if log.get("client_id") == client_id 
                    and Decimal(str(log.get("position_value"))) == position_value
                    and log.get("loan_days") == loan_days]
    
    assert len(matching_logs) > 0, "No matching audit logs found"
    audit_log = matching_logs[0]
    
    # Verify that the audit log contains request_id matching the X-Request-ID header
    assert audit_log.get("request_id") == "test-request-123"
    
    # Verify that the audit log contains user_agent matching the User-Agent header
    assert audit_log.get("user_agent") == "E2E-Test-Client/1.0"
    
    # Verify that the audit log contains ip_address field
    assert "ip_address" in audit_log
    
    logger.info("Request context audit test successful")


@pytest.mark.e2e
def test_audit_log_pagination(environment):
    """Tests pagination of audit log retrieval."""
    logger.info("Starting pagination audit test")
    
    # Create API client
    api_client = create_api_client()
    
    # Make multiple fee calculations (at least 10)
    scenario = get_test_scenario("normal_market")
    ticker = scenario["ticker"]
    loan_days = scenario["loan_days"]
    client_id = scenario["client_id"]
    
    for i in range(10):
        api_client.calculate_locate_fee(
            ticker=ticker,
            position_value=scenario["position_value"] + (Decimal(i) * Decimal('10000')),
            loan_days=loan_days,
            client_id=client_id
        )
    
    # Wait briefly for audit logs to be written
    time.sleep(1)
    
    # Retrieve first page of audit logs with page_size=5
    response1 = get_audit_logs(api_client, {
        "page": 1,
        "page_size": 5
    })
    
    # Verify that response contains pagination metadata (total, page, pages)
    assert "total" in response1
    assert "page" in response1
    assert "pages" in response1
    assert "items" in response1
    
    # Verify that response contains exactly 5 items
    assert response1["page"] == 1
    assert len(response1["items"]) == 5
    
    # Retrieve second page of audit logs
    response2 = get_audit_logs(api_client, {
        "page": 2,
        "page_size": 5
    })
    
    # Verify that second page contains different items than first page
    page1_ids = [item["audit_id"] for item in response1["items"]]
    page2_ids = [item["audit_id"] for item in response2["items"]]
    
    assert not set(page1_ids).intersection(set(page2_ids)), "Found duplicate items across pages"
    
    # Retrieve all pages and verify total number of items matches expected
    all_items = []
    for page in range(1, response1["pages"] + 1):
        page_response = get_audit_logs(api_client, {
            "page": page,
            "page_size": 5
        })
        all_items.extend(page_response["items"])
    
    assert len(all_items) == response1["total"], f"Expected {response1['total']} total items, got {len(all_items)}"
    
    logger.info("Pagination audit test successful")


@pytest.mark.e2e
@pytest.mark.skip(reason='Requires mock server configuration to simulate API failure')
def test_audit_log_for_fallback_mechanism(environment):
    """Tests that fallback mechanism usage is properly logged in audit records."""
    logger.info("Starting fallback mechanism audit test")
    
    # Create API client
    api_client = create_api_client()
    
    # Configure mock servers to simulate external API failure
    # This setup would require special configuration to make external APIs fail
    
    # Get test scenario
    scenario = get_test_scenario("normal_market")
    ticker = scenario["ticker"]
    position_value = scenario["position_value"]
    loan_days = scenario["loan_days"]
    client_id = scenario["client_id"]
    
    # Make a fee calculation request that will trigger fallback mechanism
    calculation_response = api_client.calculate_locate_fee(
        ticker=ticker,
        position_value=position_value,
        loan_days=loan_days,
        client_id=client_id
    )
    
    # Verify calculation response is successful despite external API failure
    assert calculation_response.status == "success"
    
    # Wait briefly for audit log to be written
    time.sleep(1)
    
    # Retrieve audit logs for the calculation
    audit_logs = get_ticker_audit_logs(api_client, ticker)
    
    # Find the matching audit log entry
    matching_logs = [log for log in audit_logs 
                    if log.get("client_id") == client_id 
                    and Decimal(str(log.get("position_value"))) == position_value
                    and log.get("loan_days") == loan_days]
    
    assert len(matching_logs) > 0, "No matching audit logs found"
    audit_log = matching_logs[0]
    
    # Verify that the audit log contains data_sources indicating fallback usage
    assert "data_sources" in audit_log
    data_sources = audit_log["data_sources"]
    
    # Verify that the data source for the failed API shows a fallback source
    fallback_found = False
    for source, value in data_sources.items():
        if "fallback" in value.lower():
            fallback_found = True
            break
    
    assert fallback_found, "No fallback sources found in audit log"
    
    logger.info("Fallback mechanism audit test successful")