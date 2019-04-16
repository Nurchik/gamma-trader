import unittest
import exchange
from typing import List, Tuple, Dict, Any, Optional, cast
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from cex_objects import CEXTicker, CEXOrderInfo, CEXPlacedOrderInfo
from datetime import datetime
from trader import Trader, ChangeLevels, TradingDirective, OrderDone, OrderExpired, PartiallyExecutedOrder
import traceback


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


class CEXStub3(CEXStub2):
    def __init__(self, *args, tickers_raw=[]):
        super().__init__(*args, tickers_raw=tickers_raw)
        self.orders: Dict[str, Any] = {}
        self.order_data_template: Dict[str, Any] = {
            "time": 19995568,
            "type": "buy",
            "user": "user001",
            "price": 150.67,
            "amount": 1000.0,
            "symbol1": "ETH",
            "symbol2": "USD",
            "lastTxTime": "202030333",
            "lastTx": "345346346",
            "remains": 1000.0,
            "status": "a"
        }
        self.order_counter: int = 0

    def set_order(self, order_id: str, order_data: Dict[str, Any]) -> None:
        self.orders[order_id] = {**self.order_data_template, **order_data}

    def get_order(self, order_id: str) -> Dict[str, Any]:
        return self.orders.get(order_id)

    def get_order_info(self, order_id: str) -> CEXOrderInfo:
        order_data: Dict[str, Any] = self.orders.get(order_id)
        return CEXOrderInfo(order_data)

    def cancel_order(self, order_id: str) -> None:
        order_data = {**self.get_order(order_id), **{"status": "c"}}
        self.set_order(order_id, order_data)

    def place_order(self, order_type: str, pair: str, price: float, amount: float) -> CEXPlacedOrderInfo:
        order_id: str = f"1000{self.order_counter}"
        time: int = int(datetime.now().timestamp())
        self.order_counter += 1
        self.set_order(order_id, {
            "id": order_id,
            "time": time,
            "type": order_type,
            "price": price,
            "amount": amount,
            "remains": amount
        })
        return CEXPlacedOrderInfo({"id": order_id, "time": time, "complete": False, "amount": 1.0, "pending": 1.0,
                                   "price": 100.0, "type": "sell"})


class TickerProcessingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.exchange = CEXStub("test", "test", "test",from_date=datetime.fromisoformat("2019-04-08T10:33:04"),
                                to_date=datetime.fromisoformat("2019-04-08T10:34:04"))
        self.seller = Trader(self.exchange, "sell", "ETH/USD", 1000.00, 10.00)

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
        self.seller = Trader(self.exchange, "sell", "ETH/USD", 1000.00, 10.00)

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
        self.exchange = CEXStub3("test", "test", "test")
        self.seller = Trader(self.exchange, "sell", "ETH/USD", 1000.00, 10.00)

    def test_instant_order(self):
        order_id: str = "0000001"
        self.seller.current_order = order_id
        self.exchange.set_order(order_id, {"id": order_id, "status": "d"})
        exc: Optional[Exception] = None
        try:
            self.seller.control_order()
        except OrderDone as err:
            exc = err
        self.assertIsInstance(exc, OrderDone)

    def test_order(self):
        order_id: str = "0000001"
        self.seller.current_order = order_id
        self.exchange.set_order(order_id, {"id":order_id, "status": "a"})
        self.seller.order_ttl = 0
        for i in range(1, 6):
            self.seller.control_order()
            self.assertEqual(self.seller.order_ttl, i)
        self.exchange.set_order(order_id, {"id": order_id, "status": "d"})
        exc: Optional[Exception] = None
        try:
            self.seller.control_order()
        except OrderDone as err:
            exc = err
        self.assertIsInstance(exc, OrderDone)
        self.assertEqual(self.seller.order_ttl, 5)

    def test_expired_order(self):
        order_id: str = "0000001"
        self.seller.current_order = order_id
        self.exchange.set_order(order_id, {"id": order_id, "status": "a", "remains": 550.75})
        self.seller.order_ttl = 0
        exc: Optional[Exception] = None
        for i in range(1, 11):
            try:
                self.seller.control_order()
            except Exception as err:
                exc = err
            if i < 10:
                self.assertEqual(self.seller.order_ttl, i)
                self.assertIsNone(exc)
            else:
                self.assertIsInstance(exc, OrderExpired)
                self.assertEqual(self.seller.order_ttl, 10)
        self.assertEqual(self.exchange.get_order(order_id).get("status"), "c")

    def test_partial_order(self):
        order_id: str = "0000001"
        self.seller.current_order = order_id
        self.exchange.set_order(order_id, {"id": order_id, "status": "c", "remains": 0.0})
        self.seller.order_ttl = 0
        exc: Optional[Exception] = None

        try:
            self.seller.control_order()
        except Exception as err:
            exc = err
        self.assertIsInstance(exc, OrderDone)

        self.exchange.set_order(order_id, {"id": order_id, "status": "c", "remains": 15.65})
        try:
            self.seller.control_order()
        except Exception as err:
            exc = err
        self.assertIsInstance(exc, PartiallyExecutedOrder)
        self.assertEqual(exc.remains, 15.65)

        self.exchange.set_order(order_id, {"id": order_id, "status": "cd", "remains": 7535.89})
        try:
            self.seller.control_order()
        except Exception as err:
            exc = err
        self.assertIsInstance(exc, PartiallyExecutedOrder)
        self.assertEqual(exc.remains, 7535.89)


class ProcessingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.exchange = CEXStub3("test", "test", "test", tickers_raw=[
            (183.57, 182.61), (183.57, 186.61), (183.57, 193.0), (183.57, 172.69), (183.57, 182.61), (183.57, 150.78),
            (183.57, 151.78), (183.57, 152.78), (183.57, 153.78), (183.57, 154.78)
        ])
        self.seller = Trader(self.exchange, "sell", "ETH/USD", 1578.15, 10.00, 3)

    def test_processing_done(self):
        self.assertFalse(self.seller.trade_ignited)
        self.assertIsNone(self.seller.current_order)
        self.assertDictEqual(self.exchange.orders, {})
        self.seller.process()
        self.assertEqual(self.seller.order_ttl, 0)
        self.assertEqual(self.seller.min_ask, 183.57)
        self.assertEqual(self.seller.max_bid, 182.61)

        self.seller.process()
        self.assertIsNone(self.seller.current_order)
        self.assertFalse(self.seller.trade_ignited)
        self.assertEqual(self.seller.max_bid, 186.61)

        self.seller.process()
        self.assertIsNone(self.seller.current_order)
        self.assertFalse(self.seller.trade_ignited)
        self.assertEqual(self.seller.min_ask, 183.57)
        self.assertEqual(self.seller.max_bid, 193.0)

        self.seller.process()
        self.assertEqual(self.seller.current_order, "10000")
        self.assertTrue(self.seller.trade_ignited)
        self.assertEqual(self.seller.order_ttl, 0)
        self.assertEqual(self.exchange.orders.get("10000").get("status"), "a")
        self.assertEqual(self.exchange.orders.get("10000").get("price"), 172.69)
        self.assertEqual(self.exchange.orders.get("10000").get("amount"), 1578.15)
        self.assertEqual(self.exchange.orders.get("10000").get("remains"), 1578.15)
        self.assertEqual(self.exchange.orders.get("10000").get("type"), "sell")

        order_data: Dict[str, Any] = self.exchange.get_order("10000")
        self.exchange.set_order("10000", {**order_data, **{"remains": 1000.0, "status": "a"}})

        self.seller.process()
        self.assertEqual(self.seller.current_order, "10000")
        self.assertTrue(self.seller.trade_ignited)
        self.assertEqual(self.exchange.orders.get("10000").get("status"), "a")
        self.assertEqual(self.exchange.orders.get("10000").get("status"), "a")
        self.assertEqual(self.exchange.orders.get("10000").get("price"), 172.69)
        self.assertEqual(self.exchange.orders.get("10000").get("amount"), 1578.15)
        self.assertEqual(self.exchange.orders.get("10000").get("remains"), 1000.0)
        self.assertEqual(self.exchange.orders.get("10000").get("type"), "sell")
        self.assertEqual(self.seller.order_ttl, 1)

        exc: Optional[Exception] = None
        order_data: Dict[str, Any] = self.exchange.get_order("10000")
        self.exchange.set_order("10000", {**order_data, **{"remains": 0.0, "status": "d"}})
        try:
            self.seller.process()
        except Exception as err:
            exc = err
        self.assertIsInstance(exc, OrderDone)
        self.assertEqual(self.seller.order_ttl, 1)

    def test_processing_expired(self):
        self.seller.max_order_ttl = 3

        self.assertFalse(self.seller.trade_ignited)
        self.assertIsNone(self.seller.current_order)
        self.assertDictEqual(self.exchange.orders, {})
        self.seller.process()
        self.assertEqual(self.seller.order_ttl, 0)

        self.seller.process()
        self.assertIsNone(self.seller.current_order)
        self.assertFalse(self.seller.trade_ignited)

        self.seller.process()
        self.assertIsNone(self.seller.current_order)
        self.assertFalse(self.seller.trade_ignited)
        self.assertEqual(self.seller.order_ttl, 0)

        self.seller.process()
        self.assertEqual(self.seller.current_order, "10000")
        self.assertTrue(self.seller.trade_ignited)
        self.assertEqual(self.seller.order_ttl, 0)
        self.assertEqual(self.exchange.orders.get("10000").get("status"), "a")
        self.assertEqual(self.exchange.orders.get("10000").get("price"), 172.69)
        self.assertEqual(self.exchange.orders.get("10000").get("amount"), 1578.15)
        self.assertEqual(self.exchange.orders.get("10000").get("remains"), 1578.15)
        self.assertEqual(self.exchange.orders.get("10000").get("type"), "sell")

        exc: Optional[Exception] = None
        for i in range(1, 4):
            try:
                subs: float = i * 200.0
                order_data: Dict[str, Any] = self.exchange.get_order("10000")
                self.exchange.set_order("10000", {**order_data, **{"remains": round(1578.15 - subs, 3), "status": "a"}})
                self.seller.process()
                self.exchange.counter += 1  # advancing ticker's counter as it will in real life
            except Exception as err:
                exc = err
                break
        self.assertIsInstance(exc, OrderExpired)
        self.assertEqual(self.seller.order_ttl, 3)
        self.assertEqual(self.exchange.orders.get("10000").get("amount"), 1578.15)
        self.assertEqual(self.exchange.orders.get("10000").get("remains"), 978.15)
        self.assertEqual(self.exchange.orders.get("10000").get("status"), "c")
        self.assertEqual(self.seller.current_order, "10000")
        self.assertTrue(self.seller.trade_ignited)

        self.seller.process()
        self.assertEqual(self.seller.current_order, "10001")
        self.assertEqual(self.seller.order_ttl, 0)
        self.assertEqual(self.exchange.orders.get("10001").get("status"), "a")
        self.assertEqual(self.exchange.orders.get("10001").get("price"), 151.78)
        self.assertEqual(self.exchange.orders.get("10001").get("amount"), 978.15)
        self.assertEqual(self.exchange.orders.get("10001").get("remains"), 978.15)
        self.assertEqual(self.exchange.orders.get("10001").get("type"), "sell")

        self.seller.process()

        order_data: Dict[str, Any] = self.exchange.get_order("10001")
        self.exchange.set_order("10001", {**order_data, **{"status": "d"}})
        try:
            self.seller.process()
        except Exception as err:
            exc = err

        self.assertIsInstance(exc, OrderDone)
