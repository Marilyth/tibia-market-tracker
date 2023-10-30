from xtea import *
from typing import List
import zlib
import binascii
from utils.extraction.network.packet_names import client_commands, server_commands
from scapy.all import *
import time
import sys
import subprocess
import os
import traceback


class PacketAnalyser:
    def __init__(self, rounds: int = 64, byte_order: str = sys.byteorder, output: bool = False):
        """Initialises an XTeaDecrypter.

        Args:
            key (List[int]): The key to use for decryption.
            rounds (int, optional): The number of rounds to use for decryption. Defaults to 64.
            byte_order (str, optional): The byte order to use for decryption. Defaults to "little".
        """
        self.decompressor = zlib.decompressobj(-15)
        self.byte_order = byte_order
        self.queue = []
        self.rounds = rounds
        self.key = None
        self.key_string = None
        self.xtea = None
        self.output = None
        self.incomplete_packets = []

        if output:
            self.output = open(f"traffic_{time.time()}.txt", "w+")

    def log(self, text: str):
        if self.output:
            self.output.write(text + "\n")
            self.output.flush()
        else:
            print(text)

    def set_key(self, key: List[int]):
        if len(key) != 4:
            raise ValueError("Key must be 4 integers long.")

        self.key = key
        self.key_string = b""
        for key in self.key:
            self.key_string += key.to_bytes(4, byteorder=self.byte_order, signed=False)

        self.xtea = new(self.key_string, mode=MODE_ECB, rounds=self.rounds, endian="<" if self.byte_order == "little" else ">")

        self.log(f"Key set to {key}.")
        
        for packet in self.queue:
            self._decrypt_packet(packet)

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
    
    def add_to_queue(self, packet: Packet):
        """Adds a packet to the queue.

        Args:
            packet (Packet): The packet to add.
        """
        try:
            #self.log(f"{packet.summary()}: {packet[Raw].load if Raw in packet else None}")

            if self.key is None:
                pass
            else:
                self._decrypt_packet(packet[Raw].load if Raw in packet else None, packet["TCP"].sport == 7171 if "TCP" in packet else False)
        except Exception as e:
            # Print stacktrace
            traceback.print_exc()
            self.log(f"Error while decrypting packet: {e}")
        
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
        
    def decompress_bytes(self, data: bytes) -> bytes:
        """Decompresses a bytes object.

        Args:
            data (bytes): The bytes object to decompress.

        Returns:
            bytes: The decompressed bytes object.
        """
        data_str = PacketAnalyser.bytes_to_readable_string(data)
        
        # zlib does not work with Tibia packets, so use the zlib.net C# library.
        decompressor_location = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "decompressor", "bin", "Debug", "net7.0", "decompressor.dll")
        response = subprocess.run(["dotnet", decompressor_location, data_str], capture_output=True)
        
        # Get output from stdout.
        stderr = response.stderr.decode("utf-8")

        if stderr:
            raise Exception(f"Decompression failed: {stderr}")
        
        response = response.stdout.decode("utf-8")
        byte_expressions = response.split(" ")
        
        # Convert e.g. ['1B', 'A2'] to [0x1B, 0xA2].
        byte_expressions = [int(byte_expression, 16) for byte_expression in byte_expressions]
        
        # Convert byte_expressions to bytes.
        response = bytes(byte_expressions)
        
        return response

    def _decrypt_packet(self, raw_data: bytes, from_server: bool = False):
        """ Decrypts a client packet using the XTEA algorithm.
        """
        if not raw_data:
            return
        
        #self.log(f"{raw_data}\n")

        if self.incomplete_packets and from_server:
            # Append the raw_data to the last incomplete packet.
            self.incomplete_packets[-1] += raw_data
            raw_data = self.incomplete_packets[-1]
            self.incomplete_packets = []

        # First 2 bytes are the size of the packet load (minus the size bytes) in little endian. I.e. 0c00 is 12 bytes.
        packet_size = int.from_bytes(raw_data[:2], byteorder=sys.byteorder, signed=False)

        if packet_size > len(raw_data[2:]) and from_server and len(raw_data) == 1024:
            # Packet is not complete yet. Wait for the next packet.
            self.incomplete_packets.append((raw_data))
            return

        # The next 2 bytes, are the sequence number, and the next 2 bytes are the compression flag.
        sequence_number = int.from_bytes(raw_data[2:4], byteorder=sys.byteorder, signed=False)
        compression_flag = int.from_bytes(raw_data[4:6], byteorder=sys.byteorder, signed=False)

        decrypted_data = self.decrypt(raw_data[6:6 + packet_size])

        # Read encrypted_packet_length.
        decrypted_packet_length = int.from_bytes(decrypted_data[:2], byteorder=sys.byteorder, signed=False)

        # Assert that the decryption was successful.
        #assert decrypted_packet_length <= len(decrypted_data[2:])
        payload = decrypted_data[2:decrypted_packet_length + 2]
        
        is_compressed = compression_flag & 0xC000 == 0xC000
        
        if is_compressed:
            decrypted_data = self.decompress_bytes(payload)
            payload = decrypted_data[2:]
        
        hex_data = binascii.hexlify(decrypted_data)
        hex_payload = binascii.hexlify(payload)

        command = payload[0] if payload else -1
        command_name = self.command_type_to_name(command, client_commands if not from_server else server_commands)

        if not command_name == "ClientCheck" and not "Ping" in command_name and not "Invalid" in command_name:
            self.log(f"Decrypted {is_compressed=} {packet_size=} {len(raw_data) - 2=} {from_server=} {sequence_number=} {command} {command_name} {hex_data=}")

        return payload, command_name
    