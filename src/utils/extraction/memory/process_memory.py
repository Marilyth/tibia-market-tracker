import errno
import logging


logger = logging.getLogger(__name__)

# Mostly used for testing.
PROC = "/proc"
CHUNK_SIZE = 1024 * 1024


class ProcessMemory:
    def __init__(self, pid, include=None, exclude=None):
        self.pid = pid
        self.include = include
        self.exclude = exclude
        try:
            self.mem = open(f"{PROC}/{pid}/mem", "rb", buffering=0)
        except PermissionError as error:
            raise PermissionError(
                error.errno,
                f"Cannot access process {pid} memory; check Linux ptrace access policy",
            ) from error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _ranges(self):
        ranges = []
        with open(f"{PROC}/{self.pid}/maps", encoding="utf-8") as maps:
            for line in maps:
                fields = line.split(None, 5)
                start, end = (int(value, 16) for value in fields[0].split("-"))
                permissions = fields[1]
                path = fields[5].strip() if len(fields) == 6 else ""
                if permissions[0] != "r":
                    continue

                mapping = (start, end, permissions, path)
                selected = []

                # No include filter means every readable mapping is in scope.
                if self.include is None:
                    selected.append((start, end))
                for selector in self.include or ():
                    if isinstance(selector, tuple):
                        # Address selectors only scan the part overlapping this mapping.
                        low, high = max(start, selector[0]), min(end, selector[1])
                        if low < high:
                            selected.append((low, high))
                    elif self._matches(mapping, selector):
                        selected.append((start, end))

                # Exclusions are applied after includes, so they always take precedence.
                for selector in self.exclude or ():
                    if not isinstance(selector, tuple):
                        if self._matches(mapping, selector):
                            selected = []
                            break
                        continue

                    low, high = selector
                    remaining = []
                    for left, right in selected:
                        if high <= left or low >= right:
                            remaining.append((left, right))
                        else:
                            if left < low:
                                remaining.append((left, low))
                            if high < right:
                                remaining.append((high, right))
                    selected = remaining
                ranges.extend(selected)

        # Merge overlapping selectors so the same memory is never scanned twice.
        ranges.sort()
        merged = []
        for start, end in ranges:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return merged

    @staticmethod
    def _matches(mapping, selector):
        _, _, permissions, path = mapping
        if selector == "heap":
            return path == "[heap]"
        if selector == "executable":
            return "x" in permissions
        raise ValueError(f"Unknown memory mapping: {selector}")

    def scan(self, pattern: bytes):
        if not pattern:
            raise ValueError("pattern must not be empty")

        addresses = []
        # Keep enough bytes from the previous chunk to match across chunk boundaries.
        overlap = len(pattern) - 1
        for start, end in self._ranges():
            position = start
            previous = b""
            while position < end:
                size = min(CHUNK_SIZE, end - position)
                try:
                    chunk = self._read_at(position, size)
                except OSError as error:
                    # Maps can change while scanning; skip the rest of this range.
                    logger.warning("Skipping unreadable memory at %#x: %s", position, error)
                    break
                if not chunk:
                    break

                data = previous + chunk
                base = position - len(previous)
                match = data.find(pattern)
                while match >= 0:
                    addresses.append(base + match)
                    # Advance one byte so overlapping matches are retained.
                    match = data.find(pattern, match + 1)

                previous = data[-overlap:] if overlap else b""
                position += len(chunk)
                if len(chunk) < size:
                    # Don't bridge a partial read as though its missing bytes were contiguous.
                    break
        return addresses

    def read(self, address: int, size: int) -> bytes:
        if size < 0:
            raise ValueError("size must be non-negative")
        data = self._read_at(address, size)
        if len(data) != size:
            raise OSError(errno.EIO, f"Short read at {address:#x}: expected {size} bytes, got {len(data)}")
        return data

    def _read_at(self, address, size):
        self.mem.seek(address)
        return self.mem.read(size)

    def close(self):
        if not self.mem.closed:
            self.mem.close()
