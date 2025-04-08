from datetime import datetime
from pydantic import BaseModel


class WorldData(BaseModel):
    """A data class containing information about a Tibia server, and it's last update time.
    """
    """The name of the world."""
    name: str
    """The last update time."""
    last_update: datetime
