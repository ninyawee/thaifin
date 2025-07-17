from cachetools import cached, TTLCache
from tenacity import retry, stop_after_attempt, wait_exponential
import httpx
from typing import Optional

from thaifin.sources.thai_securities_data.model import (
    ThaiSecuritiesDataResponse, 
    StockListResponse, 
    FinancialDataResponse
)

from thaifin.sources.thai_securities_data.models import MetaData
# Base URL for Thai Securities Data API
base_url = "https://raw.githubusercontent.com/lumduan/thai-securities-data/main"

@cached(cache=TTLCache(maxsize=1000, ttl=24 * 60 * 60))  # 24 hours cache
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
def get_meta_data() -> MetaData:
    """
    Get metadata for Thai Securities Data.
    
    Returns:
        MetaData: Metadata object containing last updated time, total securities, market and sector data.
    """
    url = f"{base_url}/metadata.json"
    
    with httpx.Client() as client:
        response = client.get(url)
        response.raise_for_status()
    
    return MetaData.model_validate_json(response.text)

@cached(cache=TTLCache(maxsize=12345, ttl=24 * 60 * 60))
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
def get_stock_list() -> StockListResponse:
    """
    Get list of all available stocks from Thai Securities Data.
    
    Returns:
        StockListResponse: Response containing list of stock data
    """
    url = f"{base_url}/stocks"
    
    with httpx.Client() as client:
        response = client.get(url)
        response.raise_for_status()
    
    return StockListResponse.model_validate_json(response.text)

@cached(cache=TTLCache(maxsize=12345, ttl=24 * 60 * 60))
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
def get_financial_data(symbol: str, period: Optional[str] = None) -> FinancialDataResponse:
    """
    Get financial data for a specific stock from Thai Securities Data.
    
    Args:
        symbol (str): Stock symbol (e.g., 'PTT', 'KBANK')
        period (str, optional): Period for data ('quarterly', 'yearly', or 'all')
    
    Returns:
        FinancialDataResponse: Response containing financial data
    """
    url = f"{base_url}/stocks/{symbol}/financials"
    params = {}
    if period:
        params["period"] = period
    
    with httpx.Client() as client:
        response = client.get(url, params=params)
        response.raise_for_status()
    
    return FinancialDataResponse.model_validate_json(response.text)

@cached(cache=TTLCache(maxsize=1000, ttl=24 * 60 * 60))
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
def get_stock_info(symbol: str) -> ThaiSecuritiesDataResponse:
    """
    Get detailed information for a specific stock.
    
    Args:
        symbol (str): Stock symbol (e.g., 'PTT', 'KBANK')
    
    Returns:
        ThaiSecuritiesDataResponse: Response containing stock information
    """
    url = f"{base_url}/stocks/{symbol}"
    
    with httpx.Client() as client:
        response = client.get(url)
        response.raise_for_status()
    
    return ThaiSecuritiesDataResponse.model_validate_json(response.text)

@cached(cache=TTLCache(maxsize=1000, ttl=6 * 60 * 60))  # 6 hours cache for market data
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
def get_market_data(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> ThaiSecuritiesDataResponse:
    """
    Get market data (price, volume) for a specific stock.
    
    Args:
        symbol (str): Stock symbol (e.g., 'PTT', 'KBANK')
        start_date (str, optional): Start date in YYYY-MM-DD format
        end_date (str, optional): End date in YYYY-MM-DD format
    
    Returns:
        ThaiSecuritiesDataResponse: Response containing market data
    """
    url = f"{base_url}/stocks/{symbol}/market-data"
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    
    with httpx.Client() as client:
        response = client.get(url, params=params)
        response.raise_for_status()
    
    return ThaiSecuritiesDataResponse.model_validate_json(response.text)
