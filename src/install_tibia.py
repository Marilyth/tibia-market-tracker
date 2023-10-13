import requests
import tarfile
import os
from pyvirtualdisplay import Display
import Xlib.display

def is_tibia_downloaded():
    """Checks if Tibia is installed.
    """
    return os.path.exists("./Tibia/Tibia")

def download_package():
    """Downloads and extracts the Tibia package, if it is not already downloaded.
    """
    # Check if Tibia is already downloaded.
    if is_tibia_downloaded():
        print("Tibia is already downloaded.")
        return

    package_url = "https://static.tibia.com/download/tibia.x64.tar.gz"

    print("Downloading Tibia package...")
    r = requests.get(package_url, stream=True)

    with open("tibia.tar.gz", "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            f.write(chunk)

    print("Download complete.")

    # Extract the package
    print("Extracting Tibia package...")
    
    tar = tarfile.open("tibia.tar.gz")
    tar.extractall()
    tar.close()

    # Delete the package
    os.remove("tibia.tar.gz")

    print("Extraction complete.")

    if not is_tibia_downloaded():
        raise Exception("Tibia downloading failed.")

def install_tibia():
    """Triggers the installation of Tibia, if it is not already installed.
    """
    # Start_game already handles the installation process.
    with Display(visible=False, size=(1600, 900)):
        import pyautogui
        from utils.tibia import Client
        pyautogui._pyautogui_x11._display = Xlib.display.Display(os.environ['DISPLAY'])
        client = Client()
        client.start_game("Tibia/Tibia")
        client.exit_tibia()

if __name__ == "__main__":
    download_package()
    install_tibia()