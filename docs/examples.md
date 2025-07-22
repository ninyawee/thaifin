# 💡 Examples

## 🚀 Basic Examples

### Getting Started

```python
from thaifin import Stock, Stocks
import pandas as pd

# Simple 3-line stock data access
stock = Stock('PTT')
quarterly_data = stock.quarter_dataframe
yearly_data = stock.yearly_dataframe
```

### Search and Discovery

```python
# Smart search (auto-detects language)
thai_banks = Stocks.search('ธนาคาร', limit=5)
energy_stocks = Stocks.search('energy', limit=3)
cp_companies = Stocks.search('cp')

# List all stocks
all_symbols = Stocks.list()
print(f"Total stocks: {len(all_symbols)}")

# Get detailed stock information
stocks_df = Stocks.list_with_names(language='th')
print(stocks_df.head())
```

### Language Support

```python
# English mode
stock_en = Stock('PTT', language='en')
print(f"Company: {stock_en.company_name}")
print(f"Sector: {stock_en.sector}")

# Thai mode
stock_th = Stock('PTT', language='th')
print(f"บริษัท: {stock_th.company_name}")
print(f"กลุ่ม: {stock_th.sector}")
```

---

## 📊 Financial Analysis Examples

### Revenue Growth Analysis

```python
def analyze_revenue_growth(symbol, periods=8):
    """Analyze revenue growth over specified periods"""
    stock = Stock(symbol, language='th')
    
    # Get quarterly data
    quarterly = stock.quarter_dataframe
    if quarterly.empty:
        return None
    
    # Focus on revenue data
    if 'รายได้รวม' not in quarterly.columns:
        print(f"No revenue data for {symbol}")
        return None
    
    # Get recent periods
    recent_data = quarterly[['รายได้รวม', 'รายได้รวม การเติบโตเทียบปีก่อนหน้า (%)']].tail(periods)
    
    print(f"📈 Revenue Growth Analysis: {stock.company_name}")
    print("=" * 60)
    
    for period, row in recent_data.iterrows():
        revenue = row['รายได้รวม']
        growth = row['รายได้รวม การเติบโตเทียบปีก่อนหน้า (%)']
        print(f"{period}: {revenue:>10} ล้านบาท (YoY: {growth:>6}%)")
    
    return recent_data

# Example usage
revenue_analysis = analyze_revenue_growth('PTT', periods=8)
```

### Profitability Comparison

```python
def compare_profitability(symbols, language='th'):
    """Compare profitability metrics across multiple stocks"""
    results = []
    
    for symbol in symbols:
        try:
            stock = Stock(symbol, language=language)
            yearly = stock.yearly_dataframe
            
            if not yearly.empty:
                latest = yearly.tail(1)
                
                # Extract key metrics
                data = {
                    'Symbol': symbol,
                    'Company': stock.company_name,
                    'Sector': stock.sector
                }
                
                # Add financial metrics (Thai column names)
                if 'รายได้รวม' in latest.columns:
                    data['Revenue (M THB)'] = latest['รายได้รวม'].iloc[0]
                if 'กำไรสุทธิ' in latest.columns:
                    data['Net Profit (M THB)'] = latest['กำไรสุทธิ'].iloc[0]
                if 'อัตรากำไรสุทธิ (%)' in latest.columns:
                    data['Net Margin (%)'] = latest['อัตรากำไรสุทธิ (%)'].iloc[0]
                if 'ROE (%)' in latest.columns:
                    data['ROE (%)'] = latest['ROE (%)'].iloc[0]
                
                results.append(data)
                
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
    
    if results:
        df = pd.DataFrame(results)
        return df.sort_values('ROE (%)', ascending=False)
    return None

# Compare major banks
banking_stocks = ['KBANK', 'SCB', 'BBL', 'KTB', 'BAY']
profitability_df = compare_profitability(banking_stocks)
print(profitability_df)
```

### Financial Health Assessment

