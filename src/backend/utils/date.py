"""
Utility module providing date and time functions for the Borrow Rate & Locate Fee Pricing Engine.

This module handles date calculations, formatting, and validation required for loan periods,
rate calculations, and time-based operations.
"""

from datetime import datetime, date, timedelta
import time
from typing import Optional, Union
from decimal import Decimal  # standard library

# Constants
DAYS_IN_YEAR = 365
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DEFAULT_TTL_SECONDS = 300  # 5 minutes default TTL for data freshness


def get_current_date() -> date:
    """
    Returns the current date as a date object.

    Returns:
        date: Current date
    """
    return date.today()


def get_current_datetime() -> datetime:
    """
    Returns the current date and time as a datetime object.

    Returns:
        datetime: Current date and time
    """
    return datetime.now()


def get_current_timestamp() -> float:
    """
    Returns the current timestamp in seconds since epoch.

    Returns:
        float: Current timestamp
    """
    return time.time()


def format_date(date_obj: date, format_str: Optional[str] = None) -> str:
    """
    Formats a date object as a string using the specified format.

    Args:
        date_obj: The date object to format
        format_str: Optional format string (uses DATE_FORMAT if None)

    Returns:
        str: Formatted date string
    """
    if format_str is None:
        format_str = DATE_FORMAT
    return date_obj.strftime(format_str)


def format_datetime(datetime_obj: datetime, format_str: Optional[str] = None) -> str:
    """
    Formats a datetime object as a string using the specified format.

    Args:
        datetime_obj: The datetime object to format
        format_str: Optional format string (uses DATETIME_FORMAT if None)

    Returns:
        str: Formatted datetime string
    """
    if format_str is None:
        format_str = DATETIME_FORMAT
    return datetime_obj.strftime(format_str)


def format_iso(datetime_obj: datetime) -> str:
    """
    Formats a datetime object as an ISO 8601 string.

    Args:
        datetime_obj: The datetime object to format

    Returns:
        str: ISO formatted datetime string
    """
    return datetime_obj.strftime(ISO_FORMAT)


def parse_date(date_str: str, format_str: Optional[str] = None) -> Optional[date]:
    """
    Parses a date string into a date object.

    Args:
        date_str: The date string to parse
        format_str: Optional format string (uses DATE_FORMAT if None)

    Returns:
        date: Parsed date object, or None if parsing fails
    """
    if format_str is None:
        format_str = DATE_FORMAT
    
    try:
        return datetime.strptime(date_str, format_str).date()
    except ValueError:
        return None


def parse_datetime(datetime_str: str, format_str: Optional[str] = None) -> Optional[datetime]:
    """
    Parses a datetime string into a datetime object.

    Args:
        datetime_str: The datetime string to parse
        format_str: Optional format string (uses DATETIME_FORMAT if None)

    Returns:
        datetime: Parsed datetime object, or None if parsing fails
    """
    if format_str is None:
        format_str = DATETIME_FORMAT
    
    try:
        return datetime.strptime(datetime_str, format_str)
    except ValueError:
        return None


def parse_iso(iso_str: str) -> Optional[datetime]:
    """
    Parses an ISO 8601 datetime string into a datetime object.

    Args:
        iso_str: The ISO 8601 string to parse

    Returns:
        datetime: Parsed datetime object, or None if parsing fails
    """
    try:
        return datetime.strptime(iso_str, ISO_FORMAT)
    except ValueError:
        return None


def add_days(date_obj: Union[date, datetime], days: int) -> Union[date, datetime]:
    """
    Adds a specified number of days to a date or datetime object.

    Args:
        date_obj: The date or datetime object
        days: Number of days to add

    Returns:
        Union[date, datetime]: Date or datetime with days added
    """
    return date_obj + timedelta(days=days)


def subtract_days(date_obj: Union[date, datetime], days: int) -> Union[date, datetime]:
    """
    Subtracts a specified number of days from a date or datetime object.

    Args:
        date_obj: The date or datetime object
        days: Number of days to subtract

    Returns:
        Union[date, datetime]: Date or datetime with days subtracted
    """
    return date_obj - timedelta(days=days)


def days_between(start_date: Union[date, datetime], end_date: Union[date, datetime]) -> int:
    """
    Calculates the number of days between two date or datetime objects.

    Args:
        start_date: The starting date
        end_date: The ending date

    Returns:
        int: Number of days between dates
    """
    delta = end_date - start_date
    return delta.days


