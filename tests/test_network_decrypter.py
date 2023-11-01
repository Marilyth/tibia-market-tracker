from utils.extraction.network.packet_analyser import PacketAnalyser
import os


class TestDebugger:
    def setup_method(self):
        self.analyzer = PacketAnalyser(output=False)

    def test_ExampleTraffic_CanDecrypt(self):
        # Arrange
        self.analyzer.set_key([0x729fc9ca, 0xde11a6ab, 0x5741b35c, 0x43693b71])

        packages = []
        with open(os.path.join(os.path.dirname(__file__), "traffic_1698786393.771707.txt"), "rb") as f:
            example_network_packet = f.readlines()

            for packet in example_network_packet:
                if b"Raw: " in packet:
                    data = packet.split(b"Raw: ")[1]
                    data = eval(data)
                    packages.append([data, packet.split(b" > ")[0].split(b" ")[-1]])
        
        # Act
        decrypted_payloads = []
        for package, sender in packages:
            try:
                result = self.analyzer._decrypt_packet(package, sender)
                if result:
                    decrypted_payloads.append(result)
            except Exception as e:
                print(f"Failed to decrypt package: {e}")
                assert False

        # Assert
        assert any([payload[1] == "MarketBrowse" for payload in decrypted_payloads])
        assert any([payload[1] == "MarketDetail" for payload in decrypted_payloads])
        assert any([payload[1] == "GoEast" for payload in decrypted_payloads])
        assert any([payload[1] == "MarketLeave" for payload in decrypted_payloads])

        # Check if the bytes payload contains the value 41200. The sell offer for Tibia Coins.
        assert any([b"\xF0\xA0\x00\x00" in payload[0] for payload in decrypted_payloads])

        # Check if the bytes payload contains the value 10001. The sell offer for Tibia Coins.
        assert any([b"\x11\x27\x00\x00" in payload[0] for payload in decrypted_payloads])

        # Check if the bytes payload contains the values 22118. The item id for Tibia Coins.
        assert any([b"\x66\x56" in payload[0] for payload in decrypted_payloads])