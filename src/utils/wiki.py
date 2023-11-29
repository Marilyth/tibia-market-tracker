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


class Wiki:
    def __init__(self):
        pass

    def get_all_marketable_items(self) -> List[str]:
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

    def get_events(self, after_date: datetime = None) -> List[EventData]:
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

    def get_item_ids(self) -> Tuple[Dict[int, str], Dict[str, int]]:
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

    def get_marketable_proto_items(self) -> List[appearances_pb2.Appearance]:
        """Parses the appearance.dat file, and returns all items with the market flag set.

        Returns:
            List[appearances_pb2.Appearance]: A list of all items with the market flag set.
        """
        assets_folder = os.path.expanduser("/root/.local/share/CipSoft GmbH/Tibia/packages/Tibia/assets")
        appearances_dat_file_name = [file_name for file_name in os.listdir(assets_folder) if file_name.startswith("appearances-") and file_name.endswith(".dat")][0]

        appearances = appearances_pb2.Appearances()
        appearances.ParseFromString(open(f"{assets_folder}/{appearances_dat_file_name}", "rb").read())

        marketable_items = []
        for item in appearances.object:
            if str(item.flags.market):
                marketable_items.append(item)

        return marketable_items