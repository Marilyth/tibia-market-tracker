from utils.wiki import Wiki
from typing import List


class NPCSaleData:
    def __init__(self, name: str, sell_price: int, location: str, currency_object_type_id: int, currency_quest_flag_display_name: str):
        self.name = name
        self.location = location
        self.price = sell_price
        self.currency_object_type_id = currency_object_type_id
        self.currency_quest_flag_display_name = currency_quest_flag_display_name

class ItemMetaData:
    def __init__(self, id: int):
        self.id = id
        self.category: str = None
        self.is_upgradeable: bool = False
        self.name: str = None
        self.npc_sell: List[NPCSaleData] = []
        self.npc_buy: List[NPCSaleData] = []
        self.wiki_name: str = None

    def load_wiki_name(self):
        """Load the pretty name of the item from the wiki.
        """
        if self.id in Wiki.get_wiki_names():
            self.wiki_name = Wiki.get_wiki_names()[self.id]

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
            self.name = proto_item.name

            for sale_data in proto_item.flags.npcsaledata:
                if sale_data.buy_price > 0:
                    self.npc_buy.append(NPCSaleData(sale_data.name, sale_data.buy_price, sale_data.location, sale_data.currency_object_type_id, sale_data.currency_quest_flag_display_name))
                if sale_data.sale_price > 0:
                    self.npc_sell.append(NPCSaleData(sale_data.name, sale_data.sale_price, sale_data.location, sale_data.currency_object_type_id, sale_data.currency_quest_flag_display_name))

            return True
        else:
            return False

class MarketValues:
    def __init__(self, time: float, sell_offer: int, buy_offer: int, month_sell_offer: int, month_buy_offer: int, sold: int, bought: int, highest_sell: int, lowest_buy: int, approx_offers: int, sell_offers: int, buy_offers: int, lowest_sell: int, highest_buy: int, id: int):
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

    def get_metadata(self, load_wiki_name: bool = True) -> ItemMetaData:
        """Returns the metadata of the item.

        Returns:
            ItemMetaData: The metadata of the item.
        """
        metadata = ItemMetaData(self.id)
        metadata.load_from_proto()

        if load_wiki_name:
            metadata.load_wiki_name()

        return metadata