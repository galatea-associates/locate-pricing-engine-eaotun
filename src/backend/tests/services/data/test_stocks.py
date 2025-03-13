# Standard library imports
import pytest
from decimal import Decimal
from unittest import mock

# Internal imports
from ...services.data.stocks import StockService
from ...db.crud import stock
from ...db.models.stock import Stock
from ...schemas.stock import StockSchema, RateResponse
from ...core.constants import BorrowStatus
from ...core.exceptions import TickerNotFoundException, ExternalAPIException
from ...services.external.seclend_api import get_borrow_rate
from ...services.external.market_api import get_stock_volatility
from ...services.external.event_api import get_event_risk_factor
from ...services.calculation.borrow_rate import calculate_borrow_rate
from ...services.cache.redis import RedisCache
from src.backend.tests.conftest import test_db, mock_redis_cache, stock_data, easy_to_borrow_stock, hard_to_borrow_stock, invalid_ticker, mock_seclend_response, mock_market_volatility_response, mock_event_calendar_response


@pytest.mark.unit
def test_get_stock_success(test_db, mock_redis_cache, easy_to_borrow_stock):
    """Test successful retrieval of stock data by ticker"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Mock the stock.get_by_ticker method to return a Stock instance based on easy_to_borrow_stock
    with mock.patch.object(stock, "get_by_ticker", return_value=Stock(**easy_to_borrow_stock)):
        # Call stock_service.get_stock with the ticker from easy_to_borrow_stock
        retrieved_stock = stock_service.get_stock(easy_to_borrow_stock["ticker"])
        
        # Assert that the returned object is a StockSchema instance
        assert isinstance(retrieved_stock, StockSchema)
        # Assert that the ticker matches the input ticker
        assert retrieved_stock.ticker == easy_to_borrow_stock["ticker"]
        # Assert that the borrow_status matches the expected value
        assert retrieved_stock.borrow_status == easy_to_borrow_stock["borrow_status"]


@pytest.mark.unit
def test_get_stock_not_found(test_db, mock_redis_cache, invalid_ticker):
    """Test retrieval of non-existent stock returns None"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Mock the stock.get_by_ticker method to return None
    with mock.patch.object(stock, "get_by_ticker", return_value=None):
        # Call stock_service.get_stock with the invalid_ticker
        retrieved_stock = stock_service.get_stock(invalid_ticker)
        
        # Assert that the returned value is None
        assert retrieved_stock is None


@pytest.mark.unit
def test_get_stock_or_404_success(test_db, mock_redis_cache, easy_to_borrow_stock):
    """Test successful retrieval of stock data by ticker or 404"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Mock the stock.get_by_ticker_or_404 method to return a Stock instance based on easy_to_borrow_stock
    with mock.patch.object(stock, "get_by_ticker_or_404", return_value=Stock(**easy_to_borrow_stock)):
        # Call stock_service.get_stock_or_404 with the ticker from easy_to_borrow_stock
        retrieved_stock = stock_service.get_stock_or_404(easy_to_borrow_stock["ticker"])
        
        # Assert that the returned object is a StockSchema instance
        assert isinstance(retrieved_stock, StockSchema)
        # Assert that the ticker matches the input ticker
        assert retrieved_stock.ticker == easy_to_borrow_stock["ticker"]
        # Assert that the borrow_status matches the expected value
        assert retrieved_stock.borrow_status == easy_to_borrow_stock["borrow_status"]


@pytest.mark.unit
def test_get_stock_or_404_not_found(test_db, mock_redis_cache, invalid_ticker):
    """Test retrieval of non-existent stock raises TickerNotFoundException"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Mock the stock.get_by_ticker_or_404 method to raise TickerNotFoundException
    with mock.patch.object(stock, "get_by_ticker_or_404", side_effect=TickerNotFoundException(invalid_ticker)):
        # Use pytest.raises to assert that calling stock_service.get_stock_or_404 with invalid_ticker raises TickerNotFoundException
        with pytest.raises(TickerNotFoundException):
            stock_service.get_stock_or_404(invalid_ticker)


