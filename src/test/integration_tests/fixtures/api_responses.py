"""
Provides mock API responses for integration testing of the Borrow Rate & Locate Fee Pricing Engine.
This module contains predefined response fixtures for both external APIs (SecLend, Market Volatility, Event Calendar)
and internal API endpoints, allowing tests to run without actual API dependencies.
"""

import pytest  # version: 7.4.0+
from datetime import datetime  # version: standard library
from decimal import Decimal  # version: standard library
from typing import Dict, List, Any, Optional  # version: standard library

from ...backend.core.constants import BorrowStatus, TransactionFeeType, ErrorCodes
from .stocks import TEST_STOCKS
from .brokers import TEST_BROKERS
from .volatility import TEST_VOLATILITY_DATA, MARKET_VOLATILITY_DATA

# Current timestamp for consistent response times
CURRENT_TIMESTAMP = datetime.now().isoformat()

# SecLend API mock responses
SECLEND_API_RESPONSES = {
    # Successful borrow rate response
    'get_borrow_rate_success': {
        'rate': Decimal('0.05'),
        'status': BorrowStatus.EASY.value,
        'timestamp': CURRENT_TIMESTAMP
    },
    
    # Not found response
    'get_borrow_rate_not_found': {
        'error': ErrorCodes.TICKER_NOT_FOUND.value,
        'message': 'Ticker not found',
        'timestamp': CURRENT_TIMESTAMP
    },
    
    # Error response
    'get_borrow_rate_error': {
        'error': ErrorCodes.EXTERNAL_API_UNAVAILABLE.value,
        'message': 'External API error',
        'timestamp': CURRENT_TIMESTAMP
    },
    
    # Batch success response
    'get_borrow_rates_batch_success': {
        'rates': [
            {
                'ticker': 'AAPL',
                'rate': Decimal('0.05'),
                'status': BorrowStatus.EASY.value
            },
            {
                'ticker': 'TSLA',
                'rate': Decimal('0.12'),
                'status': BorrowStatus.MEDIUM.value
            },
            {
                'ticker': 'GME',
                'rate': Decimal('0.35'),
                'status': BorrowStatus.HARD.value
            }
        ],
        'timestamp': CURRENT_TIMESTAMP
    },
    
    # Batch partial success response
    'get_borrow_rates_batch_partial': {
        'rates': [
            {
                'ticker': 'AAPL',
                'rate': Decimal('0.05'),
                'status': BorrowStatus.EASY.value
            },
            {
                'ticker': 'INVALID',
                'error': ErrorCodes.TICKER_NOT_FOUND.value
            },
            {
                'ticker': 'GME',
                'rate': Decimal('0.35'),
                'status': BorrowStatus.HARD.value
            }
        ],
        'timestamp': CURRENT_TIMESTAMP
    }
}

# Market Volatility API mock responses
MARKET_API_RESPONSES = {
    # Successful market volatility response
    'get_market_volatility_success': {
        'value': Decimal('20.5'),
        'timestamp': CURRENT_TIMESTAMP
    },
    
    # Error response
    'get_market_volatility_error': {
        'error': ErrorCodes.EXTERNAL_API_UNAVAILABLE.value,
        'message': 'Market data API unavailable',
        'timestamp': CURRENT_TIMESTAMP
    },
    
    # Successful stock volatility response
    'get_stock_volatility_success': {
        'ticker': 'AAPL',
        'volatility': Decimal('18.5'),
        'event_risk_factor': 2,
        'timestamp': CURRENT_TIMESTAMP
    },
    
    # Not found response
    'get_stock_volatility_not_found': {
        'error': ErrorCodes.TICKER_NOT_FOUND.value,
        'message': 'Volatility data not found for ticker',
        'timestamp': CURRENT_TIMESTAMP
    },
    
    # Successful volatility history response
    'get_volatility_history_success': {
        'ticker': 'AAPL',
        'history': [
            {
                'date': (datetime.now() - datetime.timedelta(days=7)).isoformat(),
                'volatility': Decimal('17.2')
            },
            {
                'date': (datetime.now() - datetime.timedelta(days=6)).isoformat(),
                'volatility': Decimal('17.8')
            },
            {
                'date': (datetime.now() - datetime.timedelta(days=5)).isoformat(),
                'volatility': Decimal('18.1')
            },
            {
                'date': (datetime.now() - datetime.timedelta(days=4)).isoformat(),
                'volatility': Decimal('18.3')
            },
            {
                'date': (datetime.now() - datetime.timedelta(days=3)).isoformat(),
                'volatility': Decimal('18.5')
            }
        ],
        'timestamp': CURRENT_TIMESTAMP
    }
}

