import thaifin


def test_stock():
    stock = thaifin.Stock("PTT")
    print(thaifin.Stocks.list())
    print(thaifin.Stocks.search("จัสมิน"))
    # Access dataframes to ensure they work
    _ = stock.quarter_dataframe
    _ = stock.yearly_dataframe
    print(stock)


def test_all_symbol():
    all_symbols = thaifin.Stocks.list()
    print(all_symbols[:10])  # Print only first 10 to avoid too much output

    # Test only first 3 symbols to avoid too many API calls
    for symbol in all_symbols[:3]:
        stock = thaifin.Stock(symbol)
        print(stock)
