"""
Unit tests for the Event Calendar API client implementation in the Borrow Rate & Locate Fee Pricing Engine.

These tests verify the functionality of retrieving event risk data from the external Event Calendar API,
including successful data retrieval, error handling, and fallback mechanisms.
"""

import pytest
import respx
import asyncio
from unittest.mock import patch

from pytest_asyncio import pytest_asyncio

from ....services.external.event_api import (
    get_event_risk_factor,
    async_get_event_risk_factor,
    get_upcoming_events,
    async_get_upcoming_events,
    get_event_types,
    get_event_details
)
from ....core.exceptions import ExternalAPIException
from ...fixtures.api_responses import (
    mock_event_calendar_response,
    mock_high_event_risk_response,
    mock_no_event_risk_response,
    mock_api_error_response
)


@pytest.mark.parametrize('ticker, expected_risk_factor', [('AAPL', 3), ('TSLA', 5), ('GME', 8)])
def test_get_event_risk_factor_success(respx_mock, ticker, expected_risk_factor):
    """Test successful retrieval of event risk factor for a ticker."""
    # Arrange
    api_url = "https://api.example.com/events"
    respx_mock.get(f"{api_url}").mock(
        return_value=respx.Response(
            status_code=200,
            json=mock_event_calendar_response(ticker)
        )
    )
    
    # Act
    with patch('src.backend.services.external.event_api.get_api_config', 
               return_value={'base_url': 'https://api.example.com', 'events_endpoint': 'events', 'api_key': 'test_key'}):
        result = get_event_risk_factor(ticker)
    
    # Assert
    assert result == expected_risk_factor
    assert respx_mock.calls.last.request.url.path == "/events"
    assert respx_mock.calls.last.request.url.params["ticker"] == ticker
    assert respx_mock.calls.last.request.headers["X-API-Key"] == "test_key"


@pytest.mark.parametrize('error_type', ['not_found', 'unauthorized', 'server_error'])
def test_get_event_risk_factor_api_error(respx_mock, error_type):
    """Test fallback to default risk factor when API returns an error."""
    # Arrange
    ticker = "AAPL"
    api_url = "https://api.example.com/events"
    status_code = 404 if error_type == 'not_found' else 401 if error_type == 'unauthorized' else 500
    respx_mock.get(f"{api_url}").mock(
        return_value=respx.Response(
            status_code=status_code,
            json=mock_api_error_response(error_type)
        )
    )
    
    # Act
    with patch('src.backend.services.external.event_api.get_api_config', 
               return_value={'base_url': 'https://api.example.com', 'events_endpoint': 'events', 'api_key': 'test_key'}):
        result = get_event_risk_factor(ticker)
    
    # Assert
    assert result == 0  # Default risk factor
    assert respx_mock.calls.last.request.url.path == "/events"


def test_get_event_risk_factor_api_timeout(respx_mock):
    """Test fallback to default risk factor when API times out."""
    # Arrange
    ticker = "AAPL"
    api_url = "https://api.example.com/events"
    respx_mock.get(f"{api_url}").mock(side_effect=TimeoutError("Connection timeout"))
    
    # Act
    with patch('src.backend.services.external.event_api.get_api_config', 
               return_value={'base_url': 'https://api.example.com', 'events_endpoint': 'events', 'api_key': 'test_key'}):
        result = get_event_risk_factor(ticker)
    
    # Assert
    assert result == 0  # Default risk factor


def test_get_event_risk_factor_no_events(respx_mock, mock_no_event_risk_response):
    """Test handling of response with no events."""
    # Arrange
    ticker = "AAPL"
    api_url = "https://api.example.com/events"
    respx_mock.get(f"{api_url}").mock(
        return_value=respx.Response(
            status_code=200,
            json=mock_no_event_risk_response(ticker)
        )
    )
    
    # Act
    with patch('src.backend.services.external.event_api.get_api_config', 
               return_value={'base_url': 'https://api.example.com', 'events_endpoint': 'events', 'api_key': 'test_key'}):
        result = get_event_risk_factor(ticker)
    
    # Assert
    assert result == 0  # Default risk factor when no events found


