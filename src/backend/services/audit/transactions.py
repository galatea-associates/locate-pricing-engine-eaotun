"""
Implements transaction auditing and analysis functionality for the Borrow Rate & Locate Fee Pricing Engine.

This module provides methods for recording, retrieving, analyzing, and reporting on
fee calculation transactions to support regulatory compliance, business intelligence,
and troubleshooting.
"""

import logging
import datetime
import uuid
from decimal import Decimal
from typing import List, Dict, Optional, Any, Union, Tuple

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from ...db.crud.audit import audit
from ...schemas.audit import (
    AuditLogSchema,
    AuditLogFilterSchema, 
    AuditLogResponseSchema
)
from .utils import (
    format_decimal_for_audit,
    has_fallback_source,
    get_data_source_names
)
from ...core.logging import get_audit_logger

# Set up module logger
logger = logging.getLogger(__name__)


def calculate_fee_statistics(audit_logs: List[AuditLogSchema]) -> Dict[str, Any]:
    """
    Calculate statistical metrics for fee calculations over a specified period.
    
    Args:
        audit_logs: List of audit logs to analyze
        
    Returns:
        Dictionary of statistical metrics including averages, medians, and percentiles
    """
    if not audit_logs:
        return {
            "count": 0,
            "average_borrow_rate": Decimal('0'),
            "average_total_fee": Decimal('0'),
            "total_volume": Decimal('0'),
        }
    
    # Convert to pandas DataFrame for statistical analysis
    df = pd.DataFrame([
        {
            "borrow_rate": log.borrow_rate_used,
            "total_fee": log.total_fee,
            "position_value": log.position_value,
            "timestamp": log.timestamp
        }
        for log in audit_logs
    ])
    
    # Calculate statistics
    stats = {
        "count": len(audit_logs),
        "average_borrow_rate": format_decimal_for_audit(df["borrow_rate"].mean()),
        "median_borrow_rate": format_decimal_for_audit(df["borrow_rate"].median()),
        "average_total_fee": format_decimal_for_audit(df["total_fee"].mean()),
        "median_total_fee": format_decimal_for_audit(df["total_fee"].median()),
        "total_volume": format_decimal_for_audit(df["position_value"].sum()),
        "borrow_rate_percentiles": {
            "25th": format_decimal_for_audit(df["borrow_rate"].quantile(0.25)),
            "75th": format_decimal_for_audit(df["borrow_rate"].quantile(0.75)),
            "90th": format_decimal_for_audit(df["borrow_rate"].quantile(0.9))
        },
        "fee_percentiles": {
            "25th": format_decimal_for_audit(df["total_fee"].quantile(0.25)),
            "75th": format_decimal_for_audit(df["total_fee"].quantile(0.75)),
            "90th": format_decimal_for_audit(df["total_fee"].quantile(0.9))
        }
    }
    
    return stats


