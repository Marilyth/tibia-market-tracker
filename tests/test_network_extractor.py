import asyncio
import os

os.environ.setdefault("DISPLAY", ":0")

from types import SimpleNamespace

from utils.extraction.network import network_extractor
from utils.extraction.network.network_extractor import NetworkExtractor
from utils.extraction.network.network_sniffer import NetworkSniffer


def test_read_batch_uses_observed_client_ids(monkeypatch):
    pressed = []

    class FakeSniffer:
        client_market_browse_ids = list(range(12))

        def has_result(self, item_id):
            return True

        def pop_result(self, item_id):
            return SimpleNamespace(id=item_id), SimpleNamespace(id=item_id)

    async def no_wait(*args, **kwargs):
        pass

    monkeypatch.setattr(network_extractor.pyautogui, "press", lambda key: pressed.append(key))
    monkeypatch.setattr(network_extractor, "wait_like_human_async", no_wait)

    extractor = NetworkExtractor.__new__(NetworkExtractor)
    extractor.sniffer = FakeSniffer()
    extractor._category_item_ids = []

    item_ids, results, finished = asyncio.run(extractor._read_batch(12))

    assert pressed == ["down"] * 12
    assert item_ids == list(range(12))
    assert set(results) == set(range(12))
    assert not finished


def test_read_batch_stops_when_the_market_selection_repeats(monkeypatch):
    class FakeSniffer:
        def has_result(self, item_id):
            return True

        def pop_result(self, item_id):
            return SimpleNamespace(id=item_id), SimpleNamespace(id=item_id)

    async def no_wait(*args, **kwargs):
        pass

    monkeypatch.setattr(network_extractor.pyautogui, "press", lambda key: None)
    monkeypatch.setattr(network_extractor, "wait_like_human_async", no_wait)

    extractor = NetworkExtractor.__new__(NetworkExtractor)
    extractor.sniffer = FakeSniffer()
    extractor._category_item_ids = []
    observed_ids = iter([10, 11, None, 10, 11])

    async def fake_wait_for_client_browse():
        return next(observed_ids)

    extractor._wait_for_client_browse = fake_wait_for_client_browse

    item_ids, results, finished = asyncio.run(extractor._read_batch(12))

    assert item_ids == [10, 11]
    assert set(results) == {10, 11}
    assert finished


def test_read_batch_uses_previous_batch_item_at_category_boundary(monkeypatch):
    class FakeSniffer:
        def has_result(self, item_id):
            return True

        def pop_result(self, item_id):
            return SimpleNamespace(id=item_id), SimpleNamespace(id=item_id)

    async def no_wait(*args, **kwargs):
        pass

    monkeypatch.setattr(network_extractor.pyautogui, "press", lambda key: None)
    monkeypatch.setattr(network_extractor, "wait_like_human_async", no_wait)

    extractor = NetworkExtractor.__new__(NetworkExtractor)
    extractor.sniffer = FakeSniffer()
    extractor._category_item_ids = [41]
    observed_ids = iter([42, None, 41, 42])

    async def fake_wait_for_client_browse():
        return next(observed_ids)

    extractor._wait_for_client_browse = fake_wait_for_client_browse

    item_ids, results, finished = asyncio.run(extractor._read_batch(12))

    assert item_ids == [42]
    assert set(results) == {42}
    assert finished


def test_sniffer_parses_packet_in_callback(monkeypatch):
    import utils.extraction.network.network_sniffer as network_sniffer

    monkeypatch.setattr(network_sniffer, "is_ready", lambda: True)
    sniffer = NetworkSniffer()
    parsed = []

    sniffer._handle_packet = lambda flow, packet: parsed.append((flow, packet))
    flow, packet = object(), object()
    sniffer.handle_packet(flow, packet)

    assert parsed == [(flow, packet)]


def test_sniffer_pop_result_consumes_complete_result():
    sniffer = NetworkSniffer()
    expected = (object(), object())
    sniffer.results[123] = expected

    assert sniffer.pop_result(123) == expected
    assert not sniffer.has_result(123)
