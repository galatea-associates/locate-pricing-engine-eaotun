# Test Data Generators

Tools for generating synthetic test data for the Borrow Rate & Locate Fee Pricing Engine

This module provides a comprehensive set of tools for generating realistic test data for the Borrow Rate & Locate Fee Pricing Engine. The generated data can be used for unit tests, integration tests, performance tests, and end-to-end tests.

## Features

- Generation of synthetic stocks with configurable borrow statuses and rates
- Creation of broker configurations with various fee structures
- Volatility and event risk data generation for different market scenarios
- Market data generation with historical price movements
- Event data generation for corporate actions
- API key generation for authentication testing
- Support for multiple output formats (JSON, CSV, SQL)
- Predefined test scenarios (normal market, high volatility, corporate events, etc.)
- Configurable parameters for all data types

## Installation

1. Ensure Python 3.11+ is installed
2. Install required dependencies: `pip install -r requirements.txt`
3. Configure environment variables or use default settings

## Usage

### Basic Usage
```bash
# Generate all data types with default settings
python run_generation.py --all

# Generate specific data types
python run_generation.py --stocks --brokers

# Specify a test scenario
python run_generation.py --all --scenario high_volatility

# Specify output format
python run_generation.py --all --output-format json
```

### Advanced Usage
```bash
# Customize data volume
python run_generation.py --all --stock-count 500 --broker-count 25

# Customize time ranges
python run_generation.py --all --history-days 60 --future-days 30

# Use custom configuration file
python run_generation.py --all --config custom_config.yaml
```

## Available Test Scenarios

- `normal_market`: Standard market conditions with average volatility
- `high_volatility`: Market conditions with elevated volatility
- `corporate_events`: Many stocks with upcoming corporate events
- `hard_to_borrow`: Market with limited stock availability
- `market_disruption`: Extreme market conditions with very high volatility

## Configuration

### Environment Variables
The data generators can be configured using environment variables:

```
# Database configuration
TEST_DB_HOST=localhost
TEST_DB_PORT=5432
TEST_DB_USER=postgres
TEST_DB_PASSWORD=postgres
TEST_DB_NAME=test_pricing_engine

# Stock generation
STOCK_COUNT=1000
ETB_PERCENTAGE=0.7
HTB_PERCENTAGE=0.3
MIN_STOCK_PRICE=1.0
MAX_STOCK_PRICE=1000.0
MIN_BORROW_RATE=0.01
MAX_BORROW_RATE=0.5

# Broker generation
BROKER_COUNT=50
MIN_MARKUP_PERCENTAGE=0.05
MAX_MARKUP_PERCENTAGE=0.25
MIN_TRANSACTION_AMOUNT=1.0
MAX_TRANSACTION_AMOUNT=100.0

# Volatility generation
MIN_VOLATILITY_INDEX=10.0
MAX_VOLATILITY_INDEX=50.0
MIN_EVENT_RISK_FACTOR=0
MAX_EVENT_RISK_FACTOR=10
VOLATILITY_HISTORY_DAYS=30

# Event generation
EVENTS_PER_STOCK_PROBABILITY=0.2
EVENT_FUTURE_DAYS_RANGE=30
```

### Custom Configuration File
You can also provide a custom YAML configuration file:

```yaml
stock_generation:
  count: 500
  etb_percentage: 0.6
  htb_percentage: 0.4

broker_generation:
  count: 25
  min_markup_percentage: 0.1
  max_markup_percentage: 0.3

test_scenarios:
  custom_scenario:
    description: "Custom test scenario"
    volatility_range: [20.0, 40.0]
    etb_percentage: 0.5
    htb_percentage: 0.5
    event_probability: 0.4
```

## Output Formats

- `json`: JSON files for easy consumption in JavaScript/Python
- `csv`: CSV files for import into spreadsheets or databases
- `sql`: SQL insert statements for direct database loading

## Module Structure

- `config.py`: Configuration settings and utilities
- `stocks.py`: Stock data generation
- `brokers.py`: Broker configuration generation
- `volatility.py`: Volatility and event risk data generation
- `market_data.py`: Historical market data generation
- `event_data.py`: Corporate event data generation
- `api_keys.py`: API key generation
- `run_generation.py`: Main script for running data generation

## Examples

### Example Stock Data
```json
{
  "ticker": "AAPL",
  "borrow_status": "EASY",
  "min_borrow_rate": 0.03,
  "company_name": "Apple Inc.",
  "exchange": "NASDAQ",
  "sector": "Technology",
  "last_updated": "2023-10-15T14:30:22Z"
}
```

### Example Volatility Data
```json
{
  "stock_id": "AAPL",
  "vol_index": 18.5,
  "event_risk_factor": 2,
  "timestamp": "2023-10-15T14:30:22Z"
}
```

### Example Broker Configuration
```json
{
  "client_id": "broker123",
  "markup_percentage": 0.15,
  "transaction_fee_type": "PERCENTAGE",
  "transaction_amount": 0.02,
  "active": true
}
```

## Contributing

1. Follow the project's coding standards
2. Add tests for new data generation features
3. Update documentation when adding new features
4. Ensure backward compatibility with existing test data

## Troubleshooting

- **Issue**: Missing dependencies
  **Solution**: Run `pip install -r requirements.txt`

- **Issue**: Permission errors when writing output files
  **Solution**: Check directory permissions or specify a different output directory

- **Issue**: Database connection errors
  **Solution**: Verify database configuration in environment variables or .env file