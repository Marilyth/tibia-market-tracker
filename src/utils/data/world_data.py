from dataclasses import dataclass
from typing import List
from datetime import datetime


@dataclass
class WorldDataResponse:
    """A data class containing information about each supported Tibia server, and it's last update time.
    """
    """The list of worlds."""
    worlds: List["WorldData"]


@dataclass
class WorldData:
    """A data class containing information about a Tibia server, and it's last update time.
    """
    """The name of the world."""
    name: str
    """The last update time."""
    last_update: datetime