# Event Calendar API mock responses
EVENT_API_RESPONSES = {
    # Successful events response
    'get_events_success': {
        'events': [
            {
                'event_id': 'evt_12345',
                'ticker': 'AAPL',
                'event_type': 'earnings',
                'event_date': (datetime.now() + datetime.timedelta(days=7)).isoformat(),
                'risk_factor': 5
            }
        ],
        'timestamp': CURRENT_TIMESTAMP
    },
    
    # Empty events response
    'get_events_empty': {
        'events': [],
        'timestamp': CURRENT_TIMESTAMP
    },
    
    # Error response
    'get_events_error': {
        'error': ErrorCodes.EXTERNAL_API_UNAVAILABLE.value,
        'message': 'Event calendar API unavailable',
        'timestamp': CURRENT_TIMESTAMP
    },
    
    # High risk events response
    'get_events_high_risk': {
        'events': [
            {
                'event_id': 'evt_67890',
                'ticker': 'GME',
                'event_type': 'earnings',
                'event_date': (datetime.now() + datetime.timedelta(days=2)).isoformat(),
                'risk_factor': 8
            },
            {
                'event_id': 'evt_67891',
                'ticker': 'GME',
                'event_type': 'shareholder_meeting',
                'event_date': (datetime.now() + datetime.timedelta(days=5)).isoformat(),
                'risk_factor': 7
            }
        ],
        'timestamp': CURRENT_TIMESTAMP
    }
}

# Calculation API mock responses
CALCULATION_API_RESPONSES = {
    # Successful fee calculation response
    'calculate_locate_fee_success': {
        'status': 'success',
        'total_fee': Decimal('3428.77'),
        'breakdown': {
            'borrow_cost': Decimal('3195.34'),
            'markup': Decimal('188.53'),
            'transaction_fees': Decimal('40.90')
        },
        'borrow_rate_used': Decimal('0.19')
    },
    
    # Error response
    'calculate_locate_fee_error': {
        'status': 'error',
        'error': ErrorCodes.CALCULATION_ERROR.value,
        'message': 'Error calculating locate fee'
    },
    
    # Successful borrow rate response
    'get_borrow_rate_success': {
        'status': 'success',
        'ticker': 'AAPL',
        'current_rate': Decimal('0.05'),
        'borrow_status': BorrowStatus.EASY.value,
        'volatility_index': Decimal('18.5'),
        'event_risk_factor': 2,
        'last_updated': CURRENT_TIMESTAMP
    }
}

# Standard error responses
ERROR_RESPONSES = {
    # Invalid parameter error
    'invalid_parameter': {
        'status': 'error',
        'error': ErrorCodes.INVALID_PARAMETER.value,
        'message': "Invalid parameter: 'loan_days' must be ≥ 1",
        'valid_params': ['ticker', 'position_value>0', 'loan_days>0', 'client_id']
    },
    
    # Unauthorized error
    'unauthorized': {
        'status': 'error',
        'error': ErrorCodes.UNAUTHORIZED.value,
        'message': 'Invalid or missing API key'
    },
    
    # Ticker not found error
    'ticker_not_found': {
        'status': 'error',
        'error': ErrorCodes.TICKER_NOT_FOUND.value,
        'message': 'Ticker not found: {ticker}'
    },
    
    # Rate limit exceeded error
    'rate_limit_exceeded': {
        'status': 'error',
        'error': ErrorCodes.RATE_LIMIT_EXCEEDED.value,
        'message': 'Rate limit exceeded. Try again in {retry_after} seconds'
    },
    
    # Calculation error
    'calculation_error': {
        'status': 'error',
        'error': ErrorCodes.CALCULATION_ERROR.value,
        'message': 'Error calculating fee: {error_detail}'
    },
    
    # External API unavailable error
    'external_api_unavailable': {
        'status': 'error',
        'error': ErrorCodes.EXTERNAL_API_UNAVAILABLE.value,
        'message': 'External API unavailable: {api_name}'
    }
}


