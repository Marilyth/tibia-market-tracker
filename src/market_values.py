

class MarketValues:
    def __init__(self, name: str, time: float, sell_offer: int, buy_offer: int, month_sell_offer: int, month_buy_offer: int, sold: int, bought: int, highest_sell: int, lowest_buy: int, approx_offers: int):
        self.buy_offer: int = max(buy_offer, lowest_buy)
        self.sell_offer: int = min(sell_offer, highest_sell) if sold > 0 else sell_offer
        self.month_sell_offer: int = month_sell_offer
        self.month_buy_offer: int = month_buy_offer
        self.sold: int = sold
        self.bought: int = bought
        self.time: float = time
        self.active_traders: int = approx_offers
        self.name = name

    def __str__(self) -> str:
        return f"{self.name.lower()},{self.sell_offer},{self.buy_offer},{self.month_sell_offer},{self.month_buy_offer},{self.sold},{self.bought},{self.active_traders}"

    def history_string(self) -> str:
        """Returns the relevant historic values of the object as a string, separated by commas.
        This includes the sell offer, buy offer, sold, bought and approx offers values, followed by the time of the data.

        Returns:
            str: A string containing all the values of the object, separated by commas.
        """
        return f"{self.sell_offer},{self.buy_offer},{self.sold},{self.bought},{self.active_traders},{self.time}"
