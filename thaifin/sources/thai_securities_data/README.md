# Thai Securities Data Source for ThaiFin

This module provides an alternative data source for the ThaiFin library, accessing Thai stock market data through the Thai Securities Data API. It offers comprehensive financial data, market data, and company information as an alternative to the default Finnomena source.

## 🎯 Purpose

- **Alternative Data Source**: Provides redundancy and different perspective to Finnomena
- **Comprehensive Coverage**: 10+ years of financial data with quarterly and yearly breakdowns
- **Market Data Access**: Historical price and volume data with customizable date ranges
- **Robust Implementation**: Built-in caching, retry mechanisms, and error handling

## 🚀 Quick Start

### Basic Usage

```python
from thaifin.sources.thai_securities_data.stock import ThaiSecuritiesStock

# List all available stock symbols
symbols = ThaiSecuritiesStock.list_symbol()
print(f"Available stocks: {len(symbols)}")

# Search for stocks by company name (supports fuzzy matching)
ptt_stocks = ThaiSecuritiesStock.search('PTT', limit=5)
for stock in ptt_stocks:
    print(f"{stock.symbol}: {stock.company_name}")

# Create a stock instance
stock = ThaiSecuritiesStock('PTT')
print(f"Company: {stock.company_name}")
print(f"Sector: {stock.sector}")
```

### Financial Data Analysis

```python
# Get quarterly financial data
quarterly_df = stock.quarter_dataframe
print(quarterly_df.head())

# Get yearly financial data
yearly_df = stock.yearly_dataframe
print(yearly_df.head())

# Analyze revenue trend
revenue_data = yearly_df['revenue'].dropna()
print(f"Revenue growth: {revenue_data.pct_change().iloc[-1]:.2%}")
```

### Market Data Access

```python
# Get historical market data
market_data = stock.get_market_data(
    start_date='2023-01-01', 
    end_date='2023-12-31'
)

# Analyze price performance
if 'close_price' in market_data.columns:
    price_return = market_data['close_price'].pct_change().cumsum().iloc[-1]
    print(f"2023 Price Return: {price_return:.2%}")
```

## 📊 Available Data

### Financial Metrics (Quarterly & Yearly)

- **Revenue & Profitability**: revenue, gross_profit, net_profit, ebitda
- **Margins**: gross_margin, net_margin, operating_margin
- **Financial Position**: total_assets, total_equity, total_debt, cash
- **Ratios**: debt_to_equity, return_on_equity, return_on_assets, current_ratio
- **Per Share Data**: earnings_per_share, book_value_per_share, dividend_per_share
- **Growth Rates**: revenue_growth_yoy, net_profit_growth_yoy, eps_growth_yoy
- **Cash Flow**: operating_cash_flow, investing_cash_flow, financing_cash_flow
- **Market Data**: market_cap, enterprise_value, price_to_earnings, ev_to_ebitda

### Market Data

- **Price Data**: open_price, high_price, low_price, close_price, adj_close
- **Volume Data**: volume, value (trading value in THB)
- **Market Metrics**: market_cap, shares_outstanding

### Company Information

- **Basic Info**: symbol, name_th, name_en, sector, industry, market
- **Corporate Data**: registered_capital, paid_up_capital, par_value
- **Trading Info**: ipo_date, listing_date, trading_status
- **Contact**: address, phone, website

## 🏗️ Architecture

### API Client (`api.py`)
- **Caching**: TTLCache with 24-hour expiration for financial data, 6-hour for market data
- **Retry Logic**: 3 attempts with exponential backoff (4-10 seconds)
- **Error Handling**: Comprehensive HTTP error handling with meaningful messages

### Data Models (`model.py`)
- **Pydantic Models**: Type-safe data validation and parsing
- **Flexible Schema**: Optional fields accommodate varying data availability
- **DateTime Support**: Proper handling of date/time fields

### Stock Interface (`stock.py`)
- **Familiar API**: Similar interface to main ThaiFin Stock class
- **Pandas Integration**: All data returned as pandas DataFrames
- **Search Functionality**: Fuzzy matching for Thai and English company names

## 🔧 Configuration

### Environment Variables
No environment variables required - the API uses publicly accessible endpoints.

### Caching Configuration
```python
# Default cache settings (can be customized)
@cached(cache=TTLCache(maxsize=12345, ttl=24 * 60 * 60))  # 24 hours
def get_financial_data(...):
    ...

@cached(cache=TTLCache(maxsize=1000, ttl=6 * 60 * 60))   # 6 hours
def get_market_data(...):
    ...
```

### Retry Configuration
```python
@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=4, max=10), 
    reraise=True
)
```

## 📝 API Reference

