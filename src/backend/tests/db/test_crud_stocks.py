# Standard Library Imports
from decimal import Decimal

# Third-Party Imports
import pytest  # pytest 7.4.0+

# Internal Imports
from src.backend.core.constants import BorrowStatus
from src.backend.core.exceptions import TickerNotFoundException
from src.backend.db.crud.stocks import stock
from src.backend.db.models.stock import Stock
from src.backend.schemas.stock import StockCreate, StockUpdate
from src.backend.tests.conftest import test_db
from src.backend.tests.fixtures.stocks import (
    easy_to_borrow_stock,
    hard_to_borrow_stock,
    invalid_ticker,
    stock_data,
)


def test_get_by_ticker(test_db, easy_to_borrow_stock):
    """Test retrieving a stock by ticker symbol"""
    # Arrange
    ticker = easy_to_borrow_stock["ticker"]

    # Act
    retrieved_stock = stock.get_by_ticker(test_db, ticker)

    # Assert
    assert retrieved_stock is not None
    assert retrieved_stock.ticker == ticker
    assert retrieved_stock.borrow_status == BorrowStatus.EASY


def test_get_by_ticker_not_found(test_db, invalid_ticker):
    """Test retrieving a non-existent stock by ticker symbol"""
    # Act
    retrieved_stock = stock.get_by_ticker(test_db, invalid_ticker)

    # Assert
    assert retrieved_stock is None


def test_get_by_ticker_or_404(test_db, easy_to_borrow_stock):
    """Test retrieving a stock by ticker symbol or raising 404"""
    # Arrange
    ticker = easy_to_borrow_stock["ticker"]

    # Act
    retrieved_stock = stock.get_by_ticker_or_404(test_db, ticker)

    # Assert
    assert retrieved_stock is not None
    assert retrieved_stock.ticker == ticker


def test_get_by_ticker_or_404_not_found(test_db, invalid_ticker):
    """Test that get_by_ticker_or_404 raises TickerNotFoundException for non-existent ticker"""
    # Act & Assert
    with pytest.raises(TickerNotFoundException):
        stock.get_by_ticker_or_404(test_db, invalid_ticker)


def test_get_by_lender_api_id(test_db, easy_to_borrow_stock):
    """Test retrieving a stock by lender API ID"""
    # Arrange
    lender_api_id = easy_to_borrow_stock["lender_api_id"]

    # Act
    retrieved_stock = stock.get_by_lender_api_id(test_db, lender_api_id)

    # Assert
    assert retrieved_stock is not None
    assert retrieved_stock.lender_api_id == lender_api_id


def test_get_stocks_by_borrow_status(test_db):
    """Test retrieving stocks filtered by borrow status"""
    # Act
    stocks = stock.get_stocks_by_borrow_status(test_db, BorrowStatus.EASY)

    # Assert
    assert len(stocks) > 0
    for s in stocks:
        assert s.borrow_status == BorrowStatus.EASY


def test_update_min_borrow_rate(test_db, easy_to_borrow_stock):
    """Test updating the minimum borrow rate for a stock"""
    # Arrange
    ticker = easy_to_borrow_stock["ticker"]
    new_min_borrow_rate = Decimal("0.02")

    # Act
    updated_stock = stock.update_min_borrow_rate(test_db, ticker, new_min_borrow_rate)

    # Assert
    assert updated_stock is not None
    assert updated_stock.min_borrow_rate == new_min_borrow_rate

    # Verify the update
    retrieved_stock = stock.get_by_ticker(test_db, ticker)
    assert retrieved_stock.min_borrow_rate == new_min_borrow_rate


def test_update_borrow_status(test_db, easy_to_borrow_stock):
    """Test updating the borrow status for a stock"""
    # Arrange
    ticker = easy_to_borrow_stock["ticker"]
    new_borrow_status = BorrowStatus.MEDIUM

    # Act
    updated_stock = stock.update_borrow_status(test_db, ticker, new_borrow_status)

    # Assert
    assert updated_stock is not None
    assert updated_stock.borrow_status == new_borrow_status

    # Verify the update
    retrieved_stock = stock.get_by_ticker(test_db, ticker)
    assert retrieved_stock.borrow_status == new_borrow_status


