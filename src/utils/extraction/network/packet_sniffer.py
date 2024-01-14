from scapy.all import sniff, Packet, AsyncSniffer, Raw, wrpcap
from typing import Callable
import sys


class PacketSniffer:
    def __init__(self, port: int = 7171, interface = "nordlynx", record: bool = False):
        self.port = port
        self.interface = interface
        self.record = record
        self.callback = None

        if record:
            # Clear the recording file.
            open("recording.pcap", "w+").close()

    def _callback(self, packet: Packet):
        if self.record:
            wrpcap("recording.pcap", packet, append=True)

        if self.callback:
            self.callback(packet)

    def sniff(self, callback: Callable[[Packet], None] = None, pcap: str = None, sniff_async: bool = True):
        self.callback = callback

        if sniff_async:
            AsyncSniffer(
                prn=self._callback,
                iface=self.interface,
                offline=pcap,
                # Sniff TCP packets on the specified port.
                filter=f"tcp and (dst port {self.port} or src port {self.port} or dst port 7172 or src port 7172)",
            ).start()
        else:
            sniff(
                prn=self._callback,
                iface=self.interface,
                offline=pcap,
                # Sniff TCP packets on the specified port.
                filter=f"tcp and (dst port {self.port} or src port {self.port} or dst port 7172 or src port 7172)",
            )

if __name__ == "__main__":
    sniffer = PacketSniffer(port=int(sys.argv[1]))
    sniffer.sniff(lambda p: print(f"{p.summary()}: {p[Raw].load if Raw in p else 'None'}"))
    import time
    while True:
        time.sleep(1)
        pass