def analyze_fallback_usage(audit_logs: List[AuditLogSchema]) -> Dict[str, Any]:
    """
    Analyze patterns of fallback mechanism usage in audit logs.
    
    Args:
        audit_logs: List of audit logs to analyze
        
    Returns:
        Analysis of fallback usage including frequency and impact
    """
    if not audit_logs:
        return {
            "fallback_count": 0,
            "fallback_percentage": Decimal('0'),
            "common_fallback_sources": []
        }
    
    # Filter logs with fallback usage
    fallback_logs = [log for log in audit_logs if has_fallback_source(log.data_sources)]
    fallback_count = len(fallback_logs)
    total_count = len(audit_logs)
    
    if fallback_count == 0:
        return {
            "fallback_count": 0,
            "fallback_percentage": Decimal('0'),
            "common_fallback_sources": []
        }
    
    # Calculate statistics
    fallback_percentage = format_decimal_for_audit(Decimal(fallback_count) / Decimal(total_count) * 100)
    
    # Identify common fallback sources
    fallback_sources = {}
    for log in fallback_logs:
        for source_name, source_data in log.data_sources.items():
            if isinstance(source_data, dict) and source_data.get("is_fallback", False):
                fallback_sources[source_name] = fallback_sources.get(source_name, 0) + 1
    
    # Sort sources by frequency
    common_sources = sorted(
        [{"source": k, "count": v} for k, v in fallback_sources.items()],
        key=lambda x: x["count"],
        reverse=True
    )
    
    # Group fallbacks by ticker
    ticker_fallbacks = {}
    for log in fallback_logs:
        ticker = log.ticker
        ticker_fallbacks[ticker] = ticker_fallbacks.get(ticker, 0) + 1
    
    # Sort tickers by fallback frequency
    problematic_tickers = sorted(
        [{"ticker": k, "count": v} for k, v in ticker_fallbacks.items()],
        key=lambda x: x["count"],
        reverse=True
    )[:10]  # Top 10 tickers
    
    # Calculate rate difference when fallbacks are used
    if fallback_logs and len(audit_logs) > fallback_count:
        normal_rates = [log.borrow_rate_used for log in audit_logs if not has_fallback_source(log.data_sources)]
        fallback_rates = [log.borrow_rate_used for log in fallback_logs]
        
        avg_normal_rate = sum(normal_rates) / len(normal_rates)
        avg_fallback_rate = sum(fallback_rates) / len(fallback_rates)
        rate_difference = format_decimal_for_audit(avg_fallback_rate - avg_normal_rate)
    else:
        rate_difference = None
    
    return {
        "fallback_count": fallback_count,
        "fallback_percentage": fallback_percentage,
        "common_fallback_sources": common_sources[:5],  # Top 5 sources
        "problematic_tickers": problematic_tickers,
        "rate_difference": rate_difference
    }


def generate_daily_report_data(db: Session, report_date: datetime.date) -> Dict[str, Any]:
    """
    Generate data for daily transaction report.
    
    Args:
        db: Database session
        report_date: Date for which to generate the report
        
    Returns:
        Report data including transaction counts, volumes, and statistics
    """
    # Calculate start and end datetime for the date
    start_datetime = datetime.datetime.combine(report_date, datetime.time.min)
    end_datetime = datetime.datetime.combine(report_date, datetime.time.max)
    
    # Retrieve audit logs for the date
    audit_logs = audit.get_audit_logs_by_date_range(db, start_datetime, end_datetime)
    
    if not audit_logs:
        return {
            "date": report_date.isoformat(),
            "transaction_count": 0,
            "transaction_volume": Decimal('0'),
            "statistics": {
                "count": 0,
                "average_borrow_rate": Decimal('0'),
                "average_total_fee": Decimal('0'),
                "total_volume": Decimal('0'),
            },
            "fallback_analysis": {
                "fallback_count": 0,
                "fallback_percentage": Decimal('0'),
                "common_fallback_sources": []
            },
            "top_clients": [],
            "top_tickers": []
        }
    
    # Convert to schemas for analysis
    audit_log_schemas = [log.to_schema() for log in audit_logs]
    
    # Calculate fee statistics
    statistics = calculate_fee_statistics(audit_log_schemas)
    
    # Analyze fallback usage
    fallback_analysis = analyze_fallback_usage(audit_log_schemas)
    
    # Group by client
    client_data = {}
    for log in audit_log_schemas:
        client_id = log.client_id
        client_data[client_id] = client_data.get(client_id, {})
        client_data[client_id]["count"] = client_data[client_id].get("count", 0) + 1
        client_data[client_id]["volume"] = client_data[client_id].get("volume", Decimal('0')) + log.position_value
    
    # Calculate top clients by volume
    top_clients = sorted(
        [{"client_id": k, "count": v["count"], "volume": v["volume"]} for k, v in client_data.items()],
        key=lambda x: x["volume"],
        reverse=True
    )[:10]  # Top 10 clients
    
    # Group by ticker
    ticker_data = {}
    for log in audit_log_schemas:
        ticker = log.ticker
        ticker_data[ticker] = ticker_data.get(ticker, {})
        ticker_data[ticker]["count"] = ticker_data[ticker].get("count", 0) + 1
        ticker_data[ticker]["volume"] = ticker_data[ticker].get("volume", Decimal('0')) + log.position_value
    
    # Calculate top tickers by volume
    top_tickers = sorted(
        [{"ticker": k, "count": v["count"], "volume": v["volume"]} for k, v in ticker_data.items()],
        key=lambda x: x["volume"],
        reverse=True
    )[:10]  # Top 10 tickers
    
    # Compile report data
    report_data = {
        "date": report_date.isoformat(),
        "transaction_count": len(audit_log_schemas),
        "transaction_volume": statistics["total_volume"],
        "statistics": statistics,
        "fallback_analysis": fallback_analysis,
        "client_breakdown": client_data,
        "ticker_breakdown": ticker_data,
        "top_clients": top_clients,
        "top_tickers": top_tickers
    }
    
    return report_data


