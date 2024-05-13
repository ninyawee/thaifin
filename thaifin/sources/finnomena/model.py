from typing import Any, Optional
from pydantic import BaseModel


class FinnomenaBaseResponse(BaseModel):
    status: bool
    statusCode: int
    data: list[dict[str, Any]]

class ListingDatum(BaseModel):
    name: str
    th_name: str
    en_name: str
    security_id: str
    exchange: str

class StockListingResponse(FinnomenaBaseResponse):
    data: list[ListingDatum]

class QuarterFinancialSheetDatum(BaseModel):
    security_id: str
    fiscal: int
    quarter: int
    cash: Optional[str]
    da: Optional[str]
    debt_to_equity: Optional[str]
    equity: Optional[str]
    earning_per_share: Optional[str]
    earning_per_share_yoy: Optional[str]
    earning_per_share_qoq: Optional[str]
    gpm: Optional[str]
    gross_profit: Optional[str]
    net_profit: Optional[str]
    net_profit_yoy: Optional[str]
    net_profit_qoq: Optional[str]
    npm: Optional[str]
    revenue: Optional[str]
    revenue_yoy: Optional[str]
    revenue_qoq: Optional[str]
    roa: Optional[str]
    roe: Optional[str]
    sga: Optional[str]
    sga_per_revenue: Optional[str]
    total_debt: Optional[str]
    dividend_yield: Optional[str]
    book_value_per_share: Optional[str]
    close: Optional[str]
    mkt_cap: Optional[str]
    price_earning_ratio: Optional[str]
    price_book_value: Optional[str]
    ev_per_ebit_da: Optional[str]
    ebit_dattm: Optional[str]
    paid_up_capital: Optional[str]
    cash_cycle: Optional[str]
    operating_activities: Optional[str]
    investing_activities: Optional[str]
    financing_activities: Optional[str]
    asset: Optional[str]
    end_of_year_date: Optional[str]


class FinancialSheetsResponse(FinnomenaBaseResponse):
    status: bool
    statusCode: int
    data: list[QuarterFinancialSheetDatum]
