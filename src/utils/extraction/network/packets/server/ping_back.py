from utils.extraction.network.packets.packet_base import PacketBase


class PingBack(PacketBase):
    def __init__(self):
        super().__init__(False)

    def from_packet(self, packet: bytes) -> 'PingBack':
        return super().from_packet(packet)
