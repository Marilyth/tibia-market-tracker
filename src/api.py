from utils.data.market_values import MarketValues, ItemMetaData
from utils.wiki import EventData
from utils.mongo_manager import MongoManager
from utils.json_helper import json_to_object
import uvicorn
from fastapi import FastAPI, Response, Request, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import json
import os
import asyncio
from typing import Dict, Tuple, List, Annotated
import time
from utils.jwt_helper import JWTHelper
from utils.data.world_data import WorldData
from datetime import datetime, timedelta

# Set up the API.
limiter = Limiter(key_func=get_remote_address, default_limits=["1/2seconds"])
bearer_scheme = HTTPBearer()
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

app.add_middleware(GZipMiddleware)

# Read config file.
config = {}
with open(os.path.join(os.path.dirname(__file__), "config", "config.json"), "r") as c:
    config = json.loads(c.read())
    
# Set up any caches.
full_scans: Dict[str, Tuple[float, List[MarketValues]]] = {}
fullscan_lock = asyncio.Lock()
world_data: List[WorldData] = None

jwt_helper = JWTHelper(config["jwtSecret"])
mongo_manager: MongoManager = MongoManager(config["mongodbConnectionString"])

# Helpers.
def check_secret(secret: str):
    """Checks if the given secret is valid.

    Args:
        secret (str): The secret to check.

    Raises:
        HTTPException: If the secret is invalid.
    """
    if secret != config["jwtSecret"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid secret."
        )

def bearer_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """Checks if the given credentials are valid.
    
    Args:
        credentials (HTTPAuthorizationCredentials, optional): The credentials to check. Defaults to Depends(bearer_scheme).
        
    Raises:
        HTTPException: If the credentials are invalid.
    """
    username, reason = jwt_helper.verify_token(credentials.credentials, verify_expired=False)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=reason
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

        if server not in full_scans or (time.time() - full_scans[server][0]) >= 3600:
            values = mongo_manager.get_latest_market_values(server)

            if not values:
                return None, []

            values = sorted(values, key=lambda x: (x.sell_offers + x.buy_offers), reverse=True)
            full_scans[server] = (time.time(), values)
    except Exception as e:
        print(f"Error while reading fullscan: {e}")
    finally:
        fullscan_lock.release()

    return full_scans[server]

def get_cached_world_data() -> List[WorldData]:
    """Gets the world data.

    Returns:
        WorldDataResponse: The world data.
    """
    global world_data

    if not world_data:
        world_data = mongo_manager.get_world_data()

    return world_data

def log_request_result(request: Request, result: Response):
    """Logs the result of the request being made.

    Args:
        request (fastapi.Request): The request being made.
        result (fastapi.Response): The result of the request.
    """
    pass#mongo_manager.add_access_log(request.client.host, request.url.path, request.url.query, result.status_code)

def filter_outliers(values: List[MarketValues], keys: List[str], outlier_factor: float = 5, neighbour_search_range: int = 10):
    """Filter out outliers in the values list (spikes in values that are too high or too low).

    Args:
        values (List[Dict[str, float]]): The values to filter.
        keys (List[str]): The keys to filter.
        outlier_factor (float, optional): The factor to use to determine if a value is an outlier. Defaults to 5.
        neighbour_search_range (int, optional): The range to search for neighbours. Defaults to 10.
    """
    for i, value in enumerate(values):
        if i > 0 and i < len(values) - 1:
            for stat_name in keys:
                current = getattr(value, stat_name)
                
                if current == -1:
                    continue
                
                # Find the value before this one, that is not -1.
                before = -1
                for j in range(i - 1, max(i - neighbour_search_range, 0), -1):
                    before = getattr(values[j], stat_name)
                    if before != -1:
                        break
                    
                if before == -1:
                    continue
                
                # Find the value after this one, that is not -1.
                after = -1
                for j in range(i + 1, min(i + neighbour_search_range, len(values))):
                    after = getattr(values[j], stat_name)
                    if after != -1:
                        break
                
                if after == -1:
                    continue
                
                if current > before * outlier_factor and current > after * outlier_factor or\
                    current < before / outlier_factor and current < after / outlier_factor:
                    setattr(value, stat_name, -1)

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

    # Actual request.
    response = await call_next(request)

    # After.
    log_request_result(request, response)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response

