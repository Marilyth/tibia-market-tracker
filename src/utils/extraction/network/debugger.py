import subprocess
import os
from typing import List


class XteaDebugger:
    def __init__(self, process_id: int):
        self.process_id = process_id
        self.breakpoint_address = None
    
    def find_breakpoint_address(self) -> str:
        """Find the breakpoint address of the XTEA encryption function.
        This is done by finding the magic number 0x61c88647 in the executable.
        """
        file_location = os.path.join("/", "root", ".local", "share", "CipSoft GmbH", "Tibia", "packages", "Tibia", "bin", "client")

        # Extract the assembly executable of Tibia.
        command = ["objdump", "-M", "intel", "-Sd", file_location]
        objdump_process = subprocess.run(command, capture_output=True)
        stderr = objdump_process.stderr.decode("utf-8")
        
        if stderr:
            raise Exception(f"objdump failed: {stderr}")

        stdout = objdump_process.stdout.decode("utf-8")
        breakpoint_address = None
                
        # Look for the xtea magic number 0x61c88647. There are two of them, the encryption and decryption.
        # Either is fine, since this is a symmetric key.
        for line in stdout.split("\n"):
            if "0x61c88647" in line:
                breakpoint_address = line.split(":")[0].strip()
                # Move breakpoint address 9 bytes back to the instruction after reading in the key.
                breakpoint_address = hex(int(breakpoint_address, 16) - 9)
                break

        self.breakpoint_address = breakpoint_address

    def find_key(self) -> List[int]:
        """Attach gdb to the process self.process_id and set a breakpoint at the address self.breakpoint_address.
        Prints 128 bits out of the $rdi address.
        Returns the gdb output as a string.
        """
        if not self.breakpoint_address:
            self.find_breakpoint_address()

        file_dir = os.path.dirname(os.path.realpath(__file__))
        gdb_file_directory = os.path.join(file_dir, "gdb_find_xtea")

        command = ["gdb", "-p", str(self.process_id), "-batch", 
                         "-ex", f"b *{self.breakpoint_address}",
                         "-x", f"{gdb_file_directory}"]
        
        gdb_output = subprocess.run(command, capture_output=True).stdout.decode("utf-8")
        keys = [key for key in gdb_output.split(":\t")[1].split("\n")[0].split("\t") if key]
        
        # Keys are in 0x00 format, convert to bytes.
        keys = [int(key, 16) for key in keys]

        # Write key to file for debugging purposes.
        with open("key.txt", "w") as f:
            f.write(",".join([str(k) for k in keys]))

        return keys
        