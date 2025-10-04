class Character:
    def __init__(self, username: str, password: str, slot: int, server: str = "Unknown", name: str = "Unknown") -> None:
        self.username = username
        self.password = password
        self.slot = slot
        self.server = server
        self.name = name

class Schedule:
    def __init__(self, schedule_hours: dict[str, list[Character]] = {}):
        self.hours = schedule_hours

    def pick_character(self, hour: int) -> Character:
        """Takes the next character in the queue for the given hour, and moves it to the end of the queue.

        Args:
            hour (int): The hour to pick the character for.

        Returns:
            Character: The character to use for the given hour.
        """
        hour_string = str(hour)

        if hour_string in self.hours and len(self.hours[hour_string]) > 0:
            character = self.hours[hour_string].pop(0)
            self.hours[hour_string].append(character)

            return character

        return None
