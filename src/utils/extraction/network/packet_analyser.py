from xtea import *
from typing import List
import zlib
import binascii
from utils.extraction.network.packet_names import client_commands, server_commands
from utils.extraction.network.market_packet_reader import MarketPacketReader, MarketPacketValues
from utils.json_helper import object_to_json
from scapy.all import *
import time
import sys
import subprocess
import os
import traceback
from threading import Lock


class PacketAnalyser:
    def __init__(self, rounds: int = 64, byte_order: str = sys.byteorder):
        """Initialises an XTeaDecrypter.

        Args:
            key (List[int]): The key to use for decryption.
            rounds (int, optional): The number of rounds to use for decryption. Defaults to 64.
            byte_order (str, optional): The byte order to use for decryption. Defaults to "little".
        """
        self.decompressor = {}
        self.byte_order = byte_order
        self.queue = []
        self.rounds = rounds
        self.key = None
        self.key_string = None
        self.xtea = None
        self.blocked_src: str = None
        self.incomplete_packets = []
        self.results: List[MarketPacketValues] = []
        self.decrompression_stream = bytes()
        self.queue_lock = Lock()
        self.prev = bytes()

    def set_key(self, key: List[int]):
        if len(key) != 4:
            raise ValueError("Key must be 4 integers long.")


        self.queue_lock.acquire()

        self.key = key
        self.key_string = b""
        for key in self.key:
            self.key_string += key.to_bytes(4, byteorder=self.byte_order, signed=False)

        self.xtea = new(self.key_string, mode=MODE_ECB, rounds=self.rounds, endian="<" if self.byte_order == "little" else ">")
        print(f"Key set to {self.key}.")

        # Handle all packets in the queue.
        for packet in self.queue:
            try:
                self._handle_packet(packet)
            except Exception as e:
                pass
        
        self.queue_lock.release()

    @staticmethod
    def command_type_to_name(type: int, commands: dict) -> str:
        """Converts a type to a type name.

        Args:
            type (int): The type to convert.
            commands (dict): The commands to use for the conversion.

        Returns:
            str: The type name.
        """
        for command_name, command_type in commands.items():
            if command_type == type:
                return command_name
        
        return "Unknown"

    def decrypt(self, data: bytes) -> bytes:
        decrypted_data = self.xtea.decrypt(PacketAnalyser.pad_data(data))
        
        return decrypted_data
    
    def encrypt(self, data: bytes) -> bytes:
        encrypted_data = self.xtea.encrypt(PacketAnalyser.pad_data(data))
        
        return encrypted_data
    
    @staticmethod
    def pad_data(data: bytes) -> bytes:
        """Pads the data to be encrypted. It has to be a multiple of 8 bytes.

        Args:
            data (bytes): The data to pad.

        Returns:
            bytes: The padded data.
        """
        missing_bytes = (8 - len(data) % 8) % 8

        return data + b"\x00" * missing_bytes

    def _handle_packet(self, packet: Packet):
        """Helper function to handle a packet.

        Args:
            packet (Packet): The packet to handle.
        """
        # If the key is not set yet, add the packet to the queue and handle later.
        if self.key is None:
            self.queue.append(packet)
            return
        
        # Print packet flag, i.e. S, A, PA, SA, etc.
        packet_src = packet['IP'].src
        packet_src_port = packet['TCP'].sport
        packet_src = f"{packet_src}:{packet_src_port}"
        packet_seq = packet['TCP'].seq
        packet_load = len(packet[Raw].load) if Raw in packet else 0

        # There seem to be multiple identical streams when talking to Tibia.
        # The first one is being blocked by us. Also ignore all streams that are not from Tibia 7171.
        if packet_src == self.blocked_src or packet_src_port != 7171:
            return

        load = packet[Raw].load if Raw in packet else None
        next_data = packet[Raw].load if Raw in packet else None

        # A packet might contain multiple commands. Handle them one by one.
        while next_data:
            result = self._decrypt_packet(next_data, f"{packet['IP'].src}:{packet['TCP'].sport}")
            next_data = None
        
            if result:
                payload, command_name, next_data = result

                packet_reader = MarketPacketReader(payload)
                try:
                    packet_reader.read_packet()
                    self.results.append(packet_reader.result)
                except Exception as e:
                    if "packet type" not in str(e):
                        if not self.blocked_src:
                            self.blocked_src = packet_src
                            print(f"Blocked {packet_src} due to error: {e}")
                        traceback.print_exc()
                        print(f"Error while reading market packet {payload}: {e}")

    def handle_packet(self, packet: Packet):
        """Handles a Tibia packet.

        Args:
            packet (Packet): The packet to handle.
        """
        self.queue_lock.acquire()
        
        try:
            self._handle_packet(packet)
        except Exception as e:
            traceback.print_exc()
            print(f"Error while decrypting packet: {e}")
        finally:
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
        data_str = PacketAnalyser.bytes_to_readable_string(data)

        # zlib does not work with Tibia packets, so use the zlib.net C# library.
        if not sender in self.decompressor:
            decompressor_location = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "decompressor", "bin", "Debug", "net7.0", "decompressor.dll")
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

    def _decrypt_packet(self, raw_data: bytes, sender: str):
        """ Decrypts a client packet using the XTEA algorithm.
        """
        if not raw_data:
            return
        
        from_server = ":7171" in sender

        #self.log(f"{raw_data}\n")

        # First 2 bytes are the size of the packet load in multiples of 8 bytes (minus the header) in little endian. I.e. 0c00 is 12 bytes.
        packet_size = int.from_bytes(raw_data[:2], byteorder=sys.byteorder, signed=False) * 8
        actual_size = len(raw_data[6:])

        # The next 2 bytes, are the sequence number, and the next 2 bytes are the compression flag.
        sequence_number = int.from_bytes(raw_data[2:4], byteorder=sys.byteorder, signed=False)
        compression_flag = int.from_bytes(raw_data[4:6], byteorder=sys.byteorder, signed=False)
        
        is_compressed = compression_flag == 0xC000
        is_valid = is_compressed or compression_flag == 0x0000

        if self.incomplete_packets and from_server and not is_valid:
            # Append the raw_data to the last incomplete packet.
            incomplete_packet = [packet for packet in self.incomplete_packets if packet[1] == sender][-1]
            raw_data = incomplete_packet[0] + raw_data
            actual_size = len(raw_data[6:])
            packet_size = int.from_bytes(raw_data[:2], byteorder=sys.byteorder, signed=False) * 8
            sequence_number = int.from_bytes(raw_data[2:4], byteorder=sys.byteorder, signed=False)
            compression_flag = int.from_bytes(raw_data[4:6], byteorder=sys.byteorder, signed=False)
            is_compressed = compression_flag == 0xC000
            is_valid = is_compressed or compression_flag == 0x0000
            self.incomplete_packets.remove(incomplete_packet)

        if packet_size > actual_size and from_server and is_compressed:
            # Packet is not complete yet. Wait for the next packet.
            self.incomplete_packets.append((raw_data, sender))
            return
        
        # Unfinished packet was not completed. Remove it.
        for packet in self.incomplete_packets[:]:
            if packet[1] == sender:
                print("Unfinished packet was not completed. Removing.")
                self.incomplete_packets.remove(packet)

        # If size is bigger than the actual size, there is another packet appended to this one.
        next_data = None
        if packet_size < actual_size:
            next_data = raw_data[6 + packet_size:]
            raw_data = raw_data[:packet_size + 6]
        
        decrypted_data = self.decrypt(raw_data[6:6 + packet_size])
        payload = decrypted_data

        if not is_valid:
            if not from_server:
                print(f"Invalid compression flag: {compression_flag}")
                return
            else:
                raise Exception(f"Invalid compression flag: {compression_flag}")
        
        if is_compressed:
            # Because the payload is now a multiple of 8 bytes, a few bytes are superfluous sometimes.
            truncate_bytes = int.from_bytes(payload[:1], byteorder=sys.byteorder, signed=False)
            decrypted_data = self.decompress_bytes(payload[1:-truncate_bytes], sender)
            decompressed_data_length = int.from_bytes(decrypted_data[:2], byteorder=sys.byteorder, signed=False)
            payload = payload[:1] + decrypted_data[2:]

        command = payload[1] if payload else -1
        command_name = self.command_type_to_name(command, client_commands if not from_server else server_commands)

        return payload, command_name, next_data
    