def generate_monthly_report_data(db: Session, year: int, month: int) -> Dict[str, Any]:
    """
    Generate data for monthly transaction report.
    
    Args:
        db: Database session
        year: Year for the report
        month: Month for the report
        
    Returns:
        Report data including monthly transaction counts, volumes, and statistics
    """
    # Calculate start and end datetime for the month
    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
    
    start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
    end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
    
    # Retrieve audit logs for the month
    audit_logs = audit.get_audit_logs_by_date_range(db, start_datetime, end_datetime)
    
    if not audit_logs:
        return {
            "year": year,
            "month": month,
            "transaction_count": 0,
            "transaction_volume": Decimal('0'),
            "statistics": {
                "count": 0,
                "average_borrow_rate": Decimal('0'),
                "average_total_fee": Decimal('0'),
                "total_volume": Decimal('0'),
            },
            "fallback_analysis": {
                "fallback_count": 0,
                "fallback_percentage": Decimal('0'),
                "common_fallback_sources": []
            },
            "daily_trend": [],
            "top_clients": [],
            "top_tickers": []
        }
    
    # Convert to schemas for analysis
    audit_log_schemas = [log.to_schema() for log in audit_logs]
    
    # Calculate fee statistics
    statistics = calculate_fee_statistics(audit_log_schemas)
    
    # Analyze fallback usage
    fallback_analysis = analyze_fallback_usage(audit_log_schemas)
    
    # Group by client
    client_data = {}
    for log in audit_log_schemas:
        client_id = log.client_id
        client_data[client_id] = client_data.get(client_id, {})
        client_data[client_id]["count"] = client_data[client_id].get("count", 0) + 1
        client_data[client_id]["volume"] = client_data[client_id].get("volume", Decimal('0')) + log.position_value
    
    # Calculate top clients by volume
    top_clients = sorted(
        [{"client_id": k, "count": v["count"], "volume": v["volume"]} for k, v in client_data.items()],
        key=lambda x: x["volume"],
        reverse=True
    )[:10]  # Top 10 clients
    
    # Group by ticker
    ticker_data = {}
    for log in audit_log_schemas:
        ticker = log.ticker
        ticker_data[ticker] = ticker_data.get(ticker, {})
        ticker_data[ticker]["count"] = ticker_data[ticker].get("count", 0) + 1
        ticker_data[ticker]["volume"] = ticker_data[ticker].get("volume", Decimal('0')) + log.position_value
    
    # Calculate top tickers by volume
    top_tickers = sorted(
        [{"ticker": k, "count": v["count"], "volume": v["volume"]} for k, v in ticker_data.items()],
        key=lambda x: x["volume"],
        reverse=True
    )[:10]  # Top 10 tickers
    
    # Group by day for trend analysis
    daily_trend = []
    day_data = {}
    for log in audit_log_schemas:
        day = log.timestamp.date().isoformat()
        if day not in day_data:
            day_data[day] = {
                "date": day,
                "count": 0,
                "volume": Decimal('0'),
                "average_rate": [],
                "average_fee": []
            }
        
        day_data[day]["count"] += 1
        day_data[day]["volume"] += log.position_value
        day_data[day]["average_rate"].append(log.borrow_rate_used)
        day_data[day]["average_fee"].append(log.total_fee)
    
    # Calculate daily averages
    for day, data in day_data.items():
        data["average_rate"] = format_decimal_for_audit(sum(data["average_rate"]) / len(data["average_rate"]))
        data["average_fee"] = format_decimal_for_audit(sum(data["average_fee"]) / len(data["average_fee"]))
        daily_trend.append(data)
    
    # Sort by date
    daily_trend.sort(key=lambda x: x["date"])
    
    # Compile report data
    report_data = {
        "year": year,
        "month": month,
        "transaction_count": len(audit_log_schemas),
        "transaction_volume": statistics["total_volume"],
        "statistics": statistics,
        "fallback_analysis": fallback_analysis,
        "client_breakdown": client_data,
        "ticker_breakdown": ticker_data,
        "daily_trend": daily_trend,
        "top_clients": top_clients,
        "top_tickers": top_tickers
    }
    
    return report_data


