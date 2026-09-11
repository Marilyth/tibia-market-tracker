from utils.client import Client
import utils.extraction.ocr.ocr as screenshot
from utils.data.market_values import MarketValues
from utils.extraction.extractor import Extractor
from utils.human_movement import wait_like_human, repeat_like_human
from typing import *
import pyautogui
import time
import logging


logger = logging.getLogger(__name__)


class OCRExtractor(Extractor):
    def __init__(self, client: Client):
        super().__init__(client)
        self.client.market_tab = "offers"

    def setup(self):
        self.client.start_game()
        self.client.login_to_game()
        if not self.client.open_market():
            self.client.exit_tibia()
            raise Exception("Failed to open market.")

    def extract_market_values_async(self) -> List[MarketValues]:
        pass

    def search_item(self, name: str, id: Optional[int] = None) -> MarketValues:
        """
        Literally searches for the given item in the market, takes screenshots and uses OCR to read the values.
        """
        try:
            pyautogui.hotkey("ctrl", "z")
            pyautogui.typewrite(name, 0.1)

            item_position = 1
            repeat_like_human(lambda: pyautogui.press("down"), item_position, 0.5)

            def parse_value(value: str) -> int:
                if value.isnumeric():
                    return int(value)
                else:
                    return -1

            def scan_details():
                if "images/Statistics.png" not in self.client.position_cache:
                    self.client.position_cache["images/Statistics.png"] = pyautogui.locateOnScreen("images/Statistics.png", grayscale=True, confidence=0.9)

                statistics = self.client.position_cache["images/Statistics.png"]
                interpreted_statistics = screenshot.read_image_text(screenshot.process_image(screenshot.take_screenshot(statistics.left, statistics.top, 300, 140), rescale_factor=3))\
                    .replace(",", "").replace(".", "").replace(" ", "").replace("k", "000").splitlines()
                interpreted_statistics = [stat for stat in interpreted_statistics if len(stat) > 0]

                buy_amount = parse_value(interpreted_statistics[0])
                highest_buy_offer = parse_value(interpreted_statistics[1])
                average_buy_offer = parse_value(interpreted_statistics[2])
                lowest_buy_offer = parse_value(interpreted_statistics[3])

                sell_amount = parse_value(interpreted_statistics[4])
                highest_sell_offer = parse_value(interpreted_statistics[5])
                average_sell_offer = parse_value(interpreted_statistics[6])
                lowest_sell_offer = parse_value(interpreted_statistics[7])

                return buy_amount, highest_buy_offer, average_buy_offer, lowest_buy_offer, sell_amount, highest_sell_offer, average_sell_offer, lowest_sell_offer

            def scan_offers():
                if "images/Offers.png" not in self.client.position_cache:
                    self.client.position_cache["images/Offers.png"] = list(pyautogui.locateAllOnScreen("images/Offers.png", grayscale=True, confidence=0.9))
                offers = self.client.position_cache["images/Offers.png"]
                sell_offers = offers[0]
                buy_offers = offers[1]

                interpreted_buy_offer = screenshot.read_image_text(screenshot.process_image(screenshot.take_screenshot(buy_offers.left, buy_offers.top + buy_offers.height + 3, buy_offers.width, buy_offers.height), rescale_factor=3))\
                    .replace(",", "").replace(".", "").replace(" ", "").replace("k", "000").split("\n")[0]
                interpreted_sell_offer = screenshot.read_image_text(screenshot.process_image(screenshot.take_screenshot(sell_offers.left, sell_offers.top + sell_offers.height + 3, sell_offers.width, sell_offers.height), rescale_factor=3))\
                    .replace(",", "").replace(".", "").replace(" ", "").replace("k", "000").split("\n")[0]

                sell_offer = parse_value(interpreted_sell_offer)
                buy_offer = parse_value(interpreted_buy_offer)

                sellers = 0
                buyers = 0

                return buy_offer, sell_offer, max([sellers, buyers])

            if self.client.market_tab == "offers":
                buy_offer, sell_offer, approx_offers = scan_offers()
                self.client._wait_until_find("images/Details.png", timeout=5, click=True, throw_on_timeout=True)
                buy_amount, highest_buy_offer, average_buy_offer, lowest_buy_offer, sell_amount, highest_sell_offer, average_sell_offer, lowest_sell_offer = scan_details()
                self.client.market_tab = "details"
            else:
                buy_amount, highest_buy_offer, average_buy_offer, lowest_buy_offer, sell_amount, highest_sell_offer, average_sell_offer, lowest_sell_offer = scan_details()
                self.client._wait_until_find("images/OffersButton.png", timeout=5, click=True, throw_on_timeout=True)
                buy_offer, sell_offer, approx_offers = scan_offers()
                self.client.market_tab = "offers"

            values = MarketValues(time.time(), sell_offer, buy_offer, average_sell_offer, average_buy_offer, sell_amount, buy_amount, highest_sell_offer, lowest_buy_offer, approx_offers, -1, -1, lowest_sell_offer, highest_buy_offer, id if id else None)

            return values
        except pyautogui.FailSafeException as e:
            exit(1)
        except Exception as e:
            self.client._add_to_log(f"Market search failed for {name}: {e}")
            logger.exception(f"Market search failed for {name}: {e}")

            return MarketValues(time.time(), -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1)