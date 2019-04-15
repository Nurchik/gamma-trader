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
        self.id: str = ""
        self.time: str = ""
        super().__init__(*args)

    def init(self) -> None:
        self.id = self.json_obj["id"]
        self.time = self.json_obj["time"]

    def __str__(self):
        return f"id = {self.id}, time = {self.time}"


class CEXOrderInfo(CEXApiData):
    def __init__(self, *args):
        self.id: str = ""
        self.time: str = ""
        self.type: str = ""
        self.user: str = ""
        self.status: Optional[OrderStatus] = None
        self.price: float = -1
        self.amount: float = -1
        self.symbol1: str = ""
        self.symbol2: str = ""
        self.lastTxTime: str = ""
        self.lastTx: str = ""
        self.remains: float = -1
        self.orderId: str = ""
        super().__init__(*args)

    def init(self) -> None:
        self.id = self.json_obj["id"]
        self.time = self.json_obj["time"]
        self.type = self.json_obj["type"]
        self.user = self.json_obj["user"]
        self.price = float(self.json_obj["price"])
        self.amount = float(self.json_obj["amount"])
        self.symbol1 = self.json_obj["symbol1"]
        self.symbol2 = self.json_obj["symbol2"]
        self.lastTxTime = self.json_obj["lastTxTime"]
        self.lastTx = self.json_obj["lastTx"]
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
        return f"id = {self.id}, time = {self.time}, type = {self.type}, user = {self.user}, price = {self.price}, " \
            f"amount = {self.amount}, symbol1 = {self.symbol1}, symbol2 = {self.symbol2}, " \
            f"lastTxTime = {self.lastTxTime}, lastTx = {self.lastTx}, remains = {self.remains}, status = {self.status}"


class CEXTicker(CEXApiData):
    def __init__(self, *args):
        self.bid: float = -1
        self.ask: float = -1
        self.low: float = -1
        self.high: float = -1
        self.last: float = -1
        self.volume: float = -1
        self.volume30d: float = -1
        self.timestamp: int = -1
        self.priceChange: float = -1
        self.priceChangePercentage: float = -1
        self.pair: str = ""
        super().__init__(*args)

    def init(self) -> None:
        self.bid = float(self.json_obj["bid"])
        self.ask = float(self.json_obj["ask"])
        self.low = float(self.json_obj["low"])
        self.high = float(self.json_obj["high"])
        self.last = float(self.json_obj["last"])
        self.volume = float(self.json_obj["volume"])
        self.volume30d = float(self.json_obj["volume30d"])
        self.timestamp = int(self.json_obj["timestamp"])
        self.priceChange = float(self.json_obj["priceChange"])
        self.priceChangePercentage = float(self.json_obj["priceChangePercentage"])
        self.pair = self.json_obj["pair"]

    def __str__(self):
        return f"bid = {self.bid}, ask = {self.ask}, low = {self.low}, high = {self.high}, last = {self.last}, " \
            f"volume = {self.volume}, volume30d = {self.volume30d}, timestamp = {self.timestamp}, " \
            f"priceChange = {self.priceChange}, priceChangePercentage = {self.priceChangePercentage}, " \
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
