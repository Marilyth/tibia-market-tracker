import pyautogui
from random import randint, uniform
from pytweening import easeInOutQuad
import asyncio


def cubic_bezier(t, p0, p1, p2, p3):
    """Calculates the cubic bezier curve for the given points and time.

    Args:
        t (float): The time.
        p0 (float): The first point.
        p1 (float): The second point.
        p2 (float): The third point.
        p3 (float): The fourth point.
    """
    u = 1 - t
    t_squared = t * t
    u_squared = u * u
    u_cubed = u_squared * u
    t_cubed = t_squared * t
    return u_cubed * p0 + 3 * u_squared * t * p1 + 3 * u * t_squared * p2 + t_cubed * p3


def repeat_like_human(func: callable, repetitions: int, wait_time: float = 0.2, target_deviation: float = 0.05):
    """Repeats the given function like a human would. I.e. with delay.

    Args:
        func (callable): The function to repeat.
        repetitions (int): The number of repetitions.
        wait_time (float): The time to wait between each repetition in seconds.
        target_deviation (float, optional): The maximum deviation from the target time in seconds. Defaults to 0.1.
    """
    for i in range(repetitions):
        func()
        wait_like_human(wait_time, target_deviation)


def wait_like_human(wait_time: float, target_deviation: float = 0.1):
    """Waits for the specified amount of time like a human would.

    Args:
        wait_time (float): The time to wait in seconds.
        target_deviation (float, optional): The maximum deviation from the target time in seconds. Defaults to 0.1.
    """
    wait_time += uniform(-target_deviation, target_deviation)
    pyautogui.sleep(wait_time)

async def wait_like_human_async(wait_time: float, target_deviation: float = 0.1):
    """Asynchronously waits for the specified amount of time like a human would.

    Args:
        wait_time (float): The time to wait in seconds.
        target_deviation (float, optional): The maximum deviation from the target time in seconds. Defaults to 0.1.
    """
    wait_time += uniform(-target_deviation, target_deviation)
    await asyncio.sleep(wait_time)

def move_mouse_like_human(x: int, y: int, target_deviation: int = 5):
    """Moves the mouse to the specified coordinates like a human would.

    Args:
        x (int): The x coordinate.
        y (int): The y coordinate.
        target_deviation (int, optional): The maximum deviation from the target coordinates. Defaults to 5.
    """
    # Get current mouse position.
    current_mouse_position = pyautogui.position()

    # No need to move the mouse if it is already at the target position.
    if abs(current_mouse_position.x - x) <= target_deviation and abs(current_mouse_position.y - y) <= target_deviation:
        return

    # Add a little deviation to the target position.
    x += randint(-target_deviation, target_deviation)
    y += randint(-target_deviation, target_deviation)

    vector_x = x - current_mouse_position.x
    vector_y = y - current_mouse_position.y

    # Calculate the distance between the current mouse position and the target position.
    distance = ((x - current_mouse_position.x) ** 2 + (y - current_mouse_position.y) ** 2) ** 0.5
    duration = (max(distance, 250) + randint(-100, 100))

    x_path_bezier = [current_mouse_position.x,
              (current_mouse_position.x + vector_x * uniform(0.4, 0.6)),
              current_mouse_position.x + vector_x * uniform(0.85, 0.9),
              x]
    y_path_bezier = [current_mouse_position.y,
              current_mouse_position.y + vector_y * uniform(0.4, 0.6),
              current_mouse_position.y + vector_y * uniform(0.85, 0.9),
              y]

    # Add a little deviation to the path in points 1 and 2, depending on their distance from the previous point.
    for i in range(1, 3):
        x_distance = (x_path_bezier[i] - x_path_bezier[i - 1])
        y_distance = (y_path_bezier[i] - y_path_bezier[i - 1])

        x_path_bezier[i] += uniform(-x_distance / 2, x_distance / 2)
        y_path_bezier[i] += uniform(-y_distance / 2, y_distance / 2)

    steps = int(duration // 10)
    line_progress = [easeInOutQuad(t / (steps - 1)) for t in range(steps)]

    x_path = [cubic_bezier(t_i, x_path_bezier[0], x_path_bezier[1], x_path_bezier[2], x_path_bezier[3]) for t_i in line_progress]
    y_path = [cubic_bezier(t_i, y_path_bezier[0], y_path_bezier[1], y_path_bezier[2], y_path_bezier[3]) for t_i in line_progress]

    # Update mouse position every 10 ms.
    previous_pause = pyautogui.PAUSE
    pyautogui.PAUSE = 0.01

    # Move the mouse to the target positions along the path.
    for x_step, y_step in zip(x_path, y_path):
        pyautogui.moveTo(x_step, y_step)

    # Reset delay.
    pyautogui.PAUSE = previous_pause
