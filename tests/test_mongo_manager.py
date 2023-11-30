from utils.mongo_manager import MongoManager
import os


class TestDebugger:
    def setup_method(self):
        self.manager = MongoManager("")

    def test_GetLatestMarketValues_ReturnsExpected(self):
        # Act
        result = self.manager.get_latest_market_values("Antica")

        # Assert
        assert len(result) > 3600
        assert "id" in result[0]
        assert "name" in result[0]
        assert "category" in result[0]