```python
def assess_financial_health(symbol):
    """Comprehensive financial health assessment"""
    stock = Stock(symbol, language='th')
    
    print(f"🏥 Financial Health Assessment: {stock.company_name}")
    print("=" * 70)
    
    # Get latest yearly data
    yearly = stock.yearly_dataframe
    if yearly.empty:
        print("❌ No yearly data available")
        return
    
    latest = yearly.tail(1)
    
    # Profitability Analysis
    print("\n💰 Profitability Metrics:")
    profitability_metrics = [
        ('รายได้รวม', 'Revenue', 'ล้านบาท'),
        ('กำไรสุทธิ', 'Net Profit', 'ล้านบาท'),
        ('อัตรากำไรสุทธิ (%)', 'Net Margin', '%'),
        ('ROE (%)', 'Return on Equity', '%'),
        ('ROA (%)', 'Return on Assets', '%')
    ]
    
    for thai_col, eng_name, unit in profitability_metrics:
        if thai_col in latest.columns:
            value = latest[thai_col].iloc[0]
            print(f"   {eng_name:20}: {value:>10} {unit}")
    
    # Financial Structure
    print("\n🏗️ Financial Structure:")
    structure_metrics = [
        ('หนี้สิน/ทุน (เท่า)', 'Debt-to-Equity', 'times'),
        ('กำไรต่อหุ้น (EPS)', 'Earnings per Share', 'THB'),
        ('มูลค่าหุ้นทางบัญชีต่อหุ้น (บาท)', 'Book Value per Share', 'THB')
    ]
    
    for thai_col, eng_name, unit in structure_metrics:
        if thai_col in latest.columns:
            value = latest[thai_col].iloc[0]
            print(f"   {eng_name:20}: {value:>10} {unit}")
    
    # Market Valuation
    print("\n📊 Market Valuation:")
    market_metrics = [
        ('ราคาล่าสุด (บาท)', 'Current Price', 'THB'),
        ('มูลค่าหลักทรัพย์ตามราคาตลาด (ล้านบาท)', 'Market Cap', 'M THB'),
        ('P/E (เท่า)', 'P/E Ratio', 'times'),
        ('EV / EBITDA', 'EV/EBITDA', 'times')
    ]
    
    for thai_col, eng_name, unit in market_metrics:
        if thai_col in latest.columns:
            value = latest[thai_col].iloc[0]
            print(f"   {eng_name:20}: {value:>10} {unit}")

# Example usage
assess_financial_health('PTT')
```

---

## 🏭 Sector Analysis Examples

### Sector Performance Ranking

```python
def rank_sector_performance():
    """Rank all sectors by average ROE performance"""
    print("🏆 Sector Performance Ranking")
    print("=" * 50)
    
    # Get all stocks with details
    all_stocks_df = Stocks.list_with_names()
    sectors = all_stocks_df['sector'].unique()
    
    sector_performance = []
    
    for sector in sectors:
        if pd.isna(sector) or sector == '-':
            continue
            
        sector_stocks = all_stocks_df[all_stocks_df['sector'] == sector]['symbol'].tolist()
        roe_values = []
        
        for symbol in sector_stocks[:10]:  # Sample first 10 stocks per sector
            try:
                stock = Stock(symbol, language='th')
                yearly = stock.yearly_dataframe
                
                if not yearly.empty and 'ROE (%)' in yearly.columns:
                    latest_roe = yearly['ROE (%)'].tail(1).iloc[0]
                    if pd.notna(latest_roe) and isinstance(latest_roe, (int, float)):
                        roe_values.append(float(latest_roe))
            except:
                continue
        
        if roe_values:
            avg_roe = sum(roe_values) / len(roe_values)
            sector_performance.append({
                'Sector': sector,
                'Average ROE (%)': round(avg_roe, 2),
                'Stocks Analyzed': len(roe_values),
                'Total Stocks': len(sector_stocks)
            })
    
    # Sort by performance
    performance_df = pd.DataFrame(sector_performance)
    performance_df = performance_df.sort_values('Average ROE (%)', ascending=False)
    
    print(f"\n📊 Top Performing Sectors:")
    print(performance_df.head(10))
    
    return performance_df

sector_rankings = rank_sector_performance()
```

