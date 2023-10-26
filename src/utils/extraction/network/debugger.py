import subprocess
import os
from typing import List


class XteaDebugger:
    def __init__(self, process_id: int, breakpoint_address: str = "0xd4990d"):
        self.process_id = process_id
        self.breakpoint_address = breakpoint_address
    
    def find_key(self) -> List[int]:
        """Attach gdb to the process self.process_id and set a breakpoint at the address self.breakpoint_address.
        Prints 128 bits out of the $rdi address.
        Returns the gdb output as a string.
        """
        file_dir = os.path.dirname(os.path.realpath(__file__))
        gdb_file_directory = os.path.join(file_dir, "gdb_find_xtea")

        command = ["gdb", "-p", str(self.process_id), "-batch", 
                         "-ex", f"b *{self.breakpoint_address}",
                         "-x", f"{gdb_file_directory}"]
        
        gdb_output = subprocess.run(command, capture_output=True).stdout.decode("utf-8")
        keys = [key for key in gdb_output.split(":\t")[1].split("\n")[0].split("\t") if key]

        print(keys)
        
        # Keys are in 0x00 format, convert to bytes.
        keys = [int(key, 16) for key in keys]

        return keys
        

# Check executable of Tibia with
# objdump -M intel -Sd .local/share/CipSoft\ GmbH/Tibia/packages/Tibia/bin/client

# In it, you can find the XTEA magic number 0x61c88647
# | grep -C 5 61c88647
#   d4990a:	8b 34 97             	mov    esi,DWORD PTR [rdi+rdx*4]
#   d4990d:	89 ca                	mov    edx,ecx
#   d4990f:	c1 e2 04             	shl    edx,0x4
#   d49912:	31 da                	xor    edx,ebx
#   d49914:	01 c6                	add    esi,eax
#   d49916:	2d 47 86 c8 61       	sub    eax,0x61c88647

# In this case, d4990a loads part of the XTEA key into esi.
