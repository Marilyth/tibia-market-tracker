from typing import List
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster
import asyncio
import os
import requests
import subprocess


async def start_proxy(addons: List):
    options = Options()
    master = DumpMaster(options)
    master.addons.add(*addons)

    asyncio.create_task(master.run())

    # Need to install certificate of mitm to proxy SSL traffic.
    certificate_path = os.path.expanduser("~/.mitmproxy/mitmproxy-ca-cert.pem")
    subprocess.run(["mv", certificate_path, "/usr/local/share/ca-certificates/mitmproxy.crt"])
    subprocess.run(["update-ca-certificates"])

    os.environ["http_proxy"] = "http://localhost:8080"
    os.environ["https_proxy"] = "http://localhost:8080"

    # Wait until the proxy is reachable.
    while True:
        try:
            response = await asyncio.to_thread(requests.get, "http://www.google.com")
            if response.status_code == 200:
                print("Proxy is running and reachable.")
                return
        except Exception as e:
            pass

        print("Waiting for proxy to be reachable...")
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(start_proxy([]))