### Banking Sector Deep Dive

```python
def banking_sector_analysis():
    """Comprehensive analysis of banking sector"""
    print("🏦 Banking Sector Analysis")
    print("=" * 50)
    
    # Get banking stocks
    banking_stocks = Stocks.filter_by_sector('Banking')
    print(f"📊 Found {len(banking_stocks)} banking stocks")
    
    banking_data = []
    
    for symbol in banking_stocks:
        try:
            stock = Stock(symbol, language='th')
            yearly = stock.yearly_dataframe
            quarterly = stock.quarter_dataframe
            
            if not yearly.empty:
                latest_year = yearly.tail(1)
                latest_quarter = quarterly.tail(1) if not quarterly.empty else None
                
                data = {
                    'Symbol': symbol,
                    'Bank': stock.company_name,
                    'Market': stock.market
                }
                
                # Annual metrics
                if 'รายได้รวม' in latest_year.columns:
                    data['Annual Revenue (B THB)'] = round(float(latest_year['รายได้รวม'].iloc[0]) / 1000, 2)
                if 'กำไรสุทธิ' in latest_year.columns:
                    data['Annual Profit (B THB)'] = round(float(latest_year['กำไรสุทธิ'].iloc[0]) / 1000, 2)
                if 'ROE (%)' in latest_year.columns:
                    data['ROE (%)'] = latest_year['ROE (%)'].iloc[0]
                if 'ROA (%)' in latest_year.columns:
                    data['ROA (%)'] = latest_year['ROA (%)'].iloc[0]
                
                # Latest market data
                if latest_quarter is not None and 'ราคาล่าสุด (บาท)' in latest_quarter.columns:
                    data['Current Price (THB)'] = latest_quarter['ราคาล่าสุด (บาท)'].iloc[0]
                if latest_quarter is not None and 'P/E (เท่า)' in latest_quarter.columns:
                    data['P/E Ratio'] = latest_quarter['P/E (เท่า)'].iloc[0]
                
                banking_data.append(data)
                
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
    
    if banking_data:
        banking_df = pd.DataFrame(banking_data)
        
        print(f"\n💰 Banking Sector Overview:")
        print(banking_df.sort_values('Annual Revenue (B THB)', ascending=False))
        
        # Summary statistics
        print(f"\n📊 Sector Summary:")
        print(f"   Average ROE: {banking_df['ROE (%)'].mean():.2f}%")
        print(f"   Average ROA: {banking_df['ROA (%)'].mean():.2f}%")
        print(f"   Total Revenue: {banking_df['Annual Revenue (B THB)'].sum():.2f} Billion THB")
        
        return banking_df
    
    return None

banking_analysis = banking_sector_analysis()
```

---

## 📈 Investment Strategy Examples

### Value Investing Screen

