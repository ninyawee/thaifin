import arrow
import pandas as pd
from fuzzywuzzy import process

from thaifin.sources.finnomena import get_financial_sheet
from thaifin.sources.finnomena import get_stock_list

class Stock:
    """
    Represents a stock with methods to search, list, and retrieve detailed financial information.
    """

    @classmethod
    def search(cls, company_name: str, limit: int = 5):
        """
        Search for stocks matching the given company name.

        Args:
            company_name (str): The name of the company to search for.
            limit (int): The maximum number of results to return.

        Returns:
            list[Stock]: A list of Stock objects corresponding to the top matches.
        """
        list_ = get_stock_list().data
        # since th_name and en_name are identical, we only search against th_name
        search_against = {x.th_name: x for x in list_}
        search_result = process.extract(company_name, search_against, limit=limit)
        return [cls(s[0].name) for s in search_result]

    @staticmethod
    def list_symbol():
        """
        List all stock symbols.

        Returns:
            list[str]: A list of all stock symbols.
        """
        list_ = get_stock_list().data
        return [s.name for s in list_]

    @staticmethod
    def find_symbol(symbol: str):
        """
        Find a stock by its symbol.

        Args:
            symbol (str): The stock symbol to search for.

        Returns:
            StockData: The stock data object corresponding to the given symbol.
        """
        list_ = get_stock_list().data
        return next(obj for obj in list_ if obj.name == symbol)

    def __init__(self, symbol: str):
        """
        Initialize a Stock object with the given symbol.

        Args:
            symbol (str): The stock symbol.
        """
        symbol = symbol.upper()
        self.info = self.find_symbol(symbol)
        self.fundamental = get_financial_sheet(self.info.security_id).data
        self.updated = arrow.utcnow()

    @property
    def symbol(self):
        """
        The stock symbol.

        Returns:
            str: The symbol of the stock.
        """
        return self.info.name

    @property
    def company_name(self):
        """
        The English name of the company.

        Returns:
            str: The English name of the company.
        """
        return self.info.enName

    @property
    def thai_company_name(self):
        """
        The Thai name of the company.

        Returns:
            str: The Thai name of the company.
        """
        return self.info.thName

    @property
    def quarter_dataframe(self):
        """
        The quarterly financial data as a pandas DataFrame.

        Returns:
            pd.DataFrame: The DataFrame containing quarterly financial data.
        """
        df = pd.DataFrame([s.model_dump(exclude={"security_id"}) for s in self.fundamental])
        # Quarter 9 means yearly values
        df = df[df.quarter != 9]
        df["Time"] = df.fiscal.astype(str) + "Q" + df.quarter.astype(str)
        df = df.set_index("Time")
        df.index = pd.to_datetime(df.index).to_period("Q")
        df = df.drop(columns=["fiscal", "quarter"])
        return df

    @property
    def yearly_dataframe(self):
        """
        The yearly financial data as a pandas DataFrame.

        Returns:
            pd.DataFrame: The DataFrame containing yearly financial data.
        """
        df = pd.DataFrame([s.model_dump(exclude={"security_id"}) for s in self.fundamental])
        # Quarter 9 means yearly values
        df = df[df.quarter == 9]
        df = df.set_index("fiscal")
        df.index = pd.to_datetime(df.index, format="%Y").to_period("Y")
        df = df.drop(columns=["quarter"])
        return df

    def __repr__(self):
        """
        String representation of the Stock object.

        Returns:
            str: A string representation showing the stock symbol and last update time.
        """
        return f'<Stock "{self.symbol}" - updated {self.updated.humanize()}>'
