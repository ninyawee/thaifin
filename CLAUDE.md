# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Lint/Test Commands

### Running Tests
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_stocks_api.py

# Run tests requiring internet connection
uv run pytest tests/public_internet_tests/

# Run tests with verbose output
uv run pytest -v
```

### Linting
```bash
# Run ruff linter
ruff check . --fix

# Format code with ruff
ruff format .
```

### Documentation
```bash
# Generate documentation with pdoc
just docs
# Or directly:
pdoc ./thaifin/ -o ./docs/
```

### Model Generation
```bash
# Generate Pydantic models from JSON schemas
just models
```

## High-level Architecture

### Core Components

1. **Stock Class** (`thaifin/stock.py`): 
   - Handles individual stock operations
   - Fetches and caches financial data from multiple sources
   - Provides pandas DataFrames for quarterly and yearly financial data
   - Uses `SafeProperty` descriptor pattern for safe attribute access

2. **Stocks Class** (`thaifin/stocks.py`):
   - Handles collection operations (search, list, filter)
   - Smart search with Thai/English auto-detection using rapidfuzz
   - Filtering by sector and market
   - No state - all methods are classmethods

3. **Data Sources** (`thaifin/sources/`):
   - **Finnomena**: Provides historical financial data (10+ years)
     - API client with retry logic (tenacity)
     - Caching with cachetools
     - Returns quarterly/yearly financial sheets
   - **Thai Securities Data**: Provides stock metadata
     - Company names, sectors, industries, markets
     - Multi-language support (Thai/English)

### Data Flow

1. User creates `Stock('PTT')` → fetches metadata from Thai Securities Data
2. Accessing `stock.quarter_dataframe` → fetches financial data from Finnomena API
3. Data is cached to reduce API calls and improve performance
4. All data returned as pandas DataFrames or Pydantic models

### Key Design Patterns

- **Service Pattern**: Each data source has a service class handling API communication
- **Model Pattern**: Pydantic models for data validation and type safety
- **Caching**: Using cachetools for API response caching
- **Retry Logic**: Using tenacity for robust API calls with exponential backoff
- **Lazy Loading**: Financial data only fetched when accessed

### Dependencies

- HTTP: `httpx` for API calls
- Data: `pandas`, `numpy` for data manipulation
- Validation: `pydantic` for data models
- Search: `rapidfuzz` for fuzzy string matching
- Caching: `cachetools` for API response caching
- Retry: `tenacity` for robust API calls