import pytest
from PIL import Image

from src.screenshot import take_screenshot, process_image, read_image_text


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
