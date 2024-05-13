import pytest
from thaifin.sources.finnomena import get_financial_sheet, get_stock_list
from thaifin.sources.finnomena.model import FinancialSheetsResponse, StockListingResponse
import uuid



def test_get_financial_sheet_real_api():
    # Execute
    ptt_stock_id = uuid.UUID("9d80ae13-226f-4da0-88aa-a709bb139d4c")  # Assuming this UUID is a valid security_id for testing
    result = get_financial_sheet(ptt_stock_id)
    
    # Verify
    assert isinstance(result, FinancialSheetsResponse)
    assert result.status == True
    assert result.statusCode == 200
    assert len(result.data) > 0

def test_get_stock_list_real_api():
    # Execute
    result = get_stock_list()
    
    # Verify
    assert isinstance(result, StockListingResponse)
    assert result.status == True
    assert result.statusCode == 200
    assert len(result.data) > 0
    assert any(stock.name == "PTT" for stock in result.data)  # Assuming 'PTT' is a valid stock name for testing

