import pytest
from datetime import datetime
from utils.tibia_wiki import EventData, Wiki


class TestWiki:
    def setup(self):
        self.wiki = Wiki()

    def test_EventDataToString_WhenGivenSingleData_ReturnsExpected(self):
        # Assign
        date = datetime(2022, 1, 1)
        events = ["Event 1"]
        event_data = EventData(date, events)

        # Assert
        assert str(event_data) == "2022.01.01,Event 1"
        
    def test_EventDataToString_WhenGivenMultipleData_ReturnsExpected(self):
        # Assign
        date = datetime(2022, 1, 1)
        events = ["Event 1", "Event 2"]
        event_data = EventData(date, events)

        # Assert
        assert str(event_data) == "2022.01.01,Event 1,Event 2"

    def test_GetAllMarketableItems_WhenCalled_ReturnsAtLeast3100(self):
        # Act
        items = self.wiki.get_all_marketable_items()

        # Assert
        assert len(items) > 3100

    def test_GetEvents_WhenCalled_ReturnsAtLeast20Days(self):
        # Act
        events = self.wiki.get_events()

        # Assert
        assert len(events) > 20

    def test_GetEvents_WhenCalledWithAfterDate_ReturnsDaysAfterDate(self):
        # Act
        events = self.wiki.get_events()
        after_events = self.wiki.get_events(events[-2].date)

        # Assert
        assert len(after_events) == 1
