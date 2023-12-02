from utils.data.market_values import MarketValues, ItemMetaData


def test_LoadValues_ReturnsExpected():
    # Assign
    fire_sword = ItemMetaData(3280)
    tibia_coins = ItemMetaData(22118)
    
    # Act
    fire_sword.load_from_proto()
    fire_sword.load_wiki_name()
    tibia_coins.load_from_proto()
    tibia_coins.load_wiki_name()

    # Assert
    assert fire_sword.category == "Swords"
    assert fire_sword.is_upgradeable == True
    assert fire_sword.name == "fire sword"
    assert not fire_sword.npc_sell
    assert any([npc.name == "Nah'bob" for npc in fire_sword.npc_buy])

    assert tibia_coins.category == "Tibia Coins"
    assert tibia_coins.is_upgradeable == False
    assert tibia_coins.name == "Tibia Coins"
    assert not tibia_coins.npc_sell
    assert not tibia_coins.npc_buy