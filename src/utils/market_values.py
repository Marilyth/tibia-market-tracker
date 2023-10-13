class MarketValues:
    def __init__(self, name: str, time: float, sell_offer: int, buy_offer: int, month_sell_offer: int, month_buy_offer: int, sold: int, bought: int, highest_sell: int, lowest_buy: int, approx_offers: int):
        self.buy_offer: int = max(buy_offer, lowest_buy) if bought > 0 and lowest_buy > -1 else buy_offer
        self.sell_offer: int = min(sell_offer, highest_sell) if sold > 0 and highest_sell > -1 else sell_offer
        self.month_sell_offer: int = month_sell_offer
        self.month_buy_offer: int = month_buy_offer
        self.sold: int = sold
        self.bought: int = bought
        self.time: float = time
        self.active_traders: int = approx_offers
        self.name = name
    
    @staticmethod
    def from_string(string: str):
        """Creates a MarketValues object from a string.
        The string must be in the format of the __str__ method of this class.

        Args:
            string (str): The string to convert to a MarketValues object.

        Returns:
            MarketValues: The MarketValues object created from the string.
        """
        line_values = string.split(",")
        sell_offer, buy_offer, month_sell_offer, month_buy_offer, sold, bought, active_traders = line_values[-7:]
        name = ",".join(line_values[:-7])
        
        return MarketValues(name, -1, float(sell_offer), float(buy_offer), float(month_sell_offer), float(month_buy_offer), float(sold), float(bought), -1, -1, float(active_traders))

    @staticmethod
    def from_history_string(string: str):
        line_values = string.split(",")
        sell_offer, buy_offer, sold, bought, active_traders, time = line_values
        
        return MarketValues(None, float(time), float(sell_offer), float(buy_offer), -1, -1, float(sold), float(bought), -1, -1, float(active_traders))

    def __str__(self) -> str:
        return f"{self.name.lower()},{self.sell_offer},{self.buy_offer},{self.month_sell_offer},{self.month_buy_offer},{self.sold},{self.bought},{self.active_traders}"

    def history_string(self) -> str:
        """Returns the relevant historic values of the object as a string, separated by commas.
        This includes the sell offer, buy offer, sold, bought and approx offers values, followed by the time of the data.

        Returns:
            str: A string containing all the values of the object, separated by commas.
        """
        return f"{self.sell_offer},{self.buy_offer},{self.sold},{self.bought},{self.active_traders},{self.time}"
