import arrow
import pandas as pd

from thaifin.sources.finnomena.model import (
    ListingDatum,
    QuarterFinancialSheetDatum
)
from thaifin.sources.finnomena import FinnomenaService

class Stock:

    def __init__(self, symbol: str):
        """
        Initialize a Stock object with the given symbol.

        Args:
            symbol (str): The stock symbol.
        """
        symbol_upper: str = symbol.upper()
        self.info: ListingDatum = FinnomenaService().get_stock(symbol_upper)
        self.fundamental: list[QuarterFinancialSheetDatum] = FinnomenaService().get_financial_sheet(symbol_upper)
        self.updated = arrow.utcnow()

    @property
    def symbol(self) -> str:
        """
        The stock symbol.

        Returns:
            str: The symbol of the stock.
        """
        return self.info.name

    @property
    def company_name(self) -> str:
        """
        The English name of the company.

        Returns:
            str: The English name of the company.
        """
        return self.info.en_name

    @property
    def thai_company_name(self) -> str:
        """
        The Thai name of the company.

        Returns:
            str: The Thai name of the company.
        """
        return self.info.th_name

    @property
    def quarter_dataframe(self) -> pd.DataFrame:
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
    def yearly_dataframe(self) -> pd.DataFrame:
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

    def __repr__(self) -> str:
        """
        String representation of the Stock object.

        Returns:
            str: A string representation showing the stock symbol and last update time.
        """
        return f'<Stock "{self.symbol}" - updated {self.updated.humanize()}>'
    
if __name__ == "__main__":
    # Example usage
    stock = Stock("ptt") # Automatically converts to uppercase
    print(stock.company_name)
    print(stock.thai_company_name)
    print(stock.quarter_dataframe)
    print(stock.yearly_dataframe)
