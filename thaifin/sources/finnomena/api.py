from furl import furl
from cachetools import cached, TTLCache
from pydantic import UUID4
from tenacity import retry, stop_after_attempt, wait_exponential
import requests


from thaifin.sources.finnomena.model import FinancialSheetsResponse, StockListingResponse


base_url = furl("https://www.finnomena.com/market-info/api/public")

@cached(cache=TTLCache(maxsize=12345, ttl=24 * 60 * 60))
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
def get_financial_sheet(security_id: UUID4):
    url = base_url / "stock/summary"
    url = url / str(security_id)

    response = requests.request(
        "GET", url
    )

    return FinancialSheetsResponse.model_validate_json(response.content)




@cached(cache=TTLCache(maxsize=1, ttl=24 * 60 * 60))
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
def get_stock_list() -> StockListingResponse:
    url = base_url / "stock/list"
    url.args["exchange"] = "TH"

    response = requests.request("GET", url)

    return StockListingResponse.model_validate_json(response.content)
