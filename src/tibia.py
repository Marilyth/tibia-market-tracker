import pyautogui
import subprocess
import time
from typing import *
import screenshot
import os
import random
import traceback
from market_memory_reader import MarketMemoryReader
from market_values import MarketValues
from tibia_wiki import Wiki
import shutil


class Client:
    def __init__(self):
        '''
        Starts Tibia, updates it if necessary.
        '''
        # Start Tibia.
        pyautogui.PAUSE = 0.1
        self.tibia_settings_location = os.path.join(os.path.expanduser("~"), ".local", "share", "CipSoft GmbH", "Tibia", "packages", "Tibia", "conf")
        self.tibia: subprocess.Popen = None
        self.position_cache = {}
        self.market_tab = "offers"
        self.market_reader: MarketMemoryReader = None
        self.client_log = []

        # Load item ids from wiki, or from items.csv if wiki is down.
        try: 
            self.id_to_name, self.name_to_id = Wiki().get_item_ids()

            # Save the item ids to items.csv.
            with open("items.csv", "w+") as f:
                for key, value in self.name_to_id.items():
                    f.write(f"{key},{value}\n")
        except Exception as e:
            self._add_to_log(f"Failed to get item ids from wiki. {e}")
            
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
        Checks if the update or install button exists, and if so, installs or updates and starts Tibia.
        """
        if not self._wait_until_find("images/Install.png", click=True, timeout=5, cache=False):
            self._wait_until_find("images/Update.png", click=True, timeout=10, cache=False)

        # Create ~/.local/share/CipSoft Gmbh/Tibia/packages/config if it doesn't exist.
        os.makedirs(self.tibia_settings_location, exist_ok=True)

        # Copy ./config/clientoptions.json.
        shutil.copyfile("./config/clientoptions.json", os.path.join(self.tibia_settings_location, "clientoptions.json"))

        # Wait until update is done, and click play button.
        self._wait_until_find("images/PlayButton.png", click=True, cache=False, timeout=600)
        time.sleep(5)

    def login_to_game(self, email: str, password: str):
        """
        Logs into the provided account, and selects the provided character.
        """
        password_position = self._wait_until_find("images/PasswordField.png", click=True, cache=False)
        pyautogui.typewrite(password)

        self._add_to_log("Finding email field")
        email_position = self._wait_until_find("images/EmailField.png", click=True, cache=False)
        pyautogui.typewrite(email)

        pyautogui.press("enter")

        # Go ingame.
        character_position = self._wait_until_find("images/BotCharacter.png", cache=False)
        pyautogui.doubleClick(character_position)
        
        # Wait until ingame.
        self._wait_until_find("images/Ingame.png", cache=False)
        self._add_to_log("Ingame.")

    def exit_tibia(self):
        """
        Closes Tibia unsafely. Probably better to log out before.
        """
        pyautogui.hotkey("alt", "f4")
        self._wait_until_find("images/Exit.png", click=True, cache=False, timeout=5)

    def open_market(self):
        """
        Searches for an empty depot, and opens the market on it.
        """
        self._add_to_log("Opening market")

        if not self.market_reader:
            self.market_reader = MarketMemoryReader()
            
        def try_open_market() -> bool:
            x, y = self._wait_until_find("images/SuccessDepotTile.png", timeout=5, cache=False, exact=True)
            if x >= 0:
                # We are at a depot, check if already opened.
                if self._wait_until_find("images/Market.png", click=True, cache=False, timeout=5)[0] == -1:
                    self._add_to_log("Opening depot")

                    # Needs to be adjusted if the resolution is not 1600x900 fullscreen!
                    pyautogui.leftClick(645, 320)

                    # Tried to open depot, check if it worked.
                    if self._wait_until_find("images/Market.png", click=True, cache=False, timeout=5)[0] == -1:
                        return False
                
                # Depot and market are open, wait for market to load.
                self._wait_until_find("images/Details.png", cache=False, timeout=5)

                self._add_to_log("Market open.")
                return True
            
            return False

        if pyautogui.locateCenterOnScreen("images/SuccessDepotTile.png") and try_open_market():
            return True
        
        found_depots = len(list(pyautogui.locateAllOnScreen("images/DepotTile.png")))
        self._add_to_log(f"Found {found_depots} depots.")

        for i in range(len(list(pyautogui.locateAllOnScreen("images/DepotTile.png")))):
            print(f"Trying depot {i}...")
            depot_position = list(pyautogui.locateAllOnScreen("images/DepotTile.png"))[i]
            pyautogui.leftClick(depot_position)
            if try_open_market():
                return True

        self._add_to_log("Opening market failed!")
        return False
        
    def _find_memory_addresses(self):
        """Walks through a few highly sold items to find necessary memory addresses.
        """
        pyautogui.PAUSE = 0.1
        self._add_to_log("Finding relevant memory addresses with OCR.")
        iterations = 0

        items = [("tibia coins", 22118), ("time ring", 3053), ("stealth ring", 3049), ("rope belt", 11492), ("stone skin amulet", 3081), ("collar of red plasma", 23544),
                 ("gold token", 22721), ("silver token", 22516), ("silencer claws", 20200), ("bloody pincers", 9633), ("elvish talisman", 9635), ("broken shamanic staff", 11452)]

        while not self.market_reader.has_finished_filtering:
            random.shuffle(items)
            for item, id in items:
                if self.market_reader.has_finished_filtering:
                    break
                
                values = self.search_item(item, id)
                self._add_to_log(len(self.market_reader.sell_offer_reader.addresses))
                self._add_to_log(len(self.market_reader.buy_offer_reader.addresses))
                self._add_to_log(len(self.market_reader.sell_details_reader.addresses))
                self._add_to_log(len(self.market_reader.buy_details_reader.addresses))
                self._add_to_log(len(self.market_reader.item_id_reader.addresses))
            
            iterations += 1
            if iterations > 5:
                self.market_reader.reset()
                raise Exception("Failed to find memory addresses after 5 iterations. Aborted.")
                

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
        item_fail_count = 0
        memory_fail_count = 0
        loop_back = False

        while True:
            loop_back = False

            # Reopen the market to avoid being kicked out.
            while True:
                try:
                    self.close_market()
                    self.wiggle()
                    next_wiggle = time.time() + 60 * 13
                    self.open_market()
                    

                    # Find memory addresses if they haven't been found yet.
                    if not self.market_reader.has_finished_filtering:
                        self._find_memory_addresses()
                    
                    break
                except Exception as e:
                    self._add_to_log(e)
                    memory_fail_count += 1
                    self.market_reader.reset()

                    if memory_fail_count >= 5:
                        raise e

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
                    # If fetching results failed 10 times in a row, restart and skip this item.
                    if item_fail_count >= 5:
                        self._add_to_log("Failed 5 times, skipping item...")
                        starting_index += 1
                        item_fail_count = 0
                        pyautogui.press("down")
                        time.sleep(0.5)
                    
                    # If the last result failed, reload the item.
                    if item_fail_count > 0:
                        pyautogui.press("up")
                        time.sleep(0.5)

                    # Go to next item. Wait a bit to make sure we aren't rate limited.
                    pyautogui.press("down")
                    time.sleep(0.5)

                    pyautogui.PAUSE = 0.01

                    try:
                        values, id, was_duplicate = self.market_reader.get_current_market_values("Unknown")
                    except Exception as e:
                        self._add_to_log(f"category: {category_index}, index: {starting_index}, Error: {e}")
                        item_fail_count += 1
                        continue

                    # If the id is the same as the last one, we have reached the end of the category.
                    if id == last_item_id:
                        break
                    
                    # If we have failed 10 times in a row, we should probably restart.
                    if was_duplicate and id != last_item_id and\
                        (values.month_sell_offer + values.month_buy_offer != 0) and\
                            id != 22118:
                        item_fail_count += 1
                        continue

                    item_fail_count = 0
                    starting_index += 1

                    if id not in self.id_to_name:
                        self._add_to_log("Unknown item id: " + str(id) + ", category: " + str(category_index) + ", index: " + str(starting_index))
                    else:
                        values.name = self.id_to_name[id]

                    self._add_to_log(values)

                    if values.name != "Unknown":
                        results.append(values)

                    last_item_id = id

                    # Wiggle every once in a while to avoid being kicked out.
                    if time.time() > next_wiggle:
                        loop_back = True
                        break
                else:
                    loop_back = True
                    break
                
            if loop_back:
                continue

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
                self._wait_until_find("images/Details.png", timeout=5, click=True, throw_on_timeout=True)
                interpreted_statistics = scan_details()
                self.market_tab = "details"
            else:
                interpreted_statistics = scan_details()
                self._wait_until_find("images/OffersButton.png", timeout=5, click=True, throw_on_timeout=True)
                buy_offer, sell_offer, approx_offers = scan_offers()
                self.market_tab = "offers"

            values = MarketValues(name, time.time(), sell_offer, buy_offer, int(interpreted_statistics[6]), int(interpreted_statistics[2]), int(interpreted_statistics[4]), int(interpreted_statistics[0]), int(interpreted_statistics[5]), int(interpreted_statistics[3]), approx_offers)
            self.market_reader.find_current_memory(buy_offer, sell_offer, int(interpreted_statistics[1]), int(interpreted_statistics[5]), id)
            
            return values
        except pyautogui.FailSafeException as e:
            exit(1)
        except Exception as e:
            self._add_to_log(f"Market search failed for {name}: {e}")
            traceback.print_exc()

            return MarketValues(name, time.time(), -1, -1, -1, -1, -1, -1, -1, -1, -1)

    def close_market(self):
        """
        Closes the market window using the escape hotkey.
        Also clears the cache to avoid clicking before the market opens.
        """
        self._add_to_log("Closing market...")
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
        self._add_to_log("Wiggling character...")
        pyautogui.hotkey("ctrl", "right")
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "left")
        time.sleep(0.5)
        self.market_tab = "offers"

    def _wait_until_find(self, image: str, timeout: int = 60, click: bool = False, cache: bool = True, exact: bool = False, throw_on_timeout: bool = False) -> Tuple[int, int]:
        start_time = time.time()

        while time.time() - start_time < timeout:
            if cache and image in self.position_cache:
                self._add_to_log(f"Found {image} in cache.")
                position = self.position_cache[image]
            else:
                self._add_to_log(f"Looking for {image}...")
                pyautogui.moveTo(20, 20)
                if not exact:
                    position = pyautogui.locateCenterOnScreen(image, grayscale=True, confidence=0.9)
                else:
                    position = pyautogui.locateCenterOnScreen(image)
                if position:
                    self.position_cache[image] = position

            if position:
                self._add_to_log(f"Found {image} at {position}.")
                if click:
                    self._add_to_log(f"Clicking {image}...")
                    pyautogui.leftClick(position)
                    
                return position

            time.sleep(0.2)
        
        self._add_to_log(f"Finding {image} failed.")
        if throw_on_timeout:
            raise TimeoutError(f"Finding {image} failed.")
        
        return (-1, -1)
    
    def _add_to_log(self, message: str):
        self.client_log.append(message)
        print(message)
