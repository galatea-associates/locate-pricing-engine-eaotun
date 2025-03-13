"""
Utility functions for the audit service in the Borrow Rate & Locate Fee Pricing Engine.

This module provides helper functions for creating standardized data source entries,
formatting decimal values, serializing/deserializing audit data, and analyzing
audit records to support regulatory compliance and troubleshooting.
"""

import json  # standard library
from decimal import Decimal  # standard library
from typing import Dict, List, Optional, Any, Union  # standard library
from datetime import datetime  # standard library
import uuid  # standard library

from ...schemas.audit import DataSourceSchema

# Constants for decimal precision
DECIMAL_PRECISION = 4  # Standard precision for rates and adjustments
MONEY_PRECISION = 2  # Precision for monetary values (dollars and cents)


def create_data_source_entry(
    source_name: str,
    source_type: str,
    is_fallback: bool,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized data source entry for audit logs.
    
    Args:
        source_name: Name of the data source
        source_type: Type of the data source (e.g., 'api', 'cache', 'database')
        is_fallback: Whether this is a fallback data source
        metadata: Additional metadata about the data source
        
    Returns:
        Standardized data source entry
    """
    entry = {
        "source_name": source_name,
        "source_type": source_type,
        "is_fallback": is_fallback,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if metadata:
        entry["metadata"] = metadata
        
    return entry


def create_api_data_source(
    api_name: str,
    endpoint: str,
    is_fallback: bool,
    status_code: Optional[int] = None,
    response_time: Optional[float] = None
) -> Dict[str, Any]:
    """
    Create a data source entry for an external API.
    
    Args:
        api_name: Name of the API service
        endpoint: API endpoint that was called
        is_fallback: Whether this is a fallback data source
        status_code: HTTP status code from the API response
        response_time: Response time in milliseconds
        
    Returns:
        API data source entry
    """
    metadata = {
        "endpoint": endpoint
    }
    
    if status_code is not None:
        metadata["status_code"] = status_code
        
    if response_time is not None:
        metadata["response_time"] = response_time
        
    return create_data_source_entry(api_name, "api", is_fallback, metadata)


def create_cache_data_source(
    cache_name: str,
    key: str,
    hit: bool,
    ttl: Optional[float] = None
) -> Dict[str, Any]:
    """
    Create a data source entry for cache access.
    
    Args:
        cache_name: Name of the cache service
        key: Cache key that was accessed
        hit: Whether the access was a cache hit
        ttl: Time-to-live value for the cache entry in seconds
        
    Returns:
        Cache data source entry
    """
    metadata = {
        "key": key,
        "hit": hit
    }
    
    if ttl is not None:
        metadata["ttl"] = ttl
        
    # Cache is never a fallback source
    return create_data_source_entry(cache_name, "cache", False, metadata)


def create_database_data_source(
    table_name: str,
    operation: str,
    is_fallback: bool,
    query_time: Optional[float] = None
) -> Dict[str, Any]:
    """
    Create a data source entry for database access.
    
    Args:
        table_name: Name of the database table
        operation: Database operation (e.g., 'select', 'insert')
        is_fallback: Whether this is a fallback data source
        query_time: Query execution time in milliseconds
        
    Returns:
        Database data source entry
    """
    metadata = {
        "operation": operation
    }
    
    if query_time is not None:
        metadata["query_time"] = query_time
        
    return create_data_source_entry(table_name, "database", is_fallback, metadata)


def format_decimal_for_audit(
    value: Union[Decimal, float],
    precision: Optional[int] = None
) -> Decimal:
    """
    Format decimal values consistently for audit logs.
    
    Args:
        value: Decimal or float value to format
        precision: Number of decimal places to round to (defaults to DECIMAL_PRECISION)
        
    Returns:
        Formatted decimal value with consistent precision
    """
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    
    if precision is None:
        precision = DECIMAL_PRECISION
        
    return value.quantize(Decimal(f'0.{"0" * precision}'))


def has_fallback_source(data_sources: List[Dict[str, Any]]) -> bool:
    """
    Check if fallback mechanisms were used in a calculation.
    
    Args:
        data_sources: List of data source entries
        
    Returns:
        True if any data source used fallback mechanisms
    """
    for source in data_sources:
        if source.get("is_fallback", False):
            return True
    return False


def get_data_source_names(data_sources: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Extract data source names from audit records.
    
    Args:
        data_sources: List of data source entries
        
    Returns:
        Dictionary mapping data types to source names
    """
    result = {}
    for source in data_sources:
        source_name = source.get("source_name", "unknown")
        source_type = source.get("source_type", "unknown")
        result[source_type] = source_name
    return result


class AuditDataEncoder(json.JSONEncoder):
    """Custom JSON encoder for audit data types."""
    
    def default(self, obj):
        """Convert special types to JSON-serializable formats."""
        if isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)


def serialize_audit_data(data: Dict[str, Any]) -> str:
    """
    Serialize audit data for storage.
    
    Args:
        data: Audit data dictionary
        
    Returns:
        JSON string representation of audit data
    """
    return json.dumps(data, cls=AuditDataEncoder)


def deserialize_audit_data(json_data: str) -> Dict[str, Any]:
    """
    Deserialize audit data from storage.
    
    Args:
        json_data: JSON string of audit data
        
    Returns:
        Deserialized audit data
    """
    def decimal_parser(dct):
        for key, value in dct.items():
            if isinstance(value, str):
                try:
                    if '.' in value and value.replace('.', '').isdigit():
                        dct[key] = Decimal(value)
                except:
                    pass
        return dct
    
    return json.loads(json_data, object_hook=decimal_parser)


def create_audit_context(
    request_id: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create contextual information for audit logging.
    
    Args:
        request_id: Identifier for the API request
        user_agent: User agent of the client making the request
        ip_address: IP address of the client
        additional_context: Any additional contextual information
        
    Returns:
        Audit context dictionary
    """
    context = {
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if request_id:
        context["request_id"] = request_id
        
    if user_agent:
        context["user_agent"] = user_agent
        
    if ip_address:
        context["ip_address"] = ip_address
        
    if additional_context:
        context.update(additional_context)
        
    return context