@pytest.mark.unit
def test_get_stocks_by_borrow_status(test_db, mock_redis_cache, stock_data):
    """Test retrieval of stocks filtered by borrow status"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Filter stock_data to get only EASY status stocks
    easy_stocks = [stock for stock in stock_data if stock["borrow_status"] == BorrowStatus.EASY]
    # Create Stock instances for these filtered stocks
    easy_stock_instances = [Stock(**stock) for stock in easy_stocks]
    
    # Mock the stock.get_stocks_by_borrow_status method to return these Stock instances
    with mock.patch.object(stock, "get_stocks_by_borrow_status", return_value=easy_stock_instances):
        # Call stock_service.get_stocks_by_borrow_status with BorrowStatus.EASY
        retrieved_stocks = stock_service.get_stocks_by_borrow_status(BorrowStatus.EASY)
        
        # Assert that the returned list has the expected length
        assert len(retrieved_stocks) == len(easy_stocks)
        # Assert that all returned items are StockSchema instances
        assert all(isinstance(item, StockSchema) for item in retrieved_stocks)
        # Assert that all returned items have BorrowStatus.EASY
        assert all(item.borrow_status == BorrowStatus.EASY for item in retrieved_stocks)


@pytest.mark.unit
def test_get_current_borrow_rate_with_cache(test_db, mock_redis_cache, easy_to_borrow_stock, mock_seclend_response):
    """Test retrieval of current borrow rate with cache hit"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Create a cached rate response based on mock_seclend_response
    cached_rate = RateResponse(
        ticker=easy_to_borrow_stock["ticker"],
        current_rate=Decimal(mock_seclend_response["rate"]),
        borrow_status=easy_to_borrow_stock["borrow_status"],
        last_updated=datetime.now()
    )
    
    # Mock the RedisCache.get method to return the cached response
    mock_redis_cache.get.return_value = cached_rate.model_dump_json()
    
    # Call stock_service.get_current_borrow_rate with the ticker from easy_to_borrow_stock and use_cache=True
    retrieved_rate = stock_service.get_current_borrow_rate(easy_to_borrow_stock["ticker"], use_cache=True)
    
    # Assert that the returned object is a RateResponse instance
    assert isinstance(retrieved_rate, RateResponse)
    # Assert that the ticker matches the input ticker
    assert retrieved_rate.ticker == easy_to_borrow_stock["ticker"]
    # Assert that the current_rate matches the expected value
    assert retrieved_rate.current_rate == Decimal(mock_seclend_response["rate"])
    
    # Verify that the external API was not called
    assert get_borrow_rate.call_count == 0


@pytest.mark.unit
def test_get_current_borrow_rate_without_cache(test_db, mock_redis_cache, easy_to_borrow_stock, mock_seclend_response, mock_market_volatility_response, mock_event_calendar_response):
    """Test retrieval of current borrow rate with cache miss"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Mock the RedisCache.get method to return None (cache miss)
    mock_redis_cache.get.return_value = None
    
    # Mock the stock.get_by_ticker_or_404 method to return a Stock instance based on easy_to_borrow_stock
    with mock.patch.object(stock, "get_by_ticker_or_404", return_value=Stock(**easy_to_borrow_stock)):
        # Mock the get_borrow_rate function to return mock_seclend_response
        with mock.patch("src.backend.services.data.stocks.get_borrow_rate", return_value=mock_seclend_response):
            # Mock the get_stock_volatility function to return mock_market_volatility_response
            with mock.patch("src.backend.services.data.stocks.get_stock_volatility", return_value=mock_market_volatility_response):
                # Mock the get_event_risk_factor function to return mock_event_calendar_response
                with mock.patch("src.backend.services.data.stocks.get_event_risk_factor", return_value=mock_event_calendar_response):
                    # Mock the calculate_borrow_rate function to return a calculated rate
                    with mock.patch("src.backend.services.data.stocks.calculate_borrow_rate", return_value=Decimal("0.06")):
                        # Call stock_service.get_current_borrow_rate with the ticker from easy_to_borrow_stock and use_cache=False
                        retrieved_rate = stock_service.get_current_borrow_rate(easy_to_borrow_stock["ticker"], use_cache=False)
                        
                        # Assert that the returned object is a RateResponse instance
                        assert isinstance(retrieved_rate, RateResponse)
                        # Assert that the ticker matches the input ticker
                        assert retrieved_rate.ticker == easy_to_borrow_stock["ticker"]
                        # Assert that the current_rate matches the expected calculated value
                        assert retrieved_rate.current_rate == Decimal("0.06")
                        
                        # Verify that the external API was called
                        assert get_borrow_rate.call_count == 1
                        # Verify that the RedisCache.set method was called to cache the result
                        assert mock_redis_cache.set.call_count == 1


@pytest.mark.unit
def test_get_current_borrow_rate_external_api_failure(test_db, mock_redis_cache, easy_to_borrow_stock):
    """Test fallback mechanism when external API fails"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Mock the RedisCache.get method to return None (cache miss)
    mock_redis_cache.get.return_value = None
    
    # Mock the stock.get_by_ticker_or_404 method to return a Stock instance based on easy_to_borrow_stock
    with mock.patch.object(stock, "get_by_ticker_or_404", return_value=Stock(**easy_to_borrow_stock)):
        # Mock the get_borrow_rate function to raise ExternalAPIException
        with mock.patch("src.backend.services.data.stocks.get_borrow_rate", side_effect=ExternalAPIException("SecLend API")):
            # Call stock_service.get_current_borrow_rate with the ticker from easy_to_borrow_stock
            retrieved_rate = stock_service.get_current_borrow_rate(easy_to_borrow_stock["ticker"])
            
            # Assert that the returned object is a RateResponse instance
            assert isinstance(retrieved_rate, RateResponse)
            # Assert that the ticker matches the input ticker
            assert retrieved_rate.ticker == easy_to_borrow_stock["ticker"]
            # Assert that the current_rate matches the min_borrow_rate from the stock
            assert retrieved_rate.current_rate == Decimal(easy_to_borrow_stock["min_borrow_rate"])
            
            # Verify that the fallback mechanism was used
            assert get_borrow_rate.call_count == 1


