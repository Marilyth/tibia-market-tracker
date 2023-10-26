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

        if output:
            self.output = open(f"traffic_{time.time()}.txt", "w+")

    def log(self, text: str):
        if self.output:
            self.output.write(text)
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
            self.log(f"{packet.summary()}: {PacketAnalyser.bytes_to_readable_string(packet[Raw].load if Raw in packet else None)}\n")

            if self.key is None:
                pass
            else:
                self._decrypt_packet(packet[Raw].load if Raw in packet else None, packet["TCP"].sport == 7171 if "TCP" in packet else False)
        except Exception as e:
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
        decompressor_location = os.path.join(os.path.dirname(__file__), "..", "..", "..", "decompressor", "bin", "Debug", "net7.0", "decompressor.dll")
        response = subprocess.run(["dotnet", decompressor_location, data_str], capture_output=True)
        
        # Get output from stdout.
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

        # First 2 bytes are the size of the packet load (minus the size bytes) in little endian. I.e. 0c00 is 12 bytes.
        packet_size = int.from_bytes(raw_data[:2], byteorder=sys.byteorder, signed=False)

        #assert packet_size == len(example_network_packet[2:])

        # The next 2 bytes, are the sequence number, and the next 2 bytes are the compression flag.
        sequence_number = int.from_bytes(raw_data[2:4], byteorder=sys.byteorder, signed=False)
        compression_flag = int.from_bytes(raw_data[4:6], byteorder=sys.byteorder, signed=False)

        decrypted_data = self.decrypt(raw_data[6:6 + packet_size])

        # Read encrypted_packet_length.
        decrypted_packet_length = int.from_bytes(decrypted_data[:2], byteorder=sys.byteorder, signed=False)

        # Assert that the decryption was successful.
        assert decrypted_packet_length <= len(decrypted_data[2:])
        payload = decrypted_data[2:decrypted_packet_length + 2]
        
        is_compressed = compression_flag & 0xC000 == 0xC000
        
        if is_compressed:
            #print(", ".join([f"0x{byte:02x}" for byte in raw_data]))
            #print(", ".join([f"0x{byte:02x}" for byte in payload]))
            decrypted_data = self.decompress_bytes(payload)
            payload = decrypted_data[2:]
        
        hex_data = binascii.hexlify(decrypted_data)
        hex_payload = binascii.hexlify(payload)

        command = payload[0]
        command_name = self.command_type_to_name(command, client_commands if not from_server else server_commands)
        self.log(f"Decrypted {from_server=} {command} {command_name}")

        return payload
    

if __name__ == "__main__":
    xtea_decrypter = PacketAnalyser()
    xtea_decrypter.set_key([0x66c112a6, 0xddecf1e0, 0x8f674514, 0x31d0171c])

    packages = []
    with open(os.path.join(os.path.dirname(__file__), "example_traffic.txt"), "rb") as f:
        example_network_packet = f.readlines()

        for packet in example_network_packet:
            if b"Raw: " in packet:
                data = packet.split(b"Raw: ")[1]
                data = eval(data)
                packages.append([data, b"7171 > " in packet])
    
    for package, from_server in packages:
        try:
            xtea_decrypter._decrypt_packet(package, from_server)
        except Exception as e:
            pass
        