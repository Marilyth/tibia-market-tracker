from utils.data.market_values import MarketValues, ItemMetaData, MarketBoard, MarketBoardTraderData
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
from utils.data.world_data import WorldActivity, WorldData
from datetime import datetime, timedelta
from contextvars import ContextVar


# Set up the API.
limiter = Limiter(key_func=get_remote_address, default_limits=["1/2seconds"], headers_enabled=True)
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
market_boards: Dict[str, List[MarketBoard]] = {}

jwt_helper = JWTHelper(config["jwtSecret"])
mongo_manager: MongoManager = MongoManager(config["mongodbConnectionString"])

request_var: ContextVar[str] = ContextVar("request_user", default=None)

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

def get_ratelimit() -> str:
    """Gets the ratelimit for the given request.

    Returns:
        str: The ratelimit for the given request.
    """
    request = request_var.get()
    auth_header = request.headers.get("Authorization", None)

    # Unauthorized requests are limited more heavily.
    if not auth_header:
        return "1/5seconds;5/minute;100/hour"

    username, _ = jwt_helper.verify_token(auth_header.split(" ")[1], verify_expired=False)

    # The discord bot is handling requests for many people, so it needs a higher rate limit.
    if username == "discord-bot":
        return "200/5seconds"

    # All other authorized requests are limited normally.
    return "1/5seconds;10/minute"

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

        if server not in full_scans:
            values = mongo_manager.get_latest_market_values(server)

            if not values:
                return None, []

            values = sorted(values, key=lambda x: (x.sell_offers + x.buy_offers), reverse=True)
            full_scans[server] = values
    except Exception as e:
        print(f"Error while reading fullscan: {e}")
    finally:
        fullscan_lock.release()

    return full_scans[server]

def get_cached_market_boards(server: str) -> List[MarketBoard]:
    """Gets the market board for the given item on the given server.

    Args:
        server (str): The server to get the market board for.

    Returns:
        MarketBoard: The market boards for the given server.
    """
    global market_boards

    if server not in market_boards:
        market_boards[server] = mongo_manager.get_market_boards(server)

    return market_boards[server]

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
    mongo_manager.add_access_log(request.client.host, request.url.path, request.url.query, result.status_code)

def normalize_server_name(name: str) -> str:
    """Normalizes the given server name.

    Args:
        name (str): The server name to normalize.

    Returns:
        str: The normalized server name.
    """
    name = name.strip()
    return name[0].upper() + name[1:].lower()

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
    token = request_var.set(request)
    response = await call_next(request)
    request_var.reset(token)

    # After.
    log_request_result(request, response)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response

@app.get("/add_statistic", include_in_schema=False, dependencies=[Depends(bearer_auth)])
async def add_statistic(request: Request, response: Response, identifier: str, sub_identifier: str = None, value: str = None):
    """Adds the given statistic to the database.

    Args:
        identifier (str): The identifier of the statistic.
        sub_identifier (str, optional): The sub identifier of the statistic. Defaults to None.
        value (str, optional): The value of the statistic. Defaults to None.
    """
    mongo_manager.add_statistic(request.client.host, identifier, sub_identifier, value)

