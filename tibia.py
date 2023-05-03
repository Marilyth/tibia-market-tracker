import pyautogui
import subprocess
import time
from typing import *
import screenshot
import requests
from datetime import datetime, timedelta
import re
from memory_reader import MemoryReader
import ctypes
import os


class EventData:
    def __init__(self, date: datetime, events: List[str]):
        self.date = date
        self.events = events

    def __str__(self) -> str:
        return f"{self.date.strftime('%Y.%m.%d')},{','.join(self.events)}"


class MarketValues:
    def __init__(self, name: str, time: float, sell_offer: int, buy_offer: int, month_sell_offer: int, month_buy_offer: int, sold: int, bought: int, highest_sell: int, lowest_buy: int, approx_offers: int):
        self.buy_offer: int = max(buy_offer, lowest_buy)
        self.sell_offer: int = max(min(sell_offer, highest_sell), self.buy_offer) if sold > 0 else sell_offer
        self.month_sell_offer: int = month_sell_offer
        self.month_buy_offer: int = month_buy_offer
        self.sold: int = sold
        self.bought: int = bought
        self.time: float = time

        self.profit: int = self.sell_offer - self.buy_offer
        # Subtract 2% of the offer values, or a maximum of 250000gp, from the profit due to market fees.
        self.profit -= (min(int(self.buy_offer * 0.02), 250000) + min(int(self.sell_offer * 0.02), 250000))
        self.rel_profit: float = round(self.profit / self.buy_offer, 2) if self.buy_offer > 0 else 0
        self.potential_profit: int = self.profit * min(sold, bought)
        self.active_traders: int = approx_offers
        self.name = name

    def __str__(self) -> str:
        return f"{self.name.lower()},{self.sell_offer},{self.buy_offer},{self.month_sell_offer},{self.month_buy_offer},{self.sold},{self.bought},{self.profit},{self.rel_profit},{self.potential_profit},{self.active_traders}"

    def history_string(self) -> str:
        """Returns the relevant historic values of the object as a string, separated by commas.
        This includes the sell offer, buy offer, sold, bought and approx offers values, followed by the time of the data.

        Returns:
            str: A string containing all the values of the object, separated by commas.
        """
        return f"{self.sell_offer},{self.buy_offer},{self.sold},{self.bought},{self.active_traders},{self.time}"

