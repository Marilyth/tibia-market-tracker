import ctypes
import subprocess
import os
import logging
from typing import List
from utils.extraction.memory.memory_reader import MemoryReader


logger = logging.getLogger(__name__)


class XteaDebugger:
    def __init__(self):
        self.process_id = MemoryReader.get_process_id("client")[-1]
        self.breakpoint_address = None

    def find_key_by_anchor(self) -> List[int]:
        """Find the XTEA key by using an anchor in memory.
        Returns the key as a list of integers.
        """
        # The key appears twice exactly 160 bytes apart.
        # 8 bytes after both appearances, this bytearray begins consistently as of 25.09.2026.
        # There are not many matches either way so maybe get rid of the 160 byte check and try them all.
        anchor = bytearray.fromhex("ffffffffffffff3f0400000000000000")
        memory_reader = MemoryReader(self.process_id)

        keys = None
        addresses = memory_reader.filter_value(anchor)
        for i in range(len(addresses)):
            if i == 0:
                continue

            if addresses[i] - addresses[i - 1] == 160:
                # 8 bytes are unknown, 16 bytes are for the key.
                key_address = addresses[i] - (8 + 16)
                raw = bytes(memory_reader.process.read_memory(key_address, (ctypes.c_byte * 16)()))

                keys = [int.from_bytes(raw[i:i+4], "little") for i in range(0, 16, 4)]
                logger.info(f"Potential key: {keys}")

        memory_reader.process.close()

        if not keys:
            raise ValueError("No potential XTEA keys found.")

        # Write key to file for debugging purposes.
        with open("key.txt", "w") as f:
            f.write(",".join([str(k) for k in keys]))
            
        return keys

    def find_breakpoint_address(self) -> str:
        """Find the breakpoint address of the XTEA encryption function.
        This is done by finding the magic number 0x61c88647 in the executable.
        """
        # Look for the xtea decryption code using the magic number 0x61c88647 in memory.
        # The client used to be in memory with an offset of 0, but that changed since the new client.
        # Now this code needs to be searched.
        memory_reader = MemoryReader(self.process_id)
        xtea_code = bytearray.fromhex("89cac1e20431da01c62d4786c861") # As of 12.09.2024. Check assembly if changed.

        address = memory_reader.filter_value(xtea_code)[0]
        memory_reader.process.close()

        # Convert to hex for gdb.
        self.breakpoint_address = hex(address)
        logger.info(f"Found breakpoint address: {self.breakpoint_address}")

    def find_key_by_debugger(self) -> List[int]:
        """Attach gdb to the process self.process_id and set a breakpoint at the address self.breakpoint_address.
        Prints 128 bits out of the $rdi address.
        Keep in mind this will get you banned. Use a sacrificial lamb account for anchor extraction.
        Returns the gdb output as a string.
        """
        if not self.breakpoint_address:
            self.find_breakpoint_address()

        logger.debug(self.breakpoint_address)

        file_dir = os.path.dirname(os.path.realpath(__file__))
        gdb_file_directory = os.path.join(file_dir, "gdb_find_xtea")

        command = ["gdb", "-p", str(self.process_id), "-batch",
                         "-ex", f"b *{self.breakpoint_address}",
                         "-x", f"{gdb_file_directory}"]

        gdb_output = subprocess.check_output(command).decode("utf-8")
        logger.debug(f"{gdb_output=}")
        keys = [key for key in gdb_output.split(":\t")[1].split("\n")[0].split("\t") if key]

        # Keys are in 0x00 format, convert to bytes.
        keys = [int(key, 16) for key in keys]

        # Write key to file for debugging purposes.
        with open("key.txt", "w") as f:
            f.write(",".join([str(k) for k in keys]))

        logger.info(f"Found key: {keys}")

        # Log the context around the key in memory for anchor analysis.
        key_bytes = bytearray(b"".join([k.to_bytes(4, "little") for k in keys]))

        memory_reader = MemoryReader(self.process_id)
        addresses = memory_reader.filter_value(key_bytes)
        logger.info(f"Addresses for full key: {addresses}")
        logger.info(f"Key bytes: {key_bytes.hex()}")

        for address in addresses:
            logger.info(f"Address for context: {address}")
            context = memory_reader.get_context(address, 1500)
            expression = "".join([f"{byte.value:02x}" for byte in context.values()])
            logger.info(f"Context around key: {expression}")

        memory_reader.process.close()

        return keys
