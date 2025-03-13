```
### Technical Requirements for a Borrow Rate & Locate Fee Pricing Engine  
Below is a structured technical specification to design a pricing engine calculating **borrow rates** and **locate fees**, including data requirements, formulas, and REST API endpoints.

---

## **1. Data Requirements**  

#### **A. Internal Database Schema**  
- **Stocks Table** (Metadata for borrow status and external references):  
  ```sql
  CREATE TABLE Stocks (
    ticker VARCHAR(10) PRIMARY KEY,
    borrow_status ENUM('EASY', 'MEDIUM', 'HARD'), -- Easy-to-Borrow, Hard-to-Borrow tiers
    lender_api_id VARCHAR(50),                    -- Foreign key to external API's identifier (e.g., SecLend)
    min_borrow_rate DECIMAL(5,2) DEFAULT 0.0      -- Baseline rate if real-time data is unavailable
  );
  ```

- **Brokers Table** (Broker-specific markups and fees):  
  ```sql
  CREATE TABLE Brokers (
    client_id VARCHAR(50),
    markup_percentage DECIMAL(4,2),               -- e.g., 0.03 = +3% over base borrow rate
    transaction_fee_type ENUM('FLAT', 'PERCENTAGE'), 
    transaction_amount DECIMAL(10,2)              -- $X (flat) or % of PositionValue (%)
  );
  ```

- **Market Data Cache** (For volatility/event-based adjustments):  
  ```sql
  CREATE TABLE Volatility (
    stock_id VARCHAR(10),
    vol_index DECIMAL(5,2),                       -- e.g., VIX score for S&P equities
    event_risk_factor INT                         -- 0–10 based on earnings/news (external API)
  );
  ```

#### **B. External Data Sources**  
- **Real-Time Borrow Rate APIs**:  
  - Example: SecLend's API provides current `base_borrow_rate` and availability for each stock ticker.
  - Endpoint Example: `GET /api/v1/borrows/{ticker}` → Returns `{ "rate": 0.15, "status": "HARD" }`.

- **Market Volatility API**:  
  - Fetches volatility indices (e.g., VIX) to adjust borrow rates during volatile periods.
  - Example: `GET /api/market/vix` → Returns a volatility score (e.g., 20.5).

- **Event Calendar API**:  
  - Checks for upcoming earnings, trials, or regulatory events affecting borrow demand.

---

## **2. Formulas**  

#### **A. Borrow Rate Calculation**  
The base borrow rate is sourced from external APIs but adjusted dynamically:  
```python
def calculate_borrow_rate(ticker):
    # Get real-time rate from SecLend API (or fallback to Stocks.min_borrow_rate if unavailable)
    try:
        api_rate = get_sec_lend_rate(ticker)
    except:
        api_rate = Stocks.min_borrow_rate  # Fallback
    
    # Adjust for volatility and events
    volatility_adj = Volatility.vol_index * 0.01   # +1% per point over 20
    event_risk_adj = (Volatility.event_risk_factor / 10) * api_rate  # e.g., 5/10 → +0.5x rate
    
    total_adjusted_rate = api_rate * (1 + volatility_adj + event_risk_adj)
    
    return max(total_adjusted_rate, Stocks.min_borrow_rate)  # Ensure >= baseline
```

#### **B. Locate Fee Formula**  
Total fee paid by the client includes borrow cost + broker markup + transaction fees:  
```python
def calculate_total_fee(
    position_value: float,
    loan_days: int,
    base_borrow_rate: float,
    client_id: str) -> dict:

    # Step 1: Get Broker's Markup and Fees from Brokers table
    broker_data = get_broker_by_client(client_id)
    markup_pct = broker_data['markup_percentage']
    tx_fee_type = broker_data['transaction_fee_type']
    tx_amount = broker_data['transaction_amount']

    # Step 2: Calculate Borrow Cost (Annualized → Adjusted to Days)
    annual_cost = position_value * base_borrow_rate
    time_factor = loan_days / 365.0
    borrow_cost = annual_cost * time_factor

    # Step 3: Add Broker Markup
    markup_cost = borrow_cost * markup_pct

    # Step 4: Calculate Transaction Fees
    if tx_fee_type == 'FLAT':
        transaction_fees = tx_amount
    else:
        transaction_fees = position_value * (tx_amount / 100)  # Percentage
    
    # Total Fee
    total_fee = borrow_cost + markup_cost + transaction_fees

    return {
        "total_fee": round(total_fee, 2),
        "breakdown": {
            "borrow_cost": round(borrow_cost, 2),
            "markup": round(markup_cost, 2),
            "transaction_fees": round(transaction_fees, 2)
        }
    }
```

---

## **3. REST API Endpoint**  
#### **Endpoint**: `/api/v1/calculate-locate`  

| **HTTP Method** | `GET` or `POST` (JSON) |
|------------------|------------------------|
| **Parameters**   | - `ticker`: Stock symbol (e.g., "AAPL") <br> - `position_value`: Notional value of the short sale in USD <br> - `loan_days`: Duration of borrow period (days) <br> - `client_id`: Unique client identifier for markup/fee tier |

#### **Example Request**  
```http
GET /api/v1/calculate-locate?ticker=AAPL&position_value=100000&loan_days=30&client_id=xyz123 HTTP/1.1
```

OR (for POST):  
```json
{
  "ticker": "GME",
  "position_value": 50000,
  "loan_days": 60,
  "client_id": "big_fund_007"
}
```

#### **Example Response**  
```json
{
  "status": "success",
  "total_fee": 3428.77,
  "breakdown": {
    "borrow_cost": 3195.34,       // Base rate + volatility/events (e.g., 10% annual * $50k → $12,671 annually)
    "markup": 188.53,            // Broker's +2% markup on borrow cost
    "transaction_fees": 40.9     // Flat $40 fee from broker config
  },
  "borrow_rate_used": 0.19       // 19% annualized (base rate adjusted for risk)
}
```

---

## **4. Additional Considerations**  

### **A. Caching Strategy**  
- Use Redis to cache borrow rates and volatility data:  
  ```python
  # Cache example with TTL = 5 minutes:
  redis.set(f"borrow_rate_{ticker}", api_rate, ex=300)
  ```

### **B. Error Handling**  
- Return errors for invalid inputs (e.g., negative loan_days):  
  ```json
  {
    "error": "Invalid parameter: 'loan_days' must be ≥ 1",
    "valid_params": ["ticker", "position_value>0"]
  }
  ```

### **C. Security**  
- **Authentication**: Require API keys for requests (e.g., via `Authorization` header).  
- **Rate Limiting**: Implement per-client rate limits to prevent abuse.  

---

## **5. Deployment & Dependencies**  
- **Backend Stack**: Python (FastAPI) or Node.js + PostgreSQL/Redis.  
- **External APIs**: Integrate with SecLend, Yahoo Finance API for volatility, and an event calendar service like Calendarific.

This system ensures dynamic pricing while exposing a clean REST interface for applications to compute borrow costs and locate fees in real time.
```