def is_date_in_range(check_date: Union[date, datetime], 
                     start_date: Union[date, datetime], 
                     end_date: Union[date, datetime]) -> bool:
    """
    Checks if a date is within a specified range.

    Args:
        check_date: The date to check
        start_date: The start of the range
        end_date: The end of the range

    Returns:
        bool: True if date is in range, False otherwise
    """
    return start_date <= check_date <= end_date


def is_date_in_future(check_date: Union[date, datetime]) -> bool:
    """
    Checks if a date is in the future.

    Args:
        check_date: The date to check

    Returns:
        bool: True if date is in the future, False otherwise
    """
    if isinstance(check_date, datetime):
        return check_date > datetime.now()
    return check_date > date.today()


def is_date_in_past(check_date: Union[date, datetime]) -> bool:
    """
    Checks if a date is in the past.

    Args:
        check_date: The date to check

    Returns:
        bool: True if date is in the past, False otherwise
    """
    if isinstance(check_date, datetime):
        return check_date < datetime.now()
    return check_date < date.today()


def calculate_loan_end_date(start_date: Union[date, datetime], loan_days: int) -> Union[date, datetime]:
    """
    Calculates the end date of a loan based on start date and loan days.

    Args:
        start_date: The loan start date
        loan_days: The duration of the loan in days

    Returns:
        Union[date, datetime]: End date of the loan
    """
    return start_date + timedelta(days=loan_days)


def is_data_fresh(data_timestamp: datetime, ttl_seconds: Optional[int] = None) -> bool:
    """
    Checks if data timestamp is within the freshness threshold.

    Args:
        data_timestamp: The timestamp of the data
        ttl_seconds: Time-to-live in seconds (uses DEFAULT_TTL_SECONDS if None)

    Returns:
        bool: True if data is fresh, False otherwise
    """
    if ttl_seconds is None:
        ttl_seconds = DEFAULT_TTL_SECONDS
    
    current_time = datetime.now()
    age_seconds = (current_time - data_timestamp).total_seconds()
    
    return age_seconds < ttl_seconds


def get_ttl_expiry(ttl_seconds: int) -> float:
    """
    Calculates the expiry timestamp for a TTL.

    Args:
        ttl_seconds: Time-to-live in seconds

    Returns:
        float: Expiry timestamp
    """
    return time.time() + ttl_seconds


def get_remaining_ttl(expiry_timestamp: float) -> int:
    """
    Calculates the remaining TTL in seconds for a timestamp.

    Args:
        expiry_timestamp: The expiry timestamp

    Returns:
        int: Remaining TTL in seconds, 0 if expired
    """
    remaining_seconds = expiry_timestamp - time.time()
    return max(0, int(remaining_seconds))


def get_date_components(date_obj: Union[date, datetime]) -> tuple[int, int, int]:
    """
    Extracts year, month, and day components from a date object.

    Args:
        date_obj: The date or datetime object

    Returns:
        tuple[int, int, int]: Tuple of (year, month, day)
    """
    return (date_obj.year, date_obj.month, date_obj.day)


def get_time_components(datetime_obj: datetime) -> tuple[int, int, int]:
    """
    Extracts hour, minute, and second components from a datetime object.

    Args:
        datetime_obj: The datetime object

    Returns:
        tuple[int, int, int]: Tuple of (hour, minute, second)
    """
    return (datetime_obj.hour, datetime_obj.minute, datetime_obj.second)


def get_last_day_of_month(date_obj: Union[date, datetime]) -> Union[date, datetime]:
    """
    Gets the last day of the month for a given date.

    Args:
        date_obj: The date or datetime object

    Returns:
        Union[date, datetime]: Date object representing the last day of the month
    """
    year, month = date_obj.year, date_obj.month
    
    # Calculate first day of next month
    if month == 12:
        next_month_year = year + 1
        next_month = 1
    else:
        next_month_year = year
        next_month = month + 1
    
    first_of_next_month = date(next_month_year, next_month, 1)
    last_day_of_month = first_of_next_month - timedelta(days=1)
    
    # If input was a datetime, return datetime
    if isinstance(date_obj, datetime):
        return datetime.combine(last_day_of_month, date_obj.time())
    return last_day_of_month