def test_get_event_risk_factor_invalid_response(respx_mock):
    """Test handling of invalid API response format."""
    # Arrange
    ticker = "AAPL"
    api_url = "https://api.example.com/events"
    respx_mock.get(f"{api_url}").mock(
        return_value=respx.Response(
            status_code=200,
            json={"invalid_format": True}  # Missing required 'events' field
        )
    )
    
    # Act
    with patch('src.backend.services.external.event_api.get_api_config', 
               return_value={'base_url': 'https://api.example.com', 'events_endpoint': 'events', 'api_key': 'test_key'}):
        result = get_event_risk_factor(ticker)
    
    # Assert
    assert result == 0  # Default risk factor when response is invalid


@pytest.mark.asyncio
@pytest.mark.parametrize('ticker, expected_risk_factor', [('AAPL', 3), ('TSLA', 5), ('GME', 8)])
async def test_async_get_event_risk_factor_success(respx_mock, ticker, expected_risk_factor):
    """Test successful asynchronous retrieval of event risk factor."""
    # Arrange
    api_url = "https://api.example.com/events"
    respx_mock.get(f"{api_url}").mock(
        return_value=respx.Response(
            status_code=200,
            json=mock_event_calendar_response(ticker)
        )
    )
    
    # Act
    with patch('src.backend.services.external.event_api.get_api_config', 
               return_value={'base_url': 'https://api.example.com', 'events_endpoint': 'events', 'api_key': 'test_key'}):
        result = await async_get_event_risk_factor(ticker)
    
    # Assert
    assert result == expected_risk_factor
    assert respx_mock.calls.last.request.url.path == "/events"
    assert respx_mock.calls.last.request.url.params["ticker"] == ticker
    assert respx_mock.calls.last.request.headers["X-API-Key"] == "test_key"


@pytest.mark.parametrize('ticker', ['AAPL', 'TSLA', 'GME'])
def test_get_upcoming_events_success(respx_mock, ticker):
    """Test successful retrieval of upcoming events for a ticker."""
    # Arrange
    api_url = "https://api.example.com/events"
    respx_mock.get(f"{api_url}").mock(
        return_value=respx.Response(
            status_code=200,
            json=mock_event_calendar_response(ticker)
        )
    )
    
    # Act
    with patch('src.backend.services.external.event_api.get_api_config', 
               return_value={'base_url': 'https://api.example.com', 'events_endpoint': 'events', 'api_key': 'test_key'}):
        result = get_upcoming_events(ticker)
    
    # Assert
    assert isinstance(result, list)
    if len(result) > 0:
        assert "event_id" in result[0]
        assert "ticker" in result[0]
        assert "event_type" in result[0]
        assert "event_date" in result[0]
        assert "risk_factor" in result[0]
    
    assert respx_mock.calls.last.request.url.path == "/events"
    assert respx_mock.calls.last.request.url.params["ticker"] == ticker


def test_get_upcoming_events_with_days_ahead(respx_mock):
    """Test retrieval of upcoming events with days_ahead parameter."""
    # Arrange
    ticker = "AAPL"
    days_ahead = 7
    api_url = "https://api.example.com/events"
    respx_mock.get(f"{api_url}").mock(
        return_value=respx.Response(
            status_code=200,
            json=mock_event_calendar_response(ticker)
        )
    )
    
    # Act
    with patch('src.backend.services.external.event_api.get_api_config', 
               return_value={'base_url': 'https://api.example.com', 'events_endpoint': 'events', 'api_key': 'test_key'}):
        result = get_upcoming_events(ticker, days_ahead=days_ahead)
    
    # Assert
    assert isinstance(result, list)
    assert respx_mock.calls.last.request.url.path == "/events"
    assert respx_mock.calls.last.request.url.params["ticker"] == ticker
    assert respx_mock.calls.last.request.url.params["days_ahead"] == str(days_ahead)


