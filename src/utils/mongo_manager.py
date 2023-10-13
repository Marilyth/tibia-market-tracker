import pymongo
from utils.market_values import MarketValues
from typing import List
import os
from tqdm import tqdm


class ItemPricesCollection:
    def __init__(self, name: str):
        self.name = name
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

        return value_dict
    
    def to_mongo_dict(self) -> dict:
        """Converts the ItemPricesCollection to a dictionary for storage in MongoDB.

        Returns:
            dict: A dictionary containing the name and history of the ItemPricesCollection.
        """
        history = {}

        for server in self.history:
            history[server] = [ItemPricesCollection.MarketValues_to_mongo_dict(market_value) for market_value in self.history[server]]

        return {"name": self.name, "history": history}


class MongoManager:
    def __init__(self, connection_string: str, database_name: str = "TibiaMarketTracker", collection_name: str = "ItemPrices"):
        self.client = pymongo.MongoClient(connection_string)
        self.database = self.client[database_name]
        self.collection = self.database[collection_name]

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
                    item_values[item_name] = ItemPricesCollection(item_name)
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
                self.collection.insert_one(item_values[item].to_mongo_dict())

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

        # Check if the item already exists in the database. Load the name and collection NAMES only, not their values.
        item = self.collection.find_one({"name": market_values.name.lower()}, {"name": 1, "history": 1})

        if item:
            # Add the market values to the history[server] list.
            self.collection.update_one({"name": market_values.name.lower()}, {"$push": {f"history.{server}": ItemPricesCollection.MarketValues_to_mongo_dict(market_values) } } )
        else:
            # Add the item to the database.
            collection = ItemPricesCollection(market_values.name.lower())
            collection.history[server] = [market_values]
            self.collection.insert_one(collection.to_mongo_dict())

    def get_item_history(self, item: str, server: str) -> List[dict]:
        """Gets the history of the item on the given server.

        Args:
            item (str): The item to get the history for.
            server (str): The server to get the history for.

        Returns:
            List[MarketValues]: The history of the item on the given server.
        """
        # Load only the requested server's history.
        item = self.collection.find_one({"name": item.lower()}, {"history": {server.lower(): 1}})

        if item:
            return item["history"][server.lower()]
        else:
            return []
        
    def get_latest_market_values(self, server: str, name: str = None, max_sell_price: int = None, min_buy_price: int = None, max_buy_price: int = None,
                    min_sell_price: int = None, max_flippers: int = None, min_flippers: int = None, order_by: str = None, ascending: bool = True) -> List[dict]:
        """Gets the market values of the items which match the given criteria.

        Args:
            server (str): The server of the item.
            name (str): The name of the item.
            max_sell_price (int): The maximum sell price of the item.
            min_buy_price (int): The minimum buy price of the item.
            max_buy_price (int): The maximum buy price of the item.
            min_sell_price (int): The minimum sell price of the item.
            max_flippers (int): The maximum number of flippers of the item.
            min_flippers (int): The minimum number of flippers of the item.
            order_by (str): The field to order by.
            ascending (bool): Whether to sort ascending or descending.
        
        Returns:
            List[dict]: The market values of the items which match the given criteria.
        """
        # Load only the requested server's history.
        query = {"history": {server.lower(): {"$exists": True}}}

        # Only retrieve the last entry of the history[server]'s history. Don't include the rest of the history, and don't include other servers.
        projection = {"name": 1, "history": {server.lower(): {"$slice": -1}}}

        items = self.collection.find(query, projection)

        if items:
            return list(items)
        else:
            return []