```python
def value_investing_screen(min_roe=15, max_pe=15, min_revenue=1000):
    """Screen for value investment opportunities"""
    print("💎 Value Investing Screen")
    print("=" * 50)
    print(f"Criteria: ROE ≥ {min_roe}%, P/E ≤ {max_pe}, Revenue ≥ {min_revenue}M THB")
    
    all_symbols = Stocks.list()
    candidates = []
    
    for symbol in all_symbols[:100]:  # Sample first 100 for demo
        try:
            stock = Stock(symbol, language='th')
            yearly = stock.yearly_dataframe
            quarterly = stock.quarter_dataframe
            
            if yearly.empty or quarterly.empty:
                continue
            
            latest_year = yearly.tail(1)
            latest_quarter = quarterly.tail(1)
            
            # Extract criteria values
            roe = latest_year['ROE (%)'].iloc[0] if 'ROE (%)' in latest_year.columns else None
            pe = latest_quarter['P/E (เท่า)'].iloc[0] if 'P/E (เท่า)' in latest_quarter.columns else None
            revenue = latest_year['รายได้รวม'].iloc[0] if 'รายได้รวม' in latest_year.columns else None
            
            # Apply screens
            if (roe and roe >= min_roe and 
                pe and pe <= max_pe and pe > 0 and
                revenue and revenue >= min_revenue):
                
                candidates.append({
                    'Symbol': symbol,
                    'Company': stock.company_name,
                    'Sector': stock.sector,
                    'ROE (%)': round(roe, 2),
                    'P/E Ratio': round(pe, 2),
                    'Revenue (M THB)': round(revenue, 0),
                    'Market': stock.market
                })
                
        except Exception as e:
            continue
    
    if candidates:
        candidates_df = pd.DataFrame(candidates)
        candidates_df = candidates_df.sort_values(['ROE (%)', 'P/E Ratio'], ascending=[False, True])
        
        print(f"\n✅ Found {len(candidates_df)} candidates:")
        print(candidates_df)
        
        return candidates_df
    else:
        print("❌ No stocks meet the criteria")
        return None

value_stocks = value_investing_screen()
```

### Dividend Yield Hunters

```python
def dividend_yield_analysis(min_yield=3.0):
    """Find stocks with attractive dividend yields"""
    print("💰 Dividend Yield Analysis")
    print("=" * 50)
    print(f"Minimum Yield: {min_yield}%")
    
    all_symbols = Stocks.list()
    dividend_stocks = []
    
    for symbol in all_symbols[:150]:  # Sample for demo
        try:
            stock = Stock(symbol, language='th')
            quarterly = stock.quarter_dataframe
            
            if quarterly.empty:
                continue
            
            latest = quarterly.tail(1)
            
            if 'อัตราส่วนเงินปันผลตอบแทน (%)' in latest.columns:
                yield_value = latest['อัตราส่วนเงินปันผลตอบแทน (%)'].iloc[0]
                
                if yield_value and float(yield_value) >= min_yield:
                    dividend_stocks.append({
                        'Symbol': symbol,
                        'Company': stock.company_name,
                        'Sector': stock.sector,
                        'Dividend Yield (%)': round(float(yield_value), 2),
                        'Current Price (THB)': latest.get('ราคาล่าสุด (บาท)', {}).iloc[0] if 'ราคาล่าสุด (บาท)' in latest.columns else 'N/A'
                    })
                    
        except:
            continue
    
    if dividend_stocks:
        dividend_df = pd.DataFrame(dividend_stocks)
        dividend_df = dividend_df.sort_values('Dividend Yield (%)', ascending=False)
        
        print(f"\n💎 High Dividend Yield Stocks:")
        print(dividend_df.head(15))
        
        # Sector distribution
        print(f"\n🏭 Sector Distribution:")
        sector_dist = dividend_df['Sector'].value_counts()
        for sector, count in sector_dist.head(5).items():
            print(f"   {sector}: {count} stocks")
        
        return dividend_df
    
    return None

dividend_analysis = dividend_yield_analysis()
```

### Growth Stock Screening