def compare_report_data(current_report: Dict[str, Any], previous_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare two report datasets to identify trends and changes.
    
    Args:
        current_report: Current period report data
        previous_report: Previous period report data
        
    Returns:
        Comparison data with percentage changes and trend indicators
    """
    if not previous_report or not current_report:
        return {
            "error": "Cannot compare reports: one or both reports are empty",
            "has_previous_data": bool(previous_report),
            "has_current_data": bool(current_report)
        }
    
    comparison = {}
    
    # Calculate percentage changes for key metrics
    if previous_report["transaction_count"] > 0:
        count_change = ((current_report["transaction_count"] - previous_report["transaction_count"]) / 
                        previous_report["transaction_count"]) * 100
        comparison["transaction_count_change"] = format_decimal_for_audit(Decimal(count_change))
    else:
        comparison["transaction_count_change"] = None
    
    if previous_report["transaction_volume"] > 0:
        volume_change = ((current_report["transaction_volume"] - previous_report["transaction_volume"]) / 
                         previous_report["transaction_volume"]) * 100
        comparison["transaction_volume_change"] = format_decimal_for_audit(Decimal(volume_change))
    else:
        comparison["transaction_volume_change"] = None
    
    # Compare statistics
    stats_comparison = {}
    
    if (previous_report["statistics"]["average_borrow_rate"] > 0 and 
        current_report["statistics"]["average_borrow_rate"] > 0):
        rate_change = ((current_report["statistics"]["average_borrow_rate"] - 
                         previous_report["statistics"]["average_borrow_rate"]) / 
                        previous_report["statistics"]["average_borrow_rate"]) * 100
        stats_comparison["average_borrow_rate_change"] = format_decimal_for_audit(Decimal(rate_change))
    else:
        stats_comparison["average_borrow_rate_change"] = None
    
    if (previous_report["statistics"]["average_total_fee"] > 0 and 
        current_report["statistics"]["average_total_fee"] > 0):
        fee_change = ((current_report["statistics"]["average_total_fee"] - 
                        previous_report["statistics"]["average_total_fee"]) / 
                       previous_report["statistics"]["average_total_fee"]) * 100
        stats_comparison["average_total_fee_change"] = format_decimal_for_audit(Decimal(fee_change))
    else:
        stats_comparison["average_total_fee_change"] = None
    
    comparison["statistics_comparison"] = stats_comparison
    
    # Compare fallback usage
    fallback_comparison = {}
    
    if (previous_report["fallback_analysis"]["fallback_percentage"] > 0 and 
        current_report["fallback_analysis"]["fallback_percentage"] > 0):
        fallback_change = ((current_report["fallback_analysis"]["fallback_percentage"] - 
                             previous_report["fallback_analysis"]["fallback_percentage"]) / 
                            previous_report["fallback_analysis"]["fallback_percentage"]) * 100
        fallback_comparison["fallback_percentage_change"] = format_decimal_for_audit(Decimal(fallback_change))
    else:
        fallback_comparison["fallback_percentage_change"] = None
    
    comparison["fallback_comparison"] = fallback_comparison
    
    # Identify new top clients and tickers
    new_top_clients = []
    for client in current_report["top_clients"]:
        client_id = client["client_id"]
        if not any(prev_client["client_id"] == client_id for prev_client in previous_report["top_clients"]):
            new_top_clients.append(client)
    
    new_top_tickers = []
    for ticker in current_report["top_tickers"]:
        ticker_symbol = ticker["ticker"]
        if not any(prev_ticker["ticker"] == ticker_symbol for prev_ticker in previous_report["top_tickers"]):
            new_top_tickers.append(ticker)
    
    comparison["new_top_clients"] = new_top_clients
    comparison["new_top_tickers"] = new_top_tickers
    
    # Identify significant changes in client and ticker activity
    significant_client_changes = []
    for current_client in current_report["top_clients"]:
        client_id = current_client["client_id"]
        prev_client = next((c for c in previous_report["top_clients"] if c["client_id"] == client_id), None)
        
        if prev_client and prev_client["volume"] > 0:
            volume_change = ((current_client["volume"] - prev_client["volume"]) / prev_client["volume"]) * 100
            if abs(volume_change) > 20:  # 20% threshold for significant change
                significant_client_changes.append({
                    "client_id": client_id,
                    "previous_volume": prev_client["volume"],
                    "current_volume": current_client["volume"],
                    "volume_change_percentage": format_decimal_for_audit(Decimal(volume_change))
                })
    
    significant_ticker_changes = []
    for current_ticker in current_report["top_tickers"]:
        ticker_symbol = current_ticker["ticker"]
        prev_ticker = next((t for t in previous_report["top_tickers"] if t["ticker"] == ticker_symbol), None)
        
        if prev_ticker and prev_ticker["volume"] > 0:
            volume_change = ((current_ticker["volume"] - prev_ticker["volume"]) / prev_ticker["volume"]) * 100
            if abs(volume_change) > 20:  # 20% threshold for significant change
                significant_ticker_changes.append({
                    "ticker": ticker_symbol,
                    "previous_volume": prev_ticker["volume"],
                    "current_volume": current_ticker["volume"],
                    "volume_change_percentage": format_decimal_for_audit(Decimal(volume_change))
                })
    
    comparison["significant_client_changes"] = significant_client_changes
    comparison["significant_ticker_changes"] = significant_ticker_changes
    
    return comparison


class TransactionAuditor:
    """Service for auditing, analyzing, and reporting on fee calculation transactions."""
    
    def __init__(self, db: Session):
        """
        Initialize the transaction auditor with a database session.
        
        Args:
            db: Database session for querying audit logs
        """
        self._db = db
        self._logger = get_audit_logger()
        self._logger.info("TransactionAuditor service initialized")
    
    def record_transaction(self, audit_log: AuditLogSchema) -> None:
        """
        Record a transaction in the audit log for later analysis.
        
        Args:
            audit_log: Audit log data to record
        """
        # The actual database insertion is handled by the AuditLogger component
        # This method is for additional analytics processing or validation
        self._logger.info(
            f"Transaction recorded: {audit_log.ticker} for {audit_log.client_id} - "
            f"Position: {audit_log.position_value} - Rate: {audit_log.borrow_rate_used} - "
            f"Fee: {audit_log.total_fee}"
        )
    
    def get_client_transactions(self, client_id: str, start_date: Optional[datetime.date] = None,
                               end_date: Optional[datetime.date] = None, skip: Optional[int] = None,
                               limit: Optional[int] = None) -> List[AuditLogSchema]:
        """
        Get all transactions for a specific client with optional date filtering.
        
        Args:
            client_id: Client identifier
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of audit logs for the client
        """
        # Get transactions by client ID
        transactions = audit.get_audit_logs_by_client(self._db, client_id, skip, limit)
        
        # Apply date filtering if provided
        if start_date or end_date:
            filtered_transactions = []
            for transaction in transactions:
                transaction_date = transaction.timestamp.date()
                
                # Check start date
                if start_date and transaction_date < start_date:
                    continue
                
                # Check end date
                if end_date and transaction_date > end_date:
                    continue
                
                filtered_transactions.append(transaction)
            
            return [transaction.to_schema() for transaction in filtered_transactions]
        
        return [transaction.to_schema() for transaction in transactions]
    
    def get_ticker_transactions(self, ticker: str, start_date: Optional[datetime.date] = None,
                              end_date: Optional[datetime.date] = None, skip: Optional[int] = None,
                              limit: Optional[int] = None) -> List[AuditLogSchema]:
        """
        Get all transactions for a specific ticker with optional date filtering.
        
        Args:
            ticker: Stock symbol
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of audit logs for the ticker
        """
        # Get transactions by ticker
        transactions = audit.get_audit_logs_by_ticker(self._db, ticker, skip, limit)
        
        # Apply date filtering if provided
        if start_date or end_date:
            filtered_transactions = []
            for transaction in transactions:
                transaction_date = transaction.timestamp.date()
                
                # Check start date
                if start_date and transaction_date < start_date:
                    continue
                
                # Check end date
                if end_date and transaction_date > end_date:
                    continue
                
                filtered_transactions.append(transaction)
            
            return [transaction.to_schema() for transaction in filtered_transactions]
        
        return [transaction.to_schema() for transaction in transactions]
    
    def get_fallback_transactions(self, start_date: Optional[datetime.date] = None,
                                end_date: Optional[datetime.date] = None, skip: Optional[int] = None,
                                limit: Optional[int] = None) -> List[AuditLogSchema]:
        """
        Get all transactions where fallback mechanisms were used.
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of audit logs with fallback usage
        """
        # Get transactions with fallback
        transactions = audit.get_audit_logs_with_fallback(self._db, skip, limit)
        
        # Apply date filtering if provided
        if start_date or end_date:
            filtered_transactions = []
            for transaction in transactions:
                transaction_date = transaction.timestamp.date()
                
                # Check start date
                if start_date and transaction_date < start_date:
                    continue
                
                # Check end date
                if end_date and transaction_date > end_date:
                    continue
                
                filtered_transactions.append(transaction)
            
            return [transaction.to_schema() for transaction in filtered_transactions]
        
        return [transaction.to_schema() for transaction in transactions]
    
    def get_transaction_by_id(self, audit_id: Union[str, uuid.UUID]) -> Optional[AuditLogSchema]:
        """
        Get a specific transaction by its audit ID.
        
        Args:
            audit_id: Unique identifier for the audit log
            
        Returns:
            Found audit log or None
        """
        # Convert string to UUID if necessary
        if isinstance(audit_id, str):
            try:
                audit_id = uuid.UUID(audit_id)
            except ValueError:
                self._logger.warning(f"Invalid UUID format: {audit_id}")
                return None
        
        # Query the database
        transaction = audit.get_audit_log(self._db, audit_id)
        
        if transaction:
            return transaction.to_schema()
        
        self._logger.warning(f"Transaction not found with ID: {audit_id}")
        return None
    
    def filter_transactions(self, filters: AuditLogFilterSchema) -> AuditLogResponseSchema:
        """
        Filter transactions based on various criteria.
        
        Args:
            filters: Filter criteria for audit logs
            
        Returns:
            Filtered and paginated audit logs
        """
        return audit.filter_audit_logs(self._db, filters)
    
    def generate_daily_report(self, report_date: Optional[datetime.date] = None) -> Dict[str, Any]:
        """
        Generate a daily report of transaction activity.
        
        Args:
            report_date: Date for the report (defaults to current date)
            
        Returns:
            Daily report data
        """
        if report_date is None:
            report_date = datetime.date.today()
        
        report_data = generate_daily_report_data(self._db, report_date)
        
        self._logger.info(
            f"Generated daily report for {report_date.isoformat()} - "
            f"Transactions: {report_data['transaction_count']} - "
            f"Volume: {report_data['transaction_volume']}"
        )
        
        return report_data
    
    def generate_monthly_report(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate a monthly report of transaction activity.
        
        Args:
            year: Year for the report (defaults to current year)
            month: Month for the report (defaults to current month)
            
        Returns:
            Monthly report data
        """
        today = datetime.date.today()
        
        if year is None:
            year = today.year
            
        if month is None:
            month = today.month
        
        report_data = generate_monthly_report_data(self._db, year, month)
        
        self._logger.info(
            f"Generated monthly report for {year}-{month:02d} - "
            f"Transactions: {report_data['transaction_count']} - "
            f"Volume: {report_data['transaction_volume']}"
        )
        
        return report_data
    
    def compare_daily_reports(self, current_date: datetime.date,
                           previous_date: datetime.date) -> Dict[str, Any]:
        """
        Compare two daily reports to identify trends.
        
        Args:
            current_date: Date of the current report
            previous_date: Date of the previous report
            
        Returns:
            Comparison data between the two daily reports
        """
        current_report = generate_daily_report_data(self._db, current_date)
        previous_report = generate_daily_report_data(self._db, previous_date)
        
        comparison = compare_report_data(current_report, previous_report)
        
        self._logger.info(
            f"Compared daily reports: {previous_date.isoformat()} vs {current_date.isoformat()} - "
            f"Transaction count change: {comparison.get('transaction_count_change')}%"
        )
        
        return comparison
    
    def compare_monthly_reports(self, current_year: int, current_month: int,
                             previous_year: int, previous_month: int) -> Dict[str, Any]:
        """
        Compare two monthly reports to identify trends.
        
        Args:
            current_year: Year of the current report
            current_month: Month of the current report
            previous_year: Year of the previous report
            previous_month: Month of the previous report
            
        Returns:
            Comparison data between the two monthly reports
        """
        current_report = generate_monthly_report_data(self._db, current_year, current_month)
        previous_report = generate_monthly_report_data(self._db, previous_year, previous_month)
        
        comparison = compare_report_data(current_report, previous_report)
        
        self._logger.info(
            f"Compared monthly reports: {previous_year}-{previous_month:02d} vs {current_year}-{current_month:02d} - "
            f"Transaction count change: {comparison.get('transaction_count_change')}%"
        )
        
        return comparison
    
    def analyze_client_activity(self, client_id: str, start_date: Optional[datetime.date] = None,
                              end_date: Optional[datetime.date] = None) -> Dict[str, Any]:
        """
        Analyze transaction patterns for a specific client.
        
        Args:
            client_id: Client identifier
            start_date: Start date for analysis period
            end_date: End date for analysis period
            
        Returns:
            Analysis of client transaction patterns
        """
        # Get client transactions
        transactions = self.get_client_transactions(client_id, start_date, end_date)
        
        if not transactions:
            return {
                "client_id": client_id,
                "transaction_count": 0,
                "transaction_volume": Decimal('0'),
                "has_activity": False
            }
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame([
            {
                "ticker": t.ticker,
                "timestamp": t.timestamp,
                "position_value": t.position_value,
                "loan_days": t.loan_days,
                "borrow_rate": t.borrow_rate_used,
                "total_fee": t.total_fee,
                "day_of_week": t.timestamp.strftime("%A"),
                "hour_of_day": t.timestamp.hour
            }
            for t in transactions
        ])
        
        # Calculate overall metrics
        transaction_count = len(transactions)
        transaction_volume = format_decimal_for_audit(sum(t.position_value for t in transactions))
        avg_transaction_size = format_decimal_for_audit(transaction_volume / transaction_count)
        avg_borrow_rate = format_decimal_for_audit(sum(t.borrow_rate_used for t in transactions) / transaction_count)
        
        # Identify frequently traded tickers
        ticker_counts = df["ticker"].value_counts().to_dict()
        ticker_volumes = df.groupby("ticker")["position_value"].sum().to_dict()
        ticker_rates = df.groupby("ticker")["borrow_rate"].mean().to_dict()
        
        top_tickers = [
            {
                "ticker": ticker,
                "count": count,
                "volume": format_decimal_for_audit(ticker_volumes.get(ticker, Decimal('0'))),
                "average_rate": format_decimal_for_audit(ticker_rates.get(ticker, Decimal('0')))
            }
            for ticker, count in sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)
        ][:10]  # Top 10 tickers
        
        # Analyze time patterns
        day_distribution = df["day_of_week"].value_counts().to_dict()
        hour_distribution = df["hour_of_day"].value_counts().to_dict()
        
        # Calculate loan duration patterns
        loan_days_avg = format_decimal_for_audit(df["loan_days"].mean())
        loan_days_median = int(df["loan_days"].median())
        loan_days_distribution = df["loan_days"].value_counts().to_dict()
        
        # Compile analysis
        analysis = {
            "client_id": client_id,
            "transaction_count": transaction_count,
            "transaction_volume": transaction_volume,
            "has_activity": True,
            "average_transaction_size": avg_transaction_size,
            "average_borrow_rate": avg_borrow_rate,
            "top_tickers": top_tickers,
            "time_patterns": {
                "day_distribution": day_distribution,
                "hour_distribution": hour_distribution
            },
            "loan_duration": {
                "average_days": loan_days_avg,
                "median_days": loan_days_median,
                "distribution": loan_days_distribution
            }
        }
        
        return analysis
    
    def analyze_ticker_activity(self, ticker: str, start_date: Optional[datetime.date] = None,
                              end_date: Optional[datetime.date] = None) -> Dict[str, Any]:
        """
        Analyze transaction patterns for a specific ticker.
        
        Args:
            ticker: Stock symbol
            start_date: Start date for analysis period
            end_date: End date for analysis period
            
        Returns:
            Analysis of ticker transaction patterns
        """
        # Get ticker transactions
        transactions = self.get_ticker_transactions(ticker, start_date, end_date)
        
        if not transactions:
            return {
                "ticker": ticker,
                "transaction_count": 0,
                "transaction_volume": Decimal('0'),
                "has_activity": False
            }
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame([
            {
                "client_id": t.client_id,
                "timestamp": t.timestamp,
                "position_value": t.position_value,
                "loan_days": t.loan_days,
                "borrow_rate": t.borrow_rate_used,
                "total_fee": t.total_fee,
                "date": t.timestamp.date(),
                "has_fallback": has_fallback_source(t.data_sources)
            }
            for t in transactions
        ])
        
        # Calculate overall metrics
        transaction_count = len(transactions)
        transaction_volume = format_decimal_for_audit(sum(t.position_value for t in transactions))
        avg_transaction_size = format_decimal_for_audit(transaction_volume / transaction_count)
        avg_borrow_rate = format_decimal_for_audit(sum(t.borrow_rate_used for t in transactions) / transaction_count)
        
        # Identify clients trading this ticker
        client_counts = df["client_id"].value_counts().to_dict()
        client_volumes = df.groupby("client_id")["position_value"].sum().to_dict()
        
        top_clients = [
            {
                "client_id": client_id,
                "count": count,
                "volume": format_decimal_for_audit(client_volumes.get(client_id, Decimal('0')))
            }
            for client_id, count in sorted(client_counts.items(), key=lambda x: x[1], reverse=True)
        ][:10]  # Top 10 clients
        
        # Analyze borrow rate trends over time
        rate_trend = []
        if len(df) > 0:
            date_rates = df.groupby("date")["borrow_rate"].mean().to_dict()
            rate_trend = [
                {
                    "date": date.isoformat(),
                    "rate": format_decimal_for_audit(rate)
                }
                for date, rate in sorted(date_rates.items())
            ]
        
        # Analyze fallback usage
        fallback_count = df["has_fallback"].sum()
        fallback_percentage = format_decimal_for_audit((fallback_count / transaction_count) * 100)
        
        if fallback_count > 0:
            fallback_rates = df[df["has_fallback"]]["borrow_rate"].tolist()
            normal_rates = df[~df["has_fallback"]]["borrow_rate"].tolist()
            
            avg_fallback_rate = (sum(fallback_rates) / len(fallback_rates)) if fallback_rates else Decimal('0')
            avg_normal_rate = (sum(normal_rates) / len(normal_rates)) if normal_rates else Decimal('0')
            
            rate_difference = format_decimal_for_audit(avg_fallback_rate - avg_normal_rate)
        else:
            rate_difference = None
        
        # Compile analysis
        analysis = {
            "ticker": ticker,
            "transaction_count": transaction_count,
            "transaction_volume": transaction_volume,
            "has_activity": True,
            "average_transaction_size": avg_transaction_size,
            "average_borrow_rate": avg_borrow_rate,
            "top_clients": top_clients,
            "rate_trend": rate_trend,
            "fallback_analysis": {
                "fallback_count": int(fallback_count),
                "fallback_percentage": fallback_percentage,
                "rate_difference": rate_difference
            }
        }
        
        return analysis