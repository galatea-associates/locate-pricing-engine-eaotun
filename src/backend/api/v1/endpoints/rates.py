"""
Implements the REST API endpoints for retrieving borrow rates in the Borrow Rate & Locate Fee Pricing Engine.
This module provides endpoints to get current borrow rates for specific securities, including volatility and event risk adjustments. It handles authentication, input validation, caching, and error handling for all rate-related API requests.
"""

import logging
from decimal import Decimal
from typing import Optional, List

# FastAPI imports
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status  # fastapi 0.103.0+

# Internal imports
from ...api.deps import get_db, get_redis_cache, authenticate_api_key, validate_ticker  # Import database session context manager
from ...schemas.response import BorrowRateResponse  # Import response model
from ...services.data.stocks import StockService  # Import stock data service
from ...services.calculation.borrow_rate import calculate_borrow_rate  # Import borrow rate calculation function
from ...core.constants import BorrowStatus  # Import borrow status enum
from ...core.exceptions import TickerNotFoundException, ExternalAPIException  # Import exception class
from ...services.cache.redis import RedisCache  # Import Redis cache client

# Initialize logger
logger = logging.getLogger(__name__)

# Create API router instance
router = APIRouter(tags=["rates"])


@router.get('/{ticker}', response_model=BorrowRateResponse, status_code=status.HTTP_200_OK)
@router.get('/ticker/{ticker}', response_model=BorrowRateResponse, status_code=status.HTTP_200_OK)
async def get_borrow_rate(
    ticker: str = Path(..., title="Stock ticker symbol"),
    client_id: str = Depends(authenticate_api_key),
    use_cache: bool = Query(True, description="Whether to use cached data if available"),
    cache: RedisCache = Depends(get_redis_cache),
    db: any = Depends(get_db)
) -> BorrowRateResponse:
    """
    Endpoint to get the current borrow rate for a specific ticker
    """
    logger.info(f"Request received to get borrow rate for ticker: {ticker}")

    try:
        # Initialize StockService with the provided cache and db session
        stock_service = StockService(cache=cache, db=db)

        # Try to get the current borrow rate using stock_service.get_current_borrow_rate
        rate_data = await stock_service.get_current_borrow_rate(ticker, use_cache=use_cache)

        # Create and return BorrowRateResponse with status='success' and rate data
        response = BorrowRateResponse(
            status="success",
            ticker=ticker,
            current_rate=rate_data["current_rate"],
            borrow_status=rate_data["borrow_status"],
            volatility_index=rate_data["volatility_index"],
            event_risk_factor=rate_data["event_risk_factor"],
            last_updated=rate_data["last_updated"]
        )
        return response

    except TickerNotFoundException as e:
        # Handle TickerNotFoundException and return 404 Not Found
        logger.warning(f"Ticker not found: {ticker}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except ExternalAPIException as e:
        # Handle ExternalAPIException and return 503 Service Unavailable
        logger.error(f"External API error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    except Exception as e:
        # Handle other exceptions and return 500 Internal Server Error
        logger.exception(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/status/{status}', response_model=List[BorrowRateResponse], status_code=status.HTTP_200_OK)
async def get_borrow_rates_by_status(
    status: BorrowStatus = Path(..., title="Borrow status (EASY, MEDIUM, HARD)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    client_id: str = Depends(authenticate_api_key),
    cache: RedisCache = Depends(get_redis_cache),
    db: any = Depends(get_db)
) -> List[BorrowRateResponse]:
    """
    Endpoint to get borrow rates for stocks with a specific borrow status
    """
    logger.info(f"Request received to get borrow rates by status: {status}")

    try:
        # Initialize StockService with the provided cache and db session
        stock_service = StockService(cache=cache, db=db)

        # Get stocks with the specified borrow status using stock_service.get_stocks_by_borrow_status
        stocks = await stock_service.get_stocks_by_borrow_status(status=status, skip=skip, limit=limit)

        # Create BorrowRateResponse objects for each stock
        borrow_rates = []
        for stock in stocks:
            rate_data = await stock_service.get_current_borrow_rate(stock.ticker)
            borrow_rates.append(
                BorrowRateResponse(
                    status="success",
                    ticker=stock.ticker,
                    current_rate=rate_data["current_rate"],
                    borrow_status=rate_data["borrow_status"],
                    volatility_index=rate_data["volatility_index"],
                    event_risk_factor=rate_data["event_risk_factor"],
                    last_updated=rate_data["last_updated"]
                )
            )

        # Return list of BorrowRateResponse objects
        return borrow_rates

    except Exception as e:
        # Handle exceptions and return appropriate error responses
        logger.exception(f"Error getting borrow rates by status: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get('/{ticker}/calculate', response_model=BorrowRateResponse, status_code=status.HTTP_200_OK)
async def calculate_custom_rate(
    ticker: str = Path(..., title="Stock ticker symbol"),
    volatility_index: Optional[Decimal] = Query(None, description="Custom volatility index"),
    event_risk_factor: Optional[int] = Query(None, description="Custom event risk factor"),
    client_id: str = Depends(authenticate_api_key),
    cache: RedisCache = Depends(get_redis_cache),
    db: any = Depends(get_db)
) -> BorrowRateResponse:
    """
    Endpoint to calculate a custom borrow rate with specific parameters
    """
    logger.info(f"Request received to calculate custom rate for ticker: {ticker}")

    try:
        # Initialize StockService with the provided cache and db session
        stock_service = StockService(cache=cache, db=db)

        # Get stock data to verify ticker exists and get minimum rate
        stock = await stock_service.get_stock_or_404(ticker)
        min_rate = stock.min_borrow_rate

        # Calculate borrow rate using calculate_borrow_rate with provided parameters
        calculated_rate = await calculate_borrow_rate(ticker, min_rate=min_rate)

        # Create and return BorrowRateResponse with calculated rate
        response = BorrowRateResponse(
            status="success",
            ticker=ticker,
            current_rate=calculated_rate,
            borrow_status=stock.borrow_status.value,
            volatility_index=volatility_index,
            event_risk_factor=event_risk_factor,
            last_updated=stock.updated_at
        )
        return response

    except TickerNotFoundException as e:
        # Handle TickerNotFoundException and return 404 Not Found
        logger.warning(f"Ticker not found: {ticker}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except ExternalAPIException as e:
        # Handle ExternalAPIException and return 503 Service Unavailable
        logger.error(f"External API error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    except Exception as e:
        # Handle exceptions and return appropriate error responses
        logger.exception(f"Error calculating custom rate: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))