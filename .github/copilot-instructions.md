# 🔧 ThaiFin - AI Agent Context

## Project Overview

**ThaiFin** is a Python library that provides easy access to Thai stock fundamental data spanning 10+ years. Created by the same author as PythaiNAV, this library democratizes access to Thai financial market data that was previously only available to investment firms.

## 🎯 Core Purpose

- **Primary Goal**: Provide simple, 3-line access to comprehensive Thai stock fundamental data
- **Target Users**: Data scientists, investors, financial analysts, students working with Thai stock market
- **Value Proposition**: Fast, robust access to 10+ years of financial data with caching and auto-retry capabilities
- **Philosophy**: Make financial data accessible to everyone (ISC License)

## 🏗️ Architecture & Tech Stack

### Core Framework

- **Main API**: Single `Stock` class with intuitive methods (`Stock.search()`, `Stock.list_symbol()`)
- **Data Sources**: Uses dual data sources - Thai Securities Data API for company metadata and Finnomena API for financial data
- **Language Support**: Full multilingual support (English/Thai) for company names and metadata
- **Data Format**: Returns pandas DataFrames for easy analysis and visualization
- **Python Version**: Requires Python 3.11+ for modern features and performance
- **Package Manager**: Uses `uv` for dependency management and execution

### Dependencies

**Core Dependencies:**
- `requests>=2.31.0` & `httpx>=0.27.0` - HTTP client libraries for API calls
- `pandas>=2.0.0` & `numpy>=1.24.0` - Data manipulation and analysis
- `pydantic>=2.7.0` - Data validation and parsing
- `cachetools>=5.0.0` - 24-hour TTL caching to reduce server load
- `tenacity>=8.0.0` - Robust API calls with exponential backoff retry
- `beautifulsoup4>=4.12.0` & `lxml>=5.0.0` - HTML parsing capabilities
- `fuzzywuzzy>=0.18.0` - Company name fuzzy search
- `arrow>=1.3.0` - Date/time handling
- `furl>=2.1.0` - URL manipulation

**Development Dependencies:**
- `pytest>=8.0.0` - Testing framework
- `pdoc>=14.0.0` - Documentation generation
- `jupyter>=1.0.0` - Interactive development

### Design Principles

- **Simplicity**: Minimal code required for common tasks
- **Robustness**: Auto-retry with exponential backoff, comprehensive error handling
- **Performance**: Intelligent caching (24hr TTL) to minimize API calls
- **Data Quality**: Pydantic models ensure type safety and validation
- **User Experience**: Pandas DataFrames for familiar data manipulation

## 📁 Project Structure

```
thaifin/
├── thaifin/                    # Main package
│   ├── __init__.py            # Exports Stock class
│   ├── stock.py               # Main Stock API class
│   ├── models/                # Pydantic data models
│   └── sources/               # Data source implementations
│       ├── finnomena/         # Financial data source
│       │   ├── api.py        # API client with caching/retry
│       │   ├── model.py      # Response models
│       │   └── service.py    # Service layer abstraction
│       └── thai_securities_data/  # Company metadata source
│           ├── api.py        # API client for Thai Securities Data
│           ├── service.py    # Service layer abstraction
│           └── models/       # SecurityData and MetaData models
├── tests/                     # Test suite
│   ├── public_internet_tests/ # Integration tests requiring internet
│   └── sample_data/          # Test data and fixtures
├── samples/                   # Usage examples and notebooks
├── docs/                     # Generated documentation (pdoc)
├── API/                      # Raw API response samples
└── debug/                    # Debug scripts (gitignored)
```

## 🔧 Environment Configuration

### Required Environment Variables

**None required** - The library works out of the box with public APIs. All data sources use publicly accessible endpoints.

### Configuration Loading

- **Caching**: TTLCache with 24-hour expiration automatically configured
- **Retry Logic**: 3 attempts with exponential backoff (4-10 seconds) built-in
- **Rate Limiting**: Handled through caching to respect API providers

## 📊 Data Models & API Structure

### Core API Usage

```python
from thaifin import Stock

# Search for stocks by company name (fuzzy matching)
stocks = Stock.search('จัสมิน', limit=5)

# Get all available stock symbols
symbols = Stock.list_symbol()  # ['PTT', 'KBANK', 'SCB', ...]

# Create stock instance with language support
stock_en = Stock('PTT', language='en')  # English metadata and financial data
stock_th = Stock('PTT', language='th')  # Thai metadata and financial data

# Access financial data (from Finnomena API) - supports both languages
quarterly_data_en = stock_en.quarter_dataframe  # English column names
quarterly_data_th = stock_th.quarter_dataframe  # Thai column names
yearly_data_en = stock_en.yearly_dataframe      # English column names  
yearly_data_th = stock_th.yearly_dataframe      # Thai column names

# Access company metadata (from Thai Securities Data API)
print(stock_en.company_name)    # "PTT PUBLIC COMPANY LIMITED"
print(stock_th.company_name)    # "บริษัท ปตท. จำกัด (มหาชน)"
print(stock_en.industry)        # Industry classification
print(stock_en.sector)          # Sector classification
print(stock_en.market)          # Market (SET/mai)
```

### Financial Data Structure

