from utils.data.market_values import ItemMetaData
from utils.extraction.network.packets.PacketBase import PacketBase
from utils.extraction.network.packets.enums import MarketBrowseType
import struct


class MarketBrowse(PacketBase):
    def __init__(self):
        super().__init__(True)

        self.id: int
        self.tier: int
        self.browse_type: MarketBrowseType

    def from_packet(self, packet: bytes) -> 'MarketBrowse':
        super().from_packet(packet)
        self._read_packet()

        return self

    def from_data(self, item_id: int, tier: int, browse_type: MarketBrowseType) -> 'MarketBrowse':
        """Creates a MarketBrowse packet from given data.

        Args:
            id (int): The item ID.
            tier (int): The item tier.
            browse_type (MarketBrowseType): The type of market browse.

        Returns:
            MarketBrowse: The constructed MarketBrowse packet.
        """
        packet = bytearray()
        packet.append(browse_type.value)
        packet.extend(struct.pack('<H', item_id))

        if tier > -1:
            packet.append(tier)

        self.packet = bytes(packet)

    def _read_packet(self):
        self.browse_type = MarketBrowseType(self._read_byte())
        self.id = self._read_short()

        meta_data = ItemMetaData(id=self.id)
        meta_data.load_from_proto()
        self.tier = meta_data.tier

        if self.tier > -1:
            self.tier = self._read_byte()
