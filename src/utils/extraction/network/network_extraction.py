from utils.client import Client
from utils.data.market_values import MarketValues, MarketBoard, MarketBoardTraderData
from utils.extraction.memory.memory_extraction import MemoryExtractor
from utils.extraction.network.packet_sniffer import PacketSniffer
from utils.extraction.network.packet_analyser import PacketAnalyser
from utils.extraction.network.tcp_reassembler import TCPReassembler
from utils.extraction.network.market_packet_reader import MarketPacketValues
from utils.extraction.network.debugger import XteaDebugger
from utils.extraction.extractor import Extractor
from utils.market_categories import market_categories
import time
from typing import *
import pyautogui
from tqdm import tqdm
import traceback
from utils.human_movement import wait_like_human, repeat_like_human
from utils.waiter import wait_until
from utils.json_helper import object_to_json


class NetworkExtractor(Extractor):
    def __init__(self, client: Client):
        super().__init__(client)
        self.memory_extractor = MemoryExtractor(client)
        self.packet_sniffer = PacketSniffer(record=False)
        self.packet_analyser = PacketAnalyser()
        self.tcp_reassembler = TCPReassembler()
        self.tcp_reassembler.set_new_data_callback(self.packet_analyser.handle_packet)
        self.xtea_key = None

    def setup(self, manual_session: bool = False):
        """
        Sets up the network extraction by sniffing packets, logging in, extracting the XTEA key, and opening the market.
        """
        self.packet_sniffer.sniff(self.tcp_reassembler.add_to_queue)
        self.client.start_game()
        self.client.login_to_game()
        
        self.xtea_key = XteaDebugger(self.client.tibia_process_id).find_key()
        self.packet_analyser.set_key(self.xtea_key)
        if not self.client.open_market():
            self.client.exit_tibia()
            raise Exception("Failed to open market.")
        
        # Don't actually do anything if this is a manual session.
        while manual_session:
            time.sleep(1)

    def extract_market_values(self) -> Tuple[List[MarketValues], List[MarketBoard]]:
        items: List[MarketPacketValues] = []
        market_value_items: List[MarketValues] = []
        market_boards: List[MarketBoard] = []

        for category in tqdm(market_categories[:19] + market_categories[-1:], desc=f"Category"):
            try:
                items.extend(self.crawl_market(category.index))
            except Exception as e:
                traceback.print_exc()
                
                print(f"Error while crawling market: {e}")
                break

        # Convert items to MarketValues objects.
        for item in items:
            market_values, historical_values = item.convert_to_marketvalues()
            market_sellers = sorted([MarketBoardTraderData(name=seller.name, amount=seller.amount, price=seller.price, time=seller.timestamp) for seller in item.sell_offers], key=lambda x: x.price, reverse=True)
            market_buyers = sorted([MarketBoardTraderData(name=buyer.name, amount=buyer.amount, price=buyer.price, time=buyer.timestamp) for buyer in item.buy_offers], key=lambda x: x.price, reverse=True)
            market_boards.append(MarketBoard(id=item.id, sellers=market_sellers, buyers=market_buyers, update_time=time.time()))

            for historical_value in historical_values[::-1]:
                market_value_items.append(historical_value)

            market_value_items.append(market_values)
            #print(f"Converted to market_value_item: {object_to_json(market_values)}")

        return market_value_items, market_boards

    def crawl_market(self, category_index: int, starting_index: int = 0) -> List[MarketValues]:
        """
        Crawls the market for all items by iterating through the categories.

        Args:
            category_index: The index of the category to start at.
            starting_index: The index of the item to start at.
        Returns:
            A list of MarketValues objects.
        """
        results = []

        # Reopen the market to avoid being kicked out.
        self.client.close_market()
        self.client.wiggle()
        self.client.open_market()

        self.client._wait_until_find("images/Category.png", click=True, cache=False, coordinate_deviation=1)

        # Go to the correct category.
        repeat_like_human(lambda: pyautogui.press("down"), category_index, wait_time=0.1)

        # Tab to the item list. This number might have to be changed if the market is updated.
        repeat_like_human(lambda: pyautogui.press("tab"), 10, wait_time=0.1)
        
        # Go through the items quickly, except for the last one.
        # This is to make sure the item's value is fully loaded and we aren't rate limited.
        if starting_index > 1:
            repeat_like_human(lambda: pyautogui.press("down"), starting_index, wait_time=0.06, target_deviation=0.01)
            wait_like_human(8)

        fail_count = 0
        result = None

        while True:
            pyautogui.PAUSE = 0.01
            self.packet_analyser.results = []

            # Go to the next item.
            wait_like_human(0.3, 0.05)
            pyautogui.press("down")

            # Wait for the packet to be processed.
            was_processed = wait_until(lambda: len(self.packet_analyser.results) > 0, 2, 0.01)

            if not was_processed:
                fail_count += 1

                # Reading the item failed 5 times. Continue with next category.
                if fail_count >= 5:
                    print("Failed to process packet. Continuing with next category.")
                    break
                else:
                    # Retry the item.
                    if result:
                        wait_like_human(0.3, 0.05)
                        self.packet_analyser.results = []
                        pyautogui.press("up")
                        
                        was_processed = wait_until(lambda: len(self.packet_analyser.results) > 0, 2, 0.01)
                        if was_processed:
                            test_result = self.packet_analyser.results.pop(0)

                            if test_result.id != result.id:
                                print("Reached end of category. Going up did not yield the last item.")
                                break
                    
                    continue

            # Get the result.
            fail_count = 0
            result = self.packet_analyser.results.pop(0)
            results.append(result)

            print(f"Received market packet for {result.id}")

        return results