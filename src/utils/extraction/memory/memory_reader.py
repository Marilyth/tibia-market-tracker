import psutil

from utils.extraction.memory.process_memory import ProcessMemory


class MemoryReader:
    def __init__(self, p_id=None, process=None):
        self._owns_process = process is None
        self.process = ProcessMemory(p_id) if process is None else process
        self.addresses = []
        self.value_size = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @staticmethod
    def get_process_id(process_name):
        return [process.pid for process in psutil.process_iter() if process.name() == process_name]

    def filter_value(self, value: bytes):
        value = bytes(value)
        if not value:
            raise ValueError("value must not be empty")
        self.value_size = len(value)
        if self.addresses:
            self.addresses = [
                address for address in self.addresses
                if self.process.read(address, self.value_size) == value
            ]
        else:
            self.addresses = self.process.scan(value)
        return self.addresses[:]

    def reset_filter(self):
        self.addresses = []

    def read_values(self):
        return [self.process.read(address, self.value_size) for address in self.addresses]

    def read_bytes(self, address, size):
        return self.process.read(address, size)

    def get_context(self, address, context_length=15):
        return self.process.read(address - context_length, context_length * 2 + 1)

    def close(self):
        if self._owns_process:
            self.process.close()