# Set up API endpoints.
@app.get("/market_values", dependencies=[Depends(bearer_auth)])
@limiter.limit("1/5seconds;10/minute")
async def get_market_values(request: Request, server: str, max_sell_price: int = None, min_buy_price: int = None, max_buy_price: int = None,
                            min_sell_price: int = None, max_flippers: int = None, min_flippers: int = None, skip: int = 0, limit: int = 100,
                            item_ids: str = None) -> List[MarketValues]:
    """Returns the market values of the items which match the given criteria.

    Args:
    - **server** (str): The (case sensitive) server of the item.
    - **item_ids** (List[int]): A comma seperated list of ids of the items. If not provided, all items are returned.
    - **max_sell_price** (int): The maximum sell price of the item.
    - **min_buy_price** (int): The minimum buy price of the item.
    - **max_buy_price** (int): The maximum buy price of the item.
    - **min_sell_price** (int): The minimum sell price of the item.
    - **max_flippers** (int): The maximum number of flippers of the item.
    - **min_flippers** (int): The minimum number of flippers of the item.
    - **skip** (int): The number of items to skip. Defaults to 0.
    - **limit** (int): The maximum number of items to return. Defaults to 100.
    """
    last_checked, values = await get_fullscan_async(server)

    filters = []

    if not item_ids:
        if max_sell_price:
            filters.append(lambda value: value.sell_offer <= max_sell_price)
        if min_sell_price:
            filters.append(lambda value: value.sell_offer >= min_sell_price)
        if min_buy_price:
            filters.append(lambda value: value.buy_offer >= min_buy_price)
        if max_buy_price:
            filters.append(lambda value: value.buy_offer <= max_buy_price)
        if max_flippers:
            filters.append(lambda value: value.active_traders <= max_flippers)
        if min_flippers:
            filters.append(lambda value: value.active_traders >= min_flippers)
    else:
        item_ids = [int(id) for id in item_ids.split(",")]
        filters.append(lambda value: value.id in item_ids)

    values = [value for value in values if all([filter(value) for filter in filters])]

    return values[skip:skip+limit]

@app.get("/item_history", dependencies=[Depends(bearer_auth)])
@limiter.limit("1/5seconds;10/minute")
async def get_item_history(request: Request, server: str, item_id: int, start_days_ago: int = 30, end_days_ago: int = -1) -> List[MarketValues]:
    """Returns the history of the given item.

    Args:
    - **server** (str): The (case sensitive) server of the item.
    - **item_id** (int): The id of the item.
    - **start_days_ago** (int, optional): The number of days ago to start the history from. Defaults to 30.
    - **end_days_ago** (int, optional): The number of days ago to end the history at. Defaults to -1 (all).
    """
    values = mongo_manager.get_item_history(item_id, server)
    
    filters = []

    if start_days_ago > -1:
        start_date = datetime.now() - timedelta(days=start_days_ago)
        filters.append(lambda value: value.time >= start_date.timestamp())
    if end_days_ago > -1:
        end_date = datetime.now() - timedelta(days=end_days_ago)
        filters.append(lambda value: value.time <= end_date.timestamp())

    values = [value for value in values if all([filter(value) for filter in filters])]
    
    # Filter out outliers (spikes in values that are too high or too low).
    filter_outliers(values, ["buy_offer", "sell_offer", "month_sold", "month_bought", "month_average_sell", "month_average_buy"])
    
    return values

