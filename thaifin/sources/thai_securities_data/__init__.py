"""
Thai Securities Data source for ThaiFin library.

This module provides access to Thai stock market data from Thai Securities Data API,
offering comprehensive financial data, market data, and company information.
"""

from .api import (
    get_stock_list,
    get_financial_data,
    get_stock_info,
    get_market_data
)

from .model import (
    StockBasicInfo,
    FinancialMetrics,
    MarketData,
    StockDetailInfo,
    StockListResponse,
    FinancialDataResponse,
    ThaiSecuritiesDataResponse
)

__all__ = [
    # API functions
    "get_stock_list",
    "get_financial_data", 
    "get_stock_info",
    "get_market_data",
    
    # Data models
    "StockBasicInfo",
    "FinancialMetrics",
    "MarketData", 
    "StockDetailInfo",
    "StockListResponse",
    "FinancialDataResponse",
    "ThaiSecuritiesDataResponse"
]
