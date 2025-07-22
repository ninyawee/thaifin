# 📚 ThaiFin Documentation

Welcome to ThaiFin - a Python library providing easy access to Thai stock fundamental data spanning 10+ years.

## 🎯 What is ThaiFin?

ThaiFin democratizes access to Thai financial market data that was previously only available to investment firms. With just 3 lines of code, you can access comprehensive financial data for any Thai public company.

```python
from thaifin import Stock
stock = Stock('PTT')
quarterly_data = stock.quarter_dataframe
```

## 🚀 Quick Navigation

### 📖 Getting Started
- **[Quick Start Guide](quick-start.md)** - Get up and running in minutes
- **[User Guide](user-guide.md)** - Comprehensive guide with practical examples
- **[API Reference](api-reference.md)** - Complete documentation of all classes and methods

### 🔍 Learn More
- **[Features Overview](features.md)** - Detailed overview of all capabilities
- **[Examples](examples.md)** - Real-world code examples and use cases

## 🌟 Key Features

### 🏗️ Dual-Class Architecture
- **`Stock`** - Individual stock operations (company info, financial data)
- **`Stocks`** - Collection operations (search, list, filter)

### 🌐 Comprehensive Language Support
- **English Mode**: Company names and metrics in English
- **Thai Mode**: Authentic Thai company names and financial terminology
- **Smart Search**: Auto-detects Thai vs English queries

### 📊 Rich Financial Data
- **10+ Years** of historical data
- **38+ Financial Metrics** per quarter/year
- **Real-time Updates** with intelligent caching
- **Pandas Integration** for immediate analysis

### ⚡ Performance & Reliability
- **Built-in Caching** (24-hour TTL)
- **Auto-retry Logic** with exponential backoff
- **Robust Error Handling** for production use

## 📋 Core Classes

### `Stocks` Class - Collection Operations

Perfect for discovery and exploration:

```python
from thaifin import Stocks

# Smart search (auto-detects language)
banks = Stocks.search('ธนาคาร', limit=5)  # Thai search
energy = Stocks.search('energy', limit=3)  # English search

# List and filter
all_symbols = Stocks.list()  # All stock symbols
detailed_df = Stocks.list_with_names()  # With company info
banking_stocks = Stocks.filter_by_sector('Banking')  # By sector
mai_stocks = Stocks.filter_by_market('mai')  # By market
```

### `Stock` Class - Individual Operations

Perfect for detailed analysis:

```python
from thaifin import Stock

# Create stock instance with language preference
stock = Stock('PTT', language='th')  # Thai mode

# Company information
print(f"บริษัท: {stock.company_name}")
print(f"กลุ่ม: {stock.sector}")
print(f"อุตสาหกรรม: {stock.industry}")

# Financial data as pandas DataFrames
quarterly = stock.quarter_dataframe  # Quarterly data
yearly = stock.yearly_dataframe      # Yearly data
```

## 📊 Financial Data Coverage

### Data Scope
- **Markets**: SET (main board) and mai (growth companies)
- **Companies**: 800+ listed Thai companies
- **History**: 10+ years of quarterly and yearly data
- **Metrics**: 38+ financial indicators per reporting period

### Key Metrics Available

#### Profitability
- Revenue, Net Profit, Gross Profit
- Profit Margins (Gross, Net)
- ROE, ROA, ROIC

#### Financial Health
- Debt-to-Equity Ratio
- Current Ratio
- Cash Flow (Operating, Investing, Financing)

#### Per-Share Metrics
- Earnings Per Share (EPS)
- Book Value Per Share
- Dividend Yield

#### Market Valuation
- Market Capitalization
- P/E Ratio, P/B Ratio
- EV/EBITDA

#### Growth Metrics
- Year-over-Year Growth (Revenue, Profit, EPS)
- Quarter-over-Quarter Growth

## 🛠️ Installation

```bash
# Choose your preferred method
pip install thaifin
conda install thaifin
```

**Requirements:**
- Python 3.11+
- pandas, requests, and other common data science libraries

## 💡 Usage Examples

