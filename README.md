# thaifin: ข้อมูลพื้นฐานหุ้น ง่ายแค่สามบรรทัด

## Changelog for v1.1 📜

- **API Refactoring** 🏗️: Introduced new `Stocks` class for collection operations (search, list, filter)
- **Enhanced Search** 🔍: Smart search with Thai/English auto-detection and improved matching algorithm
- **Better Organization** 📁: `Stock` class now focuses on individual stock operations, `Stocks` class handles collection operations
- **New Features** ✨: Added filtering by sector and market, enhanced listing with company details

## Changelog for v1.0 📜

- **Column Naming Convention** 📛: All column names in the API have been updated to use snake_case
- **Python Compatibility** 🐍: The library is now compatible with Python versions 3.11 and above, ensuring better performance and newer features from the latest Python release. Google Colab user might have dificulty on 3.10.

> The same author as [PythaiNAV](https://github.com/CircleOnCircles/pythainav)

 [**Documentation**](https://circleoncircles.github.io/thaifin/thaifin.html)

A Python library for access thai stock fundamental data up to 10+ years. 

- faster and lesser load to server with [cachetools](https://pypi.org/project/cachetools/)
- more robust with auto retry with expo wait via [tenacity](https://github.com/jd/tenacity)
- better than nothing docs with [pdoc](https://pdoc.dev/)

<a href="https://imgflip.com/i/4dxnzi"><img src="https://i.imgflip.com/4dxnzi.jpg" title="made at imgflip.com"/></a><div></div>

ไพทอนไลบารี่สำหรับเข้าถึงข้อมูลปัจจัยพื้นฐานของหุ้นในตลาดไทยมากถึง 10+ ปี

## Get Started

```bash
# Pick one ✨
$ pip install thaifin
$ conda install thaifin
```

```python
# Import both classes for different use cases
from thaifin import Stock, Stocks

# Collection operations with Stocks class
# Get all stock symbols
all_symbols = Stocks.list() 
# ['T', 'A', 'U', 'J', 'W', 'B', 'D', 'S', 'M', 'K', 'EE', ...

# Smart search with auto language detection
top5match = Stocks.search('จัสมิน')  # Thai search
# [<Stock JTS - updated just now>, <Stock JAS - updated just now>, <Stock JASIF - updated just now>, ...

cp_stocks = Stocks.search('cp')  # English search
# [<Stock CPALL - updated just now>, <Stock CPANEL - updated just now>, <Stock CPAXT - updated just now>, ...

# Get detailed stock list with company info
stock_df = Stocks.list_with_names()
#   symbol                                     name                 industry                  sector market
# 0   24CS  Twenty-Four Con & Supply Public Company Limited  Property & Construction                       -    mai
# 1     2S                  2S METAL PUBLIC COMPANY LIMITED              Industrials  Steel and Metal Products    SET

# Filter stocks by sector or market
banking_stocks = Stocks.filter_by_sector('Banking')
mai_stocks = Stocks.filter_by_market('mai')

# Individual stock operations with Stock class
stock = Stock('PTT')
# <Stock PTT - updated just now>

# Access company information
print(f"Company: {stock.company_name}")
print(f"Sector: {stock.sector}")
print(f"Industry: {stock.industry}")

# Get financial data as pandas DataFrames
stock.quarter_dataframe

#                 Cash            DA  ...  FinancingActivities         Asset
# Time                                ...                                   
# 2009Q1  9.383006e+07  1.070218e+07  ...         3.101551e+07  9.453044e+08
# 2009Q2  9.643438e+07  8.893013e+06  ...         3.195314e+07  1.042480e+09
# 2009Q3  1.050549e+08  1.127702e+07  ...         1.100019e+07  1.099084e+09
# 2009Q4  1.040559e+08  1.227756e+07  ...        -1.356621e+07  1.103590e+09
# ...
# 2019Q4  2.925425e+08  3.581462e+07  ...        -2.179443e+07  2.484439e+09
# 2020Q1  2.543450e+08  3.586543e+07  ...        -2.705637e+07  2.499666e+09
# 2020Q2  2.578579e+08  3.460213e+07  ...         2.117104e+07  2.449277e+09
# [46 rows x 35 columns]

stock.yearly_dataframe

                # Cash            DA  ...  FinancingActivities         Asset
# Fiscal                              ...                                   
# 2009    1.040559e+08  4.314976e+07  ...         6.040263e+07  1.103590e+09
# 2010    1.356320e+08  5.122258e+07  ...         3.761321e+06  1.249148e+09
# 2011    1.161321e+08  5.531816e+07  ...        -4.542309e+07  1.402412e+09
# 2012    1.369176e+08  6.523743e+07  ...         2.771070e+07  1.631320e+09
# 2013    1.576835e+08  7.631456e+07  ...        -5.579036e+07  1.801722e+09
# 2014    2.037854e+08  1.170070e+08  ...        -4.731543e+07  1.779179e+09
# 2015    2.399779e+08  1.488855e+08  ...        -1.638133e+08  2.173996e+09
# 2016    2.155664e+08  1.297570e+08  ...        -1.162034e+08  2.232331e+09
# 2017    1.661890e+08  1.171472e+08  ...        -1.624979e+08  2.232314e+09
# 2018    2.921843e+08  1.235563e+08  ...        -1.114676e+08  2.355484e+09
# 2019    2.925425e+08  1.332042e+08  ...        -7.022567e+07  2.484439e+09
# [11 rows x 35 columns]

```

### Columns Data

```python
class QuarterFinancialSheetDatum(BaseModel):
    security_id: str
    fiscal: int
    quarter: int
    cash: Optional[str]
    da: Optional[str]
    debt_to_equity: Optional[str]
    equity: Optional[str]
    earning_per_share: Optional[str]
    earning_per_share_yoy: Optional[str]
    earning_per_share_qoq: Optional[str]
    gpm: Optional[str]
    gross_profit: Optional[str]
    net_profit: Optional[str]
    net_profit_yoy: Optional[str]
    net_profit_qoq: Optional[str]
    npm: Optional[str]
    revenue: Optional[str]
    revenue_yoy: Optional[str]
    revenue_qoq: Optional[str]
    roa: Optional[str]
    roe: Optional[str]
    sga: Optional[str]
    sga_per_revenue: Optional[str]
    total_debt: Optional[str]
    dividend_yield: Optional[str]
    book_value_per_share: Optional[str]
    close: Optional[str]
    mkt_cap: Optional[str]
    price_earning_ratio: Optional[str]
    price_book_value: Optional[str]
    ev_per_ebit_da: Optional[str]
    ebit_dattm: Optional[str]
    paid_up_capital: Optional[str]
    cash_cycle: Optional[str]
    operating_activities: Optional[str]
    investing_activities: Optional[str]
    financing_activities: Optional[str]
    asset: Optional[str]
    end_of_year_date: Optional[str]
```

## Disclaimer

เราไม่รับประกันความเสียหายใดๆทั้งสิ้นที่เกิดจาก แหล่งข้อมูล, library, source code,sample code, documentation, library dependencies และอื่นๆ

## FAQ
Q: อยากขอบคุณอ่ะ อยากตอบแทนอ่ะ 😋 ทำไงดี?

A: ถ้าเป็น developer สามารถช่วยส่ง PR หรือ pull request ได้ครับ ไม่ว่าจะเป็นงานเล็กน้อยเช่นแก้การพิมพ์ผิด หรือช่วยทำคู่มือ ยินดีมากๆครับ สามารถสนับสนุนผม
โดยการบริจาคครั้งเดียวผ่าน [Ko-fi](https://ko-fi.com/circleoncircles) หรือ [patreon](https://www.patreon.com/CircleOnCircles) ก็ได้เช่นกันครับ นอกจากนี้ยังสามารถเขียนให้กำลังใจผมได้ทาง [![Say Thanks!](https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg)](https://saythanks.io/to/nutchanon@codustry.com)

Q: แจ้งปัญหาไงอ่ะ ?

A: ถ้าเป็น error วิธีการใช้งานเขียน stackoverflow ได้ครับ ถ้าเป็น bug หรืออยากแนะนำขอ feature เขียน issue มาได้ครับ

Q: ข้อมูลมาจากไหน เชื่อถือได้แค่ไหน ?

A: ข้อมูลมาจากสาธารณะหลายแหล่งครับ ตอนที่เขียนมีเว็ป Finnomena, Set, Settrade เชื่อถือได้ไม่ได้คงต้องตัดสินเองนะครับ

Q: สร้างมาทำไม ?

A: สมัยเป็นนักศึกษา ผมก็อยากได้สิ่งนี้มาก่อนครับ เป็นเครื่องมือช่วยประกอบการลงทุน และใช้ความรู้ทาง data science กับข้อมูลได้ ตอนนั้นไม่มีใครทำครับ 
ข้อมูลผูกขาดเฉพาะกับบริษัทลงทุนเท่านั้น ตอนนี้ก็ยังเหมือนเดิม เพิ่มเติมคือผมมีความสามารถที่จะสร้างมัน ก็อยากให้คนรุ่นต่อไปได้มี library ดีๆ เป็นสมบัติ
ของทุกคน(License ISC) ผมจึงใช้เวลาส่วนตัวมาพัฒนาครับ ทุกคนให้ความรักมันด้วยนะครับ code ก็ต้องการความรักนะ อิอิ

 
 
