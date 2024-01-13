from scapy.all import *
import time
import traceback
from threading import Lock
from utils.waiter import wait_until


class TCPReassembler:
    FIN = 0x01
    SYN = 0x02
    RST = 0x04
    PSH = 0x08
    ACK = 0x10
    URG = 0x20
    ECE = 0x40
    CWR = 0x80

    def __init__(self):
        """Initialises a TCPReassembler.
        """
        self.queue = {}
        self.output = None
        self.queue_lock = Lock()
        self.new_data_callback = None

    def set_new_data_callback(self, callback: Callable[[Packet], None]):
        """Sets the callback function to be called when new data is received.

        Args:
            callback (Callable[[Packet], None]): The callback function.
        """
        self.new_data_callback = callback

    def get_next_packet(self, source: str, timeout: int = 60) -> Optional[Packet]:
        """Returns the next packet of the TCP stream.

        Args:
            timeout (int, optional): The timeout in seconds. Defaults to 60.

        Returns:
            Optional[Packet]: The next packet of the TCP stream.
        """
        if source not in self.queue:
            raise Exception(f"Source {source} not found in queue.")

        if len(self.output_queue) == 0:
            wait_until(lambda: len(self.output_queue) > 0, timeout=timeout)
        
        return self.output_queue.pop(0)

    def add_to_queue(self, packet: Packet):
        """Adds a packet to the queue.

        Args:
            packet (Packet): The packet to add.
        """
        try:
            packet_src = packet['IP'].src
            packet_src_port = packet['TCP'].sport
            packet_src = f"{packet_src}:{packet_src_port}"
            packet_seq = packet['TCP'].seq
            packet_load = len(packet[Raw].load) if Raw in packet else 0
            packet_flag = packet['TCP'].flags

            self.queue_lock.acquire()

            try:
                if packet_src not in self.queue:
                    self.queue[packet_src] = {"current_seq": packet_seq, "packets": {packet_seq: (packet, time.time())}}
                else:
                    self.queue[packet_src]["packets"][packet_seq] = (packet, time.time())
                
                # Get all packets in the queue, which are in order of seq.
                for seq, (packet, timestamp) in sorted(self.queue[packet_src]["packets"].items()):
                    packet_length = len(packet[Raw].load) if Raw in packet else 0
                    packet_flags = packet["TCP"].flags
                    
                    # If the packet is smaller than the current sequence, it is a retransmission.
                    if seq < self.queue[packet_src]["current_seq"]:
                        if seq + packet_length > self.queue[packet_src]["current_seq"]:
                            # There is new data in a retransmission. Extract the new data.
                            packet[Raw].load = packet[Raw].load[self.queue[packet_src]["current_seq"] - seq:]
                            packet_length = len(packet[Raw].load) if Raw in packet else 0

                            # Remove the packet from the queue.
                            del self.queue[packet_src]["packets"][seq]

                            # Update sequence number.
                            self.queue[packet_src]["current_seq"] += packet_length

                            if self.new_data_callback:
                                self.new_data_callback(packet)
                    
                    # If the packet seq is equal to the current sequence, it is the next packet in the sequence.
                    elif seq == self.queue[packet_src]["current_seq"]:
                        self.queue[packet_src]["current_seq"] += packet_length

                        # If the packet is a SYN packet, add 1 to the sequence number.
                        if packet_flags & self.SYN:
                            self.queue[packet_src]["current_seq"] += 1

                        # Remove the packet from the queue.
                        del self.queue[packet_src]["packets"][seq]
                        
                        # Add the packet to the output queue.
                        if self.new_data_callback:
                            self.new_data_callback(packet)
                
                    # Clean up all packets with timestamp older than 30 seconds.
                    else:
                        if time.time() - timestamp > 30:
                            del self.queue[packet_src]["packets"][seq]
            except Exception as e:
                # Print stacktrace
                traceback.print_exc()
                print(f"Error while reading packet queue: {e}")
            finally:
                self.queue_lock.release()
            
        except Exception as e:
            # Print stacktrace
            traceback.print_exc()
            print(f"Error while reading packet: {e}")
        