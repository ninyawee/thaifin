"""
Module: service.py

This module provides the ThaiSecuritiesDataService class, which acts as a service layer for interacting with the Thai Securities Data API.
It includes methods to fetch metadata, retrieve a list of stocks, and get detailed stock information by symbol.

Classes:
    ThaiSecuritiesDataService: A service class for fetching and processing Thai securities data.

Example Usage:
    service = ThaiSecuritiesDataService()
    meta_data = service.get_meta_data()
    stock_list = service.get_stock_list()
    stock_data = service.get_stock("AOT")

"""

from thaifin.sources.thai_securities_data.api import get_meta_data, get_securities_data
from thaifin.sources.thai_securities_data.models import MetaData, SecurityData


class ThaiSecuritiesDataService:
    def __init__(self):
        pass

    def get_meta_data(self, language: str = "en") -> MetaData:
        """
        Fetch metadata for Thai Securities Data.

        Returns:
            MetaData: Metadata object containing last updated time, total securities, market and sector data.

        Raises:
            ValueError: If there is an issue with the API response or data validation.
        """
        return get_meta_data(language=language)

    def get_stock_list(self, language: str = "en") -> list[SecurityData]:
        """
        Fetch the list of stocks from Thai Securities Data API.

        Returns:
            List[SecurityData]: List of SecurityData objects containing information about securities.

        Raises:
            ValueError: If there is an issue with the API response or data validation.
        """
        securities_data: list[SecurityData] = get_securities_data(language=language)
        if not securities_data:
            raise ValueError(
                "No securities data available in the Thai Securities Data API response."
            )

        return securities_data

    def get_stock(self, symbol: str, language: str = "en") -> SecurityData:
        """
        Get stock data for a given symbol.

        Args:
            symbol (str): The stock symbol.

        Returns:
            SecurityData: The stock data object corresponding to the given symbol.

        Raises:
            ValueError: If the stock with the given symbol is not found.
        """
        stock_list: list[SecurityData] = self.get_stock_list(language=language)
        try:
            stock: SecurityData = next(s for s in stock_list if s.symbol == symbol)
        except StopIteration:
            raise ValueError(f"Stock with symbol {symbol} not found.")

        return stock


if __name__ == "__main__":
    # Example usage
    service = ThaiSecuritiesDataService()

    try:
        meta_data: MetaData = service.get_meta_data()
        print("Meta Data:", meta_data)

        stock_list: list[SecurityData] = service.get_stock_list()
        print("Stock List:", stock_list)

        stock_symbol = "AOT"  # Example stock symbol
        stock_data: SecurityData = service.get_stock(stock_symbol)
        print(f"Stock Data for {stock_symbol}:", stock_data)

    except ValueError as e:
        print(f"Error: {e}")
