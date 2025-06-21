import pyautogui
import subprocess
import time
from random import uniform
from typing import *
import os
from utils.extraction.memory.memory_reader import MemoryReader
import shutil
from utils.human_movement import move_mouse_like_human, wait_like_human, repeat_like_human


class Client:
    def __init__(self, executable_location: str, email: str, password: str, char_index: int):
        '''
        The Tibia client, and all required functionality.

        Args:
            executable_location (str): The location of the Tibia executable.
            email (str): The email of the account to log in with.
            password (str): The password of the account to log in with.
            char_index (int): The 0-based index of the character to log in with.
        '''
        pyautogui.PAUSE = 0.1
        self.tibia_data_location = os.path.join(os.path.expanduser("~"), ".local", "share", "CipSoft GmbH", "Tibia")
        self.tibia_settings_location = os.path.join(self.tibia_data_location, "packages", "Tibia", "conf")
        self.tibia_executable_location = executable_location
        self.email = email
        self.password = password
        self.char_index = char_index

        self.tibia: subprocess.Popen = None
        self.tibia_process_id = None
        self.character_name = ""
        self.character_server = ""
        self.market_tab = "offers"
        self.bot_log = []
        self.game_log = ""

        self.position_cache = {}
        self.kick_time = time.time() + 60 * 13

    def start_game(self):
        """Starts Tibia and updates it if necessary.
        """
        # If Tibia was closed before, remove the shared memory files. Otherwise Tibia will not start.
        for file in os.listdir("/tmp"):
            if file.startswith("qipc_sharedmemory"):
                os.remove(os.path.join("/tmp", file))

        # Start Tibia.
        self.tibia: subprocess.Popen = subprocess.Popen([self.tibia_executable_location], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
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
        # Tibia is using a default client, not need to use the launcher.
        if self._wait_until_find("images/PasswordField.png", click=False, cache=False, timeout=5):
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
        self._wait_until_find("images/PasswordField.png", click=False, cache=False, coordinate_deviation=2)
        pyautogui.typewrite(self.email, 0.1)
        pyautogui.press("tab")
        wait_like_human(0.2)
        pyautogui.typewrite(self.password, 0.1)
        wait_like_human(0.2)

        pyautogui.press("enter")

        # Go ingame.
        self._wait_until_find("images/CharacterSlot.png", click=True, cache=False)

        # If desired, select another character than the first one.
        repeat_like_human(lambda: pyautogui.press("down"), self.char_index)

        pyautogui.press("enter")
        
        # Wait until ingame.
        self._wait_until_find("images/Ingame.png", cache=False)
        self._add_to_log("Ingame.")
        self._update_kick_timer()
        self.tibia_process_id = MemoryReader.get_process_id("client")[-1]

        # Scroll into minimap.
        self._wait_until_find("images/ZoomMinimap.png", cache=False, click=True, exact=True, coordinate_deviation=2)
        repeat_like_human(lambda: pyautogui.click(), 5)

        tibia_output = self.get_tibia_process_output()
        self.character_name = tibia_output.split("Charakter \"")[-1].split("\"")[0]
        self.character_server = tibia_output.split("Connected to gameserver ")[-1].split("\" \"")[-1].split("\"")[0]

        self._add_to_log(f"Logged in as {self.character_name} in server {self.character_server}.")

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
        self._add_to_log("Opening market")
            
        def try_open_market() -> bool:
            x, y = self._wait_until_find("images/SuccessDepotTile.png", timeout=5, cache=False, exact=True)
            if x >= 0:
                # We are at a depot, check if already opened.
                if self._wait_until_find("images/Market.png", click=True, cache=False, timeout=5)[0] == -1:
                    self._add_to_log("Opening depot")

                    # Needs to be adjusted if the resolution is not 1600x900 fullscreen!
                    move_mouse_like_human(645, 345)
                    pyautogui.leftClick()

                    # Tried to open depot, check if it worked.
                    if self._wait_until_find("images/Market.png", click=True, cache=False, timeout=5)[0] == -1:
                        return False
                
                # Depot and market are open, wait for market to load.
                self._wait_until_find("images/Details.png", cache=False, timeout=5)

                self._add_to_log("Market open.")
                return True
            
            return False

        if pyautogui.locateCenterOnScreen("images/SuccessDepotTile.png") and try_open_market():
            return True
        
        found_depots = len(list(pyautogui.locateAllOnScreen("images/DepotTile.png")))
        self._add_to_log(f"Found {found_depots} depots.")

        for i in range(found_depots):
            move_mouse_like_human(20, 20)
            depots = list(pyautogui.locateAllOnScreen("images/DepotTile.png"))
            depot_index = i

            # If we are now obscuring the depot, try the next one.
            if len(depots) < found_depots:
                depot_index -= 1
            
            depot_index = min(depot_index, len(depots) - 1)
            print(f"Trying depot {i} ({depot_index})...")

            # Order by x and then y coordinate, so we click the top left depot first.
            depots = sorted(depots, key=lambda x: (x[0], x[1]))

            depot_position = pyautogui.center(depots[depot_index])
            move_mouse_like_human(depot_position[0], depot_position[1], 0) # Move to the center of the depot tile.
            pyautogui.leftClick()

            if try_open_market():
                return True

        self._add_to_log("Opening market failed!")
        return False

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
        print(message)
