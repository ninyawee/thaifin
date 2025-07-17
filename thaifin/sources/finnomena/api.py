from cachetools import cached, TTLCache
from pydantic import UUID4
from tenacity import retry, stop_after_attempt, wait_exponential
import httpx


from thaifin.sources.finnomena.model import FinancialSheetsResponse, StockListingResponse


base_url = "https://www.finnomena.com/market-info/api/public"

@cached(cache=TTLCache(maxsize=12345, ttl=24 * 60 * 60))
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
def get_financial_sheet(security_id: UUID4):
    url = f"{base_url}/stock/summary/{security_id}"

    with httpx.Client() as client:
        response = client.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

    return FinancialSheetsResponse.model_validate_json(response.text)




@cached(cache=TTLCache(maxsize=1, ttl=24 * 60 * 60))
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
def get_stock_list() -> StockListingResponse:
    url = f"{base_url}/stock/list"
    params = {"exchange": "TH"}

    with httpx.Client() as client:
        response = client.get(url, params=params)
        response.raise_for_status()

    # Debugging: Log the raw API response
    print("Raw API Response:", response.text)

    return StockListingResponse.model_validate_json(response.text)
