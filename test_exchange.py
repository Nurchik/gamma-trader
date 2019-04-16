import unittest
from exchange import CEXExchange, RemoteExecutionError, OrderNotFound
from typing import Dict, Any, Optional
import requests
import test_exchange_responses as test_responses
import responses
from cex_objects import CEXTicker, CEXOrderInfo, CEXPlacedOrderInfo, OrderStatus
import re
import json
import traceback

last_request = None


def ticker_callback(request):
    global last_request
    last_request = request
    return (200, {}, test_responses.TICKER_RESPONSE)


def place_order_callback(request):
    global last_request
    last_request = request
    first_symbol = request.url[-7:-4]
    if first_symbol == 'XLM':
        res = test_responses.PLACE_ORDER_RESPONSE
    else:
        res = test_responses.PLACE_ORDER_ERROR
    return (200, {}, res)


def get_order_callback(request):
    global last_request
    last_request = request
    param = json.loads(request.body)
    order_id = param.get('id')
    if order_id == '10000':
        response_json = test_responses.GET_ORDER_DONE_RESPONSE
    elif order_id == '10001':
        response_json = test_responses.GET_ORDER_CANCELLED_RESPONSE
    else:
        response_json = test_responses.GET_ORDER_NOT_FOUND
    return (200, {}, response_json)


def cancel_order_callback(request):
    global last_request
    last_request = request
    param = json.loads(request.body)
    order_id = param.get('id')
    if order_id == "10000":
        response_json = test_responses.CANCEL_ORDER_RESPONSE
    else:
        response_json = test_responses.CANCEL_ORDER_NOT_FOUND
    return (200, {}, response_json)


def prepareMocks():
    responses.add_callback(
        responses.GET,
        "https://cex.io/api/ticker/LTC/USD",
        callback=ticker_callback,
        content_type='text/json'
    )

    responses.add_callback(
        responses.POST,
        re.compile('https://cex.io/api/place_order'),
        callback=place_order_callback,
        content_type='text/json'
    )

    responses.add_callback(
        responses.POST,
        "https://cex.io/api/get_order/",
        callback=get_order_callback,
        content_type='text/json'
    )

    responses.add_callback(
        responses.POST,
        "https://cex.io/api/cancel_order/",
        callback=cancel_order_callback,
        content_type='text/json'
    )


class CEXExchangeTestable(CEXExchange):
    @responses.activate
    def request(self, url: str, method: str, param: Dict[str, Any]) -> requests.Response:
        return super().request(url, method, param)


class CEXExchangeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.exchange = CEXExchangeTestable("test", "test_key", "test")
        prepareMocks()

    def test_get_tickers(self):
        global last_request
        ticker: CEXTicker = self.exchange.get_ticker("LTC/USD")
        self.assertEqual(ticker.pair, "LTC:USD")
        self.assertEqual(ticker.price_change_percentage, -2.87)
        self.assertEqual(ticker.price_change, -2.38)
        self.assertEqual(ticker.ask, 81.47)
        self.assertEqual(ticker.bid, 80.03)
        self.assertEqual(ticker.volume_30_d, 22671.47783080)
        self.assertEqual(ticker.volume, 962.53899874)
        self.assertEqual(ticker.last, 80.55)
        self.assertEqual(ticker.high, 82.97)
        self.assertEqual(ticker.low, 77.01)
        self.assertEqual(ticker.timestamp, 1555429655)
        self.assertIsInstance(ticker.timestamp, int)
        self.assertEqual(last_request.url, "https://cex.io/api/ticker/LTC/USD")
        self.assertIsNone(last_request.body)
        self.assertEqual(last_request.method, 'GET')

    def test_cancel_order(self):
        global last_request
        self.exchange.cancel_order("10000")
        self.assertEqual(last_request.url, "https://cex.io/api/cancel_order/")
        req = json.loads(last_request.body)
        self.assertListEqual(list(req.keys()), ["id", "key", "signature", "nonce"])
        self.assertEqual(req["key"], "test_key")
        self.assertEqual(req["id"], "10000")
        self.assertEqual(last_request.method, 'POST')

    def test_cancel_order_error(self):
        global last_request

        exc: Optional[Exception] = None
        try:
            self.exchange.cancel_order("10001")
        except Exception as err:
            exc = err

        self.assertIsInstance(exc, RemoteExecutionError)
        self.assertEqual(exc.cause, "Error: Order not found")
        self.assertEqual(last_request.url, "https://cex.io/api/cancel_order/")
        req = json.loads(last_request.body)
        self.assertListEqual(list(req.keys()), ["id", "key", "signature", "nonce"])
        self.assertEqual(req["key"], "test_key")
        self.assertEqual(req["id"], "10001")
        self.assertEqual(last_request.method, 'POST')

    def test_place_order(self):
        global last_request
        placed_order: CEXPlacedOrderInfo = self.exchange.place_order("buy", "XLM/BTC", 10.575, 7700.58)
        self.assertEqual(placed_order.order_id, "8649363416")
        self.assertEqual(placed_order.order_type, "buy")
        self.assertEqual(placed_order.complete, True)
        self.assertEqual(placed_order.price, 0.11)
        self.assertEqual(placed_order.amount, 100.000)
        self.assertEqual(placed_order.pending, 100.0000000)
        self.assertEqual(placed_order.time, 1555427005911)

        self.assertEqual(last_request.url, "https://cex.io/api/place_order/XLM/BTC")
        req = json.loads(last_request.body)
        self.assertListEqual(list(req.keys()), ["type", "amount", "price", "key", "signature", "nonce"])
        self.assertEqual(req["key"], "test_key")
        self.assertEqual(req["type"], "buy")
        self.assertEqual(req["amount"], 7700.58)
        self.assertEqual(req["price"], 10.575)
        self.assertEqual(last_request.method, 'POST')

    def test_place_order_error(self):
        global last_request
        exc: Optional[Exception] = None
        try:
            placed_order: CEXPlacedOrderInfo = self.exchange.place_order("buy", "LTC/BTC", 100, 1200.57)
        except Exception as err:
            exc = err

        self.assertIsInstance(exc, RemoteExecutionError)
        self.assertEqual(exc.cause, "Error: Place order error: Insufficient funds.")
        self.assertEqual(last_request.url, "https://cex.io/api/place_order/LTC/BTC")
        req = json.loads(last_request.body)
        self.assertListEqual(list(req.keys()), ["type", "amount", "price", "key", "signature", "nonce"])
        self.assertEqual(req["key"], "test_key")
        self.assertEqual(req["type"], "buy")
        self.assertEqual(req["amount"], 1200.57)
        self.assertEqual(req["price"], 100)
        self.assertEqual(last_request.method, 'POST')

    def test_get_done_order_info(self):
        global last_request
        order_info: CEXOrderInfo = self.exchange.get_order_info("10000")
        self.assertEqual(order_info.order_id, '8544344631')
        self.assertEqual(order_info.order_type, 'sell')
        self.assertEqual(order_info.time, 1554220564111)
        self.assertEqual(order_info.last_tx_time, '2019-04-02T20:16:16.691Z')
        self.assertEqual(order_info.last_tx, '8545703401')
        self.assertEqual(order_info.user, 'up120757206')
        self.assertEqual(order_info.status, OrderStatus.DONE)
        self.assertEqual(order_info.price, 220)
        self.assertEqual(order_info.remains, 0.00000000)
        self.assertEqual(order_info.symbol_1, 'BTC')
        self.assertEqual(order_info.symbol_2, 'USD')
        self.assertEqual(order_info.amount, 1.53693924)

        self.assertEqual(last_request.url, "https://cex.io/api/get_order/")
        req = json.loads(last_request.body)
        self.assertListEqual(list(req.keys()), ["id", "key", "signature", "nonce"])
        self.assertEqual(req["key"], "test_key")
        self.assertEqual(req["id"], "10000")
        self.assertEqual(last_request.method, 'POST')

    def test_get_cancelled_order_info(self):
        global last_request
        order_info: CEXOrderInfo = self.exchange.get_order_info("10001")
        self.assertEqual(order_info.order_id, '8649363416')
        self.assertEqual(order_info.order_type, 'buy')
        self.assertEqual(order_info.time, 1555427005911)
        self.assertEqual(order_info.last_tx_time, '2019-04-16T15:04:51.633Z')
        self.assertEqual(order_info.last_tx, '8649369119')
        self.assertEqual(order_info.user, 'up120757206')
        self.assertEqual(order_info.status, OrderStatus.CANCELLED)
        self.assertEqual(order_info.price, 0.11)
        self.assertEqual(order_info.remains, 100.0000000)
        self.assertEqual(order_info.symbol_1, 'XLM')
        self.assertEqual(order_info.symbol_2, 'USD')
        self.assertEqual(order_info.amount, 100.0000000)

        self.assertEqual(last_request.url, "https://cex.io/api/get_order/")
        req = json.loads(last_request.body)
        self.assertListEqual(list(req.keys()), ["id", "key", "signature", "nonce"])
        self.assertEqual(req["key"], "test_key")
        self.assertEqual(req["id"], "10001")
        self.assertEqual(last_request.method, 'POST')

    def test_get_not_found_order_info(self):
        global last_request
        exc: Optional[Exception] = None
        try:
            order_info: CEXOrderInfo = self.exchange.get_order_info("10003")
        except Exception as err:
            exc = err

        self.assertIsInstance(exc, OrderNotFound)
        self.assertEqual(exc.order_id, "10003")
        self.assertEqual(last_request.url, "https://cex.io/api/get_order/")
        req = json.loads(last_request.body)
        self.assertListEqual(list(req.keys()), ["id", "key", "signature", "nonce"])
        self.assertEqual(req["key"], "test_key")
        self.assertEqual(req["id"], "10003")
        self.assertEqual(last_request.method, 'POST')
