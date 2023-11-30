from utils.market_values import MarketValues


def test_LoadValues_ReturnsExpected():
    # Assign
    fire_sword = MarketValues("fire sword", -1, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, -1, 3280)
    tibia_coins = MarketValues("tibia coins", -1, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, -1, 22118)
    
    # Act
    fire_sword.load_from_proto()
    fire_sword.load_pretty_name()
    tibia_coins.load_from_proto()
    tibia_coins.load_pretty_name()

    # Assert
    assert fire_sword.category == "Swords"
    assert fire_sword.is_upgradeable == True
    assert fire_sword.internal_name == "fire sword"
    assert fire_sword.name == "Fire Sword"
    assert not fire_sword.npc_sell
    assert any([npc.name == "Nah'bob" for npc in fire_sword.npc_buy])

    assert tibia_coins.category == "Tibia Coins"
    assert tibia_coins.is_upgradeable == False
    assert tibia_coins.internal_name == "Tibia Coins"
    assert tibia_coins.name == "Tibia Coins"
    assert not tibia_coins.npc_sell
    assert not tibia_coins.npc_buy