@pytest.mark.unit
def test_update_stock_borrow_status(test_db, mock_redis_cache, easy_to_borrow_stock):
    """Test updating the borrow status of a stock"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Create a Stock instance based on easy_to_borrow_stock
    stock_instance = Stock(**easy_to_borrow_stock)
    
    # Mock the stock.update_borrow_status method to return the updated Stock with BorrowStatus.HARD
    with mock.patch.object(stock, "update_borrow_status", return_value=Stock(ticker=stock_instance.ticker, borrow_status=BorrowStatus.HARD, lender_api_id=stock_instance.lender_api_id, min_borrow_rate=stock_instance.min_borrow_rate)):
        # Call stock_service.update_stock_borrow_status with the ticker and BorrowStatus.HARD
        updated_stock = stock_service.update_stock_borrow_status(stock_instance.ticker, BorrowStatus.HARD)
        
        # Assert that the returned object is a StockSchema instance
        assert isinstance(updated_stock, StockSchema)
        # Assert that the ticker matches the input ticker
        assert updated_stock.ticker == stock_instance.ticker
        # Assert that the borrow_status is BorrowStatus.HARD
        assert updated_stock.borrow_status == BorrowStatus.HARD
        
        # Verify that the RedisCache.delete method was called to invalidate the cache
        assert mock_redis_cache.delete.call_count == 1


@pytest.mark.unit
def test_update_min_borrow_rate(test_db, mock_redis_cache, easy_to_borrow_stock):
    """Test updating the minimum borrow rate of a stock"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Create a Stock instance based on easy_to_borrow_stock
    stock_instance = Stock(**easy_to_borrow_stock)
    
    # Create a new minimum rate of 0.10
    new_min_rate = Decimal("0.10")
    
    # Mock the stock.update_min_borrow_rate method to return the updated Stock with the new rate
    with mock.patch.object(stock, "update_min_borrow_rate", return_value=Stock(ticker=stock_instance.ticker, borrow_status=stock_instance.borrow_status, lender_api_id=stock_instance.lender_api_id, min_borrow_rate=new_min_rate)):
        # Call stock_service.update_min_borrow_rate with the ticker and new rate
        updated_stock = stock_service.update_min_borrow_rate(stock_instance.ticker, new_min_rate)
        
        # Assert that the returned object is a StockSchema instance
        assert isinstance(updated_stock, StockSchema)
        # Assert that the ticker matches the input ticker
        assert updated_stock.ticker == stock_instance.ticker
        # Assert that the min_borrow_rate is the new rate
        assert updated_stock.min_borrow_rate == new_min_rate
        
        # Verify that the RedisCache.delete method was called to invalidate the cache
        assert mock_redis_cache.delete.call_count == 1


