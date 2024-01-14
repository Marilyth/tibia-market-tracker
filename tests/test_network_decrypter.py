from utils.extraction.network.packet_analyser import PacketAnalyser
from utils.extraction.network.market_packet_reader import MarketPacketValues
from utils.extraction.network.packet_sniffer import PacketSniffer
from utils.extraction.network.tcp_reassembler import TCPReassembler
import os
import traceback
import time


class TestDebugger:
    def setup_method(self):
        self.analyzer = PacketAnalyser()
        self.sniffer = PacketSniffer(interface=None)
        self.tcp_reassembler = TCPReassembler()

    def test_RecordedTraffic_CanRead(self):
        # Arrange
        self.tcp_reassembler.set_new_data_callback(self.analyzer.handle_packet)
        
        # Read the xtea key from key.txt.
        with open(os.path.join(os.path.dirname(__file__), "example_traffic_analysis", "key.txt"), "r") as f:
            key = f.read().strip()
            key = key.split(",")
            key = [int(k) for k in key]
            self.analyzer.set_key(key)

        # Act
        self.sniffer.sniff(self.tcp_reassembler.add_to_queue, pcap=os.path.join(os.path.dirname(__file__), "example_traffic_analysis", "recording.pcap"), sniff_async=False)
        all_results = [result.convert_to_marketvalues() for result in self.analyzer.results]
        # sort all_results by total_immediate_profit
        all_results.sort(key=lambda x: x.total_immediate_profit, reverse=True)
        unique_results = set([result.id for result in self.analyzer.results])

        # Assert
        assert all_results
        assert 31578 in unique_results # Bear skin
        assert 3587 in unique_results # Banana
        assert len(unique_results) == 609


    def test_ExampleTraffic_CanDecrypt(self):
        # Arrange
        self.analyzer.set_key([0x91c43868, 0x5462b10e, 0xd9f0c56d, 0x46928fd6])

        packages = []
        with open(os.path.join(os.path.dirname(__file__), "example_traffic_analysis", "example_traffic.txt"), "rb") as f:
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
                result = self.analyzer._decrypt_packet(package, sender.decode("utf-8"))
                if result:
                    decrypted_payloads.append(result)
            except Exception as e:
                print(f"Failed to decrypt package: {e}")
                assert False

        # Assert
        assert any([payload[1] == "MarketBrowse" for payload in decrypted_payloads])
        assert any([payload[1] == "MarketDetail" for payload in decrypted_payloads])
        assert any([payload[1] == "MarketLeave" for payload in decrypted_payloads])
        assert any([payload[1] == "GoEast" for payload in decrypted_payloads])

        # Check if the bytes payload contains the sell value for Tibia Coins.
        assert any([b"\xBB\xA0\x00\x00" in payload[0] for payload in decrypted_payloads])

        # Check if the bytes payload contains the max sell offer for Tibia Coins.
        assert any([b"\x5C\xA5\x00\x00" in payload[0] for payload in decrypted_payloads])

        # Check if the bytes payload contains the values 22118. The item id for Tibia Coins.
        assert any([b"\x66\x56\x00\x00" in payload[0] for payload in decrypted_payloads])