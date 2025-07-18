import arrow
import pandas as pd

from thaifin.sources.finnomena.model import (
    ListingDatum,
    QuarterFinancialSheetDatum
)
from thaifin.sources.thai_securities_data.models import SecurityData, MetaData
from thaifin.sources.finnomena import FinnomenaService
from thaifin.sources.thai_securities_data import ThaiSecuritiesDataService

class Stock:

    def __init__(self, symbol: str):
        """
        Initialize a Stock object with the given symbol.

        Args:
            symbol (str): The stock symbol.
        """
        symbol_upper: str = symbol.upper()
        self.info: ListingDatum = FinnomenaService().get_stock(symbol_upper)
        self.info_th: SecurityData = ThaiSecuritiesDataService().get_stock(symbol_upper)
        self.fundamental: list[QuarterFinancialSheetDatum] = FinnomenaService().get_financial_sheet(symbol_upper)
        self.updated = arrow.utcnow()
        
    class SafeProperty:
        """ Descriptor for safely accessing attributes with a default value.
        This allows for cleaner access to attributes that may not always be present.
        Usage:
        symbol = SafeProperty('info', 'symbol')
        thai_company_name = SafeProperty('info_th', 'name')
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
    company_name = SafeProperty('info', 'en_name')
    thai_company_name = SafeProperty('info_th', 'name')
    thai_market = SafeProperty('info_th', 'market')
    thai_industry = SafeProperty('info_th', 'industry')
    thai_sector = SafeProperty('info_th', 'sector')
    thai_address = SafeProperty('info_th', 'address')
    website = SafeProperty('info_th', 'web')

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
    print(stock.thai_market)
    print(stock.thai_industry)
    print(stock.thai_sector)
    print(stock.thai_address)
    print(stock.website)
    print(stock.quarter_dataframe)
    print(stock.yearly_dataframe)
