from utils.client import Client
from utils.data.market_values import MarketValues
from utils.extraction.memory.memory_extraction import MemoryExtractor
from utils.extraction.network.packet_sniffer import PacketSniffer
from utils.extraction.network.packet_analyser import PacketAnalyser
from utils.extraction.network.debugger import XteaDebugger
from utils.extraction.extractor import Extractor
import time
from typing import *


class NetworkExtractor(Extractor):
    def __init__(self, client: Client):
        super().__init__(client)
        self.memory_extractor = MemoryExtractor(client)
        self.packet_sniffer = PacketSniffer()
        self.packet_analyser = PacketAnalyser(output=False)
        self.xtea_key = None

    def setup(self):
        """
        Sets up the network extraction by sniffing packets, logging in, extracting the XTEA key, and opening the market.
        """
        self.packet_sniffer.sniff(self.packet_analyser.add_to_queue)
        self.client.start_game()
        self.client.login_to_game()
        self.xtea_key = XteaDebugger(self.client.tibia_process_id).find_key()
        self.packet_analyser.set_key(self.xtea_key)
        if not self.client.open_market():
            self.client.exit_tibia()
            raise Exception("Failed to open market.")
        
        # Network extractor isn't done yet.
        # For now, just print the decrypted packets and let the user interact.
        while True:
            time.sleep(1)

    def extract_market_values(self) -> List[MarketValues]:
        pass