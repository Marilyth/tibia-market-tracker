import pymongo
from utils.data.market_values import MarketValues, NPCSaleData, ItemMetaData
from utils.wiki import EventData, Wiki
from typing import List
import os
from tqdm import tqdm
from datetime import datetime


class ItemPricesCollection:
    def __init__(self, id: int):
        self.id = id
        self.history = {}

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
        history = {}
        npc_sell = []
        npc_buy = []

        for server in self.history:
            history[server] = [ItemPricesCollection.MarketValues_to_mongo_dict(market_value) for market_value in self.history[server]]

        return {"id": self.id, "history": history}


class MongoManager:
    def __init__(self, connection_string: str, database_name: str = "TibiaMarketTracker"):
        self.client = pymongo.MongoClient(connection_string)
        self.database = self.client[database_name]
        self.item_prices = self.database["ItemPrices"]
        self.item_meta_data = self.database["ItemMetaData"]
        self.api_keys = self.database["APIKeys"]
        self.access_logs = self.database["AccessLogs"]
        self.events = self.database["Events"]

    def update_schema(self):
        # Remove all items from item_prices which have no id.
        self.item_prices.delete_many({"id": {"$exists": False}})

        item_ids = [item["id"] for item in self.item_prices.find({}, {"id": 1})]
        to_delete = [id for id in item_ids if not id in Wiki.get_marketable_proto_items()]

        # Remove all items from item_prices whose id is not in the wiki.
        self.item_prices.delete_many({"id": {"$in": to_delete}})

        # Remove the name field from all items in item_prices.
        self.item_prices.update_many({}, {"$unset": {"name": ""}})

        # Remove the pretty_name field from all items in item_prices.
        self.item_prices.update_many({}, {"$unset": {"pretty_name": ""}})

        # Remove the category field from all items in item_prices.
        self.item_prices.update_many({}, {"$unset": {"category": ""}})

        # Remove the is_upgradeable field from all items in item_prices.
        self.item_prices.update_many({}, {"$unset": {"is_upgradeable": ""}})

        # Remove the internal_name field from all items in item_prices.
        self.item_prices.update_many({}, {"$unset": {"internal_name": ""}})

        # Remove the npc_sell field from all items in item_prices.
        self.item_prices.update_many({}, {"$unset": {"npc_sell": ""}})

        # Remove the npc_buy field from all items in item_prices.
        self.item_prices.update_many({}, {"$unset": {"npc_buy": ""}})

    def add_api_key(self, api_key: str):
        """Adds the given api key to the database.

        Args:
            api_key (str): The api key to add.
        """
        # Check if the api key already exists in the database.
        if self.api_keys.find_one({"api_key": api_key}):
            return
        
        self.api_keys.insert_one({"api_key": api_key})

    def add_event(self, event_data: EventData):
        """Adds the given event to the database.

        Args:
            date (str): The date of the event.
            event_data (List[str]): The events to add.
        """
        event_data.events = [event for event in event_data.events if event]

        if event_data.events:
            date = event_data.date.strftime('%Y.%m.%d')
            event = self.events.find_one({"date": date})

            if not event:
                self.events.insert_one({"date": date, "events": event_data.events})
            else:
                self.events.update_one({"date": date}, {"$set": {"events": event_data.events}})

    def get_api_keys(self) -> List[str]:
        """Gets the api keys from the database.

        Returns:
            List[str]: The api keys from the database.
        """
        return [api_key["api_key"] for api_key in self.api_keys.find()]

    def add_access_log(self, ip: str, endpoint: str, parameters: str, status: int):
        """Adds the given access log to the database.

        Args:
            ip (str): The ip of the request.
            endpoint (str): The endpoint of the request.
            param (str): The param of the request.
            status (int): The status code of the request.
        """
        self.access_logs.insert_one({"ip": ip, "time": datetime.now().isoformat(), "endpoint": endpoint, "parameters": parameters, "status": status})

    def update_item_metadata(self, items: List[ItemMetaData]):
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
            
        self.item_meta_data.bulk_write(requests)

    def add_market_values(self, server: str, market_values: List[MarketValues]):
        """Adds the market values to the database.

        Args:
            market_values (MarketValues): The market values to add.
        """
        requests: List[pymongo.UpdateOne] = []

        for values_item in market_values:
            item_id = values_item.id

            # Check if the item already exists in the database. Load the name.
            item = self.item_prices.find_one({"id": item_id}, {"id": 1})

            if item:
                # Add the market values to the history[server] list.
                requests.append(pymongo.UpdateOne({"id": item_id}, {"$push": {f"history.{server}": ItemPricesCollection.MarketValues_to_mongo_dict(values_item) } } ))
            else:
                # Add the item to the database.
                collection = ItemPricesCollection(item_id)
                collection.history[server] = [values_item]

                requests.append(pymongo.InsertOne(collection.to_mongo_dict()))

        self.item_prices.bulk_write(requests)

    def get_item_history(self, id: int, server: str) -> List[dict]:
        """Gets the history of the item on the given server.

        Args:
            id (int): The id of the item to get the history for.
            server (str): The server to get the history for.

        Returns:
            List[MarketValues]: The history of the item on the given server.
        """
        # Load only the requested server's history.
        item = self.item_prices.find_one({"id": id}, {"history": {server: 1}})

        if item:
            return item["history"][server]
        else:
            return []
        
    def get_latest_market_values(self, server: str) -> List[dict]:
        """Gets the market values of the items which match the given criteria.

        Args:
            server (str): The server of the item.
        
        Returns:
            List[dict]: The market values of the items which match the given criteria.
        """
        query = {f"history.{server}": {"$exists": True}}

        # Only retrieve the last entry of the history[server]'s history. Don't include the rest of the history, and don't include other servers.
        projection = {"history": {server: {"$slice": -1}}, "id": 1}

        items = self.item_prices.find(query, projection)

        if items:
            items = list(items)
            items = [(item, item["history"][server][0]) for item in items if len(item["history"][server]) > 0]
            
            # Put the values of the item into the latest history entry for convenience.
            for values, item in items:
                item["id"] = values["id"]

            return [item for id, item in items]
        else:
            return []
        
    def get_events(self) -> List[dict]:
        """Gets all events from the database.

        Returns:
            List[EventData]: The events from the database.
        """
        return list(self.events.find({}, {"_id": 0}))
    
    def get_item_metadata(self, item_id: int = -1) -> dict:
        """Gets the item metadata from the database.

        Args:
            item_id (int): The id of the item to get the metadata for. If -1, returns all items.

        Returns:
            dict: The item metadata from the database.
        """
        if item_id == -1:
            return list(self.item_meta_data.find({}, {"_id": 0}))
        
        return self.item_meta_data.find_one({"id": item_id}, {"_id": 0})
