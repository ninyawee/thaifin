"""
This module provides the `Stocks` class, which handles collection operations for Thai stocks.
"""

import re
import pandas as pd
from rapidfuzz import fuzz
from typing import List, TYPE_CHECKING

from thaifin.sources.thai_securities_data import ThaiSecuritiesDataService
from thaifin.sources.thai_securities_data.models import SecurityData

if TYPE_CHECKING:
    from thaifin.stock import Stock


class Stocks:
    """
    A utility class for working with collections of Thai stocks.
    
    This class provides methods for searching, listing, and filtering stocks.
    For individual stock operations, use the Stock class.
    """

    @classmethod
    def search(cls, query: str, limit: int = 5, language: str = "auto") -> List['Stock']:
        """
        Smart search for stocks with Thai/English auto-detection.
        
        Search priority:
        1. Exact symbol match
        2. Fuzzy symbol matching  
        3. Company name fuzzy matching
        
        Args:
            query (str): Search term (can be Thai or English)
            limit (int): Maximum number of results to return. Defaults to 5.
            language (str): Language preference ("en", "th", or "auto"). Defaults to "auto".
            
        Returns:
            List[Stock]: List of Stock objects ranked by relevance.
            
        Examples:
            >>> Stocks.search('cp')          # Find CP stocks
            >>> Stocks.search('ซีพี')        # Find CP stocks in Thai
            >>> Stocks.search('bank')        # Find banking stocks
            >>> Stocks.search('ธนาคาร')      # Find banks in Thai
        """
        # Import here to avoid circular imports
        from thaifin.stock import Stock
        
        # Auto-detect language if needed
        if language == "auto":
            language = cls._detect_language(query)
        
        # Get stock list
        thai_service = ThaiSecuritiesDataService()
        stock_list = thai_service.get_stock_list(language=language)
        
        # Multi-stage search with weighted scoring
        matches = cls._smart_search(query, stock_list, limit)
        
        # Return Stock objects
        return [Stock(stock.symbol, language=language) for stock in matches]

    @classmethod
    def list(cls, language: str = "en") -> List[str]:
        """
        Get a list of all available stock symbols.
        
        Args:
            language (str): Language preference ("en" or "th"). Defaults to "en".
            
        Returns:
            List[str]: List of stock symbols.
            
        Examples:
            >>> symbols = Stocks.list()
            >>> print(symbols[:5])  # ['AAAV', 'ABBE', 'ABC', 'ABICO', 'ABPIF']
        """
        thai_service = ThaiSecuritiesDataService()
        stock_list = thai_service.get_stock_list(language=language)
        return [stock.symbol for stock in stock_list]

    @classmethod
    def list_with_names(cls, language: str = "en") -> pd.DataFrame:
        """
        Get a DataFrame with all stocks including names and basic info.
        
        Args:
            language (str): Language preference ("en" or "th"). Defaults to "en".
            
        Returns:
            pd.DataFrame: DataFrame with columns: symbol, name, industry, sector, market
            
        Examples:
            >>> df = Stocks.list_with_names()
            >>> print(df.head())
            >>> df_th = Stocks.list_with_names(language="th")
        """
        thai_service = ThaiSecuritiesDataService()
        stock_list = thai_service.get_stock_list(language=language)
        
        data = []
        for stock in stock_list:
            data.append({
                'symbol': stock.symbol,
                'name': stock.name,
                'industry': stock.industry,
                'sector': stock.sector,
                'market': stock.market
            })
        
        return pd.DataFrame(data)

    @classmethod
    def filter_by_sector(cls, sector: str, language: str = "en") -> List[str]:
        """
        Filter stocks by sector.
        
        Args:
            sector (str): Sector name to filter by
            language (str): Language preference ("en" or "th"). Defaults to "en".
            
        Returns:
            List[str]: List of stock symbols in the specified sector.
            
        Examples:
            >>> banking_stocks = Stocks.filter_by_sector('Banking')
            >>> energy_stocks = Stocks.filter_by_sector('พลังงาน', language='th')
        """
        thai_service = ThaiSecuritiesDataService()
        stock_list = thai_service.get_stock_list(language=language)
        
        return [stock.symbol for stock in stock_list 
                if stock.sector and sector.lower() in stock.sector.lower()]

    @classmethod
    def filter_by_market(cls, market: str, language: str = "en") -> List[str]:
        """
        Filter stocks by market.
        
        Args:
            market (str): Market name ('SET' or 'mai')
            language (str): Language preference ("en" or "th"). Defaults to "en".
            
        Returns:
            List[str]: List of stock symbols in the specified market.
            
        Examples:
            >>> set_stocks = Stocks.filter_by_market('SET')
            >>> mai_stocks = Stocks.filter_by_market('mai')
        """
        thai_service = ThaiSecuritiesDataService()
        stock_list = thai_service.get_stock_list(language=language)
        
        return [stock.symbol for stock in stock_list 
                if stock.market and market.upper() == stock.market.upper()]

    @staticmethod
    def _detect_language(text: str) -> str:
        """
        Auto-detect if text contains Thai characters.
        
        Args:
            text (str): Text to analyze
            
        Returns:
            str: "th" if Thai characters detected, "en" otherwise
        """
        # Thai Unicode range: \u0E00-\u0E7F
        thai_pattern = re.compile(r'[\u0E00-\u0E7F]')
        return "th" if thai_pattern.search(text) else "en"

    @staticmethod
    def _smart_search(query: str, stock_list: List[SecurityData], limit: int) -> List[SecurityData]:
        """
        Perform smart search with multi-stage matching and scoring.
        
        Args:
            query (str): Search query
            stock_list (List[SecurityData]): List of stocks to search
            limit (int): Maximum results to return
            
        Returns:
            List[SecurityData]: Ranked list of matching stocks
        """
        query_lower = query.lower()
        scored_matches = []
        
        for stock in stock_list:
            score = 0
            symbol_lower = stock.symbol.lower()
            name_lower = stock.name.lower() if stock.name else ""
            
            # Stage 1: Exact symbol match (highest priority)
            if symbol_lower == query_lower:
                score = 1000
            # Stage 2: Symbol starts with query
            elif symbol_lower.startswith(query_lower):
                score = 900
            # Stage 3: Symbol contains query
            elif query_lower in symbol_lower:
                score = 800
            else:
                # Stage 4: Fuzzy symbol matching
                symbol_ratio = fuzz.ratio(query_lower, symbol_lower)
                if symbol_ratio > 60:
                    score = 700 + symbol_ratio
                
                # Stage 5: Company name fuzzy matching
                if name_lower:
                    name_ratio = fuzz.partial_ratio(query_lower, name_lower)
                    if name_ratio > 60:
                        name_score = 500 + name_ratio
                        score = max(score, name_score)
            
            if score > 0:
                scored_matches.append((score, stock))
        
        # Sort by score (descending) and return top matches
        scored_matches.sort(key=lambda x: x[0], reverse=True)
        return [stock for score, stock in scored_matches[:limit]]


if __name__ == "__main__":
    # Example usage
    print("=== Stocks Class Demo ===")
    
    # Search examples
    print("\n1. Search for 'cp':")
    cp_stocks = Stocks.search('cp', limit=3)
    for stock in cp_stocks:
        print(f"  {stock.symbol}: {stock.company_name}")
    
    print("\n2. Search for 'ธนาคาร' (bank in Thai):")
    bank_stocks = Stocks.search('ธนาคาร', limit=3)
    for stock in bank_stocks:
        print(f"  {stock.symbol}: {stock.company_name}")
    
    # List examples
    print("\n3. Total stocks available:", len(Stocks.list()))
    
    print("\n4. First 5 stocks with details:")
    df = Stocks.list_with_names()
    print(df.head())
    
    # Filter examples
    print("\n5. Banking sector stocks:")
    banking = Stocks.filter_by_sector('Banking')
    print(f"  Found {len(banking)} banking stocks: {banking[:5]}")
    
    print("\n6. mai market stocks:")
    mai_stocks = Stocks.filter_by_market('mai')
    print(f"  Found {len(mai_stocks)} mai stocks: {mai_stocks[:5]}")
