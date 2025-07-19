"""
This module defines Pydantic models for handling data from the Finnomena API.

Classes:
- ListingDatum: Represents a stock listing with details like name, security ID, and exchange.
- FinnomenaListResponse: Represents the response structure for a list of stock listings.
- QuarterFinancialSheetDatum: Represents detailed financial data for a stock for a specific quarter.
- FinancialSheetsResponse: Represents the response structure for quarterly financial sheet data.

Features:
- Ensures type safety and validation for data retrieved from the Finnomena API.
- Provides a structured representation of financial and stock listing data.
"""

from typing import Optional
from pydantic import BaseModel, Field

class ListingDatum(BaseModel):
    """Model representing a stock listing."""
    name: str = Field(..., description="The stock symbol.")
    th_name: str = Field(..., description="The Thai name of the stock.")
    en_name: str = Field(..., description="The English name of the stock.")
    security_id: str = Field(..., description="The security ID of the stock.")
    exchange: str = Field(..., description="The exchange where the stock is listed.")

    class Config:
        """
        Configuration for the Pydantic model.
        Allows extra fields in the model.
        """
        extra = "allow"
class FinnomenaListResponse(BaseModel):
    """Model representing a list response from the Finnomena API."""
    status: bool = Field(..., description="Indicates if the request was successful.")
    statusCode: int = Field(..., description="The status code of the response.")
    data: list[ListingDatum] = Field(..., description="The list of stock listings.")

class QuarterFinancialSheetDatum(BaseModel):
    """Model representing financial data for a quarter."""
    security_id: str = Field(..., description="The security ID of the stock.")
    fiscal: int = Field(..., description="The fiscal year.")
    quarter: int = Field(..., description="The quarter.")
    cash: Optional[str] = Field(None, description="The cash balance.")
    da: Optional[str] = Field(None, description="Depreciation and amortization.")
    debt_to_equity: Optional[str] = Field(None, description="Debt to equity ratio.")
    equity: Optional[str] = Field(None, description="Total equity.")
    earning_per_share: Optional[str] = Field(None, description="Earnings per share.")
    earning_per_share_yoy: Optional[str] = Field(None, description="Earnings per share year over year.")
    earning_per_share_qoq: Optional[str] = Field(None, description="Earnings per share quarter over quarter.")
    gpm: Optional[str] = Field(None, description="Gross profit margin.")
    gross_profit: Optional[str] = Field(None, description="Gross profit.")
    net_profit: Optional[str] = Field(None, description="Net profit.")
    net_profit_yoy: Optional[str] = Field(None, description="Net profit year over year.")
    net_profit_qoq: Optional[str] = Field(None, description="Net profit quarter over quarter.")
    npm: Optional[str] = Field(None, description="Net profit margin.")
    revenue: Optional[str] = Field(None, description="Revenue.")
    revenue_yoy: Optional[str] = Field(None, description="Revenue year over year.")
    revenue_qoq: Optional[str] = Field(None, description="Revenue quarter over quarter.")
    roa: Optional[str] = Field(None, description="Return on assets.")
    roe: Optional[str] = Field(None, description="Return on equity.")
    sga: Optional[str] = Field(None, description="Selling, general and administrative expenses.")
    sga_per_revenue: Optional[str] = Field(None, description="Selling, general and administrative expenses per revenue.")
    total_debt: Optional[str] = Field(None, description="Total debt.")
    dividend_yield: Optional[str] = Field(None, description="Dividend yield.")
    book_value_per_share: Optional[str] = Field(None, description="Book value per share.")
    close: Optional[str] = Field(None, description="Closing price.")
    mkt_cap: Optional[str] = Field(None, description="Market capitalization.")
    price_earning_ratio: Optional[str] = Field(None, description="Price to earnings ratio.")
    price_book_value: Optional[str] = Field(None, description="Price to book value.")
    ev_per_ebit_da: Optional[str] = Field(None, description="Enterprise value to EBITDA.")
    ebit_dattm: Optional[str] = Field(None, description="EBITDA.")
    paid_up_capital: Optional[str] = Field(None, description="Paid-up capital.")
    cash_cycle: Optional[str] = Field(None, description="Cash cycle.")
    operating_activities: Optional[str] = Field(None, description="Operating activities.")
    investing_activities: Optional[str] = Field(None, description="Investing activities.")
    financing_activities: Optional[str] = Field(None, description="Financing activities.")
    asset: Optional[str] = Field(None, description="Total assets.")
    end_of_year_date: Optional[str] = Field(None, description="End of year date.")

class FinancialSheetsResponse(BaseModel):
    """Model representing the financial sheets response."""
    status: bool = Field(..., description="Indicates if the request was successful.")
    statusCode: int = Field(..., description="The status code of the response.")
    data: list[QuarterFinancialSheetDatum] = Field(..., description="The list of quarterly financial sheet data.")