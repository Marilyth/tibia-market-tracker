from utils.data.market_values import ItemMetaData
from utils.extraction.network.packets.packet_base import PacketBase


class MarketDetail(PacketBase):
    def __init__(self):
        super().__init__(from_client=False)

        self.id: int
        self.tier: int = 0
        self.details: list[str]
        self.buy_history: list[HistoryPacketValue] = []
        self.sell_history: list[HistoryPacketValue] = []

    def from_packet(self, packet: bytes) -> 'MarketDetail':
        super().from_packet(packet)
        self._read_packet()

        return self

    def _read_packet(self):
        """Reads a market packet, and saves the result to self.result.
        """
        self._read_header()
        self._read_details()
        self._read_statistics()

    def _read_header(self):
        """Reads the header of a market packet.
        """
        self.id = self.read_short()

        meta_data = ItemMetaData(id=self.id)
        meta_data.load_from_proto()

        if meta_data > -1:
            self.tier = self.read_byte()

    def _read_details(self):
        """Reads the details of a market packet. I.e. it's description, etc.
        """
        self.details = []

        # Go through each category. The amount can change every update.
        for _ in range(26):
            self.details.append(self.read_prefixed_string())

    def _read_statistics(self):
        """Reads the statistics of a market packet. I.e. it's daily sell/buy history.
        """
        def read_history(length: int) -> list[HistoryPacketValue]:
            history = []

            for i in range(length):
                amount_traded = self.read_int()
                total_gold = self.read_long()
                max_price = self.read_long()

                # Min_price is set to FFFFFFFFFFFFFFFF in packet if there were no trades.
                min_price = self.read_long()
                if amount_traded == 0:
                    min_price = 0

                history_value = HistoryPacketValue(amount_traded, total_gold, max_price, min_price)
                history.append(history_value)

            return history

        # History goes from recent to old.
        buy_history_length = self.read_byte()
        self.buy_history.extend(read_history(buy_history_length))

        sell_history_length = self.read_byte()
        self.sell_history.extend(read_history(sell_history_length))


class HistoryPacketValue:
    def __init__(self, traded: int, total_gold: int, max_price: int, min_price: int):
        self.traded = traded
        self.total_gold = total_gold
        self.max_price = max_price
        self.min_price = min_price
        self.average_price = total_gold / traded if traded > 0 else 0
