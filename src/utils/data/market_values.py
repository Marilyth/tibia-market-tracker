from utils.wiki import Wiki
from typing import List, Optional
from pydantic import BaseModel


class NPCSaleData(BaseModel):
    """A data class containing information about an NPC item sale.
    """
    name: str
    location: str
    price: int
    currency_object_type_id: int
    currency_quest_flag_display_name: str

    def is_gold(self) -> bool:
        """Returns True if the currency is gold, False otherwise.

        Returns:
            bool: True if the currency is gold, False otherwise.
        """
        return self.currency_object_type_id == 0 and self.currency_quest_flag_display_name == ""


class ItemMetaData(BaseModel):
    """A data class containing meta information about an item.
    """
    id: int
    category: Optional[str] = None
    tier: int = -1
    name: Optional[str] = None
    npc_sell: List[NPCSaleData] = None
    npc_buy: List[NPCSaleData] = None
    wiki_name: Optional[str] = None

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
            self.npc_buy = []
            self.npc_sell = []
            proto_item = proto_items[self.id]
            self.category = str(proto_item.flags.market).split("ITEM_CATEGORY_")[-1].split("\n")[0].replace("_", " ").title()
            is_upgradeable = len(str(proto_item.flags.upgradeclassification)) > 0
            if is_upgradeable:
                self.tier = int(str(proto_item.flags.upgradeclassification).split("upgrade_classification: ")[-1])
            self.name = proto_item.name

            for sale_data in proto_item.flags.npcsaledata:
                if sale_data.buy_price > 0:
                    self.npc_buy.append(NPCSaleData(name=sale_data.name, price=sale_data.buy_price, location=sale_data.location, currency_object_type_id=sale_data.currency_object_type_id, currency_quest_flag_display_name=sale_data.currency_quest_flag_display_name))
                if sale_data.sale_price > 0:
                    self.npc_sell.append(NPCSaleData(name=sale_data.name, price=sale_data.sale_price, location=sale_data.location, currency_object_type_id=sale_data.currency_object_type_id, currency_quest_flag_display_name=sale_data.currency_quest_flag_display_name))

            return True
        else:
            return False


class MarketValues(BaseModel):
    """A data class containing information about the market values of an item.
    """
    id: int
    time: float
    buy_offer: int = -1
    sell_offer: int = -1
    month_average_sell: int = -1
    month_average_buy: int = -1
    month_sold: int = -1
    month_bought: int = -1
    active_traders: int = -1
    month_highest_sell: int = -1
    month_lowest_buy: int = -1
    month_lowest_sell: int = -1
    month_highest_buy: int = -1
    buy_offers: int = -1
    sell_offers: int = -1
    day_average_sell: int = -1
    day_average_buy: int = -1
    day_sold: int = -1
    day_bought: int = -1
    day_highest_sell: int = -1
    day_lowest_sell: int = -1
    day_highest_buy: int = -1
    day_lowest_buy: int = -1
    total_immediate_profit: int = -1
    total_immediate_profit_info: str = ""


    def __post_init__(self):
        self.buy_offer: int = max(self.buy_offer, self.month_lowest_buy) if self.month_bought > 0 and self.month_lowest_buy > -1 else self.buy_offer
        self.sell_offer: int = min(self.sell_offer, self.month_highest_sell) if self.month_sold > 0 and self.month_highest_sell > -1 else self.sell_offer

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