import asyncio
from utils.client import Client
from utils.data.market_values import MarketValues, MarketBoard, MarketBoardTraderData
from utils.extraction.network.network_sniffer import NetworkSniffer
from utils.extraction.network.xtea_utils import setup
from utils.extraction.network.packets.PacketBase import PacketBase
from utils.extraction.network.packets.client.MarketBrowse import MarketBrowse
from utils.extraction.network.packets.enums import MarketBrowseType
from utils.extraction.network.packets.packet_utils import packet_to_marketvalues
from utils.extraction.network.debugger import XteaDebugger
from utils.extraction.extractor import Extractor
import time
import traceback
from utils.human_movement import wait_like_human_async
from utils.extraction.network.proxy import start_proxy
from utils.wiki import Wiki


class NetworkExtractor(Extractor):
    def __init__(self, client: Client):
        super().__init__(client)
        self.packet_analyser = NetworkSniffer(record=True)
        self.xtea_key = None

    async def setup(self, manual_session: bool = False):
        """
        Sets up the network extraction by sniffing packets, logging in, extracting the XTEA key, and opening the market.
        """
        await start_proxy([self.packet_analyser])

        # TODO: Remove test code.
        await asyncio.to_thread(input, 'Enter to extract key')
        await asyncio.to_thread(self._extract_key)
        while True:
            await asyncio.to_thread(input, 'Enter to inject message')
            # Example message. Request albino armor.
            self.packet_analyser.inject_tcp_message(PacketBase(b'\x67', True))

        # Don't actually do anything if this is a manual session.
        while manual_session:
            await asyncio.sleep(1)

    async def extract_market_values(self) -> tuple[list[MarketValues], list[MarketBoard]]:
        extracted_items: tuple[MarketValues, list[MarketValues]] = []
        market_items = [item for item in Wiki.get_marketable_proto_items().values()]

        self.client.walk_to_depot()
        self.client.wiggle()
        last_wiggle = time.time()

        batch_size = 10
        interval = 0.1
        timeout = 2
        max_retry_count = 3
        current_retry_count = 0

        while market_items:
            if time.time() - last_wiggle > 60:
                self.client.close_market()
                self.client.wiggle()
                last_wiggle = time.time()

            # Get the next batch of items.
            batch = market_items[:batch_size]
            tasks = []

            # Create MarketBrowse packets for each item in the batch.
            for item in batch:
                tasks.append(self.request_market_values(item.id, timeout=timeout))
                wait_like_human_async(interval)

            results = asyncio.gather(*tasks, return_exceptions=True)
            success_count = 0

            for item, result in zip(batch, results):
                if isinstance(result, TimeoutError):
                    # Timeouts are expected, so long as we have some results.
                    continue
                elif isinstance(result, Exception):
                    print(f"Error while requesting market values for item {item.id}: {result}")
                    traceback.print_exc()
                    continue

                extracted_items.append(result)
                market_items.remove(item)
                success_count += 1

            if success_count == 0:
                if current_retry_count >= max_retry_count:
                    raise Exception("Failed to extract market values after multiple retries.")

                print(f"Failed to extract market values for all items in batch. {current_retry_count=}")
                current_retry_count += 1

            # If we had a timeout, wait longer to avoid spamming the server.
            if success_count < batch_size:
                await wait_like_human_async(interval * 3)

        market_boards: list[MarketBoard] = []
        market_value_items: list[MarketValues] = []

        # Convert items to MarketValues objects.
        for market_values, historical_values in extracted_items:
            market_sellers = sorted([MarketBoardTraderData(name=seller.name, amount=seller.amount, price=seller.price, time=seller.timestamp) for seller in market_values.sell_offers], key=lambda x: x.price)
            market_buyers = sorted([MarketBoardTraderData(name=buyer.name, amount=buyer.amount, price=buyer.price, time=buyer.timestamp) for buyer in market_values.buy_offers], key=lambda x: x.price, reverse=True)
            market_boards.append(MarketBoard(id=item.id, sellers=market_sellers, buyers=market_buyers, update_time=time.time()))

            for historical_value in historical_values[::-1]:
                market_value_items.append(historical_value)

            market_value_items.append(market_values)

        return market_value_items, market_boards

    async def request_market_values(self, item_id: int, timeout: int = 2) -> tuple[MarketValues, list[MarketValues]]:
        """ Requests market values for a specific item by its ID.

        Args:
            item_id (int): The ID of the item to request market values for.
            timeout (int, optional): The maximum time to wait for the response. Defaults to 2 seconds.

        Raises:
            TimeoutError: Raised if the response is not received within the timeout period.

        Returns:
            tuple[MarketValues, list[MarketValues]]: The market values and historical values for the requested item.
        """
        market_item = Wiki.get_marketable_proto_items()[item_id]
        market_browse_packet = MarketBrowse().from_data(item_id, 1 if market_item.tier > -1 else -1, MarketBrowseType.Browse)
        self.packet_analyser.inject_tcp_message(market_browse_packet)

        wait_time = time.time() + timeout
        while item_id not in self.packet_analyser.browse_results or item_id not in self.packet_analyser.detail_results:
            if time.time() > wait_time:
                raise TimeoutError(f"Timeout while waiting for market browse packet for item {item_id}.")

            await asyncio.sleep(0.1)

        market_browse = self.packet_analyser.browse_results[item_id]
        market_detail = self.packet_analyser.detail_results[item_id]

        return packet_to_marketvalues(market_detail, market_browse)

    def _setup_session(self):
        self.client.start_game()
        self.client.login_to_game()

        self._extract_key()

        if not self.client.open_market():
            self.client.exit_tibia()
            raise Exception("Failed to open market.")

    def _extract_key(self):
        setup(key_segment=XteaDebugger().find_key())
