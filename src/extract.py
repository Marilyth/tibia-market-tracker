from utils.wiki import Wiki
import os
import json
from utils.json_helper import object_to_json, json_to_object
from utils.data.market_values import ItemMetaData
from utils.schedule import Schedule
import sys
import traceback
from install_tibia import install_tibia, download_package
import requests
import datetime
import psutil
import time

dry_run: bool = False
api_url: str = "https://api.tibiamarket.top"
config: dict = None

def is_tibia_running() -> bool:
    """
    Returns if Tibia is running.
    """
    for proc in psutil.process_iter():
        try:
            if proc.name() == "client":
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return False

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
        meta_data = [ItemMetaData(id=id) for id in Wiki.get_marketable_proto_items()]
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

        market_values, market_boards = extractor.extract_market_values()
        client.exit_tibia()

        print(f"Market values: {len(market_values)}")

        if not dry_run:
            # Get the last update time of the server. Add  as authorization header.
            world_data = requests.get(f"{api_url}/world_data?servers={client.character_server}", headers={"Authorization": f"Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ3ZWJzaXRlIiwiaWF0IjoxNzA2Mzc2MTM1LCJleHAiOjI0ODM5NzYxMzV9.MrRgQJyNb5rlNmdsD3oyzG3ZugVeeeF8uFNElfWUOyI"}).json()
            last_update = datetime.datetime.fromisoformat("1970-01-01T00:00:00")

            if world_data:
                last_update = datetime.datetime.fromisoformat(world_data[0]["last_update"])
                last_update = last_update.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)

            last_timestamp = last_update.timestamp()

            # Filter out market_values that are older than the last update time.
            market_values = [value for value in market_values if value.time > last_timestamp]

            print(f"Filtered market values: {len(market_values)}")
            
            print("Updating meta data...")
            update_metadata()

            print("Updating events...")
            update_events()
                
            print("Updating market values...")
            while market_values:
                batch = market_values[:4000]
                market_values = market_values[4000:]

                requests.post(f"{api_url}/add_market_values?secret={config['jwtSecret']}", json=object_to_json({"server": client.character_server, "data": batch}), 
                            headers={"Content-Type": "application/json", "Content-Encoding": "gzip"})
                
            print("Updating market boards...")
            while market_boards:
                batch = market_boards[:4000]
                market_boards = market_boards[4000:]

                requests.post(f"{api_url}/update_market_boards?secret={config['jwtSecret']}", json=object_to_json({"server": client.character_server, "data": batch}), 
                            headers={"Content-Type": "application/json", "Content-Encoding": "gzip"})

    while is_tibia_running():
        print("Tibia is running. Waiting for it to close.")
        time.sleep(60)

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
        api_url += f":{config['apiPort']}"
    
    username = None
    password = None
    slot = None

    if len(sys.argv) != 4:
        schedule: Schedule = None
        with open(os.path.join(os.path.dirname(__file__), "config", "schedule.json"), "r") as s:
            schedule = Schedule(json.loads(s.read()))

        # Get current hour of day.
        if len(sys.argv) == 2:
            hour = int(sys.argv[1])
        else:
            hour = datetime.datetime.now().hour

        # Pick the character for the current hour.
        character = schedule.pick_character(hour)
        if character is None:
            print(f"No character found for hour {hour}.")
            sys.exit(0)
        
        # Write updated schedule back to file.
        with open(os.path.join(os.path.dirname(__file__), "config", "schedule.json"), "w") as s:
            s.write(object_to_json(schedule.hours, indent=4))
        
        username = character["username"]
        password = character["password"]
        slot = character["slot"]
    else:
        username = sys.argv[1]
        password = sys.argv[2]
        slot = int(sys.argv[3])

    download_package()

    # Ensure that the results location exists.
    os.makedirs("./results", exist_ok=True)

    print(f"Using account {username} on slot {slot}.")
    do_market_search(username, password, slot, config["useVirtualDisplay"], config["showVirtualDisplay"])
