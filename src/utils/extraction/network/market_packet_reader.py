import struct
from typing import List


class MarketPacketReader:
    def __init__(self, packet: bytes):
        self.packet = packet
        self.offset = 0
        self.result = None

    def _read_bytes(self, length: int) -> bytes:
        value = self.packet[self.offset:self.offset + length]
        self.offset += length

        return value

    def _read_header(self, has_tier: bool = False):
        """Reads the header of a market packet.

        Args:
            has_tier (bool, optional): Whether the packet has an item tier. Defaults to False.

        Raises:
            Exception: If the packet type is not 0xF8.
        """
        packet_length = struct.unpack("H", self._read_bytes(2))[0]
        packet_type = struct.unpack("B", self._read_bytes(1))[0]

        if packet_type != 0xF8:
            raise Exception(f"Invalid packet type: {packet_type}")

        self.result.id = struct.unpack("H", self._read_bytes(2))[0]

        if has_tier:
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
        buy_history_length = struct.unpack("B", self._read_bytes(1))[0]

        # History goes from recent to old.
        for i in range(buy_history_length):
            amount_traded = struct.unpack("I", self._read_bytes(4))[0]
            total_gold = struct.unpack("Q", self._read_bytes(8))[0]
            max_price = struct.unpack("Q", self._read_bytes(8))[0]
            min_price = struct.unpack("Q", self._read_bytes(8))[0]

            history_value = HistoryPacketValue(amount_traded, total_gold, max_price, min_price)
            self.result.buy_history.append(history_value)

        sell_history_length = struct.unpack("B", self._read_bytes(1))[0]

        for i in range(sell_history_length):
            amount_traded = struct.unpack("I", self._read_bytes(4))[0]
            total_gold = struct.unpack("Q", self._read_bytes(8))[0]
            max_price = struct.unpack("Q", self._read_bytes(8))[0]
            min_price = struct.unpack("Q", self._read_bytes(8))[0]

            history_value = HistoryPacketValue(amount_traded, total_gold, max_price, min_price)
            self.result.sell_history.append(history_value)

    def _read_offers(self, has_tier: bool = False):
        """Reads the offers of a market packet. I.e. it's buy/sell offers.

        Args:
            has_tier (bool, optional): Whether the packet has an item tier. Defaults to False.

        Raises:
            Exception: If the packet type is not 0xF9.
        """
        packet_type = struct.unpack("B", self._read_bytes(1))[0]

        if packet_type != 0xF9:
            raise Exception(f"Invalid packet type: {packet_type}")

        unknown = struct.unpack("B", self._read_bytes(1))[0]
        item_id = struct.unpack("H", self._read_bytes(2))[0]

        if item_id != self.result.id:
            raise Exception(f"Item id mismatch: {item_id} != {self.result.id}")

        if has_tier:
            self.result.tier = struct.unpack("B", self._read_bytes(1))[0]

        buy_offer_amount = struct.unpack("I", self._read_bytes(4))[0]

        for i in range(buy_offer_amount):
            offer_timestamp = struct.unpack("I", self._read_bytes(4))[0]
            offer_counter = struct.unpack("H", self._read_bytes(2))[0]
            offer_amount = struct.unpack("H", self._read_bytes(2))[0]
            offer_price = struct.unpack("Q", self._read_bytes(8))[0]
            offer_name_length = struct.unpack("H", self._read_bytes(2))[0]
            offer_name = struct.unpack(f"{offer_name_length}s", self._read_bytes(offer_name_length))[0].decode("utf-8")

            offer_value = OfferPacketValue(offer_timestamp, offer_counter, offer_amount, offer_price, offer_name)
            self.result.buy_offers.append(offer_value)

        # sort buy offers by price, descending.
        self.result.buy_offers.sort(key=lambda x: x.price, reverse=True)

        sell_offer_amount = struct.unpack("I", self._read_bytes(4))[0]

        for i in range(sell_offer_amount):
            offer_timestamp = struct.unpack("I", self._read_bytes(4))[0]
            offer_counter = struct.unpack("H", self._read_bytes(2))[0]
            offer_amount = struct.unpack("H", self._read_bytes(2))[0]
            offer_price = struct.unpack("Q", self._read_bytes(8))[0]
            offer_name_length = struct.unpack("H", self._read_bytes(2))[0]
            offer_name = struct.unpack(f"{offer_name_length}s", self._read_bytes(offer_name_length))[0].decode("utf-8")

            offer_value = OfferPacketValue(offer_timestamp, offer_counter, offer_amount, offer_price, offer_name)
            self.result.sell_offers.append(offer_value)
        
        # Sort sell offers by price, ascending.
        self.result.sell_offers.sort(key=lambda x: x.price)

    def read_packet(self, has_tier: bool = False):
        """Reads a market packet, and saves the result to self.result.

        Args:
            has_tier (bool, optional): Whether the packet has an item tier. Defaults to False.
        """
        self.result = MarketPacketValues()
        self.offset = 0

        self._read_header(has_tier)
        self._read_details()
        self._read_statistics()
        self._read_offers(has_tier)
    

class MarketPacketValues:
    def __init__(self):
        self.id: int = None
        self.tier: int = None
        self.details: List[str] = None
        self.buy_history: List[HistoryPacketValue] = []
        self.sell_history: List[HistoryPacketValue] = []
        self.buy_offers: List[OfferPacketValue] = []
        self.sell_offers: List[OfferPacketValue] = []


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