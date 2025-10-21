from datetime import datetime
from pydantic import BaseModel


class WorldData(BaseModel):
    """A data class containing information about a Tibia server, and it's last update time.
    """
    """The name of the world."""
    name: str
    """The last update time."""
    last_update: datetime

class WorldActivity(BaseModel):
    """A data class containing information about a Tibia server's activity, and it's last update time.
    """
    """The name of the world."""
    name: str
    """The total amount of trades that happened in the past 28 days for this item."""
    total_trades: int
    """The number of offers for this item."""
    total_offers: int