**QuarterFinancialSheetDatum** contains 38+ financial metrics with full Thai language support:
- **Basic Info**: security_id, fiscal, quarter (English) | รหัสหลักทรัพย์, ปีการเงิน, ไตรมาส (Thai)
- **Profitability**: revenue, net_profit, gross_profit, gpm, npm (English) | รายได้รวม, กำไรสุทธิ, กำไรขั้นต้น, อัตรากำไรขั้นต้น (%), อัตรากำไรสุทธิ (%) (Thai)
- **Financial Ratios**: roe, roa, debt_to_equity, price_earning_ratio (English) | ROE (%), ROA (%), หนี้สิน/ทุน (เท่า), P/E (เท่า) (Thai)
- **Per Share**: earning_per_share, book_value_per_share, dividend_yield (English) | กำไรต่อหุ้น (EPS), มูลค่าหุ้นทางบัญชีต่อหุ้น (บาท), อัตราส่วนเงินปันผลตอบแทน (%) (Thai)
- **Cash Flow**: operating_activities, investing_activities, financing_activities (English) | กระแสเงินสด จากการดำเนินงาน, กระแสเงินสด จากการลงทุน, กระแสเงินสด จากกิจกรรมทางการเงิน (Thai)
- **Growth**: revenue_yoy, net_profit_yoy, earning_per_share_yoy (Year-over-Year) (English) | รายได้รวม การเติบโตเทียบปีก่อนหน้า (%), กำไรสุทธิ การเติบโตเทียบปีก่อนหน้า (%), EPS การเติบโตเทียบปีก่อนหน้า (%) (Thai)
- **Market Data**: close, mkt_cap, ev_per_ebit_da (English) | ราคาล่าสุด (บาท), มูลค่าหลักทรัพย์ตามราคาตลาด (ล้านบาท), EV / EBITDA (Thai)

### Data Sources Architecture

1. **Thai Securities Data API**: Company metadata, multilingual support (English/Thai), market classification, industry/sector data via GitHub raw files
2. **Finnomena API**: Complete financial statements, quarterly/yearly data, 38+ financial metrics with full Thai language support via REST API

**Data Flow:**
- Stock metadata (company name, industry, sector, market) → Thai Securities Data API (supports EN/TH)
- Financial data (revenue, profit, ratios, cash flow) → Finnomena API (supports EN/TH field names)
- Both sources combined in single `Stock` class for seamless bilingual user experience

**Language Support:**
- English: Returns Pydantic models with English field names
- Thai: Returns dictionaries with authentic Thai field names from Finnomena website
- Language parameter controls both metadata and financial data output format

## 🔧 Maintenance & Operations

### Regular Maintenance Tasks

- **Dependency Updates**: Monitor for security updates, especially web scraping dependencies
- **API Monitoring**: Watch for changes in Finnomena API structure
- **Data Validation**: Verify financial data accuracy against source websites
- **Performance**: Monitor cache hit rates and API response times
- **Documentation**: Update docs with `just docs` command after API changes

### Build Commands

```bash
just models  # Generate Pydantic models from JSON samples
just docs    # Generate documentation with pdoc
```

### Python Execution

**Always use `uv run` for Python execution:**
```bash
uv run python script.py           # Run Python scripts
uv run python -c "code here"      # Execute inline Python code
uv run pytest                     # Run tests
uv run jupyter notebook           # Start Jupyter
```

**Development workflow:**
```bash
uv install                        # Install dependencies
uv run python -m thaifin          # Run package as module
uv add package_name                # Add new dependency
uv remove package_name             # Remove dependency
```

## 🧪 Testing Strategy

- **Integration Tests**: `tests/public_internet_tests/` - Real API calls for validation
- **Sample Data**: `tests/sample_data/` - Cached responses for unit testing
- **Usage Examples**: `samples/view.ipynb` - Jupyter notebook demonstrations

## 📝 Commit Message Guidelines for AI Agents

1. **Use clear section headers** (e.g., 🎯 New Features, 🛠️ Technical Implementation, 📁 Files Added/Modified, ✅ Benefits, 🧪 Tested)
2. **Summarize the purpose and impact** of the change in the first line
3. **List all new and modified files** with brief descriptions
4. **Highlight user and technical benefits** clearly
5. **Note any testing or validation** performed
6. **Use bullet points** (•) for better readability
7. **Include relevant emojis** for visual organization
8. **Keep descriptions concise** but informative
9. **Use proper line breaks** for readability in tools like GitHub:
   - Separate sections with blank lines.
   - Use `\n` for line breaks in terminal commands.

### Key Files for AI Understanding

- **README.md**: User-facing documentation and usage examples
- **pyproject.toml**: Dependencies and project configuration
- **thaifin/__init__.py**: Public API exports (Stock class)
- **thaifin/stock.py**: Main API implementation with DataFrame methods and Thai language support
- **thaifin/sources/finnomena/**: Primary data source implementation with Thai language mapping
- **thaifin/sources/thai_securities_data/**: Company metadata source implementation
- **tests/public_internet_tests/**: Real-world usage patterns and integration tests
- **samples/**: Interactive examples and usage patterns including Thai language examples

### Code Organization Rules

- **Clean Imports**: All imports at the top of files
- **Debug Scripts**: All debug/investigation scripts MUST go in `/debug` folder (gitignored)
- **Tests**: All pytest tests MUST go in `/tests` folder
- **Examples**: Real-world examples in `/samples` folder
- **Documentation**: API docs and guides in `/docs` folder
- **Data Models**: Pydantic models in `/thaifin/models` and source-specific models in respective source folders

### Thai Financial Market Context

- **Stock Symbols**: Thai stock symbols like PTT, KBANK, SCB (usually 2-5 characters)
- **Company Names**: Support both Thai (จัสมิน) and English company names
- **Fiscal Periods**: Thai companies report quarterly (Q1-Q4) and annually
- **Currency**: All financial values in Thai Baht (THB)
- **Market Hours**: Thailand timezone (UTC+7)
- **Data History**: 10+ years of historical financial data available
