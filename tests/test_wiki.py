import pytest
from datetime import datetime
from utils.wiki import EventData, Wiki


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
    
    def test_GetMarketableProtoItems_ReturnsExpected(self):
        # Act
        items = self.wiki.get_marketable_proto_items()

        # Assert
        assert len(items) > 3600 and len(items) < 30000
        assert any([item.name == "fire sword" for item in items.values()])
        assert not any([item.name == "crystal bed" for item in items.values()])
        
    def test_GenerateGifForItem_WhenGivenValidItem_DoesntThrow(self):
        # Act
        self.wiki.generate_gif_for_item(22118)
        
    def test_GenerateGifForAllItems_WhenCalled_DoesntThrow(self):
        # Arrange.
        items = self.wiki.get_marketable_proto_items()
        
        # Act.
        for item in items.values():
            self.wiki.generate_gif_for_item(item.id)
    
    def test_GetEventData_ReturnsExpected(self):
        # Act
        event = self.wiki.get_event_data()
        today = datetime.today()

        # Assert
        assert event.date.year == today.year
        assert event.date.month == today.month
        assert event.date.day == today.day

    def test_GetItemIds_ReturnsExpected(self):
        # Act
        ids = self.wiki.get_item_ids()

        # Assert
        assert len(ids) > 3100