### Basic Stock Analysis
```python
from thaifin import Stock

# Analyze PTT's financial performance
ptt = Stock('PTT', language='th')
yearly = ptt.yearly_dataframe

# Focus on profitability trends
profitability = yearly[['รายได้รวม', 'กำไรสุทธิ', 'ROE (%)']].tail(5)
print(profitability)
```

### Sector Comparison
```python
from thaifin import Stocks, Stock

# Get all banking stocks
banks = Stocks.filter_by_sector('Banking')

# Compare their ROE performance
for symbol in banks[:5]:
    stock = Stock(symbol)
    latest_roe = stock.yearly_dataframe['roe'].iloc[-1]
    print(f"{symbol}: {latest_roe:.2f}% ROE")
```

### Investment Screening
```python
# Find undervalued stocks with good fundamentals
def value_screen():
    candidates = []
    for symbol in Stocks.list()[:100]:  # Sample first 100
        try:
            stock = Stock(symbol, language='th')
            latest = stock.yearly_dataframe.tail(1)
            
            roe = float(latest['ROE (%)'].iloc[0])
            pe = float(latest['P/E (เท่า)'].iloc[0])
            
            if roe > 15 and pe < 15:  # High ROE, low P/E
                candidates.append({
                    'symbol': symbol,
                    'company': stock.company_name,
                    'roe': roe,
                    'pe': pe
                })
        except:
            continue
    
    return sorted(candidates, key=lambda x: x['roe'], reverse=True)

value_stocks = value_screen()
```

## 🌐 Language Support Details

### English Mode (`language='en'`)
```python
stock = Stock('PTT', language='en')
print(stock.company_name)  # "PTT PUBLIC COMPANY LIMITED"

# DataFrame columns in English
df = stock.quarter_dataframe
print(df.columns)  # ['revenue', 'net_profit', 'roe', ...]
```

### Thai Mode (`language='th'`)
```python
stock = Stock('PTT', language='th')
print(stock.company_name)  # "บริษัท ปตท. จำกัด (มหาชน)"

# DataFrame columns in Thai
df = stock.quarter_dataframe
print(df.columns)  # ['รายได้รวม', 'กำไรสุทธิ', 'ROE (%)', ...]
```

## 🏆 Why Choose ThaiFin?

### For Investors
- **Comprehensive Data**: 10+ years of detailed financial metrics
- **Easy Analysis**: Pandas DataFrames ready for immediate use
- **Thai Market Focus**: Specialized for Thai stock market nuances

### For Developers
- **Clean API**: Intuitive dual-class design
- **Robust Architecture**: Built-in caching, retry logic, error handling
- **Modern Python**: Python 3.11+ with full type hints

### For Researchers
- **Academic Quality**: Consistent, validated financial data
- **Bulk Operations**: Efficient processing of multiple stocks
- **Export Ready**: Easy integration with analysis workflows

### For Everyone
- **Free & Open**: ISC License - truly open source
- **No API Keys**: Works out of the box with public data
- **Active Development**: Regular updates and improvements

## 📖 Documentation Structure

This documentation is organized into several sections:

1. **[Quick Start](quick-start.md)** - Get ThaiFin running immediately
2. **[User Guide](user-guide.md)** - Detailed walkthrough with examples
3. **[API Reference](api-reference.md)** - Complete technical documentation
4. **[Features](features.md)** - Comprehensive feature overview
5. **[Examples](examples.md)** - Real-world usage patterns

## 🤝 Contributing

ThaiFin is open source and welcomes contributions:

- **Bug Reports**: Found an issue? Please report it!
- **Feature Requests**: Have an idea? We'd love to hear it!
- **Code Contributions**: Pull requests are welcome
- **Documentation**: Help improve these docs

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/circleoncircles/thaifin/issues)
- **Discussions**: Community support and questions
- **Documentation**: This comprehensive guide

## ⚖️ License

ThaiFin is released under the ISC License - free for everyone to use, modify, and distribute.

## 🙏 Acknowledgments

ThaiFin is created by the same author as [PythaiNAV](https://github.com/CircleOnCircles/pythainav), with the mission to democratize access to Thai financial market data.

**Data Sources:**
- Finnomena API for financial statements
- Thai Securities Data for company metadata

---

Ready to get started? Jump to the **[Quick Start Guide](quick-start.md)** and begin exploring Thai stock data in minutes!