class Wiki:
    def __init__(self):
        pass

    def get_all_marketable_items(self) -> List[str]:
        """
        Fetches all marketable item names from the tibia fandom wiki.
        The documentation for fandom apis are available at https://www.mediawiki.org/wiki/API:Main_page.
        """
        items = []
        url = "https://tibia.fandom.com/api.php?action=query&list=categorymembers&cmtitle=Category%3AMarketable+Items&format=json&cmprop=title&cmlimit=500"
        cmcontinue = ""
        while True:
            response = requests.get(url + (f"&{cmcontinue=}" if cmcontinue else "")).json()
            items.extend([member["title"] for member in response["query"]["categorymembers"]])

            if "continue" in response:
                cmcontinue = response["continue"]["cmcontinue"]
            else:
                break

        return sorted(set([item.split(" (")[0] for item in items]))

    def get_events(self, after_date=None) -> List[EventData]:
        """
        Scrapes the event calendar from tibia.com and returns a list of EventData objects.
        """
        event_data: List[EventData] = []
        response = requests.get("https://www.tibia.com/news/?subtopic=eventcalendar").text
        events = response.split("\"eventscheduletable\"")[-1].split("</table>")[0].split("<td style")[1:]
        events = [event.split("</td>")[0] for event in events]

        today = datetime.today()
        month_modifier = -1
        today_reached = False
        for event in events:
            try:
                day = int(re.search(">([0-9]{1,2}) </span", event).group(1))

                # Event table can wrap to month before or next month, handle these cases.
                if day <= today.day and not today_reached:
                    month_modifier = 0
                if not today_reached and day == today.day:
                    today_reached = True
                elif today_reached and month_modifier == 0 and day < today.day:
                    month_modifier = 1

                month = today.month + month_modifier

                # Handle edge cases of changing year when covering multiple months.
                year = today.year
                if month == 12 and month_modifier == -1:
                    year -=1
                elif month == 1 and month_modifier == 1:
                    year += 1

                event_names = [event_name for event_name in [text.split(">")[-1] for text in event.split("</div>")[:-1]] if len(event_name) > 0]

                data_datetime = datetime(year, month, day)
                data = EventData(data_datetime, event_names)
                
                if after_date is None or data_datetime > after_date:
                    event_data.append(data)

            except Exception as e:
                print(f"Parsing event info failed for {event}: {e}")
        
        return event_data

    def get_item_ids(self) -> Tuple[Dict[int, str], Dict[str, int]]:
        """Fetches the items and their ids from https://tibia.fandom.com/wiki/Item_IDs

        Returns:
            Tuple[Dict[int, str], Dict[str, int]]: A tuple containing a dictionary mapping item ids to item names, and a dictionary mapping item names to item ids.
        """
        response = requests.get("https://tibia.fandom.com/api.php?action=parse&page=Item_IDs&format=json").json()
        response = response["parse"]["text"]["*"]
        
        # Get all the item names and ids from the table.
        items = re.findall(">([^<>]+)</a></td>\n<td>([0-9, ]+)\n</td>", response)

        # Convert the ids to ints and add them to the dictionary.
        id_to_item: Dict[int, str] = {}
        item_to_id: Dict[str, int] = {}
        for item in items:
            for id in item[1].replace(" ", ",").split(","):
                if len(id) > 0:
                    id_value = int(id.strip())

                    id_to_item[id_value] = item[0]
                    item_to_id[item[0]] =  id_value

        return id_to_item, item_to_id


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

    def find_current_memory(self, buy_offer: int, sell_offer: int, max_buy_offer: int, max_sell_offer: int, item_id: int):
        """Filters the readers with the current values. If all readers only have 1 value left, returns True.

        Args:
            buy_offer (int): The current 1st buy offer.
            sell_offer (int): The current 1st sell offer.
            avg_buy_offer (int): The current maximum buy offer.
            avg_sell_offer (int): The current maximum sell offer.
            item_id (int): The current item id.
        """
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
        average_bought = (total_bought_gold // amount_bought) if amount_bought > 0 else 0
        max_sold, min_sold, total_sold_gold, amount_sold = self.sell_details_reader.read_values()
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

        if not name.lower() == "golden helmet" and\
             sell_offer <= 0 or sell_offer > 8000000000 or \
             buy_offer <= 0 or buy_offer > 8000000000 or \
                (not was_duplicate and self.last_id == item_id) or \
            len(set(item_ids)) > 2 or\
            any(x < 100 for x in item_ids):
            #buy_timestamp > now_timestamp or sell_timestamp > now_timestamp or \
            #buy_timestamp < current_timestamp or sell_timestamp < current_timestamp:
            # Probably the address changed.
            self.sell_offer_reader.reset_filter()
            self.buy_offer_reader.reset_filter()
            self.sell_details_reader.reset_filter()
            self.buy_details_reader.reset_filter()
            self.item_id_reader.reset_filter()
            self.has_finished_filtering = False
            self.last_id = 0
            self.last_expression = ""
            raise Exception(f"The memory address might have changed: {item_id=},{buy_offer=},{sell_offer=},{buy_timestamp=},{sell_timestamp=}")

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

class Client:
    def __init__(self):
        '''
        Starts Tibia, updates it if necessary.
        '''
        # Start Tibia.
        pyautogui.PAUSE = 0.1
        self.tibia: subprocess.Popen = None
        self.position_cache = {}
        self.market_tab = "offers"
        self.market_reader: MarketMemoryReader = None

        # Load item ids from wiki, or from items.csv if wiki is down.
        try: 
            self.id_to_name, self.name_to_id = Wiki().get_item_ids()

            # Save the item ids to items.csv.
            with open("items.csv", "w+") as f:
                for key, value in self.name_to_id.items():
                    f.write(f"{key},{value}\n")
        except Exception as e:
            print(f"Failed to get item ids from wiki. {e}")
            
            # Load self.id_to_name and self.name_to_id from items.csv instead
            self.id_to_name = {}
            self.name_to_id = {}
            with open("items.csv", "r") as f:
                for line in f.readlines():
                    if len(line) >= 3:
                        values = line.split(",")
                        id = values[-1]
                        name = ",".join(values[:-1])

                        self.id_to_name[int(id)] = name
                        self.name_to_id[name] = int(id)

    def start_game(self, location: str):
        """Starts Tibia in the given location.

        Args:
            location (str): The location of the Tibia executable.
        """
        # If Tibia was closed before, remove the shared memory files. Otherwise Tibia will not start.
        for file in os.listdir("/tmp"):
            if file.startswith("qipc_sharedmemory"):
                os.remove(os.path.join("/tmp", file))

        self.tibia: subprocess.Popen = subprocess.Popen([location])
        time.sleep(5)
        self._update_tibia()

    def _update_tibia(self):
        """
        Checks if the update button exists, and if so, updates and starts Tibia.
        """
        self._wait_until_find("images/Update.png", click=True, timeout=10, cache=False)

        # Wait until update is done, and click play button.
        self._wait_until_find("images/PlayButton.png", click=True, cache=False)
        time.sleep(5)

    def login_to_game(self, email: str, password: str):
        """
        Logs into the provided account, and selects the provided character.
        """
        password_position = self._wait_until_find("images/PasswordField.png", click=True, cache=False)
        pyautogui.typewrite(password)

        print("Finding email field")
        email_position = self._wait_until_find("images/EmailField.png", click=True, cache=False)
        pyautogui.typewrite(email)

        pyautogui.press("enter")

        # Go ingame.
        character_position = self._wait_until_find("images/BotCharacter.png", cache=False)
        pyautogui.doubleClick(character_position)
        
        # Wait until ingame.
        self._wait_until_find("images/Ingame.png", cache=False)
        print("Ingame.")

    def exit_tibia(self):
        """
        Closes Tibia unsafely. Probably better to log out before.
        """
        pyautogui.hotkey("alt", "f4")
        self._wait_until_find("images/Exit.png", click=True, cache=False)

    def open_market(self):
        """
        Searches for an empty depot, and opens the market on it.
        """
        print("Opening market")

        if not self.market_reader:
            self.market_reader = MarketMemoryReader()
            
        def try_open_market() -> bool:
            x, y = self._wait_until_find("images/SuccessDepotTile.png", timeout=5, cache=False, exact=True)
            if x >= 0:
                if self._wait_until_find("images/Market.png", click=True, cache=False, timeout=5)[0] == -1:
                    print("Opening depot")
                    pyautogui.leftClick(636, 385)
                    self._wait_until_find("images/Market.png", click=True, cache=False, timeout=5)[0]
                    
                self._wait_until_find("images/Details.png", cache=False)

                print("Market open.")
                return True
            
            return False

        if pyautogui.locateCenterOnScreen("images/SuccessDepotTile.png") and try_open_market():
            return True

        for i in range(len(list(pyautogui.locateAllOnScreen("images/DepotTile.png")))):
            print(f"Trying depot {i}...")
            depot_position = list(pyautogui.locateAllOnScreen("images/DepotTile.png"))[i]
            pyautogui.leftClick(depot_position)
            if try_open_market():
                return True

        print("Opening market failed!")
        return False
        
    def _find_memory_addresses(self):
        """Walks through a few highly sold items to find necessary memory addresses.
        """
        pyautogui.PAUSE = 0.1
        print("Finding relevant memory addresses with OCR.")
        
        while not self.market_reader.has_finished_filtering:
            for item, id in [("tibia coins", 22118), ("time ring", 3053), ("stealth ring", 3049), ("rope belt", 11492), ("stone skin amulet", 3081), ("collar of red plasma", 23544)]:
                if self.market_reader.has_finished_filtering:
                    break
                
                values = self.search_item(item, id)
                print(len(self.market_reader.sell_offer_reader.addresses))
                print(len(self.market_reader.buy_offer_reader.addresses))
                print(len(self.market_reader.sell_details_reader.addresses))
                print(len(self.market_reader.buy_details_reader.addresses))
                print(len(self.market_reader.item_id_reader.addresses))
                print(values)

        # Fill memory with timestamps to know if an offer in memory still belongs to the current item.
        self.search_item("tibia coins")

    def crawl_market(self, category_index: int, starting_index: int = 0) -> List[MarketValues]:
        """
        Crawls the market for all items by iterating through the categories.

        Args:
            category_index: The index of the category to start at.
            starting_index: The index of the item to start at.
        Returns:
            A list of MarketValues objects.
        """
        results = []

        # Reopen the market to avoid being kicked out.
        self.close_market()
        self.wiggle()
        next_wiggle = time.time() + 60 * 13
        self.open_market()
        fail_count = 0

        # Find memory addresses if they haven't been found yet.
        if not self.market_reader.has_finished_filtering:
            self._find_memory_addresses()

        self._wait_until_find("images/Category.png", click=True, cache=False)

        # Go to the correct category.
        pyautogui.press("down", presses=category_index - 1)

        # Tab to the item list. This number might have to be changed if the market is updated.
        pyautogui.press("tab", presses=10)
        
        # Go through the items quickly, except for the last one.
        # This is to make sure the item's value is fully loaded and we aren't rate limited.
        if starting_index > 1:
            pyautogui.press("down", presses=starting_index)
            time.sleep(8)

        last_item_id = -1
        while True:
            if self.market_reader.has_finished_filtering:
                # If fetching results failed 10 times in a row, restart.
                if fail_count >= 10:
                    print("Restarting...")
                    return results + self.crawl_market(category_index, starting_index)
                
                # If the last result failed, reload the item.
                if fail_count > 0:
                    pyautogui.press("up")
                    time.sleep(0.5)

                # Go to next item. Wait a bit to make sure we aren't rate limited.
                pyautogui.press("down")
                time.sleep(0.5)

                pyautogui.PAUSE = 0.01

                try:
                    values, id, was_duplicate = self.market_reader.get_current_market_values("Unknown")
                except Exception as e:
                    print(f"category: {category_index}, index: {starting_index}, Error: {e}")
                    fail_count += 1
                    continue

                # If the id is the same as the last one, we have reached the end of the category.
                if id == last_item_id:
                    break
                
                # If we have failed 10 times in a row, we should probably restart.
                if was_duplicate and id != last_item_id and\
                    (values.month_sell_offer + values.month_buy_offer != 0) and\
                        id != 22118:
                    fail_count += 1
                    continue

                fail_count = 0
                starting_index += 1

                if id not in self.id_to_name:
                    print("Unknown item id: " + str(id) + ", category: " + str(category_index) + ", index: " + str(starting_index))
                else:
                    values.name = self.id_to_name[id]

                print(values)

                if values.name != "Unknown":
                    results.append(values)

                last_item_id = id

                # Wiggle every once in a while to avoid being kicked out.
                if time.time() > next_wiggle:
                    return results + self.crawl_market(category_index, starting_index)
            else:
                return results + self.crawl_market(category_index, starting_index)

        return results

    def search_item(self, name: str, id: Optional[int] = None) -> MarketValues:
        """
        Searches for the specified item in the market, and returns its current highest feasible buy and sell offers, and values for the month.
        """
        try:
            pyautogui.hotkey("ctrl", "z")
            pyautogui.typewrite(name)
            
            item_position = 1#self.item_position_dict[name.lower()] + 1
            
            for i in range(item_position):
                pyautogui.press("down")
                 # Give Tibia some time to load new values.
                time.sleep(0.45)
            
            def scan_details():
                if "images/Statistics.png" not in self.position_cache:
                    self.position_cache["images/Statistics.png"] = pyautogui.locateOnScreen("images/Statistics.png", grayscale=True, confidence=0.9)

                statistics = self.position_cache["images/Statistics.png"]
                interpreted_statistics = screenshot.read_image_text(screenshot.process_image(screenshot.take_screenshot(statistics.left, statistics.top, 300, 140), rescale_factor=3))\
                    .replace(",", "").replace(".", "").replace(" ", "").replace("k", "000").splitlines()
                interpreted_statistics = [stat for stat in interpreted_statistics if len(stat) > 0]

                return interpreted_statistics

            def scan_offers():
                if "images/Offers.png" not in self.position_cache:
                    self.position_cache["images/Offers.png"] = list(pyautogui.locateAllOnScreen("images/Offers.png", grayscale=True, confidence=0.9))
                offers = self.position_cache["images/Offers.png"]
                sell_offers = offers[0]
                buy_offers = offers[1]

                interpreted_buy_offer = screenshot.read_image_text(screenshot.process_image(screenshot.take_screenshot(buy_offers.left, buy_offers.top + buy_offers.height + 3, buy_offers.width, buy_offers.height), rescale_factor=3))\
                    .replace(",", "").replace(".", "").replace(" ", "").replace("k", "000").split("\n")[0]
                interpreted_sell_offer = screenshot.read_image_text(screenshot.process_image(screenshot.take_screenshot(sell_offers.left, sell_offers.top + sell_offers.height + 3, sell_offers.width, sell_offers.height), rescale_factor=3))\
                    .replace(",", "").replace(".", "").replace(" ", "").replace("k", "000").split("\n")[0]

                sell_offer = int(interpreted_sell_offer) if interpreted_sell_offer.isnumeric() else -1
                buy_offer = int(interpreted_buy_offer) if interpreted_buy_offer.isnumeric() else -1
                
                sellers = 0
                buyers = 0

                return buy_offer, sell_offer, max([sellers, buyers])

            if self.market_reader.has_finished_filtering:
                pyautogui.PAUSE = 0.01
                values, id, was_duplicate = self.market_reader.get_current_market_values(name, True)
                item_name = self.id_to_name[id] if id in self.id_to_name else name
                values.name = item_name
                if not values:
                    self.close_market()
                    self.wiggle()
                    self.open_market()
                    self._find_memory_addresses()
                    values = self.search_item(name)

                return values
            
            elif self.market_tab == "offers":
                buy_offer, sell_offer, approx_offers = scan_offers()
                self._wait_until_find("images/Details.png", click=True)
                interpreted_statistics = scan_details()
                self.market_tab = "details"
            else:
                interpreted_statistics = scan_details()
                self._wait_until_find("images/OffersButton.png", click=True)
                buy_offer, sell_offer, approx_offers = scan_offers()
                self.market_tab = "offers"

            values = MarketValues(name, time.time(), sell_offer, buy_offer, int(interpreted_statistics[6]), int(interpreted_statistics[2]), int(interpreted_statistics[4]), int(interpreted_statistics[0]), int(interpreted_statistics[5]), int(interpreted_statistics[3]), approx_offers)
            self.market_reader.find_current_memory(buy_offer, sell_offer, int(interpreted_statistics[1]), int(interpreted_statistics[5]), id)
            
            return values
        except pyautogui.FailSafeException as e:
            exit(1)
        except Exception as e:
            print(f"Market search failed for {name}: {e}")
            return MarketValues(name, time.time(), -1, -1, -1, -1, -1, -1, -1, -1, -1)

    def close_market(self):
        """
        Closes the market window using the escape hotkey.
        Also clears the cache to avoid clicking before the market opens.
        """
        print("Closing market...")
        pyautogui.PAUSE = 0.1
        pyautogui.press("escape")
        time.sleep(0.1)
        pyautogui.press("escape")
        time.sleep(0.1)
        self.clear_cache()

    def clear_cache(self):
        """
        Clears the position cache.
        Use this to avoid clicking on places that aren't yet loaded.
        """
        self.position_cache = {}

    def wiggle(self):
        """
        Wiggles the character to avoid being afk kicked.
        """
        print("Wiggling character...")
        pyautogui.hotkey("ctrl", "right")
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "left")
        time.sleep(0.5)
        self.market_tab = "offers"

    def _wait_until_find(self, image: str, timeout: int = 60, click: bool = False, cache: bool = True, exact: bool = False) -> Tuple[int, int]:
        start_time = time.time()

        while time.time() - start_time < timeout:
            if cache and image in self.position_cache:
                print(f"Found {image} in cache.")
                position = self.position_cache[image]
            else:
                print(f"Looking for {image}...")
                pyautogui.moveTo(20, 20)
                if not exact:
                    position = pyautogui.locateCenterOnScreen(image, grayscale=True, confidence=0.9)
                else:
                    position = pyautogui.locateCenterOnScreen(image)
                if position:
                    self.position_cache[image] = position

            if position:
                if click:
                    pyautogui.leftClick(position)
                    
                return position

            time.sleep(0.2)
        
        print(f"Finding {image} failed.")
        return (-1, -1)
    
