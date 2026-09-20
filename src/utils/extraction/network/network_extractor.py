import asyncio
import logging
import time
from collections.abc import Callable

import pyautogui
from opentelemetry import trace
from tqdm import tqdm

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
    ITEM_DELAY = 0.42
    RETRY_DELAY = 5
    PACKET_TIMEOUT = 2
    WIGGLE_INTERVAL = 14 * 60

    def __init__(self, client: Client) -> None:
        super().__init__(client)
        self.sniffer = NetworkSniffer()
        self.failed_item_ids: list[int] = []
        self._category_item_ids: list[int] = []

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

        marketable_ids = set(Wiki.get_marketable_proto_items())
        results: dict[int, MarketResult] = {}
        progress_bar = tqdm(total=len(marketable_ids), desc="Extracting market values")

        try:
            if not self.client.open_market():
                raise RuntimeError("Failed to open market.")

            # Use monotonic to ensure we don't get affected by system time changes.
            last_wiggle = time.monotonic()

            # The final "Weapons: All" category duplicates the specific weapon categories.
            for category in market_categories[:-1]:
                last_wiggle = await self._extract_category(category.index, marketable_ids, results, progress_bar, last_wiggle)
        finally:
            progress_bar.close()

        return self._convert_results(results, marketable_ids)

    async def _wait_until_ready(self) -> None:
        """Waits until packet decryption has been initialized."""
        while not is_ready():
            await asyncio.sleep(0.1)

    async def _extract_category(self, category_index: int, marketable_ids: set[int], results: dict[int, MarketResult], progress_bar: tqdm, last_wiggle: float) -> float:
        """Extracts every visible item in one market category."""
        self._category_item_ids = []
        self._select_category(category_index)
        item_offset = 0

        while True:
            # Ensure we don't get kicked out for inactivity by wiggling.
            if time.monotonic() - last_wiggle > self.WIGGLE_INTERVAL:
                self.client.close_market()
                self.client.wiggle()
                if not self.client.open_market():
                    raise RuntimeError("Failed to open market after wiggle.")

                self._select_category(category_index, item_offset)
                last_wiggle = time.monotonic()

            item_ids, batch_results, category_finished = await self._read_batch(self.BATCH_SIZE)
            if not item_ids:
                return last_wiggle

            batch_results = await self._retry_batch(item_ids, batch_results)
            self._store_batch_results(batch_results, marketable_ids, results, progress_bar)
            item_offset += len(item_ids)

            if category_finished:
                return last_wiggle

    async def _retry_batch(self, item_ids: list[int], results: dict[int, MarketResult]) -> dict[int, MarketResult]:
        """Retries missing responses while rewinding the market selection."""
        for _ in range(self.MAX_RETRIES):
            missing_ids = [item_id for item_id in item_ids if item_id not in results]
            if not missing_ids:
                return results

            await wait_like_human_async(self.RETRY_DELAY)
            repeat_like_human(lambda: pyautogui.press("up"), len(item_ids), wait_time=0.1)
            retry_ids, retry_results, _ = await self._read_batch(len(item_ids), detect_category_end=False)

            if retry_ids != item_ids:
                logger.warning("Market selection changed while retrying: expected=%s got=%s", item_ids, retry_ids)

            for item_id in missing_ids:
                if item_id in retry_results:
                    results[item_id] = retry_results[item_id]

        missing_ids = [item_id for item_id in item_ids if item_id not in results]
        for item_id in missing_ids:
            if item_id not in self.failed_item_ids:
                self.failed_item_ids.append(item_id)
            logger.warning("Failed to extract item %s after %s retries.", item_id, self.MAX_RETRIES)

        return results

    @staticmethod
    def _store_batch_results(batch_results: dict[int, MarketResult], marketable_ids: set[int], results: dict[int, MarketResult], progress_bar: tqdm) -> None:
        """Adds a batch to the aggregate and advances progress for new items."""
        for item_id, result in batch_results.items():
            if item_id in marketable_ids and item_id not in results:
                progress_bar.update(1)
            results[item_id] = result

    def _select_category(self, category_index: int, item_offset: int = 0) -> None:
        """Focuses the market item list at the requested category and offset."""
        self.sniffer.client_market_browse_ids.clear()
        self.client._wait_until_find("images/Category.png", click=True, cache=False, coordinate_deviation=1, throw_on_timeout=True)
        repeat_like_human(lambda: pyautogui.press("down"), category_index, wait_time=0.1)
        repeat_like_human(lambda: pyautogui.press("tab"), 10, wait_time=0.1)
        if item_offset:
            repeat_like_human(lambda: pyautogui.press("down"), item_offset, wait_time=0.06, target_deviation=0.01)

    async def _read_batch(self, count: int, *, detect_category_end: bool = True) -> tuple[list[int], dict[int, MarketResult], bool]:
        """Selects items, identifies them from observed client packets, and reads their results."""
        category_item_ids = self._category_item_ids
        item_ids = []
        category_finished = False

        for _ in range(count):
            pyautogui.press("down")
            item_id = await self._wait_for_client_browse()

            # If no packet was sent out, assume we are done for now.
            # Might need retry later.
            if item_id is None:
                break

            item_ids.append(item_id)
            await wait_like_human_async(self.ITEM_DELAY)

        if detect_category_end:
            category_item_ids.extend(item_ids)
            self._category_item_ids = category_item_ids

        if detect_category_end and item_ids and len(item_ids) < count and len(category_item_ids) >= 2:
            # Check if the item above the current is the second to last item we received.
            # If so, the lack of a full batch is due to the category boundary.
            await wait_like_human_async(self.RETRY_DELAY)
            pyautogui.press("up")

            observed_previous_id = await self._wait_for_client_browse()
            expected_previous_id = category_item_ids[-2]
            category_finished = observed_previous_id == expected_previous_id

            # Restore focus to the last item so a retry rewinds the
            # complete batch from a known position.
            pyautogui.press("down")
            await self._wait_for_client_browse()

            if not category_finished:
                raise RuntimeError(
                    f"Short market batch did not reach the category boundary: "
                    f"{item_ids=}, {expected_previous_id=}, {observed_previous_id=}"
                )

        results = await asyncio.gather(*(self._wait_for_result(item_id) for item_id in item_ids))
        return item_ids, {item_id: result for item_id, result in zip(item_ids, results) if result is not None}, category_finished

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

    def _convert_results(self, results: dict[int, MarketResult], marketable_ids: set[int]) -> tuple[list[MarketValues], list[MarketBoard]]:
        market_values: list[MarketValues] = []
        market_boards: list[MarketBoard] = []

        for item_id, (details, browse, extraction_time) in results.items():
            if item_id not in marketable_ids:
                continue

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
