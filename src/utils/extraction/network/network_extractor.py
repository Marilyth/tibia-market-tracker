import asyncio
import logging
import time
from collections.abc import Callable

import pyautogui
from opentelemetry import trace

from utils.client import Client
from utils.data.market_values import MarketBoard, MarketBoardTraderData, MarketValues
from utils.extraction.extractor import Extractor
from utils.extraction.network.debugger import XteaDebugger
from utils.extraction.network.network_sniffer import NetworkSniffer
from utils.extraction.network.packets.packet_utils import packet_to_marketvalues
from utils.extraction.network.packets.server.market_browse import OfferPacketValue
from utils.extraction.network.packets.server.market_browse import MarketBrowse as ServerMarketBrowse
from utils.extraction.network.packets.server.market_detail import MarketDetail
from utils.extraction.network.xtea_utils import is_ready, setup
from utils.human_movement import repeat_like_human, wait_like_human_async
from utils.extraction.network.proxy import get_proxy_env, start_proxy
from utils.market_categories import market_categories
from utils.wiki import Wiki


logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
MarketResult = tuple[MarketDetail, ServerMarketBrowse, float]


class NetworkExtractor(Extractor):
    """Extracts market data by driving the client and reading its packets."""

    BATCH_SIZE = 12
    MAX_RETRIES = 5
    ITEM_DELAY = 0.5 # Higher bursts are possible, but generally 2 items per second should be safer.
    RETRY_DELAY = 5
    PACKET_TIMEOUT = 2
    WIGGLE_INTERVAL = 14 * 60

    def __init__(self, client: Client) -> None:
        super().__init__(client)
        self.sniffer = NetworkSniffer()
        self.results: dict[int, MarketResult] = {}

    async def setup(self, manual_session: bool = False) -> None:
        """Sets up passive packet capture, logs in, extracts XTEA, and walks to the depot."""
        with tracer.start_as_current_span("network_extractor.setup"):
            await start_proxy([self.sniffer])
            self.client.env.update(get_proxy_env())
            await asyncio.to_thread(self._setup_session)

        while manual_session:
            await asyncio.sleep(1)

    async def extract_market_values_async(self) -> tuple[list[MarketValues], list[MarketBoard]]:
        """Extracts market values by navigating the market UI and reading server packets."""
        await self._wait_until_ready()

        if not self.client.open_market():
            raise RuntimeError("Failed to open market.")

        # The final "Weapons: All" category duplicates the specific weapon categories.
        for category in market_categories[:-1]:
            await self._extract_category(category.index)

        return self._convert_results()

    async def _wait_until_ready(self) -> None:
        """Waits until packet decryption has been initialized."""
        while not is_ready():
            await asyncio.sleep(0.1)

    async def _extract_category(self, category_index: int):
        """Extracts every visible item in one market category."""
        self._select_category(category_index)
        item_offset = 0
        retries = 0

        while True:
            # Ensure we don't get kicked out for inactivity by wiggling.
            if self.client.kick_time < time.time():
                self.client.close_market()
                self.client.wiggle()
                if not self.client.open_market():
                    raise RuntimeError("Failed to open market after wiggle.")

                self._select_category(category_index, item_offset)

            sent_ids, received = await self._read_batch(self.BATCH_SIZE)

            for key in received:
                self.results[key] = received[key]

            if len(received) < len(sent_ids):
                retries += 1

                if retries > self.MAX_RETRIES:
                    raise Exception(f"Failed to extract items from category {category_index} after {retries} retries.")

                logger.warning(f"Requested {len(sent_ids)} items, but only received {len(received)}. Retrying batch ({retries}/{self.MAX_RETRIES}).")

                await repeat_like_human(lambda: pyautogui.press("up"), len(sent_ids), 0.1, 0.03)
                await wait_like_human_async(self.RETRY_DELAY)
                continue
            
            retries = 0
            item_offset += len(received)

            # Sent out less items than expected. Assume we are done.
            if len(sent_ids) < self.BATCH_SIZE:
                break

        logger.info(f"Extracted {item_offset} items from category {category_index}.")

        if item_offset == 0:
            raise Exception(f"Failed to extract items from category {category_index}.")

    def _select_category(self, category_index: int, item_offset: int = 0) -> None:
        """Focuses the market item list at the requested category and offset."""
        self.sniffer.client_market_browse_ids.clear()
        self.client._wait_until_find("images/Category.png", click=True, cache=False, coordinate_deviation=1, throw_on_timeout=True)
        repeat_like_human(lambda: pyautogui.press("down"), category_index, wait_time=0.1)
        repeat_like_human(lambda: pyautogui.press("tab"), 10, wait_time=0.1)
        if item_offset:
            repeat_like_human(lambda: pyautogui.press("down"), item_offset, wait_time=0.06, target_deviation=0.01)

    async def _read_batch(self, count: int) -> tuple[list[int], dict[int, MarketResult], bool]:
        """Selects items, identifies them from observed client packets, and reads their results."""
        self.sniffer.client_market_browse_ids.clear()
        sent_ids = []

        for _ in range(count):
            await wait_like_human_async(self.ITEM_DELAY)

            pyautogui.press("down")
            item_id = await self._wait_for_client_browse()

            # No packet was sent out. Retry to ensure this was no error.
            if item_id is None:
                await wait_like_human_async(0.1, 0.05)
                pyautogui.press("up")
                await wait_like_human_async(self.RETRY_DELAY)

                pyautogui.press("down")
                item_id = await self._wait_for_client_browse()
            
            # No packet was sent out again. Assume we are finished.
            if item_id is None:
                break

            sent_ids.append(item_id)

        logger.debug(f"Sent {sent_ids=}")

        results = await asyncio.gather(*(self._wait_for_result(item_id) for item_id in sent_ids))
        return sent_ids, {item_id: result for item_id, result in zip(sent_ids, results) if result is not None}

    async def _wait_for_client_browse(self) -> int | None:
        """Waits for the client to send a market browse packet and returns the item ID."""
        if not await self._wait_until(lambda: bool(self.sniffer.client_market_browse_ids)):
            return None

        return self.sniffer.client_market_browse_ids.pop(0)

    async def _wait_for_result(self, item_id: int) -> MarketResult | None:
        if not await self._wait_until(lambda: self.sniffer.has_result(item_id)):
            return None

        details, browse = self.sniffer.pop_result(item_id)
        return details, browse, time.time()

    async def _wait_until(self, condition: Callable[[], bool]) -> bool:
        """Polls a condition until it succeeds or the packet timeout expires."""
        timeout = time.monotonic() + self.PACKET_TIMEOUT

        while not condition():
            if time.monotonic() > timeout:
                return False
            
            await asyncio.sleep(0.1)

        return True

    def _convert_results(self) -> tuple[list[MarketValues], list[MarketBoard]]:
        market_values: list[MarketValues] = []
        market_boards: list[MarketBoard] = []

        for item_id, (details, browse, extraction_time) in self.results.items():
            values, historical_values = packet_to_marketvalues(details, browse)
            market_boards.append(MarketBoard(id=details.id, sellers=self._market_board_traders(browse.sell_offers), buyers=self._market_board_traders(browse.buy_offers, reverse=True), update_time=extraction_time))
            market_values.extend(reversed(historical_values))
            market_values.append(values)

        return market_values, market_boards

    @staticmethod
    def _market_board_traders(offers: list[OfferPacketValue], *, reverse: bool = False) -> list[MarketBoardTraderData]:
        """Converts and sorts the offers used by a market board."""
        traders = (
            MarketBoardTraderData(name=offer.name, amount=offer.amount, price=offer.price, time=offer.timestamp)
            for offer in offers
        )
        return sorted(traders, key=lambda trader: trader.price, reverse=reverse)

    def _setup_session(self) -> None:
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

    def _extract_key(self) -> None:
        setup(key_segment=XteaDebugger().find_key())
