import unittest
import main
import exchange
from typing import List
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.cursor import Cursor
from cex_objects import CEXTicker
from datetime import datetime


class CEXStub(exchange.CEXExchange):
    def __init__(self, *args, from_date: datetime, to_date: datetime):
        super().__init__(*args)
        self.client: MongoClient = MongoClient("localhost", username="root", password="Admin@2019", authSource="admin")
        self.db: Database = self.client["cex"]
        self.collection: Collection = self.db["eth_usd"]
        self.from_date = from_date
        self.to_date = to_date
        self.counter: int = 0
        self.tickers = self.get_tickers()

    def count_docs(self):


    def get_tickers(self) -> Cursor:
        query = {
            "$and": [
                {
                    "timestamp": {
                        "$gte": int(self.from_date.timestamp())
                    }
                },
                {
                    "timestamp": {
                        "$lte": int(self.to_date.timestamp())
                    }
                }
            ]
        }
        return self.collection.find(query)

    def getLatestBid(self, pair: str) -> float:
        self.current_index += 1
        return self.price_list[self.current_index - 1]


class RatchetTest(unittest.TestCase):
    def test_amount_gt_balance(self):
        main.sellPair("BTC/USD", 200, 20, 10)

    def test_extremum_finder(self):
        price_list = [178, 179, 180.2, 140.5, 150, 181, 140, 198, 100]
        main.cex = CEXStub(price_list)
        for i in range(len(price_list)):
            main.sellPair("BTC/USD", 50, 12, 10)
            if (i == 4):
                self.assertEqual(main.max_bid, 180.2)
                self.assertFalse(main.sell_start)
        self.assertTrue(main.sell_start)
        self.assertEqual(main.max_bid, 181)