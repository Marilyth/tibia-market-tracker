import pytest
from PIL import Image

from utils.extraction.ocr.image_processing import take_screenshot, process_image, read_image_text, find_playspace


class TestScreenshot:
    def setup(self):
        self.test_image = Image.open("tests/raw.png")
        self.processed_image = Image.open("tests/processed.png")

    def test_TakeScreenshot_TakesScreenshot(self):
        # Act
        image = take_screenshot(0, 0, 100, 200)

        # Assert
        assert isinstance(image, Image.Image)
        assert image.size == (100, 200)

    def test_ProcessImage_3xScale_ReturnsExpected(self):
        # Act
        processed_image = process_image(self.test_image, rescale_factor=3)

        # Assert
        assert processed_image.size == self.processed_image.size
        assert processed_image.mode == self.processed_image.mode
        assert all([x == y for x, y in zip(list(processed_image.getdata()), list(self.processed_image.getdata()))])

    def test_ReadImageText_OfProcessedImage_ReturnsExpected(self):
        # Act
        text = read_image_text(self.processed_image)

        # Assert
        assert text.strip() == "2283"

    def test_FindPlayspace1_ReturnsExpected(self):
        # Arrange
        image = Image.open("tests/test_images/Playspace1.png")

        # Act
        x, y, w, h = find_playspace(image)

        # Assert
        assert abs(x - 472) < 5
        assert abs(y - 123) < 5
        assert abs(w - 481) < 5
        assert abs(h - 353) < 5

    def test_FindPlayspace2_ReturnsExpected(self):
        # Arrange
        image = Image.open("tests/test_images/Playspace2.png")

        # Act
        x, y, w, h = find_playspace(image)

        # Assert
        assert abs(x - 206) < 5
        assert abs(y - 60) < 5
        assert abs(w - 834) < 5
        assert abs(h - 612) < 5
