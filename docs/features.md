# ✨ Features Overview

## 🎯 Core Capabilities

### Dual-Class Architecture

ThaiFin provides two specialized classes for different use cases:

- **`Stock`** - Individual stock operations with deep company and financial data access
- **`Stocks`** - Collection operations for search, discovery, and filtering

### 🌐 Comprehensive Language Support

#### Bilingual Data Access
- **English Mode**: Company names, financial metrics, and column headers in English
- **Thai Mode**: Authentic Thai company names and financial terminology
- **Auto-Detection**: Smart language detection for search queries

#### Examples
```python
# English mode
stock_en = Stock('PTT', language='en')
print(stock_en.company_name)  # "PTT PUBLIC COMPANY LIMITED"

# Thai mode
stock_th = Stock('PTT', language='th') 
print(stock_th.company_name)  # "บริษัท ปตท. จำกัด (มหาชน)"
```

---

## 📊 Data Coverage

### 📈 Historical Depth
- **10+ Years** of comprehensive financial data
- **Quarterly Reports** dating back to 2009+
- **Annual Summaries** with full fiscal year data
- **Real-time Updates** with automatic data refresh

### 🏢 Market Coverage
- **SET (Stock Exchange of Thailand)** - Main board listings
- **mai (Market for Alternative Investment)** - Growth companies
- **800+ Listed Companies** across all sectors
- **Complete Universe** of Thai public companies

### 📋 Financial Metrics (38+ Data Points)

#### Core Financial Data
- Revenue, Net Profit, Gross Profit
- Cash Flow (Operating, Investing, Financing)
- Balance Sheet items (Assets, Equity, Debt)

#### Performance Ratios
- ROE (Return on Equity)
- ROA (Return on Assets) 
- Debt-to-Equity Ratio
- Gross/Net Profit Margins

#### Per-Share Metrics
- Earnings Per Share (EPS)
- Book Value Per Share
- Dividend Yield

#### Market Valuation
- Market Capitalization
- Price-to-Earnings (P/E) Ratio
- Price-to-Book (P/B) Ratio
- EV/EBITDA

#### Growth Metrics
- Year-over-Year Growth (Revenue, Profit, EPS)
- Quarter-over-Quarter Growth
- Historical Growth Trends

---

## 🔍 Advanced Search & Discovery

### Smart Search Engine

#### Multi-Language Query Processing
```python
# Thai language search
thai_banks = Stocks.search('ธนาคาร')  # Finds all banks
jasmine = Stocks.search('จัสมิน')     # Finds Jasmine companies

# English language search  
energy_cos = Stocks.search('energy')  # Energy sector companies
banks = Stocks.search('bank')         # Banking companies

# Symbol-based search
cp_group = Stocks.search('cp')        # All CP-related stocks
```

#### Fuzzy Matching
- **Intelligent Matching**: Handles typos and variations
- **Partial Matches**: Finds relevant results with incomplete queries  
- **Context Awareness**: Understands Thai and English business terminology

### Filtering & Classification

#### By Industry Sector
```python
# Major sectors available
sectors = [
    'Banking', 'Energy', 'Technology', 'Healthcare',
    'Real Estate', 'Consumer Goods', 'Industrials',
    'Transportation', 'Media & Communications'
]

banking_stocks = Stocks.filter_by_sector('Banking')
energy_stocks = Stocks.filter_by_sector('Energy')
```

#### By Market Listing
```python
# SET main board (large caps)
set_stocks = Stocks.filter_by_market('SET')

# mai (growth/small caps)
mai_stocks = Stocks.filter_by_market('mai')
```

---

## ⚡ Performance & Reliability

### Built-in Caching System
- **24-Hour TTL Cache**: Reduces server load and improves response times
- **Intelligent Refresh**: Automatic cache invalidation for stale data
- **Memory Efficient**: Optimized caching with `cachetools`

### Robust Error Handling
- **Auto-Retry Logic**: Exponential backoff with `tenacity`
- **Graceful Failures**: Continues operation despite individual stock errors
- **Connection Resilience**: Handles network interruptions seamlessly

### Performance Optimizations
```python
# Fast bulk operations
all_symbols = Stocks.list()  # Millisecond response time
detailed_list = Stocks.list_with_names()  # Cached company metadata

# Efficient individual lookups
stock = Stock('PTT')  # Cached company information
quarterly = stock.quarter_dataframe  # Cached financial data
```

---

## 🐼 Pandas Integration

### Native DataFrame Support
All financial data returns as pandas DataFrames for immediate analysis:

```python
# Get quarterly data as DataFrame
quarterly_df = stock.quarter_dataframe

# Immediate analysis capabilities
quarterly_df.describe()  # Statistical summary
quarterly_df.plot()      # Quick visualization
quarterly_df.to_csv()    # Export to CSV
quarterly_df.groupby()   # Advanced grouping
```

### Time Series Ready
- **DateTime Index**: All data indexed by fiscal period
- **Time Series Analysis**: Ready for pandas time series operations
- **Period Alignment**: Consistent quarterly/yearly periods across stocks

---

## 🛡️ Data Quality & Validation

### Data Sources
- **Finnomena API**: Primary source for financial statements
- **Thai Securities Data**: Official company metadata and classifications
- **Cross-Validation**: Multiple source verification for critical data points

### Quality Assurance
- **Pydantic Models**: Type validation and data integrity
- **Automatic Cleaning**: Standardized number formatting and null handling
- **Consistency Checks**: Validation across quarterly and yearly aggregations