@app.get("/events", dependencies=[Depends(bearer_auth)])
@limiter.limit("1/5seconds;10/minute")
async def get_events(request: Request, start_days_ago: int = 30, end_days_ago: int = -1) -> List[EventData]:
    """Returns all tracked tibia events so far.

    Args:
    - **start_days_ago** (int, optional): The number of days ago to start the history from. Defaults to 30.
    - **end_days_ago** (int, optional): The number of days ago to end the history at. Defaults to -1 (all).
    """
    events = mongo_manager.get_events()

    if start_days_ago > -1:
        start_date = datetime.now() - timedelta(days=start_days_ago)
        events = [event for event in events if event.date >= start_date]
    if end_days_ago > -1:
        end_date = datetime.now() - timedelta(days=end_days_ago)
        events = [event for event in events if event.date <= end_date]

    return events

@app.get("/item_metadata")
@limiter.limit("1/5seconds;10/minute")
async def get_item_metadata(request: Request, item_id: int = -1) -> List[ItemMetaData]:
    """Returns the metadata for the given item, or all items if no item id is given.

    Args:
    - **item_id** (int, optional): The id of the item to get the metadata for. Defaults to -1 (all).
    """
    metadata = mongo_manager.get_item_metadata(item_id)

    return metadata

@app.get("/world_data")
async def get_world_data(server: str = None) -> List[WorldData]:
    """Returns the world data for all worlds. I.e. the last time the market was scanned.
    Optionally returns only the data for the given server.

    Args:
    - **server** (str, optional): The (case sensitive) server to get the world data for. Defaults to None (all).
    """
    world_data = get_cached_world_data()

    if server:
        world_data = [world for world in world_data if world.name == server]

    return world_data

@app.get("/generate_token", include_in_schema=False)
async def generate_token(username: str, secret: str, days: int = 90) -> str:
    """Generates a token for the given username, if the secret is correct.

    Args:
        username (str): The username to generate a token for.
        secret (str): The secret to use to generate the token.
        days (int, optional): The number of days the token is valid for. Defaults to 90.

    Returns:
        str: The token.
    """
    check_secret(secret)

    return jwt_helper.create_token(username, days)

@app.post("/add_event", include_in_schema=False)
async def add_event(request: Request, secret: str, event: Annotated[str, Body()]):
    """Adds the given event to the database.

    Args:
        event (str): The event to add in JSON format.
    """
    check_secret(secret)

    # Convert the event to an object.
    event = json_to_object(event)
    event.date = datetime.strptime(event.date, "%Y-%m-%d %H:%M:%S")

    mongo_manager.add_event(event)

@app.post("/add_market_values", include_in_schema=False)
async def add_market_values(request: Request, secret: str, values: Annotated[str, Body()]):
    """Adds the given market values to the database.

    Args:
        values (str): The market values to add in JSON format.
    """
    global world_data

    check_secret(secret)

    # Convert the values to an object.
    values = json_to_object(values)
    mongo_manager.add_market_values(values.server, values.data)

    # Remove the fullscan from the cache.
    full_scans.pop(values.server, None)

    world_data = None

@app.post("/update_item_metadata", include_in_schema=False)
async def update_item_metadata(request: Request, secret: str, metadata: Annotated[str, Body()]):
    """Adds the given item metadata to the database.

    Args:
        metadata (str): The item metadata to add in JSON format.
    """
    check_secret(secret)

    # Convert the metadata to an object.
    metadata = json_to_object(metadata)
    mongo_manager.update_item_metadata(metadata)

if __name__ == "__main__":
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    
    domain = config["apiDomain"]
    port = config["apiPort"]
    
    if domain:
        uvicorn.run(app, host="0.0.0.0", port=port, ssl_keyfile=f"/etc/letsencrypt/live/{domain}/privkey.pem", ssl_certfile=f"/etc/letsencrypt/live/{domain}/fullchain.pem")
    else:
        uvicorn.run(app, host="0.0.0.0", port=port)
