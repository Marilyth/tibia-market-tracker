import zlib


class Decompressor:
    """Stateful raw deflate decompressor.

    One ``zlib.decompressobj(wbits=-15)`` per sender so deflate back-references
    span packet boundaries.
    """

    def __init__(self) -> None:
        self._ctx: dict[str, zlib.Decompress] = {}

    def decompress(self, data: bytes, sender: str) -> bytes:
        # Z_SYNC_FLUSH is stripped by CipSoft. Add it back.
        data += b'\x00\x00\xff\xff'

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
