import pymongo
from utils.data.market_values import MarketValues, NPCSaleData, ItemMetaData, MarketBoard, MarketBoardTraderData
from utils.wiki import EventData, Wiki
from utils.data.world_data import WorldData, WorldActivity
from typing import List
import os
from tqdm import tqdm
from datetime import datetime


class ItemPricesCollection:
    def __init__(self, id: int, server: str):
        self.id = id
        self.server = server
        self.history = []

    @staticmethod
    def MarketValues_to_mongo_dict(market_values: MarketValues) -> dict:
        """Converts a MarketValues object to a dictionary for storage in MongoDB.

        Args:
            market_values (MarketValues): The MarketValues object to convert.

        Returns:
            dict: A dictionary containing the name and history of the MarketValues object.
        """
        value_dict = market_values.__dict__
        value_dict.pop("id")

        # Remove all fields that have "empty" values.
        # They will be inferred when the data is loaded using the is_full_data flag.
        for key in list(value_dict.keys()):
            if value_dict[key] == 0 or value_dict[key] == -1 or value_dict[key] == "":
                value_dict.pop(key)

        return value_dict

    @staticmethod
    def NPCSaleData_to_mongo_dict(npc_sale_data: NPCSaleData) -> dict:
        """Converts a NPCSaleData object to a dictionary for storage in MongoDB.

        Args:
            npc_sale_data (NPCSaleData): The NPCSaleData object to convert.

        Returns:
            dict: A dictionary containing the name, price and location of the NPCSaleData object.
        """
        return npc_sale_data.__dict__

    @staticmethod
    def NPCSaleData_to_mongo_dict(npc_sale_data: NPCSaleData) -> dict:
        """Converts a NPCSaleData object to a dictionary for storage in MongoDB.

        Args:
            npc_sale_data (NPCSaleData): The NPCSaleData object to convert.

        Returns:
            dict: A dictionary containing the name, price and location of the NPCSaleData object.
        """
        return npc_sale_data.__dict__

    def to_mongo_dict(self) -> dict:
        """Converts the ItemPricesCollection to a dictionary for storage in MongoDB.

        Returns:
            dict: A dictionary containing the name and history of the ItemPricesCollection.
        """
        history = [ItemPricesCollection.MarketValues_to_mongo_dict(market_value) for market_value in self.history]

        return {"id": self.id, "server": self.server, "history": history}