# Set up API endpoints.
@app.get("/market_values")
@limiter.limit(get_ratelimit)
async def get_market_values(request: Request, response: Response, server: str, max_sell_price: int = None, min_buy_price: int = None, max_buy_price: int = None,
                            min_sell_price: int = None, max_flippers: int = None, min_flippers: int = None, skip: int = 0, limit: int = 100,
                            item_ids: str = None) -> List[MarketValues]:
    """Returns the market values of the items which match the given criteria.

    Args:
    - **server** (str): The server of the item.
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
    server = normalize_server_name(server)
    values = await get_fullscan_async(server)

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

    await add_statistic(request, "market_values", server, ",".join([str(item_ids), str(max_sell_price), str(min_sell_price), str(max_buy_price), str(min_buy_price), str(max_flippers), str(min_flippers)]))

    return values[skip:skip+limit]

@app.get("/batch_market_values", include_in_schema=False, dependencies=[Depends(bearer_auth)])
@limiter.limit(get_ratelimit)
async def get_batch_market_values(request: Request, response: Response, servers: str, max_sell_price: int = None, min_buy_price: int = None, max_buy_price: int = None,
                            min_sell_price: int = None, max_flippers: int = None, min_flippers: int = None, skip: int = 0, limit: int = 100,
                            item_ids: str = None) -> List[List[MarketValues]]:
    """Returns the market values of the items which match the given criteria.

    Args:
    - **servers** (str): The comma-seperated servers of the item.
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

    values = []
    for server in servers.split(","):
        server = normalize_server_name(server)
        values.append([value for value in await get_fullscan_async(server) if all([filter(value) for filter in filters])][skip:skip+limit])

    await add_statistic(request, "market_values", servers, ",".join([str(item_ids), str(max_sell_price), str(min_sell_price), str(max_buy_price), str(min_buy_price), str(max_flippers), str(min_flippers)]))

    return values

@app.get("/item_history")
@limiter.limit(get_ratelimit)
async def get_item_history(request: Request, response: Response, server: str, item_id: int, start_days_ago: int = 30, end_days_ago: int = -1) -> List[MarketValues]:
    """Returns the history of the given item.

    Args:
    - **server** (str): The server of the item.
    - **item_id** (int): The id of the item.
    - **start_days_ago** (int, optional): The number of days ago to start the history from. Defaults to 30.
    - **end_days_ago** (int, optional): The number of days ago to end the history at. Defaults to -1 (all).
    """
    server = normalize_server_name(server)
    values = mongo_manager.get_item_history(item_id, server)

    filters = []

    if start_days_ago > -1:
        start_date = datetime.now() - timedelta(days=start_days_ago)
        filters.append(lambda value: value.time >= start_date.timestamp())
    if end_days_ago > -1:
        end_date = datetime.now() - timedelta(days=end_days_ago)
        filters.append(lambda value: value.time <= end_date.timestamp())

    values = [value for value in values if all([filter(value) for filter in filters])]

    await add_statistic(request, "item_history", server, item_id)

    return values

@app.get("/batch_item_history", include_in_schema=False, dependencies=[Depends(bearer_auth)])
@limiter.limit(get_ratelimit)
async def get_batch_item_history(request: Request, response: Response, servers: str, item_id: int, start_days_ago: int = 30, end_days_ago: int = -1) -> List[List[MarketValues]]:
    """Returns the history of the given item.

    Args:
    - **servers** (str): The comma-seperated servers of the item.
    - **item_id** (int): The id of the item.
    - **start_days_ago** (int, optional): The number of days ago to start the history from. Defaults to 30.
    - **end_days_ago** (int, optional): The number of days ago to end the history at. Defaults to -1 (all).
    """
    filters = []

    if start_days_ago > -1:
        start_date = datetime.now() - timedelta(days=start_days_ago)
        filters.append(lambda value: value.time >= start_date.timestamp())
    if end_days_ago > -1:
        end_date = datetime.now() - timedelta(days=end_days_ago)
        filters.append(lambda value: value.time <= end_date.timestamp())

    values = []
    for server in servers.split(","):
        server = normalize_server_name(server)
        values.append([value for value in mongo_manager.get_item_history(item_id, server) if all([filter(value) for filter in filters])])

    await add_statistic(request, "item_history", servers, item_id)

    return values

@app.get("/events")
@limiter.limit(get_ratelimit)
async def get_events(request: Request, response: Response, start_days_ago: int = 30, end_days_ago: int = -1) -> List[EventData]:
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
@limiter.limit(get_ratelimit)
async def get_item_metadata(request: Request, response: Response, item_id: int = -1) -> List[ItemMetaData]:
    """Returns the metadata for the given item, or all items if no item id is given.

    Args:
    - **item_id** (int, optional): The id of the item to get the metadata for. Defaults to -1 (all).
    """
    metadata = mongo_manager.get_item_metadata(item_id)

    return metadata

