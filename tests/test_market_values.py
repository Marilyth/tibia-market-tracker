from data.market_values import MarketValues


def test_MarketValuesToString_GivenValues_ReturnsExpected():
    market_values = MarketValues("Item Name", 1.0, 100, 90, 110, 80, 1000, 500, 120, 70, 200)
    assert str(market_values) == "item name,100,90,110,80,1000,500,200"

def test_MarketValues_BuyLowerThanLowest_ReturnsLowest():
    market_values = MarketValues("Item Name", 1.0, 0, 10, 0, 0, 0, 1, 0, 20, 20)
    assert market_values.buy_offer == 20

def test_MarketValues_SellOfferHigherowerThanHighest_ReturnsHighest():
    market_values = MarketValues("Item Name", 1.0, 20, 0, 0, 0, 1, 0, 10, 0, 20)
    assert market_values.sell_offer == 10

def test_MarketValues_SellOfferHigherowerThanHighestNoSold_ReturnsOffer():
    market_values = MarketValues("Item Name", 1.0, 20, 0, 0, 0, 0, 0, 10, 0, 20)
    assert market_values.sell_offer == 20

def test_HistoryString_GivenValues_ReturnsExpected():
    market_values = MarketValues("Item Name", 1.0, 100, 90, 110, 80, 1000, 500, 120, 70, 200)
    assert market_values.history_string() == "100,90,1000,500,200,1.0"
