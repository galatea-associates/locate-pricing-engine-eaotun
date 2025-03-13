import os
import setuptools
from setuptools import find_packages

# Read README.md for the long description
try:
    README = open('README.md', 'r', encoding='utf-8').read()
except FileNotFoundError:
    README = "Borrow Rate & Locate Fee Pricing Engine for securities lending"

# Read requirements.txt for dependencies
try:
    REQUIREMENTS = open('requirements.txt', 'r', encoding='utf-8').read().splitlines()
except FileNotFoundError:
    REQUIREMENTS = [
        "fastapi>=0.103.0",  # API Framework
        "pydantic>=2.4.0",   # Data Validation
        "pandas>=2.1.0",     # Data Processing
        "pytest>=7.4.0",     # Testing
        "httpx>=0.25.0",     # API Client
        "redis>=7.0.0",      # Caching Layer
        "sqlalchemy>=2.0.0", # Database ORM
        "psycopg2-binary>=2.9.0", # PostgreSQL Driver
    ]

def get_version():
    """
    Extracts version from pyproject.toml or returns a default version
    
    Returns:
        str: Version string in format 'x.y.z'
    """
    # Try to use tomllib for Python 3.11+ (built-in)
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
            
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            return data.get("tool", {}).get("poetry", {}).get("version", "0.1.0")
    except (ImportError, FileNotFoundError):
        # Fallback using regex if tomllib/tomli is not available
        try:
            import re
            with open("pyproject.toml", "r", encoding="utf-8") as f:
                content = f.read()
                version_match = re.search(r'version\s*=\s*"([^"]+)"', content)
                if version_match:
                    return version_match.group(1)
        except FileNotFoundError:
            pass
        
        # Default version if all else fails
        return "0.1.0"

setuptools.setup(
    name="borrow-rate-pricing-engine",
    version=get_version(),
    description="Borrow Rate & Locate Fee Pricing Engine for securities lending",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Financial Engineering Team",
    author_email="engineering@example.com",
    url="https://github.com/organization/borrow-rate-pricing-engine",
    packages=find_packages(include=['backend', 'backend.*']),
    python_requires=">=3.11,<3.12",
    install_requires=REQUIREMENTS,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Financial",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    entry_points={
        "console_scripts": [
            "generate-api-key=backend.scripts.generate_api_key:main",
            "seed-data=backend.scripts.seed_data:main",
            "run-migrations=backend.scripts.run_migrations:main",
        ],
    },
)