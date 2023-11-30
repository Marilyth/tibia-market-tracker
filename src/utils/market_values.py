from utils.wiki import Wiki
from typing import List


class NPCSaleData:
    def __init__(self, name: str, sell_price: int, location: str):
        self.name = name
        self.location = location
        self.price = sell_price


class MarketValues:
    def __init__(self, name: str, time: float, sell_offer: int, buy_offer: int, month_sell_offer: int, month_buy_offer: int, sold: int, bought: int, highest_sell: int, lowest_buy: int, approx_offers: int, sell_offers: int, buy_offers: int, lowest_sell: int, highest_buy: int, id: int):
        self.buy_offer: int = max(buy_offer, lowest_buy) if bought > 0 and lowest_buy > -1 else buy_offer
        self.sell_offer: int = min(sell_offer, highest_sell) if sold > 0 and highest_sell > -1 else sell_offer
        self.month_sell_offer: int = month_sell_offer
        self.month_buy_offer: int = month_buy_offer
        self.sold: int = sold
        self.bought: int = bought
        self.time: float = time
        self.active_traders: int = approx_offers
        self.highest_sell: int = highest_sell
        self.lowest_buy: int = lowest_buy
        self.lowest_sell: int = lowest_sell
        self.highest_buy: int = highest_buy
        self.buy_offers: int = buy_offers
        self.sell_offers: int = sell_offers
        self.id: int = id
        self.name: str = name
        self.tier: int = 0
        self.category: str = None
        self.is_upgradeable: bool = False
        self.internal_name: str = None
        self.npc_sell: List[NPCSaleData] = []
        self.npc_buy: List[NPCSaleData] = []
    
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
        
        return MarketValues(name, -1, float(sell_offer), float(buy_offer), float(month_sell_offer), float(month_buy_offer), float(sold), float(bought), -1, -1, float(active_traders), -1, -1, -1, -1, -1)

    @staticmethod
    def from_history_string(string: str):
        line_values = string.split(",")
        sell_offer, buy_offer, sold, bought, active_traders, time = line_values
        
        return MarketValues(None, float(time), float(sell_offer), float(buy_offer), -1, -1, float(sold), float(bought), -1, -1, float(active_traders), -1, -1, -1, -1, -1)

    def __str__(self) -> str:
        return f"{self.name.lower()},{self.sell_offer},{self.buy_offer},{self.month_sell_offer},{self.month_buy_offer},{self.sold},{self.bought},{self.active_traders}"

    def history_string(self) -> str:
        """Returns the relevant historic values of the object as a string, separated by commas.
        This includes the sell offer, buy offer, sold, bought and approx offers values, followed by the time of the data.

        Returns:
            str: A string containing all the values of the object, separated by commas.
        """
        return f"{self.sell_offer},{self.buy_offer},{self.sold},{self.bought},{self.active_traders},{self.time}"

    def load_pretty_name(self):
        """Load the pretty name of the item from the wiki.
        """
        if self.id in Wiki.get_pretty_names():
            self.name = Wiki.get_pretty_names()[self.id]

    def load_from_proto(self) -> bool:
        """Load the category, is_upgradeable, internal_name and NPC values from the proto file.

        Returns:
            bool: True if the item was found in the proto file, False otherwise.
        """
        proto_items = Wiki.get_marketable_proto_items()
        
        if self.id in proto_items:
            proto_item = proto_items[self.id]
            self.category = str(proto_item.flags.market).split("ITEM_CATEGORY_")[-1].split("\n")[0].replace("_", " ").title()
            self.is_upgradeable = len(str(proto_item.flags.upgradeclassification)) > 0
            self.internal_name = proto_item.name

            for sale_data in proto_item.flags.npcsaledata:
                if sale_data.buy_price > 0:
                    self.npc_buy.append(NPCSaleData(sale_data.name, sale_data.buy_price, sale_data.location))
                if sale_data.sale_price > 0:
                    self.npc_sell.append(NPCSaleData(sale_data.name, sale_data.sale_price, sale_data.location))

            return True
        else:
            return False