"""Tests for PyDecompressor, CSharpDecompressor, and their parity.

Structure:
  TestProtocol        — both classes satisfy the Decompressor Protocol.
  TestPyDecompressor  — pure Python tests, no external deps.
  TestCSharpVsPython  — feeds the same compressed chunks to both and asserts
                        byte-for-byte identical output.
                        Skipped automatically when dotnet / the DLL is absent.
"""
import zlib
from pathlib import Path

import pytest

from utils.extraction.network.decompressors import CSharpDecompressor, Decompressor, PyDecompressor

_CSHARP_AVAILABLE = Path(CSharpDecompressor._DLL).exists()


# ---------------------------------------------------------------------------
# Helpers — produce raw deflate data the same way Tibia does
# ---------------------------------------------------------------------------

def _sync_chunk(co, data: bytes) -> bytes:
    """One Z_SYNC_FLUSH segment from a shared compressor state (BFINAL=0)."""
    return co.compress(data) + co.flush(zlib.Z_SYNC_FLUSH)


def _finish_chunk(data: bytes) -> bytes:
    """A self-contained Z_FINISH block (BFINAL=1 — independent packet)."""
    co = zlib.compressobj(level=6, method=zlib.DEFLATED, wbits=-15)
    return co.compress(data) + co.flush(zlib.Z_FINISH)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------

class TestProtocol:
    def test_py_decompressor_satisfies_protocol(self):
        assert isinstance(PyDecompressor(), Decompressor)

    @pytest.mark.skipif(not _CSHARP_AVAILABLE, reason="C# decompressor DLL not built")
    def test_csharp_decompressor_satisfies_protocol(self):
        assert isinstance(CSharpDecompressor(), Decompressor)


# ---------------------------------------------------------------------------
# Python-only tests
# ---------------------------------------------------------------------------

class TestPyDecompressor:
    def test_single_packet(self):
        co = zlib.compressobj(level=6, method=zlib.DEFLATED, wbits=-15)
        chunk = _sync_chunk(co, b"hello world")

        result = PyDecompressor().decompress(chunk, "s")

        assert result[2:] == b"hello world"
        assert int.from_bytes(result[:2], "little") == len(b"hello world")

    def test_length_prefix_matches_content(self):
        payload = b"tibia market data " * 100
        co = zlib.compressobj(level=6, method=zlib.DEFLATED, wbits=-15)

        result = PyDecompressor().decompress(_sync_chunk(co, payload), "s")

        assert int.from_bytes(result[:2], "little") == len(result[2:])
        assert result[2:] == payload

    def test_stateful_across_packets(self):
        """chunk2 back-references chunk1 — decompressor must keep context across calls."""
        co = zlib.compressobj(level=6, method=zlib.DEFLATED, wbits=-15)
        chunk1 = _sync_chunk(co, b"first packet")
        chunk2 = _sync_chunk(co, b"second packet")

        d = PyDecompressor()
        assert d.decompress(chunk1, "flow")[2:] == b"first packet"
        assert d.decompress(chunk2, "flow")[2:] == b"second packet"

    def test_five_packet_stream(self):
        co = zlib.compressobj(level=6, method=zlib.DEFLATED, wbits=-15)
        payloads = [f"packet-{i}".encode() for i in range(5)]
        chunks = [_sync_chunk(co, p) for p in payloads]

        d = PyDecompressor()
        for chunk, expected in zip(chunks, payloads, strict=True):
            assert d.decompress(chunk, "flow")[2:] == expected

    def test_stream_end_resets_context(self):
        """After BFINAL=1 the next independent packet must decompress correctly.

        Note: the C# subprocess (ComponentAce) crashes on back-to-back BFINAL=1
        blocks because its inflateEnd()+inflateInit(-15) doesn't fully reset for
        a second Z_FINISH stream. Python's decompressobj handles this correctly.
        """
        d = PyDecompressor()
        assert d.decompress(_finish_chunk(b"packet A"), "flow")[2:] == b"packet A"
        assert d.decompress(_finish_chunk(b"packet B"), "flow")[2:] == b"packet B"

    def test_eof_context_is_deleted(self):
        d = PyDecompressor()
        d.decompress(_finish_chunk(b"done"), "flow")
        assert "flow" not in d._ctx

    def test_separate_senders_independent(self):
        """Two senders with different compressor states must not interfere."""
        co_a = zlib.compressobj(level=6, method=zlib.DEFLATED, wbits=-15)
        co_b = zlib.compressobj(level=6, method=zlib.DEFLATED, wbits=-15)

        d = PyDecompressor()
        assert d.decompress(_sync_chunk(co_a, b"A-first"), "A")[2:] == b"A-first"
        assert d.decompress(_sync_chunk(co_b, b"B-first"), "B")[2:] == b"B-first"
        assert d.decompress(_sync_chunk(co_a, b"A-second"), "A")[2:] == b"A-second"
        assert d.decompress(_sync_chunk(co_b, b"B-second"), "B")[2:] == b"B-second"

    def test_reset_clears_sender(self):
        co = zlib.compressobj(level=6, method=zlib.DEFLATED, wbits=-15)
        d = PyDecompressor()
        d.decompress(_sync_chunk(co, b"x"), "s")
        d.reset("s")
        assert "s" not in d._ctx

    def test_reset_nonexistent_sender_is_noop(self):
        PyDecompressor().reset("does-not-exist")


# ---------------------------------------------------------------------------
# Parity tests: Python == C# (skipped when dotnet / DLL not available)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CSHARP_AVAILABLE, reason="C# decompressor DLL not built")
class TestCSharpVsPython:
    @pytest.fixture(autouse=True)
    def cs(self):
        d = CSharpDecompressor()
        yield d
        for sender in list(d._procs):
            d.reset(sender)

    def _compare(self, chunks: list[bytes], cs: CSharpDecompressor, sender: str = "flow") -> None:
        py = PyDecompressor()
        for i, chunk in enumerate(chunks):
            py_out = py.decompress(chunk, sender)
            cs_out = cs.decompress(chunk, sender)
            assert py_out == cs_out, (
                f"chunk {i}: py={py_out[:16].hex()} cs={cs_out[:16].hex()}"
            )

    def test_single_packet_matches(self, cs):
        co = zlib.compressobj(level=6, method=zlib.DEFLATED, wbits=-15)
        self._compare([_sync_chunk(co, b"hello tibia")], cs)

    def test_five_packet_stream_matches(self, cs):
        co = zlib.compressobj(level=6, method=zlib.DEFLATED, wbits=-15)
        chunks = [_sync_chunk(co, f"packet {i}".encode()) for i in range(5)]
        self._compare(chunks, cs)

    def test_large_payload_matches(self, cs):
        co = zlib.compressobj(level=6, method=zlib.DEFLATED, wbits=-15)
        payload = b"tibia market data " * 300  # ~5 400 bytes, well under C#'s 65536 limit
        self._compare([_sync_chunk(co, payload)], cs)

    def test_separate_senders_match(self, cs):
        co_a = zlib.compressobj(level=6, method=zlib.DEFLATED, wbits=-15)
        co_b = zlib.compressobj(level=6, method=zlib.DEFLATED, wbits=-15)
        py = PyDecompressor()

        for label, co, sender in [("A", co_a, "senderA"), ("B", co_b, "senderB")]:
            for i in range(3):
                chunk = _sync_chunk(co, f"{label}-{i}".encode())
                assert py.decompress(chunk, sender) == cs.decompress(chunk, sender)
