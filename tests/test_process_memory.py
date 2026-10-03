import os
import struct

import pytest

from utils.extraction.memory import process_memory
from utils.extraction.memory.memory_reader import MemoryReader
from utils.extraction.memory.process_memory import ProcessMemory


PID = 321
MAPS = """\
00001000-00001020 rw-p 00000000 00:00 0 [heap]
00002000-00002020 r-xp 00000000 08:01 123 /bin/client
00003000-00003020 rw-p 00000000 00:00 0
00004000-00004020 ---p 00000000 00:00 0
"""


@pytest.fixture
def proc(tmp_path, monkeypatch):
    directory = tmp_path / str(PID)
    directory.mkdir()
    (directory / "maps").write_text(MAPS)
    (directory / "mem").write_bytes(bytes(0x5000))
    monkeypatch.setattr(process_memory, "PROC", str(tmp_path))
    return tmp_path


def put(proc, address, data):
    with (proc / str(PID) / "mem").open("r+b") as memory:
        memory.seek(address)
        memory.write(data)


def test_scans_readable_mappings_and_matches_across_chunks(proc, monkeypatch):
    put(proc, 0x1000, b"aaaaaa")
    monkeypatch.setattr(process_memory, "CHUNK_SIZE", 4)
    memory = ProcessMemory(PID, include={"heap"})
    try:
        assert memory.scan(b"aaa") == [0x1000, 0x1001, 0x1002, 0x1003]
        assert memory._ranges() == [(0x1000, 0x1020)]
    finally:
        memory.close()


def test_include_and_exclude_accept_classes_and_ranges(proc):
    memory = ProcessMemory(
        PID,
        include={"heap", "executable", (0x3000, 0x3010)},
        exclude={"executable", (0x1008, 0x100C)},
    )
    try:
        assert memory._ranges() == [(0x1000, 0x1008), (0x100C, 0x1020), (0x3000, 0x3010)]
    finally:
        memory.close()


def test_default_uses_every_readable_mapping(proc):
    memory = ProcessMemory(PID)
    try:
        assert memory._ranges() == [(0x1000, 0x1020), (0x2000, 0x2020), (0x3000, 0x3020)]
    finally:
        memory.close()

    memory = ProcessMemory(PID, include={"executable"})
    try:
        assert memory._ranges() == [(0x2000, 0x2020)]
    finally:
        memory.close()


def test_memory_reader_filters_and_returns_raw_bytes(proc):
    put(proc, 0x1000, struct.pack("@l", 123))
    put(proc, 0x1010, struct.pack("@l", 123))
    memory = ProcessMemory(PID)
    reader = MemoryReader(process=memory)
    try:
        assert reader.filter_value(struct.pack("@l", 123)) == [0x1000, 0x1010]
        put(proc, 0x1010, struct.pack("@l", 9))
        assert reader.filter_value(struct.pack("@l", 123)) == [0x1000]
        assert reader.read_values() == [struct.pack("@l", 123)]
        assert reader.read_bytes(0x1000, 8) == struct.pack("@l", 123)
    finally:
        reader.close()


def test_reads_exact_bytes_and_rejects_short_reads_and_empty_patterns(proc):
    memory = ProcessMemory(PID)
    try:
        with pytest.raises(ValueError, match="must not be empty"):
            memory.scan(b"")
        with pytest.raises(OSError, match="Short read"):
            memory.read(0x6000, 1)
    finally:
        memory.close()


def test_process_and_reader_with_blocks_close_their_owned_handle(proc):
    with ProcessMemory(PID) as process:
        fd = process.mem.fileno()
        with MemoryReader(process=process) as reader:
            assert reader.process is process
        os.fstat(fd)
    with pytest.raises(OSError):
        os.fstat(fd)

    reader = MemoryReader(PID)
    fd = reader.process.mem.fileno()
    with reader:
        assert reader.process.mem.fileno() == fd
    with pytest.raises(OSError):
        os.fstat(fd)

    with pytest.raises(RuntimeError):
        with ProcessMemory(PID) as process:
            fd = process.mem.fileno()
            raise RuntimeError("test cleanup")
    with pytest.raises(OSError):
        os.fstat(fd)


def test_scan_skips_mapping_that_becomes_unreadable(proc, monkeypatch):
    put(proc, 0x1000, b"hit!hit!")
    memory = ProcessMemory(PID, include={"heap"})
    read_at = memory._read_at

    def fail_after_first_chunk(address, size):
        if address == 0x1004:
            raise OSError("mapping became unreadable")
        return read_at(address, size)

    monkeypatch.setattr(process_memory, "CHUNK_SIZE", 4)
    monkeypatch.setattr(memory, "_read_at", fail_after_first_chunk)
    try:
        assert memory.scan(b"hit!") == [0x1000]
    finally:
        memory.close()
