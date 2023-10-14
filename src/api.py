from utils.market_values import MarketValues
from utils.mongo_manager import MongoManager
import uvicorn
from fastapi import FastAPI, Response, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
app = FastAPI()
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
mongo_manager.add_api_key("demo")
api_keys = mongo_manager.get_api_keys()

# Helpers.
def api_key_auth(api_key: str = Depends(oauth2_scheme)):
    if api_key not in api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Forbidden"
        )

async def get_fullscan_async(server: str):
    """Gets the fullscan for the given server.

    Args:
        server (str): The server to get the fullscan for.

    Returns:
        list: The fullscan for the given server.
    """
    # Check if the fullscan is cached and not old. If not, read it from mongodb.
    try:
        await fullscan_lock.acquire()

        if server not in full_scans or time.time() - full_scans[server][0] + 3600 <= 0:
            values = mongo_manager.get_latest_market_values(server)

            if not values:
                return None, []
            fullscan_time = values[-1]["time"]

            full_scans[server] = (fullscan_time, values)
    except Exception as e:
        print(f"Error while reading fullscan: {e}")
    finally:
        fullscan_lock.release()

    return full_scans[server]

def log_request_result(request: Request, result: Response):
    """Logs the result of the request being made.

    Args:
        request (fastapi.Request): The request being made.
        result (fastapi.Response): The result of the request.
    """
    mongo_manager.add_access_log(request.client.host, request.url.path, request.url.query, result.status_code)

# Middleware.
@app.middleware("http")
async def middleware(request: Request, call_next):
    """Performs actions before and after the request is made.

    Args:
        request (fastapi.Request): The request being made.
        call_next (function): The function to call next.

    Returns:
        The result of the next function.
    """
    # Before.
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
async def get_market_values(request: Request, server: str, name: str = None, max_sell_price: int = None, min_buy_price: int = None, max_buy_price: int = None,
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
        filters.append(lambda value: name.lower() in value["name"].lower())
    if max_sell_price:
        filters.append(lambda value: value["sell_offer"] <= max_sell_price)
    if min_sell_price:
        filters.append(lambda value: value["sell_offer"] >= min_sell_price)
    if min_buy_price:
        filters.append(lambda value: value["buy_offer"] >= min_buy_price)
    if max_buy_price:
        filters.append(lambda value: value["buy_offer"] <= max_buy_price)
    if max_flippers:
        filters.append(lambda value: value["active_traders"] <= max_flippers)
    if min_flippers:
        filters.append(lambda value: value["active_traders"] >= min_flippers)

    values = [value for value in values if all([filter(value) for filter in filters])]

    return {"last_updated": last_updated, "total_results": len(values), "values": values[skip:skip+limit]}

@app.get("/item_history", dependencies=[Depends(api_key_auth)])
@limiter.limit("1/5seconds;10/minute")
async def get_item_history(request: Request, server: str, item: str, start_time: float = None, end_time: float = None):
    """Returns the history of the given item.

    Args:
        server (str): The server of the item.
        item (str): The name of the item.
    """
    values = mongo_manager.get_item_history(item, server)

    if not values:
        return {"error": "Item does not exist, or has no data."}

    scan_time = values[-1]["time"]
    filters = []

    if start_time:
        filters.append(lambda value: value["time"] >= start_time)
    if end_time:
        filters.append(lambda value: value["time"] <= end_time)

    values = [value for value in values if all([filter(value) for filter in filters])]
    
    return {"last_updated": scan_time, "history": values}

@app.get("/events")
@limiter.limit("1/5seconds;10/minute")
async def get_events(request: Request):
    """Returns all tracked tibia events so far.
    """
    events = mongo_manager.get_events()

    return {"events": events}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)