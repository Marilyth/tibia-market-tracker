import requests
import tarfile
import os
import logging
from pyvirtualdisplay import Display
import Xlib.display


logger = logging.getLogger(__name__)


def get_tibia_path():
    """Checks if Tibia is installed.
    """
    potential_locations = ["./Tibia/Tibia", os.path.expanduser("~/Games/Tibia/Tibia"), "/usr/local/bin/tibia"]
    
    for location in potential_locations:
        if os.path.exists(location):
            return location
    
    return None
        

def download_package():
    """Downloads and extracts the Tibia package, if it is not already downloaded.
    """
    # Check if Tibia is already downloaded.
    if get_tibia_path():
        logger.info("Tibia is already downloaded.")
        return

    package_url = "https://static.tibia.com/download/tibia.x64.tar.gz"

    logger.info("Downloading Tibia package...")
    r = requests.get(package_url, stream=True)

    with open("tibia.tar.gz", "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            f.write(chunk)

    logger.info("Download complete.")

    # Extract the package
    logger.info("Extracting Tibia package...")
    
    tar = tarfile.open("tibia.tar.gz")
    tar.extractall()
    tar.close()

    # Delete the package
    os.remove("tibia.tar.gz")

    logger.info("Extraction complete.")

    if not get_tibia_path():
        raise Exception("Tibia downloading failed.")

def install_tibia():
    """Triggers the installation of Tibia, if it is not already installed.
    """
    # Start_game already handles the installation process.
    with Display(visible=False, size=(1600, 900)):
        import pyautogui
        from utils.client import Client
        pyautogui._pyautogui_x11._display = Xlib.display.Display(os.environ['DISPLAY'])
        client = Client(get_tibia_path(), None, None)
        client.start_game()
        client.exit_tibia()

if __name__ == "__main__":
    download_package()
    install_tibia()