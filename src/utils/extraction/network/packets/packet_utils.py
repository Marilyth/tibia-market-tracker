from utils.extraction.network.packets.packet_base import PacketBase
from utils.extraction.network.packets.packet_names import ClientCommand, ServerCommand
from utils.extraction.network.packets.server.market_detail import MarketDetail
from utils.extraction.network.packets.client.market_browse import MarketBrowse as ClientMarketBrowse
from utils.extraction.network.packets.server.market_browse import MarketBrowse as ServerMarketBrowse
from utils.extraction.network.packets.server.ping import Ping as ServerPing
from utils.extraction.network.packets.client.ping import Ping as ClientPing
from utils.extraction.network.packets.server.ping_back import PingBack as ServerPingBack
from utils.extraction.network.packets.client.ping_back import PingBack as ClientPingBack
from utils.extraction.network.packets.client.connection_ping_back import ConnectionPingBack
from utils.data.market_values import ItemMetaData, MarketValues
from time import time
import logging


logger = logging.getLogger(__name__)


def read_packet(packet: bytes, from_client: bool) -> PacketBase:
    """Reads a packet and returns an instance of PacketBase which fits the packet data.

    Args:
        packet (bytes): The raw packet data.
        from_client (bool): Indicates if the packet is from the client.

    Returns:
        PacketBase: An instance of PacketBase with the parsed packet data.
    """
    packet = packet if packet else bytes([0])
    packets: list[PacketBase] = []

    while packet:
        try:
            if from_client:
                packets.append(_read_client_packet(packet))
            else:
                packets.append(_read_server_packet(packet))
        except Exception as e:
            logger.debug(f"Error reading packet: {e}. Treating as PacketBase.")
            packets.append(PacketBase(from_client).from_packet(packet))

        if type(packets[-1]) is PacketBase:
            # If the packet is a PacketBase, it means we have read the entire packet.
            break

        packet = packets[-1].get_excess()

    return packets

def _read_server_packet(packet: bytes) -> PacketBase:
    packet_code = packet[0]

    match packet_code:
        case ServerCommand.MarketDetail.value:
            return MarketDetail().from_packet(packet)
        case ServerCommand.MarketBrowse.value:
            return ServerMarketBrowse().from_packet(packet)
        case ServerCommand.Ping.value:
            return ServerPing().from_packet(packet)
        case ServerCommand.PingBack.value:
            return ServerPingBack().from_packet(packet)
        case _:
            return PacketBase(False).from_packet(packet)

def _read_client_packet(packet: bytes) -> PacketBase:
    packet_code = packet[0]

    match packet_code:
        case ClientCommand.MarketBrowse.value:
            return ClientMarketBrowse().from_packet(packet)
        case ClientCommand.Ping.value:
            return ClientPing().from_packet(packet)
        case ClientCommand.PingBack.value:
            return ClientPingBack().from_packet(packet)
        case ClientCommand.ConnectionPingBack.value:
            return ConnectionPingBack().from_packet(packet)
        case _:
            return PacketBase(True).from_packet(packet)