@pytest.mark.unit
def test_sync_stock_from_external_existing(test_db, mock_redis_cache, easy_to_borrow_stock, mock_seclend_response):
    """Test synchronizing existing stock data from external API"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Mock the get_borrow_rate function to return mock_seclend_response
    with mock.patch("src.backend.services.data.stocks.get_borrow_rate", return_value=mock_seclend_response):
        # Mock the stock.exists_by_ticker method to return True
        with mock.patch.object(stock, "exists_by_ticker", return_value=True):
            # Mock the stock.upsert method to return an updated Stock instance
            with mock.patch.object(stock, "upsert", return_value=Stock(**easy_to_borrow_stock)):
                # Call stock_service.sync_stock_from_external with the ticker
                synced_stock = stock_service.sync_stock_from_external(easy_to_borrow_stock["ticker"])
                
                # Assert that the returned object is a StockSchema instance
                assert isinstance(synced_stock, StockSchema)
                # Assert that the ticker matches the input ticker
                assert synced_stock.ticker == easy_to_borrow_stock["ticker"]
                # Assert that the borrow_status matches the expected value from the API response
                assert synced_stock.borrow_status == easy_to_borrow_stock["borrow_status"]
                
                # Verify that the RedisCache.delete method was called to invalidate the cache
                assert mock_redis_cache.delete.call_count == 1


@pytest.mark.unit
def test_sync_stock_from_external_new(test_db, mock_redis_cache, invalid_ticker, mock_seclend_response):
    """Test synchronizing new stock data from external API"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Mock the get_borrow_rate function to return mock_seclend_response
    with mock.patch("src.backend.services.data.stocks.get_borrow_rate", return_value=mock_seclend_response):
        # Mock the stock.exists_by_ticker method to return False
        with mock.patch.object(stock, "exists_by_ticker", return_value=False):
            # Mock the stock.upsert method to return a new Stock instance
            with mock.patch.object(stock, "upsert", return_value=Stock(ticker=invalid_ticker, borrow_status=BorrowStatus.EASY, lender_api_id="test", min_borrow_rate=Decimal("0.01"))):
                # Call stock_service.sync_stock_from_external with the ticker
                synced_stock = stock_service.sync_stock_from_external(invalid_ticker)
                
                # Assert that the returned object is a StockSchema instance
                assert isinstance(synced_stock, StockSchema)
                # Assert that the ticker matches the input ticker
                assert synced_stock.ticker == invalid_ticker
                # Assert that the borrow_status matches the expected value from the API response
                assert synced_stock.borrow_status == BorrowStatus.EASY
                
                # Verify that the RedisCache.delete method was called to invalidate the cache
                assert mock_redis_cache.delete.call_count == 1


@pytest.mark.unit
def test_sync_stock_from_external_api_failure(test_db, mock_redis_cache, easy_to_borrow_stock):
    """Test handling of external API failure during synchronization"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Mock the get_borrow_rate function to raise ExternalAPIException
    with mock.patch("src.backend.services.data.stocks.get_borrow_rate", side_effect=ExternalAPIException("SecLend API")):
        # Use pytest.raises to assert that calling stock_service.sync_stock_from_external raises ExternalAPIException
        with pytest.raises(ExternalAPIException):
            stock_service.sync_stock_from_external(easy_to_borrow_stock["ticker"])


@pytest.mark.unit
def test_invalidate_stock_cache(test_db, mock_redis_cache, easy_to_borrow_stock):
    """Test invalidation of stock cache entries"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Mock the RedisCache.delete method to return True
    mock_redis_cache.delete.return_value = True
    
    # Call stock_service.invalidate_stock_cache with the ticker
    result = stock_service.invalidate_stock_cache(easy_to_borrow_stock["ticker"])
    
    # Assert that the result is True
    assert result is True
    # Verify that the RedisCache.delete method was called twice (once for stock data, once for borrow rate)
    assert mock_redis_cache.delete.call_count == 2


@pytest.mark.unit
def test_exists(test_db, mock_redis_cache, easy_to_borrow_stock):
    """Test checking if a stock exists by ticker"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Mock the stock.exists_by_ticker method to return True
    with mock.patch.object(stock, "exists_by_ticker", return_value=True):
        # Call stock_service.exists with the ticker
        result = stock_service.exists(easy_to_borrow_stock["ticker"])
        # Assert that the result is True
        assert result is True
    
    # Mock the stock.exists_by_ticker method to return False
    with mock.patch.object(stock, "exists_by_ticker", return_value=False):
        # Call stock_service.exists with the ticker
        result = stock_service.exists(easy_to_borrow_stock["ticker"])
        # Assert that the result is False
        assert result is False


@pytest.mark.unit
def test_invalid_ticker_validation(test_db, mock_redis_cache):
    """Test validation of invalid ticker symbols"""
    # Create a StockService instance with mock Redis cache
    stock_service = StockService(cache=mock_redis_cache)
    
    # Create a list of invalid tickers (empty string, None, numeric, too long, special characters)
    invalid_tickers = ["", None, "123", "TOOLONG", "BAD!"]
    
    # For each invalid ticker, use pytest.raises to assert that calling various methods raises ValueError
    for ticker in invalid_tickers:
        with pytest.raises(ValueError):
            stock_service.get_stock(ticker)
        with pytest.raises(ValueError):
            stock_service.get_stock_or_404(ticker)
        with pytest.raises(ValueError):
            stock_service.get_current_borrow_rate(ticker)
        with pytest.raises(ValueError):
            stock_service.update_stock_borrow_status(ticker, BorrowStatus.EASY)
        with pytest.raises(ValueError):
            stock_service.update_min_borrow_rate(ticker, Decimal("0.01"))
        with pytest.raises(ValueError):
            stock_service.sync_stock_from_external(ticker)
        with pytest.raises(ValueError):
            stock_service.invalidate_stock_cache(ticker)
        with pytest.raises(ValueError):
            stock_service.exists(ticker)