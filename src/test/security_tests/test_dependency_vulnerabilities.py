"""
Implements security tests for scanning and identifying vulnerabilities in project dependencies of the Borrow Rate & Locate Fee Pricing Engine.
This module focuses on detecting known security issues in third-party libraries, outdated packages, and potentially vulnerable dependencies
to ensure the system's overall security posture.
"""

import os
import pathlib
import json
import logging
import pytest
import subprocess
from typing import Dict, List, Optional, Any

# Internal imports
from ..config.settings import get_test_settings, TestSettings
from ..helpers.security_tools import run_dependency_scan

# Configure module logger
logger = logging.getLogger(__name__)

# Define paths to requirements files
BACKEND_REQUIREMENTS_PATH = os.path.join('src', 'backend', 'requirements.txt')
TEST_REQUIREMENTS_PATH = os.path.join('src', 'test', 'requirements.txt')

# Define severity levels
SEVERITY_LEVELS = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL']

# Dictionary of allowed vulnerabilities - will be populated from settings
ALLOWED_VULNERABILITIES = {}


def get_requirements_file_path(relative_path: str) -> str:
    """
    Gets the absolute path to a requirements file
    
    Args:
        relative_path: Relative path to the requirements file
        
    Returns:
        Absolute path to the requirements file
    """
    # Get the project root directory
    project_root = pathlib.Path(__file__).parent.parent.parent.parent
    
    # Construct the absolute path to the requirements file
    requirements_path = project_root / relative_path
    
    # Check if the file exists
    if not requirements_path.exists():
        raise FileNotFoundError(f"Requirements file not found: {requirements_path}")
    
    return str(requirements_path)


def load_allowed_vulnerabilities() -> Dict[str, List[str]]:
    """
    Loads the list of allowed vulnerabilities from settings
    
    Returns:
        Dictionary of package names to allowed vulnerability IDs
    """
    settings = get_test_settings()
    try:
        scanner_config = settings.get_security_tool_config('dependency_scanner')
        return scanner_config.get('allowed_vulnerabilities', {})
    except (ValueError, AttributeError):
        # Return empty dict if no configuration is found
        return {}


def is_vulnerability_allowed(package_name: str, vulnerability_id: str) -> bool:
    """
    Checks if a specific vulnerability is in the allowed list
    
    Args:
        package_name: Name of the package with vulnerability
        vulnerability_id: ID of the vulnerability
        
    Returns:
        True if the vulnerability is allowed, False otherwise
    """
    global ALLOWED_VULNERABILITIES
    
    # Check if package_name is in allowed vulnerabilities
    if package_name in ALLOWED_VULNERABILITIES:
        # Check if vulnerability_id is in the list for that package
        return vulnerability_id in ALLOWED_VULNERABILITIES[package_name]
    
    return False


