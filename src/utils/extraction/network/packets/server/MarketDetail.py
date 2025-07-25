import struct
from typing import List, Tuple
from utils.data.market_values import ItemMetaData, MarketValues
from utils.extraction.network.packets.PacketBase import PacketBase
from time import time


class MarketDetail(PacketBase):
    def __init__(self, packet: bytes):
        super().__init__(packet, from_client=False)
        
        self.id: int = None
        self.tier: int = -1
        self.details: List[str] = None
        self.buy_history: List[HistoryPacketValue] = []
        self.sell_history: List[HistoryPacketValue] = []
        self.buy_offers: List[OfferPacketValue] = []
        self.sell_offers: List[OfferPacketValue] = []
        
        self._read_packet()

    def _read_packet(self):
        """Reads a market packet, and saves the result to self.result.

        Args:
            has_tier (bool, optional): Whether the packet has an item tier. Defaults to False.
        """
        self._read_header()
        self._read_details()
        self._read_statistics()
        self._read_offers()

    def _read_header(self):
        """Reads the header of a market packet.

        Args:
            has_tier (bool, optional): Whether the packet has an item tier. Defaults to False.
        """
        self.id = self._read_short()

        meta_data = ItemMetaData(id=self.id)
        meta_data.load_from_proto()
        self.tier = meta_data.tier

        if self.tier > -1:
            self.tier = self._read_byte()

    def _read_details(self):
        """Reads the details of a market packet. I.e. it's description, etc.
        """
        self.details = []
        
        # Go through each category. The amount can change every update.
        for _ in range(26):
            self.details.append(self._read_prefixed_string())

    def _read_statistics(self):
        """Reads the statistics of a market packet. I.e. it's daily sell/buy history.
        """
        def read_history(length: int) -> List[HistoryPacketValue]:
            history = []

            for i in range(length):
                amount_traded = self._read_int()
                total_gold = self._read_long()
                max_price = self._read_long()

                # Min_price is set to FFFFFFFFFFFFFFFF in packet if there were no trades.
                min_price = self._read_long()
                if amount_traded == 0:
                    min_price = 0

                history_value = HistoryPacketValue(amount_traded, total_gold, max_price, min_price)
                history.append(history_value)

            return history

        # History goes from recent to old.
        buy_history_length = self._read_byte()
        self.buy_history.extend(read_history(buy_history_length))

        sell_history_length = self._read_byte()
        self.sell_history.extend(read_history(sell_history_length))

    def _read_offers(self):
        """Reads the offers of a market packet. I.e. it's buy/sell offers.

        Args:
            has_tier (bool, optional): Whether the packet has an item tier. Defaults to False.

        Raises:
            Exception: If the packet type is not 0xF9.
        """
        # Search for the continuation packet.
        while True:
            packet_type = self._read_byte()

            if packet_type == 0xF9:
                unknown = self._read_byte()
                item_id = self._read_short()

                if item_id == self.id:
                    break

        if self.tier > -1:
            self.tier = self._read_byte()

        def read_offers(amount: int) -> List[OfferPacketValue]:
            offers = []

            for i in range(amount):
                offer_timestamp = self._read_int()
                offer_counter = self._read_short()
                offer_amount = self._read_short()
                offer_price = self._read_long()
                offer_name = self._read_prefixed_string()

                offer_value = OfferPacketValue(offer_timestamp, offer_counter, offer_amount, offer_price, offer_name)
                offers.append(offer_value)

            return offers

        buy_offer_amount = self._read_int()
        self.buy_offers.extend(read_offers(buy_offer_amount))

        # sort buy offers by price, descending.
        self.buy_offers.sort(key=lambda x: x.price, reverse=True)

        sell_offer_amount = self._read_int()
        self.sell_offers.extend(read_offers(sell_offer_amount))
        
        # Sort sell offers by price, ascending.
        self.sell_offers.sort(key=lambda x: x.price)


class HistoryPacketValue:
    def __init__(self, traded: int, total_gold: int, max_price: int, min_price: int):
        self.traded = traded
        self.total_gold = total_gold
        self.max_price = max_price
        self.min_price = min_price
        self.average_price = total_gold / traded if traded > 0 else 0


class OfferPacketValue:
    def __init__(self, timestamp: int, counter: int, amount: int, price: int, name: str):
        self.timestamp = timestamp
        self.counter = counter
        self.amount = amount
        self.price = price
        self.name = name


