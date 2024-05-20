from datetime import datetime
from typing import Dict, List, Tuple
import requests
import re
import sys
import os
from PIL import Image, ImageSequence
import json
from pydantic import BaseModel
import lzma

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
sprite_id_to_location = {}
id_to_pretty_name = {}
pretty_name_to_id = {}

class Wiki:
    def __init__(self):
        pass
    
    @staticmethod
    def _get_assets_folder() -> str:
        """Returns the path to the assets folder.

        Returns:
            str: The path to the assets folder.
        """
        # If on linux:
        if os.name == "posix":
            return os.path.expanduser("/root/.local/share/CipSoft GmbH/Tibia/packages/Tibia/assets")
        else:
            return os.path.expanduser("~\\AppData\\Local\\Tibia\\packages\\Tibia\\assets")
    
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
            assets_folder = Wiki._get_assets_folder()
            appearances_dat_file_name = [file_name for file_name in os.listdir(assets_folder) if file_name.startswith("appearances-") and file_name.endswith(".dat")][0]

            appearances = appearances_pb2.Appearances()
            appearances.ParseFromString(open(f"{assets_folder}/{appearances_dat_file_name}", "rb").read())

            for item in appearances.object:
                if str(item.flags.market):
                    proto_items[item.id] = item

        return proto_items
    
    @staticmethod
    def get_sprite_for_id(sprite_id: int) -> Image:
        """Loads the sprite for the given sprite id.

        Returns:
            Image: The sprite image.
        """
        # Load the location map if it's not already loaded.
        if not sprite_id_to_location:
            assets_folder = Wiki._get_assets_folder()
            
            Wiki.extract_lzma_sprites()
            
            with open(f"{assets_folder}/catalog-content.json", "r") as f:
                catalog = json.loads(f.read())
                
            for item in catalog:
                if item["type"] == "sprite":
                    for i in range(item["firstspriteid"], item["lastspriteid"] + 1):
                        sprite_id_to_location[i] = (os.path.join(assets_folder, item["file"][:-5].replace(".bmp", ".png")), i - item["firstspriteid"])
        
        # Load the sprite from file.
        sprite_size = 32
        sprites_per_row = 12
        
        with Image.open(sprite_id_to_location[sprite_id][0]) as img:
            sprite_index = sprite_id_to_location[sprite_id][1]
            
            # Calculate the x, y position of the sprite in the grid.
            x = (sprite_index % sprites_per_row) * sprite_size
            y = (sprite_index // sprites_per_row) * sprite_size
            
            # Crop the sprite from the grid.
            return img.crop((x, y, x + sprite_size, y + sprite_size))
    
    @staticmethod
    def get_sprites_for_item(item_id: int) -> Image:
        """
        Returns the sprites for the given item id.
        
        Returns:
            List[Image]: A list of sprite images.
        """
        item_information = Wiki.get_marketable_proto_items()[item_id]
        sprite_infos = item_information.frame_group[0].sprite_info
        
        sprites = []
        for sprite_id in sprite_infos.sprite_id:
            sprites.append(Wiki.get_sprite_for_id(sprite_id))
            
        return sprites
    
    @staticmethod
    def generate_gif_for_item(item_id: int):
        """Generates a gif for the given item id.

        Args:
            item_id (int): The item id.
        """
        sprites = Wiki.get_sprites_for_item(item_id)
        
        # If the sprites folder doesn't exist, create it.
        if not os.path.exists("sprites"):
            os.makedirs("sprites")
        
        if len(sprites) == 1:
            sprites[0].save(f"sprites/{item_id}.gif", transparency=0)
        else:
            sprites[0].save(f"sprites/{item_id}.gif", save_all=True, append_images=sprites[1:], duration=100, loop=0, transparency=0)
    
    @staticmethod
    def extract_lzma_sprites():
        """Decompresses all lzma files in the assets folder.

        Returns:
            Dict[int, appearances_pb2.Appearance]: A dictionary mapping item ids to Appearance objects.
        """
        assets_folder = Wiki._get_assets_folder()
       
        # Decrompress lzma files.
        for file_name in os.listdir(assets_folder):
            if file_name.endswith(".lzma"):
                decompressed_file_name = file_name[:-5].replace(".bmp", ".png")
                
                # Don't do anything if the decompressed file already exists, and is newer than the lzma file.
                if os.path.exists(f"{assets_folder}/{decompressed_file_name}") and \
                    os.path.getmtime(f"{assets_folder}/{decompressed_file_name}") > os.path.getmtime(f"{assets_folder}/{file_name}"):
                    continue
                
                with open(f"{assets_folder}/{file_name}", "rb") as f:
                    # Skip the first 32 bytes.
                    data = bytearray(f.read())[32:]
                    
                    # Set the 6th to 12th byte to 255 to fix the header.
                    for i in range(5, 13):
                        data[i] = 255
                    
                    decompressed = lzma.decompress(data)
                    
                    # Write the decompressed data to a new file.
                    with open(f"{assets_folder}/{file_name[:-5]}", "wb") as out:
                        out.write(decompressed)
                    
                    if file_name.endswith(".bmp.lzma"):
                        # Convert the bmp to png.
                        with Image.open(f"{assets_folder}/{file_name[:-5]}") as img:
                            img.save(f"{assets_folder}/{decompressed_file_name}")
                        
                        # Delete the bmp file.
                        os.remove(f"{assets_folder}/{file_name[:-5]}")

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

            return EventData(date=datetime(year=today.year, month=today.month, day=today.day), events=events_today)