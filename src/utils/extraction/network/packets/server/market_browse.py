from utils.data.market_values import ItemMetaData
from utils.extraction.network.packets.PacketBase import PacketBase
from utils.extraction.network.packets.enums import MarketBrowseType


class OfferPacketValue:
    def __init__(self, timestamp: int, counter: int, amount: int, price: int, name: str):
        self.timestamp = timestamp
        self.counter = counter
        self.amount = amount
        self.price = price
        self.name = name


class MarketBrowse(PacketBase):
    def __init__(self):
        super().__init__(False)

        self.id: int
        self.tier: int = -1
        self.browse_type: MarketBrowseType
        self.buy_offers: list[OfferPacketValue] = []
        self.sell_offers: list[OfferPacketValue] = []

    def from_packet(self, packet) -> 'MarketBrowse':
        super().from_packet(packet)
        self._read_packet()

        return self

    def _read_packet(self):
        self._read_header()
        self._read_offers()

    def _read_header(self):
        """Reads the header of a market packet.
        """
        self.browse_type = MarketBrowseType(self.read_byte())
        self.id = self.read_short()

        meta_data = ItemMetaData(id=self.id)
        meta_data.load_from_proto()
        self.tier = meta_data.tier

        if self.tier > -1:
            self.tier = self.read_byte()

    def _read_offers(self):
        """Reads the offers of a market packet. I.e. it's buy/sell offers.

        Raises:
            Exception: If the packet type is not 0xF9.
        """
        for _ in range(self.read_int()):
            self.buy_offers.append(self.read_offer())

        # sort buy offers by price, descending.
        self.buy_offers.sort(key=lambda x: x.price, reverse=True)

        for _ in range(self.read_int()):
            self.sell_offers.append(self.read_offer())

        # Sort sell offers by price, ascending.
        self.sell_offers.sort(key=lambda x: x.price)

    def read_offer(self) -> OfferPacketValue:
        """Reads and individual offer from the packet.

        Returns:
            OfferPacketValue: The offer value containing the timestamp, counter, amount, price and name of the offer.
        """
        offer_timestamp = self.read_int()
        offer_counter = self.read_short()
        offer_amount = self.read_short()
        offer_price = self.read_long()
        offer_name = self.read_prefixed_string()

        offer_value = OfferPacketValue(offer_timestamp, offer_counter, offer_amount, offer_price, offer_name)

        return offer_value
