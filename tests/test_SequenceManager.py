import pytest
from utils.extraction.network.sequence_manager import SequenceManager


class TestSequenceManager:
    def setup_method(self):
        self.manager = SequenceManager()

    def test_initial_state(self):
        # Test the initial state of the SequenceManager
        assert self.manager.next_sequence == 0
        assert self.manager.injection_count == 0

    def test_get_next_actual_sequence(self):
        # Test the get_next_actual_sequence method
        assert self.manager._get_next_expected_sequence() == 0

        # Modify injection_count and test again
        self.manager.injection_count = 5
        assert self.manager._get_next_expected_sequence() == 5

    def test_handle_source_message_sequence_mismatch(self):
        # Test handle_source_message when the sequence does not match
        message = b'\x00\x00\x01\x00\xFF\xFF'  # Sequence is 1
        result = self.manager.adjust_sequence_number(message)
        assert result == message  # Message should remain unchanged

    def test_handle_source_message_sequence_match(self):
        # Test handle_source_message when the sequence matches
        message = b'\x00\x00\x00\x00\xFF\xFF'  # Sequence is 0
        result = self.manager.adjust_sequence_number(message)

        # The sequence in the message should be updated
        assert result[:4] == b'\x00\x00\x00\x00'
        assert self.manager.next_sequence == 1

    def test_handle_source_message_with_injection(self):
        self.manager.next_sequence = 1

        # Test handle_source_message with injection_count affecting the sequence
        injected_message = b'\x00\x00\x00\x00\xFF\xFF'
        message = b'\x00\x00\x01\x00\xFF\xFF'

        result_injected = self.manager.adjust_sequence_number(injected_message, is_injected=True)
        result = self.manager.adjust_sequence_number(message)

        # The sequence in the message should be updated
        assert result_injected[:4] == b'\x00\x00\x01\x00'
        assert result[:4] == b'\x00\x00\x02\x00'
        assert self.manager.next_sequence == 2