class MongoManager:
    def __init__(self, connection_string: str, database_name: str = "TibiaMarketTracker_Dev"):
        self.client = pymongo.AsyncMongoClient(connection_string)
        self.database = self.client[database_name]
        self.item_prices = self.database["ItemPrices"]
        self.item_meta_data = self.database["ItemMetaData"]
        self.api_keys = self.database["APIKeys"]
        self.access_logs = self.database["AccessLogs"]
        self.statistics = self.database["Statistics"]
        self.events = self.database["Events"]
        self.market_boards = self.database["MarketBoards"]

    async def update_schema(self):
        # Remove all items from item_prices which have no id.
        await self.item_prices.delete_many({"id": {"$exists": False}})

        item_ids = [item["id"] for item in await self.item_prices.find({}, {"id": 1}).to_list(length=None)]
        to_delete = [id for id in item_ids if not id in Wiki.get_marketable_proto_items()]

        # Remove all items from item_prices whose id is not in the wiki.
        await self.item_prices.delete_many({"id": {"$in": to_delete}})

        # Remove the name field from all items in item_prices.
        await self.item_prices.update_many({}, {"$unset": {"name": ""}})

        # Remove the pretty_name field from all items in item_prices.
        await self.item_prices.update_many({}, {"$unset": {"pretty_name": ""}})

        # Remove the category field from all items in item_prices.
        await self.item_prices.update_many({}, {"$unset": {"category": ""}})

        # Remove the is_upgradeable field from all items in item_prices.
        await self.item_prices.update_many({}, {"$unset": {"is_upgradeable": ""}})

        # Remove the internal_name field from all items in item_prices.
        await self.item_prices.update_many({}, {"$unset": {"internal_name": ""}})

        # Remove the npc_sell field from all items in item_prices.
        await self.item_prices.update_many({}, {"$unset": {"npc_sell": ""}})

        # Remove the npc_buy field from all items in item_prices.
        await self.item_prices.update_many({}, {"$unset": {"npc_buy": ""}})

    async def add_event(self, event_data: EventData):
        """Adds the given event to the database.

        Args:
            date (str): The date of the event.
            event_data (List[str]): The events to add.
        """
        event_data.events = [event for event in event_data.events if event]

        if event_data.events:
            date = event_data.date.strftime('%Y.%m.%d')
            event = await self.events.find_one({"date": date})

            if not event:
                await self.events.insert_one({"date": date, "events": event_data.events})
            else:
                await self.events.update_one({"date": date}, {"$set": {"events": event_data.events}})

    async def add_access_log(self, ip: str, endpoint: str, parameters: str, status: int):
        """Adds the given access log to the database.

        Args:
            ip (str): The ip of the request.
            endpoint (str): The endpoint of the request.
            param (str): The param of the request.
            status (int): The status code of the request.
        """
        await self.access_logs.insert_one({"ip": ip, "time": datetime.now().isoformat(), "endpoint": endpoint, "parameters": parameters, "status": status})

    async def add_statistic(self, ip: str, identifier: str, sub_identifier: str, value: str):
        """Adds the given statistic log to the database.

        Args:
            ip (str): The ip of the request.
            identifier (str): The identifier of the request. E.g. "Sorted"
            sub_identifier (str): The sub identifier of the request. E.g. "buy_price"
            value (str): The value of the request. E.g. "1"
        """
        await self.statistics.insert_one({"ip": ip, "time": datetime.utcnow(), "identifier": identifier, "sub_identifier": sub_identifier, "value": value})

    async def update_item_metadata(self, items: List[ItemMetaData]):
        """Used to update the item metadata in the database.
        """
        requests: List[pymongo.UpdateOne] = []

        for item in items:
            item_id = item.id

            item_dict = item.__dict__

            # Replace npc_sell and npc_buy with the mongo dict version.
            item_dict["npc_sell"] = [ItemPricesCollection.NPCSaleData_to_mongo_dict(data) for data in item.npc_sell]
            item_dict["npc_buy"] = [ItemPricesCollection.NPCSaleData_to_mongo_dict(data) for data in item.npc_buy]

            # Add or update the fields.
            requests.append(pymongo.UpdateOne({"id": item_id}, {"$set": item_dict}, upsert=True))

        await self.item_meta_data.bulk_write(requests)

    async def add_market_values(self, server: str, market_values: List[MarketValues]):
        """Adds the market values to the database.

        Args:
            market_values (MarketValues): The market values to add.
        """
        requests: List[pymongo.UpdateOne] = []
        item_cache = {}
        item_group = {}

        for values_item in market_values:
            if values_item.id not in item_group:
                item_group[values_item.id] = []
            item_group[values_item.id].append(values_item)

        for item_id in item_group:
            values_items = item_group[item_id]

            # Check if the item already exists in the database or as an insert operation.
            if item_id in item_cache:
                item = item_cache[item_id]
            else:
                item = await self.item_prices.find_one({"id": item_id, "server": server}, {"id": 1})
                item_cache[item_id] = item if item else 1

            if item:
                # Append the market values to the history list.
                requests.append(pymongo.UpdateOne({"id": item_id, "server": server}, {"$push": {"history": {"$each": [ItemPricesCollection.MarketValues_to_mongo_dict(value) for value in values_items]}}}))
            else:
                # Add the item to the database.
                collection = ItemPricesCollection(item_id, server)
                collection.history = values_items

                requests.append(pymongo.InsertOne(collection.to_mongo_dict()))

        # Keep bulk write requests under 10000.
        while requests:
            await self.item_prices.bulk_write(requests[:10000])
            requests = requests[10000:]

    async def update_market_boards(self, server: str, market_boards: List[MarketBoard]):
        """Updates the market boards for the given items.

        Args:
            server (str): The server to update the market boards for.
            market_boards (List[MarketBoard]): The market boards to update.
        """
        requests: List[pymongo.UpdateOne] = []

        for board in market_boards:
            # Check if the item already exists in the database.
            item = await self.market_boards.find_one({"id": board.id, "server": server}, {"id": 1})
            board.buyers = [buyer.__dict__ for buyer in board.buyers if buyer]
            board.sellers = [seller.__dict__ for seller in board.sellers if seller]
            board_dict = board.__dict__

            # Add the server to the board.
            board_dict["server"] = server

            if item:
                # Update the item in the database.
                requests.append(pymongo.UpdateOne({"id": board.id, "server": server}, {"$set": board_dict}))
            else:
                # Add the item to the database.
                requests.append(pymongo.InsertOne(board_dict))

        # Keep bulk write requests under 10000.
        while requests:
            await self.market_boards.bulk_write(requests[:10000])
            requests = requests[10000:]

    async def get_market_boards(self, server: str) -> List[MarketBoard]:
        """Gets the market boards on the given server.

        Args:
            server (str): The server to get the market board for.

        Returns:
            MarketBoard: The market board of the item on the given server.
        """
        query = {"server": server}
        boards = await self.market_boards.find(query)

        return [MarketBoard(**board) for board in boards]

    async def get_item_history(self, id: int, server: str) -> List[MarketValues]:
        """Gets the history of the item on the given server.

        Args:
            id (int): The id of the item to get the history for.
            server (str): The server to get the history for.

        Returns:
            List[MarketValues]: The history of the item on the given server.
        """
        # Load only the requested server's history.
        item = await self.item_prices.find_one({"id": id, "server": server}, {"history": 1})

        if item:
            items = item["history"]
            return [MarketValues(id=id, **item) for item in items if item]
        else:
            return []

    async def get_latest_market_values(self, server: str) -> List[MarketValues]:
        """Gets the market values of the items which match the given criteria.

        Args:
            server (str): The server of the item.

        Returns:
            List[dict]: The market values of the items which match the given criteria.
        """
        query = {"server": server}

        # Only retrieve the last entry of the history's history. Don't include the rest of the history.
        projection = {"history": {"$slice": -1}, "id": 1}

        items = await self.item_prices.find(query, projection)

        if items:
            items = list(items)
            items = [(item, item["history"][0]) for item in items if len(item["history"]) > 0]

            # Put the values of the item into the latest history entry for convenience.
            for values, item in items:
                item["id"] = values["id"]

            return [MarketValues(**item) for id, item in items]
        else:
            return []

    async def get_events(self) -> List[EventData]:
        """Gets all events from the database.

        Returns:
            List[EventData]: The events from the database.
        """
        events = list(await self.events.find({}, {"_id": 0}))
        events = [EventData(events=event["events"], date=datetime.strptime(event["date"], "%Y.%m.%d")) for event in events]

        return events

    async def get_item_metadata(self, item_id: int = -1) -> List[ItemMetaData]:
        """Gets the item metadata from the database.

        Args:
            item_id (int): The id of the item to get the metadata for. If -1, returns all items.

        Returns:
            dict: The item metadata from the database.
        """
        if item_id == -1:
            meta_datas = list(await self.item_meta_data.find({}, {"_id": 0}))
        else:
            meta_datas = [await self.item_meta_data.find_one({"id": item_id}, {"_id": 0})]

        meta_datas = [ItemMetaData(**meta_data) for meta_data in meta_datas if meta_data]

        return meta_datas

    async def get_world_data(self) -> List[WorldData]:
        """Gets the latest item update time for each server for the item 22118 (tibia coin).

        Returns:
            dict: The world data from the database.
        """
        query = {"id": 22118, "server": {"$exists": True}}
        projection = {"server": 1, "history": {"$slice": -1}}

        items = await self.item_prices.find(query, projection)

        return [WorldData(name=item["server"], last_update=datetime.utcfromtimestamp(item["history"][0]["time"])) for item in items]

    async def get_item_activity(self, item_id: int) -> List[WorldActivity]:
        """Gets world activities based on a certain item.

        Returns:
            List[WorldActivity]: The world activity for the given item.
        """
        # This needs 2 projections to first get the last history entry and then sum up the trades and offers.
        # Otherwise the arrayElemAt will take the last existing property.
        pipeline = [
            {"$match": {"id": item_id}},
            {"$project": {
                "lastHistory": {"$arrayElemAt": ["$history", -1]},
                "server": 1
            }},
            {"$project": {
                "totalTrades": {"$add": [
                    {"$ifNull": ["$lastHistory.month_sold", 0]},
                    {"$ifNull": ["$lastHistory.month_bought", 0]}
                ]},
                "totalOffers": {"$add": [
                    {"$ifNull": ["$lastHistory.sell_offers", 0]},
                    {"$ifNull": ["$lastHistory.buy_offers", 0]}
                ]},
                "server": 1
            }}
        ]

        results = await self.item_prices.aggregate(pipeline)

        return [WorldActivity(name=data["server"],
                              total_trades=data["totalTrades"],
                              total_offers=data["totalOffers"]) for data in results]
