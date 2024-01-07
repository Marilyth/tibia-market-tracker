import struct
from typing import List
from utils.data.market_values import ItemMetaData, MarketValues
from time import time


class MarketPacketReader:
    def __init__(self, packet: bytes):
        self.packet = packet
        self.offset = 0
        self.result = None

    def _read_bytes(self, length: int) -> bytes:
        value = self.packet[self.offset:self.offset + length]
        self.offset += length

        return value

    def _read_header(self):
        """Reads the header of a market packet.

        Args:
            has_tier (bool, optional): Whether the packet has an item tier. Defaults to False.

        Raises:
            Exception: If the packet type is not 0xF8.
        """
        packet_length = struct.unpack("H", self._read_bytes(2))[0]
        packet_type = struct.unpack("B", self._read_bytes(1))[0]

        if packet_type != 0xF8:
            raise Exception(f"Invalid header packet type: {packet_type}")

        self.result.id = struct.unpack("H", self._read_bytes(2))[0]

        meta_data = ItemMetaData(self.result.id)
        meta_data.load_from_proto()
        self.result.tier = meta_data.tier

        if self.result.tier > -1:
            self.result.tier = struct.unpack("B", self._read_bytes(1))[0]

    def _read_details(self):
        """Reads the details of a market packet. I.e. it's description, etc.
        """
        self.result.details = []
        
        # Go through each category. The amount can change every update.
        for i in range(23):
            category_length = struct.unpack("H", self._read_bytes(2))[0]
            category_string = struct.unpack(f"{category_length}s", self._read_bytes(category_length))[0].decode("utf-8")
            self.result.details.append(category_string)

    def _read_statistics(self):
        """Reads the statistics of a market packet. I.e. it's daily sell/buy history.
        """
        def read_history(length: int) -> List[HistoryPacketValue]:
            history = []

            for i in range(length):
                amount_traded = struct.unpack("I", self._read_bytes(4))[0]
                total_gold = struct.unpack("Q", self._read_bytes(8))[0]
                max_price = struct.unpack("Q", self._read_bytes(8))[0]

                # Min_price is set to FFFFFFFFFFFFFFFF in packet if there were no trades.
                min_price = struct.unpack("Q", self._read_bytes(8))[0]
                if amount_traded == 0:
                    min_price = 0

                history_value = HistoryPacketValue(amount_traded, total_gold, max_price, min_price)
                history.append(history_value)

            return history

        # History goes from recent to old.
        buy_history_length = struct.unpack("B", self._read_bytes(1))[0]
        self.result.buy_history.extend(read_history(buy_history_length))

        sell_history_length = struct.unpack("B", self._read_bytes(1))[0]
        self.result.sell_history.extend(read_history(sell_history_length))

    def _read_offers(self):
        """Reads the offers of a market packet. I.e. it's buy/sell offers.

        Args:
            has_tier (bool, optional): Whether the packet has an item tier. Defaults to False.

        Raises:
            Exception: If the packet type is not 0xF9.
        """
        while True:
            packet_type = struct.unpack("B", self._read_bytes(1))[0]

            if packet_type == 0xF9:
                break

        unknown = struct.unpack("B", self._read_bytes(1))[0]
        item_id = struct.unpack("H", self._read_bytes(2))[0]

        if item_id != self.result.id:
            raise Exception(f"Item id mismatch: {item_id} != {self.result.id}")

        if self.result.tier > -1:
            self.result.tier = struct.unpack("B", self._read_bytes(1))[0]

        def read_offers(amount: int) -> List[OfferPacketValue]:
            offers = []

            for i in range(amount):
                offer_timestamp = struct.unpack("I", self._read_bytes(4))[0]
                offer_counter = struct.unpack("H", self._read_bytes(2))[0]
                offer_amount = struct.unpack("H", self._read_bytes(2))[0]
                offer_price = struct.unpack("Q", self._read_bytes(8))[0]
                offer_name_length = struct.unpack("H", self._read_bytes(2))[0]
                offer_name = struct.unpack(f"{offer_name_length}s", self._read_bytes(offer_name_length))[0].decode("utf-8")

                offer_value = OfferPacketValue(offer_timestamp, offer_counter, offer_amount, offer_price, offer_name)
                offers.append(offer_value)

            return offers

        buy_offer_amount = struct.unpack("I", self._read_bytes(4))[0]
        self.result.buy_offers.extend(read_offers(buy_offer_amount))

        # sort buy offers by price, descending.
        self.result.buy_offers.sort(key=lambda x: x.price, reverse=True)

        sell_offer_amount = struct.unpack("I", self._read_bytes(4))[0]
        self.result.sell_offers.extend(read_offers(sell_offer_amount))
        
        # Sort sell offers by price, ascending.
        self.result.sell_offers.sort(key=lambda x: x.price)

    def read_packet(self):
        """Reads a market packet, and saves the result to self.result.

        Args:
            has_tier (bool, optional): Whether the packet has an item tier. Defaults to False.
        """
        self.result = MarketPacketValues()
        self.offset = 0

        self._read_header()
        self._read_details()
        self._read_statistics()
        self._read_offers()
    

