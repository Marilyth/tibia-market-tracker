from typing import Callable
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster
import asyncio
import os
import requests
import subprocess


class Addon(object):
    def request(self, flow):
        pass


    def response(self, flow):
        pass


async def main():
    options = Options(http2=True)
    master = DumpMaster(options)
    master.addons.add(Addon())

    task = asyncio.create_task(master.run())
    await asyncio.sleep(1)  # Allow some time for the master to start

    # Need to install certificate of mitm to proxy SSL traffic.
    subprocess.run(["mv", "~/.mitmproxy/mitmproxy-ca-cert.pem", "/usr/local/share/ca-certificates/mitmproxy.crt"])
    subprocess.run(["update-ca-certificates"])

    os.environ["http_proxy"] = "http://localhost:8080"
    os.environ["https_proxy"] = "http://localhost:8080"

    response = await asyncio.to_thread(requests.get, "http://www.google.com")
    assert response.status_code == 200

if __name__ == "__main__":
    asyncio.run(main())