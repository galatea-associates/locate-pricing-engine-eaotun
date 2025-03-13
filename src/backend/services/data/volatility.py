"""
Service implementation for volatility data management in the Borrow Rate & Locate Fee Pricing Engine.

This module provides high-level access to volatility metrics and event risk factors used in borrow rate calculations,
with caching, validation, and fallback mechanisms.
"""

import logging
from typing import List, Dict, Optional, Union, Any
from datetime import datetime

from .utils import (
    DataServiceBase,
    validate_ticker,
    cache_result,
    DEFAULT_CACHE_TTL
)
from ...db.crud.volatility import volatility
from ...core.exceptions import TickerNotFoundException, ExternalAPIException
from ...core.constants import VOLATILITY_CACHE_TTL, EVENT_RISK_CACHE_TTL
from ..cache.redis import redis_cache
from ..external.market_api import get_market_volatility, get_stock_volatility, get_volatility_history
from ..external.event_api import get_event_risk_factor, get_upcoming_events
from ...schemas.volatility import VolatilityCreate, VolatilityUpdate, VolatilityResponse


class VolatilityService(DataServiceBase):
    """Service class for managing volatility and event risk data"""
    
    def __init__(self):
        """Initialize the volatility service"""
        super().__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
    
    @cache_result(VOLATILITY_CACHE_TTL)
    def get_volatility(self, ticker: str) -> VolatilityResponse:
        """
        Get the latest volatility data for a stock
        
        Args:
            ticker: Stock symbol
            
        Returns:
            VolatilityResponse: Volatility data including vol_index and event_risk_factor
            
        Raises:
            TickerNotFoundException: If the ticker is not found
            ValidationException: If the ticker is invalid
        """
        # Validate ticker
        ticker = validate_ticker(ticker)
        
        try:
            # Try to get volatility from database
            with self._get_db_session() as db:
                volatility_data = volatility.get_latest_by_stock(db, ticker)
            
            # If not found in database, fetch from external API
            if not volatility_data:
                self._log_operation(
                    "get_volatility",
                    f"No volatility data found in database for {ticker}, fetching from API",
                    "INFO"
                )
                
                # Fetch from external API
                fetched_data = self._fetch_volatility_from_api(ticker)
                
                # Store in database
                volatility_obj = VolatilityCreate(
                    stock_id=ticker,
                    vol_index=fetched_data['vol_index'],
                    event_risk_factor=fetched_data['event_risk_factor']
                )
                
                with self._get_db_session() as db:
                    volatility_data = volatility.create_volatility(db, volatility_obj)
            
            # Format response
            response = self._format_volatility_response(volatility_data.to_dict())
            
            self._log_operation(
                "get_volatility",
                f"Retrieved volatility data for {ticker}: vol_index={response.vol_index}, event_risk={response.event_risk_factor}",
                "INFO"
            )
            
            return response
            
        except TickerNotFoundException:
            self._log_operation(
                "get_volatility",
                f"Ticker not found: {ticker}",
                "ERROR"
            )
            raise
        except Exception as e:
            self._log_operation(
                "get_volatility",
                f"Error getting volatility for {ticker}: {str(e)}",
                "ERROR"
            )
            # Attempt to get data from external API as fallback
            try:
                fetched_data = self._fetch_volatility_from_api(ticker)
                response = self._format_volatility_response(fetched_data)
                return response
            except Exception as fallback_error:
                self._log_operation(
                    "get_volatility",
                    f"Fallback failed for {ticker}: {str(fallback_error)}",
                    "ERROR"
                )
                raise e  # Re-raise the original error
    
    def get_volatility_history(
        self, 
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[VolatilityResponse]:
        """
        Get historical volatility data for a stock
        
        Args:
            ticker: Stock symbol
            start_date: Optional start date for the data range
            end_date: Optional end date for the data range
            limit: Optional maximum number of records to return
            
        Returns:
            List[VolatilityResponse]: List of historical volatility data
            
        Raises:
            TickerNotFoundException: If the ticker is not found
            ValidationException: If the ticker is invalid
        """
        # Validate ticker
        ticker = validate_ticker(ticker)
        
        try:
            # Get historical data from database
            with self._get_db_session() as db:
                history_data = volatility.get_historical_by_stock(
                    db, ticker, start_date, end_date, limit
                )
            
            # If no data found, try to fetch from external API
            if not history_data:
                self._log_operation(
                    "get_volatility_history",
                    f"No historical data found for {ticker}, fetching from API",
                    "INFO"
                )
                
                # Fetch from external API and store in database
                try:
                    external_data = get_volatility_history(ticker)
                    
                    # Convert to VolatilityCreate objects
                    volatility_objs = []
                    for item in external_data:
                        obj = VolatilityCreate(
                            stock_id=ticker,
                            vol_index=item['vol_index'],
                            event_risk_factor=item.get('event_risk_factor', 0)
                        )
                        volatility_objs.append(obj)
                    
                    # Store in database
                    with self._get_db_session() as db:
                        history_data = volatility.bulk_create_volatility(db, volatility_objs)
                        
                except ExternalAPIException as e:
                    self._log_operation(
                        "get_volatility_history",
                        f"Failed to fetch historical data for {ticker} from API: {str(e)}",
                        "WARNING"
                    )
                    # Return empty list if no data available
                    return []
            
            # Format response
            response = [self._format_volatility_response(item.to_dict()) for item in history_data]
            
            self._log_operation(
                "get_volatility_history",
                f"Retrieved {len(response)} historical volatility records for {ticker}",
                "INFO"
            )
            
            return response
            
        except Exception as e:
            self._log_operation(
                "get_volatility_history",
                f"Error getting volatility history for {ticker}: {str(e)}",
                "ERROR"
            )
            raise
    
    @cache_result(VOLATILITY_CACHE_TTL)
    def get_market_volatility(self) -> float:
        """
        Get the current market-wide volatility index
        
        Returns:
            float: Current market volatility index value
            
        Raises:
            ExternalAPIException: If the external API is unavailable
        """
        try:
            # Get market volatility from external API
            market_vol_data = get_market_volatility()
            volatility_value = market_vol_data.get('value', 0.0)
            
            self._log_operation(
                "get_market_volatility",
                f"Retrieved market volatility: {volatility_value}",
                "INFO"
            )
            
            return float(volatility_value)
            
        except ExternalAPIException as e:
            self._log_operation(
                "get_market_volatility",
                f"Failed to get market volatility: {str(e)}",
                "ERROR"
            )
            # Return a default value as fallback (e.g., 20 which is a moderate VIX level)
            return 20.0
        except Exception as e:
            self._log_operation(
                "get_market_volatility",
                f"Error getting market volatility: {str(e)}",
                "ERROR"
            )
            # Return a default value as fallback
            return 20.0
    
    @cache_result(EVENT_RISK_CACHE_TTL)
    def get_event_risk(self, ticker: str) -> int:
        """
        Get the event risk factor for a stock
        
        Args:
            ticker: Stock symbol
            
        Returns:
            int: Event risk factor (0-10) based on upcoming events
            
        Raises:
            ValidationException: If the ticker is invalid
        """
        # Validate ticker
        ticker = validate_ticker(ticker)
        
        try:
            # Get event risk from external API
            risk_factor = get_event_risk_factor(ticker)
            
            self._log_operation(
                "get_event_risk",
                f"Retrieved event risk for {ticker}: {risk_factor}",
                "INFO"
            )
            
            return risk_factor
            
        except ExternalAPIException as e:
            self._log_operation(
                "get_event_risk",
                f"Failed to get event risk for {ticker}: {str(e)}",
                "ERROR"
            )
            # Return a default value (0 = no known event risk)
            return 0
        except Exception as e:
            self._log_operation(
                "get_event_risk",
                f"Error getting event risk for {ticker}: {str(e)}",
                "ERROR"
            )
            # Return a default value
            return 0
    
    def update_volatility(
        self,
        ticker: str,
        vol_index: float,
        event_risk_factor: int
    ) -> VolatilityResponse:
        """
        Update volatility data for a stock
        
        Args:
            ticker: Stock symbol
            vol_index: New volatility index value
            event_risk_factor: New event risk factor (0-10)
            
        Returns:
            VolatilityResponse: Updated volatility data
            
        Raises:
            ValidationException: If the input data is invalid
        """
        # Validate ticker
        ticker = validate_ticker(ticker)
        
        # Create update object
        update_data = VolatilityUpdate(
            vol_index=vol_index,
            event_risk_factor=event_risk_factor
        )
        
        try:
            with self._get_db_session() as db:
                # Try to get existing record
                existing_data = volatility.get_latest_by_stock(db, ticker)
                
                if existing_data:
                    # Update existing record
                    updated_data = volatility.update_volatility(db, existing_data, update_data)
                    self._log_operation(
                        "update_volatility",
                        f"Updated volatility for {ticker}: vol_index={vol_index}, event_risk={event_risk_factor}",
                        "INFO"
                    )
                else:
                    # Create new record
                    create_data = VolatilityCreate(
                        stock_id=ticker,
                        vol_index=vol_index,
                        event_risk_factor=event_risk_factor
                    )
                    updated_data = volatility.create_volatility(db, create_data)
                    self._log_operation(
                        "update_volatility",
                        f"Created new volatility for {ticker}: vol_index={vol_index}, event_risk={event_risk_factor}",
                        "INFO"
                    )
            
            # Invalidate cache
            self._invalidate_cache(ticker)
            
            # Format response
            response = self._format_volatility_response(updated_data.to_dict())
            
            return response
            
        except Exception as e:
            self._log_operation(
                "update_volatility",
                f"Error updating volatility for {ticker}: {str(e)}",
                "ERROR"
            )
            raise
    
    def get_stocks_with_high_volatility(
        self,
        threshold: float,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of stocks with volatility above threshold
        
        Args:
            threshold: Minimum volatility index value
            limit: Optional maximum number of records to return
            
        Returns:
            List[Dict[str, Any]]: List of stocks with high volatility
        """
        try:
            with self._get_db_session() as db:
                # Import needed here to avoid circular imports
                from sqlalchemy import select, desc
                from ...db.models.volatility import Volatility
                
                # Create a query that filters by vol_index and orders by vol_index descending
                query = select(Volatility).where(Volatility.vol_index >= threshold).order_by(desc(Volatility.vol_index))
                
                # Apply limit if provided
                if limit:
                    query = query.limit(limit)
                
                # Execute query
                result = db.execute(query).scalars().all()
                
                # Convert to dictionary format
                stocks_data = []
                for record in result:
                    stocks_data.append({
                        "ticker": record.stock_id,
                        "vol_index": float(record.vol_index),
                        "event_risk_factor": record.event_risk_factor,
                        "timestamp": record.timestamp.isoformat() if record.timestamp else None
                    })
                
                self._log_operation(
                    "get_stocks_with_high_volatility",
                    f"Found {len(stocks_data)} stocks with volatility above {threshold}",
                    "INFO"
                )
                
                return stocks_data
                
        except Exception as e:
            self._log_operation(
                "get_stocks_with_high_volatility",
                f"Error getting stocks with high volatility: {str(e)}",
                "ERROR"
            )
            raise
    
    def get_stocks_with_high_event_risk(
        self,
        threshold: int,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of stocks with event risk above threshold
        
        Args:
            threshold: Minimum event risk factor (0-10)
            limit: Optional maximum number of records to return
            
        Returns:
            List[Dict[str, Any]]: List of stocks with high event risk
        """
        try:
            with self._get_db_session() as db:
                # Import needed here to avoid circular imports
                from sqlalchemy import select, desc
                from ...db.models.volatility import Volatility
                
                # Create a query that filters by event_risk_factor and orders by event_risk_factor descending
                query = select(Volatility).where(Volatility.event_risk_factor >= threshold).order_by(desc(Volatility.event_risk_factor))
                
                # Apply limit if provided
                if limit:
                    query = query.limit(limit)
                
                # Execute query
                result = db.execute(query).scalars().all()
                
                # Convert to dictionary format
                stocks_data = []
                for record in result:
                    stocks_data.append({
                        "ticker": record.stock_id,
                        "vol_index": float(record.vol_index),
                        "event_risk_factor": record.event_risk_factor,
                        "timestamp": record.timestamp.isoformat() if record.timestamp else None
                    })
                
                self._log_operation(
                    "get_stocks_with_high_event_risk",
                    f"Found {len(stocks_data)} stocks with event risk above {threshold}",
                    "INFO"
                )
                
                return stocks_data
                
        except Exception as e:
            self._log_operation(
                "get_stocks_with_high_event_risk",
                f"Error getting stocks with high event risk: {str(e)}",
                "ERROR"
            )
            raise
    
    def get_volatility_stats(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get volatility statistics for a stock over time period
        
        Args:
            ticker: Stock symbol
            start_date: Optional start date for the data range
            end_date: Optional end date for the data range
            
        Returns:
            Dict[str, Any]: Volatility statistics including average, max, min
            
        Raises:
            TickerNotFoundException: If the ticker is not found
            ValidationException: If the ticker is invalid
        """
        # Validate ticker
        ticker = validate_ticker(ticker)
        
        try:
            with self._get_db_session() as db:
                # Get average volatility
                avg_volatility = volatility.get_average_volatility(db, ticker, start_date, end_date)
                
                # Get maximum event risk
                max_event_risk = volatility.get_max_event_risk(db, ticker, start_date, end_date)
                
                # Build response
                stats = {
                    "ticker": ticker,
                    "average_volatility": float(avg_volatility) if avg_volatility else None,
                    "max_event_risk": max_event_risk if max_event_risk else None,
                    "period_start": start_date.isoformat() if start_date else None,
                    "period_end": end_date.isoformat() if end_date else None
                }
                
                self._log_operation(
                    "get_volatility_stats",
                    f"Retrieved volatility stats for {ticker}: avg={stats['average_volatility']}, max_risk={stats['max_event_risk']}",
                    "INFO"
                )
                
                return stats
                
        except Exception as e:
            self._log_operation(
                "get_volatility_stats",
                f"Error getting volatility stats for {ticker}: {str(e)}",
                "ERROR"
            )
            raise
    
    def refresh_volatility_data(self, ticker: str) -> VolatilityResponse:
        """
        Refresh volatility data for a stock from external APIs
        
        Args:
            ticker: Stock symbol
            
        Returns:
            VolatilityResponse: Refreshed volatility data
            
        Raises:
            ValidationException: If the ticker is invalid
            ExternalAPIException: If the external APIs are unavailable
        """
        # Validate ticker
        ticker = validate_ticker(ticker)
        
        try:
            # Fetch volatility data from external API
            volatility_data = get_stock_volatility(ticker)
            vol_index = float(volatility_data.get('volatility', 0.0))
            
            # Fetch event risk data
            event_risk = get_event_risk_factor(ticker)
            
            # Update database
            update_data = self.update_volatility(ticker, vol_index, event_risk)
            
            # Invalidate cache
            self._invalidate_cache(ticker)
            
            self._log_operation(
                "refresh_volatility_data",
                f"Refreshed volatility data for {ticker}: vol_index={vol_index}, event_risk={event_risk}",
                "INFO"
            )
            
            return update_data
            
        except ExternalAPIException as e:
            self._log_operation(
                "refresh_volatility_data",
                f"External API error refreshing volatility for {ticker}: {str(e)}",
                "ERROR"
            )
            # Handle using the external API error handler from the base class
            self._handle_external_api_error(e, "Volatility API", f"refresh volatility for {ticker}")
        except Exception as e:
            self._log_operation(
                "refresh_volatility_data",
                f"Error refreshing volatility for {ticker}: {str(e)}",
                "ERROR"
            )
            raise
    
    def _fetch_volatility_from_api(self, ticker: str) -> Dict[str, Any]:
        """
        Private method to fetch volatility data from external API
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Dict[str, Any]: Volatility data from external API
            
        Raises:
            ExternalAPIException: If the external API is unavailable
        """
        try:
            # Get stock volatility from external API
            volatility_data = get_stock_volatility(ticker)
            vol_index = float(volatility_data.get('volatility', 0.0))
            
            # Get event risk from external API
            event_risk = get_event_risk_factor(ticker)
            
            result = {
                'stock_id': ticker,
                'vol_index': vol_index,
                'event_risk_factor': event_risk,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self._log_operation(
                "_fetch_volatility_from_api",
                f"Fetched volatility data from API for {ticker}: vol_index={vol_index}, event_risk={event_risk}",
                "DEBUG"
            )
            
            return result
            
        except ExternalAPIException as e:
            self._log_operation(
                "_fetch_volatility_from_api",
                f"External API error fetching volatility for {ticker}: {str(e)}",
                "ERROR"
            )
            # Handle using the external API error handler from the base class
            self._handle_external_api_error(e, "Volatility API", f"fetch volatility data for {ticker}")
    
    def _format_volatility_response(self, volatility_data: Dict[str, Any]) -> VolatilityResponse:
        """
        Private method to format volatility data into response schema
        
        Args:
            volatility_data: Dictionary containing volatility data
            
        Returns:
            VolatilityResponse: Formatted volatility response
        """
        # Determine volatility tier based on vol_index
        vol_index = float(volatility_data.get('vol_index', 0.0))
        
        if vol_index < 15:
            volatility_tier = "LOW"
        elif vol_index < 25:
            volatility_tier = "MEDIUM"
        elif vol_index < 35:
            volatility_tier = "HIGH"
        else:
            volatility_tier = "EXTREME"
        
        # Create response object
        response = VolatilityResponse(
            stock_id=volatility_data.get('stock_id'),
            vol_index=vol_index,
            event_risk_factor=volatility_data.get('event_risk_factor', 0),
            timestamp=volatility_data.get('timestamp', datetime.utcnow()),
            volatility_tier=volatility_tier
        )
        
        return response
    
    def _invalidate_cache(self, ticker: str) -> None:
        """
        Private method to invalidate cache for a ticker
        
        Args:
            ticker: Stock symbol
        """
        # Generate cache keys
        volatility_key = f"volatility:{ticker}"
        event_risk_key = f"event_risk:{ticker}"
        
        # Delete keys from cache
        redis_cache.delete(volatility_key)
        redis_cache.delete(event_risk_key)
        
        self._log_operation(
            "_invalidate_cache",
            f"Invalidated cache for ticker {ticker}",
            "DEBUG"
        )


# Create a singleton instance of the service
volatility_service = VolatilityService()