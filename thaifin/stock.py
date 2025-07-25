"""
This module provides the `Stock` class, which serves as the main API for accessing individual Thai stock fundamental data.
"""

import arrow
import pandas as pd

from thaifin.sources.finnomena.model import QuarterFinancialSheetDatum
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
        self.language: str = language
        self.info: SecurityData = ThaiSecuritiesDataService().get_stock(
            self.symbol_upper, language=self.language
        )
        self.updated: arrow.Arrow = arrow.utcnow()

    class SafeProperty:
        """Descriptor for safely accessing attributes with a default value.
        This allows for cleaner access to attributes that may not always be present.
        Usage:
        symbol = SafeProperty('info', 'symbol')
        company_name = SafeProperty('info', 'name')
        """

        def __init__(self, obj_attr: str, field_attr: str, default: str = "-"):
            self.obj_attr: str = obj_attr
            self.field_attr: str = field_attr
            self.default: str = default

        def __get__(self, instance, owner):
            if instance is None:
                return self
            obj: SecurityData = getattr(instance, self.obj_attr)
            value: str | None = getattr(obj, self.field_attr, None)
            return value if value else self.default

    symbol = SafeProperty("info", "symbol")
    company_name = SafeProperty("info", "name")
    industry = SafeProperty("info", "industry")
    sector = SafeProperty("info", "sector")
    market = SafeProperty("info", "market")
    address = SafeProperty("info", "address")
    website = SafeProperty("info", "web")

    @property
    def quarter_dataframe(self) -> pd.DataFrame:
        """
        The quarterly financial data as a pandas DataFrame.

        Returns:
            pd.DataFrame: The DataFrame containing quarterly financial data.
        """
        fundamental: list[QuarterFinancialSheetDatum] | list[dict] = (
            FinnomenaService().get_financial_sheet(
                self.symbol_upper, language=self.language
            )
        )
        if not fundamental:
            raise ValueError(
                f"No financial sheet data available for stock {self.symbol_upper}."
            )

        if self.language == "th" and isinstance(fundamental[0], dict):
            # Handle Thai data (list of dicts)
            df: pd.DataFrame = pd.DataFrame(fundamental)

            # Remove security_id column if it exists
            security_id_col = "รหัสหลักทรัพย์"
            if security_id_col in df.columns:
                df = df.drop(columns=[security_id_col])

        else:
            # For English, fundamental is a list of QuarterFinancialSheetDatum
            # Convert all to dicts excluding security_id
            dicts: list[dict] = []
            for item in fundamental:
                if isinstance(item, QuarterFinancialSheetDatum):
                    dicts.append(item.model_dump(exclude={"security_id"}))
                elif isinstance(item, dict):
                    dicts.append({k: v for k, v in item.items() if k != "security_id"})
            df = pd.DataFrame(dicts)

        # Quarter 9 means yearly values - filter for quarterly data only
        quarter_col: str = "ไตรมาส" if self.language == "th" else "quarter"
        fiscal_col: str = "ปีการเงิน" if self.language == "th" else "fiscal"
        df = df[df[quarter_col] != 9]

        if self.language == "th":
            df["ช่วงเวลา"] = (
                df[fiscal_col].astype(str) + "Q" + df[quarter_col].astype(str)
            )
            df = df.set_index("ช่วงเวลา")
        else:
            df["time"] = df[fiscal_col].astype(str) + "Q" + df[quarter_col].astype(str)
            df = df.set_index("time")

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
        fundamental: list[QuarterFinancialSheetDatum] | list[dict] = (
            FinnomenaService().get_financial_sheet(
                self.symbol_upper, language=self.language
            )
        )
        if self.language == "th" and isinstance(fundamental[0], dict):
            # Handle Thai data (list of dicts)
            df: pd.DataFrame = pd.DataFrame(fundamental)
            # Remove security_id column if it exists
            security_id_col = "รหัสหลักทรัพย์"
            if security_id_col in df.columns:
                df = df.drop(columns=[security_id_col])
        else:
            # For English, fundamental is a list of QuarterFinancialSheetDatum
            # Convert all to dicts excluding security_id
            dicts: list[dict] = []
            for item in fundamental:
                if isinstance(item, QuarterFinancialSheetDatum):
                    dicts.append(item.model_dump(exclude={"security_id"}))
                elif isinstance(item, dict):
                    dicts.append({k: v for k, v in item.items() if k != "security_id"})
            df = pd.DataFrame(dicts)
        # Quarter 9 means yearly values - filter for yearly data only
        quarter_col: str = "ไตรมาส" if self.language == "th" else "quarter"
        fiscal_col: str = "ปีการเงิน" if self.language == "th" else "fiscal"
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
