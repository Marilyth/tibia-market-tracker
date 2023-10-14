import pymongo
from utils.market_values import MarketValues
from utils.tibia_wiki import EventData
from typing import List
import os
from tqdm import tqdm
from datetime import datetime


class ItemPricesCollection:
    def __init__(self, name: str, id: int):
        self.name = name
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
        value_dict.pop("name")
        value_dict.pop("id")

        return value_dict
    
    def to_mongo_dict(self) -> dict:
        """Converts the ItemPricesCollection to a dictionary for storage in MongoDB.

        Returns:
            dict: A dictionary containing the name and history of the ItemPricesCollection.
        """
        history = {}

        for server in self.history:
            history[server] = [ItemPricesCollection.MarketValues_to_mongo_dict(market_value) for market_value in self.history[server]]

        return {"name": self.name, "id": self.id, "history": history}


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

    def _add_from_file_system(self):
        """Adds the market values from the file system to the database.
        """
        path = "./src/results"

        for server in os.listdir(path):
            # if server is not a folder, skip it.
            if not os.path.isdir(os.path.join(path, server)):
                continue
            
            item_values = {}

            for file in os.listdir(os.path.join(path, server, "histories")):
                # Add histories.
                with open(os.path.join(path, server, "histories", file), "r") as f:
                    item_name = file[:-4]
                    item_values[item_name] = ItemPricesCollection(item_name, -1)
                    item_values[item_name].history[server] = []

                    # Skip first line, because it is gibberish often.
                    for line in f.read().split("\n")[1:]:
                        if line == "":
                            continue
                        market_values = MarketValues.from_history_string(line)
                        market_values.name = item_name
                        item_values[item_name].history[server].append(market_values)
                
            # Add fullscan.
            with open(os.path.join(path, server, "fullscan.csv"), "r") as f:
                for line in f.read().split("\n"):
                    if line == "":
                        continue
                    
                    # Ignore header.
                    if not line.startswith("Name,"):
                        market_values = MarketValues.from_string(line)
                        last_history = item_values[market_values.name].history[server].pop(-1)
                        market_values.time = last_history.time
                        item_values[market_values.name].history[server].append(market_values)

            for item in tqdm(item_values, desc=f"Adding items to database"):
                self.item_prices.insert_one(item_values[item].to_mongo_dict())

    def add_api_key(self, api_key: str):
        """Adds the given api key to the database.

        Args:
            api_key (str): The api key to add.
        """
        # Check if the api key already exists in the database.
        if self.api_keys.find_one({"api_key": api_key}):
            return
        
        self.api_keys.insert_one({"api_key": api_key})

    def add_event(self, event: EventData):
        """Adds the given event to the database.

        Args:
            date (str): The date of the event.
            events (List[str]): The events to add.
        """
        event.events = [event for event in event.events if event]

        if event.events:
            date = event.date.strftime('%Y.%m.%d')
            event = self.events.find_one({"date": date})

            if not event:
                self.events.insert_one({"date": date, "events": event.events})
            else:
                self.events.update_one({"date": date}, {"$set": {"events": event.events}})

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

        item_name = market_values.name.lower()
        item_id = market_values.id

        # Check if the item already exists in the database. Load the name and collection NAMES only, not their values.
        item = self.item_prices.find_one({"name": item_name}, {"name": 1, "history": 1})

        if item:
            # Add the market values to the history[server] list.
            self.item_prices.update_one({"name": item_name}, {"$push": {f"history.{server}": ItemPricesCollection.MarketValues_to_mongo_dict(market_values) } } )
            
            # Also update the item id if it doesn't exist yet.
            if "id" not in item or item["id"] == -1:
                self.item_prices.update_one({"name": item_name}, {"$set": {"id": item_id} } )
        else:
            # Add the item to the database.
            collection = ItemPricesCollection(item_name, item_id)
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
        projection = {"name": 1, "history": {server: {"$slice": -1}}}

        items = self.item_prices.find(query, projection)

        if items:
            items = list(items)
            items = [(item["name"], item["history"][server][0]) for item in items if len(item["history"][server]) > 0]
            for name, item in items:
                item["name"] = name

            return [item for name, item in items]
        else:
            return []
        
    def get_events(self) -> List[dict]:
        """Gets all events from the database.

        Returns:
            List[EventData]: The events from the database.
        """
        return list(self.events.find({}, {"_id": 0}))