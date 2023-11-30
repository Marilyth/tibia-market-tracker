import pymongo
from utils.market_values import MarketValues, NPCSaleData
from utils.wiki import EventData, Wiki
from typing import List
import os
from tqdm import tqdm
from datetime import datetime


class ItemPricesCollection:
    def __init__(self, name: str, id: int, pretty_name: str, internal_name: str, npc_sell: List[NPCSaleData], npc_buy: List[NPCSaleData], category: str, is_upgradeable: bool):
        self.name = name
        self.internal_name = internal_name
        self.id = id
        self.pretty_name = pretty_name
        self.npc_sell = npc_sell
        self.npc_buy = npc_buy
        self.category = category
        self.is_upgradeable = is_upgradeable
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
        value_dict.pop("name")
        value_dict.pop("id")
        value_dict.pop("pretty_name")
        value_dict.pop("internal_name")
        value_dict.pop("npc_sell")
        value_dict.pop("npc_buy")
        value_dict.pop("category")
        value_dict.pop("is_upgradeable")

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

        for npc_sale_data in self.npc_sell:
            npc_sell.append(ItemPricesCollection.NPCSaleData_to_mongo_dict(npc_sale_data))

        for npc_sale_data in self.npc_buy:
            npc_buy.append(ItemPricesCollection.NPCSaleData_to_mongo_dict(npc_sale_data))

        return {"name": self.name, "id": self.id, "history": history, "pretty_name": self.pretty_name, 
                "internal_name": self.internal_name, "npc_sell": npc_sell, "npc_buy": npc_buy, 
                "category": self.category, "is_upgradeable": self.is_upgradeable}


class MongoManager:
    def __init__(self, connection_string: str, database_name: str = "TibiaMarketTracker"):
        self.client = pymongo.MongoClient(connection_string)
        self.database = self.client[database_name]
        self.item_prices = self.database["ItemPrices"]
        self.api_keys = self.database["APIKeys"]
        self.access_logs = self.database["AccessLogs"]
        self.events = self.database["Events"]

    def _add_events_from_file_system(self):
        """Adds the events from the file system to the database.
        """
        path = "./src/results/events.csv"

        with open(path, "r") as f:
            for line in f.read().split("\n"):
                if line == "":
                    continue
                
                date, events = line.split(",", 1)
                events = events.split(",")

                self.add_event(date, events)

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

    def _add_missing_fields(self, server: str, market_values: MarketValues):
        """Used to add missing fields to the database.

        Args:
            server (str): _description_
            market_values (MarketValues): _description_
        """
        # If a list of market values is given, add each one individually.
        if isinstance(market_values, list):
            for market_value in market_values:
                self.add_market_value(server, market_value)
            return

        market_values.load_from_proto()
        market_values.load_pretty_name()

        item_name = market_values.name.lower()
        item_id = market_values.id

        # Check if the item already exists in the database. Load the name and collection NAMES only, not their values.
        item = self.item_prices.find_one({"name": item_name}, {"name": 1, "id": 1, "pretty_name": 1, 
                                                               "internal_name": 1, "npc_sell": 1, "npc_buy": 1, "category": 1})

        if item:
            # Add or update the fields.
            self.item_prices.update_one({"name": item_name}, {"$set": {"pretty_name": market_values.name, "internal_name": item_name, 
                                                                        "npc_sell": [ItemPricesCollection.NPCSaleData_to_mongo_dict(data) for data in market_values.npc_sell], 
                                                                        "npc_buy": [ItemPricesCollection.NPCSaleData_to_mongo_dict(data) for data in market_values.npc_buy], 
                                                                        "category": market_values.category, "is_upgradeable": market_values.is_upgradeable, "id": item_id} } )

    def add_market_value(self, server: str, market_values: MarketValues):
        """Adds the market values to the database.

        Args:
            market_values (MarketValues): The market values to add.
        """
        # If a list of market values is given, add each one individually.
        if isinstance(market_values, list):
            for market_value in market_values:
                self.add_market_value(server, market_value)
            return

        # Don't add items that are not marketable.
        if not market_values.load_from_proto():
            return
        market_values.load_pretty_name()

        item_name = market_values.name.lower()
        item_id = market_values.id

        # Check if the item already exists in the database. Load the name.
        item = self.item_prices.find_one({"name": item_name}, {"name": 1, "id": 1})

        if item:
            # Add the market values to the history[server] list.
            self.item_prices.update_one({"name": item_name}, {"$push": {f"history.{server}": ItemPricesCollection.MarketValues_to_mongo_dict(market_values) } } )
        else:
            # Add the item to the database.
            collection = ItemPricesCollection(item_name, item_id, market_values.name, market_values.internal_name, market_values.npc_sell, market_values.npc_buy, market_values.category, market_values.is_upgradeable)
            collection.history[server] = [market_values]
            self.item_prices.insert_one(collection.to_mongo_dict())

    def get_item_history(self, item: str, server: str) -> List[dict]:
        """Gets the history of the item on the given server.

        Args:
            item (str): The item to get the history for.
            server (str): The server to get the history for.

        Returns:
            List[MarketValues]: The history of the item on the given server.
        """
        # Load only the requested server's history.
        item = self.item_prices.find_one({"name": item.lower()}, {"history": {server: 1}})

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
        projection = {"name": 1, "history": {server: {"$slice": -1}}, "id": 1, "pretty_name": 1, 
                      "internal_name": 1, "npc_sell": 1, "npc_buy": 1, "category": 1, "is_upgradeable": 1}

        items = self.item_prices.find(query, projection)

        if items:
            items = list(items)
            items = [(item, item["history"][server][0]) for item in items if len(item["history"][server]) > 0]
            
            # Put the values of the item into the latest history entry for convenience.
            for values, item in items:
                item["name"] = values["name"]

                try:
                    if "pretty_name" in values:
                        item["id"] = values["id"]
                        item["pretty_name"] = values["pretty_name"]
                        item["internal_name"] = values["internal_name"]
                        item["npc_sell"] = values["npc_sell"]
                        item["npc_buy"] = values["npc_buy"]
                        item["category"] = values["category"]
                        item["is_upgradeable"] = values["is_upgradeable"]
                except Exception as e:
                    print(f"Failed to add values to item. {e}")
                    print(f"Item: {item}")
                    print(f"Values: {values}")
                    raise e

            return [item for name, item in items]
        else:
            return []
        
    def get_events(self) -> List[dict]:
        """Gets all events from the database.

        Returns:
            List[EventData]: The events from the database.
        """
        return list(self.events.find({}, {"_id": 0}))