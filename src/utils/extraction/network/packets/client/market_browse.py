from utils.data.market_values import ItemMetaData
from utils.extraction.network.packets.packet_base import PacketBase
from utils.extraction.network.packets.enums import MarketBrowseType
from utils.extraction.network.packets.packet_names import ClientCommand
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

    def from_data(self, item_id: int, browse_type: MarketBrowseType, tier: int = -1) -> 'MarketBrowse':
        """Creates a MarketBrowse packet from given data.

        Args:
            id (int): The item ID.
            browse_type (MarketBrowseType): The type of market browse.
            tier (int): The item tier. Defaults to -1 (i.e., no tier).

        Returns:
            MarketBrowse: The constructed MarketBrowse packet.
        """
        super().from_packet(bytes([ClientCommand.MarketBrowse.value]))

        self.write_byte(browse_type.value)
        self.write_short(item_id)

        if tier > -1:
            self.write_byte(tier)

        return self

    def _read_packet(self):
        self.browse_type = MarketBrowseType(self.read_byte())
        self.id = self.read_short()

        meta_data = ItemMetaData(id=self.id)
        meta_data.load_from_proto()
        item_tier = meta_data.tier

        if item_tier > -1:
            self.tier = self.read_byte()
        else:
            # Item can't have a tier, set to -1.
            self.tier = -1