@pytest.mark.asyncio
@pytest.mark.parametrize('ticker', ['AAPL', 'TSLA', 'GME'])
async def test_async_get_upcoming_events_success(respx_mock, ticker):
    """Test successful asynchronous retrieval of upcoming events."""
    # Arrange
    api_url = "https://api.example.com/events"
    respx_mock.get(f"{api_url}").mock(
        return_value=respx.Response(
            status_code=200,
            json=mock_event_calendar_response(ticker)
        )
    )
    
    # Act
    with patch('src.backend.services.external.event_api.get_api_config', 
               return_value={'base_url': 'https://api.example.com', 'events_endpoint': 'events', 'api_key': 'test_key'}):
        result = await async_get_upcoming_events(ticker)
    
    # Assert
    assert isinstance(result, list)
    if len(result) > 0:
        assert "event_id" in result[0]
        assert "ticker" in result[0]
        assert "event_type" in result[0]
        assert "event_date" in result[0]
        assert "risk_factor" in result[0]
    
    assert respx_mock.calls.last.request.url.path == "/events"
    assert respx_mock.calls.last.request.url.params["ticker"] == ticker


def test_get_event_types_success(respx_mock):
    """Test successful retrieval of event types."""
    # Arrange
    api_url = "https://api.example.com/event-types"
    event_types = ["earnings", "dividend", "merger", "split", "conference"]
    respx_mock.get(f"{api_url}").mock(
        return_value=respx.Response(
            status_code=200,
            json={"event_types": event_types, "count": len(event_types)}
        )
    )
    
    # Act
    with patch('src.backend.services.external.event_api.get_api_config', 
               return_value={'base_url': 'https://api.example.com', 'event_types_endpoint': 'event-types', 'api_key': 'test_key'}):
        result = get_event_types()
    
    # Assert
    assert result == event_types
    assert respx_mock.calls.last.request.url.path == "/event-types"
    assert respx_mock.calls.last.request.headers["X-API-Key"] == "test_key"


def test_get_event_details_success(respx_mock):
    """Test successful retrieval of event details."""
    # Arrange
    event_id = "evt_AAPL_001"
    api_url = "https://api.example.com/event"
    event_details = {
        "event_id": event_id,
        "ticker": "AAPL",
        "event_type": "earnings",
        "event_date": "2023-12-15",
        "risk_factor": 7,
        "description": "Q4 Earnings announcement"
    }
    respx_mock.get(f"{api_url}").mock(
        return_value=respx.Response(
            status_code=200,
            json=event_details
        )
    )
    
    # Act
    with patch('src.backend.services.external.event_api.get_api_config', 
               return_value={'base_url': 'https://api.example.com', 'event_details_endpoint': 'event', 'api_key': 'test_key'}):
        result = get_event_details(event_id)
    
    # Assert
    assert result == event_details
    assert respx_mock.calls.last.request.url.path == "/event"
    assert respx_mock.calls.last.request.url.params["event_id"] == event_id
    assert respx_mock.calls.last.request.headers["X-API-Key"] == "test_key"


def test_get_event_details_not_found(respx_mock):
    """Test handling of event details not found."""
    # Arrange
    event_id = "evt_nonexistent"
    api_url = "https://api.example.com/event"
    respx_mock.get(f"{api_url}").mock(
        return_value=respx.Response(
            status_code=404,
            json=mock_api_error_response('not_found')
        )
    )
    
    # Act
    with patch('src.backend.services.external.event_api.get_api_config', 
               return_value={'base_url': 'https://api.example.com', 'event_details_endpoint': 'event', 'api_key': 'test_key'}):
        result = get_event_details(event_id)
    
    # Assert
    assert result == {}  # Empty dict when event not found
    assert respx_mock.calls.last.request.url.path == "/event"
    assert respx_mock.calls.last.request.url.params["event_id"] == event_id