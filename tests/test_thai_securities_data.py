"""
Test file for Thai Securities Data source integration.

This file demonstrates how to use the new Thai Securities Data source
and provides basic validation tests.
"""

from unittest.mock import Mock, patch
from thaifin.sources.thai_securities_data import (
    get_meta_data,
    get_securities_data,
    MetaData,
    SecurityData,
    ThaiSecuritiesDataService,
)


class TestThaiSecuritiesDataAPI:
    """Test cases for Thai Securities Data API functions"""

    def test_get_meta_data_mock(self):
        """Test meta data API with mocked response"""
        # Mock response data
        mock_meta = MetaData(
            securities=[
                {
                    "symbol": "PTT",
                    "name": "PTT Public Company Limited",
                    "industry": "Energy",
                    "sector": "Resources",
                    "market": "SET",
                }
            ]
        )

        with patch(
            "thaifin.sources.thai_securities_data.api.httpx.Client"
        ) as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_meta.model_dump()
            mock_response_obj.raise_for_status.return_value = None
            mock_client.return_value.__enter__.return_value.get.return_value = (
                mock_response_obj
            )

            result = get_meta_data()

            assert result is not None
            assert len(result.securities) == 1
            assert result.securities[0]["symbol"] == "PTT"

    def test_get_securities_data_mock(self):
        """Test securities data API with mocked response"""
        # Mock securities data
        mock_security = SecurityData(
            symbol="PTT",
            name="PTT Public Company Limited",
            market="SET",
            industry="Energy",
            sector="Resources",
            stock_type="Common Stock",
        )

        with patch(
            "thaifin.sources.thai_securities_data.api.httpx.Client"
        ) as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = {"PTT": mock_security.model_dump()}
            mock_response_obj.raise_for_status.return_value = None
            mock_client.return_value.__enter__.return_value.get.return_value = (
                mock_response_obj
            )

            result = get_securities_data("PTT")

            assert result is not None
            assert "PTT" in result
            assert result["PTT"]["symbol"] == "PTT"
            assert result["PTT"]["market"] == "SET"


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
            stock_type="Common Stock",
        )

        with patch(
            "thaifin.sources.thai_securities_data.service.get_securities_data"
        ) as mock_get:
            mock_get.return_value = {"PTT": mock_security.model_dump()}

            result = service.get_stock("PTT")

            assert result is not None
            assert result.symbol == "PTT"
            assert result.market == "SET"


# Functional test with actual network calls
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
    all_stocks = service.list_stocks()
    assert len(all_stocks) > 0
    assert all(isinstance(stock, str) for stock in all_stocks)
