import asyncio
import threading
import time

from utils.extraction.network import proxy


def test_inject_tcp_runs_on_proxy_loop(monkeypatch):
    loop = asyncio.new_event_loop()

    def run_loop():
        asyncio.set_event_loop(loop)
        loop.run_forever()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()

    calls = []
    records = {}

    class FakeCommands:
        def call(self, *args):
            calls.append(args)
            records["thread"] = threading.get_ident()

    class FakeMaster:
        commands = FakeCommands()

    monkeypatch.setattr(proxy, "_proxy_loop", loop)
    monkeypatch.setattr(proxy, "master", FakeMaster())

    try:
        proxy.inject_tcp("flow", True, b"message")

        deadline = time.time() + 2
        while not calls and time.time() < deadline:
            time.sleep(0.01)
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(5)

    assert calls == [("inject.tcp", "flow", True, b"message")]
    assert records["thread"] == thread.ident
