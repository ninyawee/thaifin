"""
This module provides the `Stock` class, which serves as the main API for accessing Thai stock fundamental data.
"""

import arrow
import pandas as pd
from fuzzywuzzy import process
from typing import List

from thaifin.sources.thai_securities_data.models import SecurityData
from thaifin.sources.finnomena import FinnomenaService
from thaifin.sources.thai_securities_data import ThaiSecuritiesDataService

class Stock:

    def __init__(self, symbol: str, language: str = "en"):
        """
        Initialize a Stock object with the given symbol and language.

        Args:
            symbol (str): The stock symbol.
            language (str): Language preference ("en" or "th"). Defaults to "en".
        """
        self.symbol_upper: str = symbol.upper()
        self.language = language
        self.info: SecurityData = ThaiSecuritiesDataService().get_stock(self.symbol_upper, language=self.language)
        self.updated = arrow.utcnow()
        
    class SafeProperty:
        """ Descriptor for safely accessing attributes with a default value.
        This allows for cleaner access to attributes that may not always be present.
        Usage:
        symbol = SafeProperty('info', 'symbol')
        company_name = SafeProperty('info', 'name')
        """
        def __init__(self, obj_attr: str, field_attr: str, default: str = '-'):
            self.obj_attr = obj_attr
            self.field_attr = field_attr
            self.default = default
        
        def __get__(self, instance, owner):
            if instance is None:
                return self
            obj = getattr(instance, self.obj_attr)
            value = getattr(obj, self.field_attr, None)
            return value if value else self.default

    symbol = SafeProperty('info', 'symbol')
    company_name = SafeProperty('info', 'name')
    industry = SafeProperty('info', 'industry')
    sector = SafeProperty('info', 'sector')
    market = SafeProperty('info', 'market')
    address = SafeProperty('info', 'address')
    website = SafeProperty('info', 'web')

    @classmethod
    def search(cls, company_name: str, limit: int = 5) -> List['Stock']:
        """
        Search for stocks by company name using fuzzy matching.

        Args:
            company_name (str): The company name to search for.
            limit (int): Maximum number of results to return. Defaults to 5.

        Returns:
            List[Stock]: List of Stock objects matching the search criteria.
        """
        # Get stock list from Thai Securities Data API
        thai_service = ThaiSecuritiesDataService()
        stock_list = thai_service.get_stock_list()
        
        # Create search dictionary combining Thai and English names
        search_against = {f"{stock.name}": stock for stock in stock_list}
        
        # Perform fuzzy search
        search_result = process.extract(company_name, search_against.keys(), limit=limit)
        
        # Return Stock objects for the best matches
        return [cls(search_against[result[0]].symbol) for result in search_result]

    @staticmethod
    def list_symbol() -> List[str]:
        """
        Get a list of all available stock symbols.

        Returns:
            List[str]: List of stock symbols.
        """
        thai_service = ThaiSecuritiesDataService()
        stock_list = thai_service.get_stock_list()
        return [stock.symbol for stock in stock_list]

    @property
    def quarter_dataframe(self) -> pd.DataFrame:
        """
        The quarterly financial data as a pandas DataFrame.

        Returns:
            pd.DataFrame: The DataFrame containing quarterly financial data.
        """
        fundamental = FinnomenaService().get_financial_sheet(self.symbol_upper, language=self.language)
        if self.language == 'th' and isinstance(fundamental[0], dict):
            # Handle Thai data (list of dicts)
            df = pd.DataFrame(fundamental)
            # Remove security_id column if it exists
            security_id_col = 'รหัสหลักทรัพย์'
            if security_id_col in df.columns:
                df = df.drop(columns=[security_id_col])
        else:
            # Handle English data (list of Pydantic models)
            df = pd.DataFrame([s.model_dump(exclude={"security_id"}) for s in fundamental])
        # Quarter 9 means yearly values - filter for quarterly data only
        quarter_col = 'ไตรมาส' if self.language == 'th' else 'quarter'
        fiscal_col = 'ปีการเงิน' if self.language == 'th' else 'fiscal'
        df = df[df[quarter_col] != 9]
        df["Time"] = df[fiscal_col].astype(str) + "Q" + df[quarter_col].astype(str)
        df = df.set_index("Time")
        df.index = pd.to_datetime(df.index).to_period("Q")
        df = df.drop(columns=[fiscal_col, quarter_col])
        return df

    @property
    def yearly_dataframe(self) -> pd.DataFrame:
        """
        The yearly financial data as a pandas DataFrame.

        Returns:
            pd.DataFrame: The DataFrame containing yearly financial data.
        """
        fundamental = FinnomenaService().get_financial_sheet(self.symbol_upper, language=self.language)
        if self.language == 'th' and isinstance(fundamental[0], dict):
            # Handle Thai data (list of dicts)
            df = pd.DataFrame(fundamental)
            # Remove security_id column if it exists
            security_id_col = 'รหัสหลักทรัพย์'
            if security_id_col in df.columns:
                df = df.drop(columns=[security_id_col])
        else:
            # Handle English data (list of Pydantic models)
            df = pd.DataFrame([s.model_dump(exclude={"security_id"}) for s in fundamental])
        # Quarter 9 means yearly values - filter for yearly data only
        quarter_col = 'ไตรมาส' if self.language == 'th' else 'quarter'
        fiscal_col = 'ปีการเงิน' if self.language == 'th' else 'fiscal'
        df = df[df[quarter_col] == 9]
        df = df.set_index(fiscal_col)
        df.index = pd.to_datetime(df.index, format="%Y").to_period("Y")
        df = df.drop(columns=[quarter_col])
        return df

    def __repr__(self) -> str:
        """
        String representation of the Stock object.

        Returns:
            str: A string representation showing the stock symbol and last update time.
        """
        return f'<Stock "{self.symbol}" - updated {self.updated.humanize()}>'
    
if __name__ == "__main__":
    # Example usage - English (default)
    stock_en = Stock("ptt")
    print("=== English Version ===")
    print("Symbol:", stock_en.symbol)
    print("Company Name:", stock_en.company_name)
    print("Industry:", stock_en.industry)
    print("Sector:", stock_en.sector)
    print("Market:", stock_en.market)
    print()
    
    # Example usage - Thai
    stock_th = Stock("ptt", language="th")
    print("=== Thai Version ===")
    print("ชื่อหุ้น:", stock_th.symbol)
    print("ชื่อบริษัท:", stock_th.company_name)
    print("อุตสาหกรรม:", stock_th.industry)
    print("กลุ่มอุตสาหกรรม:", stock_th.sector)
    print("ตลาดหลักทรัพย์:", stock_th.market)
    print()
    
    # Financial data examples
    print("=== English Financial Data ===")
    print("Quarter DataFrame (English):")
    print(stock_en.quarter_dataframe.head())
    print()
    print("Yearly DataFrame (English):")
    print(stock_en.yearly_dataframe.head())
    print()
    
    print("=== Thai Financial Data ===")
    print("Quarter DataFrame (Thai):")
    print(stock_th.quarter_dataframe.head())
    print()
    print("Yearly DataFrame (Thai):")
    print(stock_th.yearly_dataframe.head())