class MarketPacketValues:
    def __init__(self):
        self.id: int = None
        self.tier: int = -1
        self.details: List[str] = None
        self.buy_history: List[HistoryPacketValue] = []
        self.sell_history: List[HistoryPacketValue] = []
        self.buy_offers: List[OfferPacketValue] = []
        self.sell_offers: List[OfferPacketValue] = []

    def convert_to_marketvalues(self) -> MarketValues:
        """Converts the MarketPacketValues object to a MarketValues object to reduce required storage.

        Returns:
            MarketValues: The MarketValues object.
        """
        buy_offer = self.buy_offers[0].price if len(self.buy_offers) > 0 else -1
        sell_offer = self.sell_offers[0].price if len(self.sell_offers) > 0 else -1

        month_buy_offer = int(sum([x.average_price for x in self.buy_history]) / len(self.buy_history) if len(self.buy_history) > 0 else -1)
        month_sell_offer = int(sum([x.average_price for x in self.sell_history]) / len(self.sell_history) if len(self.sell_history) > 0 else -1)
        month_highest_buy_offer = max([x.max_price for x in self.buy_history]) if len(self.buy_history) > 0 else -1
        traded_min_sell_offers = [x.min_price for x in self.sell_history if x.min_price > 0]
        month_lowest_sell_offer = min(traded_min_sell_offers if traded_min_sell_offers else [0]) if len(self.sell_history) > 0 else -1
        month_highest_sell_offer = max([x.max_price for x in self.sell_history]) if len(self.sell_history) > 0 else -1
        traded_min_buy_offers = [x.min_price for x in self.buy_history if x.min_price > 0]
        month_lowest_buy_offer = min(traded_min_buy_offers if traded_min_buy_offers else [0]) if len(self.buy_history) > 0 else -1
        month_bought = sum([x.traded for x in self.buy_history]) if len(self.buy_history) > 0 else -1
        month_sold = sum([x.traded for x in self.sell_history]) if len(self.sell_history) > 0 else -1

        day_buy_offer = int(self.buy_history[0].average_price if len(self.buy_history) > 0 else -1)
        day_sell_offer = int(self.sell_history[0].average_price if len(self.sell_history) > 0 else -1)
        day_highest_buy_offer = self.buy_history[0].max_price if len(self.buy_history) > 0 else -1
        day_lowest_sell_offer = self.sell_history[0].min_price if len(self.sell_history) > 0 else -1
        day_highest_sell_offer = self.sell_history[0].max_price if len(self.sell_history) > 0 else -1
        day_lowest_buy_offer = self.buy_history[0].min_price if len(self.buy_history) > 0 else -1
        day_bought = self.buy_history[0].traded if len(self.buy_history) > 0 else -1
        day_sold = self.sell_history[0].traded if len(self.sell_history) > 0 else -1

        buy_offers = len(self.buy_offers)
        sell_offers = len(self.sell_offers)

        # Active offers are offers within the past 24 hours.
        active_sell_offers = len([x for x in self.sell_offers if time() - x.timestamp < 86400])
        active_buy_offers = len([x for x in self.buy_offers if time() - x.timestamp < 86400])

        return MarketValues(time(), sell_offer, buy_offer, month_sell_offer, month_buy_offer, month_sold, month_bought,
                            month_highest_sell_offer, month_lowest_buy_offer, min(active_sell_offers, active_buy_offers),
                            sell_offers, buy_offers, month_lowest_sell_offer, month_highest_buy_offer, self.id,
                            day_sell_offer, day_buy_offer, day_sold, day_bought, day_highest_sell_offer, day_lowest_sell_offer,
                            day_highest_buy_offer, day_lowest_buy_offer)


class HistoryPacketValue:
    def __init__(self, traded: int, total_gold: int, max_price: int, min_price: int):
        self.traded = traded
        self.total_gold = total_gold
        self.max_price = max_price
        self.min_price = min_price
        self.average_price = total_gold / traded if traded > 0 else 0


class OfferPacketValue:
    def __init__(self, timestamp: int, counter: int, amount: int, price: int, name: str):
        self.timestamp = timestamp
        self.counter = counter
        self.amount = amount
        self.price = price
        self.name = name