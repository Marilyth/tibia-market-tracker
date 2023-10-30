from utils.extraction.network.packet_analyser import PacketAnalyser
import os


class TestDebugger:
    def setup_method(self):
        self.analyzer = PacketAnalyser(output=True)

    def test_ExampleTraffic_CanDecrypt(self):
        # Arrange
        self.analyzer.set_key([0xde00dd76, 0xd588c53b, 0x93657f08, 0xc819a331])

        packages = []
        with open(os.path.join(os.path.dirname(__file__), "example_traffic.txt"), "rb") as f:
            example_network_packet = f.readlines()

            for packet in example_network_packet:
                if b"Raw: " in packet:
                    data = packet.split(b"Raw: ")[1]
                    data = eval(data)
                    packages.append([data, b"7171 > " in packet])
        
        # Act
        decrypted_payloads = []
        for package, from_server in packages:
            try:
                result = self.analyzer._decrypt_packet(package, from_server)
                if result:
                    decrypted_payloads.append(result)
            except Exception as e:
                assert False

        # Assert
        assert any([payload[1] == "MarketBrowse" for payload in decrypted_payloads])
        assert any([payload[1] == "MarketDetail" for payload in decrypted_payloads])
        assert any([payload[1] == "GoEast" for payload in decrypted_payloads])
        assert any([payload[1] == "MarketLeave" for payload in decrypted_payloads])

        # Check if the bytes payload contains the value 41200. The sell offer for Tibia Coins.
        assert any([b"\xF0\xA0\x00\x00" in payload[0] for payload in decrypted_payloads])

        # Check if the bytes payload contains the values 22118. The item id for Tibia Coins.
        assert any([b"\x66\x56" in payload[0] for payload in decrypted_payloads])