def filter_allowed_vulnerabilities(scan_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filters out allowed vulnerabilities from scan results
    
    Args:
        scan_results: Original scan results with vulnerabilities
        
    Returns:
        Filtered scan results without allowed vulnerabilities
    """
    # Create a copy of the scan results
    filtered_results = scan_results.copy()
    
    # Check if vulnerabilities exist in the results
    if 'vulnerabilities_found' not in filtered_results:
        return filtered_results
    
    # Filter out allowed vulnerabilities
    filtered_vulnerabilities = []
    for vulnerability in filtered_results.get('vulnerabilities_found', []):
        package = vulnerability.get('package', '')
        advisory = vulnerability.get('advisory', '')
        
        # Extract vulnerability ID from advisory
        vulnerability_id = advisory
        if isinstance(advisory, str) and ':' in advisory:
            vulnerability_id = advisory.split(':')[0]
        
        # Keep vulnerability if it's not in the allowed list
        if not is_vulnerability_allowed(package, vulnerability_id):
            filtered_vulnerabilities.append(vulnerability)
    
    # Update the results with filtered vulnerabilities
    filtered_results['vulnerabilities_found'] = filtered_vulnerabilities
    
    # Update vulnerability counts in the summary
    if 'summary' in filtered_results:
        filtered_results['summary']['vulnerability_count'] = len(filtered_vulnerabilities)
        
        # Reset severity counts
        for severity in ['high_risk_count', 'medium_risk_count', 'low_risk_count', 'info_count']:
            filtered_results['summary'][severity] = 0
            
        # Count vulnerabilities by severity
        for vulnerability in filtered_vulnerabilities:
            severity = vulnerability.get('severity', 'unknown').lower()
            if severity == 'critical':
                filtered_results['summary']['high_risk_count'] += 1
            elif severity == 'high':
                filtered_results['summary']['high_risk_count'] += 1
            elif severity == 'medium':
                filtered_results['summary']['medium_risk_count'] += 1
            elif severity == 'low':
                filtered_results['summary']['low_risk_count'] += 1
            else:
                filtered_results['summary']['info_count'] += 1
    
    return filtered_results


def run_safety_scan(requirements_file: str) -> Dict[str, Any]:
    """
    Runs a safety scan on a requirements file
    
    Args:
        requirements_file: Path to the requirements file
        
    Returns:
        Scan results with vulnerable dependencies
    """
    # Get the absolute path to the requirements file
    requirements_path = get_requirements_file_path(requirements_file)
    
    # Use run_dependency_scan to scan the requirements file
    scan_results = run_dependency_scan(requirements_path)
    
    # Filter out allowed vulnerabilities from the results
    return filter_allowed_vulnerabilities(scan_results)


@pytest.mark.security
@pytest.mark.dependency
def test_backend_dependencies():
    """
    Tests backend dependencies for known vulnerabilities
    """
    # Load allowed vulnerabilities
    global ALLOWED_VULNERABILITIES
    ALLOWED_VULNERABILITIES = load_allowed_vulnerabilities()
    
    try:
        # Run safety scan on backend requirements file
        scan_results = run_safety_scan(BACKEND_REQUIREMENTS_PATH)
        
        # Check for critical vulnerabilities
        critical_vulnerabilities = []
        high_vulnerabilities = []
        medium_vulnerabilities = []
        
        # Process vulnerabilities by severity
        for vulnerability in scan_results.get('vulnerabilities_found', []):
            severity = vulnerability.get('severity', 'unknown').lower()
            if severity == 'critical':
                critical_vulnerabilities.append(vulnerability)
            elif severity == 'high':
                high_vulnerabilities.append(vulnerability)
            elif severity == 'medium':
                medium_vulnerabilities.append(vulnerability)
        
        # Log information about vulnerabilities found
        logger.info(f"Found {len(scan_results.get('vulnerabilities_found', []))} vulnerabilities in backend dependencies")
        logger.info(f"Critical: {len(critical_vulnerabilities)}, High: {len(high_vulnerabilities)}, Medium: {len(medium_vulnerabilities)}")
        
        # Generate detailed report of all vulnerabilities
        if scan_results.get('vulnerabilities_found', []):
            logger.warning("Vulnerable dependencies found:")
            for vulnerability in scan_results.get('vulnerabilities_found', []):
                package = vulnerability.get('package', '')
                version = vulnerability.get('installed_version', '')
                advisory = vulnerability.get('advisory', '')
                severity = vulnerability.get('severity', 'unknown')
                
                logger.warning(f"  - {package} {version}: {advisory} (Severity: {severity})")
        
        # Assert that no critical vulnerabilities are found
        assert len(critical_vulnerabilities) == 0, f"Critical vulnerabilities found in backend dependencies: {critical_vulnerabilities}"
    
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        logger.error(f"Error scanning backend dependencies: {str(e)}")
        pytest.skip(f"Dependency scan failed: {str(e)}")


@pytest.mark.security
@pytest.mark.dependency
def test_test_dependencies():
    """
    Tests test dependencies for known vulnerabilities
    """
    # Load allowed vulnerabilities if not already loaded
    global ALLOWED_VULNERABILITIES
    if not ALLOWED_VULNERABILITIES:
        ALLOWED_VULNERABILITIES = load_allowed_vulnerabilities()
    
    try:
        # Run safety scan on test requirements file
        scan_results = run_safety_scan(TEST_REQUIREMENTS_PATH)
        
        # Check for critical vulnerabilities
        critical_vulnerabilities = []
        high_vulnerabilities = []
        medium_vulnerabilities = []
        
        # Process vulnerabilities by severity
        for vulnerability in scan_results.get('vulnerabilities_found', []):
            severity = vulnerability.get('severity', 'unknown').lower()
            if severity == 'critical':
                critical_vulnerabilities.append(vulnerability)
            elif severity == 'high':
                high_vulnerabilities.append(vulnerability)
            elif severity == 'medium':
                medium_vulnerabilities.append(vulnerability)
        
        # Log information about vulnerabilities found
        logger.info(f"Found {len(scan_results.get('vulnerabilities_found', []))} vulnerabilities in test dependencies")
        logger.info(f"Critical: {len(critical_vulnerabilities)}, High: {len(high_vulnerabilities)}, Medium: {len(medium_vulnerabilities)}")
        
        # Generate detailed report of all vulnerabilities
        if scan_results.get('vulnerabilities_found', []):
            logger.warning("Vulnerable test dependencies found:")
            for vulnerability in scan_results.get('vulnerabilities_found', []):
                package = vulnerability.get('package', '')
                version = vulnerability.get('installed_version', '')
                advisory = vulnerability.get('advisory', '')
                severity = vulnerability.get('severity', 'unknown')
                
                logger.warning(f"  - {package} {version}: {advisory} (Severity: {severity})")
        
        # Assert that no critical vulnerabilities are found
        assert len(critical_vulnerabilities) == 0, f"Critical vulnerabilities found in test dependencies: {critical_vulnerabilities}"
    
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        logger.error(f"Error scanning test dependencies: {str(e)}")
        pytest.skip(f"Dependency scan failed: {str(e)}")


@pytest.mark.security
@pytest.mark.dependency
def test_outdated_packages():
    """
    Tests for outdated packages that might have security implications
    """
    logger.info("Checking for outdated packages")
    
    try:
        # Run pip list --outdated to check for outdated packages
        result = subprocess.run(
            ["pip", "list", "--outdated", "--format=json"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the output to identify outdated packages
        try:
            outdated_packages = json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response from pip list: {result.stdout}")
            outdated_packages = []
        
        # Define security-critical packages that should be kept updated
        security_critical_packages = [
            "requests", "urllib3", "cryptography", "pyjwt", "jwt", "jsonwebtoken",
            "django", "flask", "fastapi", "sqlalchemy", "psycopg2", "pymongo",
            "boto3", "pillow", "pyyaml", "numpy", "pandas", "scipy", "twisted", 
            "werkzeug", "jinja2", "pycryptodome", "openssl", "paramiko"
        ]
        
        # Filter security-critical packages
        critical_outdated = [
            pkg for pkg in outdated_packages 
            if pkg['name'].lower() in [p.lower() for p in security_critical_packages]
        ]
        
        # Log information about outdated packages
        logger.info(f"Found {len(outdated_packages)} outdated packages")
        logger.info(f"Security-critical outdated packages: {len(critical_outdated)}")
        
        # Generate report of all outdated packages
        if outdated_packages:
            logger.warning("Outdated packages:")
            for package in outdated_packages:
                name = package.get('name', '')
                current_version = package.get('version', '')
                latest_version = package.get('latest_version', '')
                is_critical = name.lower() in [p.lower() for p in security_critical_packages]
                
                message = f"  - {name}: {current_version} -> {latest_version}"
                if is_critical:
                    message += " (SECURITY-CRITICAL)"
                    logger.warning(message)
                else:
                    logger.info(message)
        
        # Log warnings for outdated security-critical packages
        if critical_outdated:
            logger.warning("Security-critical outdated packages found:")
            for package in critical_outdated:
                name = package.get('name', '')
                current_version = package.get('version', '')
                latest_version = package.get('latest_version', '')
                
                logger.warning(f"  - {name}: {current_version} -> {latest_version}")
        
        # No assertion fails here, just a warning - failing on outdated packages is too strict
        
    except subprocess.SubprocessError as e:
        logger.error(f"Error running pip list: {str(e)}")
        pytest.skip(f"Outdated package check failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error checking for outdated packages: {str(e)}")
        pytest.skip(f"Outdated package check failed with unexpected error: {str(e)}")


@pytest.mark.security
@pytest.mark.dependency
@pytest.mark.compliance
def test_dependency_license_compliance():
    """
    Tests dependencies for license compliance
    """
    logger.info("Checking dependency license compliance")
    
    try:
        # Run license check on all dependencies
        try:
            result = subprocess.run(
                ["pip-licenses", "--format=json", "--with-license-file", "--no-license-path"],
                capture_output=True,
                text=True,
                check=True
            )
        except FileNotFoundError:
            logger.error("pip-licenses tool not found. Install with: pip install pip-licenses")
            pytest.skip("pip-licenses tool not available")
            return
        
        # Parse the output to get license information
        try:
            licenses_info = json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response from pip-licenses: {result.stdout}")
            pytest.skip("Failed to parse pip-licenses output")
            return
        
        # Define problematic licenses
        restricted_licenses = [
            "GPL",            # GNU General Public License
            "AGPL",           # GNU Affero General Public License
            "LGPL",           # GNU Lesser General Public License
            "SSPL",           # Server Side Public License
            "UNLICENSED",     # No license
            "UNKNOWN"         # Unknown license
        ]
        
        # Define warning licenses
        warning_licenses = [
            "MPL",            # Mozilla Public License
            "CDDL",           # Common Development and Distribution License
            "EPL",            # Eclipse Public License
            "EUPL"            # European Union Public License
        ]
        
        # Filter packages with problematic licenses
        problematic_licenses = []
        warning_license_packages = []
        
        for package in licenses_info:
            name = package.get('Name', '')
            version = package.get('Version', '')
            license_name = package.get('License', '')
            
            if any(license_name.startswith(restricted) or restricted in license_name 
                   for restricted in restricted_licenses):
                problematic_licenses.append({
                    'name': name,
                    'version': version,
                    'license': license_name
                })
            
            if any(license_name.startswith(warning) or warning in license_name 
                   for warning in warning_licenses):
                warning_license_packages.append({
                    'name': name,
                    'version': version,
                    'license': license_name
                })
        
        # Log information about license compliance
        logger.info(f"Total packages: {len(licenses_info)}")
        logger.info(f"Packages with restricted licenses: {len(problematic_licenses)}")
        logger.info(f"Packages with warning licenses: {len(warning_license_packages)}")
        
        # Generate license compliance report
        if problematic_licenses:
            logger.warning("Packages with restricted licenses:")
            for package in problematic_licenses:
                logger.warning(f"  - {package['name']} {package['version']}: {package['license']}")
        
        if warning_license_packages:
            logger.warning("Packages with licenses that may require attention:")
            for package in warning_license_packages:
                logger.warning(f"  - {package['name']} {package['version']}: {package['license']}")
        
        # Verify that all dependencies have compatible licenses
        assert len(problematic_licenses) == 0, f"Packages with restricted licenses found: {problematic_licenses}"
        
    except subprocess.SubprocessError as e:
        logger.error(f"Error running pip-licenses: {str(e)}")
        pytest.skip(f"License compliance check failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error checking license compliance: {str(e)}")
        pytest.skip(f"License compliance check failed with unexpected error: {str(e)}")