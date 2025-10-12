import asyncio
import os
import time
import sys
import traceback
import datetime
import json
import requests
import psutil
from install_tibia import download_package, get_tibia_path
from utils.wiki import Wiki
from utils.json_helper import object_to_json
from utils.data.market_values import ItemMetaData
from utils.schedule import Character, Schedule
from utils.extraction.network.network_extractor import NetworkExtractor
from utils.extraction.extractor import Extractor
from utils.client import Client
from utils.extraction.network.proxy import stop_proxy

dry_run: bool = False
api_url: str = "https://api.tibiamarket.top"
config: dict = None
schedule: Schedule = None

def is_tibia_running(kill: bool = True) -> bool:
    """
    Returns if Tibia is running.

    :param kill: If True, kills the Tibia process if it was started over 90 minutes ago.
    """
    xephyr_processes = []
    tracker_processes = []

    for proc in psutil.process_iter():
        try:
            proc_call_string = " ".join(proc.cmdline())

            if "python" in proc_call_string and __file__ in proc_call_string:
                tracker_processes.append(proc)

            if "Xephyr" in proc_call_string:
                xephyr_processes.append(proc)

            if "Tibia" in proc_call_string:
                if kill:
                    process_runtime = time.time() - proc.create_time()
                    if process_runtime > 90 * 60:
                        proc.kill()

                        # Kill the tracker processes as well.
                        for tracker in tracker_processes:
                            tracker.kill()

                        for xephyr in xephyr_processes:
                            xephyr.kill()

                        return False

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

def upload_data(market_values, market_boards, server: str):
    print(f"Market values: {len(market_values)}")

    if dry_run:
        return

    # Get the last update time of the server.
    world_data = requests.get(f"{api_url}/world_data?servers={server}").json()
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

        requests.post(f"{api_url}/add_market_values?secret={config['jwtSecret']}", json=object_to_json({"server": server, "data": batch}),
                    headers={"Content-Type": "application/json", "Content-Encoding": "gzip"})

    print("Updating market boards...")
    while market_boards:
        batch = market_boards[:4000]
        market_boards = market_boards[4000:]

        requests.post(f"{api_url}/update_market_boards?secret={config['jwtSecret']}", json=object_to_json({"server": server, "data": batch}),
                    headers={"Content-Type": "application/json", "Content-Encoding": "gzip"})


async def do_market_search(character: Character, virtual_display: bool, virtual_display_visible: bool):
    async def market_search():
        client = Client(get_tibia_path(), character)

        extractor: Extractor = NetworkExtractor(client)
        await extractor.setup()

        # Update the schedule with the server and name of the character slot.
        write_schedule()

        market_values, market_boards = None, None

        try:
            market_values, market_boards = await extractor.extract_market_values_async()
        except Exception as e:
            print(f"Market extraction failed: {e}")
            extractor.sniffer.save_flows("failed_flows.mitm")
        finally:
            client.exit_tibia()
            stop_proxy()

        await asyncio.to_thread(upload_data, market_values, market_boards, character.server)

    while is_tibia_running():
        print("Tibia is running. Waiting for it to close.")
        time.sleep(60)

    if virtual_display:
        from pyvirtualdisplay import Display
        with Display(visible=virtual_display_visible, size=(1600, 900)):
            import pyautogui
            import Xlib.display
            pyautogui._pyautogui_x11._display = Xlib.display.Display(os.environ['DISPLAY'])

            await market_search()
    else:
        await market_search()


def read_schedule():
    global schedule

    with open(os.path.join(os.path.dirname(__file__), "config", "schedule.json"), "r") as s:
        schedule = Schedule(json.loads(s.read()))

        # Convert the character dictionaries to Character objects.
        for hour in schedule.hours:
            if schedule.hours[hour] is not None:
                schedule.hours[hour] = [Character(**character_dict) for character_dict in schedule.hours[hour]]


def write_schedule():
    # Write updated schedule back to file.
    with open(os.path.join(os.path.dirname(__file__), "config", "schedule.json"), "w") as s:
        s.write(object_to_json(schedule.hours, indent=4))


def reorder_schedule():
    """Reorders the schedule based on world activity.
    """
    read_schedule()
    buckets = 8
    slots = 24
    slots_per_bucket = slots // buckets

    world_activity = requests.get(f"{api_url}/item_activity?item_id=22516").json()
    characters = {character.server: character for hour in schedule.hours for character in (schedule.hours[hour] or [])}

    # Clear current schedule.
    for hour in schedule.hours:
        schedule.hours[hour] = []

    # Hierarchically fill the schedule.
    # Lower buckets have less capacity than higher buckets.
    current_slot = 0

    def insert_character(character: Character):
        nonlocal current_slot
        schedule.hours[str(current_slot)].append(character)

        slot_length = len(schedule.hours[str(current_slot)])
        slot_capacity = ((current_slot - (1 if current_slot > 10 else 0)) // slots_per_bucket) + 1

        print(f"{character.server} updates at {current_slot}AM German time, every {slot_capacity} days.")

        if slot_length >= slot_capacity:
            current_slot += 1

            # Skip slot 10 for server save.
            if current_slot == 10:
                current_slot = 11

    for world in world_activity:
        if world["name"] in characters:
            character = characters[world["name"]]
            insert_character(character)

    # This only fills known characters. Unknown will be placed by hand.

    write_schedule()


async def main():
    global api_url, config, dry_run, schedule

    with open(os.path.join(os.path.dirname(__file__), "config", "config.json"), "r") as c:
        config = json.loads(c.read())
        api_url += f":{config['apiPort']}"

    character = None

    if len(sys.argv) != 4:
        # Get current hour of day.
        if len(sys.argv) == 2:
            if sys.argv[1] == "reorder":
                reorder_schedule()
                sys.exit(0)

            hour = int(sys.argv[1])
        else:
            hour = datetime.datetime.now().hour

        read_schedule()

        # Pick the character for the current hour.
        character = schedule.pick_character(hour)
        if character is None:
            print(f"No character found for hour {hour}.")
            sys.exit(0)

        write_schedule()
    else:
        character = Character(
            username=sys.argv[1],
            password=sys.argv[2],
            slot=int(sys.argv[3])
        )

    download_package()

    # Ensure that the results location exists.
    os.makedirs("./results", exist_ok=True)

    print(f"Using account {character.username} on slot {character.slot}.")
    await do_market_search(character, config["useVirtualDisplay"], config["showVirtualDisplay"])


if __name__ == "__main__":
    asyncio.run(main())
