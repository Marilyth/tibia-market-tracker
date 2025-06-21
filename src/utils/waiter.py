import time
from typing import Callable


def wait_until(func: Callable[[], bool], timeout: float = 10, interval: float = 0.1) -> bool:
    """
    Waits until func returns True or timeout is reached.

    Args:
        func: A function that returns True or False.
        timeout: How long to wait before raising an exception.
        interval: How often to check if func returns True.

    Returns:
        True if func returned True, False if timeout was reached.
    """
    start_time = time.time()

    while not func():
        if time.time() - start_time > timeout:
            return False
        
        time.sleep(interval)
    
    return True