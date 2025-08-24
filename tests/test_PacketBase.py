import struct
from utils.extraction.network.packets.packet_base import PacketBase

class TestPacketBase:
    def setup_method(self):
        """Setup a PacketBase instance for testing."""
        self.packet = PacketBase(from_client=True)
        self.packet.packet = b""
        self.packet.offset = 0

    def test_write_format_byte(self):
        """Test writing a single byte."""
        # Arrange
        value = 255  # Max value for a single byte
        fmt = "B"

        # Act
        self.packet.write_format(fmt, value)

        # Assert
        assert self.packet.packet == struct.pack(fmt, value)
        assert self.packet.offset == struct.calcsize(fmt)

    def test_write_format_short(self):
        """Test writing a 2-byte short."""
        # Arrange
        value = 65535  # Max value for a 2-byte unsigned short
        fmt = "H"

        # Act
        self.packet.write_format(fmt, value)

        # Assert
        assert self.packet.packet == struct.pack(fmt, value)
        assert self.packet.offset == struct.calcsize(fmt)

    def test_write_format_int(self):
        """Test writing a 4-byte integer."""
        # Arrange
        value = 4294967295  # Max value for a 4-byte unsigned integer
        fmt = "I"

        # Act
        self.packet.write_format(fmt, value)

        # Assert
        assert self.packet.packet == struct.pack(fmt, value)
        assert self.packet.offset == struct.calcsize(fmt)

    def test_write_format_long(self):
        """Test writing an 8-byte long."""
        # Arrange
        value = 18446744073709551615  # Max value for an 8-byte unsigned long
        fmt = "Q"

        # Act
        self.packet.write_format(fmt, value)

        # Assert
        assert self.packet.packet == struct.pack(fmt, value)
        assert self.packet.offset == struct.calcsize(fmt)

    def test_write_format_multiple_values(self):
        """Test writing multiple values sequentially."""
        # Arrange
        values = [(255, "B"), (65535, "H"), (4294967295, "I")]
        expected_packet = b"".join(struct.pack(fmt, value) for value, fmt in values)

        # Act
        for value, fmt in values:
            self.packet.write_format(fmt, value)

        # Assert
        assert self.packet.packet == expected_packet
        assert self.packet.offset == sum(struct.calcsize(fmt) for _, fmt in values)

    def test_write_format(self):
        # Arrange
        fmt = "I"  # Unsigned int (4 bytes)
        value = 123456

        # Act
        self.packet.write_format(fmt, value)

        # Assert
        expected_bytes = struct.pack(fmt, value)
        assert self.packet.packet == expected_bytes
        assert self.packet.offset == len(expected_bytes)

    def test_read_format(self):
        # Arrange
        fmt = "I"  # Unsigned int (4 bytes)
        value = 123456
        self.packet.packet = struct.pack(fmt, value)

        # Act
        result = self.packet.read_format(fmt, 4)

        # Assert
        assert result == value
        assert self.packet.offset == 4

    def test_write_bytes(self):
        # Arrange
        value = b"\x01\x02\x03"

        # Act
        self.packet.write_bytes(value)

        # Assert
        assert self.packet.packet == value
        assert self.packet.offset == len(value)

    def test_get_bytes(self):
        # Arrange
        self.packet.packet = b"\x01\x02\x03\x04\x05"
        self.packet.offset = 1

        # Act
        result = self.packet.get_bytes(3)

        # Assert
        assert result == b"\x02\x03\x04"
        assert self.packet.offset == 4

    def test_write_string(self):
        # Arrange
        value = "hello"

        # Act
        self.packet.write_string(value)

        # Assert
        assert self.packet.packet == value.encode("utf-8")
        assert self.packet.offset == len(value)

    def test_read_string(self):
        # Arrange
        value = "hello"
        self.packet.packet = value.encode("utf-8")

        # Act
        result = self.packet.read_string(len(value))

        # Assert
        assert result == value
        assert self.packet.offset == len(value)

    def test_write_prefixed_string(self):
        # Arrange
        value = "hello"

        # Act
        self.packet.write_prefixed_string(value)

        # Assert
        expected_bytes = struct.pack("H", len(value)) + value.encode("utf-8")
        assert self.packet.packet == expected_bytes
        assert self.packet.offset == len(expected_bytes)

    def test_read_prefixed_string(self):
        # Arrange
        value = "hello"
        self.packet.packet = struct.pack("H", len(value)) + value.encode("utf-8")

        # Act
        result = self.packet.read_prefixed_string()

        # Assert
        assert result == value
        assert self.packet.offset == len(self.packet.packet)

    def test_write_byte(self):
        # Arrange
        value = 255

        # Act
        self.packet.write_byte(value)

        # Assert
        assert self.packet.packet == struct.pack("B", value)
        assert self.packet.offset == 1

    def test_read_byte(self):
        # Arrange
        value = 255
        self.packet.packet = struct.pack("B", value)

        # Act
        result = self.packet.read_byte()

        # Assert
        assert result == value
        assert self.packet.offset == 1

    def test_write_short(self):
        # Arrange
        value = 65535

        # Act
        self.packet.write_short(value)

        # Assert
        assert self.packet.packet == struct.pack("H", value)
        assert self.packet.offset == 2

    def test_read_short(self):
        # Arrange
        value = 65535
        self.packet.packet = struct.pack("H", value)

        # Act
        result = self.packet.read_short()

        # Assert
        assert result == value
        assert self.packet.offset == 2

    def test_write_int(self):
        # Arrange
        value = 4294967295

        # Act
        self.packet.write_int(value)

        # Assert
        assert self.packet.packet == struct.pack("I", value)
        assert self.packet.offset == 4

    def test_read_int(self):
        # Arrange
        value = 4294967295
        self.packet.packet = struct.pack("I", value)

        # Act
        result = self.packet.read_int()

        # Assert
        assert result == value
        assert self.packet.offset == 4

    def test_write_long(self):
        # Arrange
        value = 18446744073709551615

        # Act
        self.packet.write_long(value)

        # Assert
        assert self.packet.packet == struct.pack("Q", value)
        assert self.packet.offset == 8

    def test_read_long(self):
        # Arrange
        value = 18446744073709551615
        self.packet.packet = struct.pack("Q", value)

        # Act
        result = self.packet.read_long()

        # Assert
        assert result == value
        assert self.packet.offset == 8

    def test_get_excess(self):
        # Arrange
        self.packet.packet = b"\x01\x02\x03\x04\x05"
        self.packet.offset = 2

        # Act
        result = self.packet.get_excess()

        # Assert
        assert result == b"\x03\x04\x05"

    def test_str(self):
        # Arrange
        self.packet.from_client = True
        self.packet.packet_code = 1
        self.packet.command = type("MockCommand", (), {"name": "MockCommand"})()
        self.packet.packet = b"\x01\x02\x03"

        # Act
        result = str(self.packet)

        # Assert
        assert result == "-> MockCommand (1): b'\\x02\\x03'..."