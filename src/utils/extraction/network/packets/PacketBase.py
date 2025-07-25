from utils.extraction.network.packets.packet_names import ClientCommand, ServerCommand
import struct


class PacketBase:
    def __init__(self, packet: bytes, from_client: bool):
        self.from_client = from_client
        self.packet = packet
        self.offset = 0
        self.packet_code = self._read_byte()

        if self.from_client:
            self.command = ClientCommand._value2member_map_.get(self.packet_code, ClientCommand.Invalid)
        else:
            self.command = ServerCommand._value2member_map_.get(self.packet_code, ServerCommand.Invalid)

    def _get_bytes(self, length: int) -> bytes:
        """Reads a specified number of bytes from the packet and updates the offset.

        Args:
            length (int): The number of bytes to read.

        Returns:
            bytes: The bytes read from the packet.
        """
        value = self.packet[self.offset:self.offset + length]
        self.offset += length

        return value

    def _read_format(self, fmt: str, length: int) -> object:
        """Reads a formatted value from the packet.

        Args:
            fmt (str): The format string for struct.unpack.
            length (int): The length of the bytes to read.

        Returns:
            object: The unpacked value from the packet.
        """
        return struct.unpack(fmt, self._get_bytes(length))[0]

    def _read_string(self, length: int) -> str:
        """Reads a string of a given length from the packet.

        Args:
            length (int): The length of the string to read.

        Returns:
            str: The string read from the packet.
        """
        if length <= 0:
            return ""

        return self._read_format(f"{length}s", length).decode("utf-8")

    def _read_prefixed_string(self) -> str:
        """Reads a string that starts with a short indicating its length.

        Returns:
            str: The string read from the packet.
        """
        return self._read_string(self._read_short())

    def _read_byte(self) -> int:
        """Reads a single ubyte from the packet.

        Returns:
            int: The byte read from the packet.
        """
        return self._read_format("B", 1)

    def _read_short(self) -> int:
        """Reads a ushort (2 bytes) from the packet.

        Returns:
            int: The short read from the packet.
        """
        return self._read_format("H", 2)

    def _read_int(self) -> int:
        """Reads a 4-byte uinteger from the packet.

        Returns:
            int: The integer read from the packet.
        """
        return self._read_format("I", 4)

    def _read_long(self) -> int:
        """Reads an 8-byte ulong from the packet.

        Returns:
            int: The long integer read from the packet.
        """
        return self._read_format("Q", 8)

    def __str__(self):
        """Returns a string representation of the packet."""
        arrow = "->" if self.from_client else "<-"

        return f"{arrow} {self.command.name} ({self.packet_code}): {self.packet[1:256]}..."