```python
def growth_stock_screen(min_revenue_growth=20, min_profit_growth=25):
    """Screen for high-growth stocks"""
    print("🚀 Growth Stock Screen")
    print("=" * 50)
    print(f"Criteria: Revenue Growth ≥ {min_revenue_growth}%, Profit Growth ≥ {min_profit_growth}%")
    
    all_symbols = Stocks.list()
    growth_candidates = []
    
    for symbol in all_symbols[:100]:  # Sample for demo
        try:
            stock = Stock(symbol, language='th')
            quarterly = stock.quarter_dataframe
            
            if quarterly.empty or len(quarterly) < 4:
                continue
            
            latest = quarterly.tail(1)
            
            # Get growth metrics
            revenue_growth = latest['รายได้รวม การเติบโตเทียบปีก่อนหน้า (%)'].iloc[0] if 'รายได้รวม การเติบโตเทียบปีก่อนหน้า (%)' in latest.columns else None
            profit_growth = latest['กำไรสุทธิ การเติบโตเทียบปีก่อนหน้า (%)'].iloc[0] if 'กำไรสุทธิ การเติบโตเทียบปีก่อนหน้า (%)' in latest.columns else None
            
            if (revenue_growth and float(revenue_growth) >= min_revenue_growth and
                profit_growth and float(profit_growth) >= min_profit_growth):
                
                growth_candidates.append({
                    'Symbol': symbol,
                    'Company': stock.company_name,
                    'Sector': stock.sector,
                    'Revenue Growth (%)': round(float(revenue_growth), 2),
                    'Profit Growth (%)': round(float(profit_growth), 2),
                    'Market': stock.market
                })
                
        except:
            continue
    
    if growth_candidates:
        growth_df = pd.DataFrame(growth_candidates)
        growth_df = growth_df.sort_values(['Revenue Growth (%)', 'Profit Growth (%)'], ascending=False)
        
        print(f"\n🌟 High Growth Stocks:")
        print(growth_df.head(10))
        
        return growth_df
    
    return None

growth_stocks = growth_stock_screen()
```

---

## 🔍 Advanced Analysis Examples

### Correlation Analysis

```python
def sector_correlation_analysis(sector_name):
    """Analyze correlations between stocks in a sector"""
    print(f"🔗 Correlation Analysis: {sector_name} Sector")
    print("=" * 60)
    
    sector_stocks = Stocks.filter_by_sector(sector_name)
    
    if len(sector_stocks) < 3:
        print("❌ Not enough stocks in sector for correlation analysis")
        return None
    
    # Collect revenue growth data
    stock_data = {}
    
    for symbol in sector_stocks[:10]:  # Limit to top 10 for analysis
        try:
            stock = Stock(symbol)
            quarterly = stock.quarter_dataframe
            
            if not quarterly.empty and 'revenue_yoy' in quarterly.columns:
                growth_data = quarterly['revenue_yoy'].dropna()
                if len(growth_data) >= 8:  # Need sufficient data points
                    stock_data[symbol] = growth_data.tail(8).values
                    
        except:
            continue
    
    if len(stock_data) >= 3:
        # Create correlation matrix
        import numpy as np
        
        # Align data lengths
        min_length = min(len(data) for data in stock_data.values())
        aligned_data = {symbol: data[:min_length] for symbol, data in stock_data.items()}
        
        # Calculate correlation matrix
        symbols = list(aligned_data.keys())
        correlation_matrix = np.corrcoef(list(aligned_data.values()))
        
        # Create DataFrame for better visualization
        correlation_df = pd.DataFrame(correlation_matrix, index=symbols, columns=symbols)
        
        print(f"\n📊 Revenue Growth Correlation Matrix:")
        print(correlation_df.round(3))
        
        # Find highest correlations
        print(f"\n🔗 Highest Correlations:")
        for i in range(len(symbols)):
            for j in range(i+1, len(symbols)):
                corr = correlation_matrix[i, j]
                print(f"   {symbols[i]} vs {symbols[j]}: {corr:.3f}")
        
        return correlation_df
    
    return None

# Example: Analyze banking sector correlations
banking_correlation = sector_correlation_analysis('Banking')
```

### Time Series Analysis

