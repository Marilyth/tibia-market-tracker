from utils.market_values import MarketValues
from utils.mongo_manager import MongoManager
import uvicorn
import fastapi
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import json
import os
import asyncio
from typing import Dict, Tuple, List
import time


# Set up the API.
limiter = Limiter(key_func=get_remote_address, default_limits=["1/2seconds"])
app = fastapi.FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up any caches, configs, variables and locks.
full_scans: Dict[str, Tuple[float, List[MarketValues]]] = {}
config = {}
fullscan_lock = asyncio.Lock()
with open(os.path.join(os.path.dirname(__file__), "config", "config.json"), "r") as c:
    config = json.loads(c.read())

mongo_manager: MongoManager = MongoManager(config["mongodbConnectionString"])

# Helper methods.
def does_server_exist(server: str):
    """Checks if the given server exists in the results location.

    Args:
        server (str): The server to check.

    Returns:
        bool: True if the server exists, False otherwise.
    """
    return os.path.exists(os.path.join(config["resultsLocation"], server))

def does_item_exist(server: str, name: str):
    """Checks if the given item exists in the results location.

    Args:
        server (str): The server of the item.
        name (str): The name of the item.

    Returns:
        bool: True if the item exists, False otherwise.
    """
    return does_server_exist and os.path.exists(os.path.join(config["resultsLocation"], server, "histories", f"{name.lower()}.csv"))

async def get_fullscan_async(server: str):
    """Gets the fullscan for the given server.

    Args:
        server (str): The server to get the fullscan for.

    Returns:
        list: The fullscan for the given server.
    """
    if not does_server_exist(server):
        return {"error": "Server does not exist, or has no data."}

    # Check if the fullscan is cached. If not, read it from disk.
    try:
        await fullscan_lock.acquire()
        fullscan_time = os.path.getmtime(os.path.join(config["resultsLocation"], server, "fullscan.csv"))

        if server not in full_scans or full_scans[server][0] < fullscan_time:
            with open(os.path.join(config["resultsLocation"], server, "fullscan.csv"), "r") as f:
                values = []
                for line in f.read().split("\n"):
                    if line == "":
                        continue
                    
                    # Ignore header.
                    if not line.startswith("Name,"):
                        values.append(MarketValues.from_string(line))

                full_scans[server] = (fullscan_time, values)
    except Exception as e:
        print(f"Error while reading fullscan: {e}")
    finally:
        fullscan_lock.release()

    return full_scans[server]

async def get_item_history_async(server: str, item: str):
    if not does_server_exist(server):
        return {"error": "Server does not exist, or has no data."}
    
    if not does_item_exist(server, item):
        return {"error": "Item does not exist, or has no data."}

    values = []
    scan_time = os.path.getmtime(os.path.join(config["resultsLocation"], server, "histories", f"{item.lower()}.csv"))

    with open(os.path.join(config["resultsLocation"], server, "histories", f"{item.lower()}.csv"), "r") as f:
        for line in f.read().split("\n"):
            if line == "":
                continue
            
            # Convert csv line to MarketValues object.
            value = MarketValues.from_history_string(line)
            value.name = item
            values.append(value)
    
    return scan_time, values

def log_request(request: fastapi.Request):
    """Logs the request being made.

    Args:
        request (fastapi.Request): The request being made.
    """
    print(f"Incoming request from {request.client.host}: {request.method} {request.url}")

def log_request_result(request: fastapi.Request, result: fastapi.Response):
    """Logs the result of the request being made.

    Args:
        request (fastapi.Request): The request being made.
        result (fastapi.Response): The result of the request.
    """
    print(f"Request from {request.client.host}: {request.method} {request.url} resulted in {result.status_code}")

# Middleware.
@app.middleware("http")
async def middleware(request: fastapi.Request, call_next):
    """Performs actions before and after the request is made.

    Args:
        request (fastapi.Request): The request being made.
        call_next (function): The function to call next.

    Returns:
        The result of the next function.
    """
    # Before.
    log_request(request)
    start_time = time.time()

    response = await call_next(request)

    # After.
    log_request_result(request, response)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response

# Set up API endpoints.
@app.get("/market_values")
@limiter.limit("1/5seconds;10/minute")
async def get_market_values(request: fastapi.Request, server: str, name: str = None, max_sell_price: int = None, min_buy_price: int = None, max_buy_price: int = None,
                            min_sell_price: int = None, max_flippers: int = None, min_flippers: int = None, skip: int = 0, limit: int = 100):
    """Returns the market values of the items which match the given criteria.

    Args:
        server (str): The server of the item.
        name (str): The name of the item.
        max_sell_price (int): The maximum sell price of the item.
        min_buy_price (int): The minimum buy price of the item.
        max_buy_price (int): The maximum buy price of the item.
        min_sell_price (int): The minimum sell price of the item.
        max_flippers (int): The maximum number of flippers of the item.
        min_flippers (int): The minimum number of flippers of the item.
    """
    last_updated, values = await get_fullscan_async(server)

    filters = []

    if name:
        filters.append(lambda value: name.lower() in value.name.lower())
    if max_sell_price:
        filters.append(lambda value: value.sell_offer <= max_sell_price)
    if min_buy_price:
        filters.append(lambda value: value.buy_offer >= min_buy_price)
    if max_buy_price:
        filters.append(lambda value: value.buy_offer <= max_buy_price)
    if min_sell_price:
        filters.append(lambda value: value.sell_offer >= min_sell_price)
    if max_flippers:
        filters.append(lambda value: value.active_traders <= max_flippers)
    if min_flippers:
        filters.append(lambda value: value.active_traders >= min_flippers)

    values = [value for value in values if all([filter(value) for filter in filters])]

    return {"last_updated": last_updated, "total_results": len(values), "values": values[skip:skip+limit]}

@app.get("/item_history")
@limiter.limit("1/5seconds;10/minute")
async def get_item_history(request: fastapi.Request, server: str, item: str, start_time: float = None, end_time: float = None):
    """Returns the history of the given item.

    Args:
        server (str): The server of the item.
        item (str): The name of the item.
    """
    scan_time, values = await get_item_history_async(server, item)
    filters = []

    if start_time:
        filters.append(lambda value: value.time >= start_time)
    if end_time:
        filters.append(lambda value: value.time <= end_time)

    values = [value for value in values if all([filter(value) for filter in filters])]
    
    return {"last_updated": scan_time, "history": values}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)