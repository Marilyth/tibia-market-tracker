from utils.client import Client
from utils.market_values import MarketValues
from abc import ABCMeta, abstractmethod
from typing import *


class Extractor(metaclass=ABCMeta):
    def __init__(self, client: Client):
        self.client = client
    
    @abstractmethod
    def setup(self):
        pass

    @abstractmethod
    def extract_market_values(self) -> List[MarketValues]:
        pass