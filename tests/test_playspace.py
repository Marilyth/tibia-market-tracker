from PIL import Image

from utils.playspace import find_playspace


def test_find_playspace1_returns_expected():
    image = Image.open("tests/test_images/Playspace1.png")

    x, y, width, height = find_playspace(image)

    assert abs(x - 472) < 5
    assert abs(y - 123) < 5
    assert abs(width - 481) < 5
    assert abs(height - 353) < 5


def test_find_playspace2_returns_expected():
    image = Image.open("tests/test_images/Playspace2.png")

    x, y, width, height = find_playspace(image)

    assert abs(x - 206) < 5
    assert abs(y - 60) < 5
    assert abs(width - 834) < 5
    assert abs(height - 612) < 5
