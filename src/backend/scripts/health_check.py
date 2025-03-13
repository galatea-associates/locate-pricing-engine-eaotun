#!/usr/bin/env python
"""
Health check script for the Borrow Rate & Locate Fee Pricing Engine.

This script performs connectivity checks on the database, Redis cache, and external APIs,
providing a comprehensive health status report that can be used for monitoring,
troubleshooting, and operational validation outside of the main API service.
"""

import argparse  # standard library
import sys  # standard library
import json  # standard library
import datetime  # standard library
import time  # standard library
import requests  # requests 2.28.0+
from typing import Dict, Any, Optional

# Internal imports
from ..db.session import ping_database
from ..services.cache.redis import RedisCache
from ..services.external.client import get
from ..core.constants import ExternalAPIs
from ..config.settings import get_settings
from ..utils.logging import setup_logger

# Set up logger
logger = setup_logger('scripts.health_check')

# Script version
VERSION = "1.0.0"


def check_database_health() -> Dict[str, Any]:
    """
    Checks database connectivity by executing a simple query.
    
    Returns:
        Dict[str, Any]: Database health status with connection state
    """
    logger.info("Checking database health...")
    start_time = time.time()
    
    try:
        is_connected = ping_database()
        elapsed_time = time.time() - start_time
        
        result = {
            "status": "connected" if is_connected else "disconnected",
            "response_time_ms": round(elapsed_time * 1000, 2)
        }
        
        logger.info(f"Database health check result: {result['status']}")
        return result
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Database health check failed: {str(e)}")
        
        return {
            "status": "disconnected",
            "error": str(e),
            "response_time_ms": round(elapsed_time * 1000, 2)
        }


def check_cache_health() -> Dict[str, Any]:
    """
    Checks Redis cache connectivity and retrieves cache statistics.
    
    Returns:
        Dict[str, Any]: Cache health status with connection state and statistics
    """
    logger.info("Checking cache health...")
    
    try:
        # Get settings
        settings = get_settings()
        
        # Initialize Redis cache client
        redis_cache = RedisCache(
            host="localhost",  # This should be extracted from settings
            port=6379,         # This should be extracted from settings
        )
        
        # Check if connected
        if not redis_cache.is_connected():
            return {
                "status": "disconnected",
                "error": "Failed to connect to Redis cache"
            }
        
        # Get detailed health information
        health_info = redis_cache.health_check()
        return health_info
        
    except Exception as e:
        logger.error(f"Cache health check failed: {str(e)}")
        
        return {
            "status": "disconnected",
            "error": str(e)
        }


def check_external_apis_health() -> Dict[str, Any]:
    """
    Checks connectivity to all external APIs.
    
    Returns:
        Dict[str, Any]: External APIs health status with connection states
    """
    logger.info("Checking external APIs health...")
    
    settings = get_settings()
    results = {"apis": {}}
    
    # Check all external APIs
    apis_to_check = [
        (ExternalAPIs.SECLEND, "seclend"),
        (ExternalAPIs.MARKET_VOLATILITY, "market_volatility"),
        (ExternalAPIs.EVENT_CALENDAR, "event_calendar")
    ]
    
    for api_const, api_name in apis_to_check:
        try:
            api_config = settings.get_external_api_config(api_const)
            api_url = f"{api_config['base_url']}/health"
            headers = {"X-API-Key": api_config["api_key"]}
            
            start_time = time.time()
            try:
                # Use the imported get function for consistent error handling
                response = get(
                    url=api_url,
                    service_name=api_name,
                    headers=headers,
                    timeout=5,
                    fallback_value=None
                )
                success = True
                error_message = None
            except Exception as e:
                success = False
                error_message = str(e)
                
            elapsed_time = time.time() - start_time
            
            results["apis"][api_name] = {
                "status": "available" if success else "unavailable",
                "response_time_ms": round(elapsed_time * 1000, 2)
            }
            
            if not success and error_message:
                results["apis"][api_name]["error"] = error_message
                
        except Exception as e:
            results["apis"][api_name] = {
                "status": "unavailable",
                "error": str(e)
            }
    
    # Determine overall status
    all_available = all(api["status"] == "available" for api in results["apis"].values())
    results["status"] = "available" if all_available else "degraded"
    
    return results


