from utils.extraction.network.packets.packet_base import PacketBase


class Ping(PacketBase):
    def __init__(self):
        super().__init__(False)

    def from_packet(self, packet: bytes) -> 'Ping':
        return super().from_packet(packet)
