from xtea import *
from typing import List
from mitmproxy import ctx, tcp, http, flow
from mitmproxy.io import FlowReader, FlowWriter
from utils.extraction.network.sequence_manager import SequenceManager
from utils.extraction.network.packets.packet_utils import read_packet
from utils.extraction.network.packets.packet_base import PacketBase
from utils.extraction.network.packets.server.market_detail import MarketDetail
from utils.extraction.network.packets.server.market_browse import MarketBrowse
from utils.extraction.network.packets.client.market_browse import MarketBrowse as ClientMarketBrowse
from utils.extraction.network.xtea_utils import decrypt, encrypt, is_ready
import time
import sys
import subprocess
import os
import traceback
from threading import Lock


class NetworkSniffer:
    def __init__(self, record: bool = False):
        """Initialises an XTeaDecrypter.

        Args:
            key (List[int]): The key to use for decryption.
            rounds (int, optional): The number of rounds to use for decryption. Defaults to 64.
            byte_order (str, optional): The byte order to use for decryption. Defaults to "little".
        """
        self.decompressor = {}
        self.queue: list[flow.Flow] = []
        self.key = None
        self.key_string = None
        self.xtea = None
        self.blocked_src: str = None
        self.incomplete_packets = []
        self.decrompression_stream = bytes()
        self.queue_lock = Lock()
        self.prev = bytes()
        self.flow_file = None
        self.main_flow = None
        self.sequence_numbers: dict[tuple, SequenceManager] = {}
        self.results: dict[int, tuple[MarketDetail, MarketBrowse]] = {}
        self._detail_results: dict[int, MarketDetail] = {}
        self._browse_results: dict[int, MarketBrowse] = {}

        if record:
            self.flow_file = open("flow.mitm", "wb")

    def replay(self, record_file: str = "flow.mitm"):
        """Replays the flow file that was written by the sniffer.
        """
        with open(record_file, "rb") as f:
            reader = FlowReader(f)
            flows = list(reader.stream())

            for flow_instance in flows:
                if isinstance(flow_instance, tcp.TCPFlow):
                    self.tcp_message(flow_instance)
                elif isinstance(flow_instance, http.HTTPFlow):
                    if not flow_instance.response:
                        self.request(flow_instance)
                    else:
                        self.response(flow_instance)

    def request(self, http_flow: http.HTTPFlow):
        """Handles a request packet.

        Args:
            http_flow (http.HTTPFlow): The HTTP flow to handle.
        """
        # Ignore requests, we only care about TCP messages.
        self._write_flow(http_flow)
        print(f"\n -> {http_flow.request.pretty_url}: {http_flow.request.text[:1024]}")

    def response(self, http_flow: http.HTTPFlow):
        """Handles a response packet.

        Args:
            http_flow (http.HTTPFlow): The HTTP flow to handle.
        """
        # Ignore responses, we only care about TCP messages.
        self._write_flow(http_flow)
        print(f"\n <- {http_flow.request.pretty_url}: {http_flow.response.text[:1024]}")

    def inject_tcp_message(self, packet: PacketBase):
        """Injects a TCP message into the sniffer.

        Args:
            message (bytes): The TCP message to inject.
            to_client (bool): Whether the message is from the client or server.
        """
        connection = self.main_flow.client_conn.address if packet.from_client else self.main_flow.server_conn.address
        sequence_manager = self.sequence_numbers[connection]

        # Add a padding length byte to the encrypted message.
        message = packet.packet

        padding_bytes = (8 - (len(message) + 1) % 8) % 8
        message = padding_bytes.to_bytes(1, 'little') + message

        encrypted_message = encrypt(message)

        # Build and prepend header.
        length = len(encrypted_message) // 8
        sequence_number = sequence_manager.get_next_actual_sequence()
        compression_flag = 0

        message = (
            length.to_bytes(2, 'little') +
            sequence_number.to_bytes(2, 'little') +
            compression_flag.to_bytes(2, 'little') +
            encrypted_message
        )

        ctx.master.commands.call("inject.tcp", self.main_flow, not packet.from_client, b"injected" + message)

    def tcp_message(self, tcp_flow: tcp.TCPFlow):
        """Handles a TCP message packet.

        Args:
            tcp_flow (tcp.TCPFlow): The TCP flow to handle.
        """
        message = tcp_flow.messages[-1]
        self._write_flow(tcp_flow)

        self.handle_packet(tcp_flow, message)

    def is_ready_for_injection(self) -> bool:
        """Returns whether the sniffer is ready for injection."""
        return self.main_flow is not None and is_ready()

    def handle_packet(self, tcp_flow: tcp.TCPFlow, packet: tcp.TCPMessage):
        """Handles a Tibia packet.

        Args:
            tcp_flow (tcp.TCPFlow): The TCP flow to handle.
            packet (tcp.TCPMessage): The packet to handle.
        """
        self.queue_lock.acquire()
        self.queue.append((tcp_flow, packet))

        if is_ready():
            for tcp_flow, packet in list(self.queue):
                self.queue.pop()
                self._handle_packet(tcp_flow, packet)

        self.queue_lock.release()

    @staticmethod
    def bytes_to_readable_string(data: bytes) -> str:
        """Converts a bytes object to a readable string.

        Args:
            data (bytes): The bytes object to convert.

        Returns:
            str: The readable string.
        """
        if data:
            return " ".join([f"0x{byte:02x}" for byte in data])
        else:
            return None

    def decompress_bytes(self, data: bytes, sender: str) -> bytes:
        """Decompresses a bytes object.

        Args:
            data (bytes): The bytes object to decompress.
            sender (str): The sender of the packet.

        Returns:
            bytes: The decompressed bytes object.
        """
        data_str = NetworkSniffer.bytes_to_readable_string(data)

        # zlib does not work with Tibia packets, so use the zlib.net C# library.
        if not sender in self.decompressor:
            decompressor_location = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "decompressor", "bin", "Debug", "net8.0", "decompressor.dll")
            self.decompressor[sender] = subprocess.Popen(["dotnet", decompressor_location, data_str], stderr=subprocess.PIPE, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            os.set_blocking(self.decompressor[sender].stdout.fileno(), False)
            os.set_blocking(self.decompressor[sender].stderr.fileno(), False)

        # Send data to decompressor.
        response = self.decompressor[sender].stdin.write(data_str.encode() + b"\n")
        self.decompressor[sender].stdin.flush()

        response = b''
        while len(response) == 0 or response[-1] != 10:
            new_response = self.decompressor[sender].stdout.read()

            if new_response:
                response += new_response

            time.sleep(0.01)

        response = response.decode().strip()

        if "Exception" in response:
            raise Exception(response)

        byte_expressions = response.split(" ")

        # Convert e.g. ['1B', 'A2'] to [0x1B, 0xA2].
        byte_expressions = [int(byte_expression, 16) for byte_expression in byte_expressions]

        # Convert byte_expressions to bytes.
        response = bytes(byte_expressions)

        return response

    def _decrypt_packet(self, tcp_flow: tcp.TCPFlow, packet: tcp.TCPMessage, raw_data: bytes) -> tuple[list[PacketBase], bytes] | None:
        """ Decrypts a client packet using the XTEA algorithm.
        """
        if not raw_data:
            return

        is_injected = raw_data.startswith(b"injected")
        if is_injected:
            raw_data = raw_data[8:]
            packet.content = raw_data

        sender = tcp_flow.client_conn.address if packet.from_client else tcp_flow.server_conn.address

        # First 2 bytes are the size of the packet load in multiples of 8 bytes (minus the header) in little endian. I.e. 0c00 is 12 bytes.
        packet_size = int.from_bytes(raw_data[:2], byteorder=sys.byteorder, signed=False) * 8
        actual_size = len(raw_data[6:])

        # The next 2 bytes, are the sequence number, and the next 2 bytes are the compression flag.
        sequence_number = int.from_bytes(raw_data[2:4], byteorder=sys.byteorder, signed=False)
        compression_flag = int.from_bytes(raw_data[4:6], byteorder=sys.byteorder, signed=False)

        is_compressed = compression_flag == 0xC000
        is_valid = is_compressed or compression_flag == 0x0000

        if self.incomplete_packets and not packet.from_client and not is_valid:
            # Append the raw_data to the last incomplete packet.
            incomplete_packet = [packet for packet in self.incomplete_packets if packet[1] == sender][-1]
            raw_data = incomplete_packet[0] + raw_data
            self.incomplete_packets.remove(incomplete_packet)

            return self._decrypt_packet(tcp_flow, packet, raw_data)

        if packet_size > actual_size and not packet.from_client and is_compressed:
            # Packet is not complete yet. Wait for the next packet.
            self.incomplete_packets.append((raw_data, sender))
            return

        # If size is bigger than the actual size, there is another packet appended to this one.
        next_data = None
        if packet_size < actual_size:
            next_data = raw_data[6 + packet_size:]
            raw_data = raw_data[:packet_size + 6]

        # Handle sequence number changes in case packages were injected.
        if not sender in self.sequence_numbers:
            self.sequence_numbers[sender] = SequenceManager()

        sequence_manager = self.sequence_numbers[sender]

        if is_injected:
            sequence_manager.injection_count += 1
        else:
            # The sequence number needs to be adjusted if any messages were injected.
            # Otherwise the connection drops.
            adjusted_packet_content = sequence_manager.adjust_sequence_number(raw_data)
            packet.content = packet.content.replace(raw_data, adjusted_packet_content)

        # Decrypt the packet.
        decrypted_data = decrypt(raw_data[6:6 + packet_size])
        payload = decrypted_data

        if not is_valid:
            if packet.from_client:
                print(f"Invalid compression flag: {compression_flag}")
                return None
            else:
                raise Exception(f"Invalid compression flag: {compression_flag}")

        # Because the payload is now a multiple of 8 bytes, a few bytes are superfluous sometimes.
        truncate_bytes = int.from_bytes(payload[:1], byteorder=sys.byteorder, signed=False)
        payload = payload[1:]

        if truncate_bytes > 0:
            payload = payload[:-truncate_bytes]

        if is_compressed:
            # First 2 bytes are the size of the decompressed data.
            payload = self.decompress_bytes(payload, sender)[2:]

        return read_packet(payload, packet.from_client), next_data

    def _handle_packet(self, flow: tcp.TCPFlow, packet: tcp.TCPMessage):
        """Helper function to handle a packet.

        Args:
            packet (Packet): The packet to handle.
        """
        packet_srv = flow.server_conn.address[0]
        packet_srv_port = flow.server_conn.address[1]
        packet_srv = f"{packet_srv}:{packet_srv_port}"

        # There seem to be multiple identical streams when talking to Tibia.
        # The first one is being blocked by us. Also ignore all streams that are not from Tibia 7171.
        if packet_srv == self.blocked_src or packet_srv_port != 7171:
            return

        next_data = packet.content

        # A packet might contain multiple commands. Handle them one by one.
        while next_data:
            result = None

            try:
                result = self._decrypt_packet(flow, packet, next_data)
            except Exception as e:
                if not self.blocked_src:
                    self.blocked_src = packet_srv
                    print(f"Blocked {packet_srv} due to error: {e}")

                traceback.print_exc()
                print(f"Error while reading market packet {packet.content}: {e}")

            if not result:
                return

            # Set main flow for injections.
            self.main_flow = flow

            game_packets, next_data = result

            for game_packet in game_packets:
                if isinstance(game_packet, MarketDetail):
                    print(f"Received market packet {game_packet.id}.")
                    self._detail_results[game_packet.id] = game_packet
                    self._check_if_item_complete(game_packet.id)
                elif isinstance(game_packet, MarketBrowse):
                    print(f"Received market browse packet {game_packet.id}")
                    self._browse_results[game_packet.id] = game_packet
                    self._check_if_item_complete(game_packet.id)
                elif isinstance(game_packet, ClientMarketBrowse):
                    print(f"Sending out client market browse packet {game_packet.id}")
                else:
                    # Might want to handle other packets in the future.
                    pass

    def _check_if_item_complete(self, item_id: int) -> bool:
        """Checks if we have both a MarketDetail and MarketBrowse packet for the given item ID.
        If so, adds them to the results.

        Args:
            item_id (int): The item ID to check.

        Returns:
            bool: True if we have both packets, False otherwise.
        """
        if item_id in self._detail_results and item_id in self._browse_results:
            self.results[item_id] = (self._detail_results[item_id], self._browse_results[item_id])
            return True

        return False

    def _write_flow(self, flow: flow.Flow):
        """Writes a flow to a file.

        Args:
            flow: The flow to write.
        """
        if self.flow_file is None:
            return

        writer = FlowWriter(self.flow_file)
        writer.add(flow)
