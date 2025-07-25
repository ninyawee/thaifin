"""
Test file for Thai Securities Data source integration.

This file demonstrates how to use the new Thai Securities Data source
and provides basic validation tests.
"""

from unittest.mock import Mock, patch
from thaifin.sources.thai_securities_data import (
    ThaiSecuritiesDataService,
    SecurityData,
)


class TestThaiSecuritiesDataService:
    """Test cases for ThaiSecuritiesDataService class"""

    def test_service_creation(self):
        """Test creating a service instance"""
        service = ThaiSecuritiesDataService()
        assert service is not None

    def test_get_stock_mock(self):
        """Test getting stock data through service"""
        service = ThaiSecuritiesDataService()

        # Mock the API calls
        mock_security = SecurityData(
            symbol="PTT",
            name="PTT Public Company Limited",
            market="SET",
            industry="Energy",
            sector="Resources",
            address="555 Vibhavadi Rangsit Road",
            zip="10900",
            tel="0-2537-2000",
            fax="0-2537-2001",
            web="https://www.pttplc.com",
        )

        with patch(
            "thaifin.sources.thai_securities_data.service.get_securities_data"
        ) as mock_get:
            mock_get.return_value = [mock_security]

            result = service.get_stock("PTT")

            assert result is not None
            assert result.symbol == "PTT"
            assert result.market == "SET"

    def test_list_stocks_mock(self):
        """Test listing all stocks"""
        service = ThaiSecuritiesDataService()

        # Mock the API calls
        mock_securities = [
            SecurityData(
                symbol="PTT",
                name="PTT Public Company Limited",
                market="SET",
                industry="Energy",
                sector="Resources",
                address="555 Vibhavadi Rangsit Road",
                zip="10900",
                tel="0-2537-2000",
                fax="0-2537-2001",
                web="https://www.pttplc.com",
            ),
            SecurityData(
                symbol="AOT",
                name="Airports of Thailand Public Company Limited",
                market="SET",
                industry="Transportation",
                sector="Services",
                address="222 Don Mueang",
                zip="10210",
                tel="0-2535-1111",
                fax="0-2535-1112",
                web="https://www.airportthai.co.th",
            ),
        ]

        with patch(
            "thaifin.sources.thai_securities_data.service.get_securities_data"
        ) as mock_get:
            mock_get.return_value = mock_securities

            result = service.get_stock_list()

            assert result is not None
            assert len(result) == 2
            assert result[0].symbol == "PTT"
            assert result[1].symbol == "AOT"


# Functional test with actual network calls (only run if explicitly needed)
def test_thai_securities_service_real():
    """
    Test the ThaiSecuritiesDataService with actual API calls.

    This test requires network connectivity and may be slow.
    It demonstrates actual usage of the service.
    """
    service = ThaiSecuritiesDataService()

    # Test getting a well-known stock
    ptt_stock = service.get_stock("PTT")
    assert ptt_stock is not None
    assert ptt_stock.symbol == "PTT"
    assert ptt_stock.market in ["SET", "mai"]

    # Test getting stock in Thai language
    ptt_stock_th = service.get_stock("PTT", language="th")
    assert ptt_stock_th is not None
    assert ptt_stock_th.symbol == "PTT"

    # Test listing all stocks
    all_stocks = service.get_stock_list()
    assert len(all_stocks) > 0
    assert all(isinstance(stock, SecurityData) for stock in all_stocks)
