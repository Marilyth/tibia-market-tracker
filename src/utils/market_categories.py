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
    MarketCategory(15, "Soul Cores"),
    MarketCategory(16, "Tibia Coins"),
    MarketCategory(17, "Tools"),
    MarketCategory(18, "Valuables"),
    MarketCategory(19, "Weapons: Ammo"),
    MarketCategory(20, "Weapons: Axes"),
    MarketCategory(21, "Weapons: Clubs"),
    MarketCategory(22, "Weapons: Distance"),
    MarketCategory(23, "Weapons: Swords"),
    MarketCategory(24, "Weapons: Wands"),
    MarketCategory(25, "Weapons: All"),
]