import thaifin


def test_stock():
    stock = thaifin.Stock("PTT")
    print(thaifin.Stock.list_symbol())
    print(thaifin.Stock.search("จัสมิน"))
    # Access dataframes to ensure they work
    _ = stock.quarter_dataframe
    _ = stock.yearly_dataframe
    print(stock)


def test_all_symbol():
    all_symbol = thaifin.Stock.list_symbol()
    print(all_symbol)

    for symbol in all_symbol:
        stock = thaifin.Stock(symbol)
        print(stock)
