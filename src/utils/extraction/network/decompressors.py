"""Stateful raw-deflate decompressors for Tibia TCP flows.

Both implementations share the ``Decompressor`` Protocol so NetworkSniffer can
use either without any other code change.

Output format (both classes): 2-byte little-endian length prefix + raw
decompressed bytes — callers strip with ``[2:]`` to get the payload.
"""
import os
import subprocess
import time
import zlib
from typing import Protocol, runtime_checkable


@runtime_checkable
class Decompressor(Protocol):
    def decompress(self, data: bytes, sender: str) -> bytes: ...
    def reset(self, sender: str) -> None: ...


class CSharpDecompressor:
    """Stateful raw deflate decompressor backed by the C# decompressor subprocess.

    One dotnet subprocess per sender key so each TCP flow keeps its own ZStream
    context — the same guarantee that ``self.decompressor`` dict provided in
    NetworkSniffer before this class existed.
    """

    _DLL = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "..",
            "decompressor", "bin", "Debug", "net8.0", "decompressor.dll",
        )
    )

    def __init__(self) -> None:
        self._procs: dict[str, subprocess.Popen] = {}

    @staticmethod
    def _to_hex(data: bytes) -> str:
        return " ".join(f"0x{b:02x}" for b in data)

    def decompress(self, data: bytes, sender: str) -> bytes:
        if not data:
            raise ValueError("decompress: empty payload")

        data_str = self._to_hex(data)

        if sender not in self._procs or self._procs[sender].poll() is not None:
            self._procs[sender] = subprocess.Popen(
                ["dotnet", self._DLL],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
            )
            os.set_blocking(self._procs[sender].stdout.fileno(), False)
            os.set_blocking(self._procs[sender].stderr.fileno(), False)

        try:
            self._procs[sender].stdin.write(data_str.encode() + b"\n")
            self._procs[sender].stdin.flush()

            response = b""
            while not response or response[-1] != 10:  # 10 == ord('\n')
                chunk = self._procs[sender].stdout.read()
                if chunk:
                    response += chunk
                time.sleep(0.01)

            response = response.decode().strip()

            if not all(c in "0123456789abcdefABCDEF \n" for c in response):
                raise RuntimeError(f"CSharpDecompressor error: {response}")

            return bytes(int(x, 16) for x in response.split())

        except Exception:
            try:
                self._procs[sender].kill()
            except Exception:
                pass
            del self._procs[sender]
            raise

    def reset(self, sender: str) -> None:
        proc = self._procs.pop(sender, None)
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass


class PyDecompressor:
    """Stateful raw deflate decompressor — Python-native, no subprocess.

    One ``zlib.decompressobj(wbits=-15)`` per sender so deflate back-references
    span packet boundaries, matching the ZStream behaviour in the C# version.
    """

    def __init__(self) -> None:
        self._ctx: dict[str, zlib.Decompress] = {}

    def decompress(self, data: bytes, sender: str) -> bytes:
        if sender not in self._ctx:
            self._ctx[sender] = zlib.decompressobj(wbits=-15)

        try:
            result = self._ctx[sender].decompress(data)
        except zlib.error:
            # Context exhausted or corrupted — reset and retry.
            self._ctx[sender] = zlib.decompressobj(wbits=-15)
            result = self._ctx[sender].decompress(data)

        # BFINAL=1: stream ended — reset so the next packet starts fresh,
        # mirroring inflateEnd()+inflateInit(-15) in the C# code.
        if self._ctx[sender].eof:
            del self._ctx[sender]

        return len(result).to_bytes(2, "little") + result

    def reset(self, sender: str) -> None:
        self._ctx.pop(sender, None)
