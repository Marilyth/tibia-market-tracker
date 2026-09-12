from typing import List
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster
import asyncio
import os
import requests
import subprocess
import threading
import logging


logger = logging.getLogger(__name__)

master: DumpMaster = None
_proxy_loop: asyncio.AbstractEventLoop = None
_proxy_thread: threading.Thread = None


async def _run_master(addons: List):
    """Creates and runs the mitmproxy master on the proxy event loop."""
    global master

    options = Options()
    master = DumpMaster(options, with_dumper=False)
    master.addons.add(*addons)

    await master.run()


def _proxy_thread_main(addons: List):
    global _proxy_loop

    _proxy_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_proxy_loop)

    try:
        _proxy_loop.run_until_complete(_run_master(addons))
    finally:
        _proxy_loop.close()
        _proxy_loop = None


async def start_proxy(addons: List):
    """Runs mitmproxy on its own thread and event loop.

    Blocking work on the application's event loop (pyautogui, screen scans,
    subprocesses, ...) can therefore never starve the proxy and drop the game
    connection.
    """
    global _proxy_thread

    _proxy_thread = threading.Thread(target=_proxy_thread_main, args=(addons,), name="mitmproxy", daemon=True)
    _proxy_thread.start()

    # Need to install certificate of mitm to proxy SSL traffic.
    certificate_path = os.path.expanduser("~/.mitmproxy/mitmproxy-ca-cert.pem")
    subprocess.run(["cp", certificate_path, "/usr/local/share/ca-certificates/mitmproxy.crt"])
    subprocess.run(["update-ca-certificates"])

    # Wait until the proxy is reachable.
    proxies = get_proxy_env()
    while True:
        if not _proxy_thread.is_alive():
            raise RuntimeError("Proxy thread died during startup.")

        try:
            response = await asyncio.to_thread(requests.get, "http://www.google.com", proxies=proxies)
            if response.status_code == 200:
                logger.info("Proxy is running and reachable.")
                return
        except Exception as e:
            pass

        logger.debug("Waiting for proxy to be reachable...")
        await asyncio.sleep(0.5)


def inject_tcp(flow, to_client: bool, message: bytes):
    """Injects a TCP message into the proxy from the application's thread.

    The command is marshalled onto the proxy event loop so that mitmproxy writes
    to its transports from the proxy thread.
    """
    if _proxy_loop is None or master is None:
        raise RuntimeError("Proxy is not running.")

    _proxy_loop.call_soon_threadsafe(master.commands.call, "inject.tcp", flow, to_client, message)


def get_proxy_env() -> dict:
    """Returns the environment variables that route traffic through the proxy.
    """
    return {
        "http_proxy": "http://localhost:8080",
        "https_proxy": "https://localhost:8080",
    }


def stop_proxy():
    global _proxy_thread

    if master:
        master.shutdown()

    if _proxy_thread:
        _proxy_thread.join(timeout=10)
        _proxy_thread = None


if __name__ == "__main__":
    asyncio.run(start_proxy([]))
