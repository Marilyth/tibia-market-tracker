from mem_edit import Process
import ctypes
from typing import *
import psutil


class MemoryReader:
    def __init__(self, p_id: int = None, p_name: str = None, process: Process = None) -> None:
        """Initialises a MemoryReader, used to find the memory address of a specific value, and read it henceforth.

        Args:
            c_type (_type_): The c_types type to search for.
            p_id (int, optional): The process id. Defaults to None.
            p_name (str, optional): _description_. Defaults to None.
            process (Process, optional): In case of using multiple MemoryReaders, pass the reference here. Defaults to None.
        """
        if not process:
            if p_id:
                self.process_id = p_id
            else:
                self.process_id = Process.get_pid_by_name(p_name)

            self.process: Process = Process(self.process_id)
        else:
            self.process = process
        self.addresses = []
        self.buffer = None

        self.current_type = None

    @staticmethod
    def get_process_id(process_name: str) -> List[int]:
        """Gets the process ids of the process with the given name.

        Args:
            process_name (str): The name of the process.

        Returns:
            int: The process id.
        """
        pids = []
        for proc in psutil.process_iter():
            if proc.name() == process_name:
                pids.append(proc.pid)

        return pids
    
    @staticmethod
    def _value_to_ctype(value: Union[int, str, float, bytearray]):
        """Converts the value to its ctype counterpart for searching in the memory.

        Args:
            value (_type_): The value to convert.

        Returns:
            _type_: A ctype object containing the value.
        """
        if type(value) == str:
            b = bytearray()
            b.extend(value.encode("ascii"))
            # Print the bytearray as a string of hex values.
            print(" ".join("{:02x}".format(x) for x in b))

            return (ctypes.c_char * len(b)).from_buffer(b)
        elif type(value) == bytearray:
            return (ctypes.c_char * len(value)).from_buffer(value)
        elif type(value) == int:
            if abs(value) <= 2147483647:
                return ctypes.c_long(value)
            else:
                return ctypes.c_long(value)
        elif type(value) == float:
            return ctypes.c_float(value)

    def filter_value(self, value: Union[int, str, float, bytearray], buffer = None) -> List[int]:
        """Search for the specified value in the currently filtered memory.

        Args:
            value (Union[int, str, float]): The value to search for.
            buffer (_type_, optional): Optionally, the ctypes type to use. If none is provided, 
                it is attempted to derive it from the value. Defaults to None.

        Returns:
            List[int]: The memory addresses found which match the filter.
        """
        if buffer:
            self.buffer = buffer
        else:
            self.buffer = MemoryReader._value_to_ctype(value)

        if self.addresses:
            self.addresses = self.process.search_addresses(self.addresses, self.buffer)
        else:
            self.addresses = self.process.search_all_memory(self.buffer, False)

        self.current_type = type(value)

        return self.addresses[:]

    def reset_filter(self):
        """Resets the addresses which are used to search values. Essentially starts searching anew.
        """
        self.addresses = []

    def read_values(self, full_string: bool = False) -> List[Union[int, str, float]]:
        """Returns the values found at self.addresses in the memory.
        
        Args:
            full_string (bool): If the buffer is a string, whether to attempt to read the entire string at the memory address, 
                or only starting at the memory address and using the current buffer length.

        Returns:
            List[Union[int, str, float]]: A list with the address values.
        """
        values = []

        for address in self.addresses:
            starting_address = address

            # Allow reading bigger strings than the initial value.
            if self.current_type == str:
                if full_string:
                    raw_value = (ctypes.c_byte * 1024)()

                    # Continue string to the left until null byte.
                    while True:
                        self.process.read_memory(starting_address - 1024, raw_value)

                        terminal_position = -1
                        try:
                            terminal_position = bytes(raw_value).rindex(0)
                        except Exception:
                            pass

                        if terminal_position > -1:
                            starting_address -= 1024 - terminal_position - 1
                            break
                        else:
                            starting_address -= 1024

                b = bytearray(address - starting_address + 2048)
                self.buffer = (ctypes.c_char * (address - starting_address + 2048)).from_buffer(b)

            self.process.read_memory(starting_address, self.buffer)

            if self.current_type == bytearray:
                values.append("".join("{:02x}".format(ord(x)) for x in self.buffer))
            else:
                values.append(self.buffer.value)

        return values
    
    def write_values(self, value: Union[int, str, float, bytearray]) -> None:
        """Writes the value to the addresses in the memory.

        Args:
            value (Union[int, str, float]): The value to write.
        """
        for address in self.addresses:
            self.process.write_memory(address, MemoryReader._value_to_ctype(value))

    def get_context(self, address: int, context_length: int = 15) -> Dict[int, ctypes.c_byte]:
        """Returns the context of the address in the memory.

        Args:
            address (int): The address to get the context for.
            context_length (int, optional): The length of the context to return. Defaults to 15.

        Returns:
            str: The context of the address.
        """
        context = {}

        for i in range(address - context_length, address + context_length + 1):
            context[i] = self.process.read_memory(i, ctypes.c_ubyte())

        return context

    def write_values(self, value: Union[int, str, float]) -> Dict[int, Union[int, str, float]]:
        """Writes the value to all currently saved addresses.
        """
        value = MemoryReader._value_to_ctype(value)

        for address in self.addresses:
            self.process.write_memory(address, value)