from threading import Lock


class SequenceManager:
    def __init__(self):
        self.next_sequence = 0
        self.injection_count = 0
        self.lock_object = Lock()

    def adjust_sequence_number(self, message: bytes, is_injected: bool = False) -> bytes:
        """Changes the sequence number of a message to the next expected one.

        Args:
            message (bytes): The message to adjust.
            is_injected (bool, optional): Whether the message is injected. Defaults to False.

        Returns:
            bytes: The message with the adjusted sequence number.
        """
        with self.lock_object:
            message_sequence = int.from_bytes(message[2:4], 'little')

            # If the sequence is not the next one, return the message unchanged.
            if not is_injected and message_sequence != self.next_sequence:
                return message

            message = bytearray(message)
            message[2:4] = self._get_next_expected_sequence().to_bytes(2, 'little')

            if is_injected:
                self.injection_count += 1
            else:
                self.next_sequence += 1

            return bytes(message)

    def _get_next_expected_sequence(self):
        """Returns the next actual sequence number."""
        return self.next_sequence + self.injection_count
