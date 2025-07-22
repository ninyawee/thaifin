# 🔧 API Reference

## Classes Overview

ThaiFin provides two main classes for different use cases:

- **`Stock`** - Individual stock operations (company info, financial data)
- **`Stocks`** - Collection operations (search, list, filter)

---

## `Stocks` Class - Collection Operations

### Methods

#### `search(query, limit=None, language='auto')`

Smart search for stocks by company name or symbol with automatic language detection.

**Parameters:**
- `query` (str): Search term (Thai or English)
- `limit` (int, optional): Maximum number of results
- `language` (str): Language mode ('en', 'th', 'auto')

**Returns:** List[Stock] - List of matching Stock objects

**Examples:**
```python
# Thai search
thai_results = Stocks.search('ธนาคาร', limit=5)

# English search  
eng_results = Stocks.search('energy', limit=3)

# Symbol search
cp_stocks = Stocks.search('cp')
```

#### `list(language='en')`

Get all available stock symbols.

**Parameters:**
- `language` (str): Language mode ('en', 'th')

**Returns:** List[str] - List of stock symbols

**Example:**
```python
all_symbols = Stocks.list()
# ['PTT', 'KBANK', 'SCB', 'BBL', ...]
```

#### `list_with_names(language='en')`

Get detailed stock information as DataFrame.

**Parameters:**
- `language` (str): Language mode ('en', 'th')

**Returns:** pandas.DataFrame - DataFrame with columns: symbol, name, industry, sector, market

**Example:**
```python
df = Stocks.list_with_names(language='th')
print(df.head())
```

#### `filter_by_sector(sector, language='en')`

Filter stocks by industry sector.

**Parameters:**
- `sector` (str): Sector name (e.g., 'Banking', 'Energy')
- `language` (str): Language mode ('en', 'th')

**Returns:** List[str] - List of stock symbols in the sector

**Example:**
```python
banking_stocks = Stocks.filter_by_sector('Banking')
```

#### `filter_by_market(market, language='en')`

Filter stocks by market.

**Parameters:**
- `market` (str): Market name ('SET', 'mai')
- `language` (str): Language mode ('en', 'th')

**Returns:** List[str] - List of stock symbols in the market

**Example:**
```python
mai_stocks = Stocks.filter_by_market('mai')
```

---

## `Stock` Class - Individual Operations

### Constructor

#### `Stock(symbol, language='en')`

Create a Stock instance for individual stock operations.

**Parameters:**
- `symbol` (str): Stock symbol (e.g., 'PTT', 'KBANK')
- `language` (str): Language mode ('en', 'th')

**Example:**
```python
stock = Stock('PTT', language='en')
```

### Properties

#### Company Information

| Property | Type | Description |
|----------|------|-------------|
| `symbol` | str | Stock symbol |
| `company_name` | str | Company name (language-specific) |
| `industry` | str | Industry classification |
| `sector` | str | Sector classification |
| `market` | str | Market (SET/mai) |
| `website` | str | Company website URL |

**Examples:**
```python
stock = Stock('PTT', language='en')
print(f"Company: {stock.company_name}")
print(f"Sector: {stock.sector}")
print(f"Industry: {stock.industry}")
print(f"Market: {stock.market}")
```

#### Financial Data

| Property | Type | Description |
|----------|------|-------------|
| `quarter_dataframe` | pandas.DataFrame | Quarterly financial data |
| `yearly_dataframe` | pandas.DataFrame | Yearly financial data |

**Examples:**
```python
# Get quarterly data
quarterly = stock.quarter_dataframe
print(quarterly.tail())

# Get yearly data
yearly = stock.yearly_dataframe
print(yearly.tail())
```

---

## Financial Data Structure

### Quarterly Financial Data Columns

The `quarter_dataframe` contains 38+ financial metrics:

#### Basic Information
- `security_id` / `รหัสหลักทรัพย์` - Stock symbol
- `fiscal` / `ปีการเงิน` - Fiscal year
- `quarter` / `ไตรมาส` - Quarter

#### Profitability Metrics
- `revenue` / `รายได้รวม` - Total revenue (millions THB)
- `net_profit` / `กำไรสุทธิ` - Net profit (millions THB)
- `gross_profit` / `กำไรขั้นต้น` - Gross profit (millions THB)
- `gpm` / `อัตรากำไรขั้นต้น (%)` - Gross profit margin (%)
- `npm` / `อัตรากำไรสุทธิ (%)` - Net profit margin (%)

#### Financial Ratios
- `roe` / `ROE (%)` - Return on equity (%)
- `roa` / `ROA (%)` - Return on assets (%)
- `debt_to_equity` / `หนี้สิน/ทุน (เท่า)` - Debt to equity ratio
- `price_earning_ratio` / `P/E (เท่า)` - Price to earnings ratio

#### Per Share Metrics
- `earning_per_share` / `กำไรต่อหุ้น (EPS)` - Earnings per share (THB)
- `book_value_per_share` / `มูลค่าหุ้นทางบัญชีต่อหุ้น (บาท)` - Book value per share (THB)
- `dividend_yield` / `อัตราส่วนเงินปันผลตอบแทน (%)` - Dividend yield (%)

#### Cash Flow
- `operating_activities` / `กระแสเงินสด จากการดำเนินงาน` - Operating cash flow
- `investing_activities` / `กระแสเงินสด จากการลงทุน` - Investing cash flow
- `financing_activities` / `กระแสเงินสด จากกิจกรรมทางการเงิน` - Financing cash flow

#### Growth Metrics (Year-over-Year)
- `revenue_yoy` / `รายได้รวม การเติบโตเทียบปีก่อนหน้า (%)` - Revenue YoY growth (%)
- `net_profit_yoy` / `กำไรสุทธิ การเติบโตเทียบปีก่อนหน้า (%)` - Net profit YoY growth (%)
- `earning_per_share_yoy` / `EPS การเติบโตเทียบปีก่อนหน้า (%)` - EPS YoY growth (%)

#### Market Data
- `close` / `ราคาล่าสุด (บาท)` - Latest closing price (THB)
- `mkt_cap` / `มูลค่าหลักทรัพย์ตามราคาตลาด (ล้านบาท)` - Market capitalization (millions THB)
- `ev_per_ebit_da` / `EV / EBITDA` - Enterprise value to EBITDA ratio

---

## Language Support

### English Mode (`language='en'`)
- Company names in English
- Financial data column names in English
- Returns Pydantic models with English field names

### Thai Mode (`language='th'`)
- Company names in Thai
- Financial data column names in Thai
- Returns dictionaries with authentic Thai field names

### Auto Detection (`language='auto'`)
- Available only for `Stocks.search()`
- Automatically detects Thai vs English queries
- Optimizes search results based on language

---

## Error Handling

### Common Exceptions

```python
try:
    stock = Stock('INVALID_SYMBOL')
    data = stock.quarter_dataframe
except Exception as e:
    print(f"Error: {e}")
```

### Best Practices

1. **Always use try-except** when accessing financial data
2. **Check if DataFrame is empty** before processing
3. **Validate stock symbols** using `Stocks.list()` first
4. **Handle missing data** gracefully with pandas methods

### Example with Error Handling

```python
def safe_get_stock_data(symbol):
    try:
        stock = Stock(symbol)
        quarterly = stock.quarter_dataframe
        
        if quarterly.empty:
            print(f"No quarterly data available for {symbol}")
            return None
            
        return quarterly
        
    except Exception as e:
        print(f"Error getting data for {symbol}: {e}")
        return None
```
