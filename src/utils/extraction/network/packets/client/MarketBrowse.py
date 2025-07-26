from utils.data.market_values import ItemMetaData
from utils.extraction.network.packets.PacketBase import PacketBase


class MarketBrowse(PacketBase):
    def __init__(self, packet):
        super().__init__(packet, True)

        self.id: int
        self.tier: int

        self._read_packet()

    def _read_packet(self):
        unknown = self._read_byte()
        self.id = self._read_short()

        meta_data = ItemMetaData(id=self.id)
        meta_data.load_from_proto()
        self.tier = meta_data.tier

        if self.tier > -1:
            self.tier = self._read_byte()
