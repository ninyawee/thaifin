"""
ThaiFin Stocks Module - Example Usage and Utilities

This module provides example usage patterns for the ThaiFin library,
demonstrating how to access Thai stock fundamental data in both English and Thai.
"""

from thaifin.stock import Stock


def demonstrate_basic_usage():
    """Demonstrate basic Stock class usage."""
    print("🚀 ThaiFin Basic Usage Examples")
    print("=" * 40)
    
    # Create a stock instance (English by default)
    stock = Stock("PTT")
    print(f"Stock Symbol: {stock.symbol}")
    print(f"Company Name: {stock.company_name}")
    print(f"Industry: {stock.industry}")
    print(f"Sector: {stock.sector}")
    print(f"Market: {stock.market}")
    print()


def demonstrate_thai_language_support():
    """Demonstrate Thai language support."""
    print("🇹🇭 Thai Language Support Examples")
    print("=" * 40)
    
    # English version
    stock_en = Stock("CPALL", language="en")
    print("English Company Info:")
    print(f"  Company: {stock_en.company_name}")
    print(f"  Industry: {stock_en.industry}")
    print()
    
    # Thai version
    stock_th = Stock("CPALL", language="th")
    print("Thai Company Info:")
    print(f"  บริษัท: {stock_th.company_name}")
    print(f"  อุตสาหกรรม: {stock_th.industry}")
    print()


def demonstrate_financial_data():
    """Demonstrate financial data access."""
    print("📊 Financial Data Examples")
    print("=" * 30)
    
    stock = Stock("PTT")
    
    # Quarterly data
    print("Recent Quarterly Data:")
    quarterly = stock.quarter_dataframe.head(3)
    print(quarterly[['revenue', 'net_profit', 'roe', 'roa']])
    print()
    
    # Yearly data
    print("Recent Yearly Data:")
    yearly = stock.yearly_dataframe.head(3)
    print(yearly[['revenue', 'net_profit', 'roe', 'roa']])
    print()


def demonstrate_thai_financial_data():
    """Demonstrate Thai financial data with Thai field names."""
    print("📊 Thai Financial Data Examples")
    print("=" * 35)
    
    stock_th = Stock("PTT", language="th")
    
    # Quarterly data in Thai
    print("ข้อมูลรายไตรมาสล่าสุด:")
    quarterly_th = stock_th.quarter_dataframe.head(3)
    thai_cols = ['รายได้รวม', 'กำไรสุทธิ', 'ROE (%)', 'ROA (%)']
    available_cols = [col for col in thai_cols if col in quarterly_th.columns]
    if available_cols:
        print(quarterly_th[available_cols])
    print()
    
    # Yearly data in Thai
    print("ข้อมูลรายปีล่าสุด:")
    yearly_th = stock_th.yearly_dataframe.head(3)
    if available_cols:
        available_yearly_cols = [col for col in thai_cols if col in yearly_th.columns]
        if available_yearly_cols:
            print(yearly_th[available_yearly_cols])
    print()


def demonstrate_stock_search():
    """Demonstrate stock search functionality."""
    print("🔍 Stock Search Examples")
    print("=" * 25)
    
    # Search by company name (fuzzy matching)
    print("Searching for 'ปตท':")
    results = Stock.search("ปตท", limit=3)
    for stock in results:
        print(f"  {stock.symbol}: {stock.company_name}")
    print()
    
    # Search by English name
    print("Searching for 'Bank':")
    results = Stock.search("Bank", limit=3)
    for stock in results:
        print(f"  {stock.symbol}: {stock.company_name}")
    print()


def demonstrate_stock_listing():
    """Demonstrate getting list of all stocks."""
    print("📋 Available Stock Symbols")
    print("=" * 25)
    
    symbols = Stock.list_symbol()
    print(f"Total available stocks: {len(symbols)}")
    print("Sample symbols:", symbols[:10])
    print()


def demonstrate_data_analysis():
    """Demonstrate basic data analysis with financial data."""
    print("📈 Basic Data Analysis Example")
    print("=" * 30)
    
    # Get multiple stocks for comparison
    stocks = ["PTT", "CPALL", "KBANK"]
    
    for symbol in stocks:
        stock = Stock(symbol)
        latest_data = stock.yearly_dataframe.head(1)
        
        if not latest_data.empty:
            revenue = latest_data['revenue'].iloc[0] if 'revenue' in latest_data.columns else 'N/A'
            net_profit = latest_data['net_profit'].iloc[0] if 'net_profit' in latest_data.columns else 'N/A'
            roe = latest_data['roe'].iloc[0] if 'roe' in latest_data.columns else 'N/A'
            
            print(f"{symbol} ({stock.company_name}):")
            print(f"  Revenue: {revenue}")
            print(f"  Net Profit: {net_profit}")
            print(f"  ROE: {roe}%")
            print()


# Example usage
if __name__ == "__main__":
    print("🎯 ThaiFin Library - Complete Usage Examples")
    print("=" * 50)
    print()
    
    try:
        demonstrate_basic_usage()
        print()
        
        demonstrate_thai_language_support()
        print()
        
        demonstrate_financial_data()
        print()
        
        demonstrate_thai_financial_data()
        print()
        
        demonstrate_stock_search()
        print()
        
        demonstrate_stock_listing()
        print()
        
        demonstrate_data_analysis()
        print()
        
        print("✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()