"""
Test file for Thai Securities Data source integration.

This file demonstrates how to use the new Thai Securities Data source
and provides basic validation tests.
"""

import pytest
from unittest.mock import Mock, patch
from thaifin.sources.thai_securities_data import ThaiSecuritiesDataService
from thaifin.sources.thai_securities_data.stock import ThaiSecuritiesStock
from thaifin.sources.thai_securities_data.model import (
    StockBasicInfo,
    FinancialMetrics,
    StockListResponse,
    FinancialDataResponse
)


class TestThaiSecuritiesDataAPI:
    """Test cases for Thai Securities Data API functions"""
    
    def test_get_stock_list_mock(self):
        """Test stock list API with mocked response"""
        # Mock response data
        mock_stocks = [
            StockBasicInfo(
                symbol="PTT",
                name_th="บริษัท ปตท. จำกัด (มหาชน)",
                name_en="PTT Public Company Limited",
                sector="Energy",
                market="SET"
            ),
            StockBasicInfo(
                symbol="KBANK",
                name_th="ธนาคารกสิกรไทย จำกัด (มหาชน)",
                name_en="KASIKORNBANK Public Company Limited",
                sector="Financial",
                market="SET"
            )
        ]
        
        mock_response = StockListResponse(
            success=True,
            message="Success",
            data=mock_stocks
        )
        
        with patch('thaifin.sources.thai_securities_data.api.httpx.Client') as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.text = mock_response.model_dump_json()
            mock_response_obj.raise_for_status.return_value = None
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response_obj
            
            result = get_stock_list()
            
            assert result.success is True
            assert len(result.data) == 2
            assert result.data[0].symbol == "PTT"
            assert result.data[1].symbol == "KBANK"

    def test_get_financial_data_mock(self):
        """Test financial data API with mocked response"""
        # Mock financial data
        mock_financial = [
            FinancialMetrics(
                symbol="PTT",
                fiscal_year=2023,
                quarter=4,
                revenue=1000000.0,
                net_profit=50000.0,
                total_assets=2000000.0
            )
        ]
        
        mock_response = FinancialDataResponse(
            success=True,
            message="Success", 
            data=mock_financial
        )
        
        with patch('thaifin.sources.thai_securities_data.api.httpx.Client') as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.text = mock_response.model_dump_json()
            mock_response_obj.raise_for_status.return_value = None
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response_obj
            
            result = get_financial_data("PTT")
            
            assert result.success is True
            assert len(result.data) == 1
            assert result.data[0].symbol == "PTT"
            assert result.data[0].revenue == 1000000.0


class TestThaiSecuritiesStock:
    """Test cases for ThaiSecuritiesStock class"""
    
    def test_stock_creation_mock(self):
        """Test creating a stock instance with mocked data"""
        # Mock basic info
        mock_basic_info = StockBasicInfo(
            symbol="PTT",
            name_th="บริษัท ปตท. จำกัด (มหาชน)",
            name_en="PTT Public Company Limited",
            sector="Energy",
            market="SET"
        )
        
        with patch.object(ThaiSecuritiesStock, 'find_symbol', return_value=mock_basic_info), \
             patch('thaifin.sources.thai_securities_data.stock.get_stock_info') as mock_get_info, \
             patch('thaifin.sources.thai_securities_data.stock.get_financial_data') as mock_get_financial:
            
            # Mock detailed info response
            mock_get_info.return_value.data = Mock()
            
            # Mock financial data response
            mock_get_financial.return_value.data = []
            
            stock = ThaiSecuritiesStock("PTT")
            
            assert stock.symbol == "PTT"
            assert stock.company_name == "PTT Public Company Limited"
            assert stock.thai_company_name == "บริษัท ปตท. จำกัด (มหาชน)"
            assert stock.sector == "Energy"

    def test_list_symbol_mock(self):
        """Test listing symbols with mocked data"""
        mock_stocks = [
            StockBasicInfo(symbol="PTT", name_th="PTT", name_en="PTT"),
            StockBasicInfo(symbol="KBANK", name_th="KBANK", name_en="KBANK")
        ]
        
        with patch('thaifin.sources.thai_securities_data.stock.get_stock_list') as mock_get_list:
            mock_get_list.return_value.data = mock_stocks
            
            symbols = ThaiSecuritiesStock.list_symbol()
            
            assert len(symbols) == 2
            assert "PTT" in symbols
            assert "KBANK" in symbols


def test_integration_example():
    """
    Example of how to use the Thai Securities Data source.
    This test demonstrates the integration but uses mocked data.
    """
    print("\n=== Thai Securities Data Integration Example ===")
    
    # Example 1: List all symbols (mocked)
    with patch('thaifin.sources.thai_securities_data.stock.get_stock_list') as mock_get_list:
        mock_stocks = [
            StockBasicInfo(symbol="PTT", name_th="PTT", name_en="PTT"),
            StockBasicInfo(symbol="KBANK", name_th="KBANK", name_en="KBANK")
        ]
        mock_get_list.return_value.data = mock_stocks
        
        symbols = ThaiSecuritiesStock.list_symbol()
        print(f"Available symbols (sample): {symbols[:5]}")
    
    # Example 2: Search for stocks (mocked)
    with patch('thaifin.sources.thai_securities_data.stock.get_stock_list') as mock_get_list:
        mock_stocks = [
            StockBasicInfo(symbol="PTT", name_th="ปตท", name_en="PTT Public Company"),
            StockBasicInfo(symbol="PTTEP", name_th="ปตท.สผ", name_en="PTT Exploration")
        ]
        mock_get_list.return_value.data = mock_stocks
        
        # This would normally perform fuzzy search
        search_results = ThaiSecuritiesStock.search("PTT", limit=2)
        print(f"Search results for 'PTT': Found {len(search_results)} matches (mocked)")
    
    print("=== Integration Example Complete ===")


if __name__ == "__main__":
    # Run the integration example
    test_integration_example()
    
    print("\nTo run the full test suite:")
    print("pytest tests/test_thai_securities_data.py -v")
