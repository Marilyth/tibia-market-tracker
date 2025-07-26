from utils.extraction.network.packets.PacketBase import PacketBase
from utils.extraction.network.packets.packet_names import ClientCommand, ServerCommand
from utils.extraction.network.packets.server.MarketDetail import MarketDetail
from utils.extraction.network.packets.client.MarketBrowse import MarketBrowse


def read_packet(packet: bytes, from_client: bool) -> PacketBase:
    """Reads a packet and returns an instance of PacketBase which fits the packet data.

    Args:
        packet (bytes): The raw packet data.
        from_client (bool): Indicates if the packet is from the client.

    Returns:
        PacketBase: An instance of PacketBase with the parsed packet data.
    """
    packet = packet if packet else bytes([0])

    if from_client:
        return _read_client_packet(packet)
    else:
        return _read_server_packet(packet)

def _read_server_packet(packet: bytes) -> PacketBase:
    packet_code = packet[0]

    match packet_code:
        case ServerCommand.MarketDetail.value:
            return MarketDetail(packet)
        case _:
            return PacketBase(packet, False)

def _read_client_packet(packet: bytes) -> PacketBase:
    packet_code = packet[0]

    match packet_code:
        case ClientCommand.MarketBrowse.value:
            return MarketBrowse(packet)
        case _:
            return PacketBase(packet, True)
