from utils.client import Client
from utils.data.market_values import ItemMetaData, MarketValues, MarketBoard, MarketBoardTraderData
from utils.extraction.network.network_sniffer import NetworkSniffer
from utils.extraction.network.packets.server.market_detail import MarketDetail
from utils.extraction.network.xtea_utils import setup
from utils.extraction.network.packets.client.market_browse import MarketBrowse
from utils.extraction.network.packets.server.market_browse import MarketBrowse as ServerMarketBrowse
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
import logging
from enum import Enum
from opentelemetry import trace


logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class NetworkExtractor(Extractor):
    def __init__(self, client: Client):
        super().__init__(client)
        self.sniffer = NetworkSniffer()
        self.xtea_key = None
        self.failed_item_ids: list[int] = []

    async def setup(self, manual_session: bool = False):
        """
        Sets up the network extraction by sniffing packets, logging in, extracting the XTEA key, and opening the market.
        """
        with tracer.start_as_current_span("network_extractor.setup"):
            await start_proxy([self.sniffer])
            await asyncio.to_thread(self._setup_session)

        # Don't actually do anything if this is a manual session.
        while manual_session:
            await asyncio.sleep(1)

    async def extract_market_values_async(self) -> tuple[list[MarketValues], list[MarketBoard]]:
        """Extracts market values for all marketable items by injecting MarketBrowse packets.

        Returns:
            tuple[list[MarketValues], list[MarketBoard]]: A tuple containing a list of MarketValues and a list of MarketBoards.
        """
        while not self.sniffer.is_ready_for_injection():
            await asyncio.sleep(1)

        successful_tasks: list[ItemExtractionTask] = []
        extraction_tasks = [ItemExtractionTask(item.id) for item in Wiki.get_marketable_proto_items().values()]

        last_wiggle = 0

        batch_size = 12
        time_between_items = 0.42

        max_retry_count = 3
        current_retry_count = 0

        progress_bar = tqdm(total=len(extraction_tasks), desc="Extracting market values")

        while extraction_tasks:
            if time.time() - last_wiggle > 840:
                self.client.close_market()
                self.client.wiggle()

                # First request opens the market, but doesn't get any data.
                await extraction_tasks[0].request_market_values_async(self.sniffer)
                last_wiggle = time.time()

            # Get the next batch of items.
            batch = extraction_tasks[:batch_size]
            tasks = []

            # Create MarketBrowse packets for each item in the batch.
            for task in batch:
                tasks.append(asyncio.create_task(task.request_market_values_async(self.sniffer)))
                await wait_like_human_async(time_between_items)

            await asyncio.gather(*tasks, return_exceptions=True)

            for task in batch:
                if task.status != ExtractionTaskStatus.Completed:
                    if task.attempts > max_retry_count:
                        extraction_tasks.remove(task)
                        self.failed_item_ids.append(task.item_id)
                        logger.warning(f"Failed to extract item {task.item_id} after {task.attempts} attempts.")
                    continue

                successful_tasks.append(task)
                extraction_tasks.remove(task)

            progress_bar.update(len([item for item in batch if item.status == ExtractionTaskStatus.Completed]))

            if all(item.status != ExtractionTaskStatus.Completed for item in batch):
                if current_retry_count >= max_retry_count:
                    raise Exception("Failed to extract any market values after multiple retries.")

                logger.warning(f"Entire batch failed. {current_retry_count=}")
                current_retry_count += 1
            else:
                current_retry_count = 0

            # If we had a timeout, wait longer to reset the rate limit.
            if any(item.status == ExtractionTaskStatus.TimedOut for item in batch):
                await wait_like_human_async(5)
            else:
                await wait_like_human_async(time_between_items)

        progress_bar.close()

        market_boards: list[MarketBoard] = []
        market_value_items: list[MarketValues] = []

        # Convert items to MarketValues objects.
        for task in successful_tasks:
            market_details, market_browse = task.result
            market_values, historical_values = packet_to_marketvalues(market_details, market_browse)

            market_sellers = sorted([MarketBoardTraderData(name=seller.name, amount=seller.amount, price=seller.price, time=seller.timestamp) for seller in market_browse.sell_offers], key=lambda x: x.price)
            market_buyers = sorted([MarketBoardTraderData(name=buyer.name, amount=buyer.amount, price=buyer.price, time=buyer.timestamp) for buyer in market_browse.buy_offers], key=lambda x: x.price, reverse=True)
            market_boards.append(MarketBoard(id=market_details.id, sellers=market_sellers, buyers=market_buyers, update_time=task.extraction_time))

            for historical_value in historical_values[::-1]:
                market_value_items.append(historical_value)

            market_value_items.append(market_values)

        return market_value_items, market_boards

    def _setup_session(self):
        with tracer.start_as_current_span("network_extractor.start_game"):
            self.client.start_game()

        with tracer.start_as_current_span("network_extractor.login"):
            self.client.login_to_game()

        with tracer.start_as_current_span("network_extractor.extract_key"):
            self._extract_key()

        with tracer.start_as_current_span("network_extractor.walk_to_depot"):
            if not self.client.walk_to_depot():
                self.client.exit_tibia()
                raise Exception("Failed to find depot.")

    def _extract_key(self):
        setup(key_segment=XteaDebugger().find_key())


class ItemExtractionTask:
    def __init__(self, item_id: int, timeout: int = 2):
        self.item_id = item_id
        self.timeout = timeout
        self.extraction_time = 0

        self.meta_data = ItemMetaData(id=self.item_id)
        self.meta_data.load_from_proto()

        self.attempts = 0
        self.result: tuple[MarketDetail, ServerMarketBrowse] = None
        self.status: ExtractionTaskStatus = ExtractionTaskStatus.Pending

    async def request_market_values_async(self, sniffer: NetworkSniffer):
        """Injects a MarketBrowse packet into the network sniffer, and waits for the response packets.

        Args:
            sniffer (NetworkSniffer): The network sniffer to inject the packet into.
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
        self.extraction_time = time.time()

        self.result = (market_detail, market_browse)
        self.status = ExtractionTaskStatus.Completed


class ExtractionTaskStatus(Enum):
    Pending = 1
    InProgress = 2
    TimedOut = 3
    MissedPackage = 4
    Completed = 5
