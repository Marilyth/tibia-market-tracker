from scapy.all import sniff, Packet, AsyncSniffer, Raw
from typing import Callable
import sys


class PacketSniffer:
    def __init__(self, port: int = 7171, interface = "nordlynx"):
        self.port = port
        self.interface = interface

    def sniff(self, callback: Callable[[Packet], None]):
        AsyncSniffer(
            prn=callback,
            iface=self.interface,
            filter=f"dst port {self.port} or src port {self.port}",
        ).start()

if __name__ == "__main__":
    sniffer = PacketSniffer(port=int(sys.argv[1]))
    sniffer.sniff(lambda p: print(f"{p.summary()}: {p[Raw].load if Raw in p else 'None'}"))
    import time
    while True:
        time.sleep(1)
        pass