def packet_to_marketvalues(packet: MarketDetail) -> Tuple[MarketValues, List[MarketValues]]:
    """Converts the packet to a MarketValues object to reduce required storage.

    Returns:
        MarketValues: The MarketValues object.
    """
    buy_offer = packet.buy_offers[0].price if len(packet.buy_offers) > 0 else 0
    sell_offer = packet.sell_offers[0].price if len(packet.sell_offers) > 0 else 0

    active_sell_history = [x for x in packet.sell_history if x.traded > 0]
    active_buy_history = [x for x in packet.buy_history if x.traded > 0]

    month_buy_offer = int(sum([x.average_price for x in active_buy_history]) / len(active_buy_history) if len(active_buy_history) > 0 else 0)
    month_sell_offer = int(sum([x.average_price for x in active_sell_history]) / len(active_sell_history) if len(active_sell_history) > 0 else 0)
    month_highest_buy_offer = max([x.max_price for x in packet.buy_history]) if len(packet.buy_history) > 0 else 0
    traded_min_sell_offers = [x.min_price for x in packet.sell_history if x.min_price > 0]
    month_lowest_sell_offer = min(traded_min_sell_offers if traded_min_sell_offers else [0]) if len(packet.sell_history) > 0 else 0
    month_highest_sell_offer = max([x.max_price for x in packet.sell_history]) if len(packet.sell_history) > 0 else 0
    traded_min_buy_offers = [x.min_price for x in packet.buy_history if x.min_price > 0]
    month_lowest_buy_offer = min(traded_min_buy_offers if traded_min_buy_offers else [0]) if len(packet.buy_history) > 0 else 0
    month_bought = sum([x.traded for x in packet.buy_history]) if len(packet.buy_history) > 0 else 0
    month_sold = sum([x.traded for x in packet.sell_history]) if len(packet.sell_history) > 0 else 0

    day_buy_offer = int(packet.buy_history[0].average_price if len(packet.buy_history) > 0 else 0)
    day_sell_offer = int(packet.sell_history[0].average_price if len(packet.sell_history) > 0 else 0)
    day_highest_buy_offer = packet.buy_history[0].max_price if len(packet.buy_history) > 0 else 0
    day_lowest_sell_offer = packet.sell_history[0].min_price if len(packet.sell_history) > 0 else 0
    day_highest_sell_offer = packet.sell_history[0].max_price if len(packet.sell_history) > 0 else 0
    day_lowest_buy_offer = packet.buy_history[0].min_price if len(packet.buy_history) > 0 else 0
    day_bought = packet.buy_history[0].traded if len(packet.buy_history) > 0 else 0
    day_sold = packet.sell_history[0].traded if len(packet.sell_history) > 0 else 0

    # Calculate NPC profit.
    meta_data = ItemMetaData(id=packet.id)
    meta_data.load_from_proto()
    weight = float(packet.details[14].split(" ")[0]) if packet.details[14] in packet.details[14] else 0
    gold_sell_data = [sell_data for sell_data in meta_data.npc_sell if sell_data.is_gold()]
    gold_buy_data = [buy_data for buy_data in meta_data.npc_buy if buy_data.is_gold()]
    sorted_sell_data = sorted(gold_sell_data, key=lambda x: x.price)
    sorted_buy_data = sorted(gold_buy_data, key=lambda x: x.price, reverse=True)

    npc_trade_steps = [[0],[0]]
    npc_trade_steps_info = ""

    # Buy from players, sell to NPC.
    total_immediate_profit = 0
    if sorted_buy_data and sorted_buy_data[0].price > 0:
        for player_sell_offer in packet.sell_offers:
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
        for player_buy_offer in packet.buy_offers:
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

    buy_offers = len(packet.buy_offers)
    sell_offers = len(packet.sell_offers)

    # Active offers are offers within the past 24 hours.
    active_sell_offers = len([x for x in packet.sell_offers if time() - x.timestamp < 86400])
    active_buy_offers = len([x for x in packet.buy_offers if time() - x.timestamp < 86400])

    # Create market values for all of the previous days as well.
    historical_values = []
    for i, history in enumerate(zip(packet.buy_history, packet.sell_history)):
        if i == 0:
            continue

        timestamp = time() - (i * 86400)
        historical_values.append(MarketValues(id=packet.id, time=timestamp, 
                                                day_average_buy=int(history[0].average_price), day_average_sell=int(history[1].average_price),
                                                day_sold=history[1].traded, day_bought=history[0].traded, 
                                                day_highest_sell=history[1].max_price, day_lowest_sell=history[1].min_price,
                                                day_highest_buy=history[0].max_price, day_lowest_buy=history[0].min_price))

    return MarketValues(id=packet.id, time=time(), buy_offer=buy_offer, sell_offer=sell_offer, month_average_sell=month_sell_offer, month_average_buy=month_buy_offer, month_sold=month_sold, month_bought=month_bought, active_traders=min(active_buy_offers, active_sell_offers), month_highest_sell=month_highest_sell_offer, month_lowest_buy=month_lowest_buy_offer, month_lowest_sell=month_lowest_sell_offer, month_highest_buy=month_highest_buy_offer, buy_offers=buy_offers, sell_offers=sell_offers, day_average_sell=day_sell_offer, day_average_buy=day_buy_offer, day_sold=day_sold, day_bought=day_bought, day_highest_sell=day_highest_sell_offer, day_lowest_sell=day_lowest_sell_offer, day_highest_buy=day_highest_buy_offer, day_lowest_buy=day_lowest_buy_offer, total_immediate_profit=total_immediate_profit, total_immediate_profit_info=npc_trade_steps_info), historical_values
