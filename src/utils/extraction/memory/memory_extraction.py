from utils.client import Client
from utils.market_values import MarketValues
from utils.extraction.ocr.ocr_extraction import OCRExtractor
from utils.extraction.memory.market_memory_reader import MarketMemoryReader
from utils.wiki import Wiki
from utils.extraction.extractor import Extractor
import time
from typing import *
import pyautogui
from tqdm import tqdm
import random
import traceback
from utils.human_movement import wait_like_human, repeat_like_human
import os


class MemoryExtractor(Extractor):
    def __init__(self, client: Client):
        super().__init__(client)
        self.ocr_extractor = OCRExtractor(client)
        self.market_reader: MarketMemoryReader = None

        # if file exists.
        if os.path.exists("items.csv"):
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

        # Load item ids from wiki, or from items.csv if wiki is down.
        try: 
            self.wiki_id_to_name, self.wiki_name_to_id = Wiki().get_item_ids()

            # Merge the two dictionaries.
            self.id_to_name = {**self.id_to_name, **self.wiki_id_to_name}
            self.name_to_id = {**self.name_to_id, **self.wiki_name_to_id}

            # Save the item ids to items.csv.
            with open("items.csv", "w+") as f:
                for key, value in self.name_to_id.items():
                    f.write(f"{key},{value}\n")
        except Exception as e:
            self.client._add_to_log(f"Failed to get item ids from wiki. {e}")
    
    def setup(self):
        self.client.start_game()
        self.client.login_to_game()
        self.market_reader = MarketMemoryReader(self.client.tibia_process_id)
        
        if not self.client.open_market():
            self.client.exit_tibia()
            raise Exception("Failed to open market.")

    def _find_memory_addresses(self):
        """Walks through a few highly sold items to find necessary memory addresses.
        """
        pyautogui.PAUSE = 0.1
        self.client._add_to_log("Finding relevant memory addresses with OCR.")
        iterations = 0

        items = [("tibia coins", 22118), ("time ring", 3053), ("stealth ring", 3049), ("rope belt", 11492), ("stone skin amulet", 3081), ("collar of red plasma", 23544),
                 ("gold token", 22721), ("silver token", 22516), ("silencer claws", 20200), ("bloody pincers", 9633), ("elvish talisman", 9635), ("broken shamanic staff", 11452)]

        # Repeat until all memory addresses have been found.
        while not self.market_reader.has_finished_filtering:
            # Shuffle the items to avoid running into a deadlock with OCR.
            random.shuffle(items)

            for item, id in items:
                if self.market_reader.has_finished_filtering:
                    break
                
                # Find the current items values, and search for them in memory.
                values = self.ocr_extractor.search_item(item, id)
                self.market_reader.find_current_memory(values.buy_offer, values.sell_offer, values.highest_buy, values.highest_sell, values.id)
                
                self.client._add_to_log(len(self.market_reader.sell_offer_reader.addresses))
                self.client._add_to_log(len(self.market_reader.buy_offer_reader.addresses))
                self.client._add_to_log(len(self.market_reader.sell_details_reader.addresses))
                self.client._add_to_log(len(self.market_reader.buy_details_reader.addresses))
                self.client._add_to_log(len(self.market_reader.item_id_reader.addresses))
            
            iterations += 1
            if iterations > 5:
                self.market_reader.reset()
                raise Exception("Failed to find memory addresses after 5 iterations. Aborted.")
                
        # Fill memory with timestamps to know if an offer in memory still belongs to the current item.
        self.ocr_extractor.search_item("tibia coins")
        self.market_reader.get_current_market_values("tibia coins", scan_run=True)

    def extract_market_values(self) -> List[MarketValues]:
        items = []

        for category in tqdm(range(1, 25), desc="Category"):
            try:
                items.extend(self.crawl_market(category))
            except Exception as e:
                traceback.print_exc()
                
                print(f"Error while crawling market: {e}")
                break
        
        return items

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
        is_scanning = True

        while is_scanning:
            is_scanning = False

            # Reopen the market to avoid being kicked out.
            while True:
                try:
                    self.client.close_market()
                    self.client.wiggle()
                    self.client.open_market()

                    # Find memory addresses if they haven't been found yet.
                    if not self.market_reader.has_finished_filtering:
                        self._find_memory_addresses()
                    
                    break
                except Exception as e:
                    self.client._add_to_log(e)
                    memory_fail_count += 1
                    self.market_reader.reset()

                    if memory_fail_count >= 5:
                        raise e

            self.client._wait_until_find("images/Category.png", click=True, cache=False)

            # Go to the correct category.
            repeat_like_human(lambda: pyautogui.press("down"), category_index - 1, wait_time=0.1)

            # Tab to the item list. This number might have to be changed if the market is updated.
            repeat_like_human(lambda: pyautogui.press("tab"), 10, wait_time=0.1)
            
            # Go through the items quickly, except for the last one.
            # This is to make sure the item's value is fully loaded and we aren't rate limited.
            if starting_index > 1:
                repeat_like_human(lambda: pyautogui.press("down"), starting_index, wait_time=0.06, target_deviation=0.01)
                wait_like_human(8)

            last_item_id = -1
            while True:
                if self.market_reader.has_finished_filtering:
                    # If fetching results failed 10 times in a row, restart and skip this item.
                    if item_fail_count >= 5:
                        self.client._add_to_log("Failed 5 times, skipping item...")
                        starting_index += 1
                        item_fail_count = 0
                        pyautogui.press("down")
                        wait_like_human(0.5)
                    
                    # If the last result failed, reload the item.
                    if item_fail_count > 0:
                        pyautogui.press("up")
                        wait_like_human(0.5)

                    # Go to next item. Wait a bit to make sure we aren't rate limited.
                    pyautogui.press("down")
                    wait_like_human(0.5)

                    pyautogui.PAUSE = 0.01

                    try:
                        values, was_duplicate = self.market_reader.get_current_market_values("Unknown")
                        id = values.id
                    except Exception as e:
                        self.client._add_to_log(f"category: {category_index}, index: {starting_index}, Error: {e}")
                        item_fail_count += 1
                        continue

                    # If the id is the same as the last one, we have reached the end of the category.
                    if id == last_item_id:
                        self.client._add_to_log(f"Probably reached end of {category_index=}: {values.name=} {values.id=}")
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
                        self.client._add_to_log("Unknown item id: " + str(id) + ", category: " + str(category_index) + ", index: " + str(starting_index))
                    else:
                        values.name = self.id_to_name[id]

                    self.client._add_to_log(values)

                    if values.name != "Unknown":
                        results.append(values)

                    last_item_id = id

                    # Wiggle every once in a while to avoid being kicked out.
                    if time.time() > self.client.kick_time:
                        is_scanning = True
                        break
                else:
                    is_scanning = True
                    break

        return results