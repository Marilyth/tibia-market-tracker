import pytest
from utils.tibia import Client

client = None


class TestClient:
    # Run this method once before any test
    @classmethod
    def setup_class(cls):
        cls.client = Client()

    # Run this method once after all tests
    @classmethod
    def teardown_class(cls):
        cls.client.exit_tibia()

    def test_StartGame_WhenCalled_ReturnsTrue(self):
        # Act
        self.client.start_game("/home/may/Desktop/Tibia/Tibia")

        # Assert
        assert any([log.startswith("Found src/images/Update.png at") for log in client.client_log])
        assert any([log.startswith("Found src/images/PlayButton.png at") for log in client.client_log])