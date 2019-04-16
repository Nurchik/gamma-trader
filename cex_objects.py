from typing import Dict, Any, Type, Optional
from enum import Enum


class CEXApiData:
    def __init__(self, json_obj: Dict[str, Any]):
        self.json_obj = json_obj
        self.init()

    def init(self):
        pass


class OrderStatus(Enum):
    DONE = 1
    CANCELLED = 2
    ACTIVE = 3


class CEXPlacedOrderInfo(CEXApiData):
    def __init__(self, *args):
        self.order_id: str = ""
        self.time: int = -1
        self.complete: bool = False
        self.pending: float = -1
        self.amount: float = -1
        self.order_type: str = ''
        self.price: float = -1
        super().__init__(*args)

    def init(self) -> None:
        self.order_id = self.json_obj["id"]
        self.time = int(self.json_obj["time"])
        self.complete = self.json_obj["complete"]
        self.pending = float(self.json_obj["pending"])
        self.amount = float(self.json_obj["amount"])
        self.order_type = self.json_obj["type"]
        self.price = float(self.json_obj["price"])

    def __str__(self):
        return f"order_id = {self.order_id}, time = {self.time}, complete = {self.complete}, pending = {self.pending}, " \
            f"amount = {self.amount}, order_type = {self.order_type}, price = {self.price}"


class CEXOrderInfo(CEXApiData):
    def __init__(self, *args):
        self.order_id: str = ""
        self.time: str = ""
        self.order_type: str = ""
        self.user: str = ""
        self.status: Optional[OrderStatus] = None
        self.price: float = -1
        self.amount: float = -1
        self.symbol_1: str = ""
        self.symbol_2: str = ""
        self.last_tx_time: str = ""
        self.last_tx: str = ""
        self.remains: float = -1
        super().__init__(*args)

    def init(self) -> None:
        self.order_id = self.json_obj["id"]
        self.time = self.json_obj["time"]
        self.order_type = self.json_obj["type"]
        self.user = self.json_obj["user"]
        self.price = float(self.json_obj["price"])
        self.amount = float(self.json_obj["amount"])
        self.symbol_1 = self.json_obj["symbol1"]
        self.symbol_2 = self.json_obj["symbol2"]
        self.last_tx_time = self.json_obj["lastTxTime"]
        self.last_tx = self.json_obj["lastTx"]
        self.remains = float(self.json_obj["remains"])
        self.status = self.parse_status()

    def parse_status(self) -> OrderStatus:
        status: str = self.json_obj["status"]
        if status == "d":
            return OrderStatus.DONE
        elif status == "c" or status == "cd":
            return OrderStatus.CANCELLED
        elif status == "a":
            return OrderStatus.ACTIVE
        else:
            raise Exception(f"Unknown order status \"{status}\". Order ID: {self.orderId}")

    def __str__(self):
        return f"order_id = {self.order_id}, time = {self.time}, order_type = {self.order_type}, user = {self.user}, price = {self.price}, " \
            f"amount = {self.amount}, symbol_1 = {self.symbol_1}, symbol_2 = {self.symbol_2}, " \
            f"last_tx_time = {self.last_tx_time}, last_tx = {self.last_tx}, remains = {self.remains}, status = {self.status}"


class CEXTicker(CEXApiData):
    def __init__(self, *args):
        self.bid: float = -1
        self.ask: float = -1
        self.low: float = -1
        self.high: float = -1
        self.last: float = -1
        self.volume: float = -1
        self.volume_30_d: float = -1
        self.timestamp: int = -1
        self.price_change: float = -1
        self.price_change_percentage: float = -1
        self.pair: str = ""
        super().__init__(*args)

    def init(self) -> None:
        self.bid = float(self.json_obj["bid"])
        self.ask = float(self.json_obj["ask"])
        self.low = float(self.json_obj["low"])
        self.high = float(self.json_obj["high"])
        self.last = float(self.json_obj["last"])
        self.volume = float(self.json_obj["volume"])
        self.volume_30_d = float(self.json_obj["volume30d"])
        self.timestamp = int(self.json_obj["timestamp"])
        self.price_change = float(self.json_obj["priceChange"])
        self.price_change_percentage = float(self.json_obj["priceChangePercentage"])
        self.pair = self.json_obj["pair"]

    def __str__(self):
        return f"bid = {self.bid}, ask = {self.ask}, low = {self.low}, high = {self.high}, last = {self.last}, " \
            f"volume = {self.volume}, volume_30_d = {self.volume_30_d}, timestamp = {self.timestamp}, " \
            f"price_change = {self.price_change}, price_change_percentage = {self.price_change_percentage}, " \
            f"pair = {self.pair}"


class CEXApiResponse(CEXApiData):
    def __init__(self, json_obj: Any, data_type: Optional[Type[CEXApiData]]):
        self.e: Optional[str] = None
        self.error: Optional[str] = None
        self.ok: Optional[str] = None
        self.data: Optional[CEXApiData] = None
        self.data_type = data_type
        super().__init__(json_obj)

    def init(self) -> None:
        if type(self.json_obj) != dict:
            return  # leave defaults
        self.e = self.json_obj.get("e", None)
        self.ok = self.json_obj.get("ok", None)
        self.error = self.json_obj.get("error", None)
        if (not self.error) and (not self.ok):
            self.ok = "ok"
        if self.data_type:
            if not self.json_obj.get("data", None):
                if not self.error or self.ok == "ok":
                    self.data = self.data_type(self.json_obj)
            else:
                self.data = self.data_type(self.json_obj.get("data"))

    def __str__(self):
        return f"ok = {self.ok}, e = {self.e}, error = {self.error}, data = {self.data}"
