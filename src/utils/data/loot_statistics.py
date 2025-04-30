from datetime import datetime
from pydantic import BaseModel
from typing import List


class Monster(BaseModel):
    """A data class containing loot statistics for a monster.
    """

    id: int
    """The id of the monster."""

class Loot(BaseModel):
    """A data class containing loot statistics for a monster.
    """
    item_id: int
    """The id of the item."""

    amount_looted: int
    """The amount of times the item was found."""

class LootStatistics(BaseModel):
    """A data class containing loot statistics for a monster.
    """

    monster_id: int
    """The id of the monster."""

    item_id: int
    """The id of the item."""

    loot: List[Loot]
    """The loot of the monster."""

    kills: int
    """The amount of kills of the monster."""