### Error Detection
```python
# Built-in data validation
try:
    stock = Stock('INVALID')
    data = stock.quarter_dataframe
except Exception as e:
    print(f"Handled error: {e}")

# Data availability checking
if not stock.quarter_dataframe.empty:
    # Safe to proceed with analysis
    analyze_financial_data(stock.quarter_dataframe)
```

---

## 🔧 Developer Experience

### Modern Python Standards
- **Python 3.11+**: Leverages latest Python performance improvements
- **Type Hints**: Full type annotation for better IDE support
- **Async Ready**: Built for modern async/await patterns

### Dependency Management
- **Minimal Dependencies**: Only essential, well-maintained packages
- **Version Pinning**: Stable dependency versions for reliability
- **uv Compatible**: Works with modern Python package managers

### Documentation & Examples
- **Comprehensive Docs**: Detailed API reference and user guides
- **Real-World Examples**: Practical code samples for common use cases
- **Interactive Notebooks**: Jupyter notebooks with live examples

---

## 🌍 Real-World Applications

### Investment Analysis
```python
# Portfolio optimization
def analyze_portfolio_risk(symbols):
    returns_data = []
    for symbol in symbols:
        stock = Stock(symbol)
        quarterly = stock.quarter_dataframe
        if 'revenue_yoy' in quarterly.columns:
            returns_data.append(quarterly['revenue_yoy'].values)
    return np.corrcoef(returns_data)  # Correlation matrix
```

### Financial Research
```python
# Sector performance comparison
def sector_analysis(sector_name):
    stocks = Stocks.filter_by_sector(sector_name)
    sector_data = []
    
    for symbol in stocks:
        stock = Stock(symbol, language='th')
        yearly = stock.yearly_dataframe
        if not yearly.empty:
            latest_roe = yearly['ROE (%)'].iloc[-1]
            sector_data.append({
                'symbol': symbol,
                'company': stock.company_name,
                'roe': latest_roe
            })
    
    return pd.DataFrame(sector_data).sort_values('roe', ascending=False)
```

### Academic Studies
```python
# Market efficiency studies
def market_trend_analysis():
    all_stocks = Stocks.list()
    market_data = {}
    
    for symbol in all_stocks[:50]:  # Sample analysis
        try:
            stock = Stock(symbol)
            quarterly = stock.quarter_dataframe
            if 'close' in quarterly.columns:
                prices = quarterly['close'].astype(float)
                returns = prices.pct_change().dropna()
                market_data[symbol] = returns.std()  # Volatility
        except:
            continue
    
    return market_data
```

### Automated Screening
```python
# Value investing screens
def value_screen(min_roe=15, max_pe=15):
    """Find undervalued stocks with good returns"""
    candidates = []
    all_symbols = Stocks.list()
    
    for symbol in all_symbols:
        try:
            stock = Stock(symbol, language='th')
            latest = stock.yearly_dataframe.tail(1)
            
            roe = float(latest['ROE (%)'].iloc[0])
            pe = float(latest['P/E (เท่า)'].iloc[0])
            
            if roe >= min_roe and pe <= max_pe:
                candidates.append({
                    'symbol': symbol,
                    'company': stock.company_name,
                    'roe': roe,
                    'pe': pe
                })
        except:
            continue
    
    return pd.DataFrame(candidates).sort_values('roe', ascending=False)
```

---

## 🚀 Advanced Features

### Batch Processing
```python
# Efficient multi-stock analysis
def batch_analysis(symbols, batch_size=10):
    """Process stocks in optimized batches"""
    results = []
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        batch_results = []
        
        for symbol in batch:
            try:
                stock = Stock(symbol)
                # Analysis logic here
                batch_results.append(process_stock(stock))
            except:
                continue
        
        results.extend(batch_results)
        time.sleep(0.1)  # Rate limiting
    
    return results
```

### Custom Metrics Calculation
```python
# Calculate custom financial ratios
def calculate_custom_metrics(stock_symbol):
    """Calculate additional financial metrics"""
    stock = Stock(stock_symbol)
    quarterly = stock.quarter_dataframe
    
    # Custom calculations
    quarterly['revenue_growth_ma'] = quarterly['revenue_yoy'].rolling(4).mean()
    quarterly['profit_stability'] = quarterly['net_profit'].rolling(4).std()
    quarterly['efficiency_ratio'] = quarterly['revenue'] / quarterly['asset']
    
    return quarterly[['revenue_growth_ma', 'profit_stability', 'efficiency_ratio']]
```

### Integration with Analysis Libraries
```python
# Seamless integration with popular libraries
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px

# Quick visualizations
def plot_financial_trends(symbol):
    stock = Stock(symbol)
    yearly = stock.yearly_dataframe
    
    # Matplotlib
    plt.figure(figsize=(12, 6))
    plt.plot(yearly.index, yearly['revenue'], label='Revenue')
    plt.plot(yearly.index, yearly['net_profit'], label='Net Profit')
    plt.legend()
    plt.title(f'{symbol} Financial Trends')
    plt.show()
    
    # Plotly interactive charts
    fig = px.line(yearly, x=yearly.index, y=['revenue', 'net_profit'])
    fig.show()
```

ThaiFin is designed to be the comprehensive solution for Thai stock market data analysis, combining ease of use with powerful capabilities for both beginners and advanced users.
