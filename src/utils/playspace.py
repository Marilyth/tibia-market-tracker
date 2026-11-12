from PIL import Image, ImageGrab
import cv2
import numpy as np


def find_playspace(screenshot: Image.Image = None) -> cv2.typing.Rect:
    """Find the Tibia playspace rectangle in a screenshot."""
    if screenshot is None:
        screenshot = ImageGrab.grab()

    image = np.array(screenshot)

    # The threshold captures the lower and right bounds of the playspace.
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image = cv2.threshold(image, 90, 255, cv2.THRESH_BINARY)[1]

    contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Tibia has 15x11 tiles; choose the large contour with the closest aspect ratio.
    goal_ratio = 15 / 11
    rects = [cv2.boundingRect(contour) for contour in contours]
    rects = [rect for rect in rects if rect[2] * rect[3] > 10000]
    rects.sort(key=lambda rect: abs((rect[2] / rect[3]) - goal_ratio))

    return rects[0]
