import pytesseract
from PIL import ImageGrab, Image, ImageDraw, ImageFilter
import os
from typing import *
import cv2
import numpy as np

def take_screenshot(left, top, width, height) -> Image.Image:
    """
    Takes a screenshot of the given screen coordinates, and returns the PIL.Image.
    """
    return ImageGrab.grab((left, top, left + width, top + height))

def process_image(image: Image.Image, relative_box: Tuple[int, int, int, int] = None, invert = True, rescale_factor: int = 1) -> Image.Image:
    """
    Converts the image into a more AI readable format. The endresult can be seen under selection_showcase.png and ai_image_input.png.
    relative_box in this format (relative_left, relative_top, relative_width, relative_height).
    """
    bbox = image.getbbox()
    crop_box = bbox if relative_box is None else (bbox[0] + (bbox[2] - bbox[0]) * (1 - relative_box[0]), 
                                                  bbox[1] + (bbox[-1] - bbox[1]) * (1 - relative_box[1]), 
                                                  (bbox[0] + (bbox[2] - bbox[0]) * (1 - relative_box[0])) + (bbox[2] - bbox[0]) * relative_box[2], 
                                                  (bbox[1] + (bbox[-1] - bbox[1]) * (1 - relative_box[1])) + (bbox[-1] - bbox[1]) * relative_box[-1])
    cropped_image = image.crop(crop_box)
    cropped_image = cropped_image.convert("L")

    draw = ImageDraw.Draw(image)
    draw.rectangle(crop_box, outline="black")
    image.save("selection_showcase.png")

    img = np.asarray(cropped_image, dtype="uint8")

    # Bigger images yield better accuracy with tesseract. Use this if OCR is yielding nonsense.
    if rescale_factor > 0 and rescale_factor != 1: 
        y, x = len(img), len(img[0])
        img = cv2.resize(img, [int(x * rescale_factor), int(y * rescale_factor)], interpolation = cv2.INTER_CUBIC)
    img = cv2.threshold(img, 128, 255, (cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY) | cv2.THRESH_OTSU)
    
    # Force black text on white background.
    if img[1][0][0] == 0:
        img = cv2.threshold(img[1], 128, 255, cv2.THRESH_BINARY_INV)

    cropped_image = Image.fromarray(img[1])
    cropped_image.save("ai_image_input.png")

    return cropped_image

def read_image_text(image: Image.Image, psm: int = 3, oem: int = 3, char_white_list: str = "0123456789k") -> str:
    """
    Feeds the image to tesseract, and returns the text it detected.
    """
    config = f"--oem {oem} --psm {psm} -c tessedit_char_whitelist={char_white_list}"

    try:
        return pytesseract.image_to_string(image, config=config)
    except pytesseract.TesseractNotFoundError as e:
        print(e)
        exit(1)