from exchange import CEXExchange, ServerError, RemoteExecutionError
from typing import Optional, NamedTuple, Tuple
from cex_objects import CEXTicker, OrderStatus
import logging


class OrderDone(Exception):
    def __init__(self):
        super().__init__("Selling done")


class OrderExpired(Exception):
    def __init__(self):
        super().__init__("Order expired")


class PartiallyExecutedOrder(Exception):
    def __init__(self, remains: float):
        self.remains = remains
        super().__init__("Partial execution")


class ChangeLevels(NamedTuple):
    ask_change: float
    bid_change: float


class TradingDirective(NamedTuple):
    action: str
    amount: float = -1
    price: float = -1
    pair: str = ""


class Trader:
    def __init__(self, exchange: CEXExchange, action: str, pair: str, amount: float, threshold_percent: float,
                 order_ttl: int = 10, significant_digits: int = 3):
        self.exchange = exchange
        self.pair = pair
        self.src_curr = pair.split("/")[0]
        self.dst_curr = pair.split("/")[1]
        self.amount = amount
        self.threshold_percent = threshold_percent / 100
        self.max_bid: float = -1
        self.min_ask: float = -1
        self.current_order: Optional[str] = None
        self.max_order_ttl = order_ttl
        self.order_ttl: int = 0
        self.action = action
        self.logger = logging.getLogger("4Trader")
        self.trade_ignited: bool = False
        self.significant_digits = significant_digits
        self.logger = logging.getLogger("gamma.trader")

    def process_ticker(self, ticker: CEXTicker) -> ChangeLevels:
        self.max_bid = max(self.max_bid, ticker.bid)
        if self.min_ask == -1:
            self.min_ask = ticker.ask
        else:
            self.min_ask = min(self.min_ask, ticker.ask)
        changes = ChangeLevels(ask_change=round(ticker.ask/self.min_ask, self.significant_digits),
                               bid_change=round(ticker.bid/self.max_bid, self.significant_digits))
        self.logger.debug(f"ticker={ticker}, max_bid = {self.max_bid}, min_ask = {self.min_ask}")
        self.logger.info("Ticker processed")
        return changes

    def process_changes(self, changes: ChangeLevels, ticker: CEXTicker) -> TradingDirective:
        if self.action == "buy":
            change = round(changes.ask_change - 1, self.significant_digits)
            self.logger.debug(f"Asset's sell price changed by {change * 100}%")
            if (change > 0) and (change > self.threshold_percent):
                self.logger.info(f"Threshold of {self.threshold_percent * 100}% reached. Start buying...")
                return TradingDirective(self.action, self.amount, ticker.ask, self.pair)
        else:
            change = round(1 - changes.bid_change, self.significant_digits)
            self.logger.debug(f"Asset's buy price changed by {change * 100}%")
            if (change > 0) and (change > self.threshold_percent):
                self.logger.info(f"Threshold of {self.threshold_percent * 100}% reached. Start selling...")
                return TradingDirective(self.action, self.amount, ticker.bid, self.pair)
        return TradingDirective("hold")

    def get_straight_directive(self, ticker: CEXTicker) -> TradingDirective:
        if self.action == "buy":
            price = ticker.ask
        else:
            price = ticker.bid
        self.logger.info(f"Generated straight directive")
        return TradingDirective(self.action, self.amount, price, self.pair)

    def control_order(self) -> None:
        order_info = self.exchange.get_order_info(self.current_order)
        order_status = order_info.status
        self.logger.debug(f"Controlling order {self.current_order}. Status - {order_status}")
        if order_status == OrderStatus.ACTIVE:
            self.logger.debug(f"Order: {self.current_order} is still being processed.")
            self.order_ttl += 1
            if self.order_ttl < self.max_order_ttl:
                return
            self.logger.info(f"Order: {self.current_order} reached ttl limit - {self.max_order_ttl}")
            self.exchange.cancel_order(self.current_order)
            raise OrderExpired()
        elif order_status == OrderStatus.DONE:
            self.logger.info(f"Order: {self.current_order} is done!")
            raise OrderDone()
        else:
            remains = order_info.remains
            self.logger.info(f"Order: {self.current_order} is cancelled. Remains: {remains}")

        if remains == 0:
            raise OrderDone()
        elif remains > 0:
            raise PartiallyExecutedOrder(remains)
        else:
            raise Exception(f"Unexpected negative valued remaining -> {remains}. Order: {self.current_order}")

    def trade_asset(self, trading_directive: TradingDirective) -> None:
        self.logger.debug(f"trading_directive={trading_directive}")
        self.current_order = self.exchange.place_order(trading_directive.action, trading_directive.pair,
                                                       trading_directive.price, trading_directive.amount).order_id
        self.logger.info(f'Order of type "{trading_directive.action}" created. ID - {self.current_order}')
        self.order_ttl = 0

    def process(self) -> None:
        if self.current_order:
            try:
                self.control_order()
                return
            except OrderDone as exc:
                raise exc
            except PartiallyExecutedOrder as peo:
                self.amount = peo.remains
            except Exception as err:
                raise err

        ticker = self.exchange.get_ticker(self.pair)
        if self.trade_ignited:
            trading_directive = self.get_straight_directive(ticker)
        else:
            changes = self.process_ticker(ticker)
            trading_directive = self.process_changes(changes, ticker)

        if trading_directive.action != "hold":
            self.logger.info("Trade ignited!")
            self.trade_ignited = True
            self.trade_asset(trading_directive)