@app.get("/item_activity")
@limiter.limit(get_ratelimit)
async def get_item_activity(request: Request, item_id: int) -> List[WorldActivity]:
    """Returns the total amount of active offers and verified trades for the given item
    in the past 28 days per world, sorted by most trades. This is used to determine how active
    a world is.

    Args:
        item_id (int): The id of the item.
    """
    return sorted(mongo_manager.get_item_activity(item_id), key=lambda x: x.total_trades, reverse=True)

@app.get("/world_data")
async def get_world_data(servers: str = None) -> List[WorldData]:
    """Returns the world data for all worlds. I.e. the last time the market was scanned.
    Optionally returns only the data for the given server.

    Args:
    - **servers** (str, optional): The comma-seperated servers to get the world data for. Defaults to None (all).
    """
    world_data = get_cached_world_data()
    servers_list = [normalize_server_name(server) for server in servers.split(",")] if servers else None

    if servers_list:
        world_data = [world for world in world_data if world.name in servers_list]

    return world_data

@app.get("/market_board")
@limiter.limit(get_ratelimit)
async def get_market_board(request: Request, response: Response, server: str, item_id: int) -> MarketBoard:
    """Returns the market board for the given item.

    Args:
    - **server** (str): The server of the item.
    - **item_id** (int): The id of the item.
    """
    server = normalize_server_name(server)
    values = get_cached_market_boards(server)

    # For backwards compatibility, return an individual item instead of a list.
    values = next((board for board in values if board.id == item_id), MarketBoard(id=item_id, sellers=[], buyers=[], update_time=0))

    await add_statistic(request, "market_board", server, item_id)

    return values

@app.get("/market_boards", include_in_schema=False, dependencies=[Depends(bearer_auth)])
@limiter.limit(get_ratelimit)
async def get_market_boards(request: Request, response: Response, server: str, item_id: int = -1) -> List[MarketBoard]:
    """Returns the market board for the given item.

    Args:
    - **server** (str): The server of the item.
    - **item_id** (int): The id of the item. Defaults to -1 (all).
    """
    server = normalize_server_name(server)
    values = get_cached_market_boards(server)

    if item_id != -1:
        values = [next((board for board in values if board.id == item_id), [MarketBoard(id=item_id, sellers=[], buyers=[], update_time=0)])]

    await add_statistic(request, "market_boards", server, item_id)

    return values

@app.get("/batch_market_board", include_in_schema=False, dependencies=[Depends(bearer_auth)])
@limiter.limit(get_ratelimit)
async def get_batch_market_board(request: Request, response: Response, servers: str, item_id: int) -> List[MarketBoard]:
    """Returns the market board for the given item.

    Args:
    - **servers** (str): The comma-seperated servers of the item.
    - **item_id** (int): The id of the item.
    """
    values = []

    for server in servers.split(","):
        server = normalize_server_name(server)
        server_board = get_cached_market_boards(server)

        values.append(next((board for board in server_board if board.id == item_id), MarketBoard(id=item_id, sellers=[], buyers=[], update_time=0)))

    await add_statistic(request, "market_board", str(servers), item_id)

    return values

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

@app.post("/update_market_boards", include_in_schema=False)
async def update_market_boards(request: Request, secret: str, boards: Annotated[str, Body()]):
    """Adds the given market boards to the database.

    Args:
        boards (str): The market boards to add in JSON format.
    """
    check_secret(secret)

    # Convert the boards to an object.
    boards = json_to_object(boards)
    mongo_manager.update_market_boards(boards.server, boards.data)

    # Remove the market boards from the cache.
    market_boards.pop(boards.server, None)

if __name__ == "__main__":
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"

    port = config["apiPort"]

    uvicorn.run(app, host="127.0.0.1", port=port)
