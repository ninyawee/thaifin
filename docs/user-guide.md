# 📖 User Guide

## Overview

ThaiFin is a Python library that provides easy access to Thai stock fundamental data spanning 10+ years. This guide will walk you through all the features with practical examples.

## 🎯 Core Classes

### Two Main Classes

- **`Stock`** - For working with individual stocks (company info, financial data)
- **`Stocks`** - For working with multiple stocks (search, list, filter)

### Language Support

- **English** (`language='en'`) - Company names and column names in English
- **Thai** (`language='th'`) - Company names and column names in Thai

---

## 🚀 Getting Started

### Installation

```bash
pip install thaifin
```

### Basic Import

```python
from thaifin import Stock, Stocks
import pandas as pd
```

---

## 📋 Working with Multiple Stocks (`Stocks` Class)

### 1. Smart Search

The search function automatically detects Thai vs English and finds relevant stocks:

```python
# Thai search - finds banks
bank_stocks = Stocks.search('ธนาคาร', limit=5)
for stock in bank_stocks:
    print(f"📈 {stock.symbol}: {stock.company_name}")

# English search - finds energy companies  
energy_stocks = Stocks.search('energy', limit=3)
for stock in energy_stocks:
    print(f"⚡ {stock.symbol}: {stock.company_name}")

# Symbol search - finds CP-related stocks
cp_stocks = Stocks.search('cp', limit=5)
for stock in cp_stocks:
    print(f"🏢 {stock.symbol}: {stock.company_name}")
```

### 2. List All Stocks

```python
# Get all stock symbols
all_symbols = Stocks.list()
print(f"📊 Total stocks: {len(all_symbols)}")
print(f"🔤 First 10: {all_symbols[:10]}")

# Get detailed information with company names
stocks_df = Stocks.list_with_names(language='en')
print(stocks_df.head())

# Thai version
stocks_df_th = Stocks.list_with_names(language='th')
print(stocks_df_th.head())
```

### 3. Filter by Industry Sector

```python
# See all available sectors
df_all = Stocks.list_with_names()
sectors = df_all['sector'].value_counts()
print("🏭 Available sectors:")
for sector, count in sectors.head(10).items():
    print(f"   • {sector}: {count} companies")

# Filter banking stocks
banking_stocks = Stocks.filter_by_sector('Banking')
print(f"🏦 Banking stocks: {banking_stocks}")

# Filter energy stocks  
energy_stocks = Stocks.filter_by_sector('Energy')
print(f"⚡ Energy stocks: {energy_stocks[:10]} ...")
```

### 4. Filter by Market

```python
# See market distribution
markets = df_all['market'].value_counts()
print("🏛️ Market distribution:")
for market, count in markets.items():
    print(f"   • {market}: {count} stocks")

# Filter SET stocks
set_stocks = Stocks.filter_by_market('SET')
print(f"📈 SET stocks: {len(set_stocks)} total")

# Filter mai stocks
mai_stocks = Stocks.filter_by_market('mai')
print(f"🌱 mai stocks: {len(mai_stocks)} total")
```

---

## 🏢 Working with Individual Stocks (`Stock` Class)

### 1. Basic Company Information

```python
# Create stock instance (English)
stock_en = Stock('PTT', language='en')
print("🇺🇸 PTT Company Info (English):")
print(f"   📝 Symbol: {stock_en.symbol}")
print(f"   🏢 Company: {stock_en.company_name}")
print(f"   🏭 Industry: {stock_en.industry}")
print(f"   📊 Sector: {stock_en.sector}")
print(f"   🏛️ Market: {stock_en.market}")
print(f"   🌐 Website: {stock_en.website}")

# Create stock instance (Thai)
stock_th = Stock('PTT', language='th')
print("\n🇹🇭 PTT Company Info (Thai):")
print(f"   📝 Symbol: {stock_th.symbol}")
print(f"   🏢 Company: {stock_th.company_name}")
print(f"   🏭 Industry: {stock_th.industry}")
print(f"   📊 Sector: {stock_th.sector}")
print(f"   🏛️ Market: {stock_th.market}")
```

### 2. Quarterly Financial Data

```python
# Get quarterly data (English)
quarterly_en = stock_en.quarter_dataframe
print("📈 Quarterly Financial Data (English):")
print(f"   📊 Total quarters: {len(quarterly_en)}")
print(f"   📅 Date range: {quarterly_en.index.min()} to {quarterly_en.index.max()}")

# Display recent data
print("\n🔍 Recent 5 quarters:")
print(quarterly_en.tail())

# Get quarterly data (Thai)
quarterly_th = stock_th.quarter_dataframe  
print("\n📈 Quarterly Financial Data (Thai):")

# Focus on key metrics
key_cols = ['รายได้รวม', 'กำไรสุทธิ', 'กำไรต่อหุ้น (EPS)', 'ROE (%)', 'ROA (%)']
available_cols = [col for col in key_cols if col in quarterly_th.columns]
print("\n🔍 Key metrics (recent 8 quarters):")
print(quarterly_th[available_cols].tail(8))
```

