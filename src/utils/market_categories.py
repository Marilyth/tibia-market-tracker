class MarketCategory:
    """Market category information."""

    def __init__(self, index: int, name: str):
        """Constructor for market category.

        Args:
            index (int): The index of the market category.
            name (str): The name of the market category.
        """
        self.name = name
        self.index = index

market_categories = [
    MarketCategory(0, "Armors"),
    MarketCategory(1, "Amulets"),
    MarketCategory(2, "Boots"),
    MarketCategory(3, "Containers"),
    MarketCategory(4, "Creature Products"),
    MarketCategory(5, "Decoration"),
    MarketCategory(6, "Food"),
    MarketCategory(7, "Helmets and Hats"),
    MarketCategory(8, "Legs"),
    MarketCategory(9, "Others"),
    MarketCategory(10, "Potions"),
    MarketCategory(11, "Quivers"),
    MarketCategory(12, "Rings"),
    MarketCategory(13, "Runes"),
    MarketCategory(14, "Shields"),
    MarketCategory(15, "Tibia Coins"),
    MarketCategory(16, "Tools"),
    MarketCategory(17, "Valuables"),
    MarketCategory(18, "Weapons: Ammo"),
    MarketCategory(19, "Weapons: Axes"),
    MarketCategory(20, "Weapons: Clubs"),
    MarketCategory(21, "Weapons: Distance"),
    MarketCategory(22, "Weapons: Swords"),
    MarketCategory(23, "Weapons: Wands"),
    MarketCategory(24, "Weapons: All"),
]