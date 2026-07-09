import zlib

from utils.extraction.network.decompressors import Decompressor


class TestDecompressor:
    def setup_method(self):
        self.decompressor = Decompressor()

    def raw_deflate(self, data: bytes) -> bytes:
        compressor = zlib.compressobj(wbits=-15)
        return compressor.compress(data) + compressor.flush()

    def unwrap(self, data: bytes) -> bytes:
        return data[2:]

    def test_decompresses_data(self):
        compressed = self.raw_deflate(b"hello")

        result = self.decompressor.decompress(compressed, "sender")

        assert self.unwrap(result) == b"hello"

    def test_keeps_context_per_sender(self):
        compressor = zlib.compressobj(wbits=-15)

        first = compressor.compress(b"hello ")
        first += compressor.flush(zlib.Z_SYNC_FLUSH)[:-4]

        second = compressor.compress(b"world")
        second += compressor.flush()

        assert self.unwrap(
            self.decompressor.decompress(first, "sender")
        ) == b"hello "

        assert self.unwrap(
            self.decompressor.decompress(second, "sender")
        ) == b"world"

    def test_reset_clears_sender_state(self):
        compressed = self.raw_deflate(b"hello")

        self.decompressor.decompress(compressed, "sender")

        self.decompressor.reset("sender")

        assert "sender" not in self.decompressor._ctx
