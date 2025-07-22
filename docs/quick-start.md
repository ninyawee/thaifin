# 🚀 Quick Start Guide

## Installation

```bash
# Pick one ✨
$ pip install thaifin
$ conda install thaifin
```

## Basic Usage

### Import ThaiFin

```python
from thaifin import Stock, Stocks
```

### 3-Line Access to Stock Data

```python
# 1. Create stock instance
stock = Stock('PTT')

# 2. Get quarterly financial data
quarterly_data = stock.quarter_dataframe

# 3. Get yearly financial data  
yearly_data = stock.yearly_dataframe
```

### Collection Operations

```python
# Search stocks (smart detection: Thai/English)
results = Stocks.search('ธนาคาร')  # Thai: finds banks
results = Stocks.search('bank')   # English: finds banks

# List all stock symbols
all_symbols = Stocks.list()  # ['PTT', 'KBANK', 'SCB', ...]

# Get detailed stock information
stock_df = Stocks.list_with_names()

# Filter by sector or market
banking_stocks = Stocks.filter_by_sector('Banking')
mai_stocks = Stocks.filter_by_market('mai')
```

### Language Support

```python
# English mode
stock_en = Stock('PTT', language='en')
print(stock_en.company_name)  # "PTT PUBLIC COMPANY LIMITED"

# Thai mode  
stock_th = Stock('PTT', language='th')
print(stock_th.company_name)  # "บริษัท ปตท. จำกัด (มหาชน)"
```

## Key Features

- 🌐 **Dual Language Support**: English and Thai
- 📊 **10+ Years of Data**: Comprehensive historical financial data
- 🔍 **Smart Search**: Auto-detects Thai/English queries
- ⚡ **Fast & Reliable**: Built-in caching and auto-retry
- 🐼 **Pandas Integration**: Returns familiar DataFrame objects
- 🏗️ **Clean API**: Dual-class architecture for different use cases

## Next Steps

- Read the [User Guide](user-guide.md) for detailed examples
- Explore the [API Reference](api-reference.md) for complete documentation
- Check out [Features](features.md) for advanced capabilities
- Browse [Examples](examples.md) for real-world use cases
