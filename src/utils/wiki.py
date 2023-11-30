from datetime import datetime
from typing import Dict, List, Tuple
import requests
import re
import sys
import os

# Add the proto directory to the path so that we can import from it.
sys.path.append(os.path.join(os.path.dirname(__file__), "proto"))

from utils.proto import appearances_pb2


class EventData:
    def __init__(self, date: datetime, events: List[str]):
        self.date = date
        self.events = events

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
    def get_events(after_date: datetime = None) -> List[EventData]:
        """
        Scrapes the event calendar from tibia.com and returns a list of EventData objects.
        
        Args:
            after_date (datetime, optional): Only return events after this date. Defaults to None.
           
        Returns:
            List[EventData]: A list of EventData objects.
        """
        # TODO: Consider reading ~/.local/share/CipSoft GmbH/Tibia/packages/Tibia/cache/eventschedule.json after logging in.
        event_data: List[EventData] = []
        response = requests.get("https://www.tibia.com/news/?subtopic=eventcalendar").text
        events = response.split("\"eventscheduletable\"")[-1].split("</table>")[0].split("<td style")[1:]
        events = [event.split("</td>")[0] for event in events]

        today = datetime.today()
        month_modifier = -1
        today_reached = False
        for event in events:
            try:
                day = int(re.search(">([0-9]{1,2}) </span", event).group(1))

                # Event table can wrap to month before or next month, handle these cases.
                if day <= today.day and not today_reached:
                    month_modifier = 0
                if not today_reached and day == today.day:
                    today_reached = True
                elif today_reached and month_modifier == 0 and day < today.day:
                    month_modifier = 1

                month = today.month + month_modifier

                # Handle edge cases of changing year when covering multiple months.
                year = today.year
                if month == 12 and month_modifier == -1:
                    year -=1
                elif month == 1 and month_modifier == 1:
                    year += 1

                event_names = [event_name for event_name in [text.split(">")[-1] for text in event.split("</div>")[:-1]] if len(event_name) > 0]

                data_datetime = datetime(year, month, day)
                data = EventData(data_datetime, event_names)
                
                if after_date is None or data_datetime > after_date:
                    event_data.append(data)

            except Exception as e:
                print(f"Parsing event info failed for {event}: {e}")
        
        return event_data

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
    def get_pretty_names() -> Dict[int, str]:
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