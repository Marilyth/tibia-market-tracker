import re
import sys
import os
import logging
from datetime import datetime
from typing import Dict, List, Tuple
import requests
from PIL import Image
import json
from pydantic import BaseModel
import lzma
from lxml import etree
from blackboxprotobuf import decode_message, export_protofile
from utils.data.loot_statistics import LootStatistics, Loot, Monster
import colorsys

# Add the proto directory to the path so that we can import from it.
sys.path.append(os.path.join(os.path.dirname(__file__), "data", "proto"))

from utils.data.proto import appearances_pb2
from utils.data.proto import shared_pb2


logger = logging.getLogger(__name__)


class EventData(BaseModel):
    """A data class containing information about the events of a given day.
    """
    date: datetime
    events: List[str]

    def __str__(self) -> str:
        return f"{self.date.strftime('%Y.%m.%d')},{','.join(self.events)}"


color_grid = []
proto_monsters = {}
proto_outfits = {}
proto_items = {}
marketable_proto_items = {}
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
            return os.path.expanduser("~/.local/share/CipSoft GmbH/Tibia/packages/Tibia/assets")
        else:
            return os.path.expanduser("~\\AppData\\Local\\Tibia\\packages\\Tibia\\assets")

    @staticmethod
    def get_loot_statistics(monster_name: str) -> List[LootStatistics]:
        """Fetches the loot statistics for a given monster from the tibia fandom wiki.

        Args:
            monster_name (str): The name of the monster.

        Returns:
            Dict[str, int]: A dictionary mapping item names to their drop rates.
        """
        url = f"https://tibia.fandom.com/api.php?action=parse&page=Loot_Statistics:{monster_name}&format=json"
        response = requests.get(url).json()
        html = response["parse"]["text"]["*"]
        
        statistics: List[LootStatistics] = []
        
        # Parse the html using lxml.
        tree = etree.HTML(html)
        
        # Find the tables with the loot statistics.
        tables = tree.xpath("//table[contains(@class, 'loot_list')]")
        for table in tables:
            loot: List[Loot] = []
            
            caption = etree.tostring(table.xpath(".//caption")[0], method="text", encoding="unicode")
            kills = re.findall(r"([\d,]+) kills", caption)
            
            if len(kills) > 0:
                kills = int(kills[0].replace(",", ""))
            else:
                continue
            
            rows = table.xpath(".//tr")[1:]
            headers = [etree.tostring(header, method="text", encoding="unicode").strip() for header in table.xpath(".//th")]
            total_amount_index = [i for i, header in enumerate(headers) if "amount" in header.lower()][-1]
            name_index = headers.index("Item")
            
            for row in rows:
                columns = row.xpath(".//td")
                
                item_name = etree.tostring(columns[name_index], method="text", encoding="unicode").strip()
                loot.append(Loot(item_id=-1, amount_looted=int(columns[total_amount_index].text.strip())))
            
            statistics.append(LootStatistics(monster_id=-1, item_id=-1, loot=loot, kills=kills))

        return statistics

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
            logger.warning(f"Failed to get item ids from wiki. {e}", exc_info=True)
        
        return id_to_pretty_name

    @staticmethod
    def get_proto_appearances() -> Dict[int, appearances_pb2.Appearance]:
        """Parses the appearance.dat file, and returns all items.

        Returns:
            Dict[int, appearances_pb2.Appearance]: A dictionary mapping ids to Appearance objects.
        """
        if not proto_items:
            assets_folder = Wiki._get_assets_folder()
            appearances_dat_file_name = [file_name for file_name in os.listdir(assets_folder) if file_name.startswith("appearances-") and file_name.endswith(".dat")][0]

            appearances = appearances_pb2.Appearances()
            appearances.ParseFromString(open(f"{assets_folder}/{appearances_dat_file_name}", "rb").read())

            for item in appearances.object:
                proto_items[item.id] = item
            
            for outfit in appearances.outfit:
                proto_outfits[outfit.id] = outfit
        
        return proto_items, proto_outfits

    @staticmethod
    def get_marketable_proto_items() -> Dict[int, appearances_pb2.Appearance]:
        """Parses the appearance.dat file, and returns all items with the market flag set.

        Returns:
            Dict[int, appearances_pb2.Appearance]: A dictionary mapping item ids to Appearance objects.
        """
        if not marketable_proto_items:
            all_proto_items, _ = Wiki.get_proto_appearances()
            
            for key in all_proto_items:
                item = all_proto_items[key]

                if str(item.flags.market) and item.flags.market.trade_as_object_id == item.id:
                    marketable_proto_items[key] = item
        
        return marketable_proto_items

    @staticmethod
    def get_monsters() -> Dict[int, object]:
        """Parses the staticdata.dat file, and returns all monsters.

        Returns:
            Dict[int, object]: A dictionary mapping monster ids to staticdata objects.
        """
        if not proto_monsters:
            assets_folder = Wiki._get_assets_folder()
            static_dat_file_name = [file_name for file_name in os.listdir(assets_folder) if file_name.startswith("staticdata-") and file_name.endswith(".dat")][0]

            with open(f"{assets_folder}/{static_dat_file_name}", "rb") as f:
                data = f.read()

            message, typedef = decode_message(data)
            for monster in message["1"]:
                proto_monsters[monster["1"]] = monster

        return proto_monsters

    @staticmethod
    def get_sprite_for_id(sprite_id: int, sprite_size: int = 32) -> Image:
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
        sprites_per_row = 384 // sprite_size
        file_name = sprite_id_to_location[sprite_id]
        
        with Image.open(file_name[0]) as img:
            sprite_index = sprite_id_to_location[sprite_id][1]
            
            # Calculate the x, y position of the sprite in the grid.
            x = (sprite_index % sprites_per_row) * sprite_size
            y = (sprite_index // sprites_per_row) * sprite_size
            
            # Crop the sprite from the grid.
            return img.crop((x, y, x + sprite_size, y + sprite_size))

    @staticmethod
    def get_sprites_for_appearance(appearance: appearances_pb2.Appearance) -> Tuple[Image.Image, int]:
        """
        Returns the sprites for the given appearance.
        
        Returns:
            List[Image, int]: A list of sprite images and their duration in ms.
        """
        sprite_infos = appearance.frame_group[0].sprite_info
        frame_durations = sprite_infos.animation.sprite_phase
        
        sprites = []
        for i, sprite_id in enumerate(sprite_infos.sprite_id):
            sprite_size = 32
            for bbox in sprite_infos.bounding_box_per_direction:
                if bbox.y + bbox.height > 32 or bbox.x + bbox.width > 32:
                    sprite_size = 64
                    
            sprites.append((Wiki.get_sprite_for_id(sprite_id, sprite_size), frame_durations[i].duration_min if len(frame_durations) > i else 1000))
            
        if sprite_infos.animation.loop_type == shared_pb2.ANIMATION_LOOP_TYPE.ANIMATION_LOOP_TYPE_PINGPONG:
            # Append the middle frames again, in reverse order.
            sprites += sprites[-2:0:-1]
            
        return sprites
    
    @staticmethod
    def generate_gif_for_item_id(item_id: int):
        """Generates a gif for the given id.

        Args:
            item_id (int): The item id.
        """
        appearance = Wiki.get_proto_appearances()[0][item_id]
        sprites = Wiki.get_sprites_for_appearance(appearance)
        
        # If the sprites folder doesn't exist, create it.
        if not os.path.exists("sprites"):
            os.makedirs("sprites")
        
        if len(sprites) == 1:
            sprites[0][0].save(f"sprites/{item_id}.gif")
        else:
            other_frames = [sprite[0] for sprite in sprites[1:]]
            durations = [sprite[1] for sprite in sprites]
            sprites[0][0].save(f"sprites/{item_id}.gif", save_all=True, append_images=other_frames,
                               duration=durations, loop=0, disposal=2)
    
    @staticmethod
    def generate_gif_for_outfit_id(outfit_id: int):
        """Generates a gif for the given id.

        Args:
            item_id (int): The item id.
        """
        appearance = Wiki.get_proto_appearances()[1][outfit_id]
        sprites = Wiki.get_sprites_for_appearance(appearance)
        
        # If the sprites folder doesn't exist, create it.
        if not os.path.exists("sprites"):
            os.makedirs("sprites")
        
        if len(sprites) == 1:
            sprites[0][0].save(f"sprites/o{outfit_id}.gif")
        else:
            other_frames = [sprite[0] for sprite in sprites[1:]]
            durations = [sprite[1] for sprite in sprites]
            sprites[0][0].save(f"sprites/o{outfit_id}.gif", save_all=True, append_images=other_frames,
                               duration=durations, loop=0, disposal=2)
    
    @staticmethod
    def generate_gif_for_monster_id(monster_id: int):
        """Generates a gif for the given id.

        Args:
            item_id (int): The item id.
        """
        appearance = Wiki.get_monsters()[monster_id]
        if "1" not in appearance["3"]:
            logger.debug("Monster appearance has no outfit id; skipping gif generation.")
            return
        Wiki.generate_gif_for_outfit_id(appearance["3"]["1"])
    
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
    def colorcode_to_rgb(color_code: int) -> Tuple[int, int, int]:
        """Converts a tibia color code to an RGB tuple.

        Args:
            color_code (int): The color code, which is an index on the 19x7 color grid.

        Returns:
            Tuple[int, int, int]: The RGB tuple.
        """
        if not color_grid:
            # Can't seem to make a solid algorithm for the Tibia color grid. Each row seems picked almost at random.
            row_saturation = [0.25, 0.25, 0.5, 0.66, 1, 1, 1]
            row_value = [1, 0.75, 0.75, 0.75, 1, 0.75, 0.5]
            
            for i, row in enumerate(zip(row_saturation, row_value)):
                row_grey = 1 - (1 / 7) * i
                row_colors = []
                
                for j in range(19):
                    # The first column replaces red with grey.
                    if j == 0:
                        row_colors.append([0, 0, row_grey])
                        continue
                    
                    hue = (j * (1 / 18))
                    row_colors.append([hue, row[0], row[1]])
                        
                color_grid.append(row_colors)
    
        # Convert the color code to a row and column.
        row = color_code // 19
        column = color_code % 19
        color = color_grid[row][column]
        
        return [int(v * 255) for v in colorsys.hsv_to_rgb(*color)]

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
