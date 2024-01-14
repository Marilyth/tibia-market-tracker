from utils.wiki import Wiki
import os
import json
from utils.json_helper import object_to_json
from utils.data.market_values import ItemMetaData
import sys
import traceback
from install_tibia import install_tibia, download_package
import requests

dry_run: bool = False
api_url: str = "https://api.tibiamarket.top:8001"
config: dict = None

def update_events():
    """
    Writes today's events to the database.
    """
    try:
        event = Wiki.get_event_data()

        if not dry_run:
            requests.post(f"{api_url}/add_event?secret={config['jwtSecret']}", json=object_to_json(event),
                          headers={"Content-Type": "application/json", "Content-Encoding": "gzip"})
    except Exception as e:
        traceback.print_exc()
        print(f"Writing events failed: {e}")

def update_metadata():
    """
    Updates the item metadata in the database.
    """
    try:
        meta_data = [ItemMetaData(id) for id in Wiki.get_marketable_proto_items()]
        for item in meta_data:
            item.load_wiki_name()
            item.load_from_proto()

        if not dry_run:
            requests.post(f"{api_url}/update_item_metadata?secret={config['jwtSecret']}", json=object_to_json(meta_data),
                          headers={"Content-Type": "application/json", "Content-Encoding": "gzip"})
    except Exception as e:
        traceback.print_exc()
        print(f"Writing metadata failed: {e}")

def do_market_search(email: str, password: str, char_index: int, virtual_display: bool, virtual_display_visible: bool):
    def market_search():
        from utils.extraction.memory.memory_extraction import MemoryExtractor
        from utils.extraction.network.network_extraction import NetworkExtractor
        from utils.extraction.extractor import Extractor
        from utils.client import Client

        client = Client("./Tibia/Tibia", email, password, char_index)
        extractor: Extractor = NetworkExtractor(client)
        extractor.setup()

        market_values = extractor.extract_market_values()
        client.exit_tibia()

        print(f"Market values: {len(market_values)}")

        if not dry_run:
            print("Updating market values...")
            requests.post(f"{api_url}/add_market_values?secret={config['jwtSecret']}", json=object_to_json({"server": client.character_server, "data": market_values}), 
                          headers={"Content-Type": "application/json", "Content-Encoding": "gzip"})

            print("Updating meta data...")
            update_metadata()

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

    # Ensure that the results location exists.
    os.makedirs("./results", exist_ok=True)

    do_market_search(config["email"], config["password"], char_index, config["useVirtualDisplay"], config["showVirtualDisplay"])
