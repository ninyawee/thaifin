"""
This module provides functions to interact with the Finnomena API.

Functions:
- get_financial_sheet: Fetches financial sheet data for a given security ID.
- get_stock_list: Retrieves a list of stocks available on the Finnomena platform.

Features:
- Caching: Results are cached for 24 hours to reduce API calls.
- Retry Logic: Automatically retries failed requests with exponential backoff.

Dependencies:
- cachetools: For caching API responses.
- tenacity: For retrying failed API calls.
- httpx: For making HTTP requests.
"""

from cachetools import cached, TTLCache
from pydantic import UUID4
from tenacity import retry, stop_after_attempt, wait_exponential
import httpx

from thaifin.sources.finnomena.model import (
    FinancialSheetsResponse,
    FinnomenaListResponse,
)

base_url = "https://www.finnomena.com/market-info/api/public"


@cached(cache=TTLCache(maxsize=12345, ttl=24 * 60 * 60))
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True,
)
def get_financial_sheet(security_id: UUID4):
    url = f"{base_url}/stock/summary/{security_id}"
    try:
        with httpx.Client() as client:
            response: httpx.Response = client.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors
            if response.status_code != 200:
                raise ValueError(
                    f"Failed to fetch financial sheet. Status code: {response.status_code}"
                )
            if not response.text:
                raise ValueError("No financial sheet data available in the response.")

        return FinancialSheetsResponse.model_validate_json(response.text)

    except Exception as e:
        raise ValueError(
            f"An error occurred while fetching financial sheet: {e}"
        ) from e


@cached(cache=TTLCache(maxsize=1, ttl=24 * 60 * 60))
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True,
)
def get_stock_list() -> FinnomenaListResponse:
    url: str = f"{base_url}/stock/list"
    params: dict[str, str] = {"exchange": "TH"}

    try:
        with httpx.Client() as client:
            response: httpx.Response = client.get(url, params=params)
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError(
                    f"Failed to fetch stock list. Status code: {response.status_code}"
                )
            if not response.text:
                raise ValueError("No stock data available in the response.")
        return FinnomenaListResponse.model_validate_json(response.text)

    except Exception as e:
        raise ValueError(f"An error occurred while fetching stock list: {e}") from e


if __name__ == "__main__":
    # Example usage
    try:
        stock_list: FinnomenaListResponse = get_stock_list()
        print("Stock List:", stock_list)
    except Exception as e:
        print("Error fetching stock list:", e)
