"""
Thai Securities Data Stock class - Alternative data source for ThaiFin.

This module provides an alternative Stock implementation that uses Thai Securities Data
as the data source instead of Finnomena.
"""

import arrow
import pandas as pd
from fuzzywuzzy import process
from typing import List, Optional

from thaifin.sources.thai_securities_data import (
    get_stock_list,
    get_financial_data,
    get_stock_info,
    get_market_data
)


class ThaiSecuritiesStock:
    """
    Alternative Stock class using Thai Securities Data as the data source.
    Provides similar interface to the main Stock class but with different data source.
    """

    @classmethod
    def search(cls, company_name: str, limit: int = 5) -> List['ThaiSecuritiesStock']:
        """
        Search for stocks matching the given company name using Thai Securities Data.

        Args:
            company_name (str): The name of the company to search for.
            limit (int): The maximum number of results to return.

        Returns:
            List[ThaiSecuritiesStock]: A list of ThaiSecuritiesStock objects corresponding 
            to the top matches.
        """
        stock_list = get_stock_list().data
        
        # Create search dictionary with both Thai and English names
        search_against = {}
        for stock in stock_list:
            search_against[stock.name_th] = stock
            search_against[stock.name_en] = stock
        
        search_result = process.extract(company_name, search_against, limit=limit)
        return [cls(result[1].symbol) for result in search_result]

    @staticmethod
    def list_symbol() -> List[str]:
        """
        List all stock symbols available in Thai Securities Data.

        Returns:
            List[str]: A list of all stock symbols.
        """
        stock_list = get_stock_list().data
        return [stock.symbol for stock in stock_list]

    @staticmethod
    def find_symbol(symbol: str):
        """
        Find a stock by its symbol in Thai Securities Data.

        Args:
            symbol (str): The stock symbol to search for.

        Returns:
            StockBasicInfo: The stock data object corresponding to the given symbol.
        """
        stock_list = get_stock_list().data
        return next((stock for stock in stock_list if stock.symbol == symbol), None)

    def __init__(self, symbol: str):
        """
        Initialize a ThaiSecuritiesStock object with the given symbol.

        Args:
            symbol (str): The stock symbol.
        """
        symbol = symbol.upper()
        self.basic_info = self.find_symbol(symbol)
        
        if not self.basic_info:
            raise ValueError(f"Stock symbol '{symbol}' not found in Thai Securities Data")
        
        # Get detailed information
        self.detail_info = get_stock_info(symbol).data
        
        # Get financial data (both quarterly and yearly)
        self.financial_data = get_financial_data(symbol).data
        
        self.updated = arrow.utcnow()

    @property
    def symbol(self) -> str:
        """
        The stock symbol.

        Returns:
            str: The symbol of the stock.
        """
        return self.basic_info.symbol

    @property
    def company_name(self) -> str:
        """
        The English name of the company.

        Returns:
            str: The English name of the company.
        """
        return self.basic_info.name_en

    @property
    def thai_company_name(self) -> str:
        """
        The Thai name of the company.

        Returns:
            str: The Thai name of the company.
        """
        return self.basic_info.name_th

    @property
    def sector(self) -> Optional[str]:
        """
        The sector of the company.

        Returns:
            str: The sector of the company.
        """
        return self.basic_info.sector

    @property
    def quarter_dataframe(self) -> pd.DataFrame:
        """
        The quarterly financial data as a pandas DataFrame.

        Returns:
            pd.DataFrame: The DataFrame containing quarterly financial data.
        """
        # Filter for quarterly data (quarter is not None and not 0)
        quarterly_data = [
            data for data in self.financial_data 
            if data.quarter is not None and data.quarter > 0
        ]
        
        if not quarterly_data:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame([data.model_dump() for data in quarterly_data])
        
        # Create time index
        df["Time"] = df["fiscal_year"].astype(str) + "Q" + df["quarter"].astype(str)
        df = df.set_index("Time")
        df.index = pd.to_datetime(df.index).to_period("Q")
        
        # Remove redundant columns
        df = df.drop(columns=["fiscal_year", "quarter", "symbol"], errors='ignore')
        
        return df

    @property
    def yearly_dataframe(self) -> pd.DataFrame:
        """
        The yearly financial data as a pandas DataFrame.

        Returns:
            pd.DataFrame: The DataFrame containing yearly financial data.
        """
        # Filter for yearly data (quarter is None or 0)
        yearly_data = [
            data for data in self.financial_data 
            if data.quarter is None or data.quarter == 0
        ]
        
        if not yearly_data:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame([data.model_dump() for data in yearly_data])
        
        # Set fiscal year as index
        df = df.set_index("fiscal_year")
        df.index = pd.to_datetime(df.index, format="%Y").to_period("Y")
        
        # Remove redundant columns
        df = df.drop(columns=["quarter", "symbol"], errors='ignore')
        
        return df

    def get_market_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get market data (price, volume) for the stock.

        Args:
            start_date (str, optional): Start date in YYYY-MM-DD format
            end_date (str, optional): End date in YYYY-MM-DD format

        Returns:
            pd.DataFrame: DataFrame containing market data
        """
        market_data = get_market_data(self.symbol, start_date, end_date).data
        
        if not market_data:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame([data.model_dump() for data in market_data])
        
        # Set date as index
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        # Remove symbol column
        df = df.drop(columns=['symbol'], errors='ignore')
        
        return df

    def __repr__(self) -> str:
        """
        String representation of the ThaiSecuritiesStock object.

        Returns:
            str: A string representation showing the stock symbol and last update time.
        """
        return f'<ThaiSecuritiesStock "{self.symbol}" - updated {self.updated.humanize()}>'