### 3. Yearly Financial Data

```python
# Get yearly data (English)
yearly_en = stock_en.yearly_dataframe
print("📊 Yearly Financial Data (English):")
print(f"   📊 Total years: {len(yearly_en)}")
print(f"   📅 Date range: {yearly_en.index.min()} to {yearly_en.index.max()}")

# Display recent years
print("\n🔍 Recent 5 years:")
print(yearly_en.tail())

# Get yearly data (Thai)
yearly_th = stock_th.yearly_dataframe
print("\n📊 Yearly Financial Data (Thai):")

# Focus on key yearly metrics
yearly_cols = ['รายได้รวม', 'กำไรสุทธิ', 'กำไรต่อหุ้น (EPS)', 'ROE (%)', 'อัตรากำไรสุทธิ (%)']
available_yearly = [col for col in yearly_cols if col in yearly_th.columns]
print("\n🔍 Key yearly metrics (recent 5 years):")
print(yearly_th[available_yearly].tail())
```

### 4. Analyzing Specific Columns

```python
# Show all available columns (Thai)
print("🇹🇭 All available columns in quarterly data:")
for i, col in enumerate(quarterly_th.columns, 1):
    print(f"   {i:2d}. {col}")

# Analyze revenue and profit
if 'รายได้รวม' in quarterly_th.columns and 'กำไรสุทธิ' in quarterly_th.columns:
    print("\n💰 Revenue and Profit Analysis (recent 5 quarters):")
    profit_analysis = quarterly_th[['รายได้รวม', 'กำไรสุทธิ', 'อัตรากำไรสุทธิ (%)']].tail(5)
    print(profit_analysis.round(2))

# Analyze financial ratios
ratio_cols = ['ROE (%)', 'ROA (%)', 'หนี้สิน/ทุน (เท่า)', 'P/E (เท่า)']
available_ratios = [col for col in ratio_cols if col in quarterly_th.columns]
if available_ratios:
    print("\n📊 Financial Ratios (recent 8 quarters):")
    ratios = quarterly_th[available_ratios].tail(8)
    print(ratios)
```

---

## 📈 Advanced Analysis Examples

### 1. Growth Trend Analysis

```python
def analyze_growth_trend(symbol, language='th'):
    """Analyze growth trends for a stock"""
    stock = Stock(symbol, language=language)
    print(f"🏢 Growth Analysis: {stock.company_name}")
    
    try:
        yearly_data = stock.yearly_dataframe
        if yearly_data.empty:
            print("⚠️ No yearly data available")
            return
            
        # Use recent 5 years
        recent_data = yearly_data.tail(5)
        print(f"📅 Analysis period: {recent_data.index.min()} to {recent_data.index.max()}")
        
        # Helper function to convert to number
        def safe_convert(value):
            if pd.isna(value) or value == '' or value is None:
                return None
            try:
                return float(str(value).replace(',', ''))
            except (ValueError, TypeError):
                return None
        
        # Revenue growth analysis
        if 'รายได้รวม' in recent_data.columns:
            revenue_data = {}
            for year, value in recent_data['รายได้รวม'].items():
                num_value = safe_convert(value)
                if num_value is not None:
                    revenue_data[year] = num_value
            
            if len(revenue_data) >= 2:
                print("\n💰 Revenue Analysis:")
                for year, revenue in revenue_data.items():
                    print(f"   {year}: {revenue:,.0f} million THB")
                
                # Calculate average growth rate
                revenue_values = list(revenue_data.values())
                first_revenue = revenue_values[0]
                last_revenue = revenue_values[-1]
                years_diff = len(revenue_values) - 1
                
                if first_revenue > 0:
                    growth_rate = ((last_revenue / first_revenue) ** (1/years_diff) - 1) * 100
                    total_change = ((last_revenue / first_revenue) - 1) * 100
                    print(f"   📊 Average growth rate: {growth_rate:.2f}% per year")
                    print(f"   📈 Total change: {total_change:.2f}% over {years_diff} years")
        
        # ROE analysis
        if 'ROE (%)' in recent_data.columns:
            roe_data = {}
            for year, value in recent_data['ROE (%)'].items():
                num_value = safe_convert(value)
                if num_value is not None:
                    roe_data[year] = num_value
            
            if roe_data:
                roe_values = list(roe_data.values())
                avg_roe = sum(roe_values) / len(roe_values)
                max_roe = max(roe_values)
                min_roe = min(roe_values)
                print(f"\n📊 ROE Analysis:")
                print(f"   📈 Average ROE: {avg_roe:.2f}%")
                print(f"   🔺 Maximum ROE: {max_roe:.2f}%")
                print(f"   🔻 Minimum ROE: {min_roe:.2f}%")
                
    except Exception as e:
        print(f"❌ Error: {e}")

# Example usage
analyze_growth_trend('PTT')
```