### ThaiSecuritiesStock Class

#### Class Methods
- `search(company_name: str, limit: int = 5) -> List[ThaiSecuritiesStock]`
- `list_symbol() -> List[str]`
- `find_symbol(symbol: str) -> Optional[StockBasicInfo]`

#### Instance Properties
- `symbol: str` - Stock symbol
- `company_name: str` - English company name
- `thai_company_name: str` - Thai company name
- `sector: Optional[str]` - Company sector
- `quarter_dataframe: pd.DataFrame` - Quarterly financial data
- `yearly_dataframe: pd.DataFrame` - Yearly financial data

#### Instance Methods
- `get_market_data(start_date: Optional[str], end_date: Optional[str]) -> pd.DataFrame`

### API Functions

#### Stock Data
- `get_stock_list() -> StockListResponse`
- `get_stock_info(symbol: str) -> ThaiSecuritiesDataResponse`

#### Financial Data
- `get_financial_data(symbol: str, period: Optional[str]) -> FinancialDataResponse`

#### Market Data
- `get_market_data(symbol: str, start_date: Optional[str], end_date: Optional[str]) -> ThaiSecuritiesDataResponse`

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pytest tests/test_thai_securities_data.py -v

# Run with coverage
pytest tests/test_thai_securities_data.py --cov=thaifin.sources.thai_securities_data

# Run integration example
python tests/test_thai_securities_data.py
```

### Test Structure
- **Unit Tests**: Mock-based testing for individual components
- **Integration Tests**: Real API call validation (when available)
- **Usage Examples**: Demonstration of common use cases

## 📈 Example Analysis

### Financial Health Check
```python
stock = ThaiSecuritiesStock('PTT')
yearly_data = stock.yearly_dataframe

# Latest year metrics
latest = yearly_data.iloc[-1]
print(f"ROE: {latest['return_on_equity']:.2f}%")
print(f"ROA: {latest['return_on_assets']:.2f}%")
print(f"D/E Ratio: {latest['debt_to_equity']:.2f}")
print(f"Net Margin: {latest['net_margin']:.2f}%")
```

### Growth Analysis
```python
# 5-year revenue CAGR
revenue_data = yearly_data['revenue'].dropna().tail(5)
if len(revenue_data) >= 2:
    years = len(revenue_data) - 1
    cagr = (revenue_data.iloc[-1] / revenue_data.iloc[0]) ** (1/years) - 1
    print(f"Revenue CAGR ({years} years): {cagr:.2%}")
```

### Sector Comparison
```python
# Compare multiple stocks
symbols = ['PTT', 'PTTEP', 'BANPU', 'TOP']
comparison = []

for symbol in symbols:
    try:
        stock = ThaiSecuritiesStock(symbol)
        latest = stock.yearly_dataframe.iloc[-1]
        comparison.append({
            'Symbol': symbol,
            'ROE': latest.get('return_on_equity', 'N/A'),
            'ROA': latest.get('return_on_assets', 'N/A'),
            'Net Margin': latest.get('net_margin', 'N/A')
        })
    except Exception as e:
        print(f"Error with {symbol}: {e}")

comparison_df = pd.DataFrame(comparison)
print(comparison_df)
```

## 🔄 Integration with Main ThaiFin

This Thai Securities Data source can be used alongside the main ThaiFin library:

```python
# Use both data sources for comparison
from thaifin import Stock as FinnomenaStock
from thaifin.sources.thai_securities_data.stock import ThaiSecuritiesStock

# Get data from both sources
finnomena_stock = FinnomenaStock('PTT')
thai_sec_stock = ThaiSecuritiesStock('PTT')

# Compare data quality and coverage
finn_data = finnomena_stock.yearly_dataframe
thai_data = thai_sec_stock.yearly_dataframe

print(f"Finnomena years: {len(finn_data)}")
print(f"Thai Securities years: {len(thai_data)}")
```

## 🚧 Development Notes

### Adding New Endpoints
1. Add new function to `api.py` with proper caching and retry
2. Create corresponding response model in `model.py`
3. Add method to `ThaiSecuritiesStock` class if needed
4. Update tests and documentation

### Error Handling
- All API calls include comprehensive error handling
- Meaningful error messages for debugging
- Graceful degradation when data is unavailable

### Performance Considerations
- Use appropriate cache TTL for different data types
- Monitor API rate limits and adjust retry strategies
- Consider implementing request queuing for bulk operations

## 📚 Further Reading

- [ThaiFin Main Documentation](../../README.md)
- [Finnomena Source Implementation](../finnomena/)
- [Sample Notebook](../../samples/thai_securities_data_demo.ipynb)
- [Test Examples](../../tests/test_thai_securities_data.py)
