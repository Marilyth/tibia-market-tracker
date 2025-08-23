import subprocess
import os
from typing import List
from utils.extraction.memory.memory_reader import MemoryReader


class XteaDebugger:
    def __init__(self):
        self.process_id = MemoryReader.get_process_id("client")[-1]
        self.breakpoint_address = None

    def find_breakpoint_address(self) -> str:
        """Find the breakpoint address of the XTEA encryption function.
        This is done by finding the magic number 0x61c88647 in the executable.
        """
        # Look for the xtea decryption code using the magic number 0x61c88647 in memory.
        # The client used to be in memory with an offset of 0, but that changed since the new client.
        # Now this code needs to be searched.
        memory_reader = MemoryReader(self.process_id)
        xtea_raw_code = "89cac1e20431da01c62d4786c861" # As of 12.09.2024. Check assembly if changed.
        xtea_code = bytearray()

        for i in range(0, len(xtea_raw_code), 2):
            xtea_code.append(int(xtea_raw_code[i:i+2], 16))

        address = memory_reader.filter_value(xtea_code)[0]
        memory_reader.process.close()

        # Convert to hex for gdb.
        self.breakpoint_address = hex(address)

    def find_key(self) -> List[int]:
        """Attach gdb to the process self.process_id and set a breakpoint at the address self.breakpoint_address.
        Prints 128 bits out of the $rdi address.
        Returns the gdb output as a string.
        """
        if not self.breakpoint_address:
            self.find_breakpoint_address()

        print(self.breakpoint_address)

        file_dir = os.path.dirname(os.path.realpath(__file__))
        gdb_file_directory = os.path.join(file_dir, "gdb_find_xtea")

        command = ["gdb", "-p", str(self.process_id), "-batch",
                         "-ex", f"b *{self.breakpoint_address}",
                         "-x", f"{gdb_file_directory}"]

        gdb_output = subprocess.check_output(command).decode("utf-8")
        print(f"{gdb_output=}")
        keys = [key for key in gdb_output.split(":\t")[1].split("\n")[0].split("\t") if key]

        # Keys are in 0x00 format, convert to bytes.
        keys = [int(key, 16) for key in keys]

        # Write key to file for debugging purposes.
        with open("key.txt", "w") as f:
            f.write(",".join([str(k) for k in keys]))

        return keys
