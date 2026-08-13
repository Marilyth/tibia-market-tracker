import pytest
from utils.mongo_manager import MongoManager


class TestDebugger:
    def setup_method(self):
        self.manager = MongoManager("")

    @pytest.mark.asyncio
    async def test_GetLatestMarketValues_ReturnsExpected(self):
        # Act
        result = await self.manager.get_latest_market_values("Antica")

        # Assert
        assert len(result) > 3600

    @pytest.mark.asyncio
    async def test_GetWorldData_ReturnsExpected(self):
        # Act
        result = await self.manager.get_world_data()

        # Assert
        assert len(result) > 0
        assert len(result[0].name) > 0
        assert result[0].last_update is not None

    @pytest.mark.asyncio
    async def test_GetItemComparison_ReturnsExpected(self):
        # Act
        result = await self.manager.get_item_comparison(22118)

        # Assert
        assert len(result) > 0
        assert len(result[0].name) > 0