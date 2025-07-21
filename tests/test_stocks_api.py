"""
Test file for the new Stocks and Stock classes.
"""

import pytest
from thaifin import Stock, Stocks


def test_stocks_list():
    """Test Stocks.list() returns a list of stock symbols."""
    symbols = Stocks.list()
    assert isinstance(symbols, list)
    assert len(symbols) > 0
    assert 'PTT' in symbols


def test_stocks_search():
    """Test Stocks.search() functionality."""
    # Test English search
    cp_results = Stocks.search('cp', limit=3)
    assert isinstance(cp_results, list)
    assert len(cp_results) <= 3
    assert all(isinstance(stock, Stock) for stock in cp_results)
    
    # Test Thai search
    bank_results = Stocks.search('ธนาคาร', limit=3)
    assert isinstance(bank_results, list)
    assert len(bank_results) <= 3
    assert all(isinstance(stock, Stock) for stock in bank_results)


def test_stocks_list_with_names():
    """Test Stocks.list_with_names() returns a DataFrame."""
    df = Stocks.list_with_names()
    assert hasattr(df, 'shape')  # DataFrame-like object
    assert len(df) > 0
    expected_columns = ['symbol', 'name', 'industry', 'sector', 'market']
    for col in expected_columns:
        assert col in df.columns


def test_stocks_filter_by_sector():
    """Test Stocks.filter_by_sector() functionality."""
    banking_stocks = Stocks.filter_by_sector('Banking')
    assert isinstance(banking_stocks, list)
    # Should find some banking stocks
    assert len(banking_stocks) > 0


def test_stocks_filter_by_market():
    """Test Stocks.filter_by_market() functionality."""
    set_stocks = Stocks.filter_by_market('SET')
    mai_stocks = Stocks.filter_by_market('mai')
    
    assert isinstance(set_stocks, list)
    assert isinstance(mai_stocks, list)
    assert len(set_stocks) > 0
    assert len(mai_stocks) > 0


def test_stock_individual():
    """Test individual Stock class functionality."""
    stock = Stock('PTT')
    
    # Test basic properties
    assert stock.symbol == 'PTT'
    assert stock.company_name is not None
    assert stock.sector is not None
    
    # Test string representation
    assert 'PTT' in str(stock)


def test_stock_with_language():
    """Test Stock class with different languages."""
    stock_en = Stock('PTT', language='en')
    stock_th = Stock('PTT', language='th')
    
    # Both should work
    assert stock_en.symbol == 'PTT'
    assert stock_th.symbol == 'PTT'
    
    # Company names should be different (English vs Thai)
    assert stock_en.company_name != stock_th.company_name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
