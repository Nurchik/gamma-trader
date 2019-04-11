import unittest
import exchange
from typing import List, Tuple
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from cex_objects import CEXTicker
from datetime import datetime
from seller import Seller, ChangeLevels, TradingDirective


class CEXStub(exchange.CEXExchange):
    def __init__(self, *args, from_date: datetime, to_date: datetime):
        super().__init__(*args)
        self.client: MongoClient = MongoClient("localhost", username="root", password="Admin@2019", authSource="admin")
        self.db: Database = self.client["cex"]
        self.collection: Collection = self.db["eth_usd"]
        self.from_date = from_date
        self.to_date = to_date
        self.counter: int = -1
        self.tickers: List[CEXTicker] = self.get_tickers()

    def reset_counter(self):
        self.counter = -1

    def get_tickers(self) -> List[CEXTicker]:
        tickers: List[CEXTicker] = []
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
        for doc in self.collection.find(query):
            tickers.append(CEXTicker(doc))
        return tickers

    def get_ticker(self, pair: str) -> CEXTicker:
        self.counter += 1
        return self.tickers[self.counter]


class CEXStub2(exchange.CEXExchange):
    def __init__(self, *args, tickers_raw: List[Tuple[float, float]]):
        super().__init__(*args)
        self.counter: int = -1
        self.tickers: List[CEXTicker] = self.get_tickers(tickers_raw)

    def reset_counter(self):
        self.counter = -1

    def get_tickers(self, tickers_raw: List[Tuple[float, float]]) -> List[CEXTicker]:
        tickers: List[CEXTicker] = []
        for ticker in tickers_raw:
            tickers.append(CEXTicker({
                "ask": ticker[0],
                "bid": ticker[1],
                "low": 100.0,
                "high": 200.0,
                "last": 150.0,
                "volume": 50000.0,
                "volume30d": 150000.0,
                "timestamp": 13423423523,
                "priceChange": 12.5,
                "priceChangePercentage": 1.75,
                "pair": "ETH.USD"
            }))
        return tickers

    def get_ticker(self, pair: str) -> CEXTicker:
        self.counter += 1
        return self.tickers[self.counter]


class TickerProcessingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.exchange = CEXStub("test", "test", "test",from_date=datetime.fromisoformat("2019-04-08T10:33:04"),
                                to_date=datetime.fromisoformat("2019-04-08T10:34:04"))
        self.seller = Seller(self.exchange, "sell", "ETH/USD", 1000.00, 10.00)

    def test_process_ticker(self) -> None:
        asks: List[float] = []
        bids: List[float] = []
        changes: List[ChangeLevels] = []
        while True:
            try:
                ticker = self.exchange.get_ticker(self.seller.pair)
                asks.append(ticker.ask)
                bids.append(ticker.bid)
                changes.append(self.seller.process_ticker(ticker))
            except IndexError:
                break
        max_ask = max(asks[0:10])
        max_bid = max(bids[0:10])
        ask_change = asks[9]/max_ask
        bid_change = bids[9]/max_bid
        change = changes[9]
        self.assertEqual(change.ask_change, ask_change)
        self.assertEqual(change.bid_change, bid_change)

        max_ask = max(asks[0:20])
        max_bid = max(bids[0:20])
        ask_change = asks[19] / max_ask
        bid_change = bids[19] / max_bid
        change = changes[19]
        self.assertEqual(change.ask_change, ask_change)
        self.assertEqual(change.bid_change, bid_change)

        max_ask = max(asks)
        max_bid = max(bids)
        ask_change = round(asks[-1] / max_ask, self.seller.significant_digits)
        bid_change = round(bids[-1] / max_bid, self.seller.significant_digits)
        change = changes[-1]
        self.assertEqual(change.ask_change, ask_change)
        self.assertEqual(change.bid_change, bid_change)


class ChangeProcessingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tickers_raw: List[Tuple[float, float]] = [(183.57, 182.61), (183.57, 172.61), (190.55, 171.61),
                                                  (185.67, 183.56), (201.835, 211.62), (170.45, 175.76),
                                                  (188.45, 234.56), (225.45, 234.56)]
        self.exchange = CEXStub2("test", "test", "test", tickers_raw=self.tickers_raw)
        self.seller = Seller(self.exchange, "sell", "ETH/USD", 1000.00, 10.00)

    def test_process_changes_buy(self) -> None:
        self.seller.action = "buy"
        directives: List[TradingDirective] = []
        for i in range(len(self.tickers_raw)):
            ticker: CEXTicker = self.exchange.get_ticker("ETH/USD")
            directive: TradingDirective = self.seller.process_changes(self.seller.process_ticker(ticker), ticker)
            directives.append(directive)
        directives_actions: List[str] = list(map(lambda td: td.action, directives))
        self.assertListEqual(directives_actions, ["hold", "hold", "hold", "hold", "hold", "hold", "buy", "buy"])
        self.assertEqual(directives[6].amount, 1000.0)
        self.assertEqual(directives[6].pair, "ETH/USD")
        self.assertEqual(directives[6].price, 188.45)
        self.assertEqual(directives[6].action, "buy")
        self.assertEqual(directives[3].amount, -1)
        self.assertEqual(directives[3].pair, "")
        self.assertEqual(directives[3].price, -1)
        self.assertEqual(directives[3].action, "hold")

    def test_process_changes_sell(self) -> None:
        self.seller.action = "sell"
        self.exchange.reset_counter()
        directives: List[TradingDirective] = []
        for i in range(len(self.tickers_raw)):
            ticker: CEXTicker = self.exchange.get_ticker("ETH/USD")
            directive: TradingDirective = self.seller.process_changes(self.seller.process_ticker(ticker), ticker)
            directives.append(directive)
        directives_actions: List[str] = list(map(lambda td: td.action, directives))
        self.assertListEqual(directives_actions, ["hold", "hold", "hold", "hold", "hold", "sell", "hold", "hold"])
        self.assertEqual(directives[5].amount, 1000.0)
        self.assertEqual(directives[5].pair, "ETH/USD")
        self.assertEqual(directives[5].price, 175.76)
        self.assertEqual(directives[5].action, "sell")
        self.assertEqual(directives[3].amount, -1)
        self.assertEqual(directives[3].pair, "")
        self.assertEqual(directives[3].price, -1)
        self.assertEqual(directives[3].action, "hold")


class OrderControllingTest(unittest.TestCase):
    def setUp(self) -> None:
        pass