def generate_seclend_response(
    ticker: str,
    rate: Optional[Decimal] = None,
    status: Optional[BorrowStatus] = None,
    success: bool = True
) -> Dict[str, Any]:
    """
    Generates a custom SecLend API response with specified parameters.
    
    Args:
        ticker: Stock symbol for the response
        rate: Borrow rate to include in the response (if None, uses a default based on the ticker)
        status: Borrow status to include in the response (if None, determines from ticker)
        success: Whether to generate a successful response or an error
    
    Returns:
        Dict[str, Any]: Custom SecLend API response
    """
    # If success is True, create a successful response with the provided rate and status
    if success:
        # If rate is not provided, use a default rate based on the ticker's borrow status
        if rate is None:
            for stock in TEST_STOCKS:
                if stock['ticker'] == ticker:
                    rate = stock['min_borrow_rate'] * Decimal('2.0')  # Example calculation
                    break
            else:
                # Default rate if ticker not found
                rate = Decimal('0.05')
        
        # If status is not provided, determine status based on the ticker
        if status is None:
            for stock in TEST_STOCKS:
                if stock['ticker'] == ticker:
                    status = stock['borrow_status']
                    break
            else:
                # Default status if ticker not found
                status = BorrowStatus.MEDIUM
        
        # Build successful response
        response = {
            'rate': rate,
            'status': status.value if isinstance(status, BorrowStatus) else status,
            'timestamp': CURRENT_TIMESTAMP
        }
    else:
        # If success is False, create an error response
        response = {
            'error': ErrorCodes.TICKER_NOT_FOUND.value,
            'message': f'Ticker not found: {ticker}',
            'timestamp': CURRENT_TIMESTAMP
        }
    
    return response


def generate_market_volatility_response(
    ticker: Optional[str] = None,
    volatility: Optional[Decimal] = None,
    event_risk_factor: Optional[int] = None,
    success: bool = True
) -> Dict[str, Any]:
    """
    Generates a custom Market Volatility API response with specified parameters.
    
    Args:
        ticker: Stock symbol for the response (None for market-wide volatility)
        volatility: Volatility value to include in the response
        event_risk_factor: Event risk factor to include in the response
        success: Whether to generate a successful response or an error
    
    Returns:
        Dict[str, Any]: Custom Market Volatility API response
    """
    # If success is True and ticker is provided, create a stock-specific volatility response
    if success:
        if ticker:
            # If volatility is not provided, use default values from test data
            if volatility is None:
                for vol_data in TEST_VOLATILITY_DATA:
                    if vol_data['stock_id'] == ticker:
                        volatility = vol_data['vol_index']
                        break
                else:
                    # Default volatility if ticker not found
                    volatility = Decimal('20.0')
            
            # If event_risk_factor is not provided, use default values from test data
            if event_risk_factor is None:
                for vol_data in TEST_VOLATILITY_DATA:
                    if vol_data['stock_id'] == ticker:
                        event_risk_factor = vol_data['event_risk_factor']
                        break
                else:
                    # Default event_risk_factor if ticker not found
                    event_risk_factor = 0
            
            # Build stock-specific volatility response
            response = {
                'ticker': ticker,
                'volatility': volatility,
                'event_risk_factor': event_risk_factor,
                'timestamp': CURRENT_TIMESTAMP
            }
        else:
            # If success is True and ticker is not provided, create a market-wide volatility response
            response = {
                'value': volatility if volatility is not None else MARKET_VOLATILITY_DATA['value'],
                'timestamp': CURRENT_TIMESTAMP
            }
    else:
        # If success is False, create an error response
        response = {
            'error': ErrorCodes.EXTERNAL_API_UNAVAILABLE.value,
            'message': 'Market volatility API unavailable',
            'timestamp': CURRENT_TIMESTAMP
        }
    
    return response