def get_system_health() -> Dict[str, Any]:
    """
    Collects health status from all components.
    
    Returns:
        Dict[str, Any]: Complete health status report
    """
    logger.info("Performing system health check...")
    
    # Check all components
    db_health = check_database_health()
    cache_health = check_cache_health()
    apis_health = check_external_apis_health()
    
    # Determine overall system status
    db_ok = db_health.get("status") == "connected"
    cache_ok = cache_health.get("status") == "connected" 
    apis_ok = apis_health.get("status") == "available"
    
    if db_ok and cache_ok and apis_ok:
        overall_status = "healthy"
    elif not db_ok or not cache_ok:
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"
    
    # Build complete health report
    report = {
        "version": VERSION,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "status": overall_status,
        "components": {
            "database": db_health,
            "cache": cache_health,
            "external_apis": apis_health
        }
    }
    
    return report


def format_output(health_data: Dict[str, Any], output_format: str) -> str:
    """
    Formats health check results based on output format option.
    
    Args:
        health_data: Health check results
        output_format: Format to use (json or text)
        
    Returns:
        str: Formatted health check results
    """
    if output_format == "json":
        return json.dumps(health_data, indent=2)
    else:  # text format
        lines = []
        lines.append(f"System Health Check (v{VERSION})")
        lines.append(f"Timestamp: {health_data.get('timestamp', datetime.datetime.now().isoformat())}")
        lines.append(f"Status: {health_data.get('status', 'UNKNOWN').upper()}")
        lines.append("")
        
        # Format components
        if "components" in health_data:
            components = health_data["components"]
            
            # Database
            if "database" in components:
                db = components["database"]
                lines.append("Database:")
                lines.append(f"  Status: {db.get('status', 'unknown')}")
                if "response_time_ms" in db:
                    lines.append(f"  Response Time: {db['response_time_ms']} ms")
                if "error" in db:
                    lines.append(f"  Error: {db['error']}")
                lines.append("")
            
            # Cache
            if "cache" in components:
                cache = components["cache"]
                lines.append("Cache:")
                lines.append(f"  Status: {cache.get('status', 'unknown')}")
                if "response_time_ms" in cache:
                    lines.append(f"  Response Time: {cache['response_time_ms']} ms")
                if "server_info" in cache:
                    info = cache["server_info"]
                    lines.append(f"  Redis Version: {info.get('redis_version', 'unknown')}")
                    lines.append(f"  Memory Usage: {info.get('used_memory_human', 'unknown')}")
                if "error" in cache:
                    lines.append(f"  Error: {cache['error']}")
                lines.append("")
            
            # External APIs
            if "external_apis" in components:
                apis = components["external_apis"]
                lines.append("External APIs:")
                lines.append(f"  Overall Status: {apis.get('status', 'unknown')}")
                
                if "apis" in apis:
                    for api_name, api_data in apis["apis"].items():
                        lines.append(f"  {api_name.replace('_', ' ').title()}:")
                        lines.append(f"    Status: {api_data.get('status', 'unknown')}")
                        if "response_time_ms" in api_data:
                            lines.append(f"    Response Time: {api_data['response_time_ms']} ms")
                        if "error" in api_data:
                            lines.append(f"    Error: {api_data['error']}")
                lines.append("")
        else:
            # Handle component-specific health checks
            for component, data in health_data.items():
                if component in ("version", "timestamp", "status"):
                    continue
                    
                lines.append(f"{component.replace('_', ' ').title()}:")
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, dict):
                            lines.append(f"  {key.replace('_', ' ').title()}:")
                            for subkey, subvalue in value.items():
                                lines.append(f"    {subkey.replace('_', ' ').title()}: {subvalue}")
                        else:
                            lines.append(f"  {key.replace('_', ' ').title()}: {value}")
                else:
                    lines.append(f"  Data: {data}")
                lines.append("")
        
        return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    """
    Parses command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Health check utility for the Borrow Rate & Locate Fee Pricing Engine"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)"
    )
    
    parser.add_argument(
        "--component", "-c",
        choices=["database", "cache", "external_apis", "all"],
        default="all",
        help="Component to check (default: all)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()


def main() -> int:
    """
    Main entry point for the script.
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    args = parse_args()
    
    try:
        # Perform requested health checks
        if args.component == "database":
            result = {"database": check_database_health()}
        elif args.component == "cache":
            result = {"cache": check_cache_health()}
        elif args.component == "external_apis":
            result = {"external_apis": check_external_apis_health()}
        else:  # all components
            result = get_system_health()
        
        # Format and output results
        output = format_output(result, args.format)
        print(output)
        
        # Determine exit code based on overall health status
        if args.component == "all":
            return 0 if result["status"] == "healthy" else 1
        else:
            # For individual component checks
            component_status = list(result.values())[0].get("status", "")
            if component_status in ["connected", "available"]:
                return 0
            return 1
            
    except Exception as e:
        logger.error(f"Error during health check: {str(e)}")
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())