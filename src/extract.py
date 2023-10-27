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

def write_marketable_items():
    items = Wiki().get_all_marketable_items()
    with open("tracked_items.txt", "w") as f:
        for item in items:
            f.write(item + "\n")

def write_events(results_location: str):
    """
    Writes all currently known events into the events.csv in the results_location.
    """
    try:
        last_date = datetime.min

        if os.path.exists(os.path.join(results_location, "events.csv")):
            with open(os.path.join(results_location, "events.csv"), "r") as event_file:
                previous_events = [event for event in event_file.readlines() if event and not str.isspace(event)]
                if previous_events:
                    last_date = datetime.strptime(previous_events[-1].split(",")[0], "%Y.%m.%d")

        with open(os.path.join(results_location, "events.csv"), "a+") as event_file:
            events = [event for event in Wiki().get_events(last_date) if event.date <= datetime.today()]

            if dry_run:
                return

            if events:
                # Write all events that are in the past up until today to the events file.
                # This is done so that spontaneous events that are added to the schedule are not missed.
                event_file.write("\n".join([event.__str__() for event in events]) + "\n")

                for event in events:
                    mongo_manager.add_event(event)
    except Exception as e:
        traceback.print_exc()
        print(f"Writing events failed: {e}")


def do_market_search(email: str, password: str, virtual_display: bool, virtual_display_visible: bool):
    write_events("./results")

    def market_search():
        from utils.extraction.memory.memory_extraction import MemoryExtractor
        from utils.extraction.extractor import Extractor
        from utils.client import Client

        client = Client("./Tibia/Tibia", email, password)
        extractor: Extractor = MemoryExtractor(client)
        extractor.setup()

        market_values = extractor.extract_market_values()
        client.exit_tibia()

        # Create the directory for the server if it does not exist.
        for item in tqdm(market_values, desc="Updating item values"):
            print(item)

            if not dry_run:
                mongo_manager.add_market_value(client.character_server, item)

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

    # If email and password are passed as arguments, use those instead of the ones in the config.
    # This makes tracking many servers easier.
    if len(sys.argv) > 1:
        config["email"] = sys.argv[1]
    if len(sys.argv) > 2:
        config["password"] = sys.argv[2]

    mongo_manager = MongoManager(config["mongodbConnectionString"])

    # Ensure that the results location exists.
    os.makedirs("./results", exist_ok=True)

    do_market_search(config["email"], config["password"], config["useVirtualDisplay"], config["showVirtualDisplay"])