### 2. Sector Comparison

```python
def compare_sector_performance(sector_name, top_n=5):
    """Compare top stocks in a sector"""
    print(f"🏭 Sector Performance: {sector_name}")
    
    # Get stocks in sector
    sector_stocks = Stocks.filter_by_sector(sector_name)
    print(f"📊 Total stocks in {sector_name}: {len(sector_stocks)}")
    
    # Analyze top stocks
    stock_data = []
    for symbol in sector_stocks[:top_n]:
        try:
            stock = Stock(symbol, language='th')
            yearly = stock.yearly_dataframe
            if not yearly.empty:
                latest_year = yearly.tail(1)
                if 'รายได้รวม' in latest_year.columns:
                    revenue = latest_year['รายได้รวม'].iloc[0]
                    stock_data.append({
                        'Symbol': symbol,
                        'Company': stock.company_name,
                        'Latest Revenue': revenue
                    })
        except:
            continue
    
    if stock_data:
        df = pd.DataFrame(stock_data)
        print(f"\n🔍 Top {len(df)} stocks with data:")
        print(df)

# Example usage
compare_sector_performance('Banking', top_n=5)
```

---

## 💡 Best Practices

### 1. Error Handling

Always use try-except when working with financial data:

```python
def safe_get_stock_data(symbol):
    try:
        stock = Stock(symbol)
        quarterly = stock.quarter_dataframe
        
        if quarterly.empty:
            print(f"⚠️ No data available for {symbol}")
            return None
            
        return quarterly
        
    except Exception as e:
        print(f"❌ Error getting data for {symbol}: {e}")
        return None

# Usage
data = safe_get_stock_data('PTT')
if data is not None:
    print("✅ Data retrieved successfully")
```

### 2. Data Validation

Check data quality before analysis:

```python
def validate_financial_data(df, required_cols):
    """Validate that DataFrame has required columns and data"""
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"⚠️ Missing columns: {missing_cols}")
        return False
    
    # Check for sufficient data
    if len(df) < 4:  # Less than 1 year of quarterly data
        print("⚠️ Insufficient data for analysis")
        return False
        
    return True

# Usage
required_columns = ['รายได้รวม', 'กำไรสุทธิ', 'ROE (%)']
if validate_financial_data(quarterly_th, required_columns):
    print("✅ Data validation passed")
    # Proceed with analysis
```

### 3. Performance Tips

- Use caching for repeated requests (built-in with ThaiFin)
- Filter data early to reduce memory usage
- Process stocks in batches for large datasets

```python
# Efficient batch processing
def process_stocks_in_batches(stock_symbols, batch_size=10):
    results = []
    for i in range(0, len(stock_symbols), batch_size):
        batch = stock_symbols[i:i+batch_size]
        print(f"📊 Processing batch {i//batch_size + 1}: {len(batch)} stocks")
        
        for symbol in batch:
            try:
                stock = Stock(symbol)
                # Process stock data here
                results.append(symbol)
            except:
                continue
                
    return results
```

---

## 🎯 Complete Examples

### Portfolio Analysis

```python
def analyze_portfolio(symbols, language='th'):
    """Analyze a portfolio of stocks"""
    print("📊 Portfolio Analysis")
    print("=" * 50)
    
    portfolio_data = []
    
    for symbol in symbols:
        try:
            stock = Stock(symbol, language=language)
            yearly = stock.yearly_dataframe
            
            if not yearly.empty:
                latest = yearly.tail(1)
                data = {
                    'Symbol': symbol,
                    'Company': stock.company_name,
                    'Sector': stock.sector,
                    'Market': stock.market
                }
                
                # Add financial metrics if available
                if 'รายได้รวม' in latest.columns:
                    data['Revenue'] = latest['รายได้รวม'].iloc[0]
                if 'ROE (%)' in latest.columns:
                    data['ROE'] = latest['ROE (%)'].iloc[0]
                    
                portfolio_data.append(data)
                
        except Exception as e:
            print(f"⚠️ Error processing {symbol}: {e}")
    
    if portfolio_data:
        df = pd.DataFrame(portfolio_data)
        print(f"\n✅ Successfully analyzed {len(df)} stocks:")
        print(df)
        
        # Sector distribution
        if 'Sector' in df.columns:
            print(f"\n🏭 Sector Distribution:")
            sector_dist = df['Sector'].value_counts()
            for sector, count in sector_dist.items():
                print(f"   • {sector}: {count} stocks")
    
    return portfolio_data

# Example portfolio
my_portfolio = ['PTT', 'KBANK', 'SCB', 'CPALL', 'AOT']
portfolio_analysis = analyze_portfolio(my_portfolio)
```

This user guide provides comprehensive examples and best practices for using ThaiFin effectively!
