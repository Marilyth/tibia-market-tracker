import os
from utils.extraction.network.network_sniffer import NetworkSniffer
from utils.extraction.network.packets.packet_utils import packet_to_marketvalues
from utils.extraction.network.xtea_utils import setup


class TestDebugger:
    def setup_method(self):
        self.analyzer = NetworkSniffer()

    def test_RecordedTraffic_CanRead(self):
        # Arrange
        # Read the xtea key from key.txt.
        with open(os.path.join(os.path.dirname(__file__), "example_traffic_analysis", "key.txt"), "r") as f:
            key = f.read().strip()
            key = key.split(",")
            key = [int(k) for k in key]
            setup(key_segment=key)

        # Act
        self.analyzer.replay(os.path.join(os.path.dirname(__file__), "example_traffic_analysis", "flow.mitm"))

        # Assert
        assert len(self.analyzer.results) > 4000

        for market_detail, market_browse in self.analyzer.results.values():
            market_values = packet_to_marketvalues(market_detail, market_browse)
            assert market_values

            # \0 characters would indicate failed decryption or inflation.
            for detail in market_detail.details:
                assert "\0" not in detail

            for buy_offer in market_browse.buy_offers:
                assert "\0" not in buy_offer.name

            for sell_offer in market_browse.sell_offers:
                assert "\0" not in sell_offer.name
