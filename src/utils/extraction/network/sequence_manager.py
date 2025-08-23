class SequenceManager:
    def __init__(self):
        self.next_sequence = 0
        self.injection_count = 0

    def adjust_sequence_number(self, message: bytes):
        """Replaces the sequence of the message with the current one."""
        message_sequence = int.from_bytes(message[2:4], 'little')

        # If the sequence is not the next one, return the message unchanged.
        if message_sequence != self.next_sequence:
            return message

        message = bytearray(message)
        message[2:4] = self.get_next_actual_sequence().to_bytes(2, 'little')
        self.next_sequence = message_sequence + 1

        return bytes(message)

    def get_next_actual_sequence(self):
        """Returns the next actual sequence number."""
        return self.next_sequence + self.injection_count
