# 🇹🇭 Thai Language Support Example for ThaiFin

"""
This example demonstrates how to use the new Thai language support
in ThaiFin to get financial data with Thai field names.
"""

from thaifin.sources.finnomena.service import FinnomenaService
from thaifin.sources.finnomena.model import QuarterFinancialSheetDatum

def main():
    # Initialize the service
    service = FinnomenaService()
    
    # Get financial data in English (default)
    print("📊 English Financial Data:")
    print("=" * 30)
    
    english_data = service.get_financial_sheet("CPALL", language="en")
    latest_quarter = english_data[0]
    
    # Type checking for English data
    if isinstance(latest_quarter, QuarterFinancialSheetDatum):
        print(f"Revenue: {latest_quarter.revenue}")
        print(f"Net Profit: {latest_quarter.net_profit}")
        print(f"Gross Profit: {latest_quarter.gross_profit}")
        print(f"ROE: {latest_quarter.roe}%")
        print(f"ROA: {latest_quarter.roa}%")
        print(f"P/E Ratio: {latest_quarter.price_earning_ratio}")
    
    print("\n" + "=" * 50 + "\n")
    
    # Get financial data in Thai
    print("📊 ข้อมูลทางการเงินภาษาไทย:")
    print("=" * 30)
    
    thai_data = service.get_financial_sheet("CPALL", language="th")
    latest_quarter_th = thai_data[0]
    
    # Type checking for Thai data
    if isinstance(latest_quarter_th, dict):
        print(f"รายได้รวม: {latest_quarter_th['รายได้รวม']}")
        print(f"กำไรสุทธิ: {latest_quarter_th['กำไรสุทธิ']}")
        print(f"กำไรขั้นต้น: {latest_quarter_th['กำไรขั้นต้น']}")
        print(f"ROE (%): {latest_quarter_th['ROE (%)']}")
        print(f"ROA (%): {latest_quarter_th['ROA (%)']}")
        print(f"P/E (เท่า): {latest_quarter_th['P/E (เท่า)']}")
    
    print("\n" + "=" * 50 + "\n")
    
    # Show all available Thai field names
    print("📋 รายการฟิลด์ทั้งหมดภาษาไทย:")
    print("=" * 35)
    
    if isinstance(thai_data[0], dict):
        for i, key in enumerate(thai_data[0].keys(), 1):
            print(f"{i:2d}. {key}")

if __name__ == "__main__":
    main()
