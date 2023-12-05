from utils.wiki import Wiki
import os
import json
from datetime import datetime
from utils.mongo_manager import MongoManager
from tqdm import tqdm
import sys
import traceback
from install_tibia import install_tibia, download_package

dry_run: bool = False
mongo_manager: MongoManager = None

def update_events():
    """
    Writes today's events to the database.
    """
    try:
        event = Wiki.get_event_data()

        if not dry_run:
            mongo_manager.add_event(event)
    except Exception as e:
        traceback.print_exc()
        print(f"Writing events failed: {e}")


def do_market_search(email: str, password: str, char_index: int, virtual_display: bool, virtual_display_visible: bool):
    def market_search():
        from utils.extraction.memory.memory_extraction import MemoryExtractor
        from utils.extraction.extractor import Extractor
        from utils.client import Client

        client = Client("./Tibia/Tibia", email, password, char_index)
        extractor: Extractor = MemoryExtractor(client)
        extractor.setup()

        market_values = extractor.extract_market_values()
        client.exit_tibia()

        if not dry_run:
            print("Updating market values...")
            mongo_manager.add_market_values(client.character_server, market_values)

            print("Updating meta data...")
            mongo_manager.update_item_metadata()

            print("Updating events...")
            update_events()

    if virtual_display:
        from pyvirtualdisplay import Display
        with Display(visible=virtual_display_visible, size=(1600, 900)):
            import pyautogui
            import Xlib.display
            pyautogui._pyautogui_x11._display = Xlib.display.Display(os.environ['DISPLAY'])
            market_search()
    else:
        market_search()


if __name__ == "__main__":
    with open(os.path.join(os.path.dirname(__file__), "config", "config.json"), "r") as c:
        config = json.loads(c.read())

    download_package()

    char_index = 0

    # If character index is provided, use that instead of the default.
    if len(sys.argv) > 1:
        char_index = int(sys.argv[1])

    mongo_manager = MongoManager(config["mongodbConnectionString"])

    # Ensure that the results location exists.
    os.makedirs("./results", exist_ok=True)

    do_market_search(config["email"], config["password"], char_index, config["useVirtualDisplay"], config["showVirtualDisplay"])
