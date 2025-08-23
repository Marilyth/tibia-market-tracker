from utils.client import Client
from utils.data.market_values import ItemMetaData, MarketValues, MarketBoard, MarketBoardTraderData
from utils.extraction.network.network_sniffer import NetworkSniffer
from utils.extraction.network.xtea_utils import setup
from utils.extraction.network.packets.client.market_browse import MarketBrowse
from utils.extraction.network.packets.enums import MarketBrowseType
from utils.extraction.network.packets.packet_utils import packet_to_marketvalues
from utils.extraction.network.debugger import XteaDebugger
from utils.extraction.extractor import Extractor
from utils.human_movement import wait_like_human_async
from utils.extraction.network.proxy import start_proxy
from utils.wiki import Wiki
from tqdm import tqdm
import time
import asyncio
from enum import Enum


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
            await self.extract_market_values()

        # Don't actually do anything if this is a manual session.
        while manual_session:
            await asyncio.sleep(1)

    async def extract_market_values(self) -> tuple[list[MarketValues], list[MarketBoard]]:
        while not self.packet_analyser.is_ready_for_injection():
            await asyncio.sleep(1)

        extracted_items: list[tuple[MarketValues, list[MarketValues]]] = []
        extraction_tasks = [ItemExtractionTask(item.id, 1) for item in Wiki.get_marketable_proto_items().values()]

        last_wiggle = 0

        rate_limit_unit = 5 # The base for which rate limiting is calculated.
        requests_per_unit = 13 # The number of requests allowed per rate limit unit.

        rate_limit = rate_limit_unit / requests_per_unit

        batch_size = requests_per_unit
        time_between_items = rate_limit

        max_retry_count = 3
        current_retry_count = 0

        progress_bar = tqdm(total=len(extraction_tasks), desc="Extracting market values")

        while extraction_tasks:
            if False and time.time() - last_wiggle > 60:
                self.client.close_market()
                self.client.wiggle()

                # First request opens the market, but doesn't get any data.
                await extraction_tasks[0].request_market_values_async(self.packet_analyser)
                last_wiggle = time.time()

            # Get the next batch of items.
            batch = extraction_tasks[:batch_size]
            tasks = []

            # Create MarketBrowse packets for each item in the batch.
            for item in batch:
                tasks.append(asyncio.create_task(item.request_market_values_async(self.packet_analyser)))
                await wait_like_human_async(time_between_items)

            await asyncio.gather(*tasks, return_exceptions=True)

            for item in batch:
                if item.status != ExtractionTaskStatus.Completed:
                    if item.attempts > max_retry_count:
                        extraction_tasks.remove(item)
                        print(f"Failed to extract item {item.item_id} after {item.attempts} attempts.")
                    continue

                extracted_items.append(item.result)
                extraction_tasks.remove(item)

            progress_bar.update(len([item for item in batch if item.status == ExtractionTaskStatus.Completed]))

            if all(item.status != ExtractionTaskStatus.Completed for item in batch):
                if current_retry_count >= max_retry_count:
                    raise Exception("Failed to extract any market values after multiple retries.")

                print(f"Entire batch failed. {current_retry_count=}")
                current_retry_count += 1
            else:
                current_retry_count = 0

            # If we had a timeout, wait longer to reset the rate limit.
            if any(item.status == ExtractionTaskStatus.TimedOut for item in batch):
                await wait_like_human_async(rate_limit_unit)
            else:
                await wait_like_human_async(time_between_items)

        progress_bar.close()

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

    def _setup_session(self):
        self.client.start_game()
        self.client.login_to_game()

        self._extract_key()

        if not self.client.open_market():
            self.client.exit_tibia()
            raise Exception("Failed to open market.")

    def _extract_key(self):
        setup(key_segment=XteaDebugger().find_key())


class ItemExtractionTask:
    def __init__(self, item_id: int, timeout: int = 2):
        self.item_id = item_id
        self.timeout = timeout

        self.meta_data = ItemMetaData(id=self.item_id)
        self.meta_data.load_from_proto()

        self.attempts = 0
        self.result: tuple[MarketValues, list[MarketValues]] = None
        self.status: ExtractionTaskStatus = ExtractionTaskStatus.Pending

    async def request_market_values_async(self, sniffer: NetworkSniffer):
        """ Requests market values for a specific item by its ID.

        Args:
            item_id (int): The ID of the item to request market values for.
            timeout (int, optional): The maximum time to wait for the response. Defaults to 2 seconds.

        Raises:
            TimeoutError: Raised if the response is not received within the timeout period.

        Returns:
            tuple[MarketValues, list[MarketValues]]: The market values and historical values for the requested item.
        """
        self.status = ExtractionTaskStatus.InProgress
        self.attempts += 1

        market_browse_packet = MarketBrowse().from_data(self.item_id, MarketBrowseType.Browse, min(0, self.meta_data.tier))
        sniffer.inject_tcp_message(market_browse_packet)

        wait_time = time.time() + self.timeout
        while self.item_id not in sniffer.results:
            if time.time() > wait_time:
                self.status = ExtractionTaskStatus.TimedOut

                if self.item_id in sniffer._browse_results or self.item_id in sniffer._detail_results:
                    self.status = ExtractionTaskStatus.MissedPackage

                return

            await asyncio.sleep(0.1)

        market_detail, market_browse = sniffer.results.pop(self.item_id)

        self.result = packet_to_marketvalues(market_detail, market_browse)
        self.status = ExtractionTaskStatus.Completed


class ExtractionTaskStatus(Enum):
    Pending = 1
    InProgress = 2
    TimedOut = 3
    MissedPackage = 4
    Completed = 5
