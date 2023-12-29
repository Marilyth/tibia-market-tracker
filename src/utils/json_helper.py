import json
from types import SimpleNamespace


def object_to_json(obj):
    """Convert an object to a JSON string.

    Args:
        obj (Any): The object to convert.

    Returns:
        str: The JSON string.
    """
    return json.dumps(obj, default=lambda o: o.__dict__ if hasattr(o, "__dict__") else str(o))

def json_to_object(json_string):
    """Convert a JSON string to an object.

    Args:
        json_string (str): The JSON string to convert.

    Returns:
        Any: The object.
    """
    return json.loads(json_string, object_hook=lambda d: SimpleNamespace(**d))