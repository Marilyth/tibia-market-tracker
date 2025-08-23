from utils.extraction.network.packets.packet_base import PacketBase


class ConnectionPingBack(PacketBase):
    def __init__(self):
        super().__init__(True)

    def from_packet(self, packet: bytes) -> 'ConnectionPingBack':
        return super().from_packet(packet)