def packet_to_marketvalues(details: MarketDetail, offers: ServerMarketBrowse) -> tuple[MarketValues, list[MarketValues]]:
    """Converts the packet to a MarketValues object to reduce required storage.

    Returns:
        MarketValues: The MarketValues object.
    """
    buy_offer = offers.buy_offers[0].price if len(offers.buy_offers) > 0 else 0
    sell_offer = offers.sell_offers[0].price if len(offers.sell_offers) > 0 else 0

    active_sell_history = [x for x in details.sell_history if x.traded > 0]
    active_buy_history = [x for x in details.buy_history if x.traded > 0]

    month_buy_offer = int(sum([x.average_price for x in active_buy_history]) / len(active_buy_history) if len(active_buy_history) > 0 else 0)
    month_sell_offer = int(sum([x.average_price for x in active_sell_history]) / len(active_sell_history) if len(active_sell_history) > 0 else 0)
    month_highest_buy_offer = max([x.max_price for x in details.buy_history]) if len(details.buy_history) > 0 else 0
    traded_min_sell_offers = [x.min_price for x in details.sell_history if x.min_price > 0]
    month_lowest_sell_offer = min(traded_min_sell_offers if traded_min_sell_offers else [0]) if len(details.sell_history) > 0 else 0
    month_highest_sell_offer = max([x.max_price for x in details.sell_history]) if len(details.sell_history) > 0 else 0
    traded_min_buy_offers = [x.min_price for x in details.buy_history if x.min_price > 0]
    month_lowest_buy_offer = min(traded_min_buy_offers if traded_min_buy_offers else [0]) if len(details.buy_history) > 0 else 0
    month_bought = sum([x.traded for x in details.buy_history]) if len(details.buy_history) > 0 else 0
    month_sold = sum([x.traded for x in details.sell_history]) if len(details.sell_history) > 0 else 0

    day_buy_offer = int(details.buy_history[0].average_price if len(details.buy_history) > 0 else 0)
    day_sell_offer = int(details.sell_history[0].average_price if len(details.sell_history) > 0 else 0)
    day_highest_buy_offer = details.buy_history[0].max_price if len(details.buy_history) > 0 else 0
    day_lowest_sell_offer = details.sell_history[0].min_price if len(details.sell_history) > 0 else 0
    day_highest_sell_offer = details.sell_history[0].max_price if len(details.sell_history) > 0 else 0
    day_lowest_buy_offer = details.buy_history[0].min_price if len(details.buy_history) > 0 else 0
    day_bought = details.buy_history[0].traded if len(details.buy_history) > 0 else 0
    day_sold = details.sell_history[0].traded if len(details.sell_history) > 0 else 0

    # Calculate NPC profit.
    meta_data = ItemMetaData(id=details.id)
    meta_data.load_from_proto()
    weight = float(details.details[14].split(" ")[0]) if details.details[14] in details.details[14] else 0
    gold_sell_data = [sell_data for sell_data in meta_data.npc_sell if sell_data.is_gold()]
    gold_buy_data = [buy_data for buy_data in meta_data.npc_buy if buy_data.is_gold()]
    sorted_sell_data = sorted(gold_sell_data, key=lambda x: x.price)
    sorted_buy_data = sorted(gold_buy_data, key=lambda x: x.price, reverse=True)

    npc_trade_steps = [[0],[0]]
    npc_trade_steps_info = ""

    # Buy from players, sell to NPC.
    total_immediate_profit = 0
    if sorted_buy_data and sorted_buy_data[0].price > 0:
        for player_sell_offer in offers.sell_offers:
            if player_sell_offer.price >= sorted_buy_data[0].price:
                break

            total_immediate_profit += (sorted_buy_data[0].price - player_sell_offer.price) * player_sell_offer.amount
            npc_trade_steps[0][0] += player_sell_offer.amount
            npc_trade_steps[0].append(f"Buy {player_sell_offer.amount}x from {player_sell_offer.name} for {player_sell_offer.price}.")

    if npc_trade_steps[0][0] > 0:
        npc_trade_steps[0].append(f"Sell {npc_trade_steps[0][0]}x to NPC {sorted_buy_data[0].name} in {sorted_buy_data[0].location} for {sorted_buy_data[0].price}.")
        npc_trade_steps[0].append(f"Profit: {total_immediate_profit}.")
        npc_trade_steps[0].append(f"Total oz: {npc_trade_steps[0][0] * weight}.")

    # Buy from NPC, sell to players.
    if sorted_sell_data and sorted_sell_data[0].price > 0:
        for player_buy_offer in offers.buy_offers:
            if player_buy_offer.price <= sorted_sell_data[0].price:
                break

            total_immediate_profit += (player_buy_offer.price - sorted_sell_data[0].price) * player_buy_offer.amount
            npc_trade_steps[1][0] += player_buy_offer.amount
            npc_trade_steps[1].append(f"Sell {player_buy_offer.amount}x to {player_buy_offer.name} for {player_buy_offer.price}.")

    if npc_trade_steps[1][0] > 0:
        npc_trade_steps[1].insert(1, f"Buy {npc_trade_steps[1][0]}x from NPC {sorted_sell_data[0].name} in {sorted_sell_data[0].location} for {sorted_sell_data[0].price}.")
        npc_trade_steps[1].append(f"Profit: {total_immediate_profit}.")
        npc_trade_steps[1].append(f"Total oz: {npc_trade_steps[1][0] * weight}.")

    npc_trade_steps_info = "\n".join(npc_trade_steps[0][1:] + npc_trade_steps[1][1:])

    buy_offers = len(offers.buy_offers)
    sell_offers = len(offers.sell_offers)

    # Active offers are offers within the past 24 hours.
    active_sell_offers = len([x for x in offers.sell_offers if time() - x.timestamp < 86400])
    active_buy_offers = len([x for x in offers.buy_offers if time() - x.timestamp < 86400])

    # Create market values for all of the previous days as well.
    historical_values = []
    for i, history in enumerate(zip(details.buy_history, details.sell_history)):
        if i == 0:
            continue

        timestamp = time() - (i * 86400)
        historical_values.append(MarketValues(id=details.id, time=timestamp,
                                                day_average_buy=int(history[0].average_price), day_average_sell=int(history[1].average_price),
                                                day_sold=history[1].traded, day_bought=history[0].traded,
                                                day_highest_sell=history[1].max_price, day_lowest_sell=history[1].min_price,
                                                day_highest_buy=history[0].max_price, day_lowest_buy=history[0].min_price))

    return MarketValues(id=details.id, time=time(), buy_offer=buy_offer, sell_offer=sell_offer, month_average_sell=month_sell_offer, month_average_buy=month_buy_offer, month_sold=month_sold, month_bought=month_bought, active_traders=min(active_buy_offers, active_sell_offers), month_highest_sell=month_highest_sell_offer, month_lowest_buy=month_lowest_buy_offer, month_lowest_sell=month_lowest_sell_offer, month_highest_buy=month_highest_buy_offer, buy_offers=buy_offers, sell_offers=sell_offers, day_average_sell=day_sell_offer, day_average_buy=day_buy_offer, day_sold=day_sold, day_bought=day_bought, day_highest_sell=day_highest_sell_offer, day_lowest_sell=day_lowest_sell_offer, day_highest_buy=day_highest_buy_offer, day_lowest_buy=day_lowest_buy_offer, total_immediate_profit=total_immediate_profit, total_immediate_profit_info=npc_trade_steps_info), historical_values
