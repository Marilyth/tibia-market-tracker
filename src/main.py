from utils.tibia_wiki import Wiki
import os
import json
from datetime import datetime
from utils.mongo_manager import MongoManager
from tqdm import tqdm


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
            if events:
                # Write all events that are in the past up until today to the events file.
                # This is done so that spontaneous events that are added to the schedule are not missed.
                event_file.write("\n".join([event.__str__() for event in events]) + "\n")
    except Exception as e:
        print(f"Writing events failed: {e}")


def do_market_search(email: str, password: str, tibia_location: str, results_location: str, virtual_display: bool, virtual_display_visible: bool):
    write_events(results_location)

    def market_search():
        from utils.tibia import Client

        client = Client()
        client.start_game(tibia_location)
        client.login_to_game(email, password)
        scan_path = os.path.join(results_location, client.character_server)

        # Create the directory for the server if it does not exist.
        os.makedirs(scan_path, exist_ok=True)
        os.makedirs(os.path.join(scan_path, "histories"), exist_ok=True)

        with open(os.path.join(scan_path, "fullscan_ongoing.csv"), "w+") as f:
            f.write("Name,SellPrice,BuyPrice,AvgSellPrice,AvgBuyPrice,Sold,Bought,ActiveTraders\n")
            
            if not client.open_market():
                client.exit_tibia()
                return
            
            for category in tqdm(range(1, 25), desc="Category"):
                try:
                    for item in tqdm(client.crawl_market(category), desc="Updating item values"):
                        with open(os.path.join(scan_path, "histories", f"{item.name.lower()}.csv"), "a+") as h:
                            h.write(item.history_string() + "\n")
                        f.write(f"{item}\n")

                        mongo_manager.add_market_value(client.character_server, item)
                except Exception as e:
                    print(f"Error while crawling market: {e}")
                    break
            
            # Replace full scan with the ongoing one.
            os.replace(os.path.join(scan_path, "fullscan_ongoing.csv"), os.path.join(scan_path, "fullscan.csv"))
            
        client.exit_tibia()

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

    mongo_manager = MongoManager(config["mongodbConnectionString"])

    # Ensure that the results location exists.
    os.makedirs(config["resultsLocation"], exist_ok=True)

    do_market_search(config["email"], config["password"], config["tibiaLocation"], config["resultsLocation"], config["useVirtualDisplay"], config["showVirtualDisplay"])
