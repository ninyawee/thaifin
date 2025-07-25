"""
Thai Securities Data source for ThaiFin library.

This module provides access to Thai stock market data from Thai Securities Data API,
offering comprehensive financial data, market data, and company information.
"""

from .api import (
    get_meta_data,
    get_securities_data,
)

from .models import (
    MetaData,
    SecurityData,
)

from .service import ThaiSecuritiesDataService

__all__ = [
    # API functions
    "get_meta_data",
    "get_securities_data",
    # Data models
    "MetaData",
    "SecurityData",
    # Service class
    "ThaiSecuritiesDataService",
]
