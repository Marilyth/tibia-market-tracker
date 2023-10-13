import time
from typing import *
from datetime import datetime, timedelta
from utils.memory_reader import MemoryReader
import ctypes
from utils.market_values import MarketValues


class MarketMemoryReader:
    def __init__(self):
        self.buy_details_reader: MemoryReader = MemoryReader(p_name="client")
        self.sell_details_reader: MemoryReader = MemoryReader(process=self.buy_details_reader.process)
        self.buy_offer_reader: MemoryReader = MemoryReader(process=self.buy_details_reader.process)
        self.sell_offer_reader: MemoryReader = MemoryReader(process=self.buy_details_reader.process)
        self.item_id_reader: MemoryReader = MemoryReader(process=self.buy_details_reader.process)
        self.past_offers = 32
        
        # Values to determine if current memory belongs to the current item.
        self.last_sell_times = [(0, 0) for i in range(self.past_offers)]
        self.last_buy_times = [(0, 0) for i in range(self.past_offers)]
        self.last_expression = ""
        self.last_id = 0
        
        self.has_finished_filtering = False

    def reset(self):
        """Resets the memory reader to the initial state.
        """
        self.sell_offer_reader.reset_filter()
        self.buy_offer_reader.reset_filter()
        self.sell_details_reader.reset_filter()
        self.buy_details_reader.reset_filter()
        self.item_id_reader.reset_filter()
        self.has_finished_filtering = False
        self.last_id = 0
        self.last_expression = ""

    def find_current_memory(self, buy_offer: int, sell_offer: int, max_buy_offer: int, max_sell_offer: int, item_id: int):
        """Filters the readers with the current values. If all readers only have 1 value left, returns True.

        Args:
            buy_offer (int): The current 1st buy offer.
            sell_offer (int): The current 1st sell offer.
            avg_buy_offer (int): The current maximum buy offer.
            avg_sell_offer (int): The current maximum sell offer.
            item_id (int): The current item id.
        """
        print(f"Filtering memory... {buy_offer=}, {sell_offer=}, {max_buy_offer=}, {max_sell_offer=}, {item_id=}")

        if len(self.buy_offer_reader.addresses) != 1 and buy_offer >= 100:
            self.buy_offer_reader.filter_value(0, ctypes.c_long(buy_offer))
        if len(self.sell_offer_reader.addresses) != 1 and sell_offer >= 100:
            self.sell_offer_reader.filter_value(0, ctypes.c_long(sell_offer))
        if len(self.buy_details_reader.addresses) != 1 and max_buy_offer >= 100:
            self.buy_details_reader.filter_value(0, ctypes.c_long(max_buy_offer))
        if len(self.sell_details_reader.addresses) != 1 and max_sell_offer >= 100:
            self.sell_details_reader.filter_value(0, ctypes.c_long(max_sell_offer))
        if len(self.item_id_reader.addresses) != 1 and item_id >= 100:
            self.item_id_reader.filter_value(0, ctypes.c_uint16(item_id))

        if len(self.buy_offer_reader.addresses) == 1 and len(self.sell_offer_reader.addresses) == 1 and\
            len(self.buy_details_reader.addresses) == 1 and len(self.sell_details_reader.addresses) == 1:
            self._calculate_memory_locations()
            self.has_finished_filtering = True

    def _calculate_memory_locations(self):
        """Calculates the rest of the memory locations which depend on the already found ones.
        
        Memory addresses are predictable, but the bases need to be found first. Example:

        Base: 0x155064b0 buy transactions (same arithmetic for sell)
        +8 between transaction and total
        0x155064b8 total money this month (divide by transactions for average)
        +8 between total and max
        0x155064c0 max buy
        +8 between max and min
        0x155064c8 min buy

        It seems sell offers are NOT always on the same address!
        At some point they switch to someplace else.
        
        Base: 0x19d88868 buy offer 1 (same arithmetic for sell)
        -8 between offer and amount
        0x19d88860 amount 1
        -24 between offer and unix timestamp
        0x19d88850 unix timestamp 1
        +48 between offer 1 and 2
        0x19d88898 buy offer 2
        """
        buy_offer_base = self.buy_offer_reader.addresses[0]
        self.buy_offer_reader.addresses.append(buy_offer_base - 8) # Amount bought.
        self.buy_offer_reader.addresses.append(buy_offer_base - 24) # Timestamp.
        
        sell_offer_base = self.sell_offer_reader.addresses[0]
        self.sell_offer_reader.addresses.append(sell_offer_base - 8) # Amount sold.
        self.sell_offer_reader.addresses.append(sell_offer_base - 24) # Timestamp.
        
        # Add more than 1st offers to memory reader.
        for i in range(1, self.past_offers):
            ith_buy_offer = [x + 48 * i for x in self.buy_offer_reader.addresses[:3]]
            ith_sell_offer = [x + 48 * i for x in self.sell_offer_reader.addresses[:3]]
            self.buy_offer_reader.addresses.extend(ith_buy_offer)
            self.sell_offer_reader.addresses.extend(ith_sell_offer)
            
        buy_details_base = self.buy_details_reader.addresses[0] # Max buy offer.
        self.buy_details_reader.addresses.append(buy_details_base + 8) # Min buy offer.
        self.buy_details_reader.addresses.append(buy_details_base - 8) # Total money.
        self.buy_details_reader.addresses.append(buy_details_base - 16) # Total bought.
        
        sell_details_base = self.sell_details_reader.addresses[0] # Max sell offer.
        self.sell_details_reader.addresses.append(sell_details_base + 8) # Min sell offer.
        self.sell_details_reader.addresses.append(sell_details_base - 8) # Total money.
        self.sell_details_reader.addresses.append(sell_details_base - 16) # Total sold.
        
    def get_current_market_values(self, name: str, throw_on_duplicate: bool = False) -> MarketValues:
        """Reads the current market data from memory and creates a MarketValues object with it.

        Args:
            name (str): The name of the current item. Used to fill MarketValues name.

        Returns:
            MarketValues: The MarketValues for the current item.
        """
        max_bought, min_bought, total_bought_gold, amount_bought = self.buy_details_reader.read_values()
        amount_bought = amount_bought & 0xFFFFFFFF
        average_bought = (total_bought_gold // amount_bought) if amount_bought > 0 else 0

        max_sold, min_sold, total_sold_gold, amount_sold = self.sell_details_reader.read_values()
        amount_sold = amount_sold & 0xFFFFFFFF
        average_sold = (total_sold_gold // amount_sold) if amount_sold > 0 else 0
        item_ids = self.item_id_reader.read_values()[-3:]
        print(item_ids)

        # Get the most commonly occuring id in item_ids.
        item_id = max(set(item_ids), key=item_ids.count)

        was_duplicate = False
        
        current_expression = f"{max_bought},{min_bought},{total_bought_gold},{amount_bought},{average_bought}" +\
                             f"{max_sold},{min_sold},{total_sold_gold},{amount_sold},{average_sold}" +\
                             ",".join([str(x) for x in self.buy_offer_reader.read_values()]) +\
                             ",".join([str(x) for x in self.sell_offer_reader.read_values()])
        
        # Check if this memory is a duplicate of the last item. If so, probably nonexistent item.
        if current_expression == self.last_expression:
            if throw_on_duplicate:
                raise Exception("The current memory is a duplicate of the previous item.")
            else:
                print("The current memory is a duplicate of the previous item.")
                was_duplicate = True
        
        self.last_expression = current_expression
        
        buy_offer_values = self.buy_offer_reader.read_values()
        sell_offer_values = self.sell_offer_reader.read_values()
        
        now_timestamp = (datetime.now() + timedelta(30)).timestamp()
        current_timestamp = datetime.now().timestamp()
        
        buy_offer, buy_amount, buy_timestamp = buy_offer_values[:3]
        sell_offer, sell_amount, sell_timestamp = sell_offer_values[:3]

        # Timestamps are read as 64 bit, but only the last 32 bits are used.
        sell_timestamp = sell_timestamp & 0xFFFFFFFF
        buy_timestamp = buy_timestamp & 0xFFFFFFFF

        if not name.lower() == "golden helmet" and \
                sell_offer <= 0 or sell_offer > 8000000000 or \
                buy_offer <= 0 or buy_offer > 8000000000 or \
                amount_bought + amount_sold >= 500000 or \
                (not was_duplicate and self.last_id == item_id) or \
                len(set(item_ids)) > 2 or \
                any(x < 100 for x in item_ids):
            #buy_timestamp > now_timestamp or sell_timestamp > now_timestamp or \
            #buy_timestamp < current_timestamp or sell_timestamp < current_timestamp:
            # Probably the address changed.
            self.reset()
            raise Exception(f"The memory address might have changed: {item_id=},{buy_offer=},{sell_offer=},{amount_bought=},{amount_sold=},{buy_timestamp=},{sell_timestamp=},{item_ids=},{was_duplicate=},{self.last_id}")

        # If the item id is not the same as the last one, but the timestamp is the same as the last one, then the values aren't theirs.
        if buy_timestamp == self.last_buy_times[0][0] and item_id != self.last_buy_times[0][1]:
            buy_offer = buy_amount = buy_timestamp = -1
        if sell_timestamp == self.last_sell_times[0][0] and item_id != self.last_sell_times[0][1]:
            sell_offer = sell_amount = sell_timestamp = -1
            
        offers_within_24h = [0, 0]
        
        for i in range(self.past_offers):
            b_, b__, buy_timestamp = buy_offer_values[i * 3 : (i + 1) * 3]
            s_, s__, sell_timestamp = sell_offer_values[i * 3 : (i + 1) * 3]

            # timestamp is read as a long, but it is a 32 bit int. So we need to trim it.
            sell_timestamp = sell_timestamp & 0xFFFFFFFF
            buy_timestamp = buy_timestamp & 0xFFFFFFFF
            
            if buy_timestamp != self.last_buy_times[i][0] or item_id == self.last_buy_times[i][1]:
                self.last_buy_times[i] = (buy_timestamp, item_id)
                if now_timestamp > buy_timestamp and (now_timestamp - buy_timestamp) < 86400:
                    offers_within_24h[0] += 1

            if sell_timestamp != self.last_sell_times[i][0] or item_id == self.last_sell_times[i][1]:
                self.last_sell_times[i] = (sell_timestamp, item_id)
                if now_timestamp > sell_timestamp and (now_timestamp - sell_timestamp) < 86400:
                    offers_within_24h[1] += 1

        self.last_id = item_id

        print(f"Finished reading memory: {item_id=}, {buy_offer=}, {sell_offer=}, {average_bought=}, {average_sold=}, {amount_bought=}, {amount_sold=}, {max_bought=}, {min_sold=}, {offers_within_24h=}")
        return MarketValues(name, time.time(), sell_offer, buy_offer, average_sold, average_bought, amount_sold, amount_bought, max_sold, min_bought, max(offers_within_24h)), item_id, was_duplicate