```python
def quarterly_trend_analysis(symbol, periods=20):
    """Analyze quarterly trends with moving averages"""
    print(f"📈 Quarterly Trend Analysis: {symbol}")
    print("=" * 50)
    
    stock = Stock(symbol, language='th')
    quarterly = stock.quarter_dataframe
    
    if quarterly.empty:
        print("❌ No quarterly data available")
        return None
    
    # Focus on key metrics
    analysis_cols = ['รายได้รวม', 'กำไรสุทธิ', 'ROE (%)']
    available_cols = [col for col in analysis_cols if col in quarterly.columns]
    
    if not available_cols:
        print("❌ No analysis columns available")
        return None
    
    # Get recent data
    recent_data = quarterly[available_cols].tail(periods)
    
    # Calculate moving averages
    ma_data = recent_data.copy()
    for col in available_cols:
        ma_data[f'{col}_MA4'] = recent_data[col].rolling(window=4).mean()
        ma_data[f'{col}_MA8'] = recent_data[col].rolling(window=8).mean()
    
    print(f"\n📊 Trend Analysis for {stock.company_name}:")
    print("Recent 8 quarters with moving averages:")
    display_data = ma_data.tail(8)
    
    for period in display_data.index:
        print(f"\n{period}:")
        for col in available_cols:
            current = display_data.loc[period, col]
            ma4 = display_data.loc[period, f'{col}_MA4']
            ma8 = display_data.loc[period, f'{col}_MA8']
            
            print(f"  {col}:")
            print(f"    Current: {current}")
            print(f"    4Q MA:   {ma4:.2f}" if pd.notna(ma4) else "    4Q MA:   N/A")
            print(f"    8Q MA:   {ma8:.2f}" if pd.notna(ma8) else "    8Q MA:   N/A")
    
    return ma_data

# Example usage
trend_analysis = quarterly_trend_analysis('PTT')
```

### Portfolio Simulation

```python
def simulate_portfolio_performance(symbols, weights=None):
    """Simulate portfolio performance based on historical data"""
    print("📊 Portfolio Performance Simulation")
    print("=" * 50)
    
    if weights is None:
        weights = [1/len(symbols)] * len(symbols)  # Equal weights
    
    if len(weights) != len(symbols):
        print("❌ Weights must match number of symbols")
        return None
    
    print(f"📋 Portfolio composition:")
    for symbol, weight in zip(symbols, weights):
        print(f"   {symbol}: {weight:.1%}")
    
    portfolio_data = []
    
    for symbol, weight in zip(symbols, weights):
        try:
            stock = Stock(symbol, language='th')
            yearly = stock.yearly_dataframe
            
            if not yearly.empty and 'ROE (%)' in yearly.columns:
                # Use ROE as a proxy for returns
                returns = yearly['ROE (%)'].tail(5)  # Last 5 years
                weighted_returns = returns * weight
                
                portfolio_data.append({
                    'Symbol': symbol,
                    'Weight': f"{weight:.1%}",
                    'Avg ROE (%)': returns.mean(),
                    'ROE Std (%)': returns.std(),
                    'Weighted Contribution': weighted_returns.mean()
                })
                
        except:
            continue
    
    if portfolio_data:
        portfolio_df = pd.DataFrame(portfolio_data)
        
        print(f"\n📊 Individual Stock Performance:")
        print(portfolio_df)
        
        # Portfolio metrics
        total_return = portfolio_df['Weighted Contribution'].sum()
        portfolio_risk = (portfolio_df['ROE Std (%)'] * 
                         portfolio_df['Weight'].str.rstrip('%').astype(float) / 100).sum()
        
        print(f"\n🎯 Portfolio Summary:")
        print(f"   Expected Return (ROE): {total_return:.2f}%")
        print(f"   Portfolio Risk:        {portfolio_risk:.2f}%")
        print(f"   Risk-Return Ratio:     {total_return/portfolio_risk:.2f}" if portfolio_risk > 0 else "   Risk-Return Ratio:     N/A")
        
        return portfolio_df
    
    return None

# Example: Simulate a diversified Thai portfolio
thai_portfolio = ['PTT', 'KBANK', 'CPALL', 'AOT', 'SCB']
portfolio_weights = [0.25, 0.25, 0.2, 0.15, 0.15]
portfolio_sim = simulate_portfolio_performance(thai_portfolio, portfolio_weights)
```

These examples demonstrate the versatility and power of ThaiFin for various financial analysis tasks, from basic stock research to advanced portfolio management and investment strategy development.