def generate_event_response(
    ticker: str,
    events: Optional[List[Dict[str, Any]]] = None,
    success: bool = True
) -> Dict[str, Any]:
    """
    Generates a custom Event Calendar API response with specified parameters.
    
    Args:
        ticker: Stock symbol for the response
        events: List of events to include in the response
        success: Whether to generate a successful response or an error
    
    Returns:
        Dict[str, Any]: Custom Event Calendar API response
    """
    # If success is True and events are provided, create a response with the provided events
    if success:
        # If success is True and events are not provided, create a response with default events for the ticker
        if events is None:
            # Check if we have predefined events for this ticker
            if ticker == 'AAPL':
                events = [
                    {
                        'event_id': 'evt_12345',
                        'ticker': ticker,
                        'event_type': 'earnings',
                        'event_date': (datetime.now() + datetime.timedelta(days=7)).isoformat(),
                        'risk_factor': 5
                    }
                ]
            elif ticker == 'GME':
                events = [
                    {
                        'event_id': 'evt_67890',
                        'ticker': ticker,
                        'event_type': 'earnings',
                        'event_date': (datetime.now() + datetime.timedelta(days=2)).isoformat(),
                        'risk_factor': 8
                    },
                    {
                        'event_id': 'evt_67891',
                        'ticker': ticker,
                        'event_type': 'shareholder_meeting',
                        'event_date': (datetime.now() + datetime.timedelta(days=5)).isoformat(),
                        'risk_factor': 7
                    }
                ]
            else:
                # If no events are available for the ticker, return an empty events list
                events = []
        
        # Build successful response
        response = {
            'events': events,
            'timestamp': CURRENT_TIMESTAMP
        }
    else:
        # If success is False, create an error response
        response = {
            'error': ErrorCodes.EXTERNAL_API_UNAVAILABLE.value,
            'message': 'Event calendar API unavailable',
            'timestamp': CURRENT_TIMESTAMP
        }
    
    return response


def generate_calculation_response(
    ticker: str,
    position_value: Decimal,
    loan_days: int,
    client_id: str,
    borrow_rate: Optional[Decimal] = None,
    success: bool = True
) -> Dict[str, Any]:
    """
    Generates a custom calculation API response with specified parameters.
    
    Args:
        ticker: Stock symbol for the calculation
        position_value: Notional value of short position in USD
        loan_days: Duration of borrow in days
        client_id: Client identifier for fee structure
        borrow_rate: Borrow rate to use in the calculation (if None, determines based on ticker)
        success: Whether to generate a successful response or an error
    
    Returns:
        Dict[str, Any]: Custom calculation API response
    """
    # If success is True, create a successful fee calculation response
    if success:
        # If borrow_rate is not provided, determine rate based on the ticker
        if borrow_rate is None:
            for stock in TEST_STOCKS:
                if stock['ticker'] == ticker:
                    # Simple example calculation - in real implementation this would be more complex
                    borrow_rate = stock['min_borrow_rate'] * Decimal('2.0')
                    break
            else:
                # Default rate if ticker not found
                borrow_rate = Decimal('0.05')
        
        # Get broker configuration
        broker_config = None
        for broker in TEST_BROKERS:
            if broker['client_id'] == client_id:
                broker_config = broker
                break
        
        # Use default configuration if broker not found
        if broker_config is None:
            broker_config = {
                'markup_percentage': Decimal('5.0'),
                'transaction_fee_type': TransactionFeeType.FLAT,
                'transaction_amount': Decimal('25.0')
            }
        
        # Calculate fee components based on position_value, loan_days, and borrow_rate
        days_in_year = Decimal('365')
        
        # Calculate borrow_cost: position_value * borrow_rate * (loan_days / 365)
        borrow_cost = (position_value * borrow_rate * Decimal(loan_days) / days_in_year).quantize(
            Decimal('0.01')
        )
        
        # Apply broker markup and transaction fees based on client_id
        # Markup: borrow_cost * (markup_percentage / 100)
        markup = (borrow_cost * broker_config['markup_percentage'] / Decimal('100')).quantize(
            Decimal('0.01')
        )
        
        # Transaction fee
        if broker_config['transaction_fee_type'] == TransactionFeeType.FLAT:
            transaction_fee = broker_config['transaction_amount']
        else:  # PERCENTAGE
            transaction_fee = (position_value * broker_config['transaction_amount'] / Decimal('100')).quantize(
                Decimal('0.01')
            )
        
        # Total fee
        total_fee = borrow_cost + markup + transaction_fee
        
        # Build successful response
        response = {
            'status': 'success',
            'total_fee': total_fee,
            'breakdown': {
                'borrow_cost': borrow_cost,
                'markup': markup,
                'transaction_fees': transaction_fee
            },
            'borrow_rate_used': borrow_rate
        }
    else:
        # If success is False, create an error response
        response = {
            'status': 'error',
            'error': ErrorCodes.CALCULATION_ERROR.value,
            'message': 'Error calculating locate fee'
        }
    
    return response