def test_create_with_ticker(test_db):
    """Test creating a new stock with a ticker and attributes"""
    # Arrange
    new_ticker = "NVDA"
    attributes = {"borrow_status": BorrowStatus.MEDIUM, "min_borrow_rate": Decimal("0.03")}

    # Act
    created_stock = stock.create_with_ticker(test_db, new_ticker, attributes)

    # Assert
    assert created_stock is not None
    assert created_stock.ticker == new_ticker
    assert created_stock.borrow_status == BorrowStatus.MEDIUM
    assert created_stock.min_borrow_rate == Decimal("0.03")

    # Verify the creation
    retrieved_stock = stock.get_by_ticker(test_db, new_ticker)
    assert retrieved_stock.ticker == new_ticker
    assert retrieved_stock.borrow_status == BorrowStatus.MEDIUM
    assert retrieved_stock.min_borrow_rate == Decimal("0.03")


def test_upsert_create(test_db):
    """Test upserting a new stock (create case)"""
    # Arrange
    new_ticker = "INTC"
    attributes = {"borrow_status": BorrowStatus.EASY, "min_borrow_rate": Decimal("0.01")}

    # Act
    upserted_stock = stock.upsert(test_db, new_ticker, attributes)

    # Assert
    assert upserted_stock is not None
    assert upserted_stock.ticker == new_ticker
    assert upserted_stock.borrow_status == BorrowStatus.EASY
    assert upserted_stock.min_borrow_rate == Decimal("0.01")

    # Verify the creation
    retrieved_stock = stock.get_by_ticker(test_db, new_ticker)
    assert retrieved_stock.ticker == new_ticker
    assert retrieved_stock.borrow_status == BorrowStatus.EASY
    assert retrieved_stock.min_borrow_rate == Decimal("0.01")


def test_upsert_update(test_db, easy_to_borrow_stock):
    """Test upserting an existing stock (update case)"""
    # Arrange
    ticker = easy_to_borrow_stock["ticker"]
    updated_attributes = {"borrow_status": BorrowStatus.HARD, "min_borrow_rate": Decimal("0.50")}

    # Act
    upserted_stock = stock.upsert(test_db, ticker, updated_attributes)

    # Assert
    assert upserted_stock is not None
    assert upserted_stock.ticker == ticker
    assert upserted_stock.borrow_status == BorrowStatus.HARD
    assert upserted_stock.min_borrow_rate == Decimal("0.50")

    # Verify the update
    retrieved_stock = stock.get_by_ticker(test_db, ticker)
    assert retrieved_stock.ticker == ticker
    assert retrieved_stock.borrow_status == BorrowStatus.HARD
    assert retrieved_stock.min_borrow_rate == Decimal("0.50")


def test_remove_by_ticker(test_db, easy_to_borrow_stock):
    """Test removing a stock by ticker symbol"""
    # Arrange
    ticker = easy_to_borrow_stock["ticker"]

    # Act
    removed_stock = stock.remove_by_ticker(test_db, ticker)

    # Assert
    assert removed_stock is not None
    assert removed_stock.ticker == ticker

    # Verify the removal
    retrieved_stock = stock.get_by_ticker(test_db, ticker)
    assert retrieved_stock is None


def test_exists_by_ticker(test_db, easy_to_borrow_stock, invalid_ticker):
    """Test checking if a stock exists by ticker symbol"""
    # Arrange
    valid_ticker = easy_to_borrow_stock["ticker"]

    # Act
    exists_valid = stock.exists_by_ticker(test_db, valid_ticker)
    exists_invalid = stock.exists_by_ticker(test_db, invalid_ticker)

    # Assert
    assert exists_valid is True
    assert exists_invalid is False