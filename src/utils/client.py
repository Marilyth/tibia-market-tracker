import pyautogui
import subprocess
import time
import logging
from random import uniform
from typing import *
import os
from utils.extraction.memory.memory_reader import MemoryReader
import shutil
from utils.human_movement import move_mouse_like_human, wait_like_human, repeat_like_human
from utils.schedule import Character
from utils.extraction.ocr.image_processing import find_playspace


logger = logging.getLogger(__name__)

depot_tile_orientations = ["West", "North", "South"]

class Client:
    def __init__(self, executable_location: str, character: Character):
        '''
        The Tibia client, and all required functionality.

        Args:
            executable_location (str): The location of the Tibia executable.
            character (Character): The character to log in with.
        '''
        pyautogui.PAUSE = 0.1
        self.tibia_data_location = os.path.join(os.path.expanduser("~"), ".local", "share", "CipSoft GmbH", "Tibia")
        self.tibia_settings_location = os.path.join(self.tibia_data_location, "packages", "Tibia", "conf")
        self.tibia_executable_location = executable_location
        self.character = character
        self.env = {}

        self.tibia: subprocess.Popen = None
        self.tibia_process_id = None
        self.market_tab = "offers"
        self.bot_log = []
        self.game_log = ""

        self.position_cache = {}
        self.kick_time = time.time() + 60 * 13
        self.playspace = None

    def start_game(self):
        """Starts Tibia and updates it if necessary.
        """
        # If Tibia was closed before, remove the shared memory files. Otherwise Tibia will not start.
        for file in os.listdir("/tmp"):
            if file.startswith("qipc_sharedmemory"):
                os.remove(os.path.join("/tmp", file))

        # Start Tibia.
        self.tibia: subprocess.Popen = subprocess.Popen([self.tibia_executable_location], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env={**os.environ, **self.env})
        os.set_blocking(self.tibia.stdout.fileno(), False)

        time.sleep(5)
        self._update_tibia()

    def get_tibia_process_output(self) -> str:
        """Returns the output of the Tibia process so far, and decodes it to utf-8.

        Returns:
            str: The output of the Tibia process.
        """
        if self.tibia:
            # Read line by line to avoid blocking.
            output = self.game_log

            while True:
                line = self.tibia.stdout.readline().decode("utf-8")

                if line:
                    output += line
                else:
                    self.game_log += output
                    break

            return output
        else:
            return ""

    def _update_tibia(self):
        """
        Checks if the update or install button exists, and if so, installs or updates and starts Tibia.
        """
        # Tibia is using a default client, no need to use the launcher.
        if self._wait_until_find("images/PasswordField.png", click=False, cache=False, timeout=5)[0] != -1 or \
            self._wait_until_find("images/Cancel.png", click=False, cache=False, timeout=5)[0] != -1:
            return

        # Don't click on the play button yet. We first need to replace the config file after the update.
        if self._wait_until_find("images/PlayButton.png", click=False, cache=False, timeout=5)[0] == -1:
            # No playbutton exists, so Tibia must be updated or running first.
            if self._wait_until_find("images/Update.png", click=True, timeout=5, cache=False)[0] == -1:
                self._wait_until_find("images/Install.png", click=True, timeout=5, cache=False)

        # Create ~/.local/share/CipSoft Gmbh/Tibia/packages/config if it doesn't exist.
        os.makedirs(self.tibia_settings_location, exist_ok=True)

        # Copy ./config/clientoptions.json.
        shutil.copyfile("./config/clientoptions.json", os.path.join(self.tibia_settings_location, "clientoptions.json"))

        # Wait until update is done, and click play button.
        self._wait_until_find("images/PlayButton.png", click=True, cache=False, timeout=600)
        wait_like_human(5)

    def _update_kick_timer(self):
        """Updates the timer for the next required wiggle. I.e. the time until the character would get kicked for being afk.
        """
        self.kick_time = time.time() + 60 * 13

    def login_to_game(self):
        """
        Logs into the provided account, and selects the provided character.
        """
        # In case the client crashed, cancel the error report dialog.
        self._wait_until_find("images/Cancel.png", timeout=5, click=True, cache=False, coordinate_deviation=2)
        self._wait_until_find("images/PasswordField.png", click=False, cache=False, coordinate_deviation=2, throw_on_timeout=True)
        pyautogui.typewrite(self.character.username, 0.1)
        pyautogui.press("tab")
        wait_like_human(0.2)
        pyautogui.typewrite(self.character.password, 0.1)
        wait_like_human(0.2)

        pyautogui.press("enter")

        # Go ingame.
        self._wait_until_find("images/CharacterSlot.png", click=True, cache=False, throw_on_timeout=True)

        # If desired, select another character than the first one.
        repeat_like_human(lambda: pyautogui.press("down"), self.character.slot)

        pyautogui.press("enter")

        # Wait until ingame.
        self._wait_until_find("images/Ingame.png", cache=False, throw_on_timeout=True)
        self._add_to_log("Ingame.")
        self.playspace = find_playspace()

        self._update_kick_timer()
        self.tibia_process_id = MemoryReader.get_process_id("client")[-1]

        tibia_output = self.get_tibia_process_output()
        self.character.name = tibia_output.split("Charakter \"")[-1].split("\"")[0]
        self.character.server = tibia_output.split("Connected to gameserver ")[-1].split("\" \"")[-1].split("\"")[0]

        self._add_to_log(f"Logged in as {self.character.name} in server {self.character.server}.")

    def exit_tibia(self):
        """
        Closes Tibia unsafely. Probably better to log out before.
        """
        pyautogui.press("escape")
        wait_like_human(0.2)
        pyautogui.press("escape")
        wait_like_human(0.2)

        self._wait_until_find("images/LeaveButton.png", click=True, cache=False, timeout=5)
        self._wait_until_find("images/YesButton.png", click=True, cache=False, timeout=5)

        # Can't exit while characters are displayed...
        wait_like_human(2)
        pyautogui.press("escape")

        self._wait_until_find("images/LeaveButton.png", click=True, cache=False, timeout=5)

    def open_market(self):
        """
        Searches for an empty depot, and opens the market on it.
        """
        if not self.walk_to_depot():
            return False

        # We are at a depot, check if already opened.
        if self._wait_until_find("images/Market.png", click=True, cache=False, timeout=5)[0] == -1:
            self._add_to_log("Opening depot")

            # Approximate depot screen position.
            orientation = self.is_at_depot()
            x, y = 7, 5

            if orientation == "North":
                y -= 1
            elif orientation == "South":
                y += 1
            elif orientation == "East":
                x += 1
            elif orientation == "West":
                x -= 1

            move_mouse_like_human(*self._get_playspace_tile_coordinate(x, y))
            pyautogui.leftClick()

            # Tried to open depot, check if it worked.
            if self._wait_until_find("images/Market.png", click=True, cache=False, timeout=5)[0] == -1:
                return False

        # Depot and market are open, wait for market to load.
        return self._wait_until_find("images/Details.png", cache=False, timeout=5) != -1

    def is_at_depot(self) -> str:
        """
        Checks if the character is at a depot.

        Returns:
            bool: True if the character is at a depot, False otherwise.
        """
        for orientation in depot_tile_orientations:
            x, y = self._wait_until_find(f"images/SuccessDepotTile{orientation}.png", timeout=1, cache=False, exact=True)

            if x >= 0:
                return orientation

        return None

    def walk_to_depot(self) -> bool:
        """
        Tries to find a depot and walks to it.

        Returns:
            bool: True if the character successfully walked to the depot, False otherwise.
        """
        if self.walk_to_nearby_depot():
            return True

        if self.walk_to_far_depot():
            return self.walk_to_nearby_depot()

        return False

    def walk_to_nearby_depot(self) -> bool:
        """
        Searches for an empty depot tile and walks to it.

        Returns:
            bool: True if the character successfully walked to the depot, False otherwise.
        """
        self._add_to_log("Walking to depot...")

        # Scroll into minimap.
        self._wait_until_find("images/ZoomMinimap.png", cache=False, click=True, exact=True, coordinate_deviation=2, throw_on_timeout=True)
        repeat_like_human(lambda: pyautogui.click(), 5)

        if self.is_at_depot():
            return True

        found_depots = len(self._find_all_depots())
        self._add_to_log(f"Found {found_depots} depots.")

        for i in range(found_depots):
            depots = self._find_all_depots()
            depot_index = i

            # If we are now obscuring the depot, try the next one.
            if len(depots) < found_depots:
                depot_index -= 1

            depot_index = min(depot_index, len(depots) - 1)
            logger.info(f"Trying depot {i} ({depot_index})...")

            # Order by y and then x coordinate, so we go horizontally through all before switching levels.
            depots = sorted(depots, key=lambda x: (x[1], x[0]))

            depot_position = pyautogui.center(depots[depot_index])
            move_mouse_like_human(depot_position[0], depot_position[1], 0) # Move to the center of the depot tile.
            pyautogui.leftClick()

            move_mouse_like_human(20, 20)

            if self.is_at_depot():
                return True

        return False

    def walk_to_far_depot(self) -> bool:
        """
        Searches for the depot icon in the max zoomed out minimap and walks to it.

        Returns:
            bool: True if the character successfully walked to the depot, False otherwise.
        """
        self._add_to_log("Checking if depot icon is visible in the minimap.")

        self._wait_until_find("images/ZoomOutMinimap.png", cache=False, click=True, exact=True, coordinate_deviation=2, throw_on_timeout=True)
        repeat_like_human(lambda: pyautogui.click(), 5)

        found_coordinate = pyautogui.locateCenterOnScreen("images/DepotIcon.png")

        if not found_coordinate:
            self._add_to_log("No depot icon found.")
            return False

        move_mouse_like_human(found_coordinate[0], found_coordinate[1], 2)
        pyautogui.leftClick()

        move_mouse_like_human(20, 20)

        # Wait until the icon stop moving.
        while True:
            pyautogui.sleep(2)
            new_coordinate = pyautogui.locateCenterOnScreen("images/DepotIcon.png")

            # If the icon stopped moving, or disappeared, consider it reached.
            if not new_coordinate or \
                (new_coordinate[0] == found_coordinate[0] and \
                 new_coordinate[1] == found_coordinate[1]):
                break

            found_coordinate = new_coordinate

        return True

    def close_market(self):
        """
        Closes the market window using the escape hotkey.
        Also clears the cache to avoid clicking before the market opens.
        """
        self._add_to_log("Closing market...")
        pyautogui.PAUSE = 0.1
        pyautogui.press("escape")
        wait_like_human(0.2)
        pyautogui.press("escape")
        wait_like_human(0.2)
        self.clear_cache()

    def clear_cache(self):
        """
        Clears the position cache.
        Use this to avoid clicking on places that aren't yet loaded.
        """
        self.position_cache = {}

    def wiggle(self):
        """
        Wiggles the character to avoid being afk kicked.
        """
        self._add_to_log("Wiggling character...")
        pyautogui.hotkey("ctrl", "right")
        wait_like_human(0.5)
        pyautogui.hotkey("ctrl", "left")
        wait_like_human(0.5)
        self.market_tab = "offers"
        self._update_kick_timer()

    def _find_all_depots(self):
        found_depots = []

        for orientation in depot_tile_orientations:
            found_depots += list(pyautogui.locateAllOnScreen(f"images/DepotTile{orientation}.png"))

        return found_depots

    def _wait_until_find(self, image: str, timeout: int = 60, click: bool = False, cache: bool = True, exact: bool = False, throw_on_timeout: bool = False, coordinate_deviation: int = 5) -> Tuple[int, int]:
        start_time = time.time()

        while time.time() - start_time < timeout:
            if cache and image in self.position_cache:
                self._add_to_log(f"Found {image} in cache.")
                position = self.position_cache[image]
            else:
                self._add_to_log(f"Looking for {image}...")
                move_mouse_like_human(20, 20)
                if not exact:
                    position = pyautogui.locateCenterOnScreen(image, grayscale=True, confidence=0.9)
                else:
                    position = pyautogui.locateCenterOnScreen(image)
                if position:
                    self.position_cache[image] = position

            if position:
                self._add_to_log(f"Found {image} at {position}.")
                if click:
                    self._add_to_log(f"Clicking {image}...")
                    move_mouse_like_human(position[0], position[1], coordinate_deviation)
                    pyautogui.leftClick()

                return position

            wait_like_human(0.3)

        self._add_to_log(f"Finding {image} failed.")
        if throw_on_timeout:
            raise TimeoutError(f"Finding {image} failed.")

        return (-1, -1)

    def _add_to_log(self, message: str):
        self.bot_log.append(message)
        logger.info(message)

    def _get_playspace_tile_coordinate(self, x, y) -> Tuple[int, int]:
        """
        Returns the screen coordinates of the given tile in the playspace.
        """
        if self.playspace is None:
            raise ValueError("Playspace not found.")
        
        if x < 0 or x >= 15 or y < 0 or y >= 11:
            raise ValueError("Invalid tile coordinate.")
        
        x_p, y_p, w, h = self.playspace
        tile_width = w / 15
        tile_height = h / 11

        # The playspace isn't 100% accurate, so this aims for the center.
        x_delta = tile_width * x + tile_width / 2
        y_delta = tile_height * y + tile_height / 2

        return (x_p + x_delta, y_p + y_delta)
