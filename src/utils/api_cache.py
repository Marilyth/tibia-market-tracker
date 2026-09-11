import asyncio
import logging
from utils.data.market_values import MarketBoard, MarketValues
from utils.data.world_data import WorldData
from utils.mongo_manager import MongoManager


logger = logging.getLogger(__name__)


class DataCache:
    def __init__(self, mongo_manager: MongoManager):
        self.market_values_cache: dict[str, tuple[float, list[MarketValues]]] = {}
        self.market_values_lock = asyncio.Lock()

        self.market_boards_cache: dict[str, list[MarketBoard]] = {}
        self.market_boards_lock = asyncio.Lock()

        self.world_data: list[WorldData] = None
        self.world_data_lock = asyncio.Lock()

        self.mongo_manager = mongo_manager

    def invalidate_server_cache(self, server: str):
        """Invalidates the cache for the given server.

        Args:
            server (str): The server to invalidate the cache for.
        """
        if server in self.market_values_cache:
            del self.market_values_cache[server]

        if server in self.market_boards_cache:
            del self.market_boards_cache[server]

        self.world_data = None

    async def get_market_values(self, server: str):
        """Gets the market values for the given server.

        Args:
            server (str): The server to get the market values for.

        Returns:
            list: The market values for the given server.
        """
        # Check if the market values are cached and not old. If not, read it from mongodb.
        try:
            await self.market_values_lock.acquire()

            if server not in self.market_values_cache:
                values = await self.mongo_manager.get_latest_market_values(server)

                if not values:
                    return None, []

                values = sorted(values, key=lambda x: (x.sell_offers + x.buy_offers), reverse=True)
                self.market_values_cache[server] = values
        except Exception as e:
            logger.exception(f"Error while reading fullscan: {e}")
        finally:
            self.market_values_lock.release()

        return self.market_values_cache[server]

    async def get_market_boards(self, server: str) -> list[MarketBoard]:
        """Gets the market board for the given item on the given server.

        Args:
            server (str): The server to get the market board for.

        Returns:
            MarketBoard: The market boards for the given server.
        """
        try:
            await self.market_boards_lock.acquire()

            if server not in self.market_boards_cache:
                self.market_boards_cache[server] = await self.mongo_manager.get_market_boards(server)
        except Exception as e:
            logger.exception(f"Error while reading market boards: {e}")
        finally:
            self.market_boards_lock.release()

        return self.market_boards_cache[server]

    async def get_world_data(self) -> list[WorldData]:
        """Gets the world data.

        Returns:
            WorldDataResponse: The world data.
        """
        try:
            await self.world_data_lock.acquire()

            if not self.world_data:
                self.world_data = await self.mongo_manager.get_world_data()
        finally:
            self.world_data_lock.release()

        return self.world_data
