from datetime import datetime
from typing import Dict, List, Tuple
import requests
import re
import sys
import os
import json
from pydantic import BaseModel

# Add the proto directory to the path so that we can import from it.
sys.path.append(os.path.join(os.path.dirname(__file__), "data", "proto"))

from utils.data.proto import appearances_pb2


class EventData(BaseModel):
    """A data class containing information about the events of a given day.
    """
    date: datetime
    events: List[str]

    def __str__(self) -> str:
        return f"{self.date.strftime('%Y.%m.%d')},{','.join(self.events)}"


proto_items = {}
id_to_pretty_name = {}
pretty_name_to_id = {}

class Wiki:
    def __init__(self):
        pass

    @staticmethod
    def get_all_marketable_items() -> List[str]:
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

    @staticmethod
    def get_item_ids() -> Tuple[Dict[int, str], Dict[str, int]]:
        """Fetches the items and their ids from https://tibia.fandom.com/wiki/Item_IDs

        Returns:
            Tuple[Dict[int, str], Dict[str, int]]: A tuple containing a dictionary mapping item ids to item names, and a dictionary mapping item names to item ids.
        """
        # TODO: Consider reading ~/.local/share/CipSoft GmbH/Tibia/packages/Tibia/assets/appearances-*.dat for item info.
        # This is a protobuf file. https://otland.net/threads/tibia-11-dat-file-structure.246601/
        response = requests.get("https://tibia.fandom.com/api.php?action=parse&page=Item_IDs&format=json").json()
        response = response["parse"]["text"]["*"]
        
        # Get all the item names and ids from the table.
        items = re.findall(">([^<>]+)</a></td>\n<td>([0-9, ]+)\n</td>", response)

        if not items:
            raise Exception("Failed to parse item ids from fandom wiki. Regex returned no matches.")

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

    @staticmethod
    def get_wiki_names() -> Dict[int, str]:
        """Returns a dictionary mapping item ids to their pretty names.

        Returns:
            Dict[int, str]: A dictionary mapping item ids to their pretty names.
        """
        global id_to_pretty_name, pretty_name_to_id

        if id_to_pretty_name:
            return id_to_pretty_name

        # if file exists.
        if os.path.exists("items.csv"):
            with open("items.csv", "r") as f:
                for line in f.readlines():
                    if len(line) >= 3:
                        values = line.split(",")
                        id = values[-1]
                        name = ",".join(values[:-1])

                        id_to_pretty_name[int(id)] = name
                        pretty_name_to_id[name] = int(id)

        # Load item ids from wiki, or from items.csv if wiki is down.
        try: 
            wiki_id_to_name, wiki_name_to_id = Wiki.get_item_ids()

            # Merge the two dictionaries.
            id_to_pretty_name = {**id_to_pretty_name, **wiki_id_to_name}
            pretty_name_to_id = {**pretty_name_to_id, **wiki_name_to_id}

            # Save the item ids to items.csv.
            with open("items.csv", "w+") as f:
                for key, value in pretty_name_to_id.items():
                    f.write(f"{key},{value}\n")
        except Exception as e:
            print(f"Failed to get item ids from wiki. {e}")
        
        return id_to_pretty_name

    @staticmethod
    def get_marketable_proto_items() -> Dict[int, appearances_pb2.Appearance]:
        """Parses the appearance.dat file, and returns all items with the market flag set.

        Returns:
            Dict[int, appearances_pb2.Appearance]: A dictionary mapping item ids to Appearance objects.
        """
        if not proto_items:
            assets_folder = os.path.expanduser("/root/.local/share/CipSoft GmbH/Tibia/packages/Tibia/assets")
            appearances_dat_file_name = [file_name for file_name in os.listdir(assets_folder) if file_name.startswith("appearances-") and file_name.endswith(".dat")][0]

            appearances = appearances_pb2.Appearances()
            appearances.ParseFromString(open(f"{assets_folder}/{appearances_dat_file_name}", "rb").read())

            for item in appearances.object:
                if str(item.flags.market):
                    proto_items[item.id] = item

        return proto_items

    @staticmethod
    def get_event_data() -> EventData:
        """Returns today's EventData object.

        Returns:
            EventData: Today's EventData object.
        """
        event_schedule_json = os.path.expanduser("/root/.local/share/CipSoft GmbH/Tibia/packages/Tibia/cache/eventschedule.json")

        if not os.path.exists(event_schedule_json):
            raise Exception("Failed to find event schedule json file. Make sure to log in to the game at least once.")
        
        with open(event_schedule_json, "r") as f:
            event_schedule = f.read()
            json_data = json.loads(event_schedule)["eventlist"]

            today = datetime.today().date()
            events_today = []

            for event in json_data:
                # Convert unix timestamps to dates.
                start_date = datetime.fromtimestamp(event["startdate"]).date()
                end_date = datetime.fromtimestamp(event["enddate"]).date()
                name = event["name"]

                # If the event starts or ends today, add an asterisk to the name.
                if start_date == today or end_date == today:
                    name = f"*{name}"

                # If today is between the start and end date, add the event to the list.
                if start_date <= today <= end_date:
                    events_today.append(event["name"])

            return EventData(datetime(year=today.year, month=today